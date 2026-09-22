# -*- coding: utf-8 -*-
"""Banc UI v1.96.0 : chapitre PRECEDENT / SUIVANT (One Punch-Man ch.300 <-> ch.301 ; Claymore = un seul chapitre).
Fiche : ⏮ / ⏭ presents seulement s'il y a un voisin, ouvrent le bon chapitre. Lecteur : ch. ⏭ enchaine la narration
du voisin (le son JOUE, le « Precedemment... » en tete si coche), ⏮ ch. revient ; fin de chapitre = « ▶ Chapitre
suivant » ; ecoute a l'aveugle sans boutons ; rien ne deborde a 360 px. Usage : python test_chapitres_voisins_ui.py [port]
"""
import os, sys
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


ETAT = """() => { const p = LEC.n && LEC.n.pages[LEC.i], a = document.getElementById('lecAudio');
  return { chap: CHAP_OPEN, prec: p ? (p.prec || null) : null, t: a.currentTime, paused: a.paused, ouvert: !document.getElementById('lecteur').hidden,
           prev: [document.getElementById('lecChPrev').hidden, document.getElementById('lecChPrev').disabled],
           next: [document.getElementById('lecChNext').hidden, document.getElementById('lecChNext').disabled] }; }"""

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True, args=["--autoplay-policy=no-user-gesture-required"])
    for w, h in ((1280, 1000), (360, 780)):
        print("=== %d px" % w)
        c = b.new_context(viewport={"width": w, "height": h}, is_mobile=w < 500, has_touch=w < 500)
        pg = c.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto("http://127.0.0.1:%d/manga/#k=" % PORT + KEY); pg.wait_for_timeout(2500)
        pg.evaluate("() => { try { localStorage.setItem('manga_mus_on', '0'); localStorage.removeItem('manga_prec'); } catch {} }")
        pg.reload(); pg.wait_for_timeout(2500)
        pg.click('nav button[data-tab="tChap"]'); pg.wait_for_timeout(1200)
        ouvre = lambda d: pg.evaluate("(d) => openChap(CHAPS.findIndex(c => c.dir === d))", d)
        ouvre("claymore/ch_1"); pg.wait_for_timeout(2500)
        check("Claymore (1 chapitre) : ni ⏮ ni ⏭", not pg.is_visible("#chapPrev") and not pg.is_visible("#chapNext"))
        ouvre("one-punch-man/ch_301"); pg.wait_for_timeout(2500)
        check("ch.301 : ⏮ ch. 300 visible, pas de ⏭", pg.is_visible("#chapPrev") and "300" in pg.inner_text("#chapPrev")
              and not pg.is_visible("#chapNext"), pg.inner_text("#chapPrev"))
        pg.click("#chapPrev"); pg.wait_for_timeout(2500)
        check("⏮ ouvre le ch.300", pg.evaluate("CHAP_OPEN") == "one-punch-man/ch_300" and "300" in pg.inner_text("#chapTitle"), pg.inner_text("#chapTitle"))
        check("ch.300 : ch. 301 ⏭ visible", pg.is_visible("#chapNext") and "301" in pg.inner_text("#chapNext"), pg.inner_text("#chapNext"))
        dep = pg.evaluate("() => document.documentElement.scrollWidth - innerWidth")
        check("fiche : aucun débordement", dep <= 0, dep)
        # --- lecteur
        tag = pg.evaluate("async () => (await narrAvecVoix(CHAP_OPEN)).tag")
        pg.evaluate("(t) => ouvrirLecteur([t])", tag); pg.wait_for_timeout(3000)
        e = pg.evaluate(ETAT)
        check("lecteur ch.300 : ⏮ caché, ch. ⏭ actif", e["prev"][0] and not e["next"][0] and not e["next"][1], (e["prev"], e["next"]))
        top = pg.evaluate("() => { const t = document.querySelector('.lec-top'); return [t.scrollWidth - t.clientWidth, document.getElementById('lecFermer').getBoundingClientRect().right <= innerWidth]; }")
        check("barre du lecteur : rien ne déborde, ✕ visible", top[0] <= 0 and top[1], top)
        pg.click("#lecChNext"); pg.wait_for_timeout(4500)
        e = pg.evaluate(ETAT)
        check("ch. ⏭ : lecteur toujours ouvert, sur le ch.301", e["ouvert"] and e["chap"] == "one-punch-man/ch_301", e["chap"])
        check("ch.301 : « Précédemment… » en tête et le son JOUE", e["prec"] == "ouverture" and e["t"] > 0.5 and not e["paused"], (e["prec"], e["t"]))
        check("ch.301 : ⏮ ch. actif, ⏭ caché", not e["prev"][0] and not e["prev"][1] and e["next"][0], (e["prev"], e["next"]))
        pg.click("#lecChPrev"); pg.wait_for_timeout(4500)
        e = pg.evaluate(ETAT)
        check("⏮ ch. : retour au ch.300, le son joue", e["chap"] == "one-punch-man/ch_300" and e["t"] > 0.5, (e["chap"], e["t"]))
        pg.evaluate("() => finNarr()"); pg.wait_for_timeout(500)
        check("fin du ch.300 : « ▶ Chapitre suivant »", pg.is_visible(".lec-fin-suiv") and "301" in pg.inner_text(".lec-fin-suiv"), pg.inner_text("#lecSous")[:80])
        pg.click(".lec-fin-suiv"); pg.wait_for_timeout(4500)
        check("« Chapitre suivant » enchaîne le ch.301", pg.evaluate(ETAT)["chap"] == "one-punch-man/ch_301")
        pg.click("#lecFermer"); pg.wait_for_timeout(300)
        pg.evaluate("(t) => ouvrirLecteur([t], true)", pg.evaluate("async () => (await narrAvecVoix(CHAP_OPEN)).tag")); pg.wait_for_timeout(1500)
        e = pg.evaluate(ETAT)
        check("écoute à l'aveugle : pas de boutons de chapitre", e["prev"][0] and e["next"][0])
        pg.click("#lecFermer"); pg.wait_for_timeout(300)
        check("0 erreur JS", not errs, errs[:3])
        pg.evaluate("() => { try { localStorage.removeItem('manga_mus_on'); } catch {} }")
        c.close()
    b.close()
print("\n%d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
