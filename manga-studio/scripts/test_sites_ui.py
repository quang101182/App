# -*- coding: utf-8 -*-
"""Banc v2.3.3 (etape 19) : SITES VALIDES dans « Capturer un chapitre » + bouton du pilotage renomme.

GET /manga/sites = manga-fetch/sites.json (versionne). App (1280 et 360 px) : « 🌐 Sites validés (N) » replie dans
l'etape 1 ; deplie -> une ligne par site du fichier (nom = lien qui s'ouvre dans un NOUVEL onglet, etats capture /
plusieurs chapitres, note + date du controle) ; un toucher sur le lien ouvre bien le site ; rien ne deborde ;
le bouton du pilotage dit « ✔ Choisir cet onglet » (il ne capture pas). Aucune capture lancee.
Usage : python test_sites_ui.py [port]
"""
import json, os, sys, urllib.request
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
FICHIER = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "manga-fetch", "sites.json"))
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""), flush=True)


req = urllib.request.Request("http://127.0.0.1:%d/manga/sites" % PORT, headers={"Authorization": "Bearer " + KEY})
with urllib.request.urlopen(req, timeout=20) as r:
    api = json.load(r)
attendu = json.load(open(FICHIER, encoding="utf-8"))
check("route /manga/sites = le fichier versionné", api == attendu, [x["nom"] for x in api.get("sites", [])])

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w, h in ((1280, 1000), (360, 780)):
        print("=== %d px" % w)
        ctx = b.new_context(viewport={"width": w, "height": h}); pg = ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto("http://127.0.0.1:%d/manga/#k=" % PORT + KEY); pg.wait_for_timeout(2500)
        pg.click('nav button[data-tab="tChap"]'); pg.wait_for_timeout(1200)
        pg.evaluate("() => { document.getElementById('capBox').open = true; }"); pg.wait_for_timeout(500)
        check("repliée au départ", pg.evaluate("() => !document.getElementById('capSites').open"))
        pg.click("#capSites summary"); pg.wait_for_timeout(1500)
        lignes = pg.evaluate("""() => Array.from(document.querySelectorAll('#capSitesListe .cap-site')).map(d => {
            const a = d.querySelector('a'); return {nom: a.textContent, href: a.href, cible: a.target,
              etats: d.querySelector('.etats').textContent, note: d.querySelector('.note').textContent}; })""")
        check("une ligne par site du fichier", [x["nom"] for x in lignes] == [x["nom"] for x in attendu["sites"]], lignes)
        check("liens = adresses du fichier, nouvel onglet",
              all(l["href"] == s["url"] and l["cible"] == "_blank" for l, s in zip(lignes, attendu["sites"])))
        check("MangaDex : capture ✅ · plusieurs chapitres ✅",
              any(l["nom"] == "MangaDex" and "capture ✅" in l["etats"] and "plusieurs chapitres ✅" in l["etats"] for l in lignes))
        check("MANGA Plus : plusieurs chapitres 🟠 + la raison",
              any(l["nom"] == "MANGA Plus" and "🟠" in l["etats"] and "#004" in l["note"] for l in lignes))
        check("compteur « (2) »", pg.evaluate("() => document.getElementById('capSitesN').textContent") == "(%d)" % len(attendu["sites"]))
        with ctx.expect_page(timeout=15000) as nouvelle:
            pg.click("#capSitesListe .cap-site a >> nth=0")
        np_ = nouvelle.value
        try:
            np_.wait_for_url(lambda u: u.startswith("http"), timeout=20000)   # l'onglet nait vide, puis charge
        except Exception:
            pass
        check("un toucher ouvre le site", np_.url.startswith(attendu["sites"][0]["url"].rstrip("/")), np_.url)
        np_.close()
        m = pg.evaluate("""() => ({page: document.documentElement.scrollWidth - document.documentElement.clientWidth,
            dehors: Array.from(document.querySelectorAll('#capSites *')).filter(e => e.getBoundingClientRect().right > innerWidth + 1).length})""")
        check("rien ne déborde", m["page"] <= 0 and m["dehors"] == 0, m)
        check("bouton du pilotage : « ✔ Choisir cet onglet »",
              pg.evaluate("() => document.getElementById('pilChoisir').textContent.trim()") == "✔ Choisir cet onglet")
        check("aucune erreur JS", not errs, errs)
        ctx.close()
    b.close()
print("\nVERDICT : %d/%d" % (len(OK), len(OK) + len(KO)) + ("" if not KO else "  -- KO : " + " ; ".join(KO)))
sys.exit(0 if not KO else 1)
