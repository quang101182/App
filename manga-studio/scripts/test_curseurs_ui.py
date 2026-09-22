# -*- coding: utf-8 -*-
"""Banc v2.4.5 : curseurs de volume CHIFFRES et IDENTIQUES (Quang 22/09 18h30-18h31). Lecture seule (rien n'est enregistre).

Lecteur de narration (one-punch-man, 1er chapitre narre) : 🔊 et 🎵 affichent « N % » ; glisser -> le chiffre suit.
Profil de la serie : « musique des vidéos » affiche « N % » (« 0 % — coupée » a 0). Les deux curseurs de musique ont
MEME largeur, MEME pas (1), MEME couleur, MEME echelle (0-100). 1280 + 360 px, sans debordement.
Usage : python test_curseurs_ui.py [port] [dossier_captures]
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


STYLE = """(id) => { const r = document.getElementById(id), cs = getComputedStyle(r);
    return {w: Math.round(r.getBoundingClientRect().width), step: r.step, min: r.min, max: r.max, accent: cs.accentColor}; }"""
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w, h in ((1280, 900), (360, 780)):
        print("=== %d px" % w)
        pg = b.new_page(viewport={"width": w, "height": h}); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto("http://127.0.0.1:%d/manga/#k=" % PORT + KEY); pg.wait_for_timeout(2500)
        pg.click('nav button[data-tab="tChap"]'); pg.wait_for_timeout(1500)
        d = pg.evaluate("""async () => { const l = CHAPS.filter(c => c.dir.startsWith('one-punch-man/')).sort((a, b) => parseFloat(a.chapter) - parseFloat(b.chapter));
            for (const c of l) { if (await narrAvecVoix(c.dir)) return c.dir; } return null; }""")
        pg.evaluate("async (d) => { await openChap(CHAPS.findIndex(c => c.dir === d)); await refreshMus(); const n = await narrAvecVoix(d); await ouvrirLecteur([n.tag]); }", d)
        pg.wait_for_timeout(2500)
        v = pg.evaluate("() => [document.getElementById('lecVolG').value, document.querySelector('[data-pour=lecVolG]').textContent, document.getElementById('lecMusVol').value, document.querySelector('[data-pour=lecMusVol]').textContent, !document.getElementById('lecMusBox').hidden]")
        check("lecteur : 🔊 et 🎵 affichent leur valeur", v[1] == v[0] + " %" and v[3] == v[2] + " %", v)
        pg.evaluate("() => { const r = document.getElementById('lecMusVol'); r.value = 37; r.dispatchEvent(new Event('input', {bubbles: true})); }")
        check("glisser 🎵 à 37 → « 37 % »", pg.evaluate("() => document.querySelector('[data-pour=lecMusVol]').textContent") == "37 %")
        pg.evaluate("(v) => { const r = document.getElementById('lecMusVol'); r.value = v; r.dispatchEvent(new Event('input', {bubbles: true})); }", v[2])   # remis
        lec = pg.evaluate(STYLE, "lecMusVol")
        m1 = pg.evaluate("() => Array.from(document.querySelectorAll('#lecteur *')).filter(e => e.offsetParent && !e.closest('.lec-scene') && e.getBoundingClientRect().right > innerWidth + 1).length")   # l'image zoomee est ROGNEE par .lec-scene
        check("lecteur : rien ne déborde", m1 == 0, m1)
        pg.evaluate("() => document.getElementById('lecFermer').click()"); pg.wait_for_timeout(500)
        pg.evaluate("() => ouvrirSerie('one-punch-man')"); pg.wait_for_timeout(1000)
        pg.click("#btnSuivi"); pg.wait_for_timeout(3000)
        prof = pg.evaluate(STYLE, "profVol")
        pv = pg.evaluate("() => [document.getElementById('profVol').value, document.getElementById('profVolVal').textContent]")
        check("profil : « musique des vidéos » affiche sa valeur", pv[1].startswith(pv[0] + " %"), pv)
        check("les deux curseurs de musique sont identiques (largeur, pas, échelle, couleur)",
              (lec["w"], lec["step"], lec["min"], lec["max"], lec["accent"]) == (prof["w"], prof["step"], prof["min"], prof["max"], prof["accent"]), (lec, prof))
        if w == 1280:
            pg.query_selector(".prof-l.bloc-vid").screenshot(path=os.path.join(CAP, "curseur_profil.png"))
        m2 = pg.evaluate("() => Array.from(document.querySelectorAll('#suiviBox *')).filter(e => e.offsetParent && e.getBoundingClientRect().right > innerWidth + 1).length")
        check("profil : rien ne déborde", m2 == 0, m2)
        check("aucune erreur JS", not errs, errs)
        pg.close()
    b.close()
print("\nVERDICT : %d/%d" % (len(OK), len(OK) + len(KO)) + ("" if not KO else "  -- KO : " + " ; ".join(KO)))
sys.exit(0 if not KO else 1)
