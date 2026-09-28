"""manga-fetch 0.8.6 -> 0.8.7 (28/09) : enchainement GENERIQUE « meme adresse au numero pres ». Un site dont les chapitres
s'appellent « …-7/english/p/1/ » -> « …-8/english/p/1/ » n'avait ni format connu, ni liste, ni lien « chapitre suivant »
reconnaissable (« Next on Collection ») -> « enchainement impossible ». Desormais, avant le bouton « suivant » : un lien de la
page dont l'adresse (page retiree : chapitre_path) est IDENTIQUE a celle du chapitre en cours sauf UN nombre, qui passe de N a
N+1, est le chapitre suivant. Fonction pure adresse_suivante() (testable). Rejouable."""
import shutil, sys

F = "D:/Download/02-Apps-Web/Repo-github/App/manga-studio/manga-fetch/manga_fetch.py"
s = open(F, encoding="utf-8", newline="").read()
if "def adresse_suivante(" in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"
shutil.copy2(F, F + ".bak-086")


def rep(a, b):
    global s
    a, b = a.replace("\n", NL), b.replace("\n", NL)
    assert s.count(a) == 1, (s.count(a), a[:80])
    s = s.replace(a, b)


rep('VERSION = "0.8.6"  # 0.8.6 (28/09)', 'VERSION = "0.8.7"  # 0.8.7 (28/09) : enchainement « meme adresse au n° pres » ; 0.8.6 (28/09)')

rep('''def enchainement_possible(url: str):''', '''def adresse_suivante(avant: str, liens, courant) -> str:
    """0.8.7 : parmi les liens de la page, celui du chapitre SUIVANT quand les adresses ne different QUE par le numero
    (« serie-7/english/p/1/ » -> « serie-8/english/p/1/ ») : memes morceaux non numeriques, un seul nombre change, de N a N+1.
    Rend l'adresse du lien (telle quelle) ou ""."""
    try:
        n0 = int(_num(courant))
    except Exception:
        return ""
    base = re.split(r"(\\d+)", chapitre_path(avant).rstrip("/"))
    for h in liens or []:
        h = (h or "").split("#")[0]
        hb = re.split(r"(\\d+)", chapitre_path(h).rstrip("/"))
        if len(hb) != len(base) or hb == base:
            continue
        diff = [i for i in range(len(base)) if base[i] != hb[i]]
        if len(diff) == 1 and diff[0] % 2 == 1 and base[diff[0]].isdigit() and hb[diff[0]].isdigit() \\
                and int(base[diff[0]]) == n0 and int(hb[diff[0]]) == n0 + 1:
            return h
    return ""


def enchainement_possible(url: str):''')

rep('''    if not lien:
        return _suivant_par_bouton(page, avant, courant, jusqua, entiers)       # v0.7.2''',
    '''    if not lien:                                                               # 0.8.7 : meme adresse au n° pres
        lien = adresse_suivante(avant, page.evaluate("() => [...document.querySelectorAll('a[href]')].map(a => a.href)"), courant) or None
        if lien:
            log_evt("série", "chapitre suivant trouvé par l'adresse (même adresse au numéro près)", lien=lien)
    if not lien:
        return _suivant_par_bouton(page, avant, courant, jusqua, entiers)       # v0.7.2''')

open(F, "w", encoding="utf-8", newline="").write(s)
print("ok 0.8.7")
