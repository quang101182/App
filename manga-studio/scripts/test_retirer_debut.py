# -*- coding: utf-8 -*-
"""Banc manga-fetch 0.8.8 : retirer_debut_suivant() / dedoublonner -- hors ligne, dossiers temporaires.
A. derniere page du ch.1 = 1re du ch.2 (memes octets) -> retiree du ch.1, deplacee dans _retirees/, manifeste a jour, ch.2 intact.
B. pages differentes -> rien. C. meme taille mais octets differents -> rien. D. rejouer -> rien. MUTATION : --ancien -> ROUGE.
Usage : python test_retirer_debut.py [--ancien chemin/manga_fetch.py]"""
import json, os, shutil, sys, tempfile, types

HERE = os.path.dirname(os.path.abspath(__file__))
F = sys.argv[sys.argv.index("--ancien") + 1] if "--ancien" in sys.argv else os.path.join(HERE, "..", "manga-fetch", "manga_fetch.py")
m = types.ModuleType("mf"); m.__file__ = F
exec(compile(open(F, encoding="utf-8").read().split("\ndef main(")[0], F, "exec"), m.__dict__)
m.log_evt = lambda *a, **k: None
f = getattr(m, "retirer_debut_suivant", None)
OK, KO = [], []
T = tempfile.mkdtemp(prefix="banc_retirer_")


def check(nom, cond, d=""):
    (OK if cond else KO).append(nom); print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(d) if d else ""))


def chap(nom, pages):
    d = os.path.join(T, nom); os.makedirs(d)
    for i, b in enumerate(pages, 1):
        open(os.path.join(d, "page_%03d.png" % i), "wb").write(b)
    json.dump({"pages": [{"file": "page_%03d.png" % i} for i in range(1, len(pages) + 1)]}, open(os.path.join(d, "manifest.json"), "w"))
    return d


try:
    a, b = chap("ch_1", [b"A1", b"A2", b"OUVERTURE-2"]), chap("ch_2", [b"OUVERTURE-2", b"B2"])
    r = f(a, b) if f else ""
    ma = json.load(open(os.path.join(a, "manifest.json")))
    check("A. dernière page = 1re du suivant -> retirée", r == "page_003.png" and len(ma["pages"]) == 2 and not os.path.exists(os.path.join(a, "page_003.png")), r)
    check("A. jamais effacée : dans _retirees/", os.path.isfile(os.path.join(a, "_retirees", "page_003.png")))
    check("A. suivant intact", len(json.load(open(os.path.join(b, "manifest.json")))["pages"]) == 2 and os.path.isfile(os.path.join(b, "page_001.png")))
    check("D. rejouer -> rien", f is not None and f(a, b) == "")
    c, d = chap("ch_3", [b"C1", b"C2"]), chap("ch_4", [b"D1", b"D2"])
    check("B. pages différentes -> rien", f is not None and f(c, d) == "" and len(json.load(open(os.path.join(c, "manifest.json")))["pages"]) == 2)
    e, g = chap("ch_5", [b"E1", b"XY"]), chap("ch_6", [b"XZ", b"G2"])
    check("C. même taille, octets différents -> rien", f is not None and f(e, g) == "")
finally:
    shutil.rmtree(T, ignore_errors=True)
print("\nVERDICT : %d/%d" % (len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
