# -*- coding: utf-8 -*-
"""Manga Studio v2.6.1 (23/09/2026) : la ligne « pas encore de pochette » quitte la carte de serie.
Quang (13h43) : elle ajoutait une ligne et cassait l'homogeneite des cartes. L'image le montre deja (une page du chapitre
en attendant) ; l'info reste au survol de l'image, et les boutons de pochette restent dans la barre de la serie.
Rejouable : python app_patch_261_sans_ligne_pochette.py <manga_studio.html>.
"""
import sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "v2.6.1 : pochette au survol" in s:
    print("deja patche"); sys.exit(0)


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


for a in ("<title>Manga Studio v2.6.0</title>", 'id="verBadge">v2.6.0</span>', 'const VERSION = "2.6.0";'):
    rep(a, a.replace("2.6.0", "2.6.1"))
rep("""      + (s.pochette ? "" : '<small class="muted">pas encore de pochette</small>')\n""", "")
rep("""                                                  : srcURL(s.cover)) + '" alt="">'""",
    """                                                  : srcURL(s.cover)) + '" alt=""' + (s.pochette ? "" : ' title="pas encore de pochette : une page du chapitre en attendant"') + '>'   // v2.6.1 : pochette au survol""")
open(p, "w", encoding="utf-8").write(s)
print("patche")
