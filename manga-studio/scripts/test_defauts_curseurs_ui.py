# -*- coding: utf-8 -*-
"""Banc R18 phase 2 (v2.91.0) : ☆ = defaut d'un curseur de lecture pour TOUTE l'application, propage aux autres appareils.
ISOLE : instance 8191, donnees = COPIE (son propre _reglages.json) ; les reglages reels des 2 applications sont verifies
intacts. Deux « appareils » = deux navigateurs (stockages separes). 0 credit.
Usage : python test_defauts_curseurs_ui.py <html> <proxy>        (html v2.90.0 -> ROUGE)"""
import hashlib, json, os, shutil, subprocess, sys, tempfile, time, urllib.request
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
HTML, PROXY = (os.path.abspath(x) for x in sys.argv[1:3])
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
DONNEES = os.path.expanduser(r"~\Documents\MangaStudio-donnees")
SRC = os.path.join(DONNEES, "sources")
PAGE = open(HTML, encoding="utf-8").read()
OK, KO = [], []


def check(n, c, d=""):
    (OK if c else KO).append(n); print(("  [OK] " if c else "  [KO] ") + n + (" -- " + str(d)[:180] if d else ""), flush=True)


emp = lambda f: hashlib.sha1(open(f, "rb").read()).hexdigest() if os.path.isfile(f) else None
REELS = [os.path.join(SRC, "_reglages.json"), os.path.join(DONNEES, "prive", "_reglages.json")]
avant = [emp(f) for f in REELS]
T = tempfile.mkdtemp(prefix="defcurs_")
SD = os.path.join(T, "one-punch-man"); os.makedirs(SD)
shutil.copytree(os.path.join(SRC, "one-punch-man", "ch_5"), os.path.join(SD, "ch_5"), ignore=shutil.ignore_patterns("video"))
for f in ("serie.json", "suivi.json", "dialogues_distribution.json"):
    shutil.copy(os.path.join(SRC, "one-punch-man", f), os.path.join(SD, f))
srv = subprocess.Popen([sys.executable, os.path.join(HERE, "proxy_8191.py"), PROXY], env=dict(os.environ, MANGA_SOURCES_DIR=T),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def appareil(b, larg):
    ctx = b.new_context(viewport={"width": larg, "height": 900}, is_mobile=larg < 700, has_touch=larg < 700)
    pg = ctx.new_page(); pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)))
    pg.route("**/*", lambda rt: rt.fulfill(status=200, content_type="text/html; charset=utf-8", body=PAGE)
             if rt.request.method == "GET" and rt.request.url.split("#")[0].split("?")[0].rstrip("/").endswith("/manga") else rt.continue_())
    pg.goto("http://127.0.0.1:8191/manga#k=" + KEY); pg.wait_for_timeout(1500)
    pg.evaluate("() => localStorage.setItem('manga_serie','one-punch-man')"); pg.reload()
    pg.wait_for_function("() => typeof RESUME !== 'undefined' && RESUME && RESUME.chapitres", timeout=30000); pg.wait_for_timeout(800)
    pg.evaluate("() => openChap(CHAPS.findIndex(c => c.dir === 'one-punch-man/ch_5'))"); pg.wait_for_timeout(2500)
    return ctx, pg


