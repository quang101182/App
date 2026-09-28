"""manga-fetch 0.8.8 -> 0.8.9 (28/09) : lecteur PAGE PAR PAGE dont l'adresse de chaque page est « /s/<cle hex>/<galerie>-<page> »
(la cle CHANGE a chaque page, la galerie non) : chaque page aurait ete prise pour un nouveau chapitre. chapitre_path() ramene
ces adresses a la galerie (« /s/-/<galerie> »). Rejouable."""
import shutil, sys

F = "D:/Download/02-Apps-Web/Repo-github/App/manga-studio/manga-fetch/manga_fetch.py"
s = open(F, encoding="utf-8", newline="").read()
if "RE_PAGE_GALERIE" in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"
shutil.copy2(F, F + ".bak-088")


def rep(a, b):
    global s
    a, b = a.replace("\n", NL), b.replace("\n", NL)
    assert s.count(a) == 1, (s.count(a), a[:80])
    s = s.replace(a, b)


rep('VERSION = "0.8.8"  # 0.8.8 (28/09)', 'VERSION = "0.8.9"  # 0.8.9 (28/09) : pages « /s/<cle>/<galerie>-<page> » = une seule galerie ; 0.8.8 (28/09)')
rep('''RE_PAGE_FINALE = re.compile(r"/(?:p|page|pg)[-/]\\d+/?$", re.I)   # 0.8.6 : « .../p/3/ », « .../page/3 », « .../page-3/ »''',
    '''RE_PAGE_FINALE = re.compile(r"/(?:p|page|pg)[-/]\\d+/?$", re.I)   # 0.8.6 : « .../p/3/ », « .../page/3 », « .../page-3/ »
RE_PAGE_GALERIE = re.compile(r"/s/[0-9a-f]{6,16}/(\\d+)-\\d+/?$", re.I)  # 0.8.9 : « /s/<cle hex>/<galerie>-<page> » (cle changeante)''')
rep('''    u = (u or "").split("?")[0].split("#")[0]
    m = RE_PAGE_FINALE.search(u)''', '''    u = (u or "").split("?")[0].split("#")[0]
    g = RE_PAGE_GALERIE.search(u)
    if g:                                                   # 0.8.9 : la galerie, pas la page (ni sa cle)
        return u[:g.start()] + "/s/-/" + g.group(1)
    m = RE_PAGE_FINALE.search(u)''')
open(F, "w", encoding="utf-8", newline="").write(s)
print("ok 0.8.9")
