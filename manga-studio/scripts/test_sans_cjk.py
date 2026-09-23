# -*- coding: utf-8 -*-
"""Banc N2 (narrate_chapter v2.1.0) : aucun caractere japonais/chinois/coreen ne va a la voix. 0 appel payant.
1. phrases types -> texte attendu ; 2. AUCUNE narration existante de la bibliotheque n'est modifiee ;
3. mutation : un garde-fou faux doit faire echouer le banc. Usage (venv kohya) : python test_sans_cjk.py
"""
import glob, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import narrate_chapter as nc

CAS = [("Saitô (研修医) arrive enfin à l'hôpital.", "Saitô arrive enfin à l'hôpital."),
       ("Devant la plaque « 宿直室 », il hésite.", "Devant la plaque, il hésite."),
       ("Le docteur 斉藤英二郎, épuisé, s'effondre.", "Le docteur, épuisé, s'effondre."),
       ("Il crie ガガガ ! puis se tait.", "Il crie ! puis se tait."),
       ("Aucun caractère ici, rien ne change.", "Aucun caractère ici, rien ne change."),
       ("Hé, 나 혼자만 레벨업 est un titre coréen.", "Hé, est un titre coréen.")]


def verifier():
    return [(a, nc.sans_cjk(a)[0]) for a, b in CAS if nc.sans_cjk(a)[0] != b]


ko = verifier()
print(("[OK] " if not ko else "[KO] ") + "phrases types : %d/%d" % (len(CAS) - len(ko), len(CAS)), ko[:2])
ch = tot = 0
for f in glob.glob(os.path.join(HERE, "..", "sources", "*", "ch_*", "narration", "*", "narration.json")):
    for p in json.load(open(f, encoding="utf-8")).get("pages", []):
        t = (p.get("narration") or "").strip(); tot += 1; ch += nc.sans_cjk(t)[0] != t
print(("[OK] " if ch == 0 else "[KO] ") + "narrations existantes inchangees : %d modifiee(s) sur %d pages" % (ch, tot))
vrai = nc._RE_CJK; nc._RE_CJK = r"[a]"
mut = len(verifier()); nc._RE_CJK = vrai
print(("[OK] " if mut else "[KO] ") + "mutation (garde-fou faux) : %d cas en echec" % mut)
sys.exit(0 if not ko and ch == 0 and mut else 1)
