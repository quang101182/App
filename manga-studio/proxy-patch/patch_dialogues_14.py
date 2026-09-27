# -*- coding: utf-8 -*-
"""Manga Studio v3.3.0 -- 14e patch serveur (27/09, « ⚡ Tout faire ») : /manga/dialogues_lancer accepte action « tout »
(dialogues.py 1.21.0 : preparer -> ARRET si doute -> voix -> video) ; « traduire » vaut aussi pour « tout » ;
« sans_preparation » (preparation deja a jour) -> --sans-preparation. Suppose patch_dialogues_12. Rejouable."""
import io, sys

P = sys.argv[1]
s = io.open(P, encoding="utf-8", newline="").read()
if '"detecter", "tout"' in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", NL), b.replace("\n", NL)
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %s" % (s.count(a), a[:70]))
    s = s.replace(a, b)


rep('''def manga_dialogues_lancer(d, action, pages="", traduire=False):
    if action not in ("preparer", "voix", "video", "detecter"):''',
    '''def manga_dialogues_lancer(d, action, pages="", traduire=False, sans_prep=False):
    if action not in ("preparer", "voix", "video", "detecter", "tout"):   # v3.3.0 : « tout » (dialogues.py 1.21.0)''')
rep('''    if action == "preparer" and not _dlg_francais(base) and not (traduire and pages):''',
    '''    if action in ("preparer", "tout") and not sans_prep and not _dlg_francais(base) and not (traduire and pages):''')
rep('''    if action in ("voix", "video") and not os.path.isfile(os.path.join(dd, "dialogues.json")):''',
    '''    if (action in ("voix", "video") or (action == "tout" and sans_prep)) and not os.path.isfile(os.path.join(dd, "dialogues.json")):''')
rep('''+ (["--traduire"] if traduire and action == "preparer" else [])''',
    '''+ (["--traduire"] if traduire and action in ("preparer", "tout") else []) + (["--sans-preparation"] if sans_prep and action == "tout" else [])''')
rep('''                self._json(200, manga_dialogues_lancer(str(data.get("d") or ""), str(data.get("action") or ""),
                                                       str(data.get("pages") or ""), data.get("traduire") is True))''',
    '''                self._json(200, manga_dialogues_lancer(str(data.get("d") or ""), str(data.get("action") or ""),
                                                       str(data.get("pages") or ""), data.get("traduire") is True,
                                                       data.get("sans_preparation") is True))   # v3.3.0''')
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
