# -*- coding: utf-8 -*-
"""Manga Studio v3.5.9 (S17, Quang 28/09 : ignorer les petits cris DES la detection) : /manga/dialogues_bulles transmet, pour une
page en detection seule, le texte LU sur la page par dialogues.py detecter (champ « lu », RapidOCR local) -- l'app y applique
la regle des petits cris (avant : texte vide -> impossible de juger avant la traduction). Rejouable."""
import io, sys

P = sys.argv[1]
s = io.open(P, encoding="utf-8", newline="").read()
if '"texte": (x.get("lu") or "").strip()}' in s:
    print("deja applique"); sys.exit(0)
a = '''bl = [{"id": x["id"], "box": x["box"], "type": "dialogue", "texte": ""} for x in det[str(n)].get("bulles") or []]'''
b = '''bl = [{"id": x["id"], "box": x["box"], "type": "dialogue", "texte": (x.get("lu") or "").strip()} for x in det[str(n)].get("bulles") or []]'''
if s.count(a) != 1:
    raise SystemExit("ancre introuvable ou multiple (%d)" % s.count(a))
s = s.replace(a, b)
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
