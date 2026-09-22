# -*- coding: utf-8 -*-
"""Banc narrate_chapter v1.99.0 : FREIN COMMUN a tous les programmes + un « 429 » ne consomme plus d'essai. 0 appel reel.
1. 3 programmes x 12 passages simultanes dans _frein() (fichier de compteur a part) : jamais plus de 18 sur 60 s glissantes,
   36 passages au total, etalement ~1 min. Mutation : sans verrou commun (_frein_local), la limite est depassee -> rouge.
2. Faux gateway qui repond 429 sept fois puis OK : post() REUSSIT (avant : echec au 5e refus). Les pauses sont court-circuitees.
Usage : python test_frein_commun.py
"""
import json, os, subprocess, sys, tempfile, time, urllib.error, io

HERE = os.path.dirname(os.path.abspath(__file__))
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


ENFANT = r'''
import sys, time, json
sys.path.insert(0, %r)
import narrate_chapter as nc
nc.FREIN_F = sys.argv[1]
nc.MAX_PAR_MIN = 18          # le MECANISME est teste a 18, quelle que soit la valeur de production
if sys.argv[3] == "local": nc._frein = nc._frein_local
t = []
for _ in range(12):
    nc._frein(); t.append(time.time())
open(sys.argv[2], "w").write(json.dumps(t))
''' % HERE


def course(mode):
    d = tempfile.mkdtemp(prefix="frein_")
    f = os.path.join(d, "frein.json")
    sc = os.path.join(d, "enfant.py"); open(sc, "w").write(ENFANT)
    t0 = time.time()
    ps = [subprocess.Popen([sys.executable, sc, f, os.path.join(d, "t%d.json" % k), mode]) for k in range(3)]
    [p.wait(timeout=200) for p in ps]
    tous = sorted(sum((json.load(open(os.path.join(d, "t%d.json" % k))) for k in range(3)), []))
    pire = max(sum(1 for u in tous if t <= u < t + 60) for t in tous)
    return tous, pire, time.time() - t0


print("=== 1. frein commun (3 programmes x 12)")
tous, pire, duree = course("commun")
check("36 passages", len(tous) == 36, len(tous))
check("jamais plus de 18 sur 60 s glissantes", pire <= 18, pire)
check("étalement ~1 min (18 tout de suite, 18 après 60 s)", 58 <= duree <= 75, round(duree, 1))
print("=== mutation : chacun son frein (l'ancien code)")
tous, pire, duree = course("local")
check("MUTATION rouge attendue : la limite est dépassée", pire > 18, pire)

print("=== 2. « 429 » sept fois puis OK")
sys.path.insert(0, HERE)
import narrate_chapter as nc
nc.SECRET = "x"; nc.FREIN_F = os.path.join(tempfile.mkdtemp(prefix="frein_"), "f.json")
nc.journal = lambda *a, **k: None
reel_sleep = time.sleep
compte = {"n": 0}


class Rep:
    def __init__(self, b): self.b = b
    def __enter__(self): return io.BytesIO(self.b)
    def __exit__(self, *a): return False


def faux(req, timeout=None):
    compte["n"] += 1
    if compte["n"] <= 7:
        raise urllib.error.HTTPError(req.full_url, 429, "Too Many", {}, io.BytesIO(b'{"retry_after": 0}'))
    return Rep(b'{"ok": true}')


nc.urllib.request.urlopen = faux
nc.time.sleep = lambda s: None
try:
    r = nc.post("/api/x", {})
    check("post() réussit après 7 refus", r == {"ok": True} and compte["n"] == 8, (r, compte["n"]))
except Exception as e:
    check("post() réussit après 7 refus", False, e)
compte["n"] = -100                                      # refuse sans fin -> doit s'arreter (15 refus + 5 essais)
try:
    nc.post("/api/x", {}); check("refus sans fin : s'arrête", False, "a rendu quelque chose")
except RuntimeError as e:
    check("refus sans fin : s'arrête avec une erreur claire", "429" in str(e), str(e)[:80])
nc.time.sleep = reel_sleep
print("\n%d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
