# -*- coding: utf-8 -*-
"""Banc UI de la bibliotheque (v1.76.0) sur l'APP REELLE (proxy 8190), PC 1280 px puis telephone 360 px.

Series + pochettes, ouverture d'une serie, memoire apres rechargement, essais de narration replies,
apercu de voix (lecture puis arret), selection de pages (sans RIEN supprimer), retour, debordement.
Usage : python test_bibliotheque_ui.py      Verdict chiffre en sortie.
"""
import os, sys
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
URL = "http://127.0.0.1:8190/manga"
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w, h in ((1280, 900), (360, 780)):
        print("=== %d px" % w)
        c = b.new_context(viewport={"width": w, "height": h}, has_touch=(w < 400), is_mobile=(w < 400))
        pg = c.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(URL + "#k=" + KEY)
        pg.wait_for_timeout(2500)
        pg.evaluate("() => { try { localStorage.removeItem('manga_serie'); } catch {} }")
        pg.click('nav button[data-tab="tChap"]')
        pg.wait_for_selector("#chapList [data-serie]", timeout=15000)
        series = pg.eval_on_selector_all("#chapList [data-serie]", "els => els.map(e => e.dataset.serie)")
        check("series listees (une carte par manga)", len(series) == len(set(series)) and "one-punch-man" in series, series)
        check("aucun chapitre melange aux series", pg.eval_on_selector_all("#chapList [data-chap]", "e => e.length") == 0)
        pg.wait_for_timeout(1500)
        poch = pg.eval_on_selector('#chapList [data-serie="claymore"] img', "i => [i.naturalWidth, i.src.includes('pochette')]")
        check("pochette officielle affichee (claymore)", poch[0] > 0 and poch[1], poch)
        # v1.77.0 : annees sur la carte, chapitres ranges par tome
        carte = pg.inner_text('#chapList [data-serie="claymore"]')
        check("carte Claymore : 2001–2014 · terminé · 27 tomes", "2001–2014" in carte and "terminé" in carte and "27 tomes" in carte, carte.replace("\n", " | "))
        pg.click('#chapList [data-serie="claymore"]'); pg.wait_for_timeout(1200)
        tete = pg.query_selector("#chapList .tome-tete")
        check("Claymore : chapitre range sous « Tome 1 » avec sa couverture",
              tete is not None and "Tome 1" in tete.inner_text()
              and pg.eval_on_selector("#chapList .tome-tete img", "i => i.naturalWidth") > 0)
        pg.click("#btnLibBack"); pg.wait_for_timeout(300)
        pg.click('#chapList [data-serie="one-punch-man"]')
        pg.wait_for_timeout(500)
        check("OPM : chapitres « Hors tome »", "Hors tome" in pg.inner_text("#chapList"))
        chaps = pg.eval_on_selector_all("#chapList [data-chap]", "e => e.length")
        check("la serie montre SES chapitres (OPM = 2)", chaps == 2 and pg.is_visible("#libNav"), chaps)
        pg.reload(); pg.wait_for_timeout(3500)
        check("serie ouverte memorisee apres rechargement",
              pg.eval_on_selector_all("#chapList [data-chap]", "e => e.length") == 2 and pg.is_visible("#libNav"))
        pg.click("#chapList [data-chap] >> nth=1")         # ch_301 (tri par numero)
        pg.wait_for_selector("#chapDetail:not([hidden])", timeout=15000)
        pg.wait_for_timeout(2500)
        essais = pg.query_selector("#narrRuns details.narr-essais")
        check("essais techniques replies", essais is not None and not essais.get_attribute("open"))
        check("titre du chapitre = 301", "301" in pg.inner_text("#chapTitle"), pg.inner_text("#chapTitle"))
        # v1.77.0 : supprimer une narration depuis l'interface (un essai de banc devenu inutile, -> corbeille)
        cible = pg.evaluate("() => NARRS.findIndex(n => n.tag === 'k3-noms-v3-a')")
        if cible >= 0:
            pg.once("dialog", lambda d: d.accept())
            pg.click("#narrRuns details.narr-essais summary")
            pg.click('#narrRuns [data-suppr-narr="%d"]' % cible); pg.wait_for_timeout(1500)
            check("narration supprimee depuis l'app", pg.evaluate("() => !NARRS.some(n => n.tag === 'k3-noms-v3-a')")
                  and not os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sources",
                                                      "one-punch-man", "ch_301", "narration", "k3-noms-v3-a")))
        check("chaque narration terminee a son bouton 🗑",
              pg.evaluate("() => NARRS.filter(n => n.etat !== 'en cours').length === document.querySelectorAll('#narrRuns [data-suppr-narr]').length"))
        # apercu de voix
        pg.select_option("#narrVoice", "Fenrir")
        pg.click("#btnVoixApercu"); pg.wait_for_timeout(1500)
        etat = pg.evaluate("() => [APERCU.paused, APERCU.currentTime, decodeURIComponent(APERCU.src).includes('_apercus/Fenrir.mp3')]")
        check("apercu de voix en lecture", etat[0] is False and etat[1] > 0 and etat[2], etat)
        check("bouton passe a l'arret", pg.inner_text("#btnVoixApercu").strip() == "■")
        pg.click("#btnVoixApercu"); pg.wait_for_timeout(300)
        check("apercu arrete", pg.evaluate("() => APERCU.paused") and pg.inner_text("#btnVoixApercu").strip() == "▶")
        # v1.78.0 : clic sur une page = visionneuse DANS l'app (plus d'onglet), zoom, navigation
        onglets = []
        c.on("page", lambda np: onglets.append(np))
        f0 = pg.locator("#chapPages figure").nth(0)
        f0.evaluate("e => e.scrollIntoView({block: 'center', behavior: 'instant'})"); pg.wait_for_timeout(200)
        bb = f0.bounding_box(); pg.mouse.click(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2)
        pg.wait_for_timeout(700)
        check("page -> visionneuse dans l'app, aucun onglet", pg.is_visible("#lightbox") and not onglets
              and pg.evaluate("() => LB === 0 && $('lbImg').naturalWidth > 0"))
        wb = pg.locator("#lbWrap").bounding_box()
        if w > 400:
            pg.mouse.move(wb["x"] + wb["width"] / 2, wb["y"] + wb["height"] / 3)
            pg.mouse.wheel(0, -300); pg.wait_for_timeout(300)
            check("molette = zoom", pg.evaluate("() => Z.k > 1"), pg.evaluate("() => Z.k"))
            pg.keyboard.press("ArrowRight"); pg.wait_for_timeout(300)
            check("fleche -> page suivante, zoom remis a 1", pg.evaluate("() => LB === 1 && Z.k === 1"))
        else:
            cdp = c.new_cdp_session(pg)
            def glisse(x0, x1, y):
                cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x0, "y": y}]})
                for i in range(1, 6):
                    cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x0 + (x1 - x0) * i / 5, "y": y}]})
                cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
                pg.wait_for_timeout(400)
            cx, cy = wb["x"] + wb["width"] / 2, wb["y"] + wb["height"] / 2
            glisse(cx + 100, cx - 100, cy)
            check("balayage a gauche (doigt) -> page suivante", pg.evaluate("() => LB") == 1, pg.evaluate("() => LB"))
            glisse(cx - 100, cx + 100, cy)
            check("balayage a droite -> page precedente", pg.evaluate("() => LB") == 0, pg.evaluate("() => LB"))
            cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": cx - 30, "y": cy, "id": 1}, {"x": cx + 30, "y": cy, "id": 2}]})
            for i in range(1, 6):
                cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": cx - 30 - 16 * i, "y": cy, "id": 1}, {"x": cx + 30 + 16 * i, "y": cy, "id": 2}]})
            cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []}); pg.wait_for_timeout(300)
            k = pg.evaluate("() => Z.k")
            check("pincee (2 doigts) = zoom", k > 1.5, k)
            glisse(cx + 100, cx - 100, cy)
            check("zoome, le glisse deplace l'image et ne tourne PAS la page", pg.evaluate("() => LB") == 0)
        pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
        check("Echap ferme la visionneuse", not pg.is_visible("#lightbox"))
        # selection de pages : rien n'est supprime
        pg.click("#btnPagesSel")
        def clic_page(k):
            # Clic SOURIS au centre de la page, une fois centree a l'ecran (comme un utilisateur).
            # Mesure du 21/09 : centree, c'est bien l'IMG qui est sous le point ; c'est le re-defilement
            # automatique de Playwright qui la glissait sous l'en-tete fixe (clic intercepte, test bloque).
            # behavior 'instant' : l'app defile en DOUCEUR ; mesurer en pleine animation = cliquer l'en-tete.
            loc = pg.locator("#chapPages figure").nth(k)
            loc.evaluate("e => e.scrollIntoView({block: 'center', behavior: 'instant'})"); pg.wait_for_timeout(200)
            bb = loc.bounding_box(); pg.mouse.click(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2)
        clic_page(0); clic_page(2)
        n = pg.eval_on_selector_all("#chapPages figure.pg-sel", "e => e.length")
        check("selection de 2 pages", n == 2 and "(2)" in pg.inner_text("#btnPagesDel") and not pg.is_visible("#btnPagePoch"), n)
        clic_page(2)
        etat = pg.evaluate("() => [PAGES_SEL ? [...PAGES_SEL] : null, $('btnPagePoch').hidden, $('btnPagesDel').textContent]")
        check("1 page -> bouton pochette propose", pg.is_visible("#btnPagePoch"), etat)
        pg.click("#btnPagesSel")
        check("sortie de selection", pg.eval_on_selector_all("#chapPages figure.pg-sel", "e => e.length") == 0
              and not pg.is_visible("#btnPagesDel"))
        # retour aux series
        pg.click("#btnLibBack"); pg.wait_for_timeout(400)
        check("retour a toutes les series", pg.eval_on_selector_all("#chapList [data-serie]", "e => e.length") == len(series)
              and not pg.is_visible("#chapDetail"))
        dep = pg.evaluate("() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]")
        check("pas de debordement horizontal", dep[0] <= dep[1], dep)
        check("aucune erreur JS", not errs, errs[:2])
        pg.screenshot(path=os.path.join(os.environ["TEMP"], "bib_%d.png" % w))
        pg.evaluate("() => { try { localStorage.removeItem('manga_serie'); } catch {} }")
        c.close()
    b.close()
print("\n=== VERDICT : %d/%d" % (len(OK), len(OK) + len(KO)) + ("" if not KO else "  ECHECS : " + ", ".join(KO)))
sys.exit(1 if KO else 0)
