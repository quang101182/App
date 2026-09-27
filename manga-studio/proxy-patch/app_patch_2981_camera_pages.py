# -*- coding: utf-8 -*-
"""v2.98.1 (27/09, Quang 15h10 : « case par case activé par défaut […] on a déjà la fonction ») : la caméra « suivre la case »
du lecteur des Dialogues ne zoomait JAMAIS quand les images d'origine du chapitre ne s'appellent pas page_NNN.png au numéro de
la page (mesuré sur l'app réelle : noritaka ch.1 = 0 zoom sur 22 répliques, 22 « sans case »). Cause : `dllCaseDe` cherchait
les cases sous `x.file` = nom de la page TRADUITE (page_005.png) alors que /manga/cases les range sous le nom de l'image
d'ORIGINE (manifeste : page 5 = page_011.jpg). Correctif : on cherche d'abord sous le fichier d'origine de la page
(`e.fichiers[page - 1]`, déjà servi par /manga/dialogues), puis sous `x.file` (repli, comportement d'avant). Suppose v2.98.0.
Rejouable."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v2.98.1" in s[:900]:
    print("deja applique"); sys.exit(0)
if "v2.98.0" not in s[:1400]:
    print("ERREUR : appliquer d'abord app_patch_2980_retrait_reste.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


rep("<title>Manga Studio v2.98.0</title>", "<title>Manga Studio v2.98.1</title>")
rep('<span class="ver" id="verBadge">v2.98.0</span>', '<span class="ver" id="verBadge">v2.98.1</span>')
rep('const VERSION = "2.98.0";', 'const VERSION = "2.98.1";   // v2.98.1 : la camera « suivre la case » trouve les cases quand les images d origine ne portent pas le n° de page')
rep("""  Object.assign(DLL, { d, doc: e.doc, dist: e.distribution || {}, liste, i: Math.max(0, Math.min(liste.length - 1, depuis || 0)), page: null, pause: false, cases: null,""",
    """  Object.assign(DLL, { d, doc: e.doc, dist: e.distribution || {}, liste, i: Math.max(0, Math.min(liste.length - 1, depuis || 0)), page: null, pause: false, cases: null, fich,""")
rep("""  const pg = DLL.cases && DLL.cases.pages && DLL.cases.pages[x.file];""",
    """  const cp = DLL.cases && DLL.cases.pages;                          // v2.98.1 : cases rangees sous le nom de l'image d'ORIGINE
  const pg = cp && ((DLL.fich && cp[DLL.fich[x.page - 1]]) || cp[x.file]);""")
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok v2.98.1")
