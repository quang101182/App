# -*- coding: utf-8 -*-
"""Banc dialogues.py 1.28.0 (S2-bis) -- HORS LIGNE, dossier temporaire : reparation des bulles entourees en DOUBLE laissees par
<= 1.25.0. Page A : un seul ajout, doublon d'une bulle traduite -> retire + image .avant_ajouts remise (+ sauvegardes).
Page B : un doublon + un VRAI ajout -> doublon retire, vrai ajout garde, image INTACTE. Page C (hors plage) : intacte.
Rejouer = rien de plus. MUTATION : sans la reparation (dialogues.py 1.27.0) -> ROUGE.
Usage : python test_reparer_ajouts.py [--ancien chemin/dialogues.py]"""
import json, os, shutil, sys, tempfile, types

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[sys.argv.index("--ancien") + 1] if "--ancien" in sys.argv else os.path.join(HERE, "dialogues.py")
T = tempfile.mkdtemp(prefix="banc_reparer_")
os.environ.update(MANGA_SOURCES_DIR=T, MANGA_DEPENSES=os.path.join(T, "_depenses.jsonl"))
sys.path.insert(0, HERE)
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail)[:160] if detail else ""))


m = types.ModuleType("dialogues_banc"); m.__file__ = SRC
exec(compile(open(SRC, encoding="utf-8").read(), SRC, "exec"), m.__dict__)
ch = os.path.join(T, "serie", "ch_1"); fr = os.path.join(ch, "traduction", "fr"); os.makedirs(fr)
B = lambda x, y, w, h: {"x": x, "y": y, "w": w, "h": h}
tr = {"pages": [
    {"page": 1, "file": "page_001.png", "bulles": [{"id": 100, "type": "dialogue", "box": B(.59, .17, .26, .06), "trad": "C'EST TOI."},
                                                  {"id": 900, "type": "dialogue", "box": B(.38, .11, .62, .22), "trad": "C'EST TOI.", "ajout": True}]},
    {"page": 2, "file": "page_002.png", "bulles": [{"id": 1, "type": "dialogue", "box": B(.1, .1, .2, .05), "trad": "A"},
                                                  {"id": 900, "type": "dialogue", "box": B(.05, .05, .35, .15), "trad": "A", "ajout": True},
                                                  {"id": 901, "type": "dialogue", "box": B(.6, .7, .2, .1), "trad": "VRAI AJOUT", "ajout": True}]},
    {"page": 3, "file": "page_003.png", "bulles": [{"id": 1, "type": "dialogue", "box": B(.1, .1, .2, .05), "trad": "B"},
                                                  {"id": 900, "type": "dialogue", "box": B(.05, .05, .35, .15), "trad": "B", "ajout": True}]}]}
json.dump(tr, open(os.path.join(fr, "traduction.json"), "w", encoding="utf-8"), ensure_ascii=False)
for n in (1, 2, 3):
    open(os.path.join(fr, "page_%03d.png" % n), "wb").write(b"ABIMEE-%d" % n)
    open(os.path.join(fr, "page_%03d.png.avant_ajouts" % n), "wb").write(b"PROPRE-%d" % n)
lire = lambda n: open(os.path.join(fr, "page_%03d.png" % n), "rb").read()
f = getattr(m, "reparer_ajouts_doubles", None)
n = f(ch, {1, 2}) if f else 0
t2 = {p["page"]: [b["id"] for b in p["bulles"]] for p in json.load(open(os.path.join(fr, "traduction.json"), encoding="utf-8"))["pages"]}
check("A. doublon retire de la traduction (p.1 : 100 seule)", t2[1] == [100], t2[1])
check("A. image d'avant les ajouts REMISE (p.1)", lire(1) == b"PROPRE-1", lire(1))
check("A. sauvegardes .avant_reparation (image + traduction)", os.path.isfile(os.path.join(fr, "page_001.png.avant_reparation"))
      and os.path.isfile(os.path.join(fr, "traduction.json.avant_reparation")))
check("B. doublon retire, VRAI ajout garde (p.2 : 1 + 901)", t2[2] == [1, 901], t2[2])
check("B. image INTACTE (un vrai ajout y est dessine)", lire(2) == b"ABIMEE-2", lire(2))
check("C. page hors plage intacte (p.3)", t2[3] == [1, 900] and lire(3) == b"ABIMEE-3", (t2[3], lire(3)))
check("nombre retire = 2", n == 2, n)
n2 = f(ch, {1, 2}) if f else -1
check("rejouer = rien de plus", n2 == 0, n2)
shutil.rmtree(T, ignore_errors=True)
print("\nVERDICT : %d/%d" % (len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
