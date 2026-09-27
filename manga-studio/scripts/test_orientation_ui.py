# -*- coding: utf-8 -*-
"""Banc R25 (v2.96.0) : savoir OU l'on est -- fil d'Ariane + bandeau d'ecran. App REELLE (principale 8190, One Punch-Man ch.5),
lecture seule. Usage : python test_orientation_ui.py [html] [largeur]        (html v2.95.0 -> ROUGE)"""
import os, sys
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(HERE, "..", "manga_studio.html")
LARG = int(sys.argv[2]) if len(sys.argv) > 2 else 360
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PAGE = open(HTML, encoding="utf-8").read()
OK, KO = [], []


def check(n, c, d=""):
    (OK if c else KO).append(n); print(("  [OK] " if c else "  [KO] ") + n + (" -- " + str(d)[:170] if d else ""), flush=True)


FIL = "() => [...document.querySelectorAll('#ouFil button')].map(b => b.textContent)"
BANDE = "() => { const b = document.getElementById('ouBande'); return b && !b.hidden ? [b.querySelector('.ou-t').textContent, b.style.getPropertyValue('--ouc'), b.querySelector('.retour').textContent] : null }"
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    pg = b.new_context(viewport={"width": LARG, "height": 800}, is_mobile=LARG < 700, has_touch=LARG < 700).new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.route("**/*", lambda rt: rt.fulfill(status=200, content_type="text/html; charset=utf-8", body=PAGE)
             if rt.request.method == "GET" and rt.request.url.split("#")[0].split("?")[0].rstrip("/").endswith("/manga") else rt.continue_())
    pg.goto("http://127.0.0.1:8190/manga#k=" + KEY); pg.wait_for_timeout(1500)
    pg.evaluate("() => { localStorage.removeItem('manga_serie'); localStorage.setItem('manga_onglet','tChap'); localStorage.setItem('manga_chap_bloc',''); }"); pg.reload()
    pg.wait_for_function("() => typeof RESUME !== 'undefined' && RESUME && RESUME.chapitres", timeout=30000); pg.wait_for_timeout(1500)
    check("racine de la bibliothèque : ni fil ni bandeau", pg.evaluate("() => document.getElementById('ouFil').hidden && document.getElementById('ouBande').hidden"))
    pg.evaluate("() => ouvrirSerie('one-punch-man')"); pg.wait_for_timeout(1500)
    f = pg.evaluate(FIL); bd = pg.evaluate(BANDE)
    check("série : fil « 📚 › One Punch-Man », bandeau violet « ← Toutes les séries »", f[:1] == ["📚"] and len(f) == 2 and bd and bd[1] == "#b58cff" and "Toutes les séries" in bd[2], (f, bd))
    pg.evaluate("() => openChap(CHAPS.findIndex(c => c.dir === 'one-punch-man/ch_5'))"); pg.wait_for_timeout(3000)
    f = pg.evaluate(FIL); bd = pg.evaluate(BANDE)
    check("chapitre : fil « 📚 › série › ch. 5 », bandeau rouge « CHAPITRE 5 » + « ← série »", len(f) == 3 and f[2] == "ch. 5" and bd and bd[1] == "#e84a5f" and "5" in bd[0], (f, bd))
    pg.evaluate("() => clOuvrir('dlg')"); pg.wait_for_timeout(1200)
    f = pg.evaluate(FIL); bd = pg.evaluate(BANDE)
    check("bloc 🎭 ouvert : fil « … › ch. 5 › 🎭 Dialogues », bandeau vert d'eau « DIALOGUES »", len(f) == 4 and "Dialogues" in f[3] and bd and bd[1] == "#3fc7a8" and bd[0] == "Dialogues", (f, bd))
    check("dernière étape en gras (ici)", pg.evaluate("() => document.querySelector('#ouFil button:last-child').classList.contains('ici')"))
    if LARG <= 400:
        check("fil sur UNE ligne, aucun débordement (%d px)" % LARG, pg.evaluate("() => { const f = document.getElementById('ouFil'); return f.getBoundingClientRect().height < 36 && document.documentElement.scrollWidth <= document.documentElement.clientWidth }"))
    pg.click("#ouFil [data-ou-go='chapitre']"); pg.wait_for_timeout(800)
    check("fil « ch. 5 » touché : le bloc se referme, on reste dans le chapitre", len(pg.evaluate(FIL)) == 3 and pg.evaluate("() => CL_OUVERT") == "")
    pg.click("#ouBande [data-ou-ret]"); pg.wait_for_timeout(1500)
    check("« ← série » du bandeau : retour à la fiche de la série", len(pg.evaluate(FIL)) == 2 and not pg.evaluate("() => ouVis('chapDetail')"), pg.evaluate(FIL))
    pg.evaluate("() => document.getElementById('btnDlgSerie').click()"); pg.wait_for_timeout(3000)
    bd = pg.evaluate(BANDE)
    check("panneau 🎭 de la série : bandeau « DIALOGUES DE LA SÉRIE » vert d'eau", bd and bd[0] == "Dialogues de la série" and bd[1] == "#3fc7a8", bd)
    pg.click("#ouFil [data-ou-go='racine']"); pg.wait_for_timeout(1500)
    check("fil « 📚 » touché : retour à la racine (plus de fil)", pg.evaluate("() => document.getElementById('ouFil').hidden"))
    check("0 erreur JS", not errs, errs)
print("VERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
