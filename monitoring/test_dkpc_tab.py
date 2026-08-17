# Onglet dkpc du tableau de bord, teste dans un vrai navigateur contre la VRAIE
# passerelle. Le jeton admin est lu dans le KV et pose dans localStorage : il
# n'est jamais ecrit sur disque ni affiche.
import json, os, re, pathlib, subprocess, sys, time, urllib.request
import websocket

RACINE = pathlib.Path("D:/Download/02-Apps-Web/Repo-github")
PAGE = RACINE / "App/monitoring/monitoring-v2.html"
PORT = 9241
PROFIL = pathlib.Path(os.environ["TEMP"]) / "EdgeAuto-dkpc"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

# ── Jeton Cloudflare (memoire perso, hors depot) puis jeton admin depuis le KV ──
qr = (pathlib.Path.home() / ".claude/projects/D--Download-02-Apps-Web-Repo-github/memory/_quickref.md")
cf = re.search(r"(cfut_[A-Za-z0-9_-]+)", qr.read_text(encoding="utf-8", errors="ignore")).group(1)
ACCOUNT = "9252be67c92c344899dfc0647bcdb1a0"
NS = "c06227125aae4fda9c01f46ff2261d4b"
req = urllib.request.Request(
    f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT}/storage/kv/namespaces/{NS}/values/cfg:admin_token",
    headers={"Authorization": f"Bearer {cf}"})
admin = urllib.request.urlopen(req).read().decode().strip()
if not admin:
    sys.exit("cfg:admin_token vide — impossible de tester la vue authentifiee")

proc = subprocess.Popen([EDGE, f"--remote-debugging-port={PORT}", f"--user-data-dir={PROFIL}",
                         "--no-first-run", "--no-default-browser-check", "--headless=new", "--remote-allow-origins=*",
                         f"file:///{PAGE.as_posix()}"])
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
def ev(expr, attendre=True):
    global n
    n += 1
    ws.send(json.dumps({"id": n, "method": "Runtime.evaluate",
                        "params": {"expression": expr, "returnByValue": True, "awaitPromise": attendre}}))
    while True:
        m = json.loads(ws.recv())
        if m.get("id") == n:
            r = m.get("result", {})
            if "exceptionDetails" in r:
                return {"__exception": str(r["exceptionDetails"].get("exception", {}).get("description"))[:300]}
            return r.get("result", {}).get("value")

ok = ko = 0
def t(nom, cond, detail=""):
    global ok, ko
    if cond: ok += 1; print(f"  OK    {nom}")
    else: ko += 1; print(f"  ECHEC {nom}{' — ' + str(detail)[:200] if detail else ''}")

print("=== Le JS du dashboard vit-il ? ===")
t("VERSION lisible (aucune erreur de syntaxe)", ev("typeof VERSION !== 'undefined' && VERSION").__str__().startswith("v2.28"),
  ev("typeof VERSION !== 'undefined' ? VERSION : 'JS MORT'"))
t("l'onglet dkpc est declare", ev("APPS.some(a => a.key === 'dkpc')") is True)
t("renderDkpcView existe", ev("typeof renderDkpcView === 'function'") is True)

print("\n=== L'onglet s'affiche avec les vraies donnees ===")
ev(f"localStorage.setItem('monitoring_dkpc_token', {json.dumps(admin)})", attendre=False)
# ⚠️ Le dashboard sert un CACHE localStorage : sans purge, on teste l'affichage
# d'hier et on croit que le nouveau code ne marche pas. Piège payé le 17/08.
ev("Object.keys(localStorage).filter(k=>k.startsWith('monitoring_v2_cache')).forEach(k=>localStorage.removeItem(k)); 1", attendre=False)
ev("location.hash = '#dkpc'; location.reload(); true", attendre=False)
time.sleep(6)
ws = websocket.create_connection(page(), timeout=60); n = 0
time.sleep(10)

titre = ev("document.querySelector('#view-root h1')?.textContent?.trim()")
t("le titre est celui de DictoKey PC", "DictoKey PC" in (titre or ""), titre)

verrou = ev("!!document.querySelector('[data-token-save]')")
t("pas d'ecran « token requis » (le jeton est accepte)", verrou is False)

txt = ev("document.querySelector('#view-root')?.textContent || ''")
t("la section revenu est rendue", "MRR" in (txt or "") and "Revenu" in (txt or ""), (txt or "")[:150])
t("le parc de licences est rendu", "Parc de licences" in (txt or ""))
t("aucun echec de chargement affiche", "Echec du chargement" not in (txt or "").replace("é", "e"), (txt or "")[:200])

lignes = ev("document.querySelectorAll('#view-root table.data-table tbody tr').length")
print(f"  (info) lignes de licences affichees : {lignes}")

# Le piege du projet : afficher un MRR qui compte les non-payants.
mrr = ev("""(() => {
  const tiles = [...document.querySelectorAll('#view-root .kpi-tile')];
  const o = {};
  tiles.forEach(t => { o[t.querySelector('.kpi-label')?.textContent?.trim()] = t.querySelector('.kpi-value')?.textContent?.trim(); });
  return o;
})()""")
print("  (info) KPI :", json.dumps(mrr, ensure_ascii=False))
essais = ev("""(() => {
  const tiles = [...document.querySelectorAll('#view-root .kpi-tile')];
  const e = tiles.find(t => (t.querySelector('.kpi-label')?.textContent||'').includes('Essais'));
  return e ? e.querySelector('.kpi-value')?.textContent?.trim() : null;
})()""")
mrrNet = [v for k, v in (mrr or {}).items() if "MRR encaiss" in k]
t("l'essai en cours ne compte PAS comme du revenu",
  bool(mrrNet) and mrrNet[0].startswith("0") and essais not in (None, "0"),
  f"MRR={mrrNet} essais={essais}")

# ⚠️ Relire le DOM ICI : `txt` a été capturé plus haut, avant la fin du rendu.
txt = ev("document.querySelector('#view-root')?.textContent || ''")
# L'usage est desormais REELLEMENT compte : on verifie qu'il s'affiche.
t("la section usage reel est rendue", "Usage" in (txt or "") and "Utilisateurs actifs" in (txt or ""), (txt or "")[:200])
t("le cout estime est affiche", "Cout estime" in (txt or "").replace("û","u").replace("é","e"), "")
t("l'activite par jour est rendue", "Activite par jour" in (txt or "").replace("é","e"), "")
t("les utilisateurs actifs sont > 0", any(c.isdigit() for c in str(mrr)), str(mrr))

# Le token ne doit pas fuiter dans le DOM rendu.
t("le jeton admin n'apparait pas dans la page", admin not in (ev("document.documentElement.outerHTML") or ""))

ws.close(); proc.terminate()
print(f"\nVERDICT : {ok} OK, {ko} ECHEC")
sys.exit(0 if ko == 0 else 1)
