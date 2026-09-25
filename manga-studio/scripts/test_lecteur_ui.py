# -*- coding: utf-8 -*-
"""Banc UI v1.83.0 sur l'APP REELLE : barre de TEMPS du lecteur (clic + glisse, PC et doigt) et recherche dans
le TEXTE des narrations. Lit la narration kimi-fenrir d'OPM 301 (15 pages avec voix). Verdict chiffre en sortie.
Usage : python test_lecteur_ui.py
"""
import os, sys
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True, args=["--autoplay-policy=no-user-gesture-required"])
    for w, h in ((1280, 900), (360, 780)):
        print("=== %d px" % w)
        c = b.new_context(viewport={"width": w, "height": h}, has_touch=(w < 400), is_mobile=(w < 400))
        pg = c.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto("http://127.0.0.1:8190/manga#k=" + KEY); pg.wait_for_timeout(3000)
        pg.evaluate("() => { try { localStorage.removeItem('manga_serie'); } catch {} }")
        pg.click('nav button[data-tab="tChap"]'); pg.wait_for_timeout(1500)
        if pg.is_visible("#btnLibBack"):
            pg.click("#btnLibBack"); pg.wait_for_timeout(300)
        # --- recherche dans le texte des narrations
        pg.fill("#libRech", ""); pg.type("#libRech", "armure blue", delay=20); pg.wait_for_timeout(1500)
        res = pg.inner_text("#libTexte") if pg.is_visible("#libTexte") else ""
        check("« armure blue » -> OPM ch.301 dans les narrations", "301" in res and "armure" in res.lower(), res[:120].replace("\n", " | "))
        pg.click("#libTexte [data-rtxt] >> nth=0"); pg.wait_for_timeout(3000)
        check("clic sur le resultat -> le chapitre 301 s'ouvre", pg.is_visible("#chapDetail") and "301" in pg.inner_text("#chapTitle"))
        # --- lecteur : barre de temps
        pg.evaluate("() => clOuvrir('narr')"); pg.wait_for_timeout(300)   # v2.60.0 : blocs replies par defaut
        i = pg.evaluate("() => NARRS.findIndex(n => n.tag === 'kimi-fenrir')")
        pg.click('#narrRuns [data-ecoute="%d"]' % i); pg.wait_for_timeout(2500)
        tot = pg.inner_text("#lecTemps")
        check("la barre affiche le temps (x:xx / y:yy)", " / " in tot, tot)
        bb = pg.locator("#lecBar").bounding_box()
        y = bb["y"] + bb["height"] / 2
        if w > 400:
            pg.mouse.click(bb["x"] + bb["width"] * 0.6, y); pg.wait_for_timeout(1500)
        else:
            cdp = c.new_cdp_session(pg)
            for typ, x in (("touchStart", 0.2), ("touchMove", 0.4), ("touchMove", 0.6), ("touchEnd", None)):
                cdp.send("Input.dispatchTouchEvent", {"type": typ, "touchPoints": [] if x is None else [{"x": bb["x"] + bb["width"] * x, "y": y}]})
                pg.wait_for_timeout(120)
            pg.wait_for_timeout(1500)
        etat = pg.evaluate("() => ({i: LEC.i, n: LEC.n.pages.length, t: $('lecAudio').currentTime, "
                           "pct: parseFloat($('lecProg').style.width), ok: LEC.n.pages.slice(0, LEC.i).reduce((s, p) => s + dureePage(p), 0) "
                           "/ LEC.n.pages.reduce((s, p) => s + dureePage(p), 0)})")
        check("clic / glisse a 60 % -> on saute vers 60 % du chapitre", 50 <= etat["pct"] <= 70 and etat["i"] >= 6, etat)
        # point vise dans la page = 60 % du chapitre - duree des pages d'avant ; l'audio a JOUE depuis (+ ~1,5 s)
        vise = pg.evaluate("() => { const tot = LEC.n.pages.reduce((s, p) => s + dureePage(p), 0); "
                           "return 0.6 * tot - LEC.n.pages.slice(0, LEC.i).reduce((s, p) => s + dureePage(p), 0); }")
        check("la lecture reprend au POINT VISE dans la page (pas au debut)", etat["t"] >= vise - 0.3,
              "lu %.2f s, vise %.2f s" % (etat["t"], vise))
        # revenir au debut par la barre
        if w > 400:
            pg.mouse.click(bb["x"] + 2, y); pg.wait_for_timeout(1500)
            check("clic tout a gauche -> page 1", pg.evaluate("() => LEC.i") == 0)
        pg.click("#lecFermer")
        check("aucune erreur JS", not errs, errs[:2])
        c.close()
    b.close()
print("\n=== VERDICT : %d/%d" % (len(OK), len(OK) + len(KO)) + ("" if not KO else "  ECHECS : " + ", ".join(KO)))
sys.exit(1 if KO else 0)
