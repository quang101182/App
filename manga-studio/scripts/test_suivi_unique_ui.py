# -*- coding: utf-8 -*-
"""Banc v2.79.2 : UN seul suivi de capture a la fois. Reproduit le journal du telephone de Quang (26/09 12h54:31 : ~40 lignes
« capture en serie terminee » en 50 ms) : 40 suivreCapture() lances d'un coup, /manga/fetch_status SIMULE lent (800 ms) et
« fini » -> on compte les lignes « terminee » et les rechargements de la bibliotheque. APP REELLE, rien n'est ecrit.
Usage : python test_suivi_unique_ui.py [port] [--mutation]   (--mutation : app v2.79.1 servie -> doit sortir ROUGE)
"""
import json, os, sys, time
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
MUT = "--mutation" in sys.argv; sys.argv = [a for a in sys.argv if a != "--mutation"]
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
ICI = os.path.dirname(os.path.abspath(__file__))
OK, KO = [], []
def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail)[:200] if detail else ""), flush=True)

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    pg = b.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.route("**/*", lambda r: r.abort() if r.request.method == "POST" else r.continue_())
    if MUT:
        corps = open(os.path.join(ICI, "..", "manga_studio.html.bak-20260926-v2792"), encoding="utf-8").read()   # = v2.79.1
        pg.route("**/manga", lambda r, q=None: r.fulfill(status=200, content_type="text/html; charset=utf-8", body=corps))
    pg.goto("http://127.0.0.1:%d/manga#k=%s" % (PORT, KEY)); pg.wait_for_timeout(4500)
    lent = {"n": 0}
    def statut(route):
        lent["n"] += 1; time.sleep(0.8)
        route.fulfill(status=200, content_type="application/json", body=json.dumps({"etat": "fini", "suite": 2, "serie": "SÉRIE : 1 chapitre(s) : 1",
                      "dossiers": [], "titre": "banc suivi", "chapitre": "1", "duree_s": 1, "sortie": []}))
    pg.route("**/manga/fetch_status*", statut)
    pg.evaluate("""() => { window._nRefresh = 0; const r = refreshChaps; refreshChaps = async (...a) => { _nRefresh++; return r(...a); };
                    window._nLog = 0; const l = log; log = (m, ...x) => { if (/capture en série terminée/.test(m)) _nLog++; return l(m, ...x); }; }""")
    pg.evaluate("() => { for (let i = 0; i < 40; i++) suivreCapture().catch(() => {}); }")
    pg.wait_for_timeout(6000)
    n = pg.evaluate("() => [_nLog, _nRefresh]")
    check("40 suivis lancés d'un coup → UNE seule ligne « capture en série terminée »", n[0] == 1, n)
    check("… et UN seul rechargement de la bibliothèque", n[1] == 1, n)
    check("un seul appel au serveur pendant le suivi en cours (pas 40)", lent["n"] <= 2, lent["n"])
    pg.evaluate("() => suivreCapture().catch(() => {})"); pg.wait_for_timeout(2500)
    check("le suivi suivant repart normalement une fois le 1er fini", pg.evaluate("() => _nLog") == 2, pg.evaluate("() => _nLog"))
    check("aucune erreur JS", not errs, errs[:3])
    b.close()
print("\nVERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
