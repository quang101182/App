# -*- coding: utf-8 -*-
"""Banc v3.4.2 + v3.4.3 (Quang 19h14-19h15) : pourcentages sur les curseurs du lecteur des Dialogues ; video prete =
« ▶ Video » (un bouton) ; musique changee = video « a refaire (musique) ». App REELLE 8190, lecture seule, 360 + 1280 px.
Usage : python test_video_musique_ui.py <serie/ch_N avec musique et video SANS musique> [--page f.html]"""
import os, sys
from playwright.sync_api import sync_playwright
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
args = sys.argv[1:]
PAGE = None
if "--page" in args:
    i = args.index("--page"); PAGE = open(args[i + 1], encoding="utf-8").read(); del args[i:i + 2]
CH = args[0]
OK, KO = [], []
def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom); print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail)[:160] if detail else ""), flush=True)
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w in (360, 1280):
        for mus in ("1", "0"):
            ctx = b.new_context(viewport={"width": w, "height": 850}, is_mobile=w < 800, has_touch=w < 800, service_workers="block"); pg = ctx.new_page(); errs = []
            pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("dialog", lambda d: d.dismiss())
            def route(rt):
                u = rt.request.url.split("#")[0].split("?")[0].rstrip("/")
                if rt.request.method != "GET": return rt.fulfill(status=200, body='{"ok":true}', content_type="application/json")
                if PAGE and u.endswith("/manga"): return rt.fulfill(status=200, body=PAGE, content_type="text/html; charset=utf-8")
                return rt.continue_()
            pg.route("**/*", route)
            pg.goto("http://127.0.0.1:8190/manga/#k=" + KEY); pg.wait_for_timeout(2500)
            pg.evaluate("([s, m]) => { localStorage.setItem('manga_onglet','tChap'); localStorage.setItem('manga_serie', s); localStorage.setItem('manga_mus_on', m); }", [CH.split("/")[0], mus])
            pg.reload(); pg.wait_for_timeout(3500)
            pg.evaluate("d => openChap(CHAPS.findIndex(c => c.dir === d))", CH); pg.wait_for_timeout(3500)
            pg.evaluate("() => clOuvrir('dlg')"); pg.wait_for_timeout(3000)
            r = pg.evaluate("() => ({ v: VERSION, vid: $('dlgVid').textContent, pret: $('dlgVid').classList.contains('dpl-pret'), chip: (document.querySelector('#dplListe .dpl.sel .m') || {}).textContent || '' })")
            if mus == "1":
                check("%d px, musique ACTIVEE, video faite sans : « à refaire (musique) »" % w, "Refaire (musique)" in r["vid"] and "à refaire (musique)" in r["chip"], r)
            else:
                check("%d px, musique COUPEE : video prete = « ▶ Vidéo » (bouton vert)" % w, r["vid"].startswith("▶ Vidéo") and r["pret"], r)
                pg.evaluate("() => dlgLecteur()"); pg.wait_for_timeout(3000); pg.evaluate("() => { try { DLL.audio.pause(); } catch(e){} dllRegOuvrir(true); }"); pg.wait_for_timeout(1200)
                pc = pg.evaluate("() => [...document.querySelectorAll('#dlgLec .curseur-val')].map(x => [x.dataset.pour, x.textContent, !!x.offsetParent])")
                check("%d px : lecteur des Dialogues, volume general avec « NN %% »" % w, any(x[0] == "dllVol" and x[1].endswith(" %") for x in pc), pc)
                check("%d px : volume de la musique avec « NN %% »" % w, any(x[0] == "dllMusVol" and x[1].endswith(" %") for x in pc), pc)
            check("%d px : 0 erreur JS" % w, not errs, errs[:2])
            ctx.close()
    b.close()
print("\nVERDICT : %d/%d" % (len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
