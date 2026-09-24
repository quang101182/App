# -*- coding: utf-8 -*-
"""Banc S2 (compartiment secret, 24/09/2026) : l'app sait dans quel espace elle est, appui long sur 📚, rien ne trahit.

App reelle (8190 normal, 8192 prive), Edge sans fenetre. Verifie :
- /manga/espace : « normal » sur 8190, « prive » sur 8192 ; les deux refusent sans cle (401) ;
- titre, icone et manifeste IDENTIQUES dans les deux espaces ; la marque (badge pointille + point) n'existe QUE dans
  l'espace prive ;
- clic simple sur 📚 = l'onglet Bibliotheque, rien d'autre ; appui de 0,8 s = rien ; appui de 1,4 s = l'autre espace,
  la cle suit (bibliotheque chargee, aucun 401) et disparait de l'URL ; retour par le meme geste ;
- 360 px : aucun debordement horizontal, dans les deux espaces ; aucune erreur JavaScript.
Captures : scripts/espace_normal_360.png, espace_prive_360.png. N'ecrit rien cote serveur.
"""
import json, os, sys, urllib.error, urllib.request
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
N, P = "http://127.0.0.1:8190", "http://127.0.0.1:8192"
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail and not cond else ""), flush=True)


def espace(base, cle=True):
    r = urllib.request.Request(base + "/manga/espace", headers={"Authorization": "Bearer " + KEY} if cle else {})
    try:
        return json.load(urllib.request.urlopen(r, timeout=10))
    except urllib.error.HTTPError as e:
        return e.code


def etat(pg):
    return pg.evaluate("""() => ({
      url: location.href, titre: document.title, prive: document.body.classList.contains("esp-p"),
      bord: getComputedStyle(document.getElementById("verBadge")).borderTopStyle,
      point: getComputedStyle(document.getElementById("verBadge"), "::after").content,
      icone: [...document.querySelectorAll('link[rel="icon"],link[rel="manifest"],link[rel="apple-touch-icon"]')].map(l => l.getAttribute("href")).join("|"),
      onglet: (document.querySelector("nav button.sel") || {}).dataset?.tab,
      cle: !!localStorage.getItem("manga_key"),
      deborde: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
      nom: typeof ESPACE === "object" ? ESPACE.nom : null })""")


def appui(pg, ms):
    b = pg.locator('nav button[data-tab="tChap"]'); bb = b.bounding_box()
    pg.mouse.move(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2)
    pg.mouse.down(); pg.wait_for_timeout(ms); pg.mouse.up()


print("1. serveur")
check("8190 annonce « normal »", (espace(N) or {}).get("espace") == "normal", espace(N))
check("8192 annonce « prive »", (espace(P) or {}).get("espace") == "prive", espace(P))
check("les deux refusent sans cle (401)", espace(N, False) == 401 and espace(P, False) == 401, (espace(N, False), espace(P, False)))

with sync_playwright() as pw:
    nav = pw.chromium.launch(channel="msedge", headless=True)
    for largeur in (1280, 360):
        print("2. interface a %d px" % largeur)
        ctx = nav.new_context(viewport={"width": largeur, "height": 800})
        pg = ctx.new_page(); errs = []; refus = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("response", lambda r: refus.append(r.url) if r.status == 401 else None)
        pg.goto(N + "/manga/#k=" + KEY); pg.wait_for_timeout(2500)
        n = etat(pg)
        check("normal : pas de marque (badge plein, sans point)", not n["prive"] and n["bord"] == "solid" and n["point"] in ("none", "normal"), n)
        check("normal : ESPACE.nom = normal", n["nom"] == "normal", n["nom"])
        if largeur == 360:
            check("normal 360 px : aucun debordement", not n["deborde"]); pg.screenshot(path=os.path.join(HERE, "espace_normal_360.png"))
        pg.locator('nav button[data-tab="tPlate"]').click(); pg.wait_for_timeout(300)
        pg.locator('nav button[data-tab="tChap"]').click(); pg.wait_for_timeout(800)
        c = etat(pg)
        check("clic simple sur 📚 : onglet Bibliotheque, meme adresse", c["onglet"] == "tChap" and c["url"].startswith(N), c)
        appui(pg, 800); pg.wait_for_timeout(1200)
        check("appui de 0,8 s : rien ne change", etat(pg)["url"].startswith(N))
        appui(pg, 1400); pg.wait_for_url(P + "/manga/**", timeout=8000); pg.wait_for_timeout(3000)
        p = etat(pg)
        check("appui de 1,4 s : l'espace prive s'ouvre", p["url"].startswith(P) and p["nom"] == "prive", p["url"])
        check("la cle a suivi et a quitte l'adresse", p["cle"] and "#k=" not in p["url"], p["url"])
        check("titre identique", p["titre"] == n["titre"], (p["titre"], n["titre"]))
        check("icone + manifeste identiques", p["icone"] == n["icone"] and n["icone"], (p["icone"], n["icone"]))
        check("prive : la marque discrete est la (pointille + point)", p["prive"] and p["bord"] == "dashed" and "·" in p["point"], p)
        check("prive : bibliotheque chargee sans refus (aucun 401)", not [u for u in refus if u.startswith(P)], refus[:3])
        if largeur == 360:
            check("prive 360 px : aucun debordement", not p["deborde"]); pg.screenshot(path=os.path.join(HERE, "espace_prive_360.png"))
        pg.locator('nav button[data-tab="tPlate"]').click(); pg.wait_for_timeout(300)
        appui(pg, 1400); pg.wait_for_url(N + "/manga/**", timeout=8000); pg.wait_for_timeout(2500)
        r = etat(pg)
        check("retour par le meme geste : espace normal, sans marque", r["url"].startswith(N) and not r["prive"] and r["nom"] == "normal", r)
        check("aucune erreur JavaScript", not errs, errs[:3])
        ctx.close()
    nav.close()
print("\n%d/%d" % (len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
