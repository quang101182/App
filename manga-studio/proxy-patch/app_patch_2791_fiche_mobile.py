# -*- coding: utf-8 -*-
"""v2.79.1 (Quang 26/09 16h50 : « tout ce que tu trouves a corriger, tu le fais ») -- deux defauts PREEXISTANTS de la fiche :
1. a 360 px, l'etat de la Narration d'un chapitre NON narre faisait 0 px (les pastilles de cout prenaient la place)
   -> pastilles sur une 2e ligne, comme les ingredients de la Video (v2.79.0) ;
2. « Traduire » affiche dans l'en-tete meme quand le chapitre est DEJA dans la langue voulue -> plus de bouton
   (changer de langue cible reste possible en depliant la ligne).
Rejouable : python app_patch_2791_fiche_mobile.py [chemin de manga_studio.html]"""
import io, sys
P = sys.argv[1] if len(sys.argv) > 1 else r"D:\Download\02-Apps-Web\Repo-github\App\manga-studio\manga_studio.html"
s = io.open(P, encoding="utf-8", newline="").read()
if 'const VERSION = "2.79.1"' in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"
def rep(a, z):
    global s
    a, z = a.replace("\n", NL), z.replace("\n", NL)
    assert s.count(a) == 1, ("ancre", a[:70], s.count(a))
    s = s.replace(a, z)
rep("""  .cl-est{display:none} .cl-box.bloc-narr:not(.cl-ouv) .cl-est{display:flex;flex-wrap:wrap;flex:0 1 auto;min-width:0}""",
"""  .cl-est{display:none} .cl-box.bloc-narr:not(.cl-ouv) .cl-est{display:flex;flex-wrap:wrap;flex:0 1 auto;min-width:0}
  .cl-box.bloc-narr:not(.cl-ouv) > .cl-tete{flex-wrap:wrap;row-gap:4px}                 /* v2.79.1 : couts en 2e ligne */
  .cl-box.bloc-narr:not(.cl-ouv) .cl-est:not(:empty){order:10;flex:1 1 100%;padding-left:34px}""")
rep("""    return { etat, est: "", act: clBouton("🌐 Traduire", "btnTraduire") };""",
"""    return { etat, est: "", act: meme ? "" : clBouton("🌐 Traduire", "btnTraduire") };   // v2.79.1 : rien a traduire""")
rep("<title>Manga Studio v2.79.0</title>", "<title>Manga Studio v2.79.1</title>")
rep('<span class="ver" id="verBadge">v2.79.0</span>', '<span class="ver" id="verBadge">v2.79.1</span>')
rep('const VERSION = "2.79.0";', 'const VERSION = "2.79.1";')
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("v2.79.1 applique")
