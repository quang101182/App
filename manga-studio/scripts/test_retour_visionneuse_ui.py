# -*- coding: utf-8 -*-
"""Banc v2.61.0. APP REELLE (8190), One Punch-Man ch.301, 1280 px puis 360 px. Tout POST bloque.
A. (Quang 13h49) appui long -> « Tout traiter » -> fermer = RETOUR exact la ou on etait : par ← Fermer de la barre, par le
   bouton du panneau, et (PC) par Echap. Mesure : la place du chapitre a l'ecran, avant / apres (± 6 px).
B. (Quang 13h48) visionneuse (image agrandie) : la meme barre -- bulle verte « page N/M » a gauche, ← Fermer, ‹ › ronds -- et
   glissement SUR LA BARRE dans le sens des boutons (droite = suivante, gauche = precedente), geste court = rien.
Usage : python test_retour_visionneuse_ui.py [port]
"""
import os, sys
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = sys.argv[1] if len(sys.argv) > 1 else "8190"
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


APPUI = """() => new Promise(ok => { const b = $('nfInfo'), r = b.getBoundingClientRect(), x = r.left + r.width / 2, y = r.top + r.height / 2;
  b.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, pointerType: 'touch', button: 0, clientX: x, clientY: y }));
  setTimeout(() => { b.dispatchEvent(new PointerEvent('pointerup', { bubbles: true, pointerType: 'touch', clientX: x, clientY: y })); ok(); }, 800); })"""
