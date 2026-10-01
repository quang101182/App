# -*- coding: utf-8 -*-
"""Banc v3.6.2 : bandeau « nouvelle version ». App REELLE 8190 (page substituee si --page), POST interceptes.
La NAVIGATION recoit la page ; le fetch de verification (/manga/, type fetch) recoit selon le cas :
A. la MEME version -> aucun bandeau ; B. une version DIFFERENTE -> bandeau visible, dans l'ecran, texte = la version,
   aucun rechargement d'office ; C. toucher le bandeau -> la page se recharge ; D. serveur injoignable -> rien, 0 erreur ;
E. une 2e verification dans la minute n'interroge PAS le serveur. 360 puis 1280 px. 0 erreur JS.
Usage : python test_version_dispo_ui.py [--page f.html]"""
import os, re, sys
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
    for w, h in ((360, 780), (1280, 900)):
        print("=== %d px" % w)
        c = b.new_context(viewport={"width": w, "height": h}, is_mobile=w < 400, has_touch=w < 400, service_workers="block")
        pg = c.new_page(); errs = []; etat = {"mode": "meme", "verifs": 0, "navs": 0}
        pg.on("pageerror", lambda e: errs.append(str(e)))
        def route(rt):
            r = rt.request; u = r.url.split("#")[0].split("?")[0].rstrip("/")
            if r.method == "POST" and not any(k in r.url for k in ("sources", "resume", "fetch_status", "langue", "serie_infos", "videos")):
                return rt.fulfill(status=200, body='{"ok":true}', content_type="application/json")
            if r.method == "GET" and u.endswith("/manga"):
                if r.resource_type == "document":
                    etat["navs"] += 1
                    if PAGE: return rt.fulfill(status=200, body=PAGE, content_type="text/html; charset=utf-8")
                    return rt.continue_()
                etat["verifs"] += 1
                if etat["mode"] == "panne": return rt.abort()
                v = etat["ver"] if etat["mode"] == "meme" else "9.9.9"
                return rt.fulfill(status=200, body="<!DOCTYPE html>\n<html><head><title>Manga Studio v%s</title>" % v + "x" * 5000,
                                  content_type="text/html; charset=utf-8")
            rt.continue_()
        pg.route("**/*", route)
        pg.goto("http://127.0.0.1:8190/manga#k=" + KEY); pg.wait_for_timeout(3000)
        etat["ver"] = pg.evaluate("() => VERSION"); print("  version :", etat["ver"])
        if not pg.evaluate("() => typeof majVerifier === 'function'"):
            check("présence de la vérification de version", False, "absente (version d'avant 3.6.2)"); c.close(); continue
        verifier = lambda: (pg.evaluate("() => { MAJ.t = 0; return majVerifier(); }"), pg.wait_for_timeout(600))
        bandeau = lambda: pg.evaluate("() => { const e = document.getElementById('majDispo'); if (!e) return null; const r = e.getBoundingClientRect(); return { t: e.textContent, g: r.left, d: r.right, h: r.top, b: r.bottom, vis: document.elementFromPoint((r.left + r.right) / 2, (r.top + r.bottom) / 2) === e }; }")   # au-dessus de tout, touchable
        verifier()
        check("A. même version -> aucun bandeau", bandeau() is None and etat["verifs"] >= 1, etat)
        etat["mode"] = "panne"; verifier()
        check("D. serveur injoignable -> aucun bandeau", bandeau() is None)
        etat["mode"] = "neuve"; n0 = etat["navs"]
        pg.evaluate("() => { MAJ.t = 0; document.dispatchEvent(new Event('visibilitychange')); }"); pg.wait_for_timeout(800)
        bd = bandeau()
        check("B. version différente -> bandeau (au retour sur l'app)", bd and "v9.9.9" in bd["t"] and bd["vis"], bd)
        check("B. bandeau entièrement dans l'écran", bd and bd["g"] >= 0 and bd["d"] <= w and bd["h"] >= 0, bd)
        check("B. aucun rechargement d'office", etat["navs"] == n0)
        v0 = etat["verifs"]; pg.evaluate("() => majVerifier()"); pg.wait_for_timeout(500)
        check("E. 2e vérification dans la minute : pas de requête", etat["verifs"] == v0, (v0, etat["verifs"]))
        check("0 débordement", not pg.evaluate("() => document.documentElement.scrollWidth > document.documentElement.clientWidth"))
        etat["mode"] = "meme"
        with pg.expect_navigation(timeout=15000):
            pg.evaluate("() => document.getElementById('majDispo').click()")
        pg.wait_for_timeout(1500)
        check("C. toucher -> la page se recharge", etat["navs"] == n0 + 1 and bandeau() is None, etat["navs"] - n0)
        check("0 erreur JS", not errs, errs[:2])
        c.close()
    b.close()
print("\nVERDICT : %d/%d" % (len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
