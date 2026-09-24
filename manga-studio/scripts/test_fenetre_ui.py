# -*- coding: utf-8 -*-
"""Banc v2.14.0 (Quang 24/09 16h10-16h22) : la FENETRE DE CAPTURE pilotee depuis l'app, sur la vraie fenetre Edge dediee.

Etat de depart SAUVE (position/taille de la fenetre, fichier %LOCALAPPDATA%/manga-fetch/fenetre.json) puis RESTAURE.
Aucune capture lancee, 0 $. Verifie : la rangee « Fenetre » apparait quand la fenetre est ouverte ; fenetre retrecie a
516 x 274 -> le controle d'avant capture le DIT (question a l'ecran, trop petite, minimum) ; « Taille sure puis capturer »
l'agrandit a >= 700 x 950 interieur SANS la deplacer ; « Ranger » la remet a la place ; « Retenir » ecrit la place ; 360 px
sans debordement ; 0 erreur JS. Capture : scripts/fenetre_360.png.
"""
import json, os, sys, urllib.request
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import cdp_mini as cm
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
URL = "http://127.0.0.1:8190/manga/#k=" + KEY
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""), flush=True)


def fenetre_id():
    l = json.load(urllib.request.urlopen(cm.CDP_NAV + "/json/list"))
    t = [x for x in l if x["type"] == "page"][0]
    with cm._navigateur() as n:
        return n.cmd("Browser.getWindowForTarget", targetId=t["id"])["windowId"]


def bornes(wid, b=None):
    with cm._navigateur() as n:
        if b:
            n.cmd("Browser.setWindowBounds", windowId=wid, bounds=b)
        return n.cmd("Browser.getWindowBounds", windowId=wid)["bounds"]


wid = fenetre_id()
avant = {k: v for k, v in bornes(wid).items() if k != "windowState"}
conf0 = open(cm.FENETRE_CONF, "rb").read() if os.path.isfile(cm.FENETRE_CONF) else None
place = cm.fenetre_conf()["place"]
try:
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        pg = b.new_page(viewport={"width": 1280, "height": 900}); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("dialog", lambda d: d.accept())                  # le confirm natif de capture n'est pas appele ici
        pg.goto(URL); pg.wait_for_timeout(3000)
        check("version affichée = celle du fichier", pg.inner_text("#verBadge") == "v" + __import__("banc_outils").version_app())
        pg.click('nav button[data-tab="tChap"]'); pg.wait_for_timeout(800)
        pg.evaluate("() => { const d = $('capFen').closest('details'); if (d && !d.open) d.querySelector('summary').click(); }")
        pg.evaluate("() => refreshCapTabs()"); pg.wait_for_timeout(1500)
        check("rangée « Fenêtre » visible (fenêtre de capture ouverte)", pg.evaluate("() => !$('capFen').hidden"))
        bornes(wid, {"left": 1500, "top": 300, "width": 516, "height": 274})
        pg.evaluate("() => { window._fv = null; fenVerifier().then(v => window._fv = v); }"); pg.wait_for_timeout(2500)
        vis = pg.is_visible("#ask"); txt = pg.inner_text("#askX") if vis else ""
        check("fenêtre rétrécie -> question « trop petite » avec le minimum", vis and "trop petite" in pg.inner_text("#askT")
              and "700 × 950" in txt and "492 × 148" in txt, txt[:160])
        pg.set_viewport_size({"width": 360, "height": 800}); pg.wait_for_timeout(400)
        pg.screenshot(path=os.path.join(HERE, "fenetre_question_360.png"))
        pg.click("#askYes"); pg.wait_for_timeout(3000)
        bb = bornes(wid)
        r = pg.evaluate("() => window._fv")
        check("« Taille sûre puis capturer » -> assez grande, capture autorisée", r is True, r)
        check("… sans la déplacer", bb["left"] == 1500 and bb["top"] == 300, bb)
        pg.set_viewport_size({"width": 1280, "height": 900}); pg.wait_for_timeout(300)
        pg.click("#capFenRanger"); pg.wait_for_timeout(2500)
        bb = bornes(wid)
        check("« Ranger sur le côté » -> exactement la place", all(bb[k] == place[k] for k in place), (bb, place))
        pg.evaluate("() => { window._fv = null; fenVerifier().then(v => window._fv = v); }"); pg.wait_for_timeout(2500)
        check("à sa place, le contrôle laisse passer sans question", pg.evaluate("() => window._fv") is True and pg.is_hidden("#ask"))
        bornes(wid, {"left": 2300, "top": 1300, "width": 1100, "height": 1400})
        pg.click("#capFenRetenir"); pg.wait_for_timeout(2500)
        c = json.load(open(cm.FENETRE_CONF, encoding="utf-8"))
        check("« Retenir cette place » l'écrit dans fenetre.json", c["place"] == {"left": 2300, "top": 1300, "width": 1100, "height": 1400}, c)
        pg.set_viewport_size({"width": 360, "height": 800}); pg.wait_for_timeout(400)
        pg.evaluate("() => $('capFen').scrollIntoView({block:'center'})"); pg.wait_for_timeout(300)
        check("360 px : pas de débordement", pg.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth"))
        pg.screenshot(path=os.path.join(HERE, "fenetre_360.png"))
        check("aucune erreur JS", not errs, errs[:2])
        b.close()
finally:
    if conf0 is None:
        try: os.remove(cm.FENETRE_CONF)
        except OSError: pass
    else:
        open(cm.FENETRE_CONF, "wb").write(conf0)
    fin = bornes(wid, avant)
    print("restauré : fenêtre", fin, "· fenetre.json", "absent (défaut)" if conf0 is None else "remis")
print("\n%d/%d" % (len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
