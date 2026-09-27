# -*- coding: utf-8 -*-
"""Banc v2.93.0 : « si je suis dans la secondaire, je reste dedans tant que je ne suis pas revenu par 📚 ». Principale 8190 et
secondaire 8192 REELLES, un seul navigateur (chaque adresse garde SON stockage, comme sur le telephone). « Rouvrir l'icone de la
principale » = ouvrir une page neuve sur la principale. La fenetre dediee du PC est court-circuitee (chemin du telephone).
Usage : python test_rester_secondaire_ui.py [html]        (html v2.92.0 -> ROUGE)"""
import os, sys
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(HERE, "..", "manga_studio.html")
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PAGE = open(HTML, encoding="utf-8").read()
OK, KO = [], []
P, S = "http://127.0.0.1:8190/manga/", "http://127.0.0.1:8192/manga/"
STUB = "() => { window.espaceFenetre = async () => { throw new Error('banc : chemin du telephone'); }; }"


def check(n, c, d=""):
    (OK if c else KO).append(n); print(("  [OK] " if c else "  [KO] ") + n + (" -- " + str(d)[:160] if d else ""), flush=True)


def attendre(pg, nom):
    pg.wait_for_function("n => typeof ESPACE !== 'undefined' && ESPACE.nom === n", arg=nom, timeout=30000); pg.wait_for_timeout(1000)


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    ctx = b.new_context(viewport={"width": 390, "height": 800}, is_mobile=True, has_touch=True)
    ctx.route("**/*", lambda rt: rt.fulfill(status=200, content_type="text/html; charset=utf-8", body=PAGE)
              if rt.request.method == "GET" and rt.request.url.split("#")[0].split("?")[0].rstrip("/").endswith("/manga") else rt.continue_())
    errs = []
    pg = ctx.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(P + "#k=" + KEY); attendre(pg, "normal"); pg.evaluate(STUB)
    pg.evaluate("() => espaceBasculer()"); pg.wait_for_url(S + "**", timeout=20000); attendre(pg, "prive")
    check("appui long (chemin du téléphone) : on est dans la secondaire", True)
    pg2 = ctx.new_page(); pg2.on("pageerror", lambda e: errs.append(str(e)))
    pg2.goto(P); pg2.wait_for_url(S + "**", timeout=20000); attendre(pg2, "prive")
    check("icône de la PRINCIPALE rouverte : renvoyé aussitôt dans la secondaire", pg2.url.startswith(S), pg2.url)
    pg2.close()
    pg.evaluate(STUB)
    pg.evaluate("() => document.querySelector('nav button[data-tab=\"tChap\"]').click()"); pg.wait_for_timeout(300)   # se placer sur 📚
    pg.click('nav button[data-tab="tChap"]'); pg.wait_for_url(P + "**", timeout=20000); attendre(pg, "normal")
    check("📚 dans la secondaire : retour à la principale", pg.url.startswith(P))
    check("… l'adresse est nettoyée (plus de « retour=1 »)", "retour=1" not in pg.url, pg.url)
    check("… et la principale a OUBLIÉ la secondaire", pg.evaluate("() => localStorage.getItem('manga_reste_secondaire')") is None)
    pg3 = ctx.new_page(); pg3.goto(P); pg3.wait_for_timeout(4000)
    check("icône de la principale rouverte ensuite : on RESTE dans la principale", pg3.url.startswith(P), pg3.url)
    # filet : secondaire injoignable -> pas de boucle
    pg3.evaluate("() => { localStorage.setItem('manga_reste_secondaire', 'http://127.0.0.1:8199/manga/'); localStorage.removeItem('manga_reste_secondaire:t'); }")
    pg4 = ctx.new_page()
    try:
        pg4.goto(P, timeout=15000)
    except Exception:
        pass
    pg4.wait_for_timeout(2000)
    pg5 = ctx.new_page(); pg5.goto(P); attendre(pg5, "normal"); pg5.wait_for_timeout(1500)
    check("secondaire injoignable : la principale ne boucle pas, elle reste ouverte", pg5.url.startswith(P), pg5.url)
    check("… et le dit", "injoignable" in pg5.evaluate("() => document.body.innerText"), "")
    pg5.evaluate("() => { localStorage.removeItem('manga_reste_secondaire'); localStorage.removeItem('manga_reste_secondaire:t'); }")
    # appui long annule : journalise
    pg5.evaluate("() => document.querySelector('nav button[data-tab=\"tChap\"]').click()"); pg5.wait_for_timeout(300)
    bx = pg5.locator('nav button[data-tab="tChap"]').bounding_box()
    pg5.mouse.move(bx["x"] + 5, bx["y"] + 5); pg5.mouse.down(); pg5.wait_for_timeout(600)
    pg5.mouse.move(bx["x"] - 80, bx["y"] - 80); pg5.wait_for_timeout(300); pg5.mouse.up(); pg5.wait_for_timeout(300)
    check("appui long interrompu : journalisé avec sa cause", "appui long annulé" in pg5.evaluate("() => document.body.innerText + [...document.querySelectorAll('#log div')].map(x => x.textContent).join(' ')"))
    check("le bouton 📚 garde le geste (touch-action:none)", pg5.evaluate("() => document.querySelector('nav button[data-tab=\"tChap\"]').style.touchAction") == "none")
    check("0 erreur JS", not errs, errs)
print("VERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