ETOILE = "() => { const b = document.querySelector('[data-def=\"vit_cloud\"]'); return b ? b.textContent : null }"
try:
    for _ in range(60):
        try:
            urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8191/manga/el_solde", headers={"Authorization": "Bearer " + KEY}), timeout=5); break
        except Exception:
            time.sleep(1)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        cpc, pc = appareil(b, 1280)
        check("PC : ☆ à côté de la vitesse ☁ du bloc Narration", pc.evaluate(ETOILE) == "☆")
        pc.evaluate("() => { $('narrVitCloud').value = '1.3'; $('narrVitCloud').dispatchEvent(new Event('change')); }"); pc.wait_for_timeout(400)
        et = pc.locator('[data-def="vit_cloud"]')
        (et.click() if et.is_visible() else pc.evaluate("() => document.querySelector('[data-def=\"vit_cloud\"]').click()")); pc.wait_for_timeout(1500)
        reg = json.load(open(os.path.join(T, "_reglages.json"), encoding="utf-8"))
        check("☆ : 1,3 = défaut de CETTE application (son _reglages.json)", reg.get("defauts", {}).get("vit_cloud") == 1.3, reg.get("defauts"))
        check("PC : ★ plein", pc.evaluate(ETOILE) == "★")
        # un 2e appareil, stockage vierge : il adopte le defaut au tour de suivi (au plus ~15 s)
        ctel, tel = appareil(b, 390)
        for _ in range(40):
            if tel.evaluate("() => localStorage.getItem('manga_vit_cloud')") == "1.3":
                break
            tel.wait_for_timeout(500)
        check("téléphone : adopte 1,3 tout seul (tour de suivi)", tel.evaluate("() => [localStorage.getItem('manga_vit_cloud'), $('narrVitCloud').value]") == ["1.3", "1.3"],
              tel.evaluate("() => [localStorage.getItem('manga_vit_cloud'), $('narrVitCloud').value]"))
        tel.evaluate("() => { $('narrVitCloud').value = '1.1'; $('narrVitCloud').dispatchEvent(new Event('change')); }"); tel.wait_for_timeout(300)
        tel.evaluate("() => modeSuivre()"); tel.wait_for_timeout(1500)
        check("téléphone : SA valeur locale (1,1) n'est pas écrasée au tour suivant ; ☆ vide", tel.evaluate("() => $('narrVitCloud').value") == "1.1" and tel.evaluate(ETOILE) == "☆")
        pc.evaluate("() => { $('narrVitCloud').value = '1.5'; $('narrVitCloud').dispatchEvent(new Event('change')); }"); pc.wait_for_timeout(300)
        pc.evaluate("() => document.querySelector('[data-def=\"vit_cloud\"]').click()"); pc.wait_for_timeout(1500)
        tel.evaluate("() => modeSuivre()"); tel.wait_for_timeout(1500)
        check("nouveau ☆ sur le PC (1,5) : réimposé au téléphone", tel.evaluate("() => $('narrVitCloud').value") == "1.5")
        # volume general : ☆ sur le PC -> le telephone
        pc.evaluate("() => { $('lecVolG').value = 60; $('lecVolG').dispatchEvent(new Event('input')); }")
        pc.evaluate("() => document.querySelector('[data-def=\"vol_g\"]').click()"); pc.wait_for_timeout(1500)
        tel.evaluate("() => modeSuivre()"); tel.wait_for_timeout(1500)
        check("volume général 60 : défaut, adopté par le téléphone", tel.evaluate("() => [VOL_G, localStorage.getItem('manga_vol_g')]") == [60, "60"],
              tel.evaluate("() => [VOL_G, localStorage.getItem('manga_vol_g')]"))
        # vitesse du lecteur des Dialogues : MEMORISEE desormais
        tel.evaluate("() => { $('dllVit').value = '1.25'; $('dllVit').dispatchEvent(new Event('change')); }"); tel.reload()
        tel.wait_for_function("() => typeof RESUME !== 'undefined' && RESUME", timeout=30000); tel.wait_for_timeout(1500)
        check("vitesse du lecteur des Dialogues mémorisée (1,25 après rechargement)", tel.evaluate("() => $('dllVit').value") == "1.25")
        check("menu ⋯ du lecteur vidéo : « ☆ vitesse actuelle par défaut »", tel.evaluate("() => !!document.querySelector('#vidMenu [data-def=\"vid_vit\"]')"))
        check("0 erreur JS (2 appareils)", not (pc.errs or tel.errs), pc.errs + tel.errs)
    check("réglages RÉELS des 2 applications intacts", [emp(f) for f in REELS] == avant)
finally:
    srv.kill(); time.sleep(1); shutil.rmtree(T, ignore_errors=True)
    try:
        os.remove(os.path.expanduser(r"~\Documents\ComfyUI\_studio_llm_proxy_8191.py"))
    except Exception:
        pass
print("VERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
