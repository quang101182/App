# -*- coding: utf-8 -*-
"""Banc v2.90.0 : la bascule principale -> secondaire (chemin du TELEPHONE : l'adresse de l'autre application) ne laisse AUCUNE
entree d'historique -- le geste retour ne ramene plus a la principale. Principale 8190 et secondaire 8192 REELLES ; la fenetre
dediee du PC est court-circuitee (espaceFenetre echoue -> chemin du telephone). Usage : python test_bascule_historique_ui.py [html]"""
import os, sys
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(HERE, "..", "manga_studio.html")
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PAGE = open(HTML, encoding="utf-8").read()
OK, KO = [], []


def check(n, c, d=""):
    (OK if c else KO).append(n); print(("  [OK] " if c else "  [KO] ") + n + (" -- " + str(d)[:160] if d else ""), flush=True)


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    ctx = b.new_context(viewport={"width": 390, "height": 800}, is_mobile=True, has_touch=True)
    ctx.route("**/*", lambda rt: rt.fulfill(status=200, content_type="text/html; charset=utf-8", body=PAGE)
              if rt.request.method == "GET" and rt.request.url.split("#")[0].split("?")[0].rstrip("/").endswith("/manga") else rt.continue_())
    pg = ctx.new_page()
    pg.goto("about:blank")
    pg.goto("http://127.0.0.1:8190/manga/#k=" + KEY)
    pg.wait_for_function("() => typeof ESPACE !== 'undefined' && ESPACE.nom === 'normal'", timeout=30000); pg.wait_for_timeout(800)
    n0 = pg.evaluate("() => history.length")
    pg.evaluate("() => { window.espaceFenetre = async () => { throw new Error('pas de fenetre dediee (banc : chemin du telephone)'); }; espaceBasculer(); }")
    pg.wait_for_url("**:8192/**", timeout=20000)
    pg.wait_for_function("() => typeof ESPACE !== 'undefined' && ESPACE.nom === 'prive'", timeout=30000)
    check("bascule : on est dans la secondaire", pg.evaluate("() => ESPACE.nom") == "prive")
    garde = pg.evaluate("() => !!(history.state && history.state.garde)")   # v2.92.0 : la secondaire pose SA garde du retour
    check("aucune entrée d'historique de la bascule (%d -> %d, garde du retour : %s)" % (n0, pg.evaluate("() => history.length"), garde),
          pg.evaluate("() => history.length") == n0 + (1 if garde else 0))
    pg.go_back(); pg.wait_for_timeout(600)
    if garde:
        pg.go_back(); pg.wait_for_timeout(1500)                                # 2e retour (dans les 2,5 s) = quitter
    check("geste retour : ne ramène PAS à la principale", ":8190" not in pg.url, pg.url)
print("VERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