GLISSE = """([dx]) => { const n = document.querySelector('#lightbox .lbbar'), r = $('lbName').getBoundingClientRect(), y = r.top + r.height / 2, x0 = r.left + r.width / 2;
  const t = x => new Touch({ identifier: 1, target: $('lbName'), clientX: x, clientY: y });
  $('lbName').dispatchEvent(new TouchEvent('touchstart', { touches: [t(x0)], changedTouches: [t(x0)], bubbles: true }));
  for (let k = 1; k <= 6; k++) $('lbName').dispatchEvent(new TouchEvent('touchmove', { touches: [t(x0 + dx * k / 6)], changedTouches: [t(x0 + dx * k / 6)], bubbles: true }));
  $('lbName').dispatchEvent(new TouchEvent('touchend', { touches: [], changedTouches: [t(x0 + dx)], bubbles: true })); }"""

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w, h in ((1280, 900), (360, 780)):
        tel = w < 400
        print("=== %d px" % w)
        c = b.new_context(viewport={"width": w, "height": h}, is_mobile=tel, has_touch=tel)
        pg = c.new_page(); errs, posts = [], []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        def route(rt):
            r = rt.request
            if r.method == "POST" and not any(k in r.url for k in ("activite", "costs", "savelog")):
                posts.append(r.url.split("?")[0]); return rt.abort()
            rt.continue_()
        pg.route("**/*", route)
        pg.goto("http://127.0.0.1:%s/manga#k=%s" % (PORT, KEY)); pg.wait_for_timeout(2500)
        pg.evaluate("() => { localStorage.setItem('manga_onglet','tChap'); localStorage.setItem('manga_serie','one-punch-man'); localStorage.removeItem('manga_chap_bloc'); }")
        pg.reload(); pg.wait_for_timeout(4500)
        i = pg.evaluate("() => CHAPS.findIndex(c => c.dir === 'one-punch-man/ch_301')")
        pg.evaluate("i => document.querySelector('#chapList [data-chap=\"' + i + '\"]').click()", i); pg.wait_for_timeout(3500)
        ou = lambda: pg.evaluate("() => Math.round($('chapDetail').getBoundingClientRect().top)")
        # --- A. retour exact, par les 3 chemins
        chemins = [("← Fermer de la barre", "() => $('nfRet').click()"), ("bouton du panneau", "() => $('suiviFermer').click()")]
        if not tel:
            chemins.append(("Échap", None))
        for nom, js in chemins:
            pg.evaluate("() => { const f = document.querySelectorAll('#chapPages figure')[6]; scrollTo(0, scrollY + f.getBoundingClientRect().top - 120); }")
            pg.wait_for_timeout(700)
            avant = ou()
            pg.evaluate(APPUI); pg.wait_for_timeout(1800)
            ouvert = pg.evaluate("() => !$('suiviBox').hidden")
            deplace = abs(ou() - avant) > 30
            if js: pg.evaluate(js)
            else: pg.keyboard.press("Escape")
            pg.wait_for_timeout(900)
            apres = ou()
            check("appui long → Tout traiter → %s : retour EXACT sur le chapitre" % nom, ouvert and deplace and abs(apres - avant) <= 6
                  and pg.evaluate("() => $('suiviBox').hidden && CHAP_OPEN === 'one-punch-man/ch_301'"), (avant, apres))
        # --- B. visionneuse
        pg.evaluate("() => document.querySelectorAll('#chapPages figure img')[2].click()"); pg.wait_for_timeout(1500)
        check("visionneuse ouverte", pg.evaluate("() => !$('lightbox').hidden"))
        v = pg.evaluate("""() => [getComputedStyle($('lbName')).backgroundColor, $('lbName').getBoundingClientRect().left < $('lbClose').getBoundingClientRect().left,
            ['lbClose', 'lbPrev', 'lbNext'].every(id => parseFloat(getComputedStyle($(id)).borderRadius) >= 18), $('lbName').textContent]""")
        check("même barre : bulle VERTE « page N/M » à gauche, boutons ronds", v[0] == "rgb(31, 91, 58)" and v[1] and v[2] and v[3].startswith("3/"), v)
        n0 = pg.evaluate("() => LB")
        if tel:
            pg.evaluate(GLISSE, [25]); pg.wait_for_timeout(500)
            check("glissement COURT sur la barre : rien", pg.evaluate("() => LB") == n0)
            pg.evaluate(GLISSE, [120]); pg.wait_for_timeout(700)
            check("glissement à DROITE : image SUIVANTE (le sens du bouton ›)", pg.evaluate("() => LB") == n0 + 1, pg.evaluate("() => LB"))
            pg.evaluate(GLISSE, [-120]); pg.wait_for_timeout(700)
            check("glissement à GAUCHE : image PRÉCÉDENTE", pg.evaluate("() => LB") == n0, pg.evaluate("() => LB"))
            r = pg.evaluate("() => [innerWidth, innerHeight]")
            check("affichage intact après les glissements", r == [360, 780], r)
        pg.click("#lbNext"); pg.wait_for_timeout(500)
        check("› : image suivante", pg.evaluate("() => LB") == n0 + 1)
        pg.click("#lbClose"); pg.wait_for_timeout(500)
        check("← Fermer : visionneuse fermée", pg.evaluate("() => $('lightbox').hidden"))
        if tel:                                   # C. lecteur de narration : meme glissement sur SA barre (⏮ ⏸ ⏭)
            pg.evaluate("() => localStorage.setItem('manga_serie','claymore')"); pg.reload(); pg.wait_for_timeout(4000)
            i = pg.evaluate("() => CHAPS.findIndex(c => c.dir === 'claymore/ch_1')")
            pg.evaluate("i => document.querySelector('#chapList [data-chap=\"' + i + '\"]').click()", i); pg.wait_for_timeout(3500)
            pg.evaluate("() => document.querySelector('#narrRuns [data-ecoute]').click()"); pg.wait_for_timeout(2500)
            GL = """([dx, cible]) => { const el = document.querySelector(cible), r = el.getBoundingClientRect(), y = r.top + r.height / 2, x0 = r.left + r.width / 2;
              const t = x => new Touch({ identifier: 1, target: el, clientX: x, clientY: y });
              el.dispatchEvent(new TouchEvent('touchstart', { touches: [t(x0)], changedTouches: [t(x0)], bubbles: true }));
              for (let k = 1; k <= 6; k++) el.dispatchEvent(new TouchEvent('touchmove', { touches: [t(x0 + dx * k / 6)], changedTouches: [t(x0 + dx * k / 6)], bubbles: true }));
              el.dispatchEvent(new TouchEvent('touchend', { touches: [], changedTouches: [t(x0 + dx)], bubbles: true })); }"""
            i0 = pg.evaluate("() => LEC.i")
            pg.evaluate(GL, [120, "#lecPlay"]); pg.wait_for_timeout(800)
            check("lecteur : glissement à DROITE sur sa barre = page SUIVANTE", pg.evaluate("() => LEC.i") == i0 + 1, (i0, pg.evaluate("() => LEC.i")))
            pg.evaluate(GL, [-120, "#lecPlay"]); pg.wait_for_timeout(800)
            check("lecteur : glissement à GAUCHE = page PRÉCÉDENTE", pg.evaluate("() => LEC.i") == i0)
            pg.evaluate(GL, [120, "#lecVolG"]); pg.wait_for_timeout(800)
            check("lecteur : un glissement sur le VOLUME ne tourne pas la page", pg.evaluate("() => LEC.i") == i0)
            pg.evaluate("() => $('lecFermer').click()"); pg.wait_for_timeout(500)
        check("RIEN n'est parti (aucun POST)", not posts, posts[:4])
        check("aucune erreur JS", not errs, errs[:3])
        pg.evaluate("() => localStorage.removeItem('manga_serie')")
        c.close()
    b.close()

print("\nVERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
