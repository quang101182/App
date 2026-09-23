"""Mesure (chantier 4-septies, remontee Video Studio 24/09) : part de la page ou du DESSIN a ete remplace par du blanc uni.

Critere propose par Video Studio : blocs de 24 px blancs unis dans la traduction (moyenne > 248, ecart-type < 4) la ou
l'original avait du dessin (ecart-type > 25). Pages fautives > 20 %, pages correctes < 16 % (selon eux).

Usage : python mesure_cases_effacees.py [serie/ch_N ...]   (defaut : OPM ch.1-10, Black Jack ch.1-2, Noritaka ch.1)
"""
import json, os, sys
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SRC = os.path.normpath(os.path.join(HERE, "..", "sources"))
BLOC = 24


def cases_effacees(orig, trad):
    """% des blocs de la page : dessin dans l'original, blanc uni dans la traduction."""
    A = np.asarray(orig.convert("L"), dtype=np.float32)
    B = np.asarray(trad.convert("L").resize(orig.size), dtype=np.float32)
    H, W = A.shape; h, w = H // BLOC, W // BLOC
    a = A[:h * BLOC, :w * BLOC].reshape(h, BLOC, w, BLOC); b = B[:h * BLOC, :w * BLOC].reshape(h, BLOC, w, BLOC)
    dessin = a.std(axis=(1, 3)) > 25
    blanc = (b.mean(axis=(1, 3)) > 248) & (b.std(axis=(1, 3)) < 4)
    return 100.0 * float((dessin & blanc).mean())


def chapitre(rel):
    t = json.load(open(os.path.join(SRC, rel, "traduction", "fr", "traduction.json"), encoding="utf-8"))
    out = []
    for p in t["pages"]:
        f = os.path.join(SRC, rel, "traduction", "fr", "page_%03d.png" % p["page"])
        if not os.path.isfile(f):
            continue
        out.append((p["page"], cases_effacees(Image.open(os.path.join(SRC, rel, p["source"])), Image.open(f))))
    return out


if __name__ == "__main__":
    chs = sys.argv[1:] or (["one-punch-man/ch_%d" % i for i in range(1, 11)]
                           + ["black-jack-ni-yoroshiku/ch_1", "black-jack-ni-yoroshiku/ch_2", "noritaka/ch_1"])
    tout = []
    for rel in chs:
        r = chapitre(rel)
        tout += [(v, rel, p) for p, v in r]
        haut = sorted(r, key=lambda x: -x[1])[:3]
        print("%-32s %3d pages | max : %s" % (rel, len(r), ", ".join("p.%d %.1f %%" % (p, v) for p, v in haut)))
    tout.sort(reverse=True)
    print("\nLes 12 pires :")
    for v, rel, p in tout[:12]:
        print("  %5.1f %%  %s p.%d" % (v, rel, p))
