# -*- coding: utf-8 -*-
"""Banc v2.57.0 : APPUI LONG sur la bulle verte = panneau « ▶ Tout traiter » ouvert et pre-regle, JAMAIS lance.
APP REELLE (8190), 1280 px puis 360 px. Tout POST est BLOQUE (rien ne peut partir, meme par erreur) et compte.
1. toucher COURT (0,2 s) : rien (Quang : pas de toucher simple, le bouton retour est a cote) ;
2. appui long qui BOUGE (30 px) : rien (c'est un glissement) ;
3. appui long en SERIE : panneau ouvert, portee « pas terminés », « ▶ Lancer » a l'ecran ;
4. appui long en CHAPITRE : panneau ouvert, CE chapitre seul coche ;
5. bibliotheque : un message, pas de panneau ; 6. aucun POST (rien lance), aucune erreur JS.
Usage : python test_appui_long_ui.py [port]
"""
import os, sys
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = sys.argv[1] if len(sys.argv) > 1 else "8190"
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


DOWN = """([typ]) => { const b = $('nfInfo'), r = b.getBoundingClientRect(); window._p = [r.left + r.width / 2, r.top + r.height / 2];
  b.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, pointerType: typ, button: 0, clientX: _p[0], clientY: _p[1] })); }"""
MOVE = """([typ, dx]) => $('nfInfo').dispatchEvent(new PointerEvent('pointermove', { bubbles: true, pointerType: typ, clientX: _p[0] + dx, clientY: _p[1] }))"""
UP = """([typ]) => $('nfInfo').dispatchEvent(new PointerEvent('pointerup', { bubbles: true, pointerType: typ, clientX: _p[0], clientY: _p[1] }))"""

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w, h in ((1280, 900), (360, 780)):
        tel = w < 400; typ = "touch" if tel else "mouse"
        print("=== %d px" % w)
        c = b.new_context(viewport={"width": w, "height": h}, is_mobile=tel, has_touch=tel)
        pg = c.new_page(); errs, posts = [], []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        def route(rt):
            r = rt.request
            if r.method == "POST" and not any(k in r.url for k in ("activite", "costs", "savelog")):
                posts.append(r.url.split("?")[0]); return rt.abort()
            rt.continue_()
        pg.route("**/*", route)
        pg.goto("http://127.0.0.1:%s/manga#k=%s" % (PORT, KEY)); pg.wait_for_timeout(2500)
        pg.evaluate("() => { localStorage.setItem('manga_onglet','tChap'); localStorage.setItem('manga_serie','one-punch-man'); }")
        pg.reload(); pg.wait_for_timeout(4500)
        ouvert = lambda: pg.evaluate("() => !$('suiviBox').hidden")
        def appui(ms, dx=0):
            pg.evaluate(DOWN, [typ])
            if dx: pg.wait_for_timeout(100); pg.evaluate(MOVE, [typ, dx])
            pg.wait_for_timeout(ms); pg.evaluate(UP, [typ]); pg.wait_for_timeout(1800)
        appui(200)
        check("toucher COURT (0,2 s) : rien", not ouvert())
        appui(900, dx=30)
        check("appui long qui BOUGE (30 px) : rien (c'est un glissement)", not ouvert())
        appui(900)
        check("appui long en SÉRIE : panneau « Tout traiter » ouvert", ouvert())
        check("… portée « pas terminés » (jamais « toute la série »)", pg.evaluate("() => LOT_PORTEE") == "restant", pg.evaluate("() => LOT_PORTEE"))
        check("… « ▶ Lancer » à l'écran, pas lancé", pg.evaluate("() => { const r = $('suiviLancer').getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight; }"))
        pg.evaluate("() => { $('suiviBox').hidden = true; }")
        i = pg.evaluate("() => CHAPS.findIndex(c => c.dir === 'one-punch-man/ch_301')")
        pg.evaluate("i => document.querySelector('#chapList [data-chap=\"' + i + '\"]').click()", i); pg.wait_for_timeout(3000)
        appui(900)
        sel = pg.evaluate("() => [LOT_PORTEE, [...LOT_SEL]]")
        check("appui long en CHAPITRE : panneau ouvert, CE chapitre seul coché", ouvert() and sel == ["sel", ["one-punch-man/ch_301"]], sel)
        pg.evaluate("() => { $('suiviBox').hidden = true; $('btnChapClose').click(); $('btnLibBack').click(); }"); pg.wait_for_timeout(1500)
        appui(900)
        check("bibliothèque : pas de panneau (message « ouvre un manga »)", not ouvert() and "ouvre d'abord" in pg.inner_text("#toast"), pg.inner_text("#toast"))
        check("RIEN n'est parti (aucun POST)", not posts, posts[:4])
        check("aucune erreur JS", not errs, errs[:3])
        pg.evaluate("() => localStorage.removeItem('manga_serie')")
        c.close()
    b.close()

print("\nVERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
