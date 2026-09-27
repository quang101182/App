# -*- coding: utf-8 -*-
"""Banc v2.99.2 (captures de Quang 27/09 16h34-16h36). App REELLE 8190, lecture seule (non-GET intercepte, service worker bloque).
1. fil d'Ariane DANS la colonne de l'app (grand ecran 1362 px et 360 px) ;
2. panneaux 🎬 Videos et 🎭 Dialogues de la serie : UN seul bouton « ← serie » visible, et il ramene bien a la serie ;
3. bloc 🎭 du chapitre : « ✓ Voix » de la meme couleur que « ✓ Video » quand les voix sont faites.
Usage : python test_fil_doublon_ui.py <serie> <serie/ch_N voix faites> [--ancien fichier.html]   (--ancien -> ROUGE)"""
import os, sys
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
args = sys.argv[1:]
ANCIEN = None
if "--ancien" in args:
    i = args.index("--ancien"); ANCIEN = open(args[i + 1], encoding="utf-8").read(); del args[i:i + 2]
SERIE, CH = args[0], args[1]
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail)[:170] if detail else ""), flush=True)


VIS = "el => !!(el && el.offsetParent)"
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w, h in ((1362, 850), (360, 780)):
        print("=== %d px" % w)
        ctx = b.new_context(viewport={"width": w, "height": h}, is_mobile=w < 800, has_touch=w < 800, service_workers="block")
        pg = ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        def route(rt):
            u = rt.request.url.split("#")[0].split("?")[0].rstrip("/")
            if rt.request.method != "GET":
                return rt.fulfill(status=200, body='{"ok":true}', content_type="application/json")
            if ANCIEN and u.endswith("/manga"):
                return rt.fulfill(status=200, body=ANCIEN, content_type="text/html; charset=utf-8")
            return rt.continue_()
        pg.route("**/*", route)
        pg.goto("http://127.0.0.1:8190/manga/#k=" + KEY); pg.wait_for_timeout(3000)
        pg.evaluate("s => { localStorage.setItem('manga_onglet','tChap'); localStorage.setItem('manga_serie', s); localStorage.setItem('manga_chap_bloc',''); }", SERIE)
        pg.reload(); pg.wait_for_timeout(4000)
        print("     version : " + pg.evaluate("() => VERSION"))
        for nom, mot, bid in (("Videos", "Vidéos", "vidFermer"), ("Dialogues", "Dialogues", "dlgsFermer")):
            pg.evaluate("id => document.getElementById(id).click()", "btnVideos" if nom == "Videos" else "btnDlgSerie")
            pg.wait_for_timeout(1500)
            r = pg.evaluate("""bid => { const f = document.getElementById('ouFil'), m = document.querySelector('main'), cs = getComputedStyle(m);
                const fb = f.querySelector('button'), mg = m.getBoundingClientRect().left + parseFloat(cs.paddingLeft);
                const rets = [...document.querySelectorAll('.btn.retour')].filter(x => x.offsetParent);
                return { fil: !f.hidden, filG: fb ? Math.round(fb.getBoundingClientRect().left) : -1, colG: Math.round(mg),
                         rets: rets.map(x => x.textContent.trim()), ouvert: !!document.getElementById(bid).closest('.pan:not([hidden])') }; }""", bid)
            check("%s : panneau ouvert, fil d'Ariane affiche" % nom, r["ouvert"] and r["fil"], r)
            check("%s : fil aligne sur la colonne de l'app (±12 px)" % nom, abs(r["filG"] - r["colG"]) <= 12, (r["filG"], r["colG"]))
            ban = pg.evaluate("() => (document.querySelector('.ou-bande [data-ou-ret]') || {}).textContent || ''").strip()
            check("%s : UN seul bouton « %s » visible (pas de doublon sous le bandeau)" % (nom, ban), bool(ban) and [x for x in r["rets"]].count(ban) == 1, r["rets"])
            pg.evaluate("() => document.querySelector('.ou-bande [data-ou-ret]').click()"); pg.wait_for_timeout(1200)
            ferme = pg.evaluate("bid => !document.getElementById(bid).closest('.pan:not([hidden])')", bid)
            check("%s : le bouton du bandeau ramene a la serie (panneau ferme)" % nom, ferme)
        # bloc 🎭 du chapitre
        pg.evaluate("d => openChap(CHAPS.findIndex(c => c.dir === d))", CH); pg.wait_for_timeout(3000)
        pg.evaluate("() => clOuvrir('dlg')"); pg.wait_for_timeout(2500)
        c = pg.evaluate("""() => { const v = $('dlgVoix'), d = $('dplPrepFait'), col = el => getComputedStyle(el).color + '|' + getComputedStyle(el).opacity;
                              return { voix: v.textContent, cv: col(v), vid: d.textContent, cd: col(d) }; }""")
        if c["voix"].startswith("✓") and c["vid"].startswith("✓"):
            check("« ✓ Voix » de la meme couleur que « ✓ Prepare »", c["cv"] == c["cd"], c)
        else:
            print("     (pas de voix + video faites sur ce chapitre : contrôle de couleur saute)", c)
        check("0 erreur JS", not errs, errs[:2])
        ctx.close()
    b.close()
print("\nVERDICT : %d/%d" % (len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
