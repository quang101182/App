# -*- coding: utf-8 -*-
"""Banc UI v1.88.0 : cellule d'ACTIVITE de l'en-tete (demande Quang 22/09 05h12).
1. la HAUTEUR de l'en-tete ne depasse pas celle de v1.87 (mesuree avant : 43 / 75,5 / 94,5 / 94,5 px a
   1280 / 412 / 360 / 320) et NE BOUGE PAS entre « rien en cours », « en cours » et panneau ouvert ;
2. donnees REELLES : ce que dit /manga/activite est ce que montre la cellule ;
3. transitions (reponses simulees : 2 taches -> 1 -> 0) : « +1 », toast de fin, « Termine pendant cette
   session », etat vert, clic sur une tache = ouverture du chapitre.
Usage : python test_activite_ui.py [port]
"""
import json, os, sys, urllib.request
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
REF = {1280: 43, 412: 75.5, 360: 94.5, 320: 94.5}
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


reel = json.load(urllib.request.urlopen(urllib.request.Request(
    "http://127.0.0.1:%d/manga/activite" % PORT, headers={"Authorization": "Bearer " + KEY}), timeout=30))
print("activite reelle :", [(x["type"], x.get("titre"), x.get("fait"), x.get("total")) for x in reel["items"]])
N1 = {"type": "narration", "d": "claymore/ch_1", "titre": "Claymore", "chapitre": "1", "tag": "kimi-charon", "etape": "vision", "fait": 12, "total": 62}
T1 = {"type": "traduction", "d": "one-punch-man/ch_301", "titre": "One Punch Man", "chapitre": "301", "langue": "fr", "fait": 3, "total": 19}
HAUT = "() => document.querySelector('header').getBoundingClientRect().height"

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w in (1280, 412, 360, 320):
        print("=== %d px" % w)
        c = b.new_context(viewport={"width": w, "height": 800}, is_mobile=w < 500, has_touch=w < 500)
        pg = c.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        etat = {"items": []}
        pg.goto("http://127.0.0.1:%d/manga#k=" % PORT + KEY); pg.wait_for_timeout(3500)
        # --- donnees reelles
        txt = pg.inner_text("#actTxt")
        if reel["items"]:
            x = reel["items"][0]
            check("reel : la cellule nomme la tache en cours", pg.evaluate("() => $('hdrAct').classList.contains('on')") and x["titre"] in txt, txt)
        else:
            check("reel : rien en cours -> gris « Rien en cours »", txt == "Rien en cours", txt)
        # --- simulation des transitions
        pg.route("**/manga/activite*", lambda r: r.fulfill(status=200, content_type="application/json",
                                                           body=json.dumps({"items": etat["items"], "t": 0})))
        etat["items"] = []
        pg.evaluate("() => { ACT.items = []; ACT.finis = []; }")       # on repart d'un etat propre (le reel ne doit pas « finir » ici)
        pg.evaluate("() => actRafraichir()"); pg.wait_for_timeout(400)
        h0 = pg.evaluate(HAUT)
        check("repos : gris, « Rien en cours »", pg.inner_text("#actTxt") == "Rien en cours" and not pg.evaluate("() => $('hdrAct').classList.contains('on')"))
        check("hauteur de l'en-tete <= v1.87 (%s px)" % REF[w], h0 <= REF[w] + 0.5, h0)
        etat["items"] = [N1, T1]
        pg.evaluate("() => actRafraichir()"); pg.wait_for_timeout(400)
        h1 = pg.evaluate(HAUT)
        check("2 taches : allumee, 1re nommee + « +1 »", "Claymore" in pg.inner_text("#actTxt") and pg.inner_text("#actN") == "+1", pg.inner_text("#hdrAct"))
        check("la hauteur ne bouge pas quand ca travaille", h1 == h0, (h0, h1))
        bb = pg.locator("#hdrAct").bounding_box()
        check("cellule dans l'ecran, pas de debordement", bb["x"] >= 0 and bb["x"] + bb["width"] <= w
              and pg.evaluate("() => document.documentElement.scrollWidth - innerWidth") <= 0, bb)
        pg.click("#hdrAct"); pg.wait_for_timeout(500)
        n = pg.locator("#actListe .act-it").count()
        check("clic : panneau avec les 2 taches et leurs barres", n == 2 and pg.locator("#actListe .act-bar").count() == 2, n)
        check("panneau superpose : la hauteur ne bouge pas", pg.evaluate(HAUT) == h0)
        pp = pg.locator("#actPanel").bounding_box()
        check("panneau entierement dans l'ecran", pp["x"] >= 0 and pp["x"] + pp["width"] <= w, pp)
        hb = pg.evaluate("() => document.querySelector('header').getBoundingClientRect().bottom")
        check("panneau SOUS l'en-tete (ne cache pas la cellule)", pp["y"] >= hb, (pp["y"], hb))
        pg.screenshot(path=os.path.join(os.environ.get("TEMP", "."), "act_ui_%d.png" % w))
        etat["items"] = [T1]
        pg.evaluate("() => actRafraichir()"); pg.wait_for_timeout(500)
        check("une tache finit : toast + « Termine pendant cette session »",
              "Narration finie" in pg.inner_text("#toast") and "Claymore" in pg.inner_text("#actFinis"), pg.inner_text("#toast"))
        etat["items"] = []
        pg.evaluate("() => actRafraichir()"); pg.wait_for_timeout(500)
        check("tout fini : etat vert « ✓ … finie », hauteur inchangee",
              pg.evaluate("() => $('hdrAct').classList.contains('fini')") and pg.inner_text("#actTxt").startswith("✓") and pg.evaluate(HAUT) == h0,
              pg.inner_text("#actTxt"))
        pg.click("#actFinis [data-fini] >> nth=-1"); pg.wait_for_timeout(3500)   # la plus ancienne = la narration Claymore
        check("clic sur une tache -> le chapitre s'ouvre", pg.is_hidden("#actPanel") and pg.is_visible("#chapDetail")
              and "claymore — chapitre 1" in pg.inner_text("#chapTitle").lower(), pg.inner_text("#chapTitle"))
        pg.click("#hdrAct"); pg.wait_for_timeout(300); pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
        check("Echap ferme le panneau", pg.is_hidden("#actPanel"))
        check("aucune erreur JS", not errs, errs[:2])
        c.close()
    b.close()
print("\n=== VERDICT : %d/%d" % (len(OK), len(OK) + len(KO)) + ("" if not KO else "  ECHECS : " + ", ".join(KO)))
sys.exit(1 if KO else 0)
