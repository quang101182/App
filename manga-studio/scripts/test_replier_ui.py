# -*- coding: utf-8 -*-
"""Banc v2.58.0 : REPLIER vite ce qui s'est deplie (Quang 25/09 13h16, capture : « Profil et traitement » reste ouvert sur la
bibliotheque, et plus de retour). APP REELLE (8190), 1280 px puis 360 px. Tout POST bloque (rien ne part). Etat de
« Capturer un chapitre » (memorise sur l'appareil) restaure a la fin.
1. le cas de la capture : Profil ouvert puis « ← Toutes les séries » -> le panneau se referme ;
2. ← de la barre devient « ← Fermer » et replie : Profil, Vidéos, Capturer un chapitre ; puis reprend son role ;
3. Echap (PC) replie le panneau ; Echap avec un menu ⋯ ouvert ferme le MENU, pas le panneau.
Usage : python test_replier_ui.py [port]
"""
import os, sys
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = sys.argv[1] if len(sys.argv) > 1 else "8190"
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w, h in ((1280, 900), (360, 780)):
        tel = w < 400
        print("=== %d px" % w)
        c = b.new_context(viewport={"width": w, "height": h}, is_mobile=tel, has_touch=tel)
        pg = c.new_page(); errs, posts = [], []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        def route(rt):
            r = rt.request
            if r.method == "POST" and not any(k in r.url for k in ("activite", "costs", "savelog")):
                posts.append(r.url.split("?")[0]); return rt.abort()
            rt.continue_()
        pg.route("**/*", route)
        pg.goto("http://127.0.0.1:%s/manga#k=%s" % (PORT, KEY)); pg.wait_for_timeout(2500)
        cap_avant = pg.evaluate("() => localStorage.getItem('manga_capture_ouvert')")
        pg.evaluate("() => { localStorage.setItem('manga_onglet','tChap'); localStorage.setItem('manga_serie','one-punch-man'); localStorage.setItem('manga_capture_ouvert','0'); }")
        pg.reload(); pg.wait_for_timeout(4500)
        ret = lambda: pg.evaluate("() => [$('nfRet').textContent, $('nfRet').disabled]")
        vis = lambda i: pg.evaluate("i => !$(i).hidden", i)
        # 1. le cas de la capture d'ecran
        pg.evaluate("() => $('btnSuivi').click()"); pg.wait_for_timeout(1500)
        check("Profil ouvert", vis("suiviBox"))
        check("← de la barre devient « ← Fermer »", ret() == ["← Fermer", False], ret())
        pg.evaluate("() => $('btnLibBack').click()"); pg.wait_for_timeout(1200)
        check("« ← Toutes les séries » : le Profil se REFERME (plus de panneau orphelin)", not vis("suiviBox"))
        check("… bibliothèque : ← grisé (rien à fermer)", ret()[1] is True, ret())
        # 2. ← replie chaque panneau, puis reprend son role
        pg.evaluate("() => { localStorage.setItem('manga_serie','one-punch-man'); }"); pg.reload(); pg.wait_for_timeout(4500)
        for bouton, box, nom in (("btnSuivi", "suiviBox", "Profil"), ("btnVideos", "vidBox", "Vidéos")):
            pg.evaluate("i => $(i).click()", bouton); pg.wait_for_timeout(1500)
            ok_ouvert = vis(box)
            pg.click("#nfRet"); pg.wait_for_timeout(600)
            check("%s : ouvert, puis « ← Fermer » le replie" % nom, ok_ouvert and not vis(box))
            check("%s : la série reste ouverte, ← redevient « ← Séries »" % nom, pg.evaluate("() => LIB_SERIE") == "one-punch-man" and ret() == ["← Séries", False], ret())
        pg.evaluate("() => { $('btnLibBack').click(); $('capBox').open = true; }"); pg.wait_for_timeout(800)
        check("Capturer un chapitre ouvert : ← = « ← Fermer »", ret() == ["← Fermer", False], ret())
        pg.click("#nfRet"); pg.wait_for_timeout(500)
        check("… « ← Fermer » le replie", not pg.evaluate("() => $('capBox').open"))
        # 3. Echap (PC)
        if not tel:
            pg.evaluate("() => { localStorage.setItem('manga_serie','one-punch-man'); }"); pg.reload(); pg.wait_for_timeout(4500)
            pg.evaluate("() => $('btnSuivi').click()"); pg.wait_for_timeout(1500)
            pg.evaluate("() => document.querySelector('.lib-actions .plus').click()"); pg.wait_for_timeout(200)
            menu = pg.evaluate("() => !!document.querySelector('.menu-pan:not([hidden])')")
            pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
            check("Échap avec un menu ⋯ ouvert : ferme le MENU, le panneau reste", menu and not pg.evaluate("() => !!document.querySelector('.menu-pan:not([hidden])')") and vis("suiviBox"))
            pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
            check("Échap (sans menu) : replie le panneau", not vis("suiviBox"))
        check("RIEN n'est parti (aucun POST)", not posts, posts[:4])
        check("aucune erreur JS", not errs, errs[:3])
        pg.evaluate("v => { localStorage.removeItem('manga_serie'); v === null ? localStorage.removeItem('manga_capture_ouvert') : localStorage.setItem('manga_capture_ouvert', v); }", cap_avant)
        c.close()
    b.close()

print("\nVERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
