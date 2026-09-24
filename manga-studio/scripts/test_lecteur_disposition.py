# -*- coding: utf-8 -*-
"""Banc UI de la DISPOSITION du lecteur (v2.34.0, maquette_ensemble_v1 ecran 5) sur l'APP REELLE, PC 1280 puis tel 360.

Ouvre la narration kimi-fenrir d'OPM 301 (comme test_lecteur_ui.py). Verifie : « ← Fermer » bleu a gauche, titre sur
une ligne, en bas seulement ⏮ ⏸ ⏭ + volume + ⚙ ; le panneau ⚙ (vitesse, sous-titres, karaoke, camera, musique) s'ouvre
PAR-DESSUS l'image (qui garde sa taille), au-dessus des commandes ; une bascule y marche ; Echap ferme le panneau PUIS le
lecteur. Remet la bascule touchee comme avant. Usage : python test_lecteur_disposition.py [port]
"""
import os, sys
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = sys.argv[1] if len(sys.argv) > 1 else "8190"
ICI = os.path.dirname(os.path.abspath(__file__))
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


def vis(pg, sel):
    return pg.eval_on_selector(sel, "e => e.checkVisibility({ visibilityProperty: true }) && e.getBoundingClientRect().width > 0")


def boite(pg, sel):
    return pg.eval_on_selector(sel, "e => { const r = e.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; }")


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True, args=["--autoplay-policy=no-user-gesture-required"])
    for w, h in ((1280, 900), (360, 780)):
        print("=== %d px" % w)
        c = b.new_context(viewport={"width": w, "height": h}, has_touch=(w < 400), is_mobile=(w < 400))
        pg = c.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto("http://127.0.0.1:%s/manga#k=%s" % (PORT, KEY)); pg.wait_for_timeout(3000)
        avant = pg.evaluate("() => localStorage.getItem('manga_serie')")
        pg.evaluate("() => { try { localStorage.removeItem('manga_serie'); } catch {} }")
        pg.click('nav button[data-tab="tChap"]'); pg.wait_for_timeout(1500)
        if pg.is_visible("#btnLibBack"):
            pg.click("#btnLibBack"); pg.wait_for_timeout(300)
        pg.fill("#libRech", ""); pg.type("#libRech", "armure blue", delay=20); pg.wait_for_timeout(1500)
        pg.click("#libTexte [data-rtxt] >> nth=0"); pg.wait_for_timeout(3000)
        i = pg.evaluate("() => NARRS.findIndex(n => n.tag === 'kimi-fenrir')")
        pg.click('#narrRuns [data-ecoute="%d"]' % i); pg.wait_for_timeout(2500)
        check("lecteur ouvert", vis(pg, "#lecteur"))
        f, t = boite(pg, "#lecFermer"), boite(pg, "#lecteur .lec-top")
        check("« ← Fermer » bleu, à gauche", pg.inner_text("#lecFermer").startswith("←") and "retour" in pg.get_attribute("#lecFermer", "class")
              and f[0] - t[0] < 20, (f, t))
        th = pg.eval_on_selector("#lecteur .lec-t", "e => [e.getBoundingClientRect().height, e.scrollWidth > e.clientWidth]")
        check("titre sur UNE ligne (points de suspension si trop long)", th[0] < 26, th)
        bas = pg.eval_on_selector_all("#lecteur .lec-ctl > *", "es => es.filter(e => e.checkVisibility()).map(e => e.id || e.className)")
        check("en bas : ⏮ ⏸ ⏭ + volume + ⚙ seulement", bas == ["lecPrev", "lecPlay", "lecNext", "lec-chk", "lecRegBtn"], bas)
        tops = pg.eval_on_selector_all("#lecteur .lec-ctl > *", "es => [...new Set(es.filter(e => e.checkVisibility()).map(e => Math.round(e.getBoundingClientRect().top + e.getBoundingClientRect().height / 2)))]")
        check("commandes sur une rangée", max(tops) - min(tops) <= 4, tops)
        check("réglages cachés au départ", not vis(pg, "#lecReg") and not vis(pg, "#lecVit"))
        img0 = boite(pg, "#lecteur .lec-scene")
        pg.click("#lecRegBtn"); pg.wait_for_timeout(300)
        check("⚙ ouvre le panneau (vitesse, sous-titres, karaoké, caméra)", all(vis(pg, x) for x in ("#lecReg", "#lecVit", "#lecSousOn", "#lecKarOn", "#lecCamOn")))
        check("l'image garde sa taille (panneau PAR-DESSUS)", boite(pg, "#lecteur .lec-scene") == img0, (img0, boite(pg, "#lecteur .lec-scene")))
        r, ctl = boite(pg, "#lecReg"), boite(pg, "#lecteur .lec-ctl")
        check("panneau juste au-dessus des commandes, dans l'écran", r[3] <= ctl[1] + 1 and r[1] >= 0 and r[0] >= 0 and r[2] <= w + 0.5, (r, ctl))
        sous = pg.evaluate("() => $('lecSousOn').checked")
        pg.click("label.lec-ligne:has(#lecSousOn)"); pg.wait_for_timeout(200)
        check("toucher la ligne « Sous-titres » bascule", pg.evaluate("() => $('lecSousOn').checked") != sous)
        pg.click("label.lec-ligne:has(#lecSousOn)"); pg.wait_for_timeout(200)
        check("… et rebascule (état d'origine remis)", pg.evaluate("() => $('lecSousOn').checked") == sous)
        pg.screenshot(path=os.path.join(ICI, "lecteur_%d.png" % w))
        pg.keyboard.press("Escape"); pg.wait_for_timeout(200)
        check("Échap ferme d'abord le panneau", not vis(pg, "#lecReg") and vis(pg, "#lecteur"))
        pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
        check("… puis le lecteur", not vis(pg, "#lecteur"))
        check("aucune erreur JS", not errs, errs[:2])
        pg.evaluate("a => { a == null ? localStorage.removeItem('manga_serie') : localStorage.setItem('manga_serie', a); }", avant)
        c.close()
    b.close()
print("\nVERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
