# -*- coding: utf-8 -*-
"""Patch du proxy 8190 : titres alternatifs des series (Manga Studio v1.81.0, 21/09/2026).

Pour la recherche intelligente : « Frieren » doit trouver « Sousou no Frieren », « Lord of Destruction »
doit trouver « Hakaiou Noritaka ». MangaDex les donne deja (attributes.altTitles) dans la reponse que
manga_serie_infos recoit : on les garde dans serie.json (30 au plus, toutes langues).
Rejouable : python patch_titres_alt.py <chemin du proxy>. Suppose patch_tomes.py applique.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if '"titres_alt":' in s:
    print("deja patche")
    sys.exit(0)
a = '''    info = {"mangadex_id": mid, "titre_mangadex": titre_mdx, "annee_debut": ma.get("year"), "annee_fin": fin,'''
if s.count(a) != 1:
    raise SystemExit("ancre introuvable (%d) : patch_tomes.py applique ?" % s.count(a))
s = s.replace(a, '''    alt = []
    for x in [ma.get("title") or {}] + list(ma.get("altTitles") or []):
        for t in x.values():
            if t and t not in alt:
                alt.append(t)
    info = {"mangadex_id": mid, "titre_mangadex": titre_mdx, "titres_alt": alt[:30],
            "annee_debut": ma.get("year"), "annee_fin": fin,''')
open(p, "w", encoding="utf-8").write(s)
print("patch titres alt OK")
