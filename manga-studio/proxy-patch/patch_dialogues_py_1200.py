# -*- coding: utf-8 -*-
"""dialogues.py 1.19.0 -> 1.20.0 (27/09, Quang 17h43 : « j'ai retravaille les bulles, mais a aucun moment ca ne me propose de
refaire la preparation, les voix et la video »). Refaire la preparation d'une plage RETIRE les repliques des pages traitees
qui ne sont plus produites (bulle exclue, disparue) : avant, l'ancienne replique (et sa voix) restait dans le chapitre.
Rejouable : python patch_dialogues_py_1200.py dialogues.py"""
import sys
P = sys.argv[1]
s = open(P, encoding="utf-8", newline="").read()
if 'VERSION = "1.20.0"' in s:
    print("deja applique"); sys.exit(0)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


rep('VERSION = "1.19.0"  #', 'VERSION = "1.20.0"  # 1.20.0 (27/09) : refaire une plage RETIRE les repliques qui ne sont plus produites (bulle exclue / disparue) ;  #')
rep('''    for p in pages:
        img = os.path.join(chap_dir, *p["img_rel"].split("/"))
        for b in p["_bulles"]:
            cle = "%d-%d" % (p["page"], b["id"])''',
    '''    generes = set()                                                     # 1.20.0 : ce que CETTE preparation produit
    for p in pages:
        img = os.path.join(chap_dir, *p["img_rel"].split("/"))
        for b in p["_bulles"]:
            cle = "%d-%d" % (p["page"], b["id"])
            generes.add(cle)''')
rep('''    ambiances = [r.get("ambiance") for r in reponses if r.get("ambiance")]''',
    '''    traitees = voulues & {p["page"] for p in tr["pages"]}               # 1.20.0 : pages de la plage connues de la source
    retirees = [c for c, x in par_cle.items() if x.get("page") in traitees and c not in generes]
    for c in retirees:
        par_cle.pop(c)
    if retirees:
        log("  %d replique(s) retiree(s) : bulle exclue ou plus detectee (%s)" % (len(retirees), ", ".join(sorted(retirees)[:12])))
    ambiances = [r.get("ambiance") for r in reponses if r.get("ambiance")]''')
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok 1.20.0")
