# -*- coding: utf-8 -*-
"""Banc v3.6.1 : POSITION VERTICALE conservee au retour. App REELLE 8190 (page substituee si --page), LECTURE SEULE : les POST
sont interceptes (rien n'est ecrit dans la bibliotheque de Quang). 1280 puis 360 px.
A. liste des series defilee a mi-hauteur -> ouvrir une serie (clic sur sa carte) -> la serie s'ouvre EN HAUT ;
B. « ← Séries » -> la liste revient a la MEME position (±4 px) ;
C. idem par le bouton retour de la barre flottante (nfAller("retour")) ;
D. page d'une serie a beaucoup de chapitres, defilee -> ouvrir un chapitre -> fermer -> MEME position ;
E. chapitre -> chapitre suivant -> fermer -> toujours la position d'AVANT le 1er chapitre ; 0 erreur JS.
Usage : python test_position_retour_ui.py [--page f.html]"""
import os, sys
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
a = sys.argv[1:]; PAGE = None
if "--page" in a:
    i = a.index("--page"); PAGE = open(a[i + 1], encoding="utf-8").read()
OK, KO = [], []


def check(nom, cond, d=""):
    (OK if cond else KO).append(nom); print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(d)[:150] if d else ""), flush=True)


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w, h in ((1280, 900), (704, 800), (360, 780)):
        print("=== %d px" % w)
        c = b.new_context(viewport={"width": w, "height": h}, is_mobile=w < 400, has_touch=w < 400, service_workers="block")
        pg = c.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        def route(rt):
            r = rt.request
            if r.method == "POST" and not any(k in r.url for k in ("activite", "costs", "fetch_status", "savelog", "source_pages", "sources")):
                return rt.fulfill(status=200, body='{"ok":true}', content_type="application/json")
            if PAGE and r.method == "GET" and r.url.split("#")[0].split("?")[0].rstrip("/").endswith("/manga"):
                return rt.fulfill(status=200, body=PAGE, content_type="text/html; charset=utf-8")
            rt.continue_()
        pg.route("**/*", route)
        pg.goto("http://127.0.0.1:8190/manga#k=" + KEY); pg.wait_for_timeout(2500)
        pg.evaluate("() => { localStorage.setItem('manga_onglet','tChap'); localStorage.removeItem('manga_serie'); }")
        pg.reload(); pg.wait_for_timeout(4500)
        print("  version :", pg.evaluate("() => VERSION"))
        y = lambda: pg.evaluate("() => Math.round(scrollY)")
        top = lambda sel: pg.evaluate("s => { const e = document.querySelector(s); return e ? Math.round(e.getBoundingClientRect().top) : null; }", sel)
        MILIEU = """sel => { const t = innerHeight / 2; let best = null, d = 1e9;
          document.querySelectorAll(sel).forEach(x => { const r = x.getBoundingClientRect(); const e = Math.abs(r.top - t);
            if (r.height && e < d){ d = e; best = x; } }); return best ? (best.dataset.serie || best.dataset.chap) : null; }"""
        haut = pg.evaluate("() => document.documentElement.scrollHeight - innerHeight")
        for tour, retour in (("B", "() => $('btnLibBack').click()"), ("C", "() => nfAller('retour')")):
            if haut < 200: print("  (liste des series sans defilement a cette largeur : %d px) -- B/C non applicables" % haut); break
            pg.evaluate("v => scrollTo(0, v)", int(haut * 0.6)); pg.wait_for_timeout(400)
            slug = pg.evaluate(MILIEU, "#chapList [data-serie]"); sel = '#chapList [data-serie="%s"]' % slug; t0 = top(sel)
            pg.evaluate("s => document.querySelector(s).click()", sel); pg.wait_for_timeout(900)
            if tour == "B": check("A. la série s'ouvre en haut (y=%d)" % y(), y() < 50 and pg.evaluate("() => LIB_SERIE") == slug, slug)
            pg.evaluate("() => scrollTo(0, 400)"); pg.wait_for_timeout(300)      # on se promene dans la page de la serie
            pg.evaluate(retour); pg.wait_for_timeout(900)
            check("%s. retour -> la carte touchée au même endroit de l'écran (%s -> %s)" % (tour, t0, top(sel)), t0 is not None and abs(top(sel) - t0) <= 4, slug)
        slug = pg.evaluate("() => { const n = {}; CHAPS.forEach(c => { const s = serieDe(c.dir); n[s] = (n[s] || 0) + 1; }); return Object.keys(n).sort((a, b) => n[b] - n[a])[0]; }")
        pg.evaluate("s => ouvrirSerie(s)", slug); pg.wait_for_timeout(1200)
        haut = pg.evaluate("() => document.documentElement.scrollHeight - innerHeight")
        for tour in ("D", "E"):
            pg.evaluate("v => scrollTo(0, v)", int(haut * (0.5 if tour == "D" else 0.3))); pg.wait_for_timeout(400)
            k = pg.evaluate(MILIEU, "#chapList [data-chap]"); sel = '#chapList [data-chap="%s"]' % k; t0 = top(sel)
            pg.evaluate("s => document.querySelector(s).click()", sel); pg.wait_for_timeout(2500)
            ouvert = pg.evaluate("() => !$('chapDetail').hidden"); v = None
            if tour == "E":
                v = pg.evaluate("() => { const b = $('chapNext'); if (b && !b.hidden && !b.disabled){ b.click(); return true; } return false; }"); pg.wait_for_timeout(2500)
            pg.evaluate("() => $('btnChapClose').click()"); pg.wait_for_timeout(800)
            nom = "D. chapitre fermé" if tour == "D" else "E. chapitre -> suivant (%s) -> fermé" % v
            check("%s -> le chapitre touché au même endroit de l'écran (%s -> %s)" % (nom, t0, top(sel)), ouvert and abs(top(sel) - t0) <= 4, slug)
        check("0 erreur JS", not errs, errs[:2])
        c.close()
    b.close()
print("\nVERDICT : %d/%d" % (len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
