# -*- coding: utf-8 -*-
"""Banc UI « le reste » (v2.35.0-v2.36.0, maquette_ensemble_v1 ecran 6) sur l'APP REELLE, PC 1280 puis tel 360.

Retours bleus a gauche (Activite, Couts), journal (Copier / Envoyer + ⋯ Exporter, Vider rouge), galerie (↻, 🗑 cache sans
selection), planche (exports dans ⋯), narrations d'OPM 301 (▶ 📥 + ⋯ avec 🗑 rouge en dernier), personnages (supprimer
dans ⋯), et le 🔗 de « Reprendre » : TOUJOURS la fenetre Edge dediee (appels INTERCEPTES : aucun onglet n'est ouvert
chez Quang, aucune fenetre lancee). Ne supprime rien.  Usage : python test_reste_ui.py [port]
"""
import json, os, sys
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = sys.argv[1] if len(sys.argv) > 1 else "8190"
URL = "http://127.0.0.1:%s/manga" % PORT
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


def vis(pg, sel):
    return pg.eval_on_selector(sel, "e => e.checkVisibility({ visibilityProperty: true }) && e.getBoundingClientRect().width > 0")


def onglet(pg, tab):
    if vis(pg, 'nav button[data-tab="%s"]' % tab): pg.click('nav button[data-tab="%s"]' % tab)
    else: pg.click(".nav-plus .plus"); pg.click('.nav-plus [data-go="%s"]' % tab)
    pg.wait_for_timeout(1500)


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w, h in ((1280, 900), (360, 780)):
        print("=== %d px" % w)
        c = b.new_context(viewport={"width": w, "height": h}, has_touch=(w < 400), is_mobile=(w < 400))
        pg = c.new_page()
        errs, ecrit, pilote = [], [], []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("request", lambda r: ecrit.append(r.url) if r.method == "POST" and any(k in r.url for k in ("suppr", "delete", "corbeille")) else None)
        pg.goto(URL + "#k=" + KEY); pg.wait_for_timeout(2500)
        avant = pg.evaluate("() => [localStorage.getItem('manga_onglet'), localStorage.getItem('manga_serie')]")
        pg.evaluate("() => { localStorage.setItem('manga_onglet','tChap'); localStorage.removeItem('manga_serie'); }")
        pg.reload(); pg.wait_for_timeout(3500)
        # --- Activite : retour a gauche
        pg.click("#hdrAct"); pg.wait_for_timeout(600)
        r1, r2 = (pg.eval_on_selector(x, "e => e.getBoundingClientRect().left") for x in ("#actFermer", "#actPanel"))
        check("Activité : retour bleu à gauche", "retour" in pg.get_attribute("#actFermer", "class") and r1 - r2 < 30, (r1, r2))
        pg.click("#actFermer"); pg.wait_for_timeout(200)
        check("Activité : ← ferme", not vis(pg, "#actPanel"))
        # --- Couts
        pg.click("#hdrPlus"); pg.click("#hdrCost"); pg.wait_for_timeout(1500)
        check("Coûts : « ← Retour » bleu", vis(pg, "#coutsFermer") and "retour" in pg.get_attribute("#coutsFermer", "class"))
        pg.click("#coutsFermer"); pg.wait_for_timeout(200)
        # --- 🔗 Reprendre : appels interceptes
        etat = {"edge": False}
        def route(rt):
            u = rt.request.url
            if "/manga/pilote_onglets" in u:
                rt.fulfill(status=200, content_type="application/json", body=json.dumps({"edge": etat["edge"], "onglets": [], "capture": False}))
            elif "/manga/fetch_edge" in u:
                etat["edge"] = True; pilote.append(("fetch_edge", "")); rt.fulfill(status=200, content_type="application/json", body='{"ok":true}')
            elif "/manga/pilote" in u:
                pilote.append(("pilote", rt.request.post_data or "")); rt.fulfill(status=200, content_type="application/json", body='{"ok":true,"id":"x"}')
            else:
                rt.continue_()
        pg.route("**/manga/pilote**", route); pg.route("**/manga/fetch_edge**", route)
        pg.evaluate("() => { window.__ouvert = []; window.open = (...a) => { window.__ouvert.push(a[0]); return null; }; }")
        slug = pg.evaluate("() => { const e = derniersLiens().find(y => y.actifs && y.actifs.length); return e ? e.s : null; }")
        if slug:
            pg.evaluate("s => ouvrirDernierLien(s)", slug); pg.wait_for_timeout(2500)
            nouvel = [x for x in pilote if x[0] == "pilote" and '"nouvel"' in x[1]]
            check("🔗 fenêtre fermée : elle est d'abord ouverte", ("fetch_edge", "") in pilote, pilote[:3])
            check("🔗 puis le site part dans la fenêtre dédiée (pilote/nouvel)", len(nouvel) == 1, nouvel[:1])
            check("🔗 jamais dans le navigateur courant", not pg.evaluate("() => window.__ouvert.length"))
        else:
            print("  (aucun lien de reprise enregistré : 🔗 non vérifié)")
        pg.unroute("**/manga/pilote**"); pg.unroute("**/manga/fetch_edge**")
        # --- narrations (OPM 301)
        if pg.is_visible("#btnLibBack"): pg.click("#btnLibBack"); pg.wait_for_timeout(300)
        pg.fill("#libRech", ""); pg.type("#libRech", "armure blue", delay=20); pg.wait_for_timeout(1500)
        pg.click("#libTexte [data-rtxt] >> nth=0"); pg.wait_for_timeout(3000)
        li = "#narrRuns .narr-run:has([data-ecoute])"
        check("narration : ▶ et 📥 en vue", vis(pg, li + " [data-ecoute]") and vis(pg, li + " [data-hl]"))
        check("narration : 🗑 rangé", not vis(pg, li + " [data-suppr-narr]"))
        pg.click(li + " .plus"); pg.wait_for_timeout(200)
        items = pg.eval_on_selector_all(li + " .menu-pan > button", "bs => bs.filter(b => b.checkVisibility()).map(b => [b.innerText.trim(), b.className])")
        check("narration : ⋯ finit par Supprimer, en rouge", items and "Supprimer" in items[-1][0] and "rouge" in items[-1][1], items)
        mp = pg.eval_on_selector(li + " .menu-pan", "e => { const r = e.getBoundingClientRect(); return [r.left, r.right]; }")
        check("narration : menu dans l'écran", mp[0] >= 0 and mp[1] <= w + 0.5, mp)
        pg.keyboard.press("Escape")
        # --- galerie
        onglet(pg, "tGal")
        check("galerie : ↻ en icône", pg.inner_text("#btnRefreshGal").strip() == "↻")
        check("galerie : 🗑 caché sans sélection", not vis(pg, "#btnGalDel"))
        # --- planche : exports dans ⋯
        onglet(pg, "tPlate")
        check("planche : exports rangés", not vis(pg, "#btnExport") and not vis(pg, "#btnExportPdf"))
        pg.click("#btnExport >> xpath=ancestor::div[contains(@class,'menu-plus')][1]//button[contains(@class,'plus')]"); pg.wait_for_timeout(200)
        check("planche : ⋯ → PNG et PDF", vis(pg, "#btnExport") and vis(pg, "#btnExportPdf"))
        pg.keyboard.press("Escape")
        pg.click("#btnDelPage >> xpath=ancestor::div[contains(@class,'menu-plus')][1]//button[contains(@class,'plus')]"); pg.wait_for_timeout(200)
        mp = pg.eval_on_selector("#btnDelPage >> xpath=ancestor::div[contains(@class,'menu-pan')][1]", "e => { const r = e.getBoundingClientRect(); return [r.left, r.right]; }")
        check("planche : ⋯ de la planche dans l'écran (QA : sortait à gauche)", mp[0] >= 0 and mp[1] <= w + 0.5, mp)
        pg.keyboard.press("Escape")
        check("planche : suppression de planche rangée (rouge)", not vis(pg, "#btnDelPage") and "rouge" in pg.get_attribute("#btnDelPage", "class"))
        # --- journal (onglet Reglages)
        onglet(pg, "tSet")
        check("journal : Copier et Envoyer en vue", vis(pg, "#btnCopyLog") and vis(pg, "#btnSendLog"))
        check("journal : Vider rangé, en rouge", not vis(pg, "#btnClearLog") and "rouge" in pg.get_attribute("#btnClearLog", "class"))
        # --- personnages : supprimer dans ⋯
        onglet(pg, "tPerso")
        n = pg.eval_on_selector_all("#charList [data-chdel]", "e => e.length")
        if n:
            check("personnages : supprimer rangé dans ⋯ (rouge)", not vis(pg, "#charList [data-chdel]")
                  and "rouge" in pg.eval_on_selector("#charList [data-chdel]", "b => b.className"))
        dbd = pg.evaluate("() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
        check("aucun débordement horizontal", dbd <= 0, dbd)
        check("rien supprimé", not ecrit, ecrit[:3])
        check("aucune erreur JS", not errs, errs[:2])
        pg.evaluate("a => { ['manga_onglet','manga_serie'].forEach((n, i) => a[i] == null ? localStorage.removeItem(n) : localStorage.setItem(n, a[i])); }", avant)
        c.close()
    b.close()
print("\nVERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
