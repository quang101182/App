# -*- coding: utf-8 -*-
"""v2.90.0 (27/09, Quang 13h47 : « quand je fais un retour en arriere via la navigation par gestes, ca peut me ramener a
l'application principale ») : la bascule principale <-> secondaire sur le TELEPHONE faisait `location.href = <autre adresse>`
-> une ENTREE D'HISTORIQUE de plus dans la meme fenetre : le geste retour y revenait. Desormais `location.replace()` : l'autre
application REMPLACE la page, le geste retour ne ramene plus a celle qu'on vient de quitter. (Sur le PC, la secondaire vit dans
sa propre fenetre : inchange.) Suppose v2.89.0. Rejouable."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v2.90.0" in s[:400]:
    print("deja applique"); sys.exit(0)
if "v2.89.0" not in s[:400]:
    print("ERREUR : appliquer d'abord app_patch_2890_defauts_voix.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


rep("<title>Manga Studio v2.89.0</title>", "<title>Manga Studio v2.90.0</title>")
rep('<span class="ver" id="verBadge">v2.89.0</span>', '<span class="ver" id="verBadge">v2.90.0</span>')
rep('const VERSION = "2.89.0";', 'const VERSION = "2.90.0";   // v2.90.0 : la bascule d application REMPLACE la page (le geste retour n y revient plus)')
rep("""  const u = espaceAutreURL(); if (u) location.href = u;         // repli : pas de fenetre dediee (ou telephone)""",
    """  const u = espaceAutreURL(); if (u) location.replace(u);      // repli : pas de fenetre dediee (ou telephone) -- v2.90.0 : replace, pas d'historique""")
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
