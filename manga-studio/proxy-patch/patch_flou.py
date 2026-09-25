# -*- coding: utf-8 -*-
"""Patch du proxy : POST /manga/reglages transmet aussi « flou_discretion » (Manga Studio v2.51.0, 25/09/2026).

Le flou de la secondaire hors de la fenetre devient OPTIONNEL (Quang 25/09 11h19), reglage persistant par application
(reglages 1.3.0). Sans ce patch, la route ne transmet que mode + relais_moderation -> l'interrupteur serait ignore en silence
(meme piege que le relais, v2.43.0). A rejouer APRES patch_relais.py. Usage : python patch_flou.py <chemin du proxy>.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8", newline="").read()
A = 'manga_reglages({k: data[k] for k in ("mode", "relais_moderation") if k in data}))   # v2.43.0'
B = 'manga_reglages({k: data[k] for k in ("mode", "relais_moderation", "flou_discretion") if k in data}))   # v2.43.0 ; v2.51.0'
if B in s:
    print("deja patche"); sys.exit(0)
if s.count(A) != 1:
    raise SystemExit("ancre introuvable ou multiple (%d) -- patch_relais.py d'abord ?" % s.count(A))
open(p, "w", encoding="utf-8", newline="").write(s.replace(A, B))
print("ok")
