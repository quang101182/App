# -*- coding: utf-8 -*-
"""Banc UI v2.7.2 : choix du NOM DU MANGA a la capture (etape 3) -- « Mes series » puis « Masquees » repliees.
Le banc calcule LUI-MEME, depuis /manga/sources et /manga/bibliotheque, ce que la liste doit montrer (combien, dans quel
ordre, quelles masquees) et le compare a l'app. PC 1280 px + telephone 360 px. Ne modifie RIEN dans la bibliotheque.
Usage : python test_cap_titres_ui.py [port]
"""
import json, os, sys, urllib.request
from datetime import datetime
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banc_outils as bo

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cap_titres_%d.png")
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""), flush=True)


def api(path):
    r = urllib.request.Request("http://127.0.0.1:%d%s" % (PORT, path), headers={"Authorization": "Bearer " + KEY})
    with urllib.request.urlopen(r, timeout=60) as x:
        return json.load(x)


def attendu():
    """Ordre attendu, calcule sans le code de l'app : ouverte recemment, puis capture la plus recente, puis A-Z."""
    bib = api("/manga/bibliotheque")
    ser = {}
    for c in api("/manga/sources")["items"]:
        s = ser.setdefault(c["slug"], {"slug": c["slug"], "title": c["title"], "date": 0})
        try:
            s["date"] = max(s["date"], datetime.fromisoformat((c.get("captured_at") or "").replace("Z", "+00:00")).timestamp())
        except ValueError:
            pass
    ouv, masq = bib.get("ouvertes") or {}, set(bib.get("masquees") or [])
    l = sorted(ser.values(), key=lambda s: (-(ouv.get(s["slug"]) or 0), -s["date"], s["title"].lower()))
    return [s["title"] for s in l if s["slug"] not in masq], [s["title"] for s in l if s["slug"] in masq]


