# -*- coding: utf-8 -*-
"""Banc v2.12.0 (feuille de route 4-undecies, 24/09) : la DOUBLE ESTIMATION ☁ / 🖥 dans l'app reelle, comme Quang.

Cree sources/banc-estim-ui/ (2 chapitres de 3 pages copies d'OPM 298-299), retire a la fin ; l'interrupteur est remis
dans son etat de depart. AUCUN appel payant : les confirmations « Traduire » et « Lancer » sont lues puis REFUSEES.
Verifie : chapitre (narration + traduction) et lot du profil affichent les deux pastilles, chiffres = serveur
(estimation.py / plan du lot), le mode actif est plein ; un clic sur la pastille du haut les inverse SANS recharger ;
les confirmations portent les deux estimations, le mode actif en premier ; 360 px sans debordement ; 0 erreur JS.
Captures : scripts/estim_1280.png, estim_360.png, estim_lot_360.png.
"""
import json, os, re, shutil, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import estimation, reglages
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
SRC = os.path.normpath(os.path.join(HERE, "..", "sources"))
BANC = os.path.join(SRC, "banc-estim-ui")
URL = "http://127.0.0.1:8190/manga/#k=" + KEY
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""), flush=True)


def prepare():
    shutil.rmtree(BANC, ignore_errors=True)
    for i, src in ((1, "one-punch-man/ch_298"), (2, "one-punch-man/ch_299")):
        cs, cd = os.path.join(SRC, src), os.path.join(BANC, "ch_%d" % i)
        os.makedirs(cd)
        man = json.load(open(os.path.join(cs, "manifest.json"), encoding="utf-8"))
        man.update(pages=man["pages"][1:4], chapter=str(i), slug="banc-estim-ui", title="banc estim ui")
        for p in man["pages"]:
            shutil.copy(os.path.join(cs, p["file"]), os.path.join(cd, p["file"]))
        json.dump(man, open(os.path.join(cd, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


usd = lambda v: (("%.2f" % v) if v >= 0.1 or v == 0 else ("%.3f" % v)).replace(".", ",") + " $"


def puces(pg, sel):
    return pg.evaluate("""s => [...document.querySelectorAll(s + ' .est2 .e')].map(e => ({t: e.textContent, on: e.classList.contains('on'),
                          pc: e.classList.contains('pc')}))""", sel)


def ouvrir_chapitre(pg):
    pg.goto(URL); pg.wait_for_timeout(2500)
    pg.click('nav button[data-tab="tChap"]'); pg.wait_for_timeout(1000)
    pg.evaluate("() => refreshChaps()"); pg.wait_for_timeout(1500)
    pg.evaluate("() => ouvrirSerie('banc-estim-ui')"); pg.wait_for_timeout(1200)
    pg.evaluate("() => openChap(CHAPS.findIndex(c => c.dir === 'banc-estim-ui/ch_1'))"); pg.wait_for_timeout(2500)


mode0 = reglages.lire()["mode"]
prepare()
dial = []
try:
    reglages.ecrire(mode="cloud")
    et = estimation.etalonnage()
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        pg = b.new_page(viewport={"width": 1280, "height": 900}); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("dialog", lambda d: (dial.append(d.message), d.dismiss()))
        ouvrir_chapitre(pg)
        check("version affichée v2.12.0", pg.inner_text("#verBadge") == "v2.12.0")
        check("l'étalonnage est arrivé avec le réglage", pg.evaluate("() => !!(ETAL && ETAL.narration && ETAL.narration.gemini)"))
        eng = pg.evaluate("() => $('narrEngine').value")
        att = estimation.chapitre(3, {"narration"}, eng, et)
        n = puces(pg, "#narrEstim")
        check("Narrer : deux pastilles ☁ / 🖥", len(n) == 2 and n[0]["t"].startswith("☁") and n[1]["t"].startswith("🖥"), n)
        check("Narrer : chiffres = serveur (%s)" % eng, usd(att["cloud"]["usd"]) in n[0]["t"] and usd(att["pc"]["usd"]) in n[1]["t"],
              (att, [x["t"] for x in n]))
        check("en ligne actif : ☁ plein, 🖥 estompé", n[0]["on"] and not n[1]["on"])
        t = puces(pg, "#tradEstim")
        att_t = estimation.chapitre(3, {"traduction"}, "gemini", et)
        check("Traduire : deux pastilles, chiffres = serveur", len(t) == 2 and usd(att_t["cloud"]["usd"]) in t[0]["t"], [x["t"] for x in t])
        pg.screenshot(path=os.path.join(HERE, "estim_1280.png"), full_page=False)
        # bascule par la pastille du haut : tout suit, sans recharger
        pg.click("#hdrMode"); pg.wait_for_timeout(1500)
        n2, t2 = puces(pg, "#narrEstim"), puces(pg, "#tradEstim")
        check("clic pastille -> serveur en « pc »", reglages.lire()["mode"] == "pc")
        check("clic pastille -> 🖥 plein, ☁ estompé (narration ET traduction)", n2[1]["on"] and not n2[0]["on"] and t2[1]["on"] and not t2[0]["on"])
        check("🖥 annonce la carte graphique occupée", "carte" in n2[1]["t"] or att["pc"]["gpu_min"] < 0.5, n2[1]["t"])
        pg.click("#btnTraduire"); pg.wait_for_timeout(800)
        m = dial[-1] if dial else ""
        check("confirmation Traduire : 🖥 d'abord, ☁ ensuite", re.search(r"▶ 🖥 Sur mon PC.*\n\s+☁ En ligne", m) is not None, m[:200])
        check("Traduire refusé : rien lancé", not os.path.isdir(os.path.join(BANC, "ch_1", "traduction")))
        # le lot du profil
        pg.click("#btnSuivi"); pg.wait_for_timeout(3000)
        l = puces(pg, "#lotEstim")
        plan = pg.evaluate("() => SUIVI.plan")
        vis = [x for x in plan if x["a_faire"]]
        som = {"cloud": sum(x["estim"]["cloud"]["usd"] for x in vis), "pc": sum(x["estim"]["pc"]["usd"] for x in vis)}
        check("le plan du serveur porte les deux estimations", all("estim" in x for x in plan))
        check("lot : deux pastilles, 🖥 actif", len(l) == 2 and l[1]["on"] and not l[0]["on"], l)
        check("lot : sommes = plan du serveur", usd(som["cloud"]) in l[0]["t"] and usd(som["pc"]) in l[1]["t"], (som, [x["t"] for x in l]))
        pg.click("#suiviLancer"); pg.wait_for_timeout(800)
        m = dial[-1] if dial else ""
        check("confirmation Lancer : les deux estimations", "🖥 Sur mon PC" in m and "☁ En ligne" in m, m[-200:])
        pg.click("#hdrMode"); pg.wait_for_timeout(1500)
        l2 = puces(pg, "#lotEstim")
        check("rebascule ☁ : le lot suit sans recharger", l2[0]["on"] and not l2[1]["on"])
        # 360 px
        pg.set_viewport_size({"width": 360, "height": 800}); pg.wait_for_timeout(800)
        check("360 px : la page ne déborde pas", pg.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth"))
        pg.screenshot(path=os.path.join(HERE, "estim_lot_360.png"), full_page=False)
        pg.click("#suiviFermer"); pg.wait_for_timeout(400)
        pg.evaluate("() => $('narrEstim').scrollIntoView({block:'center'})"); pg.wait_for_timeout(400)
        larg = pg.evaluate("() => { const r = $('narrEstim').querySelector('.est2').getBoundingClientRect(); return [r.left, r.right]; }")
        check("360 px : les pastilles tiennent dans l'écran", larg[0] >= 0 and larg[1] <= 360, larg)
        pg.screenshot(path=os.path.join(HERE, "estim_360.png"), full_page=False)
        check("aucune erreur JS", not errs, errs[:2])
        b.close()
finally:
    shutil.rmtree(BANC, ignore_errors=True)
    reglages.ecrire(mode=mode0)
print("interrupteur remis à « %s » · série de banc retirée : %s" % (reglages.lire()["mode"], not os.path.isdir(BANC)))
print("\n%d/%d" % (len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
