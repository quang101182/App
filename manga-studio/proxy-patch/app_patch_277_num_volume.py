# -*- coding: utf-8 -*-
"""v2.77.0 (Quang 26/09 14h57, capture Solo Leveling .../vol-2/) : le numero suggere d'apres l'adresse reconnait un VOLUME
ENTIER « …/vol-N/ » = ch. N (meme numerotation que manga-fetch 0.6.0 : RE_VOL). « vol-16-chapitre-179-5 » etait deja lu
(179.5) par la regle generique. Rejouable : python app_patch_277_num_volume.py [chemin de manga_studio.html]"""
import io, sys
P = sys.argv[1] if len(sys.argv) > 1 else r"D:\Download\02-Apps-Web\Repo-github\App\manga-studio\manga_studio.html"
s = io.open(P, encoding="utf-8", newline="").read()
if 'const VERSION = "2.77.0"' in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"
def rep(a, z):
    global s
    a, z = a.replace("\n", NL), z.replace("\n", NL)
    assert s.count(a) == 1, ("ancre", a[:70], s.count(a))
    s = s.replace(a, z)
rep("""    if (q && /^\d+(\.\d+)?$/.test(q)) return q;
""", """    if (q && /^\d+(\.\d+)?$/.test(q)) return q;
    const v = /\/vol-(\d+)\/?$/i.exec(u.pathname);                       // v2.77.0 : volume ENTIER « …/vol-2/ » = ch. 2 (manga-fetch)
    if (v) return v[1].replace(/^0+(?=\d)/, "");
""")
rep("<title>Manga Studio v2.76.0</title>", "<title>Manga Studio v2.77.0</title>")
rep('<span class="ver" id="verBadge">v2.76.0</span>', '<span class="ver" id="verBadge">v2.77.0</span>')
rep('const VERSION = "2.76.0";', 'const VERSION = "2.77.0";')
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("v2.77.0 applique")
