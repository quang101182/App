# -*- coding: utf-8 -*-
"""Banc v2.50.0 : ALERTE « capture arretee avant son but » + REPRISE en un clic. APP REELLE, 1280 px puis 360 px.
Donnees FICTIVES : /manga/capture_derniere, /manga/pilote_onglets, /manga/pilote et /manga/fetch_capture sont INTERCEPTES
(aucune capture lancee, aucun onglet ouvert, aucun titre reel) ; tout autre POST fait echouer le banc. localStorage restaure.
1. bilan non tenu -> bandeau + pastille ❌, texte (faits, objectif, raison), boutons « ch. 23 » ;
2. bilan tenu / deja vu -> rien ; 3. « Ouvrir » -> un onglet sur l'adresse SANS jeton ;
4. « Reprendre » : refuse tant que l'onglet affiche la verification ; sinon relance au ch. 23, depuis la PAGE 1, objectif garde ;
5. ✕ -> bandeau et pastille disparaissent, et ne reviennent pas au rechargement ; 6. 360 px : aucun debordement.
Usage : python test_capture_alerte_ui.py [port]
"""
import json, os, sys
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = sys.argv[1] if len(sys.argv) > 1 else "8190"
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


URL23 = "https://site.test/serie/chapter-23/"
BILAN = {"fin": 1790300000.5, "titre": "Serie Banc", "chapitre_depart": "1", "suite": 0, "jusqua": "40", "code": 2,
         "arret": "le chapitre 23 a échoué (code 2)", "faits": [str(i) for i in range(1, 23)], "tenu": False,
         "reprise": {"chapitre": "23", "url": URL23, "page1": False, "entiers": True, "jusqua": "40"}}

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w, h in ((1280, 900), (360, 780)):
        print("=== %d px" % w)
        c = b.new_context(viewport={"width": w, "height": h}, is_mobile=w < 400, has_touch=w < 400)
        pg = c.new_page()
        E = {"bilan": dict(BILAN), "titre_onglet": "Just a moment...", "pilote": [], "capture": [], "autres": [], "dialogs": [], "fen": [], "grande": True, "encours": False}
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))

        def route(rt):
            u, m = rt.request.url, rt.request.method
            if "/manga/fetch_status" in u and m == "GET":                   # v2.55.0 : une capture tourne-t-elle ?
                return rt.fulfill(status=200, content_type="application/json", body=json.dumps({"etat": "en cours" if E["encours"] else "aucune"}))
            if "/manga/capture_derniere" in u:
                return rt.fulfill(status=200, content_type="application/json", body=json.dumps(E["bilan"]))
            if "/manga/pilote_onglets" in u:
                return rt.fulfill(status=200, content_type="application/json", body=json.dumps(
                    {"edge": True, "capture": False, "onglets": [{"id": "o1", "titre": E["titre_onglet"], "url": URL23 + "?__cf_chl_rt_tk=x"}]}))
            if m == "POST" and "/manga/pilote" in u:
                corps = json.loads(rt.request.post_data or "{}")
                if str(corps.get("action", "")).startswith("fenetre_"):     # v2.52.0 : ranger + taille, notes dans l'ordre
                    E["fen"].append(corps["action"])
                    return rt.fulfill(status=200, content_type="application/json", body=json.dumps(
                        {"ok": True, "assez_grande": E["grande"], "reduite": False, "interieur": [1400 if E["grande"] else 600, 900]}))
                E["pilote"].append(corps)
                return rt.fulfill(status=200, content_type="application/json", body='{"ok": true, "id": "o1"}')
            if m == "POST" and "/manga/fetch_capture" in u:
                E["capture"].append(json.loads(rt.request.post_data or "{}"))
                return rt.fulfill(status=200, content_type="application/json", body='{"ok": true}')
            if m == "POST" and "/manga/fetch_status" not in u and not any(k in u for k in ("activite", "costs", "savelog", "espace_fenetre")):
                E["autres"].append(u)
                return rt.abort()
            if m == "POST" and "espace_fenetre" in u:           # fenVerifier : l'etat de la fenetre (lecture) -> « assez grande »
                return rt.fulfill(status=200, content_type="application/json", body='{"assez_grande": true, "reduite": false}')
            return rt.continue_()
        pg.route("**/*", route)

        def dlg(d):
            E["dialogs"].append(d.message); d.accept()
        pg.on("dialog", dlg)
        pg.goto("http://127.0.0.1:%s/manga#k=%s" % (PORT, KEY)); pg.wait_for_timeout(2500)
        avant = pg.evaluate("() => localStorage.getItem('manga_cap_vu')")
        pg.evaluate("() => localStorage.removeItem('manga_cap_vu')"); pg.reload(); pg.wait_for_timeout(5000)
        check("version = VERSION du code", pg.inner_text("#verBadge").strip() == "v" + pg.evaluate("() => VERSION"))
        vis = lambda s: pg.eval_on_selector(s, "e => !e.hidden && e.getBoundingClientRect().width > 0")
        check("bilan NON tenu → bandeau visible", vis("#capAlerte"))
        check("pastille ❌ sur l'activité", vis("#actErr"))
        t = pg.inner_text("#capAlerteTxt")
        check("texte : titre, 22 faits, objectif ch. 40, raison", "Serie Banc" in t and "22 chapitre(s)" in t and "ch. 40" in t and "23 a échoué" in t, t)
        check("boutons nommés « ch. 23 »", "ch. 23" in pg.inner_text("#capAlerteOuvrir") and "ch. 23" in pg.inner_text("#capAlerteReprendre"))
        check("aucun débordement horizontal", pg.evaluate("() => document.documentElement.scrollWidth <= innerWidth"))
        # 3. Ouvrir
        pg.click("#capAlerteOuvrir"); pg.wait_for_timeout(800)
        check("« Ouvrir » : un onglet sur l'adresse du ch. 23 (sans jeton)", E["pilote"] == [{"action": "nouvel", "url": URL23}], E["pilote"])
        # 4. Reprendre : la verification est encore affichee -> refus, rien ne part
        n0 = len(E["dialogs"])
        pg.click("#capAlerteReprendre"); pg.wait_for_timeout(800)
        check("« Reprendre » REFUSE tant que le site affiche sa vérification", not E["capture"]
              and any("vérification" in d for d in E["dialogs"][n0:]), E["dialogs"][n0:])
        E["titre_onglet"] = "Serie Banc - Chapter 23"
        # v2.52.0 : fenetre restee trop petite -> la reprise NE part PAS
        E["grande"], E["fen"] = False, []
        n1 = len(E["dialogs"])
        pg.click("#capAlerteReprendre"); pg.wait_for_timeout(1500)
        check("fenêtre restée trop petite → reprise bloquée, message", not E["capture"]
              and any("trop petite" in d for d in E["dialogs"][n1:]), E["dialogs"][n1:])
        E["grande"], E["fen"] = True, []
        pg.click("#capAlerteReprendre"); pg.wait_for_timeout(1500)
        check("reprise : fenêtre RANGÉE puis mise à la TAILLE SÛRE, automatiquement", E["fen"] == ["fenetre_ranger", "fenetre_taille"], E["fen"])
        check("… sans question à l'écran (aucune modale ouverte)", pg.evaluate("() => !document.querySelector('.demander:not([hidden]), .modal-q:not([hidden])')"))
        cap = E["capture"][0] if E["capture"] else {}
        check("reprise lancée au ch. 23, jusqu'au 40, sans intermédiaires", cap.get("chapter") == "23" and cap.get("jusqua") == "40"
              and cap.get("suite") == 0 and cap.get("entiers") is True and cap.get("title") == "Serie Banc", cap)
        check("reprise TOUJOURS depuis la page 1 (jamais le milieu du chapitre)", cap.get("page1") is True, cap.get("page1"))
        check("l'onglet visé est celui du ch. 23", (cap.get("tab") or "").startswith(URL23), cap.get("tab"))
        check("la reprise ferme le bandeau", not vis("#capAlerte"))
        # 5. ✕ et memoire
        pg.evaluate("() => { localStorage.removeItem('manga_cap_vu'); capAlerteVerifier(); }"); pg.wait_for_timeout(600)
        pg.click("#capAlerteOk"); pg.wait_for_timeout(300)
        check("✕ → bandeau et pastille disparaissent", not vis("#capAlerte") and not vis("#actErr"))
        pg.reload(); pg.wait_for_timeout(5000)
        check("… et ne reviennent pas au rechargement (même bilan)", not vis("#capAlerte"))
        # v2.55.0 : une capture EN COURS (reprise lancee d'un autre appareil) -> le bilan d'avant est caduc, pas de bandeau
        E["bilan"] = dict(BILAN, fin=1790301111.0); E["encours"] = True
        pg.evaluate("() => capAlerteVerifier()"); pg.wait_for_timeout(600)
        check("capture EN COURS → pas de bandeau « arrêtée » (bilan d'avant caduc)", not vis("#capAlerte") and not vis("#actErr"))
        E["encours"] = False
        pg.evaluate("() => capAlerteVerifier()"); pg.wait_for_timeout(600)
        check("… et il revient si plus rien ne tourne (bilan non tenu, pas encore vu)", vis("#capAlerte"))
        # v2.56.0 : le SITE s'arrete avant l'objectif (ch. 40 pas paru) -> information bleue, ni ❌ ni reprise
        E["bilan"] = dict(BILAN, fin=1790302222.0, reprise=None, code=3, arret="aucun chapitre après le 39 sur ce site (liens de la page)")
        pg.evaluate("() => capAlerteVerifier()"); pg.wait_for_timeout(600)
        t = pg.inner_text("#capAlerteTxt")
        check("fin du SITE : information (bleue), sans ❌ ni reprise", vis("#capAlerte") and pg.evaluate("() => $('capAlerte').classList.contains('info')")
              and not vis("#actErr") and not vis("#capAlerteReprendre") and "s'arrête au ch. 39" in t and "pas encore paru" in t, t)
        # 2. tenu -> rien
        E["bilan"] = dict(BILAN, fin=1790300999.0, tenu=True, reprise=None)
        pg.evaluate("() => capAlerteVerifier()"); pg.wait_for_timeout(600)
        check("bilan TENU → aucun bandeau", not vis("#capAlerte"))
        E["bilan"] = {}
        pg.evaluate("() => capAlerteVerifier()"); pg.wait_for_timeout(600)
        check("aucun bilan → aucun bandeau", not vis("#capAlerte"))
        check("aucune autre écriture (POST inattendu)", not E["autres"], E["autres"][:3])
        check("aucune erreur JS", not errs, errs[:3])
        pg.evaluate("v => { v === null ? localStorage.removeItem('manga_cap_vu') : localStorage.setItem('manga_cap_vu', v); }", avant)
        c.close()
    b.close()

print("\nVERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
