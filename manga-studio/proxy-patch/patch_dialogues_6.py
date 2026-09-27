# -*- coding: utf-8 -*-
"""Manga Studio v2.82.0 -- mode Dialogues, 6e patch serveur (27/09) :
- D10 (maquette_dialogues_serie_v1 validee par Quang 02h28) : le resume de la bibliotheque dit, par chapitre, s'il a des
  DIALOGUES (« dlg ») -> bouton 🎭 de la fiche serie + badge 🎭 de la liste ;
- R1-bis (Quang 02h35 : « des pages ont ete sautees ») : /manga/dialogues rend « fichiers » (pages du manifeste, dans l'ordre)
  pour que le lecteur montre aussi les pages SANS replique de la portee.
Suppose patch_dialogues_5.py. Rejouable : python patch_dialogues_6.py <chemin du proxy>"""
import io, sys

P = sys.argv[1]
s = io.open(P, encoding="utf-8", newline="").read()
if "def _trad_etat(" not in s:
    print("ERREUR : appliquer d'abord patch_dialogues_5.py"); sys.exit(1)
if 'it["dlg"] =' in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"


def ajouter_apres(ancre, ligne):
    global s
    assert s.count(ancre) == 1, ("ancre", s.count(ancre), ancre[:70])
    s = s.replace(ancre, ancre + NL + ligne)


ajouter_apres('            it["prec"] = os.path.isfile(os.path.join(cd, "precedemment", "ouverture.json"))',
              '            it["dlg"] = os.path.isfile(os.path.join(cd, "dialogues", "dialogues.json"))          # v2.82.0 (D10)')
ajouter_apres('            "vf": not _te and (_dlg_lire(os.path.join(base, "langue.json")) or {}).get("langue") == "fr",',
              '            "fichiers": [x.get("file") for x in ((_dlg_lire(os.path.join(base, "manifest.json")) or {}).get("pages") or [])],   # v2.82.0 (R1-bis)')
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("proxy patche (6)")
