# -*- coding: utf-8 -*-
"""Manga Studio v2.82.1 -- mode Dialogues, 7e patch serveur (R3-bis, Quang 27/09 03h08 : « plusieurs videos sur un meme
chapitre, pages 5 a 10 et 35 a 42 ? ») : /manga/dialogues_lancer transmet la PORTEE aussi a l'action « video »
(dialogues.py >= 1.10.0 : une video par portee, dialogues_p5-10.mp4). Suppose patch_dialogues_6.py.
Rejouable : python patch_dialogues_7.py <chemin du proxy>"""
import io, sys

P = sys.argv[1]
s = io.open(P, encoding="utf-8", newline="").read()
if 'it["dlg"] =' not in s:
    print("ERREUR : appliquer d'abord patch_dialogues_6.py"); sys.exit(1)
a = '''(["--pages", pages] if pages and action != "video" else [])'''
b = '''(["--pages", pages] if pages else [])'''
if a not in s and b in s:
    print("deja applique"); sys.exit(0)
assert s.count(a) == 1, ("ancre", s.count(a))
s = s.replace(a, b)
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("proxy patche (7)")
