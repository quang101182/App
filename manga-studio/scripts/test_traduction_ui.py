# -*- coding: utf-8 -*-
"""Banc UI v1.84.0 sur l'APP REELLE : traduction des dialogues (bloc Traduire, selecteur VO / langue dans la
grille, la visionneuse et le lecteur). Lit Claymore ch.1 (62 pages traduites en fr le 22/09). Ne lance AUCUNE traduction.
PC 1280 px puis telephone 360 px. Verdict chiffre en sortie. Usage : python test_traduction_ui.py
"""
import os, sys
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
CHAP = "claymore/ch_1"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


def srcs(pg):
    return pg.evaluate("() => [...document.querySelectorAll('#chapPages figure img')].map(i => i.src)")


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True, args=["--autoplay-policy=no-user-gesture-required"])
    for w, h in ((1280, 900), (360, 780)):
        print("=== %d px" % w)
        c = b.new_context(viewport={"width": w, "height": h}, has_touch=(w < 400), is_mobile=(w < 400))
        pg = c.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto("http://127.0.0.1:%d/manga#k=" % PORT + KEY); pg.wait_for_timeout(3000)
        pg.evaluate("() => { try { localStorage.removeItem('manga_trad_vue'); } catch {} }")
        check("version >= 1.84.0 affichee", pg.inner_text("#verBadge") >= "v1.84.0", pg.inner_text("#verBadge"))
        pg.click('nav button[data-tab="tChap"]'); pg.wait_for_timeout(1500)
        i = pg.evaluate("(d) => CHAPS.findIndex(c => c.dir === d)", CHAP)
        check("Claymore ch.1 dans la liste", i >= 0, i)
        pg.evaluate("(i) => openChap(i)", i); pg.wait_for_timeout(3000)
        check("bloc Traduire visible", pg.is_visible("#btnTraduire") and pg.is_visible("#tradVue"))
        opts = pg.evaluate("() => [...$('tradVue').options].map(o => o.value)")
        check("selecteur : VO + francais", opts == ["", "fr"], opts)
        etat = pg.inner_text("#tradEtat")
        check("etat : bulles traduites affichees", "294 bulle" in etat, etat)
        s0 = srcs(pg)
        check("par defaut : pages VO", s0 and not any("traduction" in x for x in s0), len(s0))
        pg.select_option("#tradVue", "fr"); pg.wait_for_timeout(2500)
        s1 = srcs(pg)
        n_tr = sum("traduction%2Ffr" in x for x in s1)
        check("fr : les 62 pages traduites", n_tr == 62 == len(s1), (n_tr, len(s1)))
        check("fr : page 1 et page 62 = traduction", "traduction%2Ffr%2Fpage_001" in s1[0] and "traduction%2Ffr" in s1[-1])
        pg.evaluate("() => document.querySelectorAll('#chapPages figure img')[0].scrollIntoView()"); pg.wait_for_timeout(1500)
        nat = pg.evaluate("() => document.querySelectorAll('#chapPages figure img')[0].naturalWidth")
        check("l'image traduite se charge", nat > 100, nat)
        # visionneuse
        pg.click("#chapPages figure >> nth=0"); pg.wait_for_timeout(1500)
        lb = pg.evaluate("() => $('lbImg').src")
        check("visionneuse : page traduite", "traduction%2Ffr" in lb)
        pg.keyboard.press("Escape"); pg.wait_for_timeout(500)
        # lecteur (si une narration avec voix existe)
        k = pg.evaluate("() => NARRS.findIndex(n => n.audio || n.voix || n.voice)")
        if k >= 0:
            pg.evaluate("(k) => ouvrirLecteur([NARRS[k].tag])", k); pg.wait_for_timeout(2500)
            li = pg.evaluate("() => [...$('lecteur').querySelectorAll('img')].map(i => i.src).filter(Boolean)")
            check("lecteur : page traduite", any("traduction%2Ffr" in x for x in li), [x.split("&_k=")[0] for x in li[:1]])
            pg.click("#lecFermer"); pg.wait_for_timeout(500)
        else:
            print("  (pas de narration avec voix sur ce chapitre : lecteur non teste)")
        # persistance + retour VO
        pg.reload(); pg.wait_for_timeout(3000)
        pg.click('nav button[data-tab="tChap"]'); pg.wait_for_timeout(1000)
        pg.evaluate("(i) => openChap(i)", i); pg.wait_for_timeout(3000)
        check("choix fr memorise apres rechargement", pg.evaluate("() => $('tradVue').value") == "fr")
        pg.select_option("#tradVue", ""); pg.wait_for_timeout(1500)
        check("retour VO : plus aucune page traduite", not any("traduction" in x for x in srcs(pg)))
        # telephone : rien ne deborde
        dep = pg.evaluate("() => document.documentElement.scrollWidth - innerWidth")
        check("pas de debordement horizontal", dep <= 0, dep)
        bb = pg.locator("#btnTraduire").bounding_box()
        check("bouton Traduire dans l'ecran", bb and bb["x"] >= 0 and bb["x"] + bb["width"] <= w, bb)
        pg.screenshot(path=os.path.join(os.environ.get("TEMP", "."), "trad_ui_%d.png" % w))
        check("aucune erreur JS", not errs, errs[:2])
        c.close()
    b.close()
print("\n=== VERDICT : %d/%d" % (len(OK), len(OK) + len(KO)) + ("" if not KO else "  ECHECS : " + ", ".join(KO)))
sys.exit(1 if KO else 0)
