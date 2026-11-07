# Onglet DictoKey du tableau de bord (v2.51.0) : cartes « Activation : 1re dictée » et « Semaine de bienvenue »,
# testees dans un vrai Edge contre la VRAIE passerelle. Jeton admin lu dans l'environnement (DKA, pose par
# avec_secret.py), jamais ecrit sur disque ni affiche :
#   python .claude/scripts/avec_secret.py "jeton admin DictoKey (dk-a)" DKA -- python App/monitoring/test_dk_tab.py
# file:// est representatif ICI : la passerelle DictoKey repond Access-Control-Allow-Origin: * (gateway index.js:109).
import json, os, pathlib, subprocess, sys, time, urllib.request
import websocket

PAGE = pathlib.Path("D:/Download/02-Apps-Web/Repo-github/App/monitoring/monitoring-v2.html")
PORT = 9243
PROFIL = pathlib.Path(os.environ["TEMP"]) / "EdgeAuto-dktab"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
admin = os.environ.get("DKA", "").strip()
if not admin:
    sys.exit("DKA absent : lancer via avec_secret.py")

proc = subprocess.Popen([EDGE, f"--remote-debugging-port={PORT}", f"--user-data-dir={PROFIL}", "--no-first-run",
                         "--no-default-browser-check", "--headless=new", "--remote-allow-origins=*",
                         "--window-size=1280,900", f"file:///{PAGE.as_posix()}"])
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

ws = websocket.create_connection(page(), timeout=90); n = 0
def cmd(method, params=None):
    global n
    n += 1
    ws.send(json.dumps({"id": n, "method": method, "params": params or {}}))
    while True:
        m = json.loads(ws.recv())
        if m.get("id") == n: return m.get("result", {})
def ev(expr, attendre=True):
    r = cmd("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": attendre})
    if "exceptionDetails" in r: return {"__exception": str(r["exceptionDetails"])[:300]}
    return r.get("result", {}).get("value")

ok = ko = 0
def t(nom, cond, detail=""):
    global ok, ko
    if cond: ok += 1; print(f"  OK    {nom}")
    else: ko += 1; print(f"  ECHEC {nom}{' — ' + str(detail)[:300] if detail else ''}")

try:
    print("=== JS vivant ===")
    t("VERSION = v2.51.0", str(ev("typeof VERSION !== 'undefined' && VERSION")).startswith("v2.51.0"), ev("typeof VERSION"))
    t("les deux fonctions existent", ev("typeof renderDkPremiereDictee === 'function' && typeof renderDkBienvenue === 'function'") is True)

    print("\n=== Onglet DictoKey, vraies donnees ===")
    ev(f"localStorage.setItem('monitoring_admin_token', {json.dumps(admin)}); 1", attendre=False)
    ev("Object.keys(localStorage).filter(k=>k.startsWith('monitoring_v2_cache')).forEach(k=>localStorage.removeItem(k)); 1", attendre=False)
    ev("location.hash = '#dk'; location.reload(); true", attendre=False)
    time.sleep(5)
    ws.close(); ws = websocket.create_connection(page(), timeout=90); n = 0
    for _ in range(30):
        if ev("!!document.querySelector('#dk-bienv') || !!document.querySelector('[data-panel=\"dk-bienv\"]') || (document.querySelector('#view-root')?.textContent||'').includes('Semaine de bienvenue')"): break
        time.sleep(2)
    txt = ev("document.querySelector('#view-root')?.textContent || ''") or ""
    t("pas d'ecran « jeton requis »", ev("!!document.querySelector('[data-token-save]')") is False)
    t("carte 1re dictee rendue", "Activation : 1ʳᵉ dictée" in txt and "Installations qui font une 1ʳᵉ vraie dictée" in txt, txt[:200])
    i = txt.find("Installations qui font"); print("  (info)", txt[i:i + 260].replace("\n", " "))
    t("carte 1re dictee : un total chiffre", "Total" in txt[i:i + 400] and "%" in txt[i:i + 400])
    t("carte bienvenue rendue", "Semaine de bienvenue (gratuits)" in txt and "Interrupteur" in txt, txt[:200])
    j = txt.find("Interrupteur :", txt.find("Semaine de bienvenue (gratuits)")); print("  (info)", txt[j:j + 260].replace("\n", " "))
    t("interrupteur lu = Ombre (etat reel au 07/11)", "Ombre" in txt[j:j + 60], txt[j:j + 80])
    t("aucun BUG signale sur les vraies donnees", "BUG" not in txt[j:j + 2000])
    t("les autres cartes restent rendues (accueil)", "Nouvel accueil (app 2.75)" in txt)
    t("jeton absent du DOM", admin not in (ev("document.documentElement.outerHTML") or ""))

    print("\n=== 360 px : rien ne deborde ===")
    cmd("Emulation.setDeviceMetricsOverride", {"width": 360, "height": 800, "deviceScaleFactor": 1, "mobile": True})
    ev("document.querySelectorAll('details').forEach(d => d.open = true); 1", attendre=False)
    time.sleep(2)
    larg = ev("""(() => { const de = document.documentElement; const out = [];
      for (const id of ['dk-premiere', 'dk-bienv']) {
        const el = document.getElementById(id) || document.querySelector(`[data-panel="${id}"]`) || [...document.querySelectorAll('.panel, details, section')].find(x => (x.textContent||'').includes(id === 'dk-bienv' ? 'Semaine de bienvenue (gratuits)' : 'Activation : 1ʳᵉ dictée'));
        if (!el) { out.push(id + ':absent'); continue; }
        el.querySelectorAll('*').forEach(c => { if (c.scrollWidth > c.clientWidth + 1 && getComputedStyle(c).overflowX !== 'visible') out.push(id + ':' + c.className); });
        const r = el.getBoundingClientRect(); if (r.right > 361) out.push(id + ':right=' + Math.round(r.right));
      }
      return { page: de.scrollWidth <= de.clientWidth, details: out }; })()""")
    t("la page ne deborde pas a 360 px", bool(larg) and larg.get("page") is True, larg)
    t("aucun conteneur interne des 2 cartes ne scrolle", bool(larg) and not larg.get("details"), larg)
    shot = cmd("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
finally:
    try: ws.close()
    except Exception: pass
    proc.terminate()
print(f"\nVERDICT : {ok} OK, {ko} ECHEC")
sys.exit(0 if ko == 0 else 1)
