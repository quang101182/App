# -*- coding: utf-8 -*-
"""Banc v2.86.0 : le geste de bascule entre les deux applications, au VRAI clic / appui (Playwright = evenements de
confiance). Principale 8190 et secondaire 8192 REELLES ; espaceBasculer est remplace par un COMPTEUR (on ne change jamais
vraiment d'application). En 1280 (souris) puis 360 (tactile).
Usage : python test_geste_bascule_ui.py [html]        (html v2.85.0 -> ROUGE)"""
import os, sys
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(HERE, "..", "manga_studio.html")
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PAGE = open(HTML, encoding="utf-8").read()
OK, KO = [], []
BIB = 'nav button[data-tab="tChap"]'


def check(n, c, d=""):
    (OK if c else KO).append(n); print(("  [OK] " if c else "  [KO] ") + n + (" -- " + str(d)[:160] if d else ""), flush=True)


def ouvrir(b, port, larg):
    ctx = b.new_context(viewport={"width": larg, "height": 800}, is_mobile=larg < 700, has_touch=larg < 700)
    pg = ctx.new_page(); pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)))
    pg.route("**/*", lambda rt: rt.fulfill(status=200, content_type="text/html; charset=utf-8", body=PAGE)
             if rt.request.method == "GET" and rt.request.url.split("#")[0].split("?")[0].rstrip("/").endswith("/manga") else rt.continue_())
    pg.goto("http://127.0.0.1:%d/manga#k=%s" % (port, KEY))
    pg.wait_for_function("() => typeof ESPACE !== 'undefined' && ESPACE.nom && typeof RESUME !== 'undefined' && RESUME", timeout=30000)
    pg.wait_for_timeout(800)
    pg.evaluate("() => { window.__bascule = 0; window.espaceBasculer = () => { window.__bascule++; }; }")
    return ctx, pg


def n(pg):
    return pg.evaluate("() => window.__bascule")


def onglet(pg, tab):
    # clic PAR PROGRAMME : se placer sur un onglet sans jamais declencher le geste teste
    pg.evaluate("t => document.querySelector('nav button[data-tab=\"' + t + '\"]').click()", tab)
    pg.wait_for_timeout(300)


def appui_long(pg):
    bx = pg.locator(BIB).bounding_box()
    pg.mouse.move(bx["x"] + bx["width"] / 2, bx["y"] + bx["height"] / 2); pg.mouse.down(); pg.wait_for_timeout(1500); pg.mouse.up()
    pg.wait_for_timeout(300)


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for larg in (1280, 360):
        print("=== %d px" % larg)
        # --- SECONDAIRE
        ctx, pg = ouvrir(b, 8192, larg)
        check("secondaire reconnue", pg.evaluate("() => ESPACE.nom") == "prive")
        onglet(pg, "tChap")
        pg.click(BIB); pg.wait_for_timeout(300)
        check("secondaire, 📚 déjà affiché : appui simple = retour à la principale", n(pg) == 1, n(pg))
        onglet(pg, "tPerso")
        pg.click(BIB); pg.wait_for_timeout(400)
        check("secondaire, depuis un autre onglet : 1er appui = Bibliothèque, PAS de bascule",
              n(pg) == 1 and pg.evaluate("() => document.querySelector('%s').classList.contains('sel')" % BIB.replace("'", "\\'")))
        pg.click(BIB); pg.wait_for_timeout(300)
        check("secondaire : 2e appui = retour à la principale", n(pg) == 2, n(pg))
        pg.evaluate("() => document.querySelector('nav button[data-tab=\"tChap\"]').click()"); pg.wait_for_timeout(300)
        check("secondaire : un clic PAR PROGRAMME (l'app qui revient à 📚) ne bascule jamais", n(pg) == 2, n(pg))
        check("0 erreur JS (secondaire)", not pg.errs, pg.errs); ctx.close()
        # --- PRINCIPALE
        ctx, pg = ouvrir(b, 8190, larg)
        check("principale reconnue", pg.evaluate("() => ESPACE.nom") == "normal")
        onglet(pg, "tChap")
        pg.click(BIB); pg.wait_for_timeout(300)
        check("principale : appui simple sur 📚 = aucune bascule", n(pg) == 0, n(pg))
        appui_long(pg)
        check("principale, 📚 déjà affiché : appui long = secondaire", n(pg) == 1, n(pg))
        onglet(pg, "tPerso")
        appui_long(pg)
        check("principale, depuis un autre onglet : appui long = Bibliothèque seulement, pas de bascule",
              n(pg) == 1 and pg.evaluate("() => document.querySelector('%s').classList.contains('sel')" % BIB.replace("'", "\\'")), n(pg))
        appui_long(pg)
        check("principale : 2e appui long = secondaire", n(pg) == 2, n(pg))
        check("0 erreur JS (principale)", not pg.errs, pg.errs); ctx.close()
print("VERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
