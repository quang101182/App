# -*- coding: utf-8 -*-
"""Banc v2.1.0 : ce que chaque serie / chapitre possede, visible dans la bibliotheque (Quang 22/09 10h58).
Cartes de serie : « 🎙 n/N narrés », 🎬, 🎵, 🌙 ; cartes de chapitre : « 🎙 n · voix », 🎤, 📜, 🌐 ; « pas encore narré » sinon.
Les chiffres sont COMPARES au disque (compte independant, pas la route du proxy). 360 px sans debordement.
Usage : python test_resume_ui.py [port]
"""
import json, os, sys
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
SRC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sources"))
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


def disque(serie, ch):
    """Compte independant : narrations dont au moins une page a une voix, et leurs voix."""
    nd, n, voix = os.path.join(SRC, serie, ch, "narration"), 0, []
    for tag in (os.listdir(nd) if os.path.isdir(nd) else []):
        f = os.path.join(nd, tag, "narration.json")
        if os.path.isfile(f):
            j = json.load(open(f, encoding="utf-8"))
            if any(p.get("audio") for p in j.get("pages") or []):
                n += 1
                if j.get("voice") and j["voice"] not in voix:
                    voix.append(j["voice"])
    return n, voix


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w, h in ((1280, 1000), (360, 780)):
        print("=== %d px" % w)
        pg = b.new_page(viewport={"width": w, "height": h}); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto("http://127.0.0.1:%d/manga/#k=" % PORT + KEY); pg.wait_for_timeout(2500)
        pg.evaluate("() => { try { localStorage.removeItem('manga_serie'); } catch {} }")
        pg.reload(); pg.wait_for_timeout(2500)
        pg.click('nav button[data-tab="tChap"]'); pg.wait_for_timeout(2500)
        carte = lambda sel: pg.evaluate("(s) => { const b = document.querySelector(s); return b ? b.innerText : ''; }", sel)
        cl = carte('#chapList [data-serie="claymore"]')
        check("série Claymore : 🎙 1/1 narré, 🎬 1, 🎵", "🎙 1/1 narré" in cl and "🎬 1" in cl and "🎵" in cl, cl.replace("\n", " | "))
        fr = carte('#chapList [data-serie="demo-frieren"]')
        check("série Demo Frieren : suivi 🌙 Gemini", "🌙 Gemini" in fr, fr.replace("\n", " | "))
        no = carte('#chapList [data-serie="noritaka"]')
        check("série Noritaka : 🎙 0/1", "🎙 0/1" in no, no.replace("\n", " | "))
        pg.click('#chapList [data-serie="claymore"]'); pg.wait_for_timeout(2500)
        n, voix = disque("claymore", "ch_1")
        c1 = carte('#chapList [data-chap]')
        check("chapitre Claymore 1 : 🎙 %d · voix du disque · 🎤 · 🌐 FR" % n, ("🎙 %d · %s" % (n, ", ".join(voix))) in c1 and "🎤" in c1 and "🌐 FR" in c1, c1.replace("\n", " | "))
        pg.click("#btnLibBack"); pg.wait_for_timeout(1500)
        pg.click('#chapList [data-serie="one-punch-man"]'); pg.wait_for_timeout(2500)
        txt = pg.evaluate("() => [...document.querySelectorAll('#chapList [data-chap]')].map(b => b.innerText)")
        c301 = [t for t in txt if "301" in t.split("\n")[0]][0]
        check("chapitre OPM 301 : 📜 (Précédemment fabriqué) · Fenrir", "📜" in c301 and "Fenrir" in c301, c301.replace("\n", " | "))
        pg.click("#btnLibBack"); pg.wait_for_timeout(1500)
        pg.click('#chapList [data-serie="noritaka"]'); pg.wait_for_timeout(2500)
        check("chapitre sans narration : « pas encore narré »", "pas encore narré" in carte('#chapList [data-chap]'))
        dep = pg.evaluate("() => document.documentElement.scrollWidth - innerWidth")
        check("aucun débordement", dep <= 0, dep)
        check("0 erreur JS", not errs, errs[:3])
        pg.evaluate("() => { try { localStorage.removeItem('manga_serie'); } catch {} }")
        if w == 360:
            pg.click("#btnLibBack"); pg.wait_for_timeout(1200)
            pg.screenshot(path=os.path.join(os.environ.get("TEMP", "."), "resume_360.png"))
        pg.close()
    b.close()
print("\n%d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
