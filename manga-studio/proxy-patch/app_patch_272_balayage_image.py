# -*- coding: utf-8 -*-
"""v2.72.0 (Quang 26/09 12h26) : visionneuse -- balayer L'IMAGE vers la DROITE = page SUIVANTE, vers la gauche = precedente
(meme sens que la barre de la visionneuse et que les autres barres ; « celui-la on l'a oublie »).
Rejouable : python app_patch_272_balayage_image.py [chemin de manga_studio.html]"""
import io, sys
P = sys.argv[1] if len(sys.argv) > 1 else r"D:\Download\02-Apps-Web\Repo-github\App\manga-studio\manga_studio.html"
s = io.open(P, encoding="utf-8", newline="").read()
if 'const VERSION = "2.72.0"' in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"
def rep(a, z):
    global s
    a, z = a.replace("\n", NL), z.replace("\n", NL)
    assert s.count(a) == 1, ("ancre", a[:70], s.count(a))
    s = s.replace(a, z)
rep("      if (Math.abs(dx) > 60 && Math.abs(dx) > 1.5 * Math.abs(dy)) lbShow(LB + (dx < 0 ? 1 : -1));",
    "      if (Math.abs(dx) > 60 && Math.abs(dx) > 1.5 * Math.abs(dy)) lbShow(LB + (dx > 0 ? 1 : -1));   // v2.72.0 : vers la DROITE = suivante (comme la barre)")
rep("<title>Manga Studio v2.71.0</title>", "<title>Manga Studio v2.72.0</title>")
rep('<span class="ver" id="verBadge">v2.71.0</span>', '<span class="ver" id="verBadge">v2.72.0</span>')
rep('const VERSION = "2.71.0";', 'const VERSION = "2.72.0";')
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("v2.72.0 applique")
