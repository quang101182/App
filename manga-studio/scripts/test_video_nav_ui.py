# -*- coding: utf-8 -*-
"""Banc v2.4.2 : lecteur VIDEO -> chapitre precedent / suivant, saut signale (Quang 22/09 16h44).

Usage : python test_video_nav_ui.py [port] [dossier_captures]. Lecture seule sur la serie one-punch-man (il lui faut
>= 3 videos). 1280 et 360 px : ouvrir la video du 2e chapitre -> « ⏮ ch. <1er> » et « ch. <3e> ⏭ », pas de saut ;
on RETIRE (dans la page seulement) la video du 3e chapitre -> « ch. <4e> ⏭ » borde d'orange + « ⚠ ... saut : ch. <3e> » ;
le bouton ouvre bien la video du 4e (titre) ; au 1er chapitre, pas de « ⏮ » ; rien ne deborde.
"""
import os, sys
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
CAP = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(os.path.abspath(__file__))
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""), flush=True)


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w, h in ((1280, 900), (360, 780)):
        print("=== %d px" % w)
        pg = b.new_page(viewport={"width": w, "height": h}); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto("http://127.0.0.1:%d/manga/#k=" % PORT + KEY); pg.wait_for_timeout(2500)
        pg.click('nav button[data-tab="tChap"]'); pg.wait_for_timeout(1200)
        pg.evaluate("() => ouvrirSerie('one-punch-man')"); pg.wait_for_timeout(1200)
        pg.evaluate("() => vidCharger('one-punch-man')"); pg.wait_for_timeout(2500)
        ch = pg.evaluate("() => VIDS.chapitres.map(c => [c.chapitre, (c.videos || []).length]).sort((a, b) => parseFloat(a[0]) - parseFloat(b[0]))")
        avec = [c for c, n in ch if n]
        if len(avec) < 4:
            check("au moins 4 vidéos dans la série", False, ch); break
        i2 = "() => VIDS.chapitres.findIndex(c => c.chapitre === '%s')"
        pg.evaluate("(i) => vidOuvrir(i)", pg.evaluate(i2 % avec[1])); pg.wait_for_timeout(800)
        etat = lambda: pg.evaluate("""() => ({titre: document.getElementById('vidLecTitre').textContent,
            prev: document.getElementById('vidLecPrev').hidden ? null : document.getElementById('vidLecPrev').textContent,
            next: document.getElementById('vidLecNext').hidden ? null : document.getElementById('vidLecNext').textContent,
            sautN: document.getElementById('vidLecNext').classList.contains('saut'), ligne: document.getElementById('vidLecSaut').textContent})""")
        e = etat()
        check("ch.%s : ⏮ ch.%s et ch.%s ⏭, pas de saut" % (avec[1], avec[0], avec[2]),
              e["prev"] == "⏮ ch. " + avec[0] and e["next"] == "ch. " + avec[2] + " ⏭" and not e["sautN"] and e["ligne"] == "", e)
        pg.evaluate("(c) => { VIDS.chapitres.find(x => x.chapitre === c).videos = []; vidNavMaj(); }", avec[2])
        e = etat()
        check("sans vidéo au ch.%s : « ch.%s ⏭ » en orange + « saut »" % (avec[2], avec[3]),
              e["next"] == "ch. " + avec[3] + " ⏭" and e["sautN"] and ("saut : ch. " + avec[2]) in e["ligne"], e)
        if w == 1280:
            pg.query_selector("#vidLecteur").screenshot(path=os.path.join(CAP, "vidnav_1280.png"))
        pg.click("#vidLecNext"); pg.wait_for_timeout(800)
        e = etat()
        check("le bouton ouvre la vidéo du ch.%s" % avec[3], ("ch. " + avec[3] + " ·") in e["titre"], e["titre"])
        pg.evaluate("(i) => vidOuvrir(i)", pg.evaluate(i2 % avec[0])); pg.wait_for_timeout(600)
        check("1er chapitre : pas de ⏮", etat()["prev"] is None)
        m = pg.evaluate("""() => Array.from(document.querySelectorAll('#vidLecteur .vid-lec-tete *')).filter(e => e.offsetParent && e.getBoundingClientRect().right > innerWidth + 1).length""")
        check("rien ne déborde", m == 0, m)
        check("aucune erreur JS", not errs, errs)
        pg.close()
    b.close()
print("\nVERDICT : %d/%d" % (len(OK), len(OK) + len(KO)) + ("" if not KO else "  -- KO : " + " ; ".join(KO)))
sys.exit(0 if not KO else 1)
