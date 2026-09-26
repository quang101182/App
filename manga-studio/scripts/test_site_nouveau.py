# -*- coding: utf-8 -*-
"""Banc d'ENTREE d'un site dans sites.json (regle Quang 22/09 : capture reelle d'un chapitre ET enchainement teste).
Ouvre la page de la SERIE dans la fenetre de capture, y lit l'adresse reelle du chapitre demande (jamais devinee), capture
ce chapitre + N suivants dans un dossier TEMPORAIRE (jamais la bibliotheque), puis rend un verdict chiffre : chapitres obtenus,
pages par chapitre, images vides / minuscules, enchainement. Le dossier est garde pour inspection (chemin affiche).
Usage : python test_site_nouveau.py <port CDP> <adresse de la serie> [n° du 1er chapitre] [suivants] [titre]
  [titre] : capture DANS la bibliotheque (route de l'app) au lieu d'un dossier temporaire.
"""
import json, os, re, subprocess, sys, tempfile, time, urllib.request
from urllib.parse import quote
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
PORT, SERIE = sys.argv[1], sys.argv[2]
NUM = sys.argv[3] if len(sys.argv) > 3 else "1"
SUITE = int(sys.argv[4]) if len(sys.argv) > 4 else 1
TITRE = sys.argv[5] if len(sys.argv) > 5 else ""        # donne : capture DANS la bibliotheque sous ce titre
PY = os.path.join(os.environ["LOCALAPPDATA"], "manga-fetch", "venv", "Scripts", "python.exe")
MF = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "manga-fetch", "manga_fetch.py")
import websocket
def onglet(url):
    return json.load(urllib.request.urlopen(urllib.request.Request(
        "http://127.0.0.1:%s/json/new?%s" % (PORT, quote(url, safe="")), method="PUT")))
def evaluer(t, js):
    ws = websocket.create_connection(t["webSocketDebuggerUrl"], timeout=30, suppress_origin=True)
    ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate", "params": {"expression": js, "returnByValue": True}}))
    while True:
        m = json.loads(ws.recv())
        if m.get("id") == 1: return m["result"]["result"].get("value")
def fermer(t):
    try: urllib.request.urlopen("http://127.0.0.1:%s/json/close/%s" % (PORT, t["id"]))
    except Exception: pass

t = onglet(SERIE); time.sleep(10)
liens = evaluer(t, "[...document.querySelectorAll('a[href]')].map(a => a.href)") or []
fermer(t)
chap = [l for l in liens if re.search(r"/chapitre-%s/?$" % re.escape(NUM), l)]
print("liens de chapitres sur la page :", len([l for l in liens if "/chapitre-" in l]), "| chapitre", NUM, "->", chap[:1])
if not chap: print("VERDICT : ECHEC -- chapitre introuvable sur la page de la serie"); sys.exit(1)
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
APP = int(os.environ.get("MANGA_APP_PORT", "8190"))
def api(ch, corps=None):
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (APP, ch), data=json.dumps(corps).encode() if corps is not None else None,
                                 headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())
if TITRE:     # v26/09 : dans la BIBLIOTHEQUE, par le chemin de l'app (route /manga/fetch_capture, verrou « une capture a la fois »)
    t = onglet(chap[0]); time.sleep(8)
    r = api("/manga/fetch_capture", {"tab": t["url"], "title": TITRE, "chapter": NUM, "page1": True, "suite": SUITE})
    if r.get("error"): fermer(t); print("VERDICT : ECHEC -- " + r["error"]); sys.exit(1)
    t0 = time.time()
    while time.time() - t0 < 1200:
        time.sleep(5); st = api("/manga/fetch_status")
        if st.get("etat") != "en cours": break
    fermer(t)
    print("duree %.0f s, etat %s | %s" % (time.time() - t0, st.get("etat"), st.get("serie") or st.get("dossier")))
    for l in (st.get("sortie") or []):
        if any(k in l for k in ("Mode", "OK :", "ECHEC", "Notes", "Webtoon", "SÉRIE", "suivant", "arrêt")): print("   ", l[:170])
    j = api("/manga/sources"); dirs = st.get("dossiers") or ([st["dossier"]] if st.get("dossier") else [])
    racine_src = j.get("root") or ""
    if not os.path.isabs(racine_src): racine_src = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), racine_src or "sources")
    lieux = [os.path.join(racine_src, d) for d in dirs]
else:
    dest = tempfile.mkdtemp(prefix="banc_site_")
    lieux = None
if lieux is None:
  t = onglet(chap[0]); time.sleep(8)
  env = dict(os.environ, PYTHONIOENCODING="utf-8", MANGA_CAPTURE_PORT=PORT)
  t0 = time.time()
  r = subprocess.run([PY, MF, "capture", "--tab", t["url"], "--title", "banc site", "--chapter", NUM, "--page-1", "--force",
                      "--suite", str(SUITE), "--out", dest], capture_output=True, text=True, encoding="utf-8", errors="replace",
                     env=env, timeout=1200)
  fermer(t)
  print("duree %.0f s, code %d" % (time.time() - t0, r.returncode))
  for l in r.stdout.splitlines():
      if any(k in l for k in ("Mode", "OK :", "ECHEC", "Notes", "Webtoon", "SÉRIE", "suivant", "arrêt", "Enchaîn")): print("   ", l[:170])
  if r.returncode: print("   stderr :", r.stderr[-600:])
from PIL import Image
res = []
for racine, dossiers, fichiers in (os.walk(dest) if lieux is None else [next(os.walk(x)) for x in lieux if os.path.isdir(x)]):
    imgs = sorted(f for f in fichiers if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")) and "cover" not in f.lower())
    if not imgs or "manifest.json" not in fichiers: continue
    man = json.load(open(os.path.join(racine, "manifest.json"), encoding="utf-8"))
    tailles = [Image.open(os.path.join(racine, f)).size for f in imgs]
    vides = sum(1 for f in imgs if Image.open(os.path.join(racine, f)).convert("L").getextrema()[1] - Image.open(os.path.join(racine, f)).convert("L").getextrema()[0] < 12)
    petites = sum(1 for w, h in tailles if w < 300 or h < 200)
    res.append((str(man.get("chapter")), len(imgs), vides, petites, tailles[0] if tailles else None))
    print("  ch.%s : %d pages, %d vides, %d minuscules, 1re page %s  (%s)" % (res[-1][0], len(imgs), vides, petites, tailles[0], racine))
ok = len(res) == SUITE + 1 and all(n >= 3 and v == 0 and p == 0 for _, n, v, p, _ in res)
print("VERDICT : %s -- %d chapitre(s) sur %d attendus ; %s" % ("OK" if ok else "ECHEC", len(res), SUITE + 1, "dans la bibliotheque" if TITRE else "dossier : " + dest))
sys.exit(0 if ok else 1)