VIS, CACH = attendu()
print("attendu : %d visibles, %d masquees ; 1re = %s" % (len(VIS), len(CACH), VIS[:1]))
items = "() => [...document.querySelectorAll('#capSugg .cap-sugg-i')].map(b => b.dataset.titre)"
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w, h in ((1280, 900), (360, 780)):
        print("=== %d px" % w)
        c = b.new_context(viewport={"width": w, "height": h}, is_mobile=w < 400, has_touch=w < 400)
        pg = c.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto("http://127.0.0.1:%d/manga#k=%s" % (PORT, KEY)); pg.wait_for_timeout(2500)
        pg.click('nav button[data-tab="tChap"]'); pg.wait_for_timeout(1800)
        check("version affichee = celle du fichier", pg.inner_text("#verBadge") == "v" + bo.version_app())
        pg.evaluate("() => { document.getElementById('capBox').open = true; }"); pg.wait_for_timeout(300)
        pg.fill("#capTitre", ""); pg.click("#capTitre"); pg.wait_for_timeout(300)
        check("la liste s'ouvre au toucher du champ", pg.is_visible("#capSugg"))
        vus = pg.evaluate(items)
        check("« Mes séries » = les visibles, dans l'ordre attendu", vus == VIS, (vus[:4], VIS[:4]))
        check("aucune masquée tant qu'on ne le demande pas", not set(vus) & set(CACH))
        check("titre « Mes séries (%d) »" % len(VIS), ("Mes séries (%d)" % len(VIS)).upper() in pg.inner_text("#capSugg").upper())
        if CACH:
            check("bouton « Afficher les masquées (%d) »" % len(CACH), ("Afficher les masquées (%d)" % len(CACH)) in pg.inner_text("#capSugg"))
            pg.click("#capSugg [data-masq='1']"); pg.wait_for_timeout(250)
            vus = pg.evaluate(items)
            check("après le bouton : visibles PUIS masquées", vus == VIS + CACH, len(vus))
            check("les masquées sont marquées", pg.locator("#capSugg .cap-sugg-i.masq").count() == len(CACH))
            check("la liste reste ouverte après le bouton", pg.is_visible("#capSugg"))
        r = pg.evaluate("() => { const e = document.getElementById('capSugg').getBoundingClientRect(); return [e.height, innerHeight, e.left, e.right, innerWidth]; }")
        check("hauteur bornée (≤ 340 px et ≤ 52 %% de l'écran) : %d px" % r[0], r[0] <= 341 and r[0] <= r[1] * 0.52 + 1)
        check("dans l'écran en largeur", r[2] >= 0 and r[3] <= r[4] + 1, r)
        check("assez large pour un titre (≥ 320 px ou l'écran − 16) : %d px" % (r[3] - r[2]), r[3] - r[2] >= min(320, r[4] - 16) - 1)
        t = pg.evaluate("() => document.getElementById('capSugg').getBoundingClientRect().top")
        check("la liste commence DANS l'écran (haut ≥ 0) : %d" % t, t >= 0)
        vu = pg.evaluate("() => { const r = document.getElementById('capTitre').getBoundingClientRect(); const e = document.elementFromPoint(r.left + 20, r.top + r.height / 2); return !!e && (e.id === 'capTitre' || !!e.closest('.cap-titre-box')); }")
        check("le champ reste visible (pas caché sous la barre d'onglets)", vu)
        l2 = pg.evaluate("() => [...document.querySelectorAll('#capSugg .cap-sugg-i')].filter(b => b.getBoundingClientRect().height > 44).length")
        check("aucun titre coupé sur 2 lignes", l2 == 0, l2)
        check("pas de défilement horizontal de la page", pg.evaluate("() => document.documentElement.scrollWidth <= innerWidth + 1"))
        pg.screenshot(path=OUT % w)
        # recherche : une masquee seule reponse -> montree d'office ; un nom inconnu -> nouvelle serie
        if CACH:
            mot = CACH[0].split()[0][:6]
            pg.fill("#capTitre", mot); pg.wait_for_timeout(300)
            vus = pg.evaluate(items)
            vis_mot = [t for t in VIS if mot.lower() in t.lower()]
            if not vis_mot:
                check("recherche « %s » : la masquée apparaît d'office" % mot, CACH[0] in vus, vus)
        pg.fill("#capTitre", VIS[0][:5]); pg.wait_for_timeout(300)
        vus = pg.evaluate(items)
        check("recherche « %s » : %s en tête" % (VIS[0][:5], VIS[0]), vus[:1] == [VIS[0]], vus)
        pg.fill("#capTitre", "zzqx nouvelle serie"); pg.wait_for_timeout(300)
        check("nom inconnu : « créera une nouvelle série »", "NOUVELLE SÉRIE" in pg.inner_text("#capSugg").upper())
        # choisir au clavier puis au doigt
        pg.fill("#capTitre", ""); pg.keyboard.press("Escape"); pg.wait_for_timeout(150)      # liste FERMEE : ↓ doit l'ouvrir ET choisir
        pg.keyboard.press("ArrowDown"); pg.keyboard.press("Enter"); pg.wait_for_timeout(200)
        check("clavier ↓ + Entrée choisit la 1re série", pg.input_value("#capTitre") == VIS[0] and not pg.is_visible("#capSugg"))
        pg.fill("#capTitre", ""); pg.click("#capTitre"); pg.wait_for_timeout(250)
        pg.click("#capSugg .cap-sugg-i >> nth=1"); pg.wait_for_timeout(200)
        check("toucher une série la choisit et ferme la liste", pg.input_value("#capTitre") == VIS[1] and not pg.is_visible("#capSugg"))
        pg.click("#capTitre"); pg.wait_for_timeout(200)
        pg.mouse.click(5, 5); pg.wait_for_timeout(250)
        check("toucher ailleurs ferme la liste", not pg.is_visible("#capSugg"))
        check("aucune erreur JS", not errs, errs[:2])
        c.close()
    b.close()
print("\n%d/%d" % (len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
