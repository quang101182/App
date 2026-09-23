"""Mesure (T1-bis, 4-sexies, 23/09/2026) : qu'est-ce qui distingue une VRAIE bulle d'un FOND de case / de page ?

Pour chaque zone de texte, on refait la diffusion de clean_bubbles (sans rien ecrire) et on releve : rapport a la boite
du texte, part de la page, contact avec le bord de la page, et contact avec le bord de la CASE (gros trait noir) --
sur les 20 pages OPM devenues blanches (v1.92) et sur les bulles legitimes a texte vertical etroit (Black Jack p.1).
Usage : python mesure_fonds.py
"""
import json, os, sys
import numpy as np
import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import ingest_page as ip                                # noqa: E402

SRC = os.path.normpath(os.path.join(HERE, "..", "sources"))
BLANCHES = {"ch_1": [12, 18, 22], "ch_2": [9], "ch_3": [1, 7], "ch_4": [11, 16, 23], "ch_6": [1, 11], "ch_7": [1, 6],
            "ch_8": [1, 11], "ch_9": [7, 10, 11, 18], "ch_10": [22]}


def mesure(img_path, t):
    im = ip.load_page(img_path)
    g = cv2.cvtColor(np.array(im.convert("RGB")), cv2.COLOR_RGB2GRAY)
    H, W = g.shape
    bx1, by1 = int(t["x"] * W), int(t["y"] * H)
    bx2, by2 = min(W, bx1 + max(1, int(t["w"] * W))), min(H, by1 + max(1, int(t["h"] * H)))
    boite = g[by1:by2, bx1:bx2]
    if boite.size == 0 or int(boite.max()) < 150:
        return None
    oy, ox = np.unravel_index(int(np.argmax(boite)), boite.shape)
    m = np.zeros((H + 2, W + 2), np.uint8)
    cv2.floodFill(g.copy(), m, (bx1 + int(ox), by1 + int(oy)), 0, (60,), (60,),
                  4 | cv2.FLOODFILL_MASK_ONLY | cv2.FLOODFILL_FIXED_RANGE | (255 << 8))
    c = m[1:H + 1, 1:W + 1] > 0
    aire = int(c.sum())
    if not aire or aire > 0.18 * H * W:
        return None
    ys, xs = np.where(c)
    bb = (xs.max() - xs.min() + 1) * (ys.max() - ys.min() + 1)
    return {"ratio": round(bb / ((bx2 - bx1) * (by2 - by1)), 1), "page": round(aire / (H * W) * 100, 2),
            "bord": bool(xs.min() <= 1 or ys.min() <= 1 or xs.max() >= W - 2 or ys.max() >= H - 2),
            "remplissage": round(aire / bb, 2)}


def zones(serie, ch, page):
    t = json.load(open(os.path.join(SRC, serie, ch, "traduction", "fr", "traduction.json"), encoding="utf-8"))
    for p in t["pages"]:
        if p["page"] == page:
            return p["source"], [dict(b["box"], texte=b.get("texte", "")) for b in p["bulles"]]
    return None, []


print("== FONDS qui ont blanchi une page (OPM v1.92, zones au ratio > 6)")
for ch, pages in BLANCHES.items():
    for pg in pages:
        src, zs = zones("one-punch-man", ch, pg)
        for z in zs:
            r = mesure(os.path.join(SRC, "one-punch-man", ch, src), z)
            if r and r["ratio"] > 6:
                print("  %s p.%d %-14s %s" % (ch, pg, z["texte"][:6], r))
print("== VRAIES bulles a texte etroit (Black Jack ch.1, ratio > 6)")
for pg in range(1, 20):
    src, zs = zones("black-jack-ni-yoroshiku", "ch_1", pg)
    for z in zs:
        r = mesure(os.path.join(SRC, "black-jack-ni-yoroshiku", "ch_1", src), z)
        if r and r["ratio"] > 6:
            print("  p.%d %-14s %s" % (pg, z["texte"][:6], r))
