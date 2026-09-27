# -*- coding: utf-8 -*-
"""v3.4.2 (27/09, Quang 19h14 : « tous les curseurs de volume […] il faut absolument indiquer les pourcentages, comme sur
le reste de l'application […] smartphone et PC ») : les 2 curseurs du lecteur des Dialogues (volume general, volume de la
musique) recoivent le « NN % » commun (.curseur-val[data-pour], tenu a jour par majCurseurs). Suppose v3.4.1. Rejouable."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v3.4.2" in s[:900]:
    print("deja applique"); sys.exit(0)
if "v3.4.1" not in s[:1400]:
    print("ERREUR : appliquer d'abord app_patch_3410_appui_long.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"
def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:80], s.count(a))
    s = s.replace(a, b)
rep("<title>Manga Studio v3.4.1</title>", "<title>Manga Studio v3.4.2</title>")
rep('<span class="ver" id="verBadge">v3.4.1</span>', '<span class="ver" id="verBadge">v3.4.2</span>')
rep('const VERSION = "3.4.1";', 'const VERSION = "3.4.2";   // v3.4.2 : pourcentages sur les curseurs de volume du lecteur des Dialogues')
rep("""🔊 <input type="range" class="lec-vol" id="dllVol" min="0" max="100" step="1"></label>'""",
    """🔊 <input type="range" class="lec-vol" id="dllVol" min="0" max="100" step="1"><span class="curseur-val" data-pour="dllVol"></span></label>'""")
rep("""<input type="range" class="lec-vol" id="dllMusVol" min="0" max="100" step="1" title="volume de la musique"></div></div>';""",
    """<input type="range" class="lec-vol" id="dllMusVol" min="0" max="100" step="1" title="volume de la musique"><span class="curseur-val" data-pour="dllMusVol"></span></div></div>';""")
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok v3.4.2")
