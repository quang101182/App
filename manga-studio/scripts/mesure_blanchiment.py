"""Mesure (T1-bis) : part de la page BLANCHIE par l'effacement d'avant (pixels non blancs devenus blancs, hors boites de
texte) -- pages OPM devenues blanches vs toutes les pages de Black Jack ch.1 et Noritaka ch.1 p.1-15 (a garder)."""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import ingest_page as ip
SRC = os.path.normpath(os.path.join(HERE, "..", "sources"))
def blanchiment(serie, ch, page):
    t = json.load(open(os.path.join(SRC, serie, ch, "traduction", "fr", "traduction.json"), encoding="utf-8"))
    p = [x for x in t["pages"] if x["page"] == page][0]
    im = ip.load_page(os.path.join(SRC, serie, ch, p["source"]))
    zs = [dict(b["box"], id=i) for i, b in enumerate(p["bulles"]) if (b.get("trad") or "").strip()]
    r, _ = ip.clean_bubbles(im, [dict(z) for z in zs])
    A = np.array(im.convert("L")); B = np.array(r.convert("L")); H, W = A.shape
    m = (B >= 250) & (A < 250)
    for z in zs:
        m[int(z["y"] * H):int((z["y"] + z["h"]) * H) + 1, int(z["x"] * W):int((z["x"] + z["w"]) * W) + 1] = False
    return round(100 * m.mean(), 2)
BL = {"ch_1": [12, 18, 22], "ch_2": [9], "ch_3": [1, 7], "ch_4": [11, 16, 23], "ch_6": [1, 11], "ch_7": [1, 6], "ch_8": [1, 11], "ch_9": [7, 10, 11, 18], "ch_10": [22]}
o = sorted(blanchiment("one-punch-man", c, p) for c, ps in BL.items() for p in ps)
print("OPM pages devenues blanches (%d) : min %.2f %% | %s" % (len(o), o[0], o))
ok = []
for c in ("ch_2", "ch_3", "ch_5"):
    t = json.load(open(os.path.join(SRC, "one-punch-man", c, "traduction", "fr", "traduction.json"), encoding="utf-8"))
    ok += [blanchiment("one-punch-man", c, x["page"]) for x in t["pages"] if x["page"] not in BL.get(c, [])]
b = sorted(blanchiment("black-jack-ni-yoroshiku", "ch_1", p) for p in range(1, 20))
n = sorted(blanchiment("noritaka", "ch_1", p) for p in range(1, 16))
print("OPM pages SAINES (%d) : max %.2f %% | %s" % (len(ok), max(ok), sorted(ok)[-6:]))
print("Black Jack ch.1 (19) : max %.2f %% | %s" % (b[-1], b[-6:]))
print("Noritaka ch.1 p.1-15 : max %.2f %% | %s" % (n[-1], n[-6:]))
