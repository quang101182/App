# -*- coding: utf-8 -*-
"""Banc UI « Profil et traitement » (v2.31.0, maquette_ensemble_v1 ecran 2) sur l'APP REELLE, PC 1280 px puis tel 360 px.

N'ENREGISTRE AUCUN REGLAGE et NE LANCE RIEN : ouvre le panneau d'une serie, lit les lignes de reglage, deplie / replie,
joue avec la selection (locale a la page), ouvre les menus. Captures dans scripts/.
Usage : python test_profil_traitement.py [port] [serie]
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
    return pg.eval_on_selector(sel, "e => e.checkVisibility({ contentVisibilityAuto: true, visibilityProperty: true }) && e.getBoundingClientRect().width > 0")


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w, h in ((1280, 900), (360, 780)):
        print("=== %d px" % w)
        c = b.new_context(viewport={"width": w, "height": h}, has_touch=(w < 400), is_mobile=(w < 400))
        pg = c.new_page()
        errs, ecrit = [], []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("request", lambda r: ecrit.append(r.url) if r.method == "POST" and ("suivi_config" in r.url or "suivi_lancer" in r.url
                                                                                   or "profil" in r.url) else None)
        pg.goto(URL + "#k=" + KEY); pg.wait_for_timeout(2500)
        avant = pg.evaluate("() => [localStorage.getItem('manga_onglet'), localStorage.getItem('manga_serie')]")
        pg.evaluate("s => { localStorage.setItem('manga_onglet','tChap'); localStorage.setItem('manga_serie', s); }", SERIE)
        pg.reload(); pg.wait_for_timeout(3500)
        check("version = VERSION du code", pg.inner_text("#verBadge").strip() == "v" + pg.evaluate("() => VERSION"))
        pg.click("#btnSuivi"); pg.wait_for_timeout(2500)
        check("panneau ouvert", vis(pg, "#suiviBox"))
        rt = pg.inner_text("#suiviFermer")
        check("retour bleu « ← <serie> »", rt.startswith("←") and len(rt) > 3 and "retour" in pg.get_attribute("#suiviFermer", "class"), rt)
        rb, nb = (pg.eval_on_selector(x, "e => e.getBoundingClientRect().left") for x in ("#suiviFermer", "#suiviBox"))
        check("retour en haut a gauche du panneau", abs(rb - nb) < 4, (rb, nb))
        vals = pg.eval_on_selector_all("#suiviBox details.prof-l > summary", "ss => ss.map(s => s.innerText.replace(/\\s+/g,' ').trim())")
        check("5 lignes de reglage", len(vals) == 5, vals)
        vv = pg.eval_on_selector_all("#suiviBox [data-v]", "e => e.map(x => x.textContent.trim())")
        check("chaque ligne montre sa valeur actuelle", len(vv) == 5 and all(vv), vv)
        check("reglages replies au depart (champs caches)", not vis(pg, "#suiviMoteur"))
        pg.click("#suiviBox details.bloc-narr > summary"); pg.wait_for_timeout(200)
        check("toucher Narration deplie ses champs", vis(pg, "#suiviMoteur") and vis(pg, "#suiviVoix"))
        pg.click("#suiviBox details.bloc-narr > summary"); pg.wait_for_timeout(200)
        check("retoucher la replie", not vis(pg, "#suiviMoteur"))
        check("« La nuit » = une ligne a bascule", vis(pg, "#suiviActif") and "bascule" in pg.get_attribute("#suiviActif", "class"))
        # ⋯ du panneau
        pg.click("#suiviBox .pan-barre .plus"); pg.wait_for_timeout(200)
        check("⋯ : défauts + journal", vis(pg, "#profDefSet") and vis(pg, "#profDefGet") and vis(pg, "#profJournalVoir"))
        pg.click("#profJournalVoir"); pg.wait_for_timeout(400)
        check("journal ouvert depuis ⋯", pg.eval_on_selector("#suiviBox .suivi-jr", "d => d.open"))
        pg.evaluate("() => { document.querySelector('#suiviBox .suivi-jr').open = false; }")
        # tout traiter
        check("portée (3 choix) visible", vis(pg, "#lotPortee") and pg.eval_on_selector_all("#lotPortee [data-p]", "e => e.length") == 3)
        n = pg.eval_on_selector_all("#lotPuces .lot-puce", "e => e.length")
        check("chapitres listés", n > 0, n)
        check("outils de sélection rangés (caches)", not vis(pg, "#lotTout"))
        pg.click("#lotSelbar .plus"); pg.wait_for_timeout(200)
        check("⋯ Choisir : tout / rien / plage / refaire", all(vis(pg, x) for x in ("#lotTout", "#lotRien", "#lotDe", "#lotA", "#lotPlage", "#lotRefaire")))
        pg.click("#lotDe"); pg.wait_for_timeout(150)
        check("taper dans la plage ne referme pas le menu", vis(pg, "#lotTout"))
        pg.click("#lotTout"); pg.wait_for_timeout(300)
        cpt = pg.inner_text("#lotCompte")
        check("Tout sélectionner", cpt.startswith("%d / %d" % (n, n)), cpt)
        check("le menu se referme après le choix", not vis(pg, "#lotTout"))
        pg.click("#lotSelbar .plus"); pg.click("#lotRien"); pg.wait_for_timeout(300)
        check("Tout désélectionner", pg.inner_text("#lotCompte").startswith("0 /"), pg.inner_text("#lotCompte"))
        pg.click('#lotPortee [data-p="restant"]'); pg.wait_for_timeout(300)
        fond = pg.eval_on_selector("#suiviLancer", "e => getComputedStyle(e).backgroundColor")
        check("UN gros bouton vert « Lancer »", fond.startswith("rgb(63, 191, 127)")
              and pg.eval_on_selector("#suiviLancer", "e => e.getBoundingClientRect().height") >= 44, fond)
        if w < 400:
            lw = pg.eval_on_selector("#suiviLancer", "e => e.getBoundingClientRect().width")
            cw = pg.eval_on_selector("#suiviBox .prof-lot", "e => e.clientWidth")
            check("tel : Lancer sur toute la largeur", lw > cw * 0.8, (lw, cw))
        bil = pg.eval_on_selector("#suiviPassage", "e => [e.className, e.innerText.trim()]")
        check("bilan du dernier passage : bandeau coloré s'il y a un texte", not bil[1] or "bandeau" in bil[0], bil)
        # bandeau rouge force (rendu seul) : Refaire remet « pas terminés »
        pg.evaluate("""() => { SUIVI.passage = Object.assign({}, SUIVI.passage, { vivant: false, etat: 'fini', serie: LIB_SERIE,
            fin: Date.now() / 1000, fait: [], erreurs: [{ d: LIB_SERIE + '/ch_1', num: '1', res: { video: 'echec : banc' } }] });
            SUIVI._rendu = true; suiviRendre(); }""")
        pg.wait_for_timeout(150)
        check("bilan en erreur : bandeau rouge + Refaire", "ko" in pg.get_attribute("#suiviPassage", "class") and vis(pg, "#suiviPassage [data-lot-refaire]"))
        pg.click('#lotPortee [data-p="tout"]'); pg.click("#suiviPassage [data-lot-refaire]"); pg.wait_for_timeout(300)
        check("Refaire -> portée « pas terminés »", pg.evaluate("() => LOT_PORTEE") == "restant")
        dbd = pg.evaluate("() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
        check("aucun debordement horizontal", dbd <= 0, dbd)
        pg.locator("#suiviBox").screenshot(path=os.path.join(ICI, "profil_%d.png" % w))
        pg.click("#suiviFermer"); pg.wait_for_timeout(300)
        check("← ferme le panneau", not vis(pg, "#suiviBox"))
        check("aucun reglage enregistre, rien lance", not ecrit, ecrit[:3])
        check("aucune erreur JS", not errs, errs[:2])
        pg.evaluate("a => { ['manga_onglet','manga_serie'].forEach((n, i) => a[i] == null ? localStorage.removeItem(n) : localStorage.setItem(n, a[i])); }", avant)
        c.close()
    b.close()
print("\nVERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
