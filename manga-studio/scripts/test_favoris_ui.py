# -*- coding: utf-8 -*-
"""Banc v3.5.7 : FAVORIS. App REELLE 8190 (page substituee si --page), LECTURE SEULE : les POST sont intercepte et la reponse du
serveur SIMULEE (favoris tenus dans le banc) -- le fichier de bibliotheque de Quang n'est jamais touche. 1280 puis 360 px.
A. ☆ sur chaque carte ; B. toucher ☆ de la 3e serie -> elle passe EN TETE, ★ ; la page de la serie ne s'ouvre PAS ;
C. le tri choisi reste applique dans chaque groupe ; D. page de la serie : ★ a cote du titre, le toucher la retire -> ordre
d'origine ; E. serveur pas encore relance (« action inconnue ») -> l'etoile revient en arriere + message ; 0 erreur JS, 0 debordement.
Usage : python test_favoris_ui.py [--page f.html]"""
import json, os, sys
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
a = sys.argv[1:]; PAGE = None
if "--page" in a:
    i = a.index("--page"); PAGE = open(a[i + 1], encoding="utf-8").read()
OK, KO = [], []


def check(nom, cond, d=""):
    (OK if cond else KO).append(nom); print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(d)[:150] if d else ""), flush=True)


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w, h in ((1280, 900), (360, 780)):
        print("=== %d px" % w)
        c = b.new_context(viewport={"width": w, "height": h}, is_mobile=w < 400, has_touch=w < 400, service_workers="block")
        pg = c.new_page(); errs, etat = [], {"fav": [], "ancien": False, "posts": []}
        pg.on("pageerror", lambda e: errs.append(str(e)))
        def route(rt):
            r = rt.request
            if r.method == "POST" and "/manga/bibliotheque" in r.url:
                d = json.loads(r.post_data or "{}"); etat["posts"].append(d)
                if etat["ancien"]: return rt.fulfill(status=200, body='{"error":"action inconnue"}', content_type="application/json")
                if d.get("action") == "favori" and d["slug"] not in etat["fav"]: etat["fav"].append(d["slug"])
                if d.get("action") == "pas_favori": etat["fav"] = [x for x in etat["fav"] if x != d["slug"]]
                return rt.fulfill(status=200, body=json.dumps({"ok": True, "favoris": etat["fav"], "masquees": [], "ouvertes": {}, "lectures": {}, "videos_pos": {}}), content_type="application/json")
            if r.method == "POST" and not any(k in r.url for k in ("activite", "costs", "fetch_status", "savelog")):
                return rt.fulfill(status=200, body='{"ok":true}', content_type="application/json")
            if PAGE and r.method == "GET" and r.url.split("#")[0].split("?")[0].rstrip("/").endswith("/manga"):
                return rt.fulfill(status=200, body=PAGE, content_type="text/html; charset=utf-8")
            rt.continue_()
        pg.route("**/*", route)
        pg.goto("http://127.0.0.1:8190/manga#k=" + KEY); pg.wait_for_timeout(2500)
        pg.evaluate("() => { localStorage.setItem('manga_onglet','tChap'); localStorage.removeItem('manga_serie'); }")
        pg.reload(); pg.wait_for_timeout(4500)
        pg.evaluate("() => { BIB.favoris = []; renderLib(); }"); pg.wait_for_timeout(300)
        ordre = lambda: pg.evaluate("() => [...document.querySelectorAll('#chapList .serie-item')].map(x => x.dataset.serie)")
        o0 = ordre()
        check("A. une ☆ sur chaque carte", pg.evaluate("() => document.querySelectorAll('#chapList .serie-item .fav-c').length") == len(o0) > 2, len(o0))
        cible = o0[2]
        pg.evaluate("s => document.querySelector('.serie-item[data-serie=\"' + s + '\"] .fav-c').click()", cible); pg.wait_for_timeout(1200)
        o1 = ordre()
        check("B. ☆ de la 3e série -> EN TÊTE, ★, page NON ouverte", o1[0] == cible and pg.evaluate("() => !LIB_SERIE")
              and pg.evaluate("s => document.querySelector('.serie-item[data-serie=\"' + s + '\"] .fav-c').textContent", cible) == "★", (o1[:3], etat["posts"][-1:]))
        check("C. le reste garde l'ordre du tri", [x for x in o1 if x != cible] == [x for x in o0 if x != cible])
        pg.evaluate("s => ouvrirSerie(s)", cible); pg.wait_for_timeout(1200)
        check("D. page de la série : ★ à côté du titre", pg.evaluate("() => $('libFav').textContent === '★' && $('libFav').classList.contains('on') && !!$('libFav').offsetParent"))
        pg.evaluate("() => $('libFav').click()"); pg.wait_for_timeout(1200)
        check("D. la toucher = retirée des favoris", pg.evaluate("() => $('libFav').textContent") == "☆" and etat["fav"] == [], etat["fav"])
        pg.evaluate("() => ouvrirSerie(null)"); pg.wait_for_timeout(800)
        check("D. ordre d'origine revenu", ordre() == o0)
        etat["ancien"] = True
        pg.evaluate("s => document.querySelector('.serie-item[data-serie=\"' + s + '\"] .fav-c').click()", cible); pg.wait_for_timeout(1200)
        check("E. serveur pas relancé : l'étoile revient en arrière, ordre intact", ordre() == o0 and pg.evaluate("() => (BIB.favoris || []).length") == 0)
        if w < 400: pg.screenshot(path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "samsung_out", "favoris_360.png"))
        check("0 débordement", not pg.evaluate("() => document.documentElement.scrollWidth > document.documentElement.clientWidth"))
        check("0 erreur JS", not errs, errs[:2])
        c.close()
    b.close()
print("\nVERDICT : %d/%d" % (len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
