# -*- coding: utf-8 -*-
"""Banc v2.23.0 (§ 3-bis) : un script lance HORS de l'app (essai, banc, sonde) apparait dans le temoin de SON application
-- « 🧪 Essai · <nom du script> », jamais ses arguments -- et, anonyme, dans la vue croisee de l'autre.

Pose un script-dormeur temporaire dans scripts/ (efface a la fin) et le lance deux fois : une pour la principale, une pour
la secondaire (MANGA_SOURCES_DIR), par le Python du venv (lanceur + enfant : UNE seule ligne attendue). Un argument
« ZZARGSECRET » verifie que les arguments ne sortent jamais.
"""
import json, os, subprocess, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PY = os.path.expanduser(r"~\Documents\ComfyUI\.venv\Scripts\python.exe")
DORMEUR = os.path.join(HERE, "zz_banc_essai_dormeur.py")
PRIVE = os.path.expanduser(r"~\Documents\MangaStudio-donnees\prive")
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail and not cond else ""), flush=True)


def api(port, chemin):
    r = urllib.request.Request("http://127.0.0.1:%d%s" % (port, chemin), headers={"Authorization": "Bearer " + KEY})
    return json.load(urllib.request.urlopen(r, timeout=20))


essais = lambda port, ch="/manga/activite": [x for x in api(port, ch).get("items", []) if x.get("type") == "essai"]
open(DORMEUR, "w", encoding="utf-8").write("import time\ntime.sleep(90)\n")
fl = getattr(subprocess, "CREATE_NO_WINDOW", 0)
env_p = dict(os.environ); env_p.pop("MANGA_SOURCES_DIR", None)
env_s = dict(os.environ, MANGA_SOURCES_DIR=PRIVE)
procs = []
try:
    avant_p, avant_s = len(essais(8190)), len(essais(8192))
    procs.append(subprocess.Popen([PY, DORMEUR, "ZZARGSECRET"], env=env_p, creationflags=fl))
    time.sleep(3)
    e = [x for x in essais(8190) if x.get("etape") == "zz_banc_essai_dormeur"]
    check("principale : l'essai lance pour elle apparait, UNE fois (lanceur + enfant)", len(e) == 1, e)
    check("... sous le nom du script, sans ses arguments", e and "ZZARGSECRET" not in json.dumps(e), e)
    check("secondaire : ne le voit pas dans SON activite", not [x for x in essais(8192) if x.get("etape") == "zz_banc_essai_dormeur"])
    procs.append(subprocess.Popen([PY, DORMEUR, "ZZARGSECRET"], env=env_s, creationflags=fl))
    time.sleep(3)
    e = [x for x in essais(8192) if x.get("etape") == "zz_banc_essai_dormeur"]
    check("secondaire : l'essai lance pour elle apparait, UNE fois", len(e) == 1, e)
    a = [x for x in api(8190, "/manga/activite_autre").get("items", []) if x.get("type") == "essai"]
    check("principale, vue croisee : l'essai de la secondaire, anonyme (type + nom du script)",
          any(x.get("etape") == "zz_banc_essai_dormeur" for x in a) and all(set(x) <= {"type", "etape", "fait", "total", "reste_s"} for x in a), a)
    na = [x for x in essais(8190) if x.get("etape") == "espace_prive"]
    check("les serveurs eux-memes ne sont jamais comptes comme essais", not na, na)
finally:
    for p in procs: subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)   # lanceur + enfant
    time.sleep(1)
    try: os.remove(DORMEUR)
    except OSError: pass
time.sleep(2)
check("fin : plus aucun essai du banc", not [x for x in essais(8190) + essais(8192) if x.get("etape") == "zz_banc_essai_dormeur"])
print("\n%d/%d" % (len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
