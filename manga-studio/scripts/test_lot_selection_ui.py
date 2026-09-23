# -*- coding: utf-8 -*-
"""Banc UI v2.7.3 : « Tout traiter » -- ☑ Tout / ☐ Rien / plage ch. X a Y (Quang 23/09 19h41).
Le banc lit le plan de la serie (/manga/suivi) et verifie que la selection affichee est EXACTEMENT celle attendue.
Ne lance RIEN (aucun clic sur « Lancer »). PC 1280 px + telephone 360 px.  Usage : python test_lot_selection_ui.py [port] [serie]
"""
import json, os, sys, urllib.parse, urllib.request
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banc_outils as bo

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
SERIE = sys.argv[2] if len(sys.argv) > 2 else "one-punch-man"
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""), flush=True)


r = urllib.request.Request("http://127.0.0.1:%d/manga/suivi?serie=%s" % (PORT, urllib.parse.quote(SERIE)),
                           headers={"Authorization": "Bearer " + KEY})
PLAN = json.load(urllib.request.urlopen(r, timeout=60))["plan"]
TOUS = [x["d"] for x in PLAN]
nums = sorted(float(x["num"]) for x in PLAN)
LO, HI = nums[len(nums) // 3], nums[2 * len(nums) // 3]
PLAGE = [x["d"] for x in PLAN if LO <= float(x["num"]) <= HI]
print("serie %s : %d chapitres ; plage %g -> %g = %d" % (SERIE, len(TOUS), LO, HI, len(PLAGE)))
sel = "() => [...document.querySelectorAll('#lotPuces .lot-puce.sel')].map(b => b.dataset.d)"
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w, h in ((1280, 900), (360, 780)):
        print("=== %d px" % w)
        c = b.new_context(viewport={"width": w, "height": h}, is_mobile=w < 400, has_touch=w < 400)
        pg = c.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto("http://127.0.0.1:%d/manga#k=%s" % (PORT, KEY)); pg.wait_for_timeout(2500)
        pg.click('nav button[data-tab="tChap"]'); pg.wait_for_timeout(1500)
        check("version affichee = celle du fichier", pg.inner_text("#verBadge") == "v" + bo.version_app())
        pg.evaluate("(s) => ouvrirSerie(s)", SERIE); pg.wait_for_timeout(1500)
        pg.click("#btnSuivi"); pg.wait_for_timeout(2500)
        check("les 3 boutons sont visibles", all(pg.is_visible(x) for x in ("#lotTout", "#lotRien", "#lotPlage")))
        pg.click("#lotRien"); pg.wait_for_timeout(250)
        check("☐ Rien : aucun chapitre sélectionné", pg.evaluate(sel) == [])
        check("☐ Rien : « Lancer » désactivé", pg.is_disabled("#suiviLancer"))
        check("☐ Rien : compteur « 0 / %d »" % len(TOUS), pg.inner_text("#lotCompte").startswith("0 / %d" % len(TOUS)))
        check("mode « ma sélection » actif", pg.get_attribute("#lotPortee [data-p='sel']", "class") and "on" in pg.get_attribute("#lotPortee [data-p='sel']", "class"))
        pg.click("#lotTout"); pg.wait_for_timeout(250)
        check("☑ Tout : les %d chapitres" % len(TOUS), sorted(pg.evaluate(sel)) == sorted(TOUS))
        check("☑ Tout : compteur « %d / %d »" % (len(TOUS), len(TOUS)), pg.inner_text("#lotCompte").startswith("%d / %d" % (len(TOUS), len(TOUS))))
        pg.fill("#lotDe", ("%g" % LO).replace(".", ",")); pg.fill("#lotA", "%g" % HI); pg.click("#lotPlage"); pg.wait_for_timeout(250)
        check("plage ch. %g à %g : exactement %d chapitres" % (LO, HI, len(PLAGE)), sorted(pg.evaluate(sel)) == sorted(PLAGE), len(pg.evaluate(sel)))
        premier = pg.evaluate(sel)[0]
        pg.click("#lotPuces .lot-puce.sel >> nth=0"); pg.wait_for_timeout(200)
        check("puis toucher un chapitre le retire (ajustement au doigt)", premier not in pg.evaluate(sel) and len(pg.evaluate(sel)) == len(PLAGE) - 1)
        check("pas de défilement horizontal", pg.evaluate("() => document.documentElement.scrollWidth <= innerWidth + 1"))
        pg.locator("#lotSelbar").screenshot(path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "lot_sel_%d.png" % w))
        check("aucune erreur JS", not errs, errs[:2])
        c.close()
    b.close()
print("\n%d/%d" % (len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
