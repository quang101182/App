# -*- coding: utf-8 -*-
"""Banc v2.92.0 : dans la SECONDAIRE, le geste retour a la racine ne la ferme plus par accident. Secondaire 8192 et principale
8190 REELLES ; « quitter l'application » = revenir a la page d'avant (about:blank), comme Android quand l'historique est vide.
Usage : python test_garde_retour_ui.py [html]        (html v2.91.0 -> ROUGE)"""
import os, sys
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(HERE, "..", "manga_studio.html")
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PAGE = open(HTML, encoding="utf-8").read()
OK, KO = [], []


def check(n, c, d=""):
    (OK if c else KO).append(n); print(("  [OK] " if c else "  [KO] ") + n + (" -- " + str(d)[:160] if d else ""), flush=True)


def ouvrir(b, port, nom):
    ctx = b.new_context(viewport={"width": 390, "height": 800}, is_mobile=True, has_touch=True)
    ctx.route("**/*", lambda rt: rt.fulfill(status=200, content_type="text/html; charset=utf-8", body=PAGE)
              if rt.request.method == "GET" and rt.request.url.split("#")[0].split("?")[0].rstrip("/").endswith("/manga") else rt.continue_())
    pg = ctx.new_page(); pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)))
    pg.goto("about:blank"); pg.goto("http://127.0.0.1:%d/manga/#k=%s" % (port, KEY))
    pg.wait_for_function("n => typeof ESPACE !== 'undefined' && ESPACE.nom === n", arg=nom, timeout=30000); pg.wait_for_timeout(1200)
    pg.evaluate("() => { window.__toasts = []; const t = window.toast; window.toast = m => { window.__toasts.push(m); return t(m); }; }")
    return ctx, pg


dans_app = lambda pg: pg.url.startswith("http://127.0.0.1")
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    ctx, pg = ouvrir(b, 8192, "prive")
    pg.go_back(); pg.wait_for_timeout(600)
    check("secondaire : 1er retour à la racine = on RESTE dans l'app", dans_app(pg), pg.url)
    check("… avec « refais retour pour quitter »", any("refais retour" in t for t in pg.evaluate("() => window.__toasts")), pg.evaluate("() => window.__toasts"))
    pg.go_back(); pg.wait_for_timeout(600)
    check("2e retour dans les 2,5 s = on QUITTE l'app", not dans_app(pg), pg.url)
    ctx.close()
    ctx, pg = ouvrir(b, 8192, "prive")
    pg.go_back(); pg.wait_for_timeout(3300)
    check("sans 2e retour : la garde se réarme (après 2,5 s)", dans_app(pg) and pg.evaluate("() => !!(history.state && history.state.garde)"))
    pg.go_back(); pg.wait_for_timeout(600)
    check("… et un retour plus tard redonne l'avertissement (on reste)", dans_app(pg) and len(pg.evaluate("() => window.__toasts")) == 2)
    pg.wait_for_timeout(3000)
    pg.evaluate("() => { choixOuvrir({ titre: 'banc', items: [{ t: 'Un manga' }, { t: 'Un autre' }] }); }"); pg.wait_for_timeout(800)
    ouvert = pg.evaluate("() => !$('choix').hidden")
    pg.go_back(); pg.wait_for_timeout(800)
    check("écran « choix du manga » : le retour le FERME, sans avertissement, on reste",
          ouvert and pg.evaluate("() => $('choix').hidden") and dans_app(pg) and len(pg.evaluate("() => window.__toasts")) == 2,
          (ouvert, pg.evaluate("() => window.__toasts")))
    check("0 erreur JS (secondaire)", not pg.errs, pg.errs); ctx.close()
    ctx, pg = ouvrir(b, 8190, "normal")
    pg.go_back(); pg.wait_for_timeout(600)
    check("principale : inchangée (le retour la quitte directement)", not dans_app(pg), pg.url)
    ctx.close()
print("VERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
