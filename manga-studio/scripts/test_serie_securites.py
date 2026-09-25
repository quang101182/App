#!/usr/bin/env python3
"""Banc manga-fetch 0.8.0 -- securites de serie, hors navigateur (verdict chiffre).

  A. _meme_contenu : un chapitre qui reprend >= 80 % des images du precedent est reconnu ; un chapitre different, non.
  B. _mettre_de_cote : le dossier est RENOMME a cote (jamais efface), contenu intact.
  C. Arguments : --jusqua-fin existe ; constantes (filet 300, saut 10, pause 3 s).
  D. Boucle de serie (lecture du source) : le plafond de 50 a disparu, le filet est commun a tous les modes,
     la pause precede chaque recherche du suivant, le « deja la » est imprime pour le proxy.

Mutation : `python test_serie_securites.py --mutation` sabote _meme_contenu (seuil a 101 %) -> A doit rougir.
Exit 0 = tout vert.
"""
import os, sys, tempfile, shutil, importlib.util

ICI = os.path.dirname(os.path.abspath(__file__))
MF = os.path.join(ICI, "..", "manga-fetch", "manga_fetch.py")
spec = importlib.util.spec_from_file_location("manga_fetch", MF)
mf = importlib.util.module_from_spec(spec); spec.loader.exec_module(mf)

OK, KO = [], []
def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))

if "--mutation" in sys.argv:
    orig = mf._meme_contenu
    def sabote(out, title, p, c):
        a = mf._empreintes(mf.chap_dir(out, title, c)); b = mf._empreintes(mf.chap_dir(out, title, p))
        return "x" if len(a) >= 2 and len(a & b) >= 1.01 * len(a) else None
    mf._meme_contenu = sabote

tmp = tempfile.mkdtemp(prefix="banc_serie_")
try:
    titre = "Banc Serie"
    def chapitre(n, contenus):
        d = mf.chap_dir(tmp, titre, n); os.makedirs(d, exist_ok=True)
        for i, c in enumerate(contenus, 1):
            open(os.path.join(d, f"{i:03d}.png"), "wb").write(c)
        return d
    chapitre("11", [b"p1-11", b"p2-11", b"p3-11", b"p4-11", b"p5-11"])
    chapitre("12", [b"p1-11", b"p2-11", b"p3-11", b"p4-11", b"p5-11"])          # le site a ressservi le 11
    chapitre("13", [b"p1-13", b"p2-13", b"p3-13", b"p4-13", b"p5-13"])          # vrai chapitre
    chapitre("14", [b"p1-13", b"autre", b"autre2", b"autre3", b"autre4"])       # 1 image commune sur 5 (couverture)
    print("=== A. contenu identique ===")
    r = mf._meme_contenu(tmp, titre, "11", "12")
    check("ch.12 = ch.11 reconnu", bool(r), r)
    check("ch.13 different -> rien", mf._meme_contenu(tmp, titre, "12", "13") is None)
    check("1 image commune sur 5 -> rien", mf._meme_contenu(tmp, titre, "13", "14") is None)
    check("chapitre absent -> rien", mf._meme_contenu(tmp, titre, "13", "99") is None)

    print("=== B. mise de cote ===")
    d12 = mf.chap_dir(tmp, titre, "12")
    nom = mf._mettre_de_cote(d12, "doublon")
    cible = os.path.join(os.path.dirname(d12), nom or "?")
    check("renvoie un nom « _doublon_ch_12_… »", bool(nom) and nom.startswith("_doublon_ch_12_"), nom)
    check("ancien dossier disparu", not os.path.exists(d12))
    check("contenu intact a cote", os.path.isdir(cible) and len(os.listdir(cible)) == 5)
    check("dossier absent -> None", mf._mettre_de_cote(d12, "doublon") is None)

    print("=== C. arguments et constantes ===")
    check("VERSION 0.8.0", mf.VERSION == "0.8.0", mf.VERSION)
    check("filet 300 / saut 10 / pause 3000", (mf.SERIE_FILET, mf.SERIE_SAUT_MAX, mf.SERIE_PAUSE_MS) == (300, 10, 3000))
    src = open(MF, encoding="utf-8").read()
    check("--jusqua-fin declare", '"--jusqua-fin"' in src)

    print("=== D. boucle de serie ===")
    check("plus de plafond 50", "min(50," not in src and "limite = 50" not in src and "50 if jusqua" not in src)
    check("filet commun (sans condition de mode)", "            if len(faits) > SERIE_FILET:" in src)
    i_pause = src.find("page.wait_for_timeout(SERIE_PAUSE_MS)"); i_suiv = src.find("num, raison = chapitre_suivant", i_pause)
    check("pause avant la recherche du suivant", 0 < i_pause < i_suiv)
    check("« DEJA LA » imprime", 'print("DEJA LA : "' in src)
    check("saut suspect : reprise au ch. propose", "(saut suspect)" in src and "reprise au ch. {num}" in src)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n=== VERDICT : {len(OK)}/{len(OK) + len(KO)} verts ===")
sys.exit(0 if not KO else 1)
