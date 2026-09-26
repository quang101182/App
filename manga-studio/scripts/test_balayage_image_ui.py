# -*- coding: utf-8 -*-
"""Banc v2.72.0 : VISIONNEUSE -- balayer L'IMAGE au doigt. Vers la DROITE = page suivante, vers la gauche = precedente
(meme sens que la barre ; Quang 26/09 12h26). Zoomee, le meme geste DEPLACE l'image (ne tourne pas la page) ; geste vertical
= rien. Vrais evenements tactiles (CDP Input.dispatchTouchEvent). APP REELLE, lecture seule. 360 et 1280 px.
Usage : python test_balayage_image_ui.py [port] [serie] [--mutation]   (--mutation : ancien sens servi -> doit sortir ROUGE)
"""
import os, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
MUT = "--mutation" in sys.argv; sys.argv = [a for a in sys.argv if a != "--mutation"]
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
SERIE = sys.argv[2] if len(sys.argv) > 2 else "one-punch-man"
OK, KO = [], []
def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail)[:200] if detail else ""), flush=True)
def saboter(route):
    r = route.fetch(); t = r.text(); a = "lbShow(LB + (dx > 0 ? 1 : -1));   // v2.72.0"
    assert a in t, "ancre de sabotage introuvable"
    route.fulfill(response=r, body=t.replace(a, "lbShow(LB + (dx < 0 ? 1 : -1));   // v2.72.0"))

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w, h in (((360, 780),) if MUT else ((360, 780), (1280, 900))):
        print("== %d px" % w)
        c = b.new_context(viewport={"width": w, "height": h}, is_mobile=w < 500, has_touch=True)
        pg = c.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        if MUT: pg.route("**/manga", saboter)
        pg.goto("http://127.0.0.1:%d/manga#k=%s" % (PORT, KEY)); pg.wait_for_timeout(4000)
        pg.evaluate("async (s) => { const l = CHAPS.map((c, i) => ({ c, i })).filter(x => x.c.dir.startsWith(s + '/')); await openChap(l[0].i); }", SERIE)
        pg.wait_for_timeout(1500)
        pg.evaluate("() => document.querySelectorAll('#chapPages figure img')[0].click()"); pg.wait_for_timeout(1200)
        n = pg.evaluate("() => LB_LISTE.length")
        check("visionneuse ouverte sur la page 1 (%d pages)" % n, pg.evaluate("() => !$('lightbox').hidden && LB === 0") and n >= 3)
        cdp = c.new_cdp_session(pg)
        wb = pg.evaluate("() => { const r = $('lbWrap').getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; }")
        def glisse(x0, x1, y0, y1=None):
            y1 = y0 if y1 is None else y1
            cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x0, "y": y0}]})
            for i in range(1, 6):
                cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x0 + (x1 - x0) * i / 5, "y": y0 + (y1 - y0) * i / 5}]})
            cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
            pg.wait_for_timeout(450)
        cx, cy = wb["x"], wb["y"]; d = min(120, w * 0.3)
        glisse(cx - d, cx + d, cy)
        check("balayer vers la DROITE → page 2 (suivante)", pg.evaluate("() => LB") == 1, pg.evaluate("() => [LB + 1, $('lbName').textContent]"))
        glisse(cx - d, cx + d, cy)
        check("encore vers la droite → page 3", pg.evaluate("() => LB") == 2, pg.evaluate("() => LB + 1"))
        glisse(cx + d, cx - d, cy)
        check("balayer vers la GAUCHE → page 2 (précédente)", pg.evaluate("() => LB") == 1, pg.evaluate("() => LB + 1"))
        glisse(cx, cx + 15, cy - 100, cy + 100)
        check("geste vertical → la page ne change pas", pg.evaluate("() => LB") == 1)
        pg.evaluate("() => zoomVers(2.5, null, null)"); pg.wait_for_timeout(300)
        glisse(cx - d, cx + d, cy)
        check("image zoomée : le même geste la déplace, la page ne change pas", pg.evaluate("() => LB === 1 && Z.k > 1"), pg.evaluate("() => [LB + 1, Z.k]"))
        pg.evaluate("() => zoomReset()")
        check("aucune erreur JS", not errs, errs[:3])
        c.close()
    b.close()
print("\nVERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
