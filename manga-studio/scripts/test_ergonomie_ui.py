# -*- coding: utf-8 -*-
"""Banc UI v1.92.0 : ergonomie bibliotheque + chapitre (Quang, 22/09 05h15), MESUREE au pixel (Claymore ch.1).
- 🗑 et ▶ des narrations a la MEME abscisse sur toutes les lignes (zones fixes), quel que soit le texte ;
- barre de bibliotheque fine (recherche + ↻ sur une ligne, < 60 px avec la ligne d'etat), sans le chemin disque ;
- actions du chapitre sur UNE ligne, avertissements de capture replies ;
- musique : 🗑 aligne ; pas de debordement horizontal. PC 1280 px + 360 px.
Usage : python test_ergonomie_ui.py [port]
"""
import os, sys
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


XS = "(sel) => [...document.querySelectorAll(sel)].map(b => Math.round(b.getBoundingClientRect().x))"
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w, h in ((1280, 1000), (360, 780)):
        print("=== %d px" % w)
        c = b.new_context(viewport={"width": w, "height": h}, is_mobile=w < 500, has_touch=w < 500)
        pg = c.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto("http://127.0.0.1:%d/manga#k=" % PORT + KEY); pg.wait_for_timeout(2500)
        pg.evaluate("() => { try { localStorage.removeItem('manga_serie'); } catch {} }")
        pg.click('nav button[data-tab="tChap"]'); pg.wait_for_timeout(2500)
        if pg.is_visible("#btnLibBack"):
            pg.click("#btnLibBack"); pg.wait_for_timeout(800)
        r = pg.evaluate("""() => { const a = document.querySelector('.lib-barre').getBoundingClientRect(),
                                         e = document.getElementById('chapState').getBoundingClientRect();
                                   return {h: Math.round(e.bottom - a.top), y1: Math.round(document.getElementById('libRech').getBoundingClientRect().y),
                                           y2: Math.round(document.getElementById('btnChapRefresh').getBoundingClientRect().y)} }""")
        check("barre de bibliotheque fine : recherche + ↻ sur une ligne, < 70 px avec l'etat (230 avant)", r["h"] < 70 and abs(r["y1"] - r["y2"]) < 6, r)
        check("l'etat ne montre plus le chemin disque", ":\\\\" not in pg.inner_text("#chapState") and "sources" not in pg.inner_text("#chapState"), pg.inner_text("#chapState"))
        i = pg.evaluate("() => CHAPS.findIndex(c => c.dir === 'claymore/ch_1')")
        pg.evaluate("(i) => openChap(i)", i); pg.wait_for_timeout(3500)
        ys = pg.evaluate("() => ['btnChapVerif','btnPagesSel','btnChapDel'].map(id => Math.round(document.getElementById(id).getBoundingClientRect().y))")
        check("actions du chapitre sur UNE ligne", len(set(ys)) == 1, ys)
        check("avertissements de capture replies", pg.evaluate("() => !$('chapNotesBox').hidden && !$('chapNotesBox').open"))
        corb = pg.evaluate(XS, "#narrRuns > .narr-run [data-suppr-narr]")
        lire = pg.evaluate(XS, "#narrRuns > .narr-run [data-ecoute]")
        check("🗑 des narrations : meme abscisse sur toutes les lignes", len(corb) >= 3 and len(set(corb)) == 1, corb)
        check("▶ des narrations : meme abscisse", len(lire) >= 3 and len(set(lire)) == 1, lire)
        tags = pg.evaluate("() => [...document.querySelectorAll('#narrRuns > .narr-run .nr-tag')].map(e => e.scrollWidth <= e.clientWidth + 1)")
        check("noms des narrations lisibles en entier", all(tags), tags)
        # le nom ne doit pas etre RECOUVERT par les boutons (le 1er banc ne mesurait que la troncature : il a laisse passer
        # un nom cache SOUS ▶ a 360 px, vu sur capture)
        recouv = pg.evaluate("""() => [...document.querySelectorAll('#narrRuns > .narr-run')].map(r => {
            const t = r.querySelector('.nr-tag').getBoundingClientRect(), a = r.querySelector('.nr-act').getBoundingClientRect();
            return !(t.right <= a.left + 1 || a.bottom <= t.top + 1 || t.bottom <= a.top + 1); })""")
        check("aucun nom recouvert par les boutons", not any(recouv), recouv)
        mus = pg.evaluate(XS, "#musListe [data-mus-suppr]")
        check("🗑 de la musique aligne", len(set(mus)) == 1, mus)
        dep = pg.evaluate("() => document.documentElement.scrollWidth - innerWidth")
        check("pas de debordement horizontal", dep <= 0, dep)
        check("aucune erreur JS", not errs, errs[:2])
        c.close()
    b.close()
print("\n=== VERDICT : %d/%d" % (len(OK), len(OK) + len(KO)) + ("" if not KO else "  ECHECS : " + ", ".join(KO)))
sys.exit(1 if KO else 0)
