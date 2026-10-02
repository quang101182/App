# -*- coding: utf-8 -*-
"""Banc narrate_chapter.py 2.14.0 (02/10/2026) : un relais renvoie « faits » en LISTE -> la narration plantait dans
latiniser APRES l'analyse payee, et vision.json (la sauvegarde de cette analyse) n'etait ecrit qu'APRES. Gratuit.
T1 normaliser_vis : liste, liste imbriquee, objet, None -> textes ; presents -> liste de textes
T2 l'analyse du 02/10 (page en liste) passe latiniser sans planter (sans mot CJK : aucun appel reseau)
T3 dans main, vision.json est ecrit AVANT l'appel a latiniser
Usage : python test_narration_types.py [--fichier narrate_chapter.py]"""
import importlib.util, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
a = sys.argv[1:]
F = a[a.index("--fichier") + 1] if "--fichier" in a else os.path.join(HERE, "narrate_chapter.py")
sys.path.insert(0, HERE)
spec = importlib.util.spec_from_file_location("nc_banc", F)
nc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nc)
OK, KO = [], []


def check(nom, cond, d=""):
    (OK if cond else KO).append(nom); print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(d)[:160] if d else ""), flush=True)


norm = getattr(nc, "normaliser_vis", None)
vis = [{"page": 54, "faits": "Aikawa parle.", "presents": ["Aikawa"], "narration": ""},
       {"page": 55, "faits": ["Nozomi entre.", "Yano la regarde."], "presents": "Nozomi", "narration": ["a", ["b"]]},
       {"page": 56, "faits": {"action": "Ils sortent."}, "presents": ["Yano", None, 3], "narration": None},
       {"page": 57, "faits": None, "presents": []}]
if norm is None:
    check("T1 normaliser_vis existe", False, "absente")
else:
    v = norm([dict(x) for x in vis])
    check("T1 faits = textes", [x["faits"] for x in v] == ["Aikawa parle.", "Nozomi entre. Yano la regarde.", "Ils sortent.", ""], [x["faits"] for x in v])
    check("T1 narration = textes", [x.get("narration") for x in v] == ["", "a b", "", None], [x.get("narration") for x in v])
    check("T1 presents = listes de textes", [x["presents"] for x in v] == [["Aikawa"], ["Nozomi"], ["Yano", "3"], []], [x["presents"] for x in v])
try:
    w = norm([dict(x) for x in vis]) if norm else [dict(x) for x in vis]
    nc.latiniser(w, "resume", [], {}, "titre", {})
    check("T2 une page en liste ne fait plus planter la suite", True)
except TypeError as e:
    check("T2 une page en liste ne fait plus planter la suite", False, e)
src = open(F, encoding="utf-8").read()
m = src[src.index("def main("):]
i_vis = m.find('"vision.json"), "w"')
i_lat = m.find("latiniser(vis,")
check("T3 vision.json ecrit AVANT latiniser", 0 <= i_vis < i_lat, (i_vis, i_lat))
print("\nVERDICT : %d/%d" % (len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
