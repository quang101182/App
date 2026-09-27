# -*- coding: utf-8 -*-
"""Banc dialogues.py 1.25.0 : le cout des voix = credits MESURES (solde ElevenLabs avant / apres), plus l'estimation ;
le tarif / caractere se recale. VRAIE cmd_voix sur une COPIE (sans voix -> tout a faire) ; ElevenLabs remplace par un faux
(el_post, solde 0 puis 500) : 0 credit depense, journal des depenses JETABLE (dossier temporaire).
Usage : python test_cout_voix_mesure.py <serie/ch_N prepare> [--ancien dialogues.py]"""
import importlib.util, json, os, shutil, sys, tempfile, types
HERE = os.path.dirname(os.path.abspath(__file__))
args = [x for x in sys.argv[1:] if not x.startswith("--")]
CH = args[0]
MOD = sys.argv[sys.argv.index("--ancien") + 1] if "--ancien" in sys.argv else os.path.join(HERE, "dialogues.py")
SRC = os.path.expanduser(r"~\Documents\MangaStudio-donnees\sources")
OK, KO = [], []
def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom); print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail)[:160] if detail else ""), flush=True)
T = tempfile.mkdtemp(prefix="cout_")
serie, chap = CH.split("/"); C = os.path.join(T, serie, chap)
os.makedirs(os.path.join(C, "dialogues"))
for f in os.listdir(os.path.join(SRC, serie)):
    if f.endswith(".json"): shutil.copy2(os.path.join(SRC, serie, f), os.path.join(T, serie, f))
for f in os.listdir(os.path.join(SRC, CH)):
    if f.endswith(".json"): shutil.copy2(os.path.join(SRC, CH, f), os.path.join(C, f))
doc = json.load(open(os.path.join(SRC, CH, "dialogues", "dialogues.json"), encoding="utf-8"))
for x in doc["repliques"]: x.pop("voix", None)                    # tout a refaire
json.dump(doc, open(os.path.join(C, "dialogues", "dialogues.json"), "w", encoding="utf-8"), ensure_ascii=False)
os.environ["MANGA_SOURCES_DIR"] = T; os.environ["MANGA_DEPENSES"] = os.path.join(T, "_depenses.jsonl")
sys.path.insert(0, HERE); sys.argv = ["x"]
spec = importlib.util.spec_from_file_location("dlg_cout", MOD); m = importlib.util.module_from_spec(spec)
try: spec.loader.exec_module(m)
except SystemExit: pass
m.SOURCES = T
import depenses; depenses.REGISTRE = os.environ["MANGA_DEPENSES"]; m.depenses = depenses
soldes = iter([{"utilises": 0, "limite": 124912, "restants": 124912}, {"utilises": 500, "limite": 124912, "restants": 124412}])
m.el_solde = lambda: next(soldes, {"utilises": 500, "limite": 124912, "restants": 124412})
m.el_post = lambda path, body: b"ID3fake"
m.fuite_balise = lambda f, t, st: (False, "")
m.balises = lambda distrib, tons, stats: {}
m.time.sleep = lambda s: None
import narrate_chapter as nc; nc.duree_mp3 = lambda f: 1.0; m.nc.duree_mp3 = nc.duree_mp3
try:
    rc = m.cmd_voix(types.SimpleNamespace(chap=CH, pages=""))
    lignes = [json.loads(l) for l in open(os.environ["MANGA_DEPENSES"], encoding="utf-8") if l.strip()] if os.path.exists(os.environ["MANGA_DEPENSES"]) else []
    v = [l for l in lignes if l.get("tag") == "voix"]
    check("generation terminee", rc == 0, rc)
    check("journal : credits MESURES (500), pas l'estimation", bool(v) and (v[-1].get("credits") == 500), v[-1:] if v else lignes[-2:])
    t = json.load(open(os.path.join(T, "_elevenlabs_tarif.json"), encoding="utf-8")) if os.path.exists(os.path.join(T, "_elevenlabs_tarif.json")) else {}
    check("tarif recale par la mesure (fichier _elevenlabs_tarif.json)", bool(t.get("par_car")) and t.get("mesures") == 1, t)
    check("les estimations suivantes utilisent le tarif mesure", abs(m.tarif_el() - t.get("par_car", -1)) < 1e-9 if t else False, (m.tarif_el() if hasattr(m, "tarif_el") else None))
finally:
    shutil.rmtree(T, ignore_errors=True)
print("\nVERDICT : %d/%d" % (len(OK), len(OK) + len(KO))); sys.exit(1 if KO else 0)
