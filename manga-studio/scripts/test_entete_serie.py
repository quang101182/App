# -*- coding: utf-8 -*-
"""Banc UI de l'en-tete d'une serie (v2.29.0, maquette_entete_serie_v1 variante A) sur l'APP REELLE (proxy 8190).

PC 1280 px puis telephone 360 px. N'appuie sur AUCUNE action (ni Masquer, ni Supprimer) : ouvre une serie,
mesure l'en-tete, ouvre/ferme le menu « ⋯ » (clic, clic ailleurs, Echap). Verdict chiffre ; captures dans scripts/.
Usage : python test_entete_serie.py [port]
"""
import os, sys
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = sys.argv[1] if len(sys.argv) > 1 else "8190"
URL = "http://127.0.0.1:%s/manga" % PORT
ICI = os.path.dirname(os.path.abspath(__file__))
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


def boite(pg, sel):
    return pg.eval_on_selector(sel, "e => { const r = e.getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }")


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w, h in ((1280, 900), (360, 780)):
        print("=== %d px" % w)
        c = b.new_context(viewport={"width": w, "height": h}, has_touch=(w < 400), is_mobile=(w < 400))
        pg = c.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(URL + "#k=" + KEY); pg.wait_for_timeout(2500)
        pg.evaluate("() => { try { localStorage.removeItem('manga_serie'); localStorage.setItem('manga_onglet','tChap'); } catch {} }")
        pg.reload(); pg.wait_for_timeout(3000)
        ver = pg.inner_text("#verBadge")
        check("version affichee v2.29.0", ver.strip() == "v2.29.0", ver)
        # la serie la plus fournie (pochette + fiche si possible)
        pg.click("#chapList .serie-item"); pg.wait_for_timeout(1200)
        check("en-tete visible", pg.is_visible("#libNav"))
        check("barre de recherche (et son ↻) masquee en vue serie", not pg.is_visible("#libBarre"))
        check("ligne d'etat « X : N chapitre(s) » masquee", not pg.is_visible("#chapState"))
        rb, rr = boite(pg, "#btnLibBack"), boite(pg, "#btnChapRefresh2")
        check("↻ sur la MEME ligne que le retour", abs(rb[1] - rr[1]) < 6 and pg.is_visible("#btnChapRefresh2"), (rb, rr))
        nav = boite(pg, "#libNav")
        check("retour en haut a gauche (du bloc)", abs(rb[0] - nav[0]) < 4, (rb, nav))
        fonds = pg.evaluate("() => [getComputedStyle($('btnLibBack')).backgroundColor, getComputedStyle($('btnVideos')).backgroundColor]")
        check("retour d'une couleur a part", fonds[0] != fonds[1], fonds)
        nb = pg.inner_text("#libNbChap")
        check("nombre de chapitres affiche", "chapitre" in nb, nb)
        th = boite(pg, "#libSerie")[3]
        check("titre sur une ligne a 1280 (h < 34 px)" if w > 400 else "titre lisible (h < 70 px)", th < (34 if w > 400 else 70), th)
        vis = pg.eval_on_selector_all(".lib-actions > .btn", "bs => bs.filter(b => b.offsetParent).map(b => b.innerText.replace(/\\s+/g,' ').trim())")
        check("4 actions en vue", len(vis) == 4, vis)
        check("menu ferme au depart", not pg.is_visible(".lib-actions .menu-pan"))
        tops = pg.eval_on_selector_all(".lib-actions > .btn, .lib-actions .plus", "bs => bs.map(b => Math.round(b.getBoundingClientRect().top))")
        check("actions + ⋯ sur une seule rangee", len(set(tops)) == 1, tops)
        pg.click(".lib-actions .plus"); pg.wait_for_timeout(200)
        items = pg.eval_on_selector_all(".lib-actions .menu-pan > button", "bs => bs.filter(b => b.offsetParent).map(b => b.innerText.trim())")
        check("⋯ ouvre 5 choix (+ un trait avant Supprimer)", len(items) == 5, items)
        check("Supprimer en DERNIER", items and "Supprimer" in items[-1], items[-1:] if items else "")
        mp = boite(pg, ".lib-actions .menu-pan")
        check("menu entierement dans l'ecran", mp[0] >= 0 and mp[0] + mp[2] <= w + 0.5, mp)
        check("aria-expanded = true", pg.get_attribute(".lib-actions .plus", "aria-expanded") == "true")
        pg.screenshot(path=os.path.join(ICI, "entete_%d.png" % w))
        pg.keyboard.press("Escape"); pg.wait_for_timeout(150)
        check("Echap referme", not pg.is_visible(".lib-actions .menu-pan"))
        pg.click(".lib-actions .plus"); pg.wait_for_timeout(150)
        pg.mouse.click(5, h - 5); pg.wait_for_timeout(150)
        check("clic ailleurs referme", not pg.is_visible(".lib-actions .menu-pan"))
        pg.click(".lib-actions .plus"); pg.wait_for_timeout(150)
        pg.click(".lib-actions .plus"); pg.wait_for_timeout(150)
        check("2e clic sur ⋯ referme", not pg.is_visible(".lib-actions .menu-pan"))
        dbd = pg.evaluate("() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
        check("aucun debordement horizontal", dbd <= 0, dbd)
        pg.click("#btnLibBack"); pg.wait_for_timeout(600)
        check("retour : liste des series + recherche revenue", pg.is_visible("#libBarre") and not pg.is_visible("#libNav")
              and pg.eval_on_selector_all("#chapList .serie-item", "e => e.length") > 0)
        check("aucune erreur JS", not errs, errs[:2])
        c.close()
    b.close()
print("\nVERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
