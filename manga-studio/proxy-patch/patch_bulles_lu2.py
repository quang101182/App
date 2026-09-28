# -*- coding: utf-8 -*-
"""Manga Studio v3.5.9 (S17, complement de patch_bulles_lu) : /manga/dialogues_bulles signale (« lu »: false) une page DETECTEE
AVANT que la detection lise le texte (detection.json sans champ « lu ») -> l'app relance la detection (gratuite, memes zones et
memes numeros : la verification de Quang reste valable). Page traduite ou jamais detectee : « lu »: null. Rejouable.
Prerequis : patch_bulles_lu.py."""
import io, sys

P = sys.argv[1]
s = io.open(P, encoding="utf-8", newline="").read()
if '"lu": lu_ok' in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"
if '"texte": (x.get("lu") or "").strip()}' not in s:
    raise SystemExit("appliquer d'abord patch_bulles_lu.py")


def rep(a, b):
    global s
    a, b = a.replace("\n", NL), b.replace("\n", NL)
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %s" % (s.count(a), a[:70]))
    s = s.replace(a, b)


rep('''        p = trp.get(n)
        if p is not None and p.get("bulles") is not None:''', '''        p, lu_ok = trp.get(n), None
        if p is not None and p.get("bulles") is not None:''')
rep('''            src, img = "detection", man[n - 1]''', '''            src, img = "detection", man[n - 1]
            lu_ok = all("lu" in x for x in det[str(n)].get("bulles") or [])''')
rep('''"bulles": sorted(bl, key=lambda x: x["id"]), "verif": verif.get(str(n))})''',
    '''"bulles": sorted(bl, key=lambda x: x["id"]), "verif": verif.get(str(n)), "lu": lu_ok})''')
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
