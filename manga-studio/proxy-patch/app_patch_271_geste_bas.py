# -*- coding: utf-8 -*-
"""v2.71.0 (Quang 26/09 12h18) : selecteur rapide -- glisser la barre du bas VERS LE BAS pour l'ouvrir (au lieu de vers le
haut, declenche sans le vouloir : c'est le geste du defilement et celui qui quitte l'application). Vers le haut n'ouvre plus rien.
Rejouable : python app_patch_271_geste_bas.py [chemin de manga_studio.html]"""
import io, sys
P = sys.argv[1] if len(sys.argv) > 1 else r"D:\Download\02-Apps-Web\Repo-github\App\manga-studio\manga_studio.html"
s = io.open(P, encoding="utf-8", newline="").read()
if 'const VERSION = "2.71.0"' in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"
def rep(a, z):
    global s
    a, z = a.replace("\n", NL), z.replace("\n", NL)
    assert s.count(a) == 1, ("ancre", a[:70], s.count(a))
    s = s.replace(a, z)
rep("function selGlisserHaut(el){                  // glisser la barre VERS LE HAUT (> 50 px, net) = ouvrir ; gauche / droite gardent leur role",
    "function selGlisserHaut(el){                  // v2.71.0 : glisser la barre VERS LE BAS (> 24 px, net : sous une barre collee en bas il n'y a que ~30-45 px de course) = ouvrir ; gauche / droite gardent leur role")
rep("    if (dy < -50 && Math.abs(dy) > Math.abs(dx) * 1.5){ const c = selContexte(); if (c) selOuvrir(c); } }, { passive: true });",
    "    if (dy > 24 && Math.abs(dy) > Math.abs(dx) * 1.5){ const c = selContexte(); if (c) selOuvrir(c); } }, { passive: true });")
rep('    el.title = "toucher : aller à… (ou glisser la barre du bas vers le haut)";',
    '    el.title = "toucher : aller à… (ou glisser la barre du bas vers le bas)";')
rep("/* la poignee rappelle le geste « glisser vers le haut » ;", "/* la poignee signale la barre a glisser (v2.71.0 : VERS LE BAS pour « aller a… ») ;")
rep("<title>Manga Studio v2.70.0</title>", "<title>Manga Studio v2.71.0</title>")
rep('<span class="ver" id="verBadge">v2.70.0</span>', '<span class="ver" id="verBadge">v2.71.0</span>')
rep('const VERSION = "2.70.0";', 'const VERSION = "2.71.0";')
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("v2.71.0 applique")
