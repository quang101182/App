# -*- coding: utf-8 -*-
"""Banc dialogues.py 1.21.x « tout » : ARRET avant les voix si l'IA doute (code 5, progress etape « doute »), sinon voix puis
video. Vraie cmd_tout ; preparer / voix / video remplaces par des faux (0 appel paye), copie temporaire (vraies donnees
intouchees). Usage : python test_tout_doute.py [--ancien dialogues.py]"""
import importlib.util, json, os, shutil, sys, tempfile, types
HERE = os.path.dirname(os.path.abspath(__file__))
MOD = sys.argv[sys.argv.index("--ancien") + 1] if "--ancien" in sys.argv else os.path.join(HERE, "dialogues.py")
OK, KO = [], []
def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom); print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail)[:150] if detail else ""), flush=True)
T = tempfile.mkdtemp(prefix="tout_"); os.environ["MANGA_SOURCES_DIR"] = T
dd = os.path.join(T, "s", "ch_1", "dialogues"); os.makedirs(dd)
def ecrire(reps, dbl=None):
    json.dump({"repliques": reps, "pages_vues": [1]}, open(os.path.join(dd, "dialogues.json"), "w", encoding="utf-8"))
    json.dump({"persos": [], "narrateur": {}, "doublons": dbl or []}, open(os.path.join(T, "s", "dialogues_distribution.json"), "w", encoding="utf-8"))
sys.path.insert(0, HERE); sys.argv = ["x"]
spec = importlib.util.spec_from_file_location("dlg_t", MOD); m = importlib.util.module_from_spec(spec)
try: spec.loader.exec_module(m)
except SystemExit: pass
m.SOURCES = T
appels = []
m.cmd_preparer = lambda a: appels.append("preparer") or 0
m.cmd_voix = lambda a: appels.append("voix") or 0
m.cmd_video = lambda a: appels.append("video") or 0
try:
    if not hasattr(m, "cmd_tout"):
        check("commande « tout » presente", False); raise SystemExit
    A = types.SimpleNamespace(chap="s/ch_1", pages="1-1", traduire=False, sans_preparation=False)
    ecrire([{"cle": "1-1", "page": 1, "id": 1, "qui": "inconnu", "lire": True}])
    appels.clear(); rc = m.cmd_tout(A); pr = json.load(open(os.path.join(dd, "progress.json"), encoding="utf-8"))
    check("personnage inconnu -> ARRET avant les voix (code 5, etape « doute »)", rc == 5 and appels == ["preparer"] and pr.get("etape") == "doute", (rc, appels, pr.get("arret")))
    ecrire([{"cle": "1-1", "page": 1, "id": 1, "qui": "Bob", "lire": True}], dbl=[{"garder": "Bob", "avec": ["Bobby"]}])
    appels.clear(); rc = m.cmd_tout(A)
    check("doublon probable -> ARRET avant les voix", rc == 5 and appels == ["preparer"], (rc, appels))
    ecrire([{"cle": "1-1", "page": 1, "id": 1, "qui": "Bob", "lire": True, "a_traiter": True}])
    appels.clear(); rc = m.cmd_tout(A)
    check("replique « a traiter » -> ARRET avant les voix", rc == 5, (rc, appels))
    ecrire([{"cle": "1-1", "page": 1, "id": 1, "qui": "Bob", "lire": True}])
    appels.clear(); rc = m.cmd_tout(A)
    check("aucun doute -> preparer, voix, video", rc == 0 and appels == ["preparer", "voix", "video"], (rc, appels))
    appels.clear(); rc = m.cmd_tout(types.SimpleNamespace(chap="s/ch_1", pages="1-1", traduire=False, sans_preparation=True))
    check("--sans-preparation -> voix puis video seulement", appels == ["voix", "video"], appels)
    m.cmd_voix = lambda a: appels.append("voix") or 4
    appels.clear(); rc = m.cmd_tout(A)
    check("quota epuise pendant les voix (code 4) -> pas de video", rc == 4 and appels == ["preparer", "voix"], (rc, appels))
finally:
    shutil.rmtree(T, ignore_errors=True)
print("\nVERDICT : %d/%d" % (len(OK), len(OK) + len(KO))); sys.exit(1 if KO else 0)
