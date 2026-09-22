# -*- coding: utf-8 -*-
"""Banc v2.2.0 : LANGUE d'origine du chapitre + securite « francais -> francais » (Quang 22/09 12h43). 0 traduction lancee.
Proxy : detection a la 1re demande (Noritaka : langue.json retire puis redemande -> MangaDex « en »), refus de traduire vers
la langue d'origine sans « force ». App : « VO — français » (Frieren) / « VO — vietnamien » (OPM 301), « ⚠ déjà en français »
quand la langue choisie = l'origine, confirmation qui, refusee, n'envoie RIEN ; la langue sur la carte du chapitre.
Usage : python test_langue_ui.py [port]
"""
import json, os, shutil, sys, urllib.request
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
SRC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sources"))
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


def api(path, body=None):
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (PORT, path), data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


# --- proxy : detection a la demande
f = os.path.join(SRC, "noritaka", "ch_1", "langue.json")
shutil.move(f, f + ".banc")
try:
    r = api("/manga/langue?d=noritaka/ch_1")
    check("détection à la 1re demande (MangaDex)", r.get("langue") == "en" and r.get("methode") == "mangadex" and os.path.isfile(f), r)
finally:
    if not os.path.isfile(f):
        shutil.move(f + ".banc", f)
    elif os.path.isfile(f + ".banc"):
        os.remove(f + ".banc")
avant = set(os.listdir(os.path.join(SRC, "demo-frieren", "ch_143")))
r = api("/manga/traduire", {"d": "demo-frieren/ch_143", "langue": "fr"})
check("proxy : fr → fr refusé sans « force »", r.get("meme_langue") and "error" in r, r)
check("… et rien n'a été lancé", not os.path.isdir(os.path.join(SRC, "demo-frieren", "ch_143", "traduction", "fr")))
check("résumé : la langue par chapitre", api("/manga/resume")["chapitres"]["one-punch-man/ch_301"].get("langue") == "vi")

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w, h in ((1280, 1000), (360, 780)):
        print("=== %d px" % w)
        pg = b.new_page(viewport={"width": w, "height": h}); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        dialogues = []
        pg.on("dialog", lambda dl: (dialogues.append(dl.message), dl.dismiss()))       # on REFUSE : rien ne doit partir
        envois = []
        pg.on("request", lambda rq: envois.append(rq.url) if "/manga/traduire" in rq.url else None)
        pg.goto("http://127.0.0.1:%d/manga/#k=" % PORT + KEY); pg.wait_for_timeout(2500)
        pg.click('nav button[data-tab="tChap"]'); pg.wait_for_timeout(1500)
        pg.evaluate("(d) => openChap(CHAPS.findIndex(c => c.dir === d))", "demo-frieren/ch_143"); pg.wait_for_timeout(3500)
        vo = pg.evaluate("() => document.querySelector('#tradVue option[value=\"\"]').textContent")
        check("Frieren : « VO — français »", vo == "VO — français", vo)
        pg.select_option("#tradLangue", "fr"); pg.wait_for_timeout(300)
        check("langue choisie = origine → « ⚠ déjà en français »", pg.is_visible("#tradMeme") and "déjà en français" in pg.inner_text("#tradMeme"))
        pg.click("#btnTraduire"); pg.wait_for_timeout(800)
        check("confirmation « DÉJÀ en français » ; refusée → rien envoyé", dialogues and "DÉJÀ en français" in dialogues[-1] and not envois, (dialogues[-1:], envois))
        pg.select_option("#tradLangue", "en"); pg.wait_for_timeout(300)
        check("autre langue → pas d'avertissement", not pg.is_visible("#tradMeme"))
        pg.evaluate("(d) => openChap(CHAPS.findIndex(c => c.dir === d))", "one-punch-man/ch_301"); pg.wait_for_timeout(3500)
        vo = pg.evaluate("() => document.querySelector('#tradVue option[value=\"\"]').textContent")
        check("OPM 301 : « VO — vietnamien »", vo == "VO — vietnamien", vo)
        pg.evaluate("() => { const b = document.querySelector('#chapList [data-serie=\"one-punch-man\"]'); if (b) b.click(); }"); pg.wait_for_timeout(2000)
        carte = pg.evaluate("() => [...document.querySelectorAll('#chapList [data-chap]')].map(b => b.innerText).join(' | ')")
        check("carte du chapitre : « VO vietnamien »", "VO vietnamien" in carte, carte[:160].replace("\n", " "))
        dep = pg.evaluate("() => document.documentElement.scrollWidth - innerWidth")
        check("aucun débordement", dep <= 0, dep)
        check("0 erreur JS", not errs, errs[:3])
        pg.close()
    b.close()
print("\n%d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
