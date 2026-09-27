# -*- coding: utf-8 -*-
"""Manga Studio v2.82.2 -- mode Dialogues, 8e patch serveur (D12 -- Quang 27/09 02h26 « un meme homme nomme 4 fois » et 02h28
« que la solution devienne de plus en plus fiable dans la globalite ») : /manga/dialogues_distribution accepte
  « fusionner » : {garder: A, avec: [B, …]} -- DEMANDE par Quang (bouton de l'app) : B… deviennent des alias de A, disparaissent
                  de la distribution, et les repliques de TOUS les chapitres suivent (meme mecanisme que « renommer ») ;
  « pas_doublon » : [A, B, …] -- ne plus proposer ce groupe (dialogues.py >= 1.11.0 lit « pas_doublons »).
Le groupe traite est retire de « doublons ». Suppose patch_dialogues_7.py. Rejouable : python patch_dialogues_8.py <proxy>"""
import io, sys

P = sys.argv[1]
s = io.open(P, encoding="utf-8", newline="").read()
if '(["--pages", pages] if pages else [])' not in s:
    print("ERREUR : appliquer d'abord patch_dialogues_7.py"); sys.exit(1)
if 'data.get("fusionner")' in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"
a = '''    if "tons" in data:
        doc["tons"] = bool(data["tons"])
    _dlg_ecrire(f, doc)'''.replace("\n", NL)
b = '''    if "tons" in data:
        doc["tons"] = bool(data["tons"])
    fu = data.get("fusionner") if isinstance(data.get("fusionner"), dict) else {}   # v2.82.2 (D12) : fusion DEMANDEE par Quang
    garde = persos.get(str(fu.get("garder") or ""))
    fondus = set()
    if garde:
        for nom in [str(x) for x in (fu.get("avec") or [])][:10]:
            bb = persos.get(nom)
            if not bb or bb is garde:
                continue
            garde["alias"] = list(dict.fromkeys((garde.get("alias") or []) + [bb["nom"]] + (bb.get("alias") or [])))
            doc["persos"] = [p for p in doc["persos"] if p is not bb]
            renommes[bb["nom"]] = garde["nom"]
            fondus.add(bb["nom"])
    pas = [str(x) for x in (data.get("pas_doublon") or [])][:10] if isinstance(data.get("pas_doublon"), list) else []
    if len(pas) >= 2:
        doc.setdefault("pas_doublons", []).append(sorted(pas))
    if fondus or pas:
        tous = fondus | set(pas)
        doc["doublons"] = [g for g in doc.get("doublons") or [] if not (({g.get("garder")} | set(g.get("avec") or [])) & tous)]
    _dlg_ecrire(f, doc)'''.replace("\n", NL)
assert s.count(a) == 1, ("ancre", s.count(a))
s = s.replace(a, b)
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("proxy patche (8)")
