# -*- coding: utf-8 -*-
"""Manga Studio v3.5.8 (S16, Quang 28/09 17h58 : « les petits gimmicks de gemissement […] ne servent a rien […] un switch
on/off ») : POST /manga/reglages accepte « petits_cris » (vrai = lus, faux = mis de cote ; reglages.py 1.7.0, par instance).
Sans ce patch, la cle etait filtree EN SILENCE par la liste blanche de la route. Rejouable."""
import io, sys

P = sys.argv[1]
s = io.open(P, encoding="utf-8", newline="").read()
if '"voix_favorites", "petits_cris")' in s:
    print("deja applique"); sys.exit(0)
a = '''for k in ("mode", "relais_moderation", "flou_discretion", "defauts", "voix_favorites") if k in data}))'''
b = '''for k in ("mode", "relais_moderation", "flou_discretion", "defauts", "voix_favorites", "petits_cris") if k in data}))'''
if s.count(a) != 1:
    raise SystemExit("ancre introuvable ou multiple (%d)" % s.count(a))
s = s.replace(a, b)
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
