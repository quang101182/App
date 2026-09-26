# -*- coding: utf-8 -*-
"""Banc v2.67.1 (Quang 26/09 03h35) : la FIN d'une capture n'ouvre plus le manga / le chapitre (l'ecran en cours ne bouge pas),
un message le dit, la bibliotheque est rafraichie. APP REELLE (8190), fin de capture SIMULEE (api() remplace dans la page pour
/manga/fetch_status uniquement) : quelques secondes, aucune capture lancee, rien n'est ecrit.
Cas : serie terminee (dossiers) et chapitre seul (dossier), avec l'utilisateur sur un autre onglet (Galerie).
Usage : python test_fin_capture_ui.py [port]
"""
import os, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
OK, KO = [], []
def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail)[:200] if detail else ""))

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    pg = b.new_page(viewport={"width": 476, "height": 860}); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("http://127.0.0.1:%d/manga#k=%s" % (PORT, KEY)); pg.wait_for_timeout(4000)
    d0 = pg.evaluate("() => CHAPS.length ? CHAPS[0].dir : null")
    check("bibliothèque chargée", bool(d0), d0)
    for nom, statut in (
        ("série", {"etat": "fini", "code": 0, "titre": "Banc", "chapitre": "3", "chapitre_depart": "1", "jusqua": "3", "suite": 0,
                   "serie": "SÉRIE : 3 chapitre(s) : 1, 2, 3 — arrêt : jusqu'au ch. 3 : fait", "dossiers": [d0], "sortie": [], "duree_s": 60}),
        ("chapitre seul", {"etat": "fini", "code": 0, "titre": "Banc", "chapitre": "1", "chapitre_depart": "1", "jusqua": "", "suite": 0,
                           "dossier": d0, "dossiers": [d0], "sortie": [], "duree_s": 30})):
        pg.evaluate("""(st) => { $('chapDetail').hidden = true; CHAP_OPEN = null;
            const btn = [...document.querySelectorAll('button, a')].find(x => /Galerie/.test(x.textContent)); if (btn) btn.click();
            window.__api0 = window.__api0 || api;
            api = (p, b) => p === '/manga/fetch_status' ? Promise.resolve(st) : window.__api0(p, b); }""", statut)
        pg.wait_for_timeout(400)
        avant = pg.evaluate("() => location.hash + '|' + (document.querySelector('.tab.on, nav .on, [aria-selected=true]') || {}).textContent")
        pg.evaluate("() => suivreCapture()"); pg.wait_for_timeout(2500)
        apres = pg.evaluate("() => location.hash + '|' + (document.querySelector('.tab.on, nav .on, [aria-selected=true]') || {}).textContent")
        ouvert = pg.evaluate("() => [CHAP_OPEN, $('chapDetail').hidden]")
        msg = pg.evaluate("() => [...document.querySelectorAll('.toast, #toast, [class*=toast]')].map(x => x.textContent).join(' | ')")
        check("%s : aucun chapitre ouvert automatiquement" % nom, ouvert[0] is None and ouvert[1] is True, ouvert)
        check("%s : l'écran en cours ne bouge pas" % nom, avant == apres, [avant, apres])
        check("%s : un message « capture terminée »" % nom, "capture terminée" in msg, msg)
        pg.evaluate("() => { api = window.__api0; }")
    check("aucune erreur JS", not errs, errs[:3])
    b.close()
print("\nVERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
