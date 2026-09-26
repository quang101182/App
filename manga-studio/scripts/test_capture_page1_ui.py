# -*- coding: utf-8 -*-
"""Banc v2.74.0 : capture -- « depuis la page 1 » COCHEE d'office (appareil neuf) et choix MEMORISE apres rechargement.
APP REELLE, rien n'est capture. 360 et 1280 px.
Usage : python test_capture_page1_ui.py [port] [--mutation]   (--mutation : ancienne app servie (ni defaut ni memoire) -> ROUGE)
"""
import os, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
MUT = "--mutation" in sys.argv; sys.argv = [a for a in sys.argv if a != "--mutation"]
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
URL = "http://127.0.0.1:%d/manga#k=%s" % (PORT, KEY)
OK, KO = [], []
def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail)[:200] if detail else ""), flush=True)
def saboter(route):
    r = route.fetch(); t = r.text(); i = t.index("// v2.74.0 : « depuis la page 1 »"); j = t.index("\n", t.index('$("capPage1").addEventListener("change"', i))
    route.fulfill(response=r, body=t[:i] + t[j:])
CASE = "() => $('capPage1').checked"

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w, h in (((360, 780),) if MUT else ((360, 780), (1280, 900))):
        print("== %d px" % w)
        c = b.new_context(viewport={"width": w, "height": h}, is_mobile=w < 500, has_touch=True)   # appareil NEUF : localStorage vide
        pg = c.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        if MUT: pg.route("**/manga", saboter)
        pg.goto(URL); pg.wait_for_timeout(3500)
        check("appareil neuf : « depuis la page 1 » cochée d'office", pg.evaluate(CASE))
        pg.evaluate("() => { $('capBox').open = true; }"); pg.wait_for_timeout(300)
        check("case visible une fois la capture dépliée", pg.is_visible("#capPage1"))
        pg.click("#capPage1"); pg.wait_for_timeout(200)
        pg.reload(); pg.wait_for_timeout(3500)
        check("décochée → rechargement → reste DÉCOCHÉE", not pg.evaluate(CASE))
        pg.evaluate("() => { $('capBox').open = true; }"); pg.wait_for_timeout(300); pg.click("#capPage1"); pg.wait_for_timeout(200)
        pg.reload(); pg.wait_for_timeout(3500)
        check("recochée → rechargement → reste COCHÉE", pg.evaluate(CASE))
        check("aucune erreur JS", not errs, errs[:3])
        c.close()
    b.close()
print("\nVERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
