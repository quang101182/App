# -*- coding: utf-8 -*-
"""Mesure v3.5.3 : les 3 options du bloc Dialogues (Tons, Encarts, Musique) sur UNE ligne, texte entier, sans debordement,
a 360 / 476 / 704 / 933 px. App reelle 8190 (page substituee si --page), lecture seule (POST interceptes).
Usage : python mesure_options_dialogues.py <serie/ch_N> [--page f.html]"""
import os, sys
from playwright.sync_api import sync_playwright
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
a = sys.argv[1:]; PAGE = None
if "--page" in a:
    i = a.index("--page"); PAGE = open(a[i + 1], encoding="utf-8").read(); del a[i:i + 2]
CH = a[0]; OK = KO = 0
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for L in (360, 476, 704, 933):
        pg = b.new_context(viewport={"width": L, "height": 800}, is_mobile=L < 800, service_workers="block").new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        def route(rt):
            u = rt.request.url.split("#")[0].split("?")[0].rstrip("/")
            if rt.request.method != "GET": return rt.fulfill(status=200, body='{"ok":true}', content_type="application/json")
            if PAGE and u.endswith("/manga"): return rt.fulfill(status=200, body=PAGE, content_type="text/html; charset=utf-8")
            return rt.continue_()
        pg.route("**/*", route)
        pg.goto("http://127.0.0.1:8190/manga/#k=" + KEY); pg.wait_for_timeout(2000)
        pg.evaluate("s => { localStorage.setItem('manga_onglet','tChap'); localStorage.setItem('manga_serie', s); }", CH.split("/")[0])
        pg.reload(); pg.wait_for_timeout(3000)
        pg.evaluate("d => openChap(CHAPS.findIndex(c => c.dir === d))", CH); pg.wait_for_timeout(3000)
        pg.evaluate("() => clOuvrir('dlg')"); pg.wait_for_timeout(2500)
        r = pg.evaluate("""() => ['dlgTons','dlgNarr','dlgMus'].map(id => { const l = $(id).closest('label'), sp = l.querySelector('span'), r = l.getBoundingClientRect();
            return { id, top: Math.round(r.top), vis: !!l.offsetParent, t: sp.textContent, entier: sp.scrollWidth <= sp.clientWidth + 1 }; })""")
        ligne = len({x["top"] for x in r}) == 1 and all(x["vis"] for x in r)
        ok = ligne and all(x["entier"] for x in r) and not pg.evaluate("() => document.documentElement.scrollWidth > document.documentElement.clientWidth") and not errs
        OK += ok; KO += not ok
        print(("  [OK] " if ok else "  [KO] ") + "%d px : une ligne=%s, textes entiers=%s -- %s" % (L, ligne, all(x["entier"] for x in r), [(x["t"], x["top"]) for x in r]), errs[:1])
        if L == 360: pg.locator("#dlgBox .dlg-opts").screenshot(path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "samsung_out", "options_dlg_360.png"))
        pg.close()
    b.close()
print("\nVERDICT : %d/%d" % (OK, OK + KO)); sys.exit(1 if KO else 0)
