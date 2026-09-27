# -*- coding: utf-8 -*-
"""Manga Studio v2.87.0 -- mode Dialogues, 9e patch serveur (R17, Quang 27/09 13h09-13h10 : « a chaque fois que je change la
vitesse d'une voix, je suis oblige de la regenerer ? » -> « oui » a la vitesse d'ECOUTE gratuite) : un personnage accepte
« ecoute » (0,7-1,5) = vitesse appliquee a la LECTURE et au montage de la video, jamais envoyee a ElevenLabs -> changer
d'avis ne coute aucun credit. « vitesse » (diction, a la generation) reste inchangee. Rejouable : python patch_dialogues_9.py <proxy>"""
import io, sys

P = sys.argv[1]
s = io.open(P, encoding="utf-8", newline="").read()
if 'p["ecoute"]' in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"
a = '''        if "vitesse" in m:
            p["vitesse"] = round(max(0.7, min(1.2, float(m["vitesse"]))), 2)
'''.replace("\n", NL)
b = '''        if "vitesse" in m:
            p["vitesse"] = round(max(0.7, min(1.2, float(m["vitesse"]))), 2)
        if "ecoute" in m:                                    # v2.87.0 (R17) : vitesse d'ECOUTE, gratuite (jamais envoyee a EL)
            p["ecoute"] = round(max(0.7, min(1.5, float(m["ecoute"]))), 2)
'''.replace("\n", NL)
if s.count(a) != 1:
    raise SystemExit("ancre introuvable ou multiple (%d)" % s.count(a))
s = s.replace(a, b)
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
