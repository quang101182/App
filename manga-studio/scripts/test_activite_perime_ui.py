# -*- coding: utf-8 -*-
"""Banc UI v3.6.3 : l'activite qui ne se lit plus est DITE perimee (Quang 03/10 : pastille figee ~2 h sur une capture finie).
1. serveur REEL : une capture fantome (etat de la capture d'ecran de Quang) disparait au 1er tour ;
2. route /manga/activite en panne (500 puis requete coupee) : 1 echec = rien ne change ; 2 echecs = pastille « ⚠ pas a jour »,
   classe .perime, bandeau dans le panneau, ligne au journal ; la tache figee reste listee (on ne l'invente pas finie) ;
3. la route revient : tout redevient normal, ligne « repond de nouveau » au journal ;
4. a 360 et 1280 px : la page ne deborde pas et la hauteur de l'en-tete ne bouge pas en etat perime.
Usage : python test_activite_perime_ui.py [port]
"""
import json, os, sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
CAP = {"type": "capture", "d": "serie-banc/ch_1", "titre": "Serie Banc", "chapitre": "1", "pages": 29,
       "fait": 0, "dernier_paru": True, "etape": "capture"}
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w in (1280, 360):
        print("=== %d px" % w)
        c = b.new_context(viewport={"width": w, "height": 800}, is_mobile=w < 500, has_touch=w < 500)
        pg = c.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto("http://127.0.0.1:%d/manga#k=" % PORT + KEY); pg.wait_for_timeout(3500)
        check("version >= 3.6.3 servie", tuple(map(int, pg.evaluate("() => VERSION").split("."))) >= (3, 6, 3), pg.evaluate("() => VERSION"))
        injecte = ("c => { clearTimeout(ACT.timer); ACT.items = [c]; ACT.vague = { debut: Date.now() - 3600e3, faits: 0, lotFaits: 0,"
                   " durees: {} }; ACT.maj = Date.now() - 125 * 60e3; ACT.panne = 0; actRendre(); }")
        # --- 1. reel
        pg.evaluate(injecte, CAP)
        pg.evaluate("() => actRafraichir()"); pg.wait_for_timeout(1500)
        check("reel : la capture fantome disparait au 1er tour", pg.evaluate("() => ACT.items.length") == 0
              and "Serie Banc ch.1 p." not in pg.inner_text("#actTxt"), pg.inner_text("#actTxt"))
        h0 = pg.evaluate("() => document.querySelector('header').getBoundingClientRect().height")
        # --- 2. panne
        etat = {"mode": "500"}
        def act(route):
            if etat["mode"] == "500": route.fulfill(status=500, body="")
            elif etat["mode"] == "coupe": route.abort("connectionreset")
            else: route.continue_()
        pg.route(lambda u: u.split("?")[0].endswith("/manga/activite"), act)
        pg.evaluate(injecte, CAP)
        pg.evaluate("() => { $('actPanel').hidden = false; }")
        pg.evaluate("() => actRafraichir()"); pg.wait_for_timeout(800)
        check("1 echec : pas encore perime", not pg.evaluate("() => $('hdrAct').classList.contains('perime')")
              and "pas à jour" not in pg.inner_text("#actTxt"), pg.inner_text("#actTxt"))
        etat["mode"] = "coupe"
        pg.evaluate("() => actRafraichir()"); pg.wait_for_timeout(800)
        txt = pg.inner_text("#actTxt")
        check("2 echecs : pastille « ⚠ pas à jour depuis 2 h 05 »", pg.evaluate("() => $('hdrAct').classList.contains('perime')")
              and "pas à jour depuis 2 h 05" in txt, txt)
        check("la tache figee reste nommee (pas inventee finie)", "Serie Banc" in txt, txt)
        check("bandeau dans le panneau", pg.is_visible("#actListe .act-perime"),
              pg.inner_text("#actListe .act-perime") if pg.locator("#actListe .act-perime").count() else "absent")
        check("info-bulle explicite", "ne répond plus" in pg.get_attribute("#hdrAct", "title"))
        journal = pg.evaluate("() => (window.LOGS || []).map(x => x.msg || x).join('\\n')") or ""
        h1 = pg.evaluate("() => document.querySelector('header').getBoundingClientRect().height")
        check("hauteur de l'en-tete inchangee en perime", h1 == h0, (h0, h1))
        check("page sans debordement horizontal", pg.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth"))
        bb = pg.locator("#actPanel").bounding_box()
        check("panneau dans l'ecran", bb["x"] >= 0 and bb["x"] + bb["width"] <= w + 0.5, bb)
        if w == 360:
            pg.screenshot(path=os.path.join(os.environ.get("TEMP", "."), "activite_perime_360.png"))
        # --- 3. retour
        etat["mode"] = "ok"
        pg.evaluate("() => actRafraichir()"); pg.wait_for_timeout(1200)
        check("retour : plus perime, panne remise a 0", not pg.evaluate("() => $('hdrAct').classList.contains('perime')")
              and pg.evaluate("() => ACT.panne") == 0 and pg.locator("#actListe .act-perime").count() == 0, pg.inner_text("#actTxt"))
        check("aucune erreur JS", not errs, errs)
        c.close()
    b.close()
print("\n%d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
