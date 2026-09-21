# -*- coding: utf-8 -*-
"""Patch du proxy 8190 : une narration SUPPRIMEE reste comptee dans les couts (Manga Studio v1.79.0, 21/09).

Constat de Quang (23h24) : la pastille est passee de 8,48 $ a 7,51 $ apres la suppression d'une narration
(k3-noms-v3-a, 0,96 $). manga_costs() ne lisait que les narrations presentes : supprimer effacait la
DEPENSE, alors que l'argent est parti. On lit aussi sources/_corbeille/ (narration.json + fidelite.json).
Rejouable : python patch_couts_corbeille.py <chemin du proxy>. Suppose patch_bibliotheque.py applique.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "(supprimee)" in s:
    print("deja patche")
    sys.exit(0)
a = '''    # anciens runs --reuse-vision (avant le marqueur v1.72) : meme lecture qu'un run PLUS ANCIEN du chapitre'''
if s.count(a) != 1:
    raise SystemExit("ancre introuvable (%d)" % s.count(a))
s = s.replace(a, '''    # v1.79.0 : les narrations mises a la CORBEILLE restent des depenses (l'argent est parti)
    corb = os.path.join(racine, "_corbeille")
    for dp, _dirs, fichiers in (os.walk(corb) if os.path.isdir(corb) else []):
        rel = os.path.relpath(dp, corb).replace("\\\\", "/")
        tag = os.path.basename(dp).split("__")[-1] + " (supprimee)"
        if "narration.json" in fichiers:
            try:
                with open(os.path.join(dp, "narration.json"), encoding="utf-8") as f: n = json.load(f)
                runs.append({"chap": n.get("chapitre") or ("corbeille/" + rel), "tag": tag, "engine": n.get("engine") or "?",
                             "date": (n.get("created_at") or time.strftime("%Y-%m-%dT%H:%M:%S",
                             time.localtime(os.path.getmtime(os.path.join(dp, "narration.json")))))[:19],
                             "prompt": n.get("prompt"), "reuse": n.get("reuse_vision"), "st": n.get("stats") or {}})
            except Exception:
                pass
        if "fidelite.json" in fichiers:
            try:
                with open(os.path.join(dp, "fidelite.json"), encoding="utf-8") as f: fj = json.load(f)
                runs.append({"chap": "corbeille/" + rel, "tag": tag + " (banc)", "engine": "juge",
                             "date": (fj.get("date") or "")[:19], "prompt": "juge", "reuse": None,
                             "st": {"cout_juge": (fj.get("bilan") or {}).get("cout", 0)}})
            except Exception:
                pass
''' + a)
open(p, "w", encoding="utf-8").write(s)
print("patch couts corbeille OK")
