# -*- coding: utf-8 -*-
"""Manga Studio v2.89.0 (R18) -- serveur : POST /manga/reglages accepte aussi « defauts » (valeurs par defaut de l'instance,
validees et FUSIONNEES par scripts/reglages.py 1.4.0, recharge a chaud). Rejouable : python patch_reglages_defauts.py <proxy>"""
import io, sys

P = sys.argv[1]
s = io.open(P, encoding="utf-8", newline="").read()
if '"flou_discretion", "defauts")' in s:
    print("deja applique"); sys.exit(0)
a = '''for k in ("mode", "relais_moderation", "flou_discretion") if k in data}'''
b = '''for k in ("mode", "relais_moderation", "flou_discretion", "defauts") if k in data}'''
if s.count(a) != 1:
    raise SystemExit("ancre introuvable ou multiple (%d)" % s.count(a))
s = s.replace(a, b)
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
