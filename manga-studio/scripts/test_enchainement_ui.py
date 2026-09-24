# -*- coding: utf-8 -*-
"""Banc v2.17.0 (app reelle, Edge sans fenetre) : a l'etape de capture, choisir un onglet dont le site N'enchaine PAS
ferme le selecteur « Chapitres » sur « ce chapitre seul » (+ message) ; un onglet qui enchaine le rouvre.
Lit les onglets REELS des fenetres de capture (principale 8190 / secondaire 8192) ; ne capture rien, n'ecrit rien.
Usage : python test_enchainement_ui.py [port]    (8190 par defaut)"""
import os, re, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
OK, KO = [], []
def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom); print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail and not cond else ""))
with sync_playwright() as pw:
    b = pw.chromium.launch(channel="msedge", headless=True)
    for larg in (1280, 360):
        pg = b.new_page(viewport={"width": larg, "height": 900}); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto("http://127.0.0.1:%d/manga/#k=%s" % (PORT, KEY)); pg.wait_for_timeout(2500)
        pg.locator('nav button[data-tab="tChap"]').click(); pg.wait_for_timeout(2500)
        pg.evaluate("refreshCapTabs()"); pg.wait_for_timeout(1500)
        tabs = pg.evaluate("CAP_TABS.map(t => [t.url, capEnchainement(t.url)[0]])")
        oui = [i for i, (_u, e) in enumerate(tabs) if e]; non = [i for i, (_u, e) in enumerate(tabs) if not e]
        print("%d px : %d onglet(s), %d qui enchainent, %d non" % (larg, len(tabs), len(oui), len(non)))
        def choisir(i):
            pg.evaluate("i => { $('capTab').value = String(i); $('capTab').dispatchEvent(new Event('change')); }", i); pg.wait_for_timeout(300)
            return pg.evaluate("() => ({mode: $('capSerieMode').value, off: $('capSerieMode').disabled, j: $('capJusqua').disabled, txt: $('capEnch').textContent})")
        if non:
            pg.evaluate("() => { $('capSerieMode').value = 'suite'; capSerieMaj(); }")
            e = choisir(non[0])
            check("site sans enchainement : « ce chapitre seul », selecteur ferme", e["mode"] == "seul" and e["off"] and e["j"], e)
            check("... et le message le dit", e["txt"].startswith("⛔"), e["txt"])
        if oui:
            e = choisir(oui[0])
            check("site qui enchaine : selecteur rouvert", not e["off"] and not e["j"], e)
            check("... et le message le dit", e["txt"].startswith("🔗"), e["txt"])
        check("au moins un cas de chaque sorte teste", bool(oui) and bool(non) or larg == 360, (len(oui), len(non)))
        check("aucune erreur JavaScript", not errs, errs[:2])
        pg.close()
    b.close()
print("\n%d/%d" % (len(OK), len(OK) + len(KO))); sys.exit(1 if KO else 0)
