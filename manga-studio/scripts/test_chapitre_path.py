# -*- coding: utf-8 -*-
"""Banc manga-fetch 0.8.6 : chapitre_path() -- une PAGE dans l'adresse n'est pas un changement de chapitre, un vrai changement
de chapitre reste vu. Hors ligne (fonction pure). MUTATION : --ancien manga_fetch.py.bak-085 -> ROUGE.
Usage : python test_chapitre_path.py [--ancien chemin]"""
import os, sys, types

HERE = os.path.dirname(os.path.abspath(__file__))
F = sys.argv[sys.argv.index("--ancien") + 1] if "--ancien" in sys.argv else os.path.join(HERE, "..", "manga-fetch", "manga_fetch.py")
src = open(F, encoding="utf-8").read()
m = types.ModuleType("mf"); m.__file__ = F
try:
    exec(compile(src.split("\ndef main(")[0], F, "exec"), m.__dict__)
except Exception as e:
    print("chargement :", e)
cp = getattr(m, "chapitre_path", None)
OK, KO = [], []


def meme(a, b):
    return cp is not None and cp(a) == cp(b)


def check(nom, cond):
    (OK if cond else KO).append(nom); print(("  [OK] " if cond else "  [KO] ") + nom)


H = "https://site.example/hentai/serie-6/english/p/%s/"
check("« /p/1/ » -> « /p/2/ » : MÊME chapitre", meme(H % 1, H % 2))
check("« /p/1/ » -> « /p/35 » (sans / final) : même chapitre", meme(H % 1, (H % 35).rstrip("/")))
check("« -6/…/p/1/ » -> « -7/…/p/1/ » : chapitre CHANGÉ", not meme(H % 1, H.replace("-6/", "-7/") % 1) and cp is not None)
check("« /page/3/ » et « /page-4 » : pages du même chapitre", meme("https://s.example/read/abc/page/3/", "https://s.example/read/abc/page/9/")
      and meme("https://s.example/read/abc/page-4", "https://s.example/read/abc/page-5"))
U = "https://mangadex.org/chapter/0f2b4c1e-1111-2222-3333-444455556666"
check("MangaDex « /chapter/<uuid>/2 » -> « /5 » : même chapitre (règle d'avant gardée)", meme(U + "/2", U + "/5"))
check("MANGA Plus « /viewer/1000233 » -> « /viewer/1000234 » : chapitre CHANGÉ (identifiant gardé)",
      cp is not None and not meme("https://mangaplus.shueisha.co.jp/viewer/1000233", "https://mangaplus.shueisha.co.jp/viewer/1000234"))
check("« chapter-12/ » -> « chapter-13/ » : chapitre CHANGÉ", cp is not None and not meme("https://s.example/m/chapter-12/", "https://s.example/m/chapter-13/"))
check("« ?style=list » et « #top » ignorés", meme(H % 1 + "?style=list", H % 1 + "#top"))
G = "https://gal.example/s/%s/3904141-%d"
check("0.8.9 : « /s/<clé>/<galerie>-1 » -> « /s/<autre clé>/<galerie>-2 » : MÊME chapitre", meme(G % ("9b0c35bf36", 1), G % ("3db0618666", 2)))
check("0.8.9 : autre galerie -> chapitre CHANGÉ", cp is not None and not meme(G % ("9b0c35bf36", 1), "https://gal.example/s/9b0c35bf36/3904142-1"))
av = getattr(m, "adresse_suivante", None)
L = ["https://site.example/hentai/serie-5/english/p/1/", "https://site.example/hentai/serie/english/p/1/",
     "https://site.example/hentai/serie-8/english/p/1/", "https://site.example/hentai/serie-7/english/p/1/#x", "https://site.example/tag/7/"]
check("0.8.7 : « …-7/…/p/12/ » -> lien « …-8/…/p/1/ » = SUIVANT", av is not None and av("https://site.example/hentai/serie-7/english/p/12/", L, "7") == L[2])
check("0.8.7 : pas de N+1 sur la page -> rien (ni le 5, ni le 1er)", av is not None and av("https://site.example/hentai/serie-8/english/p/1/", L[:2], "8") == "")
check("0.8.7 : deux nombres différents -> rien (autre œuvre)", av is not None and av("https://s.example/a-7/b-1/", ["https://s.example/a-8/b-2/"], "7") == "")
check("0.8.7 : même adresse (page seule) -> rien", av is not None and av("https://site.example/hentai/serie-7/english/p/1/", ["https://site.example/hentai/serie-7/english/p/2/"], "7") == "")
print("\nVERDICT : %d/%d" % (len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
