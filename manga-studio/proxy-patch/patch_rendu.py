# -*- coding: utf-8 -*-
"""Patch du proxy 8190 : libelle de la « version du rendu » (video_chapitre v1.97.0, 23/09/2026).
Quand RENDU est monte dans video_chapitre.py, la liste des videos dit « le moteur video a ete ameliore » au lieu
de la cle brute « moteur ». Rejouable : python patch_rendu.py <chemin du proxy>.
"""
import sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if '"moteur": "le moteur vidéo a été amélioré"' in s:
    print("deja patche"); sys.exit(0)
a = '''              "precedemment": "le « Précédemment… » a été refait"}                     # v1.95.1'''
if s.count(a) != 1:
    raise SystemExit("ancre introuvable (%d)" % s.count(a))
s = s.replace(a, '''              "precedemment": "le « Précédemment… » a été refait",                     # v1.95.1
              "moteur": "le moteur vidéo a été amélioré"}                                # v2.5.4 : version du rendu''')
open(p, "w", encoding="utf-8").write(s)
print("patche")
