# -*- coding: utf-8 -*-
"""Manga Studio v2.94.0 (R24) -- serveur : POST /manga/reglages accepte aussi « voix_favorites » (voix PREFEREES de l'instance,
validees par scripts/reglages.py 1.6.0, recharge a chaud). Suppose patch_reglages_defauts.py.
Rejouable : python patch_reglages_favorites.py <proxy>"""
import io, sys

P = sys.argv[1]
s = io.open(P, encoding="utf-8", newline="").read()
if '"defauts", "voix_favorites")' in s:
    print("deja applique"); sys.exit(0)
a = '''for k in ("mode", "relais_moderation", "flou_discretion", "defauts") if k in data}'''
b = '''for k in ("mode", "relais_moderation", "flou_discretion", "defauts", "voix_favorites") if k in data}'''
if s.count(a) != 1:
    raise SystemExit("ancre introuvable ou multiple (%d)" % s.count(a))
s = s.replace(a, b)
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
