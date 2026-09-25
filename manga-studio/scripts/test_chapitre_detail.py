# -*- coding: utf-8 -*-
"""Banc UI du detail d'un chapitre (v2.33.0, maquette_ensemble_v1 ecran 4) + suivi du mode, APP REELLE, PC 1280 puis tel 360.

NE SUPPRIME RIEN et ne change pas le mode (toute requete POST de suppression ou de reglage fait echouer le banc) :
ouvre un chapitre, verifie la barre, les actions, le ⋯, la barre de selection (pages cochees puis relachees) ; le mode
affiche est fausse A LA MAIN dans la page, puis doit revenir tout seul sur celui du serveur.
Usage : python test_chapitre_detail.py [port] [serie]
"""
import os, sys
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = sys.argv[1] if len(sys.argv) > 1 else "8190"
SERIE = sys.argv[2] if len(sys.argv) > 2 else "claymore"
URL = "http://127.0.0.1:%s/manga" % PORT
ICI = os.path.dirname(os.path.abspath(__file__))
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


def vis(pg, sel):
    return pg.eval_on_selector(sel, "e => e.checkVisibility({ visibilityProperty: true }) && e.getBoundingClientRect().width > 0")


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w, h in ((1280, 900), (360, 780)):
        print("=== %d px" % w)
        c = b.new_context(viewport={"width": w, "height": h}, has_touch=(w < 400), is_mobile=(w < 400))
        pg = c.new_page()
        errs, ecrit = [], []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("request", lambda r: ecrit.append(r.url) if r.method == "POST" and any(k in r.url for k in ("suppr", "reglages", "pochette", "corbeille")) else None)
        pg.goto(URL + "#k=" + KEY); pg.wait_for_timeout(2500)
        avant = pg.evaluate("() => [localStorage.getItem('manga_onglet'), localStorage.getItem('manga_serie')]")
        pg.evaluate("s => { localStorage.setItem('manga_onglet','tChap'); localStorage.setItem('manga_serie', s); }", SERIE)
        pg.reload(); pg.wait_for_timeout(3500)
        pg.click("#chapList [data-chap] >> nth=1"); pg.wait_for_selector("#chapDetail:not([hidden])", timeout=15000); pg.wait_for_timeout(2500)
        # v2.39.0 (QA) : a l'ouverture, le retour et les actions ne sont PAS caches sous la barre collee du haut
        bas_barre = pg.eval_on_selector(".topbar", "e => e.getBoundingClientRect().bottom")
        haut_ret = pg.eval_on_selector("#btnChapClose", "e => e.getBoundingClientRect().top")
        check("ouverture : le retour est visible sous la barre collée", haut_ret >= bas_barre - 1, (haut_ret, bas_barre))
        rt = pg.inner_text("#btnChapClose")
        check("retour bleu « ← <serie> »", rt.startswith("←") and len(rt) > 3 and "retour" in pg.get_attribute("#btnChapClose", "class"), rt)
        rb, db = (pg.eval_on_selector(x, "e => e.getBoundingClientRect().left") for x in ("#btnChapClose", "#chapDetail"))
        check("retour à gauche (plus de « Fermer » à droite)", rb - db < 30, (rb, db))
        nv = pg.eval_on_selector_all("#chapPrev, #chapNext", "bs => bs.filter(b => !b.hidden).map(b => Math.round(b.getBoundingClientRect().left))")
        check("chapitres voisins à droite", nv and min(nv) > rb + 60, nv)
        vues = pg.eval_on_selector_all("#chapDetail .chap-actions > .btn", "bs => bs.filter(b => b.checkVisibility()).map(b => b.id)")
        check("3 actions en vue : narration, pages, vidéo", vues == ["chapAllerNarr", "btnPagesSel", "chapAllerVid"], vues)
        tops = pg.eval_on_selector_all("#chapDetail .chap-actions > .btn, #chapDetail .chap-actions .plus", "bs => [...new Set(bs.map(b => Math.round(b.getBoundingClientRect().top)))]")
        check("actions + ⋯ sur une rangée", len(tops) == 1, tops)
        check("Vérifier / Supprimer le chapitre rangés", not vis(pg, "#btnChapVerif") and not vis(pg, "#btnChapDel"))
        pg.click("#chapDetail .chap-actions .plus"); pg.wait_for_timeout(200)
        items = pg.eval_on_selector_all("#chapDetail .chap-actions .menu-pan > button", "bs => bs.map(b => b.id)")
        check("⋯ : Vérifier puis Supprimer le chapitre (rouge, en dernier)", items == ["btnChapVerif", "btnChapDel"]
              and "rouge" in pg.get_attribute("#btnChapDel", "class"), items)
        pg.keyboard.press("Escape"); pg.wait_for_timeout(100)
        y0 = pg.evaluate("() => scrollY")
        pg.click("#chapAllerNarr"); pg.wait_for_timeout(900)
        check("raccourci Narration : descend jusqu'au bloc", pg.evaluate("() => scrollY") > y0 + 50, (y0, pg.evaluate("() => scrollY")))
        pg.evaluate("() => clOuvrir('narr')"); pg.wait_for_timeout(300)   # v2.60.0 : blocs replies par defaut
        if w >= 1000:   # v2.49.0 (QA 25/09) : sur PC aussi, « Kimi K3 — le plus fiabl… » (193 px) -> largeur de base 300 px
            lg = pg.evaluate("() => ['narrEngine', 'narrVoice'].map(i => Math.round($(i).getBoundingClientRect().width))")
            check("Narration PC : moteur et voix assez larges pour être lus (≥ 250 px)", min(lg) >= 250, lg)
            # v2.49.0 (QA 25/09) : un menu ⋯ qui sortirait par le BAS s'ouvre vers le HAUT
            pg.evaluate("() => clOuvrir('mus')"); pg.wait_for_timeout(300)   # v2.60.0 : blocs replies par defaut
            pg.evaluate("() => { const b = document.querySelector('#chapDetail .bloc-mus .menu-plus > .plus');"
                        " scrollBy(0, b.getBoundingClientRect().bottom - innerHeight + 12); }"); pg.wait_for_timeout(300)
            pg.click("#chapDetail .bloc-mus .menu-plus > .plus"); pg.wait_for_timeout(250)
            bas = pg.evaluate("() => { const p = document.querySelector('#chapDetail .bloc-mus .menu-pan'); const r = p.getBoundingClientRect();"
                              " return [Math.round(r.top), Math.round(r.bottom), innerHeight, !p.hidden]; }")
            check("menu ⋯ en bas d'écran : ouvert vers le haut, entièrement visible", bas[3] and bas[0] >= 0 and bas[1] <= bas[2], bas)
            pg.keyboard.press("Escape"); pg.wait_for_timeout(150)
        pg.evaluate("() => clOuvrir('narr')"); pg.wait_for_timeout(300)   # v2.60.0 : blocs replies par defaut
        if w < 400:   # v2.45.0 : Moteur de lecture et Voix ne se partagent plus une ligne (« Kimi K3 — le pl », « Charon — »)
            me, vo = (pg.eval_on_selector(x, "e => { const r = e.getBoundingClientRect(); return [Math.round(r.top), Math.round(r.width)]; }") for x in ("#narrEngine", "#narrVoice"))
            check("Narration 360 px : moteur et voix sur deux lignes, lisibles", me[0] != vo[0] and me[1] >= 250 and vo[1] >= 220, (me, vo))
        pg.evaluate("() => scrollTo(0, 0)"); pg.wait_for_timeout(200)
        # selection de pages
        check("barre de sélection cachée hors sélection", not vis(pg, "#pagesSelBarre"))
        pg.click("#btnPagesSel"); pg.wait_for_timeout(300)
        check("sélection : barre dédiée visible", vis(pg, "#pagesSelBarre") and "Touche" in pg.inner_text("#pagesSelN"))
        check("sélection : bouton devient « Terminer »", "Terminer" in pg.inner_text("#btnPagesSel"))
        pg.locator("#chapPages figure").nth(0).click(); pg.wait_for_timeout(200)
        check("1 page : Pochette proposée", vis(pg, "#btnPagePoch") and vis(pg, "#btnPagesDel"), pg.inner_text("#pagesSelN"))
        pg.locator("#chapPages figure").nth(1).click(); pg.wait_for_timeout(200)
        check("2 pages : « 2 pages », Supprimer (2), plus de Pochette", "2 pages" in pg.inner_text("#pagesSelN")
              and "(2)" in pg.inner_text("#btnPagesDel") and not vis(pg, "#btnPagePoch"))
        bb = pg.eval_on_selector("#pagesSelBarre", "e => e.getBoundingClientRect().bottom")
        check("barre collée en bas de l'écran", bb <= h and bb > h - 60, (bb, h))
        pg.click("#pagesSelFin"); pg.wait_for_timeout(200)
        check("Terminer : sélection vidée, barre cachée", not vis(pg, "#pagesSelBarre")
              and pg.eval_on_selector_all("#chapPages figure.pg-sel", "e => e.length") == 0)
        pg.screenshot(path=os.path.join(ICI, "chapitre_%d.png" % w))
        # mode : fausse la page, il doit revenir sur celui du serveur
        vrai = pg.evaluate("async () => (await api('/manga/reglages')).mode || 'cloud'")
        pg.evaluate("v => { MODE = v === 'pc' ? 'cloud' : 'pc'; modeMaj(); }", vrai)
        pg.evaluate("async () => { await modeSuivre(); }"); pg.wait_for_timeout(200)
        check("mode : une page périmée se recale sur le serveur", pg.evaluate("() => MODE") == vrai
              and pg.eval_on_selector("#hdrMode", "e => e.classList.contains('pc')") == (vrai == "pc"), vrai)
        pg.click("#btnChapClose"); pg.wait_for_timeout(300)
        check("← ferme le chapitre", not vis(pg, "#chapDetail"))
        dbd = pg.evaluate("() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
        check("aucun débordement horizontal", dbd <= 0, dbd)
        check("rien supprimé, aucun réglage écrit", not ecrit, ecrit[:3])
        check("aucune erreur JS", not errs, errs[:2])
        pg.evaluate("a => { ['manga_onglet','manga_serie'].forEach((n, i) => a[i] == null ? localStorage.removeItem(n) : localStorage.setItem(n, a[i])); }", avant)
        c.close()
    b.close()
print("\nVERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
