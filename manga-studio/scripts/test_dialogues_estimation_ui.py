# -*- coding: utf-8 -*-
"""Banc v2.81.4 : l'estimation de PREPARATION des Dialogues suit la portee (Quang 27/09 01:29 : « 4,23 $ » affiches pour
3 pages d'un chapitre de 846). App reelle 8190, page servie = le fichier donne (defaut : manga_studio.html). 0 appel paye.
Usage : python test_dialogues_estimation_ui.py [html] [serie] [chapitre]    (html = un .bak ancien -> doit sortir ROUGE)"""
import os, re, sys
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
HTML = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "manga_studio.html")
SERIE = sys.argv[2] if len(sys.argv) > 2 else "solo-leveling"
CH = sys.argv[3] if len(sys.argv) > 3 else "ch_9"
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PAGE = open(HTML, encoding="utf-8").read()
OK, KO = [], []
def check(n, c, d=""):
    (OK if c else KO).append(n); print(("  [OK] " if c else "  [KO] ") + n + (" -- " + str(d)[:160] if d else ""))
def usd(t):
    m = re.search(r"≈\s*([\d.,]+)\s*\$\s*préparation", t); return float(m.group(1).replace(",", ".")) if m else None
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w in (360, 1280):
        print("=== %d px" % w)
        pg = b.new_page(viewport={"width": w, "height": 850}); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.route("**/*", lambda rt: rt.fulfill(status=200, content_type="text/html; charset=utf-8", body=PAGE)
                 if rt.request.method == "GET" and rt.request.url.split("#")[0].split("?")[0].rstrip("/").endswith("/manga") else rt.continue_())
        pg.goto("http://127.0.0.1:8190/manga#k=" + KEY); pg.wait_for_timeout(3500)
        pg.evaluate("s => localStorage.setItem('manga_serie', s)", SERIE)
        i = pg.evaluate("d => CHAPS.findIndex(c => c.dir === d)", SERIE + "/" + CH)
        pg.evaluate("i => openChap(i)", i); pg.wait_for_timeout(3500)
        n = pg.evaluate("() => CHAP_PAGES")
        if pg.evaluate("() => !!(DLG.e && DLG.e.doc)"):
            print("  (chapitre deja prepare : estimation de preparation non affichee, banc sans objet)"); continue
        chap = usd(pg.evaluate("() => $('dlgEtat').textContent"))
        check("ce chapitre : ~0,004 $ x %d pages" % n, chap is not None and abs(chap - 0.004 * n) < 0.02, chap)
        tete0 = usd(pg.evaluate("() => document.querySelector('#dlgBox .cl-tete').textContent"))
        pg.click("#dlgBox .cl-chev"); pg.wait_for_timeout(400)
        pg.click("#dlgBox .dlg-p[data-portee=pages]")
        pg.fill("#dlgDe", "121"); pg.fill("#dlgA", "123"); pg.wait_for_timeout(400)
        pag = usd(pg.evaluate("() => $('dlgEtat').textContent"))
        check("des pages 121 a 123 : ~0,012 $ (3 pages), recalcule a la frappe", pag is not None and pag <= 0.02, pag)
        tete = usd(pg.evaluate("() => document.querySelector('#dlgBox .cl-tete').textContent"))
        check("la ligne repliee suit (chapitre puis 3 pages)", tete0 == chap and tete is not None and tete <= 0.02, (tete0, tete))
        pg.fill("#dlgA", "99999"); pg.wait_for_timeout(300)
        bor = usd(pg.evaluate("() => $('dlgEtat').textContent"))
        check("borne : jamais plus que le chapitre", bor is not None and bor <= 0.004 * n + 0.01, bor)
        pg.click("#dlgBox .dlg-p[data-portee=lot]", position={"x": 8, "y": 8}); pg.wait_for_timeout(300)
        check("plusieurs chapitres : pas de chiffre invente", usd(pg.evaluate("() => $('dlgEtat').textContent")) is None)
        check("0 erreur JS", not errs, errs)
print("VERDICT : %d OK / %d KO" % (len(OK), len(KO)))
