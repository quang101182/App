# -*- coding: utf-8 -*-
"""Sonde (26/09, bug Quang 11h15) : pendant une GENERATION video, l'onglet Video du chapitre « clignote en se redimensionnant
en hauteur » ; la fleche de droite de la ligne Narration deborde. APP REELLE 8190, 476 px (Fold ferme), generation SIMULEE :
la reponse de /manga/videos est modifiee DANS LA PAGE (file d'attente « en cours » sur le chapitre ouvert). Rien n'est ecrit.
Mesure : hauteur de #chapVid et de la ligne compacte toutes les 50 ms pendant 12 s ; debordement des lignes compactes.
Usage : python sonde_clignotement_video.py [port] [dossier du chapitre]
"""
import json, os, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
D = sys.argv[2] if len(sys.argv) > 2 else "solo-levelng-ragnarok/ch_2"
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    pg = b.new_page(viewport={"width": 476, "height": 900}, is_mobile=True, has_touch=True, device_scale_factor=2.6)
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    def route(r):
        resp = r.fetch(); j = resp.json()
        for c in j.get("chapitres", []):
            if c.get("d") == D:
                c["file"] = [{"etat": "en cours", "tag": "gemini-charon", "etape": "images", "fait": 40, "total": 126}]
        r.fulfill(response=resp, body=json.dumps(j), headers=dict(resp.headers, **{"content-type": "application/json"}))
    pg.route("**/manga/videos?serie=*", route)
    pg.goto("http://127.0.0.1:%d/manga#k=%s" % (PORT, KEY)); pg.wait_for_timeout(4000)
    i = pg.evaluate("(d) => CHAPS.findIndex(c => c.dir === d)", D)
    pg.evaluate("(i) => openChap(i)", i); pg.wait_for_timeout(3000)
    pg.evaluate("""() => { window.__h = []; const t0 = performance.now();
        const lire = () => { const v = $('chapVid'), cl = document.querySelector('[data-cl=vid], .cl-vid, #clVid');
            window.__h.push([Math.round(performance.now() - t0), v ? Math.round(v.getBoundingClientRect().height) : -1,
                             cl ? Math.round(cl.getBoundingClientRect().height) : -1, scrollY]); };
        window.__iv = setInterval(lire, 50); }""")
    pg.wait_for_timeout(12000)
    h = pg.evaluate("() => { clearInterval(window.__iv); return window.__h; }")
    vals = [x[1] for x in h]
    sauts = [(h[k][0], h[k - 1][1], h[k][1]) for k in range(1, len(h)) if h[k][1] != h[k - 1][1]]
    print("hauteur #chapVid : min %d, max %d, changements : %d" % (min(vals), max(vals), len(sauts)))
    for s in sauts[:12]: print("   t=%5d ms : %d -> %d px" % s)
    sc = [x[3] for x in h]; print("défilement de la page (scrollY) : min %d, max %d" % (min(sc), max(sc)))
    # debordement : lignes compactes / boutons qui sortent de leur cadre
    deb = pg.evaluate("""() => [...document.querySelectorAll('#chapDetail *')].filter(e => { const r = e.getBoundingClientRect(); return r.width && r.right > innerWidth - 2 && getComputedStyle(e).display !== 'none'; })
        .slice(0, 8).map(e => (e.id ? '#' + e.id : e.className ? '.' + String(e.className).split(' ')[0] : e.tagName) + ' ' + Math.round(e.getBoundingClientRect().right) + '/' + innerWidth + ' « ' + (e.textContent || '').trim().slice(0, 20) + ' »')""")
    print("éléments qui touchent/dépassent le bord droit :", deb)
    pg.screenshot(path=os.path.join(os.environ["TEMP"], "sonde_chap_476.png"))
    print("erreurs JS :", errs[:3])
    b.close()
