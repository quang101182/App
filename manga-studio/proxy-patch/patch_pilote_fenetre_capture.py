# -*- coding: utf-8 -*-
"""Manga Studio (26/09/2026, Quang 15h15) : pendant une capture, /manga/pilote n'interdit plus TOUT -- les gestes de
FENETRE prouves sans danger (mesure 25/09 : 38 deplacements = aucun effet, 165 redimensionnements = aucune image perdue)
passent : fenetre_taille (agrandit seulement), fenetre_memoriser (ecrit un fichier), fenetre_etat (lecture),
fenetre_ranger (refuse par cdp_mini si la place retenue est trop petite). Fermer, onglets, clics : toujours bloques.
Rejouable : python patch_pilote_fenetre_capture.py <chemin du proxy>"""
import io, sys
P = sys.argv[1]
s = io.open(P, encoding="utf-8", newline="").read()
if "PILOTE_OK_EN_CAPTURE" in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"
a = '''    oid, action = data.get("id") or "", data.get("action") or ""
    if _FETCH["proc"] is not None and _FETCH["proc"].poll() is None:
        return {"error": "une capture est en cours : on ne touche pas a la fenetre"}'''.replace("\n", NL)
z = '''    oid, action = data.get("id") or "", data.get("action") or ""
    en_capture = _FETCH["proc"] is not None and _FETCH["proc"].poll() is None
    if en_capture and action not in PILOTE_OK_EN_CAPTURE:
        return {"error": "une capture est en cours : on ne touche pas a la fenetre"}
    if en_capture:
        data = dict(data, en_capture=True)                     # cdp_mini : « ranger » verifie la taille, « fermer » refuse'''.replace("\n", NL)
assert s.count(a) == 1, "ancre garde"
s = s.replace(a, z)
b = "def manga_pilote(data):"
assert s.count(b) == 1
s = s.replace(b, ("# 26/09/2026 : gestes de fenetre autorises PENDANT une capture (mesures 25/09, scripts/test_deplacer_fenetre.py)" + NL
                  + 'PILOTE_OK_EN_CAPTURE = ("fenetre_taille", "fenetre_memoriser", "fenetre_etat", "fenetre_ranger")' + NL + NL + NL + b))
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("proxy patche")
