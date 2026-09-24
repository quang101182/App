# -*- coding: utf-8 -*-
"""Banc UI du panneau « Vidéos de la série » (v2.32.0, maquette_ensemble_v1 ecran 3) sur l'APP REELLE, PC 1280 puis tel 360.

NE GENERE, NE REFAIT, NE SUPPRIME AUCUNE VIDEO (toute requete POST /manga/video* fait echouer le banc) : ouvre le panneau,
verifie la disposition, les menus ⋯ (sans cliquer leurs actions), la selection (locale a la page).
Usage : python test_videos_panneau.py [port] [serie]
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
        pg.on("request", lambda r: ecrit.append(r.url) if r.method == "POST" and "/manga/video" in r.url and "video_liste" not in r.url else None)
        pg.goto(URL + "#k=" + KEY); pg.wait_for_timeout(2500)
        avant = pg.evaluate("() => [localStorage.getItem('manga_onglet'), localStorage.getItem('manga_serie')]")
        pg.evaluate("s => { localStorage.setItem('manga_onglet','tChap'); localStorage.setItem('manga_serie', s); }", SERIE)
        pg.reload(); pg.wait_for_timeout(3500)
        pg.click("#btnVideos"); pg.wait_for_timeout(2500)
        check("panneau ouvert", vis(pg, "#vidBox"))
        rt = pg.inner_text("#vidFermer")
        check("retour bleu « ← <serie> »", rt.startswith("←") and len(rt) > 3 and "retour" in pg.get_attribute("#vidFermer", "class"), rt)
        vues = pg.eval_on_selector_all("#vidBox .lib-actions > .btn", "bs => bs.filter(b => b.checkVisibility()).map(b => b.id)")
        check("3 actions en vue : manquantes, sélection, .zip", vues == ["vidManquantes", "vidSel", "vidZip"], vues)
        tops = pg.eval_on_selector_all("#vidBox .lib-actions > .btn, #vidBox .lib-actions .plus", "bs => [...new Set(bs.map(b => Math.round(b.getBoundingClientRect().top)))]")
        check("actions + ⋯ sur une rangée", len(tops) == 1, tops)
        check("périmées et une par une rangées", not vis(pg, "#vidPerimees") and not vis(pg, "#vidDl"))
        pg.click("#vidBox .lib-actions .plus"); pg.wait_for_timeout(200)
        check("⋯ : périmées + une par une", vis(pg, "#vidPerimees") and vis(pg, "#vidDl"))
        pg.keyboard.press("Escape"); pg.wait_for_timeout(100)
        n = pg.eval_on_selector_all("#vidListe .vid-it", "e => e.length")
        check("liste des chapitres", n > 0, n)
        avec = pg.eval_on_selector_all("#vidListe .vid-it", "e => e.filter(x => x.querySelector('[data-vid-voir]')).length")
        if avec:
            li = "#vidListe .vid-it:has([data-vid-voir])"
            check("vidéo prête : ▶ et ⬇ en vue", vis(pg, li + " [data-vid-voir]") and vis(pg, li + " [data-vid-dl]"))
            check("vidéo prête : refaire / supprimer rangés", not vis(pg, li + " [data-vid-suppr]"))
            pg.click(li + " .plus"); pg.wait_for_timeout(200)
            items = pg.eval_on_selector_all(li + " .menu-pan > button", "bs => bs.filter(b => b.checkVisibility()).map(b => b.innerText.trim())")
            check("⋯ de la vidéo : Supprimer en dernier, en rouge", items and "Supprimer" in items[-1]
                  and "rouge" in pg.eval_on_selector(li + " .menu-pan > button:last-child", "b => b.className"), items)
            mp = pg.eval_on_selector(li + " .menu-pan", "e => { const r = e.getBoundingClientRect(); return [r.left, r.right]; }")
            check("menu de la vidéo dans l'écran", mp[0] >= 0 and mp[1] <= w + 0.5, mp)
            pg.keyboard.press("Escape"); pg.wait_for_timeout(100)
        else:
            print("  (aucune vidéo prête dans cette série : lignes ▶/⋯ non vérifiées)")
        check("choix de la sélection rangé", not vis(pg, "#vidTout"))
        pg.click("#vidBox .lot-sel .plus"); pg.wait_for_timeout(200)
        pg.click("#vidRien"); pg.wait_for_timeout(250)
        check("Tout décocher", pg.inner_text("#vidCompte").startswith("0 coché"), pg.inner_text("#vidCompte"))
        pg.click("#vidBox .lot-sel .plus"); pg.click("#vidTout"); pg.wait_for_timeout(250)
        check("Tout cocher", pg.inner_text("#vidCompte").startswith("%d coché" % n), pg.inner_text("#vidCompte"))
        dbd = pg.evaluate("() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
        check("aucun débordement horizontal", dbd <= 0, dbd)
        pg.locator("#vidBox").screenshot(path=os.path.join(ICI, "videos_%d.png" % w))
        pg.click("#vidFermer"); pg.wait_for_timeout(200)
        check("← ferme le panneau", not vis(pg, "#vidBox"))
        check("aucune vidéo demandée ni supprimée", not ecrit, ecrit[:3])
        check("aucune erreur JS", not errs, errs[:2])
        pg.evaluate("a => { ['manga_onglet','manga_serie'].forEach((n, i) => a[i] == null ? localStorage.removeItem(n) : localStorage.setItem(n, a[i])); }", avant)
        c.close()
    b.close()
print("\nVERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
