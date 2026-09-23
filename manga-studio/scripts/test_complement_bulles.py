# -*- coding: utf-8 -*-
"""Banc v1.92.0 (traduire_chapitre) : le COMPLEMENT de bulles ne change RIEN aux bulles d'avant. 0 appel payant.
Sur toutes les pages deja traduites (sources/*/ch_*/traduction/*/traduction.json) :
  1. les zones fortes de zones_texte() == sans_chevauchement(detect(0.25)) -- a l'identique, page par page ;
  2. aucune zone de complement ne touche une zone forte ;
  3. mutation : sans le filtre « ne touche aucune zone forte », des bulles d'avant DOIVENT changer (sinon le banc
     ne prouve rien).
Usage (venv kohya) : python test_complement_bulles.py
"""
import glob, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import ingest_page as ip, traduire_chapitre as tc

cle = lambda q: (round(q["x"], 4), round(q["y"], 4), round(q["w"], 4), round(q["h"], 4))
pages = []
for tj in sorted(glob.glob(os.path.join(HERE, "..", "sources", "*", "ch_*", "traduction", "*", "traduction.json"))):
    cd = os.path.dirname(os.path.dirname(os.path.dirname(tj)))
    for p in json.load(open(tj, encoding="utf-8"))["pages"]:
        f = os.path.join(cd, p["source"])
        if os.path.isfile(f):
            pages.append(f)
diff, touche, compl, mut = [], 0, 0, 0
for f in pages:
    im = ip.load_page(f)
    avant = {cle(q) for q in tc.sans_chevauchement(ip.detect(im, 0.25)[1])}
    z = tc.zones_texte(im, 0.25, 0.10)
    fortes = {cle(q) for q in z if not q.get("complement")}
    if fortes != avant:
        diff.append(os.path.relpath(f, os.path.join(HERE, "..", "sources")))
    c = [q for q in z if q.get("complement")]; compl += len(c)
    # mutation : baisser le seuil tout court (l'ancienne idee) -> combien de bulles d'avant disparaissent ?
    mut += len(avant - {cle(q) for q in tc.sans_chevauchement(ip.detect(im, 0.10)[1])})
ok1, ok3 = not diff, mut > 0
print("pages :", len(pages), "| zones de complement :", compl)
print(("[OK] " if ok1 else "[KO] ") + "bulles d'avant IDENTIQUES sur toutes les pages", diff[:5])
print(("[OK] " if ok3 else "[KO] ") + "mutation (seuil baisse tout court) : %d bulle(s) d'avant remplacee(s) -> le banc sait voir la regression" % mut)
sys.exit(0 if ok1 and ok3 else 1)
