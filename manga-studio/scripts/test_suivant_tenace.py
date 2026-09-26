# -*- coding: utf-8 -*-
"""Banc manga-fetch 0.8.4 : chapitre_suivant_tenace -- un delai depasse PASSAGER ne tue plus la serie (TBATE, 26/09 19h25).
Sans reseau : chapitre_suivant est remplace par un faux qui echoue N fois puis reussit ; fausse page (wait_for_timeout compte).
Cas : 1 timeout puis OK -> OK au 2e essai ; 3 timeouts -> l'erreur remonte (arret net, comme avant) ; erreur de LOGIQUE ->
remonte AU 1er essai (rien n'est masque) ; coupure « net::ERR_… » -> reessayee ; succes direct -> 1 seul appel, aucune pause.
Usage : python test_suivant_tenace.py [--mutation]   (--mutation : 0.8.3 -> la fonction n'existe pas -> ROUGE)
"""
import importlib.util, importlib.machinery, os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
MUT = "--mutation" in sys.argv
ICI = os.path.dirname(os.path.abspath(__file__))
src = os.path.join(ICI, "..", "manga-fetch", "manga_fetch.py.bak-20260926-v084" if MUT else "manga_fetch.py")
spec = importlib.util.spec_from_file_location("mf", src, loader=importlib.machinery.SourceFileLoader("mf", src))
mf = importlib.util.module_from_spec(spec); spec.loader.exec_module(mf)
OK, KO = [], []
def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail)[:200] if detail else ""), flush=True)
class TimeoutError_(Exception): pass
TimeoutError_.__name__ = "TimeoutError"
class Page:
    def __init__(self): self.pauses = []
    def wait_for_timeout(self, ms): self.pauses.append(ms)
def faux(echecs, exc):
    etat = {"n": 0}
    def f(page, url, courant, jusqua, entiers=False):
        etat["n"] += 1
        if etat["n"] <= echecs: raise exc
        return "3", None
    return f, etat
tenace = getattr(mf, "chapitre_suivant_tenace", None)
if tenace is None:
    check("chapitre_suivant_tenace existe (0.8.4)", False, "absente : version " + getattr(mf, "VERSION", "?"))
else:
    mf.log_evt = lambda *a, **k: None
    TO = TimeoutError_("Page.goto: Timeout 45000ms exceeded.")
    f, e = faux(1, TO); mf.chapitre_suivant = f; p = Page()
    r = tenace(p, "u", "2", 30.0)
    check("1 timeout puis OK → ch. 3 obtenu au 2e essai, 1 pause de 15 s", r == ("3", None) and e["n"] == 2 and p.pauses == [15000], (r, e["n"], p.pauses))
    f, e = faux(3, TO); mf.chapitre_suivant = f; p = Page()
    try: tenace(p, "u", "2", 30.0); leve = False
    except Exception as x: leve = "Timeout" in str(x)
    check("3 timeouts → l'erreur remonte (arrêt net, 3 essais, 2 pauses)", leve and e["n"] == 3 and len(p.pauses) == 2, (e["n"], p.pauses))
    f, e = faux(1, KeyError("slug")); mf.chapitre_suivant = f; p = Page()
    try: tenace(p, "u", "2", 30.0); leve = False
    except KeyError: leve = True
    check("erreur de LOGIQUE → remonte au 1er essai, aucune pause (rien de masqué)", leve and e["n"] == 1 and p.pauses == [], (e["n"], p.pauses))
    f, e = faux(1, RuntimeError("net::ERR_CONNECTION_RESET")); mf.chapitre_suivant = f; p = Page()
    r = tenace(p, "u", "2", 30.0)
    check("coupure « net::ERR_… » → réessayée", r == ("3", None) and e["n"] == 2, e["n"])
    f, e = faux(0, TO); mf.chapitre_suivant = f; p = Page()
    r = tenace(p, "u", "2", 30.0)
    check("succès direct → 1 seul appel, aucune pause", r == ("3", None) and e["n"] == 1 and p.pauses == [], (e["n"], p.pauses))
    check("VERSION = 0.8.4", mf.VERSION == "0.8.4", mf.VERSION)
print("\nVERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
