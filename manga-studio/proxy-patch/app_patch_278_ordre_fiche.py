# -*- coding: utf-8 -*-
"""v2.78.0 (Quang 26/09 16h20) : fiche du chapitre -- les 4 lignes dans l'ordre LOGIQUE, celui des Reglages de la serie :
Narration -> Traduction -> Musique -> Video (la video assemble les trois autres ; sa ligne disait deja « narre d'abord »).
Avant (v2.60.0) : Narration, Video, Traduction, Musique. Rejouable : python app_patch_278_ordre_fiche.py [chemin]"""
import io, sys
P = sys.argv[1] if len(sys.argv) > 1 else r"D:\Download\02-Apps-Web\Repo-github\App\manga-studio\manga_studio.html"
s = io.open(P, encoding="utf-8", newline="").read()
if 'const VERSION = "2.78.0"' in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"
def rep(a, z):
    global s
    a, z = a.replace("\n", NL), z.replace("\n", NL)
    assert s.count(a) == 1, ("ancre", a[:70], s.count(a))
    s = s.replace(a, z)
rep("""   seule ouverte ; memorise sur l'appareil. Ordre du travail : narration, video, traduction, musique. */
const CL = [
  { k: "narr", sel: "#chapDetail .narr-box.bloc-narr", ic: "🎙", t: "Narration" },
  { k: "vid",  sel: "#chapVid",                        ic: "🎬", t: "Vidéo" },
  { k: "trad", sel: "#chapDetail .narr-box.bloc-trad", ic: "🌐", t: "Traduction" },
  { k: "mus",  sel: "#chapDetail .narr-box.bloc-mus",  ic: "🎵", t: "Musique" }];""",
"""   seule ouverte ; memorise sur l'appareil. v2.78.0 (Quang 26/09) : ordre LOGIQUE = celui des Reglages de la serie --
   narration, traduction, musique, puis VIDEO (elle assemble les trois autres). */
const CL = [
  { k: "narr", sel: "#chapDetail .narr-box.bloc-narr", ic: "🎙", t: "Narration" },
  { k: "trad", sel: "#chapDetail .narr-box.bloc-trad", ic: "🌐", t: "Traduction" },
  { k: "mus",  sel: "#chapDetail .narr-box.bloc-mus",  ic: "🎵", t: "Musique" },
  { k: "vid",  sel: "#chapVid",                        ic: "🎬", t: "Vidéo" }];""")
rep("""  const narr = document.querySelector(CL[0].sel), vid = $("chapVid");
  if (narr && vid && narr.nextElementSibling !== vid && vid.previousElementSibling !== narr) vid.parentNode.insertBefore(narr, vid);""",
"""  const blocs = CL.map(b => document.querySelector(b.sel));                    // v2.78.0 : les 4 blocs, dans l'ordre de CL
  if (blocs.every(Boolean)) for (let i = 1; i < blocs.length; i++) if (blocs[i - 1].nextElementSibling !== blocs[i]) blocs[i - 1].after(blocs[i]);""")
rep("<title>Manga Studio v2.77.0</title>", "<title>Manga Studio v2.78.0</title>")
rep('<span class="ver" id="verBadge">v2.77.0</span>', '<span class="ver" id="verBadge">v2.78.0</span>')
rep('const VERSION = "2.77.0";', 'const VERSION = "2.78.0";')
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("v2.78.0 applique")
