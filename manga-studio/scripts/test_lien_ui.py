# -*- coding: utf-8 -*-
"""Banc v2.0.0 : capturer A PARTIR D'UN LIEN (idee Quang 22/09 10h38) -- partage recu et lien colle.
1. Partage recu (/manga/?lien=...) : l'app va a la capture, ouvre le lien dans un NOUVEL onglet de la fenetre de capture,
   le choisit pour la capture, propose le titre connu de la bibliotheque (« One-Punch Man - Wikipedia » -> « One Punch-Man »),
   et NE lance PAS la capture. 2. Lien colle dans le champ + « Ouvrir sur le PC » : meme chose. 3. Le manifeste declare
   la cible de partage. Les onglets ouverts par le banc sont refermes ; ceux de Quang ne sont pas touches.
Usage : python test_lien_ui.py [port]
"""
import json, os, sys, urllib.request
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
OK, KO = [], []
LIEN = "https://en.wikipedia.org/wiki/One-Punch_Man"


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


def onglets():
    return [t for t in json.load(urllib.request.urlopen("http://127.0.0.1:9223/json/list", timeout=5)) if t["type"] == "page"]


man = json.load(urllib.request.urlopen("http://127.0.0.1:%d/manga/manifest.webmanifest" % PORT, timeout=5))
check("manifeste : cible de partage (lien, texte, titre)", (man.get("share_target") or {}).get("params", {}).get("url") == "lien", man.get("share_target"))
avant = {t["id"] for t in onglets()}
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    c = b.new_context(viewport={"width": 360, "height": 780}, is_mobile=True, has_touch=True)
    pg = c.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("http://127.0.0.1:%d/manga/#k=" % PORT + KEY); pg.wait_for_timeout(2000)
    # 1. partage recu
    pg.goto("http://127.0.0.1:%d/manga/?texte=%s" % (PORT, urllib.request.quote("Regarde ça " + LIEN)))
    pg.wait_for_function("() => /✅|⚠/.test(document.getElementById('capLienEtat').textContent)", timeout=40000)
    etat = pg.inner_text("#capLienEtat")
    check("partage : lien ouvert sur le PC et choisi", etat.startswith("✅"), etat[:90])
    check("l'adresse de l'app est nettoyée", pg.evaluate("location.search") == "")
    nouveaux = [t for t in onglets() if t["id"] not in avant]
    check("un nouvel onglet sur la bonne page", len(nouveaux) == 1 and nouveaux[0]["url"].startswith(LIEN), [t["url"] for t in nouveaux])
    choisi = pg.evaluate("() => (CAP_TABS[+document.getElementById('capTab').value] || {}).url || ''")
    check("onglet sélectionné pour la capture", choisi.startswith(LIEN), choisi)
    check("titre reconnu dans la bibliothèque", pg.input_value("#capTitre") == "One Punch-Man", pg.input_value("#capTitre"))
    check("aucune capture lancée", "capture" not in (pg.inner_text("#capEtat") or "").lower() or "cours" not in pg.inner_text("#capEtat"), pg.inner_text("#capEtat"))
    # 2. lien colle
    pg.evaluate("() => { $('capTitre').value = ''; }"); pg.fill("#capLien", "en.wikipedia.org/wiki/Claymore_(manga)"); pg.click("#btnCapLien")
    pg.wait_for_function("() => /✅|⚠/.test(document.getElementById('capLienEtat').textContent) && !document.getElementById('capLienEtat').textContent.includes('One-Punch')", timeout=40000)
    check("lien collé (sans https) : ouvert et choisi", pg.inner_text("#capLienEtat").startswith("✅"), pg.inner_text("#capLienEtat")[:90])
    check("titre reconnu : Claymore", pg.input_value("#capTitre") == "Claymore", pg.input_value("#capTitre"))
    dep = pg.evaluate("() => document.documentElement.scrollWidth - innerWidth")
    check("360 px : aucun débordement", dep <= 0, dep)
    check("0 erreur JS", not errs, errs[:3])
    b.close()
for t in onglets():
    if t["id"] not in avant:
        urllib.request.urlopen("http://127.0.0.1:9223/json/close/" + t["id"], timeout=5).read()
check("onglets du banc refermés, ceux de Quang intacts", {t["id"] for t in onglets()} == avant)
print("\n%d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
