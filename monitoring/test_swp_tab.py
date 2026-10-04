# Onglet SubWhisper Pro du tableau de bord (v2.42.0, refonte « l'essentiel d'abord »),
# teste dans un vrai navigateur contre la VRAIE passerelle Pro, en largeur PC puis 360 px.
# Le jeton admin est lu dans la memoire perso (hors depot) et pose dans localStorage :
# il n'est jamais ecrit dans ce fichier ni affiche.
import base64, json, os, re, pathlib, subprocess, sys, time, urllib.request
import websocket

RACINE = pathlib.Path("D:/Download/02-Apps-Web/Repo-github")
PAGE = RACINE / "App/monitoring/monitoring-v2.html"
PORT = 9243
PROFIL = pathlib.Path(os.environ["TEMP"]) / "EdgeAuto-swp-tab"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
SORTIE = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(os.environ["TEMP"])
GW = "https://api-gateway-pro.quang101182.workers.dev"

qr = pathlib.Path.home() / ".claude/projects/D--Download-02-Apps-Web-Repo-github/memory/_quickref.md"
m = re.search(r"\*\*SubWhisper Pro\*\* → `([^`]+)`", qr.read_text(encoding="utf-8", errors="ignore"))
if not m:
    sys.exit("jeton SWP introuvable dans _quickref.md")
admin = m.group(1)

# Verite terrain, lue directement a la passerelle (independante du rendu)
req = urllib.request.Request(GW + "/admin/swp/overview", headers={"Authorization": "Bearer " + admin, "User-Agent": "Mozilla/5.0"})  # UA urllib = 403 WAF
ov = json.load(urllib.request.urlopen(req))
reels = [c for c in ov["customers_list"] if not re.search(r"@(test|example)\.", c.get("email") or "", re.I)]
en_cours = [c for c in reels if not c["revoked"]]
resilies = [c for c in en_cours if c.get("cancelAtPeriodEnd")]

proc = subprocess.Popen([EDGE, f"--remote-debugging-port={PORT}", f"--user-data-dir={PROFIL}",
                         "--no-first-run", "--no-default-browser-check", "--headless=new", "--remote-allow-origins=*",
                         "--window-size=1400,1000", f"file:///{PAGE.as_posix()}"])
time.sleep(6)

def page():
    for _ in range(15):
        try:
            d = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/list"))
            p = [t for t in d if t.get("type") == "page" and "monitoring" in (t.get("url") or "")]
            if p: return p[0]["webSocketDebuggerUrl"]
        except Exception: pass
        time.sleep(2)
    sys.exit("Edge injoignable")

ws = websocket.create_connection(page(), timeout=60)
n = 0
def cmd(method, params=None):
    global n
    n += 1
    ws.send(json.dumps({"id": n, "method": method, "params": params or {}}))
    while True:
        r = json.loads(ws.recv())
        if r.get("id") == n: return r.get("result", {})
