# -*- coding: utf-8 -*-
"""Banc UI de la page principale (v2.30.0, maquette_ensemble_v1 lot 1) sur l'APP REELLE, PC 1280 px puis telephone 360 px.

En-tete : mode, activite, Local et VRAM visibles EN PERMANENCE (Quang 22h32-22h33), couts et ℹ️ dans ⋯.
Onglets : PC tout visible sur une ligne ; telephone 4 + « ⋯ Plus » qui mene aux onglets rares. Capture = gros bouton vert,
↻ dans la recherche, compteur a droite du tri. Alerte de fin de traitement (rendu force, puis « j'ai vu » retenu).
Ne lance rien, ne supprime rien ; restaure l'onglet et la cle « manga_lot_vu » d'avant.
Usage : python test_page_principale.py [port]
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


def vis(pg, sel):
    return pg.eval_on_selector(sel, "e => !!e.offsetParent && e.getBoundingClientRect().width > 0")


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w, h in ((1280, 900), (360, 780)):
        print("=== %d px" % w)
        c = b.new_context(viewport={"width": w, "height": h}, has_touch=(w < 400), is_mobile=(w < 400))
        pg = c.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(URL + "#k=" + KEY); pg.wait_for_timeout(2500)
        avant = pg.evaluate("() => [localStorage.getItem('manga_onglet'), localStorage.getItem('manga_lot_vu'), localStorage.getItem('manga_serie')]")
        pg.evaluate("() => { localStorage.setItem('manga_onglet','tChap'); localStorage.removeItem('manga_serie'); }")
        pg.reload(); pg.wait_for_timeout(3500)
        check("version v2.30.0", pg.inner_text("#verBadge").strip() == "v2.30.0")
        for sel, nom in (("#hdrMode", "mode ☁/🖥"), ("#hdrAct", "activite"), ("#engComfy", "Local"), (".vram", "VRAM"), ("#hdrPlus", "⋯")):
            check(nom + " visible en permanence", vis(pg, sel))
        check("couts et ℹ️ caches (dans ⋯)", not vis(pg, "#hdrCost") and not vis(pg, "#btnAide"))
        hh = pg.eval_on_selector("header", "e => e.getBoundingClientRect().height")
        check("en-tete compact (PC 1 ligne < 56 px ; tel 2 lignes < 96 px)", hh < (56 if w > 400 else 96), round(hh))
        pg.click("#hdrPlus"); pg.wait_for_timeout(200)
        check("⋯ montre les couts et les explications", vis(pg, "#hdrCost") and vis(pg, "#btnAide"),
              pg.inner_text(".hdr-plus .menu-pan").replace("\n", " | "))
        mp = pg.eval_on_selector(".hdr-plus .menu-pan", "e => { const r = e.getBoundingClientRect(); return [r.left, r.right]; }")
        check("menu de l'en-tete dans l'ecran", mp[0] >= 0 and mp[1] <= w + 0.5, mp)
        pg.keyboard.press("Escape"); pg.wait_for_timeout(150)
        # onglets
        onglets = pg.eval_on_selector_all("nav button[data-tab]", "bs => bs.filter(b => b.offsetParent).map(b => b.dataset.tab)")
        tops = pg.eval_on_selector_all("nav button[data-tab], nav .nav-plus", "bs => [...new Set(bs.filter(b => b.offsetParent).map(b => Math.round(b.getBoundingClientRect().top)))]")
        if w > 400:
            check("PC : les 8 onglets visibles", len(onglets) == 8, onglets)
            check("PC : ⋯ Plus absent", not vis(pg, ".nav-plus"))
            check("PC : groupe « Créer » après Bibliothèque", pg.eval_on_selector_all("nav .nav-grp", "e => e.filter(x => x.offsetParent).length") == 1)
        else:
            check("tel : 4 onglets + ⋯ Plus", onglets == ["tChap", "tPlate", "tProj", "tPerso"] and vis(pg, ".nav-plus"), onglets)
            lib = pg.eval_on_selector_all("nav button[data-tab], .nav-plus .plus", "bs => bs.filter(b => b.offsetParent).map(b => b.innerText.replace(/\\s+/g,' ').trim())")
            check("tel : chaque onglet a son mot", all(len(x.split(" ")) >= 2 for x in lib), lib)
            pg.click(".nav-plus .plus"); pg.wait_for_timeout(200)
            items = pg.eval_on_selector_all(".nav-plus .menu-pan > button", "bs => bs.filter(b => b.offsetParent).map(b => b.dataset.go)")
            check("tel : ⋯ Plus ouvre Ingestion, Validé, Galerie, Réglages", items == ["tIng", "tVal", "tGal", "tSet"], items)
            pg.click('.nav-plus [data-go="tGal"]'); pg.wait_for_timeout(500)
            check("tel : Galerie ouverte depuis ⋯", pg.evaluate("() => $('tGal').classList.contains('sel')"))
            check("tel : ⋯ Plus marque l'onglet actif", pg.eval_on_selector(".nav-plus .plus", "e => e.classList.contains('sel')"))
            check("tel : menu referme apres le choix", not vis(pg, ".nav-plus .menu-pan"))
            pg.click('nav button[data-tab="tChap"]'); pg.wait_for_timeout(1200)
            check("tel : retour Bibliotheque, ⋯ n'est plus actif", not pg.eval_on_selector(".nav-plus .plus", "e => e.classList.contains('sel')"))
        check("onglets sur UNE ligne", len(tops) == 1, tops)
        # bibliotheque
        pg.evaluate("() => { $('capBox').open = false; }"); pg.wait_for_timeout(150)
        fond = pg.eval_on_selector("#capBox > summary", "e => getComputedStyle(e).backgroundColor")
        check("capture = gros bouton vert", fond.startswith("rgb(63, 191, 127)"), fond)
        rr, ri = pg.eval_on_selector("#btnChapRefresh", "e => e.getBoundingClientRect().right"), pg.eval_on_selector("#libRech", "e => e.getBoundingClientRect().right")
        check("↻ DANS la barre de recherche", vis(pg, "#btnChapRefresh") and rr <= ri + 0.5, (rr, ri))
        ct = pg.eval_on_selector("#chapState", "e => [e.getBoundingClientRect().top, e.innerText]")
        tt = pg.eval_on_selector("#libTri", "e => e.getBoundingClientRect().top")
        if w > 400: check("compteur sur la ligne du tri", abs(ct[0] - tt) < 14 and "série" in ct[1], ct)
        else: check("tel : compteur dans le bloc du tri", pg.eval_on_selector("#chapState", "e => !!e.closest('#libOutils')") and "série" in ct[1], ct)
        pg.click("#btnChapRefresh"); pg.wait_for_timeout(1500)
        check("↻ relit la bibliotheque", pg.eval_on_selector_all("#chapList .serie-item", "e => e.length") > 0)
        # alerte de fin de traitement (rendu force : l'etat reel du serveur n'est pas modifie)
        pg.evaluate("""() => { LOT_ALERTE = { cle: 'banc-1', serie: 'claymore', ps: { etat: 'fini', fin: Date.now() / 1000,
             erreurs: [{ num: '1', res: { video: 'echec : chapitre introuvable' } }] } }; lotAlerteRendre(); }""")
        pg.wait_for_timeout(100)
        check("alerte : bandeau visible", vis(pg, "#lotAlerte"), pg.inner_text("#lotAlerteTxt"))
        check("alerte : pastille ❌ sur l'activite", vis(pg, "#actErr"))
        check("alerte : dit quoi (vidéo)", "vidéo" in pg.inner_text("#lotAlerteTxt"))
        pg.click("#lotAlerteOk"); pg.wait_for_timeout(100)
        check("alerte : ✕ la ferme et retient « vu »", not vis(pg, "#lotAlerte") and not vis(pg, "#actErr")
              and pg.evaluate("() => localStorage.getItem('manga_lot_vu')") == "banc-1")
        r = pg.evaluate("async () => { try { await lotAlerteVerifier(); return ['ok', !!LOT_ALERTE]; } catch (e) { return ['err', e.message]; } }")
        check("alerte : lecture de l'etat reel sans erreur", r[0] == "ok", r)
        dbd = pg.evaluate("() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
        check("aucun debordement horizontal", dbd <= 0, dbd)
        pg.screenshot(path=os.path.join(ICI, "principale_%d.png" % w))
        check("aucune erreur JS", not errs, errs[:2])
        pg.evaluate("""a => { const k = ['manga_onglet','manga_lot_vu','manga_serie'];
            k.forEach((n, i) => a[i] == null ? localStorage.removeItem(n) : localStorage.setItem(n, a[i])); }""", avant)
        c.close()
    b.close()
print("\nVERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
