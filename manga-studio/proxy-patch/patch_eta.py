# -*- coding: utf-8 -*-
"""Patch du proxy 8190 : TEMPS RESTANT de chaque tache en cours (Manga Studio v1.91.0, 22/09/2026, demande Quang 05h37).

Dans /manga/activite, chaque tache porte `reste_s` : vitesse MESUREE de son etape en cours (unites faites depuis
que le proxy la voit avancer / temps ecoule), appliquee a ce qui reste. Rien d'estime a priori : tant que l'etape
n'a pas avance d'au moins 2 unites sur 20 s, pas de chiffre (mieux vaut rien qu'un temps faux).
Pour une narration, c'est le reste de l'ETAPE (reperage, lecture, recit, voix n'ont pas la meme vitesse).
Rejouable : python patch_eta.py <chemin du proxy>. Suppose patch_activite.py applique.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "_ACT_VIT" in s:
    print("deja patche")
    sys.exit(0)
a = '''    return {"items": out, "t": time.time()}'''
b = '''    maintenant = time.time()                     # v1.91.0 : temps restant, a la vitesse MESUREE de l'etape
    for it in out:
        cle = (it["type"], it.get("d"), it.get("tag") or it.get("langue"), it.get("etape"))
        fait, total = it.get("fait"), it.get("total")
        if not isinstance(fait, (int, float)) or not total:
            continue
        t0, f0 = _ACT_VIT.setdefault(cle, (maintenant, fait))
        if fait < f0:                            # l'etape a redemarre : on repart de zero
            _ACT_VIT[cle] = (maintenant, fait); continue
        if fait - f0 >= 2 and maintenant - t0 >= 20:
            it["reste_s"] = round((total - fait) * (maintenant - t0) / (fait - f0))
    return {"items": out, "t": maintenant}'''
if s.count(a) != 1:
    raise SystemExit("ancre introuvable")
s = s.replace(a, b)
a2 = '''def manga_activite():'''
if s.count(a2) != 1:
    raise SystemExit("ancre manga_activite introuvable")
s = s.replace(a2, '''_ACT_VIT = {}                                    # v1.91.0 : (tache, etape) -> (1re fois vue, unites faites alors)


def manga_activite():''')
open(p, "w", encoding="utf-8").write(s)
print("patch eta OK")
