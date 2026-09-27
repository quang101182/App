# -*- coding: utf-8 -*-
"""Banc v3.5.5 : telecommande de la fenetre de capture -- onglets dans l'ORDRE DU PC, ✕ sur chaque onglet avec annulation.
VRAI Edge JETABLE (profil temporaire, port libre verifie) ouvert avec 3 onglets A, B, C dans cet ordre ; serveur de TEST 8191
(copie patchee du proxy, pointee sur ce port) ; page de l'app a 360 px ; vrais clics. La vraie fenetre de capture n'est jamais
touchee. Controles : ordre A B C (source « barre ») ; toucher C ne le deplace PAS ; ✕ sur chaque onglet ; ✕ B -> masque + « Annuler »
-> garde (Edge a toujours 3 onglets apres 6 s) ; ✕ B sans annuler -> Edge n'a plus que A et C ; 0 debordement, 0 erreur JS.
Usage : python test_pilote_onglets_ui.py <html> <proxy (patche ou non)>"""
import json, os, shutil, socket, subprocess, sys, tempfile, time, urllib.request
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
HTML, PROXY = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
OK, KO = [], []
k = socket.socket(); k.bind(("127.0.0.1", 0)); PORT = k.getsockname()[1]; k.close()
T = tempfile.mkdtemp(prefix="banc_pilote_")
URLS = ["https://example.com/?onglet=A", "https://example.org/?onglet=B", "https://example.net/?onglet=C"]
# titres DISTINCTS (les 3 pages « Example Domain » etaient indiscernables par leur titre) : on les renomme apres chargement


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail)[:170] if detail else ""), flush=True)


def cdp_pages():
    return [t for t in json.load(urllib.request.urlopen("http://127.0.0.1:%d/json/list" % PORT, timeout=3)) if t["type"] == "page"]


edge = next(p for p in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe") if os.path.exists(p))
eproc = subprocess.Popen([edge, "--remote-debugging-port=%d" % PORT, "--user-data-dir=" + os.path.join(T, "profil"), "--no-first-run",
                          "--no-default-browser-check", "--disable-sync", "--window-position=60,60", "--window-size=1000,700"] + URLS)
src = open(PROXY, encoding="utf-8").read()
assert 'MF_CDP = "http://127.0.0.1:9223"' in src
copie = os.path.join(T, "proxy_banc.py")
open(copie, "w", encoding="utf-8").write(src.replace('MF_CDP = "http://127.0.0.1:9223"', 'MF_CDP = "http://127.0.0.1:%d"' % PORT))
srv = subprocess.Popen([sys.executable, os.path.join(HERE, "proxy_8191.py"), copie], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
PAGE = open(HTML, encoding="utf-8").read()
try:
    for _ in range(40):
        try:
            if len(cdp_pages()) >= 3: break
        except Exception: pass
        time.sleep(0.5)
    time.sleep(3)
    import websocket
    for t in cdp_pages():
        w = websocket.create_connection(t["webSocketDebuggerUrl"], timeout=10, suppress_origin=True)
        w.send(json.dumps({"id": 1, "method": "Runtime.evaluate", "params": {"expression": "document.title = 'Onglet ' + location.search.split('=')[1]"}})); w.recv(); w.close()
    time.sleep(1.5)
    for _ in range(60):
        try:
            urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8191/manga/el_solde", headers={"Authorization": "Bearer " + KEY}), timeout=5); break
        except Exception: time.sleep(1)
    with sync_playwright() as p:
        br = p.chromium.launch(channel="msedge", headless=True)
        pg = br.new_context(viewport={"width": 360, "height": 800}, is_mobile=True, service_workers="block").new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("dialog", lambda d: d.dismiss())
        pg.route("**/*", lambda rt: rt.fulfill(status=200, content_type="text/html; charset=utf-8", body=PAGE)
                 if rt.request.method == "GET" and rt.request.url.split("#")[0].split("?")[0].rstrip("/").endswith("/manga") else rt.continue_())
        pg.goto("http://127.0.0.1:8191/manga/#k=" + KEY); pg.wait_for_timeout(3000)
        print("     version :", pg.evaluate("() => VERSION"))
        pg.evaluate("() => { $('pilBox').hidden = false; }")
        pg.evaluate("() => pilOnglets()"); pg.wait_for_timeout(1500)
        ordre = lambda: pg.evaluate("() => [...document.querySelectorAll('#pilOnglets [data-pil-onglet]')].map(b => b.title.split(' — ').pop())")
        lettre = lambda l: [u.rsplit("=", 1)[-1] for u in l]
        j = pg.evaluate("() => api('/manga/pilote_onglets')")
        check("ordre du PC : A B C (lu dans la barre d'onglets)", lettre(ordre()) == ["A", "B", "C"] and j.get("ordre") == "barre", (lettre(ordre()), j.get("ordre")))
        pg.evaluate("() => document.querySelectorAll('#pilOnglets [data-pil-onglet]')[2].click()"); pg.wait_for_timeout(2500)
        pg.evaluate("() => pilOnglets()"); pg.wait_for_timeout(1500)
        mru = [t["url"].rsplit("=", 1)[-1] for t in cdp_pages()]
        check("toucher C : il est actif dans Edge MAIS reste a sa place (A B C)", mru[0] == "C" and lettre(ordre()) == ["A", "B", "C"], (mru, lettre(ordre())))
        check("un ✕ sur CHAQUE onglet", pg.evaluate("() => document.querySelectorAll('#pilOnglets .pil-x').length") == 3)
        pg.evaluate("() => document.querySelectorAll('#pilOnglets .pil-x')[1].click()"); pg.wait_for_timeout(400)
        a = pg.evaluate("() => ({ vis: [...document.querySelectorAll('#pilOnglets [data-pil-onglet]')].length, annul: !!document.querySelector('[data-pil-annul]') })")
        check("✕ B : masque tout de suite + « Annuler » propose", a["vis"] == 2 and a["annul"], a)
        pg.evaluate("() => document.querySelector('[data-pil-annul]').click()"); pg.wait_for_timeout(6000)
        check("« Annuler » : B revient, Edge a toujours ses 3 onglets", len(cdp_pages()) == 3 and lettre(ordre()) == ["A", "B", "C"], (len(cdp_pages()), lettre(ordre())))
        pg.evaluate("() => document.querySelectorAll('#pilOnglets .pil-x')[1].click()"); pg.wait_for_timeout(7000)
        rest = sorted(t["url"].rsplit("=", 1)[-1] for t in cdp_pages())
        check("✕ B sans annuler : fermé dans Edge apres 5 s (A et C restent)", rest == ["A", "C"], rest)
        pg.evaluate("() => pilOnglets()"); pg.wait_for_timeout(1500)
        check("rangee a jour : A C", lettre(ordre()) == ["A", "C"], lettre(ordre()))
        pg.screenshot(path=os.path.join(HERE, "samsung_out", "pilote_onglets_360.png"))
        check("aucun debordement de la page", not pg.evaluate("() => document.documentElement.scrollWidth > document.documentElement.clientWidth"))
        check("0 erreur JS", not errs, errs[:2])
        br.close()
finally:
    srv.terminate()
    try: srv.wait(10)
    except Exception: srv.kill()
    f8191 = os.path.expanduser(r"~\Documents\ComfyUI\_studio_llm_proxy_8191.py")
    if os.path.exists(f8191): os.remove(f8191)
    subprocess.run(["taskkill", "/F", "/T", "/PID", str(eproc.pid)], capture_output=True)
    time.sleep(1.5)
    shutil.rmtree(T, ignore_errors=True)
print("\nVERDICT : %d/%d" % (len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
