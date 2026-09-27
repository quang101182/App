# -*- coding: utf-8 -*-
"""Manga Studio R13 (27/09) -- serveur : une page de traduction jamais LUE par le modele n'est pas « traduite ».
_trad_etat() ne compte que les pages lues -- MEME regle que traduire_chapitre.page_lue (2.2.0) et dialogues.py (1.12.0) :
« lue » si present, sinon (fichier d'avant 2.2.0) au moins une bulle. Avant 2.2.0, une page sans zone detectee n'etait
jamais envoyee au modele et restait en VO, enregistree « traduite » (27/09 : 15 pages sur 29 d'un webtoon). Consequence
dans l'app : ces pages ressortent « à traduire », et « 🌐 Traduire puis préparer » les refait -- sans rien corriger a la main.
Rend aussi « non_lues ». Rejouable : python patch_trad_lues.py <proxy>"""
import io, sys

P = sys.argv[1]
s = io.open(P, encoding="utf-8", newline="").read()
if "def _trad_page_lue(" in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", NL), b.replace("\n", NL)
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


rep('''def _trad_etat(td):''', '''def _trad_page_lue(x):
    """R13 (27/09) : MEME regle que traduire_chapitre.page_lue."""
    return bool(x.get("lue")) if "lue" in x else bool(x.get("bulles"))


def _trad_etat(td):''')
rep('''    pages = sorted(x["page"] for x in t.get("pages") or [])
    e = {"complete": bool(t.get("complete", True)), "pages": pages, "total": t.get("pages_chapitre") or len(pages),''',
    '''    pages = sorted(x["page"] for x in t.get("pages") or [] if _trad_page_lue(x))          # R13 : LUES seulement
    _tot = t.get("pages_chapitre") or len(t.get("pages") or [])
    e = {"complete": bool(t.get("complete", True)) and len(pages) >= _tot, "pages": pages, "total": _tot,
         "non_lues": sorted(x["page"] for x in t.get("pages") or [] if not _trad_page_lue(x)),''')
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
