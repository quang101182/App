# -*- coding: utf-8 -*-
"""Banc UI v2.7.4 : poubelle des morceaux dans le PROFIL de la serie (Quang 23/09 21h46). Ne supprime RIEN : la
confirmation est REFUSEE, on verifie que le morceau reste. PC + 360 px.  Usage : python test_prof_mus_suppr_ui.py [serie]"""
import json, os, sys, urllib.request
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banc_outils as bo
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
SERIE = sys.argv[1] if len(sys.argv) > 1 else "solo-levelng-ragnarok"
OK, KO = [], []
def check(n, c, d=""):
    (OK if c else KO).append(n); print(("  [OK] " if c else "  [KO] ") + n + (" -- " + str(d) if d else ""), flush=True)
def musiques():
    r = urllib.request.Request("http://127.0.0.1:8190/manga/musiques?serie=" + SERIE, headers={"Authorization": "Bearer " + KEY})
    return [x["nom"] for x in json.load(urllib.request.urlopen(r, timeout=30))["items"]]
AVANT = musiques(); print("morceaux :", AVANT)
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w, h in ((1280, 900), (360, 780)):
        print("=== %d px" % w)
        c = b.new_context(viewport={"width": w, "height": h}, is_mobile=w < 400, has_touch=w < 400); pg = c.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        vus = []
        pg.on("dialog", lambda d: (vus.append(d.message), d.dismiss()))
        pg.goto("http://127.0.0.1:8190/manga#k=" + KEY); pg.wait_for_timeout(2500)
        pg.click('nav button[data-tab="tChap"]'); pg.wait_for_timeout(1500)
        check("version = fichier", pg.inner_text("#verBadge") == "v" + bo.version_app())
        pg.evaluate("(s) => ouvrirSerie(s)", SERIE); pg.wait_for_timeout(1200)
        pg.click("#btnSuivi"); pg.wait_for_timeout(2500)
        n = pg.locator("#profMusListe [data-pm-suppr]").count()
        check("une poubelle par morceau (%d)" % len(AVANT), n == len(AVANT) and n > 0, n)
        pg.click("#profMusListe [data-pm-suppr] >> nth=0"); pg.wait_for_timeout(600)
        check("la confirmation s'affiche et nomme le morceau", vus and AVANT[0] in vus[0], vus[:1])
        check("refusée -> rien n'est supprimé", musiques() == AVANT)
        check("dans l'écran, sans défilement horizontal", pg.evaluate("() => document.documentElement.scrollWidth <= innerWidth + 1"))
        pg.locator("#profMusListe").screenshot(path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "prof_mus_%d.png" % w))
        check("aucune erreur JS", not errs, errs[:2]); c.close()
    b.close()
print("\n%d/%d" % (len(OK), len(OK) + len(KO))); sys.exit(1 if KO else 0)
