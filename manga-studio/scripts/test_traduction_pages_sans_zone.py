# -*- coding: utf-8 -*-
"""Banc R12 / R13 / R14 (27/09) : plus aucune page sautee a la traduction, une page jamais lue n'est pas « traduite », les
Dialogues lisent les textes ecartes pour l'image. Sur le chapitre webtoon de la SECONDAIRE ou le defaut a ete constate
(lecture seule : la traduction du banc part dans --sortie, en %TEMP%). Chapitre passe en argument : aucun nom ici (depot public).
Cout : un passage reel sur 3 pages (~0,013 $).
Usage : python test_traduction_pages_sans_zone.py <serie/ch_N> <p1-p2 : plage dont au moins une page sans zone detectee>
        [--script traduire_chapitre.py]        (script 2.1.0 -> ROUGE)"""
import json, os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
CH, PLAGE = sys.argv[1], sys.argv[2]
SCRIPT = sys.argv[sys.argv.index("--script") + 1] if "--script" in sys.argv else os.path.join(HERE, "traduire_chapitre.py")
os.environ.setdefault("MANGA_SOURCES_DIR", os.path.expanduser(r"~\Documents\MangaStudio-donnees\prive"))
SRC = os.environ["MANGA_SOURCES_DIR"]
PY = os.path.expanduser(r"~\Documents\ComfyUI\.venv\Scripts\python.exe")
OK, KO = [], []


def check(n, c, d=""):
    (OK if c else KO).append(n); print(("  [OK] " if c else "  [KO] ") + n + (" -- " + str(d)[:200] if d else ""), flush=True)


import traduire_chapitre as tc, ingest_page as ip, dialogues as dl
chap = os.path.join(SRC, CH)
de, a = (int(x) for x in PLAGE.split("-"))
sans_zone = [n for n in range(de, a + 1) if not tc.zones_texte(ip.load_page(os.path.join(chap, "page_%03d.jpg" % n)), 0.25, tc.CONF_COMPLEMENT)]
check("la plage contient des pages ou le detecteur ne trouve rien (%s)" % sans_zone, bool(sans_zone))
# --- R12 : passage REEL
out = tempfile.mkdtemp(prefix="trad_sans_zone_")
r = subprocess.run([PY, SCRIPT, CH, "--pages", PLAGE, "--via", "dialogues", "--sortie", out], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", env=dict(os.environ, PYTHONIOENCODING="utf-8"), timeout=600)
t = json.load(open(os.path.join(out, "traduction.json"), encoding="utf-8"))
P = {p["page"]: p for p in t["pages"]}
for n in sans_zone:
    b = [x for x in P[n]["bulles"] if (x.get("trad") or "").strip()]
    check("R12 page %d (0 zone detectee) : LUE et traduite (%d texte(s))" % (n, len(b)), P[n].get("lue") is True and b, [x.get("trad", "")[:30] for x in b])
check("R12 stats : pages_sans_zone = %d" % len(sans_zone), t["stats"].get("pages_sans_zone") == len(sans_zone), t["stats"].get("pages_sans_zone"))
# --- R15 : une grande zone d'encadre n'est plus ecartee, elle est RESSERREE sur ses lettres
trop = [(p["page"], x.get("trad", "")[:25]) for p in t["pages"] for x in p["bulles"] if (x.get("ecarte") or "").startswith("zone trop")]
check("R15 aucun texte ecarte « zone trop grande » ; %s resserre(s)" % t["stats"].get("resserres"), not trop and (t["stats"].get("resserres") or 0) >= 1, trop)
# --- R13 : la regle unique, sur la traduction REELLE du chapitre (format d'avant 2.2.0)
tr = json.load(open(os.path.join(chap, "traduction", "fr", "traduction.json"), encoding="utf-8"))
vides = sorted(p["page"] for p in tr["pages"] if not p["bulles"] and "lue" not in p)
e = tc.traduction_etat(chap)
check("R13 traduction_etat : les pages a 0 bulle d'avant 2.2.0 = « non_lues » (%d), pas « traduites »" % len(vides),
      e and e.get("non_lues") == vides and not set(vides) & set(e["pages"]), (e or {}).get("non_lues"))
src = open(os.path.join(HERE, "dialogues.py"), encoding="utf-8").read()
check("R13 dialogues.py : --traduire compte une page comme faite seulement si LUE (meme regle)",
      '(bool(p.get("lue")) if "lue" in p else bool(p.get("bulles")))' in src)
# --- R14 : les textes ecartes POUR L'IMAGE sont lus par les Dialogues ; « ...! » non
ec = [(p["page"], b) for p in tr["pages"] for b in p["bulles"] if b.get("ecarte")]
lus = [b.get("ecarte") for _, b in ec if dl.ecarte_pour_image(b)]
exclus = [b.get("ecarte") for _, b in ec if not dl.ecarte_pour_image(b)]
check("R14 « zone trop grande » / « ne tiendrait pas » -> lus par les Dialogues (%d)" % len(lus), lus and all(not x.startswith("moins de 2") for x in lus), lus)
check("R14 « moins de 2 lettres » -> toujours exclus (%d)" % len(exclus), all(x.startswith("moins de 2") for x in exclus), exclus)
print("VERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