def ev(expr):
    r = cmd("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True})
    if "exceptionDetails" in r: return {"__exception": str(r["exceptionDetails"])[:300]}
    return r.get("result", {}).get("value")

ok = ko = 0
def t(nom, cond, detail=""):
    global ok, ko
    if cond: ok += 1; print(f"  OK    {nom}")
    else: ko += 1; print(f"  ECHEC {nom}{' — ' + str(detail)[:250] if detail else ''}")

ev(f"localStorage.setItem('monitoring_swp_token', {json.dumps(admin)}); "
   "Object.keys(localStorage).filter(k=>k.startsWith('monitoring_v2_cache')).forEach(k=>localStorage.removeItem(k)); "
   "localStorage.removeItem('monitoring_v2_panels'); 1")
ev("location.hash = '#swp'; location.reload(); true")
time.sleep(4)
ws = websocket.create_connection(page(), timeout=60); n = 0
for _ in range(20):
    if ev("!!document.querySelector('#view-root .cl-list, #view-root .empty')"): break
    time.sleep(1)

def shot(nom, largeur):
    cmd("Emulation.setDeviceMetricsOverride", {"width": largeur, "height": 900, "deviceScaleFactor": 1, "mobile": largeur < 700})
    time.sleep(1.5)
    h = ev("document.documentElement.scrollHeight")
    cmd("Emulation.setDeviceMetricsOverride", {"width": largeur, "height": min(int(h), 4000), "deviceScaleFactor": 1, "mobile": largeur < 700})
    time.sleep(1)
    img = cmd("Page.captureScreenshot", {"format": "png"})["data"]
    f = SORTIE / nom
    f.write_bytes(base64.b64decode(img))
    print(f"  (capture) {f}")

print("=== Rendu ===")
t("version v2.42.x chargee", str(ev("VERSION")).startswith("v2.42"), ev("VERSION"))
txt = ev("document.querySelector('#view-root')?.textContent || ''")
t("section « L'essentiel » presente", "L’essentiel" in txt, txt[:150])
tiles = ev("Object.fromEntries([...document.querySelectorAll('#view-root .kpi-tile')].slice(0,4).map(t=>[t.querySelector('.kpi-label').textContent.trim(), t.querySelector('.kpi-value').textContent.trim()]))")
print("  (info) tuiles :", json.dumps(tiles, ensure_ascii=False))
t("4 tuiles essentielles", len(tiles or {}) == 4, tiles)
t("tuile Résiliations = verite passerelle", str(len(resilies)) == (tiles or {}).get("🚪 Résiliations"), f"{tiles} vs {len(resilies)}")
nb = ev("document.querySelectorAll('#view-root .cl-row').length")
t("une ligne par client en cours", nb == len(en_cours), f"{nb} vs {len(en_cours)}")
badges = ev("[...document.querySelectorAll('#view-root .cl-row')].map(r=>[r.querySelector('.cl-who').firstChild.textContent, r.querySelector('.badge').textContent, r.querySelectorAll('.cl-cell')[0].textContent])")
for b in badges or []: print("  (info)", b[0][:4] + "…", "|", b[1], "|", b[2])
for c in resilies:
    ligne = [b for b in badges if b[0] == c["email"]]
    t(f"résilié {c['email'][:4]}… affiché « Résilié » + date d'accès", bool(ligne) and ligne[0][1] == "Résilié" and "accès jusqu’au" in ligne[0][2], ligne)
t("plus de bandeau « au repos » (produit actif)", ev("!document.querySelector('#view-root .role-banner')") is True)
t("panneaux de detail replies par defaut", ev("[...document.querySelectorAll('#view-root .panel')].every(p=>p.dataset.open==='false')") is True)
t("le jeton n'apparait pas dans la page", admin not in (ev("document.documentElement.outerHTML") or ""))
shot("swp_pc.png", 1400)

print("=== Smartphone 360 px ===")
cmd("Emulation.setDeviceMetricsOverride", {"width": 360, "height": 800, "deviceScaleFactor": 1, "mobile": True})
time.sleep(1.5)
deb = ev("""(() => { const W = document.documentElement.clientWidth; return [...document.querySelectorAll('#view-root *')]
  .filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && (r.right > W + 1 || e.scrollWidth > e.clientWidth + 1 && getComputedStyle(e).overflowX !== 'visible'); })
  .map(e => e.className || e.tagName).slice(0, 5); })()""")
t("aucun debordement horizontal a 360 px", deb == [], deb)
ev("document.querySelectorAll('#view-root .panel-toggle').forEach(b=>b.click()); 1")
time.sleep(1)
deb2 = ev("""(() => { const W = document.documentElement.clientWidth; return [...document.querySelectorAll('#view-root *')]
  .filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.right > W + 1; }).map(e => e.className || e.tagName).slice(0, 5); })()""")
t("aucun debordement a 360 px, panneaux deplies", deb2 == [], deb2)
ev("document.querySelectorAll('#view-root .panel-toggle').forEach(b=>b.click()); localStorage.removeItem('monitoring_v2_panels'); 1")
time.sleep(0.5)
shot("swp_360.png", 360)

ws.close(); proc.terminate()
print(f"\nVERDICT : {ok} OK, {ko} ECHEC")
sys.exit(0 if ko == 0 else 1)
