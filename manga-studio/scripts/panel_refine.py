# -*- coding: utf-8 -*-
"""Raffinement des bords de cases : Pixtral localise, l'image tranche.

Constat mesure (essai 7) : Pixtral trouve le bon NOMBRE de cases, la bonne ZONE
et le bon ORDRE, mais quantifie sur une grille (2 largeurs, 1 hauteur proposees
la ou la planche en contient 5 et 4). IoU moyen 0,66 -> inexploitable pour
decouper proprement.

Ici : on garde sa localisation, et on va chercher dans l'IMAGE ou sont les vrais
bords. Deux signaux, dans cet ordre :
 1. la GOUTTIERE : une bande de lignes/colonnes quasi entierement blanches ;
 2. la BORDURE   : une ligne/colonne tres majoritairement noire (le trait du cadre).
Chaque bord de la boite proposee est "aimante" vers le signal le plus proche,
dans une fenetre de recherche bornee (sinon on saute sur la case voisine).

Aucune dependance a OpenCV : numpy + PIL suffisent pour des projections.
"""
import json, os, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SEARCH = 0.06      # fenetre de recherche, en fraction de la page
WHITE = 0.985      # une ligne est "gouttiere" si >= 98,5 % de pixels clairs
BLACK = 0.55       # une ligne est "bordure" si >= 55 % de pixels sombres


def profiles(img):
    """Renvoie, par ligne et par colonne, la fraction de pixels clairs et sombres."""
    a = np.asarray(img.convert("L"), dtype=np.uint8)
    light = a > 200
    dark = a < 80
    return {
        "row_light": light.mean(axis=1), "row_dark": dark.mean(axis=1),
        "col_light": light.mean(axis=0), "col_dark": dark.mean(axis=0),
    }


def snap(pos, limit, light, dark, inward):
    """Aimante une coordonnee vers le vrai bord.

    inward = +1 si on cherche le bord GAUCHE/HAUT d'une case (on veut la fin de
    la gouttiere), -1 pour le bord DROIT/BAS. On prefere une bordure franche ;
    a defaut, le bord de la gouttiere ; sinon on ne bouge pas.
    """
    win = int(limit * SEARCH)
    lo, hi = max(0, pos - win), min(limit - 1, pos + win)
    if hi <= lo:
        return pos, "hors-cadre"
    band = range(lo, hi + 1)
    borders = [i for i in band if dark[i] >= BLACK]
    if borders:
        best = min(borders, key=lambda i: abs(i - pos))
        return best, "bordure"
    gutters = [i for i in band if light[i] >= WHITE]
    if gutters:
        # bord interieur de la gouttiere la plus proche
        best = min(gutters, key=lambda i: abs(i - pos))
        while inward > 0 and best + 1 <= hi and light[best + 1] >= WHITE:
            best += 1
        while inward < 0 and best - 1 >= lo and light[best - 1] >= WHITE:
            best -= 1
        return best, "gouttiere"
    return pos, "inchange"


def refine(page_path, panels_json):
    im = Image.open(page_path).convert("RGB")
    W, H = im.size
    pr = profiles(im)
    data = json.load(open(panels_json, encoding="utf-8"))
    out = []
    for p in data["panels"]:
        x1, y1 = int(p["x"] * W), int(p["y"] * H)
        x2, y2 = x1 + int(p["w"] * W), y1 + int(p["h"] * H)
        nx1, r1 = snap(x1, W, pr["col_light"], pr["col_dark"], +1)
        nx2, r2 = snap(x2, W, pr["col_light"], pr["col_dark"], -1)
        ny1, r3 = snap(y1, H, pr["row_light"], pr["row_dark"], +1)
        ny2, r4 = snap(y2, H, pr["row_light"], pr["row_dark"], -1)
        if nx2 - nx1 < 40 or ny2 - ny1 < 40:   # garde-fou : on ne degenere pas une case
            nx1, ny1, nx2, ny2 = x1, y1, x2, y2
            r1 = r2 = r3 = r4 = "rejete"
        q = dict(p)
        q.update({"x": nx1 / W, "y": ny1 / H, "w": (nx2 - nx1) / W, "h": (ny2 - ny1) / H,
                  "snap": [r1, r2, r3, r4]})
        out.append(q)
        print("  case %-2s  %-9s %-9s %-9s %-9s" % (p.get("id"), r1, r2, r3, r4), flush=True)
    data["panels"] = out
    dest = panels_json.replace(".json", "_refined.json")
    json.dump(data, open(dest, "w", encoding="utf-8"), indent=1)
    return dest


def iou(a, b):
    ax1, ay1, ax2, ay2 = a["x"], a["y"], a["x"] + a["w"], a["y"] + a["h"]
    bx1, by1, bx2, by2 = b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"]
    ix = max(0, min(ax2, bx2) - max(ax1, bx1))
    iy = max(0, min(ay2, by2) - max(ay1, by1))
    inter = ix * iy
    ua = (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - inter
    return inter / ua if ua > 0 else 0


def score(truth_json, panels_json, label):
    T = json.load(open(truth_json, encoding="utf-8"))["panels"]
    P = json.load(open(panels_json, encoding="utf-8"))["panels"]
    vals = [max(iou(t, p) for p in P) for t in T]
    ok = sum(1 for v in vals if v >= 0.5)
    print("%-10s  IoU moyen %.3f   >=0.5 : %d/%d   detail %s"
          % (label, sum(vals) / len(vals), ok, len(T), " ".join("%.2f" % v for v in vals)), flush=True)
    return sum(vals) / len(vals), ok


if __name__ == "__main__":
    page = os.path.join(HERE, "manga_out", "page_hard.png")
    pj = os.path.join(HERE, "ingest_out", "page_hard_panels.json")
    tj = os.path.join(HERE, "manga_out", "page_hard_truth.json")
    print("=== raffinement des bords ===", flush=True)
    rj = refine(page, pj)
    print(flush=True)
    a = score(tj, pj, "AVANT")
    b = score(tj, rj, "APRES")
    print("\ngain IoU : %+.3f | cases >=0.5 : %d -> %d" % (b[0] - a[0], a[1], b[1]), flush=True)
