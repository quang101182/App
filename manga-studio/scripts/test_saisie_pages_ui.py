# -*- coding: utf-8 -*-
"""Banc v3.3.2 (Quang 27/09 18h37, PC : « des que je tape un chiffre, ca sort le focus de la cellule ») : taper au CLAVIER
« 40 » puis « 45 » dans les champs de / a d'une nouvelle plage du bloc 🎭 -> les deux chiffres arrivent, le curseur reste.
App REELLE 8190, lecture seule. Usage : python test_saisie_pages_ui.py <serie/ch_N> [--ancien f.html]"""
import os, sys
from playwright.sync_api import sync_playwright
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
args = sys.argv[1:]
ANCIEN = None
if "--ancien" in args:
    i = args.index("--ancien"); ANCIEN = open(args[i + 1], encoding="utf-8").read(); del args[i:i + 2]
CH = args[0]
OK, KO = [], []
def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom); print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail)[:150] if detail else ""), flush=True)
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w in (1280, 360):
        ctx = b.new_context(viewport={"width": w, "height": 850}, service_workers="block"); pg = ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        def route(rt):
            u = rt.request.url.split("#")[0].split("?")[0].rstrip("/")
            if rt.request.method != "GET": return rt.fulfill(status=200, body='{"ok":true}', content_type="application/json")
            if ANCIEN and u.endswith("/manga"): return rt.fulfill(status=200, body=ANCIEN, content_type="text/html; charset=utf-8")
            return rt.continue_()
        pg.route("**/*", route)
        pg.goto("http://127.0.0.1:8190/manga/#k=" + KEY); pg.wait_for_timeout(2500)
        pg.evaluate("s => { localStorage.setItem('manga_onglet','tChap'); localStorage.setItem('manga_serie', s); }", CH.split("/")[0]); pg.reload(); pg.wait_for_timeout(3500)
        pg.evaluate("d => openChap(CHAPS.findIndex(c => c.dir === d))", CH); pg.wait_for_timeout(3000)
        pg.evaluate("() => clOuvrir('dlg')"); pg.wait_for_timeout(2500)
        pg.evaluate("() => { const b = document.querySelector('#dplListe [data-dpl=nouv]'); if (b) b.click(); }"); pg.wait_for_timeout(600)
        for fid, val in (("dlgDe", "12"), ("dlgA", "18")):
            pg.click("#" + fid); pg.keyboard.press("Control+A"); pg.keyboard.press("Backspace"); pg.wait_for_timeout(200)
            pg.keyboard.type(val, delay=120); pg.wait_for_timeout(400)
            r = pg.evaluate("f => ({ v: $(f).value, focus: document.activeElement && document.activeElement.id })", fid)
            check("%d px : taper « %s » au clavier dans « %s » -> valeur complete, curseur reste" % (w, val, "de" if fid == "dlgDe" else "à"), r["v"] == val and r["focus"] == fid, r)
        t = pg.evaluate("() => $('dplVerif') ? ($('dlgPreparer').textContent) : ''")
        check("%d px : le libelle suit la saisie (p. 12-18)" % w, "12-18" in t, t)
        check("%d px : 0 erreur JS" % w, not errs, errs[:2])
        ctx.close()
    b.close()
print("\nVERDICT : %d/%d" % (len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
