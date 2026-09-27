# -*- coding: utf-8 -*-
"""Banc v2.81.5 (UI) : « traduire seulement les pages des Dialogues » + tracabilite, ISOLE : instance 8191 (proxy patche 5) sur
une COPIE ou OPM ch.302 a les pages 2,3,5,7,9 traduites via Dialogues et ch.303 rien ; page = le HTML donne (interception).
Le lancement est INTERCEPTE (rien de paye). Usage : python test_trad_partielle_ui.py <html> <proxy patche> <sources copie>"""
import json, os, subprocess, sys, time, urllib.request
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
HTML, PROXY, T = (os.path.abspath(x) for x in sys.argv[1:4])
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PAGE = open(HTML, encoding="utf-8").read()
OK, KO = [], []
def check(n, c, d=""):
    (OK if c else KO).append(n); print(("  [OK] " if c else "  [KO] ") + n + (" -- " + str(d)[:170] if d else ""), flush=True)
srv = subprocess.Popen([sys.executable, os.path.join(HERE, "proxy_8191.py"), PROXY], env=dict(os.environ, MANGA_SOURCES_DIR=T),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(60):
        try: urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8191/manga/el_solde", headers={"Authorization": "Bearer " + KEY}), timeout=5); break
        except Exception: time.sleep(1)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        for w, h in ((1280, 900), (360, 780)):
            print("=== %d px" % w)
            ctx = b.new_context(viewport={"width": w, "height": h}, is_mobile=w < 500, has_touch=w < 500)
            pg = ctx.new_page(); errs = []; lances = []; dialogues = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.on("dialog", lambda d: (dialogues.append(d.message), d.accept() if len(dialogues) > 1 else d.dismiss()))
            def route(rt):
                u = rt.request.url.split("#")[0].split("?")[0]
                if rt.request.method == "GET" and u.rstrip("/").endswith("/manga"):
                    return rt.fulfill(status=200, content_type="text/html; charset=utf-8", body=PAGE)
                if u.endswith("/manga/dialogues_lancer"):
                    lances.append(json.loads(rt.request.post_data or "{}"))
                    return rt.fulfill(status=200, content_type="application/json", body='{"ok": true}')
                return rt.continue_()
            pg.route("**/*", route)
            pg.goto("http://127.0.0.1:8191/manga#k=" + KEY); pg.wait_for_timeout(2500)
            pg.evaluate("() => { localStorage.setItem('manga_serie','one-punch-man'); }"); pg.reload(); pg.wait_for_function("() => typeof RESUME !== 'undefined' && RESUME && RESUME.chapitres", timeout=30000); pg.wait_for_timeout(1500)
            badge = pg.evaluate("() => { const r = RESUME.chapitres['one-punch-man/ch_302']; return r ? (r.trad || []).join() + '|' + (r.trad_partiel || []).join() : null }")
            check("bibliotheque : ch.302 = FR partiel, pas FR complet", badge == "|fr", badge)
            txt = pg.evaluate("() => document.body.innerText")
            check("bibliotheque : « 🌐 FR partiel » affiche", "FR partiel" in txt)
            # --- ch.302 : traduction partielle tracee
            pg.evaluate("() => openChap(CHAPS.findIndex(c => c.dir === 'one-punch-man/ch_302'))"); pg.wait_for_timeout(4000)
            te = pg.evaluate("() => $('tradEtat').textContent")
            check("ligne 🌐 : « 5 / 18 pages », « via 🎭 Dialogues », « le reste est en version originale »",
                  "5 / 18 pages" in te and "via 🎭 Dialogues" in te and "version originale" in te, te)
            tete = pg.evaluate("() => document.querySelector('.bloc-trad .cl-etat') ? document.querySelector('.bloc-trad .cl-etat').textContent : ''")
            check("ligne 🌐 repliee : dit « 5 / 18 pages »", "5 / 18 pages" in tete, tete)
            pg.click("#dlgBox .cl-chev"); pg.wait_for_timeout(300); pg.click("#dlgBox .dlg-p[data-portee=pages]")
            pg.fill("#dlgDe", "2"); pg.fill("#dlgA", "3"); pg.wait_for_timeout(400)
            check("pages 2-3 deja traduites : bouton « 🎭 Préparer » normal", pg.evaluate("() => $('dlgPreparer').textContent") == "🎭 Préparer")
            pg.fill("#dlgA", "4"); pg.wait_for_timeout(400)
            et = pg.evaluate("() => $('dlgEtat').textContent")
            check("pages 3-4 : « 1 page à traduire d'abord (p. 4) » + cout traduction", "1 page à traduire d'abord (p. 4)" in et and "traduction" in et, et)
            # --- ch.303 : rien de traduit
            pg.evaluate("() => openChap(CHAPS.findIndex(c => c.dir === 'one-punch-man/ch_303'))"); pg.wait_for_timeout(3500)
            if "cl-ouv" not in pg.evaluate("() => $('dlgBox').className"): pg.click("#dlgBox .cl-chev"); pg.wait_for_timeout(300)
            pg.click("#dlgBox .dlg-p[data-portee=chap]"); pg.wait_for_timeout(300)
            et = pg.evaluate("() => $('dlgEtat').textContent")
            check("ch.303 « ce chapitre » : invite a choisir des pages, Preparer grise", "choisis « des pages »" in et and pg.evaluate("() => $('dlgPreparer').disabled"), et)
            pg.click("#dlgBox .dlg-p[data-portee=pages]"); pg.fill("#dlgDe", "4"); pg.fill("#dlgA", "6"); pg.wait_for_timeout(400)
            et = pg.evaluate("() => $('dlgEtat').textContent")
            check("ch.303 p.4-6 : « 3 pages à traduire d'abord (p. 4-6) », ≈ 0,027 $ traduction (3 x 0,009 mesure)", "3 pages à traduire d'abord (p. 4-6)" in et and "0.027" in et.replace(",", "."), et)
            check("bouton « 🌐 Traduire puis préparer », actif", pg.evaluate("() => $('dlgPreparer').textContent") == "🌐 Traduire puis préparer"
                  and not pg.evaluate("() => $('dlgPreparer').disabled"))
            pg.click("#dlgPreparer"); pg.wait_for_timeout(800)
            check("1er appui : confirmation qui dit le prix et « version originale » ; refusee = rien lance",
                  dialogues and "Traduire 3 pages" in dialogues[0] and "version originale" in dialogues[0] and not lances, (dialogues[:1], lances))
            pg.click("#dlgPreparer"); pg.wait_for_timeout(800)
            check("confirmee : lancement avec traduire=true et pages 4-6", lances and lances[-1].get("traduire") is True and lances[-1].get("pages") == "4-6", lances)
            check("0 erreur JS, pas de debordement", not errs and not pg.evaluate("() => document.documentElement.scrollWidth > document.documentElement.clientWidth"), errs)
            pg.screenshot(path=os.path.join(os.environ.get("TEMP", "."), "trad_partielle_%d.png" % w))
            ctx.close()
finally:
    srv.kill()
    try: os.remove(os.path.expanduser(r"~\Documents\ComfyUI\_studio_llm_proxy_8191.py"))
    except Exception: pass
print("VERDICT : %d OK / %d KO" % (len(OK), len(KO)))
