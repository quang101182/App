# -*- coding: utf-8 -*-
"""Banc v2.51.0 : le FLOU de la secondaire hors de la fenetre devient OPTIONNEL (Quang 25/09 11h19), persistant (serveur).
APP REELLE (8192 secondaire, 8190 principale), 1280 px puis 360 px, pages SANS fenetre (aucune fenetre de Quang touchee).
1. principale : pas d'interrupteur (elle n'a pas de flou) ; 2. secondaire : interrupteur dans ⋯, ACTIF par defaut ;
3. actif : perte du focus -> floue, retour -> nette ; 4. coupe (clic reel) : le serveur l'enregistre, perte du focus -> NETTE ;
5. rechargement : toujours coupe (persistance) ; 6. rallume -> floue a nouveau ; 7. 360 px : interrupteur visible, pas de
debordement. La valeur du serveur est RELEVEE au depart et RESTAUREE a la fin, quoi qu'il arrive.
Usage : python test_flou_option_ui.py
"""
import json, os, sys, urllib.request
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
N, S = "http://127.0.0.1:8190", "http://127.0.0.1:8192"
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


def api(base, chemin, corps=None):
    rq = urllib.request.Request(base + chemin, data=json.dumps(corps).encode() if corps is not None else None,
                                headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(rq, timeout=15) as r:
        return json.load(r)


AVANT = api(S, "/manga/reglages").get("flou_discretion")
print("valeur de depart (secondaire) :", AVANT)
flou = lambda pg: pg.evaluate("() => document.body.classList.contains('esp-flou')")
perdre = lambda pg: pg.evaluate("() => { window.dispatchEvent(new Event('blur')); }")
revenir = lambda pg: pg.evaluate("() => { window.dispatchEvent(new Event('focus')); }")


def ouvrir_menu(pg):
    pg.evaluate("() => { const m = document.querySelector('#hdrFlou').closest('.menu-plus'); if (m.querySelector('.menu-pan').hidden) m.querySelector('.plus').click(); }")
    pg.wait_for_timeout(250)


try:
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        for w, h in ((1280, 900), (360, 780)):
            print("=== %d px" % w)
            c = b.new_context(viewport={"width": w, "height": h}, is_mobile=w < 400, has_touch=w < 400)
            errs = []
            pn = c.new_page(); pn.on("pageerror", lambda e: errs.append(str(e)))
            pn.goto(N + "/manga#k=" + KEY); pn.wait_for_timeout(3000)
            check("principale : pas d'interrupteur de flou", pn.evaluate("() => $('hdrFlouL').hidden"))
            pn.close()
            api(S, "/manga/reglages", {"flou_discretion": True})
            ps = c.new_page(); ps.on("pageerror", lambda e: errs.append(str(e)))
            ps.goto(S + "/manga#k=" + KEY); ps.wait_for_timeout(3500)
            check("version = VERSION du code", ps.inner_text("#verBadge").strip() == "v" + ps.evaluate("() => VERSION"))
            ouvrir_menu(ps)
            check("secondaire : interrupteur dans ⋯, visible", ps.eval_on_selector("#hdrFlouL", "e => !e.hidden && e.getBoundingClientRect().width > 0"))
            check("ACTIF par défaut", ps.is_checked("#hdrFlou"))
            ps.keyboard.press("Escape"); ps.wait_for_timeout(700)
            perdre(ps); ps.wait_for_timeout(150)
            check("actif : perte du focus → floue", flou(ps))
            revenir(ps); ps.wait_for_timeout(150)
            check("actif : retour → nette", not flou(ps))
            ouvrir_menu(ps)
            ps.click("#hdrFlou"); ps.wait_for_timeout(1200)
            check("coupé : le serveur l'enregistre", api(S, "/manga/reglages").get("flou_discretion") is False)
            ps.keyboard.press("Escape"); ps.wait_for_timeout(700)
            perdre(ps); ps.wait_for_timeout(150)
            check("coupé : perte du focus → reste NETTE", not flou(ps))
            revenir(ps)
            ps.reload(); ps.wait_for_timeout(3500)
            check("rechargement : toujours coupé (persistant)", not ps.is_checked("#hdrFlou"))
            perdre(ps); ps.wait_for_timeout(150)
            check("rechargement : perte du focus → reste nette", not flou(ps))
            revenir(ps)
            ouvrir_menu(ps)
            if w < 400:
                check("360 px : interrupteur entièrement dans l'écran", ps.eval_on_selector("#hdrFlou", "e => { const r = e.getBoundingClientRect(); return r.right <= innerWidth && r.width >= 30; }"))
                check("360 px : aucun débordement", ps.evaluate("() => document.documentElement.scrollWidth <= innerWidth"))
            ps.click("#hdrFlou"); ps.wait_for_timeout(1200)
            ps.keyboard.press("Escape"); ps.wait_for_timeout(700)
            check("rallumé : le serveur l'enregistre", api(S, "/manga/reglages").get("flou_discretion") is True)
            perdre(ps); ps.wait_for_timeout(150)
            check("rallumé : perte du focus → floue", flou(ps))
            check("aucune erreur JS", not errs, errs[:3])
            c.close()
        b.close()
finally:
    api(S, "/manga/reglages", {"flou_discretion": AVANT if isinstance(AVANT, bool) else True})
    print("valeur restauree :", api(S, "/manga/reglages").get("flou_discretion"))

print("\nVERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
