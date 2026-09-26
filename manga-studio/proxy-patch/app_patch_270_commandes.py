# -*- coding: utf-8 -*-
"""v2.70.0 (Quang 26/09 11h48-11h49) : lecteur video -- commandes AFFICHEES EN PERMANENCE ; elles ne s'effacent plus
qu'en PLEIN ECRAN (« si j'ai envie, je n'ai qu'a passer en plein ecran »). Sortie du plein ecran = elles reviennent.
Rejouable : python app_patch_270_commandes.py [chemin de manga_studio.html]"""
import io, sys
P = sys.argv[1] if len(sys.argv) > 1 else r"D:\Download\02-Apps-Web\Repo-github\App\manga-studio\manga_studio.html"
s = io.open(P, encoding="utf-8", newline="").read()
if 'const VERSION = "2.70.0"' in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"
def rep(a, z):
    global s
    a, z = a.replace("\n", NL), z.replace("\n", NL)
    assert s.count(a) == 1, ("ancre", a[:70], s.count(a))
    s = s.replace(a, z)

rep("""function vidReveil(){                                                      // F : la barre revient, et repart dans 3 s si ca joue
  $("vidLecteur").classList.remove("calme"); clearTimeout(VID.calmeT);
  VID.calmeT = setTimeout(() => {""",
"""function vidReveil(){      // F : la barre revient ; v2.70.0 : elle ne repart (3 s, si ca joue) QU'EN PLEIN ECRAN -- sinon toujours affichee
  $("vidLecteur").classList.remove("calme"); clearTimeout(VID.calmeT);
  if (document.fullscreenElement !== $("vidLecteur")) return;
  VID.calmeT = setTimeout(() => {""")
rep("""  $("vidPlein").onclick = async () => {""",
"""  document.addEventListener("fullscreenchange", () => { if (!$("vidLecteur").hidden) vidReveil(); });   // v2.70.0 : entree = effacement arme, sortie = barre rendue
  $("vidPlein").onclick = async () => {""")
rep("<title>Manga Studio v2.69.0</title>", "<title>Manga Studio v2.70.0</title>")
rep('<span class="ver" id="verBadge">v2.69.0</span>', '<span class="ver" id="verBadge">v2.70.0</span>')
rep('const VERSION = "2.69.0";', 'const VERSION = "2.70.0";')
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("v2.70.0 applique")
