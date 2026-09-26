# -*- coding: utf-8 -*-
"""Banc manga-fetch 0.8.2 : decoupage des rubans en TUILES (critere de continuite du dessin). Travaille sur des COPIES.

Chaque argument = un dossier de chapitre (ch_*) ; prefixe « originaux: » = reconstituer le chapitre AVANT decoupage depuis son
sous-dossier originaux/ (pour rejouer un webtoon deja bien decoupe). Chaque copie est decoupee par decouper_bandes() puis mesuree
(raccords « dans le dessin », comme etat_decoupe.py). Verdict par cas, attendu donne par le prefixe du cas :
  ruban:<dossier>     -> doit etre decoupe, <= 2 raccords dans le dessin apres
  manga:<dossier>     -> ne doit PAS etre touche (decouper_bandes -> None, pages identiques)
N'imprime ni nom ni adresse (cas numerotes). Usage : python test_decoupe_rubans.py ruban:D1 manga:D2 ruban:originaux:D3 …
"""
import importlib.util, json, os, shutil, sys, tempfile
import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ICI = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("mf", os.path.join(ICI, "..", "manga-fetch", "manga_fetch.py"))
mf = importlib.util.module_from_spec(spec); spec.loader.exec_module(mf)


def dessin(d):
    """Raccords qui tranchent le dessin (mf._coupe_dans_dessin : un espace raye/uni verticalement stable n'en est pas un)."""
    man = json.load(open(os.path.join(d, "manifest.json"), encoding="utf-8"))
    b = []
    for p in man["pages"]:
        with Image.open(os.path.join(d, p["file"])) as im:
            a = np.asarray(im.convert("L"), dtype=np.int16)
        b.append((a.shape[1], np.vstack([a[:8], a[-8:]])))
    return len(b), sum(1 for x, y in zip(b, b[1:]) if x[0] == y[0] and mf._coupe_dans_dessin(x[1][8:], y[1][:8]))


OK = KO = 0
tmp = tempfile.mkdtemp(prefix="banc_rubans_")
try:
    for n, arg in enumerate(sys.argv[1:], 1):
        attendu, _, src = arg.partition(":")
        dst = os.path.join(tmp, "cas%d" % n)
        if src.startswith("originaux:"):
            src = src[len("originaux:"):]
            shutil.copytree(os.path.join(src, "originaux"), dst)
        else:
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("originaux"))
        man = json.load(open(os.path.join(dst, "manifest.json"), encoding="utf-8"))
        man.pop("decoupe", None); json.dump(man, open(os.path.join(dst, "manifest.json"), "w", encoding="utf-8"))
        p0, d0 = dessin(dst)
        r = mf.decouper_bandes(dst)
        p1, d1 = dessin(dst)
        if attendu == "ruban":
            bon = bool(r) and d1 <= 2
        else:
            bon = r is None and p1 == p0
        OK += bon; KO += not bon
        print("  [%s] cas %d (%s) : %d p. -> %d p. · raccords dans le dessin %d -> %d%s"
              % ("OK" if bon else "KO", n, attendu, p0, p1, d0, d1,
                 (" · coupes hors gouttière %d" % r["coupes_hors_gouttiere"]) if r else " · non touché"))
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print("\nVERDICT : %d OK / %d KO" % (OK, KO))
sys.exit(1 if KO else 0)
