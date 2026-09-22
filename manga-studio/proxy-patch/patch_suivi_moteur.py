# -*- coding: utf-8 -*-
"""Patch du proxy 8190 : le SUIVI choisit son moteur (Manga Studio v2.0.0, 22/09/2026).
Quang (10h36) : « faire les tests avec celui qui coute le moins cher et le plus rapide [...] quand c'est debogue, passer sur
Kimi ». suivi.json « moteur » : kimi (defaut, le plus fiable) | gemini (rapide, ~1 $ et ~15 min pour 62 p.) ; l'estimation
de la file suit le moteur. Rejouable : python patch_suivi_moteur.py <chemin du proxy>. Suppose patch_suivi.py applique.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "_SUIVI_TARIF" in s:
    print("deja patche")
    sys.exit(0)


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


rep('''    cfg = {"actif": bool(data.get("actif")), "voix": voix, "moteur": "kimi", "karaoke": bool(data.get("karaoke", True)),''',
    '''    cfg = {"actif": bool(data.get("actif")), "voix": voix, "moteur": data.get("moteur") if data.get("moteur") in _SUIVI_TARIF else "kimi",
           "karaoke": bool(data.get("karaoke", True)),''')
rep('''    return {"config": cfg, "file": file, "estimation": {"cout": round(pages * 0.04, 2), "minutes": pages},''',
    '''    prix, minutes = _SUIVI_TARIF.get(cfg.get("moteur") or "kimi", _SUIVI_TARIF["kimi"])
    return {"config": cfg, "file": file, "estimation": {"cout": round(pages * prix, 2), "minutes": round(pages * minutes)},''')
rep('''def manga_suivi(serie):''',
    '''_SUIVI_TARIF = {"kimi": (0.04, 1.0), "gemini": (0.017, 0.25)}     # $ et minutes par page (mesures du 21/09)


def manga_suivi(serie):''')
open(p, "w", encoding="utf-8").write(s)
print("patch suivi moteur OK")
