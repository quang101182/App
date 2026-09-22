# -*- coding: utf-8 -*-
"""Banc v1.99.0 : HORS-LIGNE (One Punch-Man ch.301, narration avec voix + « Precedemment... »).
En ligne : 📥 garde la narration (fichiers dans le cache de l'app, index, liste « Gardes sur ce telephone »).
PUIS RESEAU COUPE (le navigateur est mis hors ligne = PC eteint) : l'app s'ouvre quand meme (coquille gardee),
la liste est la, ▶ lit : « Precedemment... » (image + son qui JOUE), page suivante (image chargee, son qui joue),
deplacement dans la barre de temps (morceaux d'audio servis depuis le stockage). Retour en ligne : 🗑 retire tout.
Usage : python test_horsligne_ui.py [port]
"""
import os, sys
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
D = "one-punch-man/ch_301"
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


ETAT = """() => { const p = LEC.n && LEC.n.pages[LEC.i], a = document.getElementById('lecAudio'), im = document.getElementById('lecImg');
  return { prec: p ? (p.prec || null) : null, info: document.getElementById('lecInfo').textContent, t: a.currentTime, paused: a.paused,
           img: im.complete && im.naturalWidth > 0, n: LEC.n ? LEC.n.pages.length : 0 }; }"""

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True, args=["--autoplay-policy=no-user-gesture-required"])
    for w, h in ((1280, 1000), (360, 780)):
        print("=== %d px" % w)
        c = b.new_context(viewport={"width": w, "height": h}, is_mobile=w < 500, has_touch=w < 500)
        pg = c.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("dialog", lambda dl: dl.accept())
        pg.goto("http://127.0.0.1:%d/manga/#k=" % PORT + KEY); pg.wait_for_timeout(3000)
        pg.evaluate("() => { try { localStorage.setItem('manga_mus_on', '0'); localStorage.removeItem('manga_hl'); } catch {} }")
        pg.reload(); pg.wait_for_timeout(3000)
        check("service worker actif et en contrôle", pg.evaluate("() => !!navigator.serviceWorker.controller"))
        check("pas de liste tant que rien n'est gardé", not pg.is_visible("#hlBox"))
        pg.click('nav button[data-tab="tChap"]'); pg.wait_for_timeout(1200)
        pg.evaluate("(d) => openChap(CHAPS.findIndex(c => c.dir === d))", D); pg.wait_for_timeout(3000)
        i = pg.evaluate("() => NARRS.findIndex(n => n.etat === 'fini' && n.audio)")
        pg.click('#narrRuns [data-hl="%d"]' % i)
        pg.wait_for_function("() => (JSON.parse(localStorage.getItem('manga_hl') || '[]')).length === 1", timeout=180000)
        pg.wait_for_timeout(1500)
        e = pg.evaluate("() => JSON.parse(localStorage.getItem('manga_hl'))[0]")
        check("gardé : index + fichiers", e["d"] == D and len(e["urls"]) > 20 and e["octets"] > 5e6, (len(e["urls"]), e["octets"]))
        n_cache = pg.evaluate("async () => (await (await caches.open('manga-horsligne-v1')).keys()).filter(r => !r.url.includes('__index_horsligne')).length")
        check("tous les fichiers sont dans le cache", n_cache == len(e["urls"]), (n_cache, len(e["urls"])))
        check("le bouton passe à ✅", pg.inner_text('#narrRuns [data-hl="%d"]' % i) == "✅")
        # --- le defaut mesure sur le Samsung : localStorage PERDU (ecrit en retard, app tuee juste apres)
        pg.evaluate("() => localStorage.removeItem('manga_hl')")
        # --- PC eteint
        c.set_offline(True)
        pg.reload(); pg.wait_for_timeout(3000)
        check("PC éteint : l'app s'ouvre quand même", pg.inner_text("#verBadge").startswith("v1.9"), pg.inner_text("#verBadge"))
        check("PC éteint + localStorage perdu : la liste des gardés est là (index dans le cache)", pg.is_visible("#hlBox") and "ch. 301" in pg.inner_text("#hlListe"), pg.inner_text("#hlTitre"))
        dep = pg.evaluate("() => document.documentElement.scrollWidth - innerWidth")
        check("aucun débordement", dep <= 0, dep)
        pg.click('#hlListe [data-hl-lire="0"]'); pg.wait_for_timeout(4000)
        s = pg.evaluate(ETAT)
        check("PC éteint : « Précédemment… » en tête, image affichée, son qui JOUE", s["prec"] == "ouverture" and s["img"] and s["t"] > 0.5 and not s["paused"], s)
        pg.click("#lecNext"); pg.wait_for_timeout(3500)
        s = pg.evaluate(ETAT)
        check("PC éteint : page du chapitre, image + son", s["prec"] is None and s["img"] and s["t"] > 0.5, s)
        # page visee = meme calcul que allerA ; puis le son doit AVANCER (morceaux servis depuis le stockage)
        vise = pg.evaluate("() => { let t = 0.6 * lecAvant(LEC.n.pages.length), i = 0; while (i < LEC.n.pages.length - 1 && t >= dureePage(LEC.n.pages[i])){ t -= dureePage(LEC.n.pages[i]); i++; } return i; }")
        pg.evaluate("() => allerA(0.6)"); pg.wait_for_timeout(1200)
        t1 = pg.evaluate("() => document.getElementById('lecAudio').currentTime"); pg.wait_for_timeout(1500)
        t2 = pg.evaluate("() => document.getElementById('lecAudio').currentTime")
        check("PC éteint : saut à 60 % -> bonne page, le son avance", pg.evaluate("() => LEC.i") == vise and t2 - t1 > 1.0,
              (pg.evaluate("() => LEC.i"), vise, round(t1, 2), round(t2, 2)))
        pg.click("#lecFermer"); pg.wait_for_timeout(300)
        # --- retour en ligne, retrait
        c.set_offline(False)
        pg.click('#hlListe [data-hl-suppr="0"]'); pg.wait_for_timeout(1500)
        n_cache = pg.evaluate("async () => (await (await caches.open('manga-horsligne-v1')).keys()).filter(r => !r.url.includes('__index_horsligne')).length")
        check("retiré : cache vidé, liste cachée", n_cache == 0 and not pg.is_visible("#hlBox"), n_cache)
        check("0 erreur JS", not errs, errs[:3])
        c.close()
    b.close()
print("\n%d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
