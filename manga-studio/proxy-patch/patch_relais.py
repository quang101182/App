# -*- coding: utf-8 -*-
"""Patch du proxy : POST /manga/reglages transmet aussi « relais_moderation » (Manga Studio v2.43.0, 25/09/2026).

Avant : la route ne passait que {"mode": ...} au module reglages -> l'interrupteur du relais automatique de moderation
(reglages 1.2.0) etait ignore en silence. Rejouable : python patch_relais.py <chemin du proxy>. Ancre verifiee.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
A = '''                self._json(200, manga_reglages({"mode": data.get("mode")}))'''
B = '''                self._json(200, manga_reglages({k: data[k] for k in ("mode", "relais_moderation") if k in data}))   # v2.43.0'''
if B in s:
    print("deja patche"); sys.exit(0)
if s.count(A) != 1:
    raise SystemExit("ancre introuvable ou multiple (%d)" % s.count(A))
open(p, "w", encoding="utf-8").write(s.replace(A, B))
print("ok")
