# -*- coding: utf-8 -*-
"""Banc v3.5.6 : page d'une SERIE -- ‹ / › de la barre du bas et glissements gauche / droite = serie precedente / suivante,
dans l'ordre de la bibliotheque tel qu'affiche (fige). APP REELLE 8190 (page substituee si --page), LECTURE SEULE (tout POST
bloque sauf lectures d'etat). 1280 px puis 360 px tactile.
Controles : ‹ › actifs au milieu de la liste, info-bulle = nom de la voisine ; › = suivante (+ message) ; ‹ = retour ; l'ordre ne
bouge pas en naviguant ; 1re serie : ‹ grise ; derniere : › grise ; telephone : glisser a droite = suivante, a gauche = precedente ;
glissement court = rien ; 0 erreur JS, 0 ecriture.
Usage : python test_series_voisines_ui.py [--page f.html]"""
import os, sys
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
a = sys.argv[1:]; PAGE = None
if "--page" in a:
    i = a.index("--page"); PAGE = open(a[i + 1], encoding="utf-8").read()
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail)[:160] if detail else ""), flush=True)


GLISSE = """([dx]) => { const n = $('navFlot'), r = n.getBoundingClientRect(), y = r.top + r.height / 2, x0 = r.left + r.width / 2;
  const t = x => new Touch({ identifier: 1, target: n, clientX: x, clientY: y });
  n.dispatchEvent(new TouchEvent('touchstart', { touches: [t(x0)], changedTouches: [t(x0)], bubbles: true }));
  for (let k = 1; k <= 6; k++) n.dispatchEvent(new TouchEvent('touchmove', { touches: [t(x0 + dx * k / 6)], changedTouches: [t(x0 + dx * k / 6)], bubbles: true }));
  n.dispatchEvent(new TouchEvent('touchend', { touches: [], changedTouches: [t(x0 + dx)], bubbles: true })); }"""

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w, h in ((1280, 900), (360, 780)):
        tel = w < 400
        print("=== %d px" % w)
        c = b.new_context(viewport={"width": w, "height": h}, is_mobile=tel, has_touch=tel, service_workers="block")
        pg = c.new_page(); errs, ecrit = [], []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        def route(rt):
            r = rt.request
            if r.method == "POST" and not any(k in r.url for k in ("activite", "costs", "fetch_status", "savelog")):
                ecrit.append(r.url); return rt.fulfill(status=200, body='{"ok":true}', content_type="application/json")
            if PAGE and r.method == "GET" and r.url.split("#")[0].split("?")[0].rstrip("/").endswith("/manga"):
                return rt.fulfill(status=200, body=PAGE, content_type="text/html; charset=utf-8")
            rt.continue_()
        pg.route("**/*", route)
        pg.goto("http://127.0.0.1:8190/manga#k=" + KEY); pg.wait_for_timeout(2500)
        pg.evaluate("() => { localStorage.setItem('manga_onglet','tChap'); localStorage.removeItem('manga_serie'); }")
        pg.reload(); pg.wait_for_timeout(4500)
        if w == 1280: print("     version :", pg.evaluate("() => VERSION"))
        ordre = pg.evaluate("() => LIB_ORDRE.slice()")
        check("liste affichée : ordre retenu (%d séries)" % len(ordre), len(ordre) >= 3, ordre[:4])
        m = ordre[1]
        pg.evaluate("s => document.querySelector('.serie-item[data-serie=\"' + s + '\"]').click()", m); pg.wait_for_timeout(2500)
        titre = lambda s: pg.evaluate("s => (CHAPS.find(x => (x.slug || x.dir.split('/')[0]) === s) || {}).title || s", s)
        e = pg.evaluate("() => ({ p: $('nfPrev').disabled, s: $('nfSuiv').disabled, tp: $('nfPrev').title, ts: $('nfSuiv').title })")
        check("série au milieu : ‹ et › actifs, info-bulles = noms des voisines", not e["p"] and not e["s"] and titre(ordre[0]) in e["tp"] and titre(ordre[2]) in e["ts"], e)
        pg.evaluate("() => $('nfSuiv').click()"); pg.wait_for_timeout(2000)
        check("› = série SUIVANTE", pg.evaluate("() => LIB_SERIE") == ordre[2], pg.evaluate("() => LIB_SERIE"))
        pg.evaluate("() => $('nfPrev').click()"); pg.wait_for_timeout(2000)
        check("‹ = série PRÉCÉDENTE (retour)", pg.evaluate("() => LIB_SERIE") == m)
        check("l'ordre n'a PAS bougé en naviguant (figé)", pg.evaluate("() => LIB_ORDRE.slice()") == ordre)
        pg.evaluate("() => $('nfPrev').click()"); pg.wait_for_timeout(2000)
        check("1re série : ‹ grisé", pg.evaluate("() => LIB_SERIE") == ordre[0] and pg.evaluate("() => $('nfPrev').disabled"))
        pg.evaluate("s => ouvrirSerie(s)", ordre[-1]); pg.wait_for_timeout(1500); pg.evaluate("() => nfMaj()")
        check("dernière série : › grisé", pg.evaluate("() => $('nfSuiv').disabled"))
        if tel:
            pg.evaluate("s => ouvrirSerie(s)", m); pg.wait_for_timeout(1500); pg.evaluate("() => nfMaj()")
            pg.evaluate("() => scrollTo(0, document.documentElement.scrollHeight)"); pg.wait_for_timeout(500)
            pg.evaluate(GLISSE, [25]); pg.wait_for_timeout(1200)
            check("glissement COURT : rien", pg.evaluate("() => LIB_SERIE") == m)
            pg.evaluate(GLISSE, [140]); pg.wait_for_timeout(2000)
            check("glisser à DROITE = série SUIVANTE", pg.evaluate("() => LIB_SERIE") == ordre[2], pg.evaluate("() => LIB_SERIE"))
            pg.evaluate("() => scrollTo(0, document.documentElement.scrollHeight)"); pg.wait_for_timeout(500)
            pg.evaluate(GLISSE, [-140]); pg.wait_for_timeout(2000)
            check("glisser à GAUCHE = série PRÉCÉDENTE", pg.evaluate("() => LIB_SERIE") == m, pg.evaluate("() => LIB_SERIE"))
            r = pg.evaluate("() => [innerWidth, Math.round($('navFlot').getBoundingClientRect().bottom) <= innerHeight]")
            check("affichage intact, barre dans l'écran", r == [360, True], r)
        pg.evaluate("() => localStorage.removeItem('manga_serie')")
        check("0 erreur JS", not errs, errs[:2])
        check("0 écriture (POST bloqués)", not ecrit, ecrit[:3])
        c.close()
    b.close()
print("\nVERDICT : %d/%d" % (len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
