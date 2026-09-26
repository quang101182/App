# -*- coding: utf-8 -*-
"""Banc D8 : lecteur + preparation des Dialogues sur les VRAIES donnees (OPM ch.5 p.13-15 prepare le 27/09), 5 largeurs. Lecture seule, 0 credit. Usage : python test_dialogues_largeurs_reel.py [port]"""
import os, sys
from playwright.sync_api import sync_playwright
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
import tempfile; SP = tempfile.gettempdir(); AL = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "aligne_dialogues.js"), encoding="utf-8").read()
PORT = sys.argv[1] if len(sys.argv) > 1 else "8190"
OK = KO = 0
def check(n, c, d=""):
    global OK, KO
    OK += bool(c); KO += (not c); print(("  [OK] " if c else "  [KO] ") + n + ("" if c else " -- " + str(d)[:200]))
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True, args=["--autoplay-policy=no-user-gesture-required", "--mute-audio"])
    for w, h in ((360, 780), (476, 900), (704, 900), (933, 700), (1280, 900)):
        print("=== %d" % w)
        ctx = b.new_context(viewport={"width": w, "height": h}, is_mobile=w < 500, has_touch=w < 500)
        pg = ctx.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto("http://127.0.0.1:%s/manga#k=%s" % (PORT, KEY)); pg.wait_for_timeout(3500)
        pg.evaluate("() => localStorage.setItem('manga_serie','one-punch-man')")
        pg.evaluate("() => openChap(CHAPS.findIndex(c => c.dir === 'one-punch-man/ch_5'))"); pg.wait_for_timeout(3500)
        etat = pg.evaluate("() => $('dlgEtat').textContent")
        check("ligne Dialogues : prêts · 12 répliques", "12 répliques" in etat, etat)
        pg.evaluate("() => dlgPrepOuvrir()"); pg.wait_for_timeout(2500)
        d = pg.evaluate("() => ({ n: document.querySelectorAll('#dlgPrep .dlgp-rep').length, over: $('dlgPrep').scrollWidth > $('dlgPrep').clientWidth + 1, pied: $('dlgpPied').textContent })")
        check("préparation : 13 répliques, pas de débordement", d["n"] == 13 and not d["over"], d)
        pg.screenshot(path=os.path.join(SP, "prep_%d.png" % w))
        pg.evaluate("() => $('dlgpRet').click()"); pg.wait_for_timeout(1000)
        pg.evaluate("() => dlgLecteur()"); pg.wait_for_timeout(2500)
        for k in range(3):
            a = pg.evaluate("(" + AL + ")")
            check("lecteur r%d : halo sur la bulle (±4 px), couleur, cadre" % k, a["ecart"] <= 4 and a["svg_sur_img"] and not a["deborde"] and a["cadre_ok"], a)
            pg.evaluate("() => $('dllSuiv').click()"); pg.wait_for_timeout(1200)
        pg.screenshot(path=os.path.join(SP, "lec_%d.png" % w))
        check("0 erreur JS", not errs, errs)
        ctx.close()
print("%d OK, %d KO" % (OK, KO))
