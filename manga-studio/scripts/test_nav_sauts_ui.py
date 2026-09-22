# -*- coding: utf-8 -*-
"""Banc v2.4.3 : les boutons chapitre precedent / suivant affichent le VRAI numero voisin et disent les SAUTS
(Quang 22/09 16h46 : « ne mettez pas un chiffre plus ou moins un bêtement »). Lecture seule sur one-punch-man.

Lecteur de narration (ouvert sur le 2e chapitre qui a une voix) : « ⏮ ch. X » / « ch. Y ⏭ » = numeros reels ;
on fait croire (dans la page seulement) que le chapitre suivant n'a pas de voix -> le bouton va au suivant d'apres,
en orange, « ⚠ ⏭ saut : ch. … sans narration » ; il ouvre bien ce chapitre. Fiche du chapitre : un TROU de numeros
(chapitre retire de la liste, dans la page) -> « saut : ch. N pas dans la bibliothèque ». 1280 + 360 px.
Usage : python test_nav_sauts_ui.py [port]
"""
import os, sys
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
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
        pg.click('nav button[data-tab="tChap"]'); pg.wait_for_timeout(1500)
        # les chapitres OPM qui ont une narration avec voix, dans l'ordre
        lisibles = pg.evaluate("""async () => { const l = CHAPS.filter(c => c.dir.startsWith('one-punch-man/')).sort((a, b) => parseFloat(a.chapter) - parseFloat(b.chapter));
            const out = []; for (const c of l) { if (await narrAvecVoix(c.dir)) out.push([c.dir, c.chapter]); } return out; }""")
        if len(lisibles) < 4:
            check("au moins 4 chapitres narrés", False, lisibles); break
        (d0, n0), (d1, n1), (d2, n2), (d3, n3) = lisibles[:4]
        pg.evaluate("async (d) => { await openChap(CHAPS.findIndex(c => c.dir === d)); const n = await narrAvecVoix(d); await ouvrirLecteur([n.tag]); }", d1)
        pg.wait_for_timeout(2500)
        lire = lambda: pg.evaluate("""() => ({prev: document.getElementById('lecChPrev').hidden ? null : document.getElementById('lecChPrev').textContent,
            next: document.getElementById('lecChNext').hidden ? null : document.getElementById('lecChNext').textContent,
            orange: document.getElementById('lecChNext').classList.contains('saut'), ligne: document.getElementById('lecSaut').textContent,
            titre: document.getElementById('lecTitre').textContent})""")
        e = lire()
        check("lecteur ch.%s : « ⏮ ch. %s » et « ch. %s ⏭ »" % (n1, n0, n2), e["prev"] == "⏮ ch. " + n0 and e["next"] == "ch. " + n2 + " ⏭", e)
        # le chapitre suivant « perd » sa voix (dans la page) -> saut jusqu'au suivant d'apres
        pg.evaluate("(d) => { const vrai = narrAvecVoix; window.narrAvecVoix = async x => x === d ? null : vrai(x); return lecNavMaj(); }", d2)
        pg.wait_for_timeout(1500)
        e = lire()
        check("ch.%s sans voix : « ch. %s ⏭ » orange + « saut … sans narration »" % (n2, n3),
              e["next"] == "ch. " + n3 + " ⏭" and e["orange"] and "sans narration" in e["ligne"] and n2 in e["ligne"], e)
        pg.click("#lecChNext"); pg.wait_for_timeout(3500)
        check("le bouton ouvre le ch.%s" % n3, pg.evaluate("() => CHAP_OPEN") == d3, pg.evaluate("() => CHAP_OPEN"))
        pg.evaluate("() => { document.getElementById('lecFermer').click(); }"); pg.wait_for_timeout(500)
        # fiche du chapitre : un TROU de numeros (le chapitre d2 retire de la liste, dans la page)
        pg.evaluate("(d) => { CHAPS = CHAPS.filter(c => c.dir !== d); }", d2)
        pg.evaluate("async (d) => { await openChap(CHAPS.findIndex(c => c.dir === d)); chapNavMaj(); }", d1); pg.wait_for_timeout(1200)
        f = pg.evaluate("""() => { const b = document.getElementById('chapNext'); return [b.textContent, b.classList.contains('saut'), b.title]; }""")
        check("fiche : ch.%s → « ch. %s ⏭ » orange, « %s pas dans la bibliothèque »" % (n1, n3, n2),
              f[0] == "ch. " + n3 + " ⏭" and f[1] and "pas dans la bibliothèque" in f[2], f)
        check("aucune erreur JS", not errs, errs)
        pg.close()
    b.close()
print("\nVERDICT : %d/%d" % (len(OK), len(OK) + len(KO)) + ("" if not KO else "  -- KO : " + " ; ".join(KO)))
sys.exit(0 if not KO else 1)
