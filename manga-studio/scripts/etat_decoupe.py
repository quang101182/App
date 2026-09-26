# -*- coding: utf-8 -*-
"""ETAT DES LIEUX du decoupage des chapitres (Quang 26/09 01h00 : « tout est decoupe n'importe comment »). LECTURE SEULE.

Pour chaque chapitre (dossier ch_* avec manifest.json) d'une racine de sources : les pages sont lues DANS L'ORDRE du manifeste ;
entre deux pages consecutives de MEME largeur, le raccord est « dans le dessin » si la derniere ligne de l'une OU la premiere
ligne de l'autre n'est pas unie ET que le dessin CONTINUE d'une page a l'autre (lignes voisines ressemblantes) (ecart a la mediane > 24 sur > 2 % de la largeur -- la regle de _coupes_webtoon). Un bon
decoupage coupe dans les gouttieres (lignes unies) ; une bulle ou une case tranchee en deux donne un raccord dans le dessin.

Usage : python etat_decoupe.py <racine des sources> [--detail]
Sortie : une ligne par serie (chapitres, pages, raccords dans le dessin, chapitres a redecouper) ; --detail = par chapitre.
Verdict par chapitre : OK (<= 2 raccords dans le dessin) · A REDECOUPER (sinon). Rien n'est ecrit.
"""
import json, os, sys
from PIL import Image
import numpy as np
import importlib.util

_spec = importlib.util.spec_from_file_location("mf", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "manga-fetch", "manga_fetch.py"))
mf = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(mf)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RAC = sys.argv[1]
DETAIL = "--detail" in sys.argv
Image.MAX_IMAGE_PIXELS = None


def bords(chemin):
    with Image.open(chemin) as im:
        w, h = im.size
        g = im.convert("L")
        haut = np.asarray(g.crop((0, 0, w, min(8, h))), dtype=np.int16)
        bas = np.asarray(g.crop((0, max(0, h - 8), w, h)), dtype=np.int16)
    return w, h, haut, bas


def chapitre(d):
    man = json.load(open(os.path.join(d, "manifest.json"), encoding="utf-8"))
    info = []
    for p in man.get("pages") or []:
        f = os.path.join(d, p["file"])
        if os.path.isfile(f):
            try: info.append(bords(f))
            except Exception: pass
    # v2 (26/09 01h05) : une page de manga peut aller jusqu'au bord sans rien trancher (la suivante est une AUTRE image). Une
    # vraie coupe = le dessin CONTINUE : ligne non unie ET derniere ligne de l'une ~ premiere ligne de l'autre (ecart moyen < 18).
    # v3 : la regle de manga-fetch 0.8.2 (_coupe_dans_dessin) -- un raccord dans un espace verticalement stable (raye, uni)
    # n'est PAS une coupe dans le dessin (mesure v2 : 4 faux positifs sur 9 dans un fond « papier » raye, verifie a l'oeil).
    dessin = sum(1 for a, b in zip(info, info[1:]) if a[0] == b[0] and mf._coupe_dans_dessin(a[3], b[2]))
    ratios = sorted(h / w for w, h, *_ in info) or [0]
    return {"pages": len(info), "dessin": dessin, "decoupe": bool(man.get("decoupe")),
            "ratio_med": ratios[len(ratios) // 2]}


tot = {"series": 0, "chap": 0, "a_redecouper": 0}
for s in sorted(os.listdir(RAC)):
    ds = os.path.join(RAC, s)
    if s.startswith(("_", ".")) or not os.path.isdir(ds):
        continue
    chs = sorted((c for c in os.listdir(ds) if c.startswith("ch_") and os.path.isfile(os.path.join(ds, c, "manifest.json"))),
                 key=lambda c: float(c[3:]) if c[3:].replace(".", "", 1).isdigit() else 1e9)
    if not chs:
        continue
    res = {c: chapitre(os.path.join(ds, c)) for c in chs}
    mauvais = [c for c, r in res.items() if r["dessin"] > 2]
    tot["series"] += 1; tot["chap"] += len(chs); tot["a_redecouper"] += len(mauvais)
    print("%-40s %3d ch. · %5d p. · raccords dans le dessin : %4d · à redécouper : %d%s"
          % (s[:40], len(chs), sum(r["pages"] for r in res.values()), sum(r["dessin"] for r in res.values()), len(mauvais),
             (" (" + ", ".join(c[3:] for c in mauvais[:12]) + ("…" if len(mauvais) > 12 else "") + ")") if mauvais else ""))
    if DETAIL:
        for c, r in res.items():
            print("    %-10s %4d p. · ratio médian %.2f · découpé : %-3s · dans le dessin : %d%s"
                  % (c, r["pages"], r["ratio_med"], "oui" if r["decoupe"] else "non", r["dessin"], "  ← À REDÉCOUPER" if r["dessin"] > 2 else ""))
print("\nTOTAL : %d série(s), %d chapitre(s), %d à redécouper" % (tot["series"], tot["chap"], tot["a_redecouper"]))
