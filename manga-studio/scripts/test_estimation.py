# -*- coding: utf-8 -*-
"""Banc 4-undecies : la double estimation de l'APP (estimChap, JS) == celle du SERVEUR (estimation.chapitre, Python).

Sans ce banc, l'ecran et le lot pourraient annoncer deux prix differents pour la meme chose sans que personne le voie.
Extrait estimChap() de manga_studio.html, l'execute sous node sur une grille d'entrees, compare a Python.
Controles de sens en plus : le PC ne coute jamais plus cher que l'en-ligne, la carte n'est occupee qu'en 🖥,
la video est a 0 $ dans les deux modes.
Usage : python scripts/test_estimation.py [--html autre.html]   -> exit 0 si tout est vert.
"""
import itertools, json, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import estimation

html = os.path.join(HERE, "..", "manga_studio.html")
if "--html" in sys.argv:
    html = sys.argv[sys.argv.index("--html") + 1]
src = open(html, encoding="utf-8").read()
m = re.search(r"function estimChap\(n, etapes, moteur\)\{.*?\n\}\n", src, re.S)
if not m:
    print("ROUGE : estimChap introuvable dans l'app"); sys.exit(1)

et = estimation.etalonnage()
ETAPES = ["narration", "karaoke", "traduction", "precedemment", "video"]
cas = []
for n in (0, 1, 17, 24, 62):
    for moteur in ("gemini", "kimi"):
        for r in range(0, len(ETAPES) + 1):
            for combo in itertools.combinations(ETAPES, r):
                cas.append((n, list(combo), moteur))

js = "let ETAL = " + json.dumps(et) + ";\n" + m.group(0) + "\nconst CAS = " + json.dumps(cas) + ";\n" \
     "console.log(JSON.stringify(CAS.map(c => estimChap(c[0], c[1], c[2]))));\n"
with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
    f.write(js); tmp = f.name
try:
    out = subprocess.run(["node", tmp], capture_output=True, text=True, encoding="utf-8")
finally:
    os.unlink(tmp)
if out.returncode:
    print("ROUGE : node a echoue\n" + out.stderr[:800]); sys.exit(1)
res_js = json.loads(out.stdout)

ecarts, sens = [], []
for (n, etapes, moteur), j in zip(cas, res_js):
    p = estimation.chapitre(n, set(etapes), moteur, et)
    for mode, k in (("cloud", "usd"), ("cloud", "min"), ("pc", "usd"), ("pc", "min"), ("pc", "gpu_min")):
        if abs(p[mode][k] - j[mode][k]) > (0.0006 if k == "usd" else 0.06):
            ecarts.append((n, etapes, moteur, mode, k, p[mode][k], round(j[mode][k], 4)))
    if j["pc"]["usd"] > j["cloud"]["usd"] + 1e-9:
        sens.append(("PC plus cher", n, etapes, moteur))
    if etapes == ["video"] and (j["cloud"]["usd"] or j["pc"]["usd"]):
        sens.append(("video payante", n, moteur))
    if "narration" in etapes and n and not j["pc"]["gpu_min"] > 0:
        sens.append(("narration PC sans carte", n, moteur))

print("%d cas compares (app JS vs serveur Python)" % len(cas))
print("ecarts : %d · controles de sens en echec : %d" % (len(ecarts), len(sens)))
for e in (ecarts + sens)[:10]:
    print("  ", e)
ok = not ecarts and not sens
print("VERT" if ok else "ROUGE")
sys.exit(0 if ok else 1)
