# -*- coding: utf-8 -*-
"""Manga Studio v2.81.2 -- mode Dialogues, 4e patch serveur (Quang 27/09 00h47 : Solo Leveling, deja en francais, refuse avec
« traduis d'abord ce chapitre en francais »). Un chapitre capture en FRANCAIS D'ORIGINE (langue.json : langue fr) est pret pour
les Dialogues sans traduction : dialogues.py >= 1.6.0 y detecte les bulles et Gemini lit leur texte.
Suppose patch_dialogues.py. Rejouable : python patch_dialogues_4.py <chemin du proxy>"""
import io, sys

P = sys.argv[1]
s = io.open(P, encoding="utf-8", newline="").read()
if "MANGA_DIALOGUES =" not in s:
    print("ERREUR : appliquer d'abord patch_dialogues.py"); sys.exit(1)
if "def _dlg_francais(" in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", NL), b.replace("\n", NL)
    assert s.count(a) == 1, ("ancre", s.count(a), a[:80])
    s = s.replace(a, b)


rep('''def _dlg_vivant(d):''', '''def _dlg_francais(base):
    """Traduction francaise presente, OU chapitre capture directement en francais (langue.json de l'app)."""
    if os.path.isfile(os.path.join(base, "traduction", "fr", "traduction.json")):
        return True
    return ((_dlg_lire(os.path.join(base, "langue.json")) or {}).get("langue") == "fr")


def _dlg_vivant(d):''')
rep('''    return {"d": d, "traduit": os.path.isfile(os.path.join(base, "traduction", "fr", "traduction.json")),''',
    '''    return {"d": d, "traduit": _dlg_francais(base),''')
rep('''    if action == "preparer" and not os.path.isfile(os.path.join(base, "traduction", "fr", "traduction.json")):''',
    '''    if action == "preparer" and not _dlg_francais(base):''')
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("proxy patche (4)")
