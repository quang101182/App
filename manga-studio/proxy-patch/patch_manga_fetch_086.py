"""manga-fetch 0.8.5 -> 0.8.6 (28/09) : un lecteur qui met le numero de PAGE dans l'adresse sous la forme « .../p/N/ »,
« .../page/N/ » ou « .../page-N/ » (et le change AU DEFILEMENT) etait pris pour un changement de CHAPITRE des la 2e page ->
« capture tronquee, 1 page ». La regle « chemin du chapitre » (avant : seulement MangaDex /chapter/<uuid>/<n>) sort au niveau du
module (chapitre_path, testable) et retire aussi ces segments de page. Un vrai changement de chapitre (…-6/… -> …-7/…) reste
vu. Rejouable."""
import shutil, sys

F = "D:/Download/02-Apps-Web/Repo-github/App/manga-studio/manga-fetch/manga_fetch.py"
s = open(F, encoding="utf-8", newline="").read()
if "def chapitre_path(" in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"
shutil.copy2(F, F + ".bak-085")


def rep(a, b):
    global s
    a, b = a.replace("\n", NL), b.replace("\n", NL)
    assert s.count(a) == 1, (s.count(a), a[:80])
    s = s.replace(a, b)


rep('VERSION = "0.8.5"', 'VERSION = "0.8.6"  # 0.8.6 (28/09) : page dans l\'adresse (/p/N/, /page/N/) != chapitre suivant ;')

rep('''def enchainement_possible(url: str):''', '''RE_PAGE_FINALE = re.compile(r"/(?:p|page|pg)[-/]\\d+/?$", re.I)   # 0.8.6 : « .../p/3/ », « .../page/3 », « .../page-3/ »


def chapitre_path(u: str) -> str:
    """Chemin reduit a l'identifiant de CHAPITRE (sans le numero de PAGE final). 0.8.6 : sorti de capture() pour etre teste.
    1. « /p/N/ », « /page/N/ », « /page-N/ » en fin d'adresse = une PAGE (lecteurs qui changent l'adresse au defilement).
    2. MangaDex : /chapter/<uuid 36>/<n> -- ne retirer le segment numerique final QUE s'il suit un segment long non
       numerique (UUID), sinon /viewer/1000233 (MANGA Plus) perdrait son identifiant (bug 18:13 du 21/09)."""
    u = (u or "").split("?")[0].split("#")[0]
    m = RE_PAGE_FINALE.search(u)
    if m:
        return u[:m.start()]
    base, _, dernier = u.rpartition("/")
    if dernier.isdigit():
        av = base.rpartition("/")[2]
        if len(av) >= 20 and not av.isdigit():
            return base
    return u


def enchainement_possible(url: str):''')

rep('''            def _chapitre_path(u: str) -> str:
                """Path réduit à l'identifiant de CHAPITRE (sans le numéro de PAGE final).
                MangaDex : /chapter/<uuid 36>/<n>. ⚠ ne retirer le segment numérique final
                QUE s'il est précédé d'un segment long non numérique (UUID) — sinon
                /viewer/1000233 (MANGA Plus) perdrait son identifiant de chapitre.
                (bug 18:13 : départ page 4 → passage en page 5 lu comme « chapitre
                suivant » → arrêt après 4 pages au lieu de finir le chapitre.)"""
                base, _, dernier = u.rpartition("/")
                if dernier.isdigit():
                    av = base.rpartition("/")[2]
                    if len(av) >= 20 and not av.isdigit():
                        return base
                return u
''', '''            _chapitre_path = chapitre_path                # 0.8.6 : regle au niveau du module (MangaDex + /p/N/)
''')

open(F, "w", encoding="utf-8", newline="").write(s)
print("ok 0.8.6")
