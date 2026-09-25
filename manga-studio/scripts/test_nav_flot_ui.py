# -*- coding: utf-8 -*-
"""Banc v2.53.0 -> v2.54.0 (toujours affichee, boutons grises) : NAVIGATION FLOTTANTE (maquette_navigation_v2, A + glissement LIMITE a la barre, valides par Quang 25/09).
APP REELLE (8190), 1280 px puis 360 px (telephone, tactile). Lecture seule : aucune ecriture (POST bloques sauf lectures d'etat).
1. en haut : invisible ; descendu : visible ;
2. PAS DE ZONE CONDAMNEE : tout en bas, le dernier element de la page s'arrete AU-DESSUS de la barre ;
3. telephone : barre FINE (<= 36 px, « la hauteur d'une barre de notification ») et au moins 14 px au-dessus du bas
   (zone des gestes d'Android) ; PC : taille standard ;
4. contenu selon l'endroit : serie (← · ↻ · ↑, sans ‹ ›), chapitre (← · ‹ · ↻ · › · ↑) ;
5. boutons : ↑ remonte, › ouvre le chapitre suivant, ← revient a la serie, ↻ garde la position ;
6. glissement SUR LA BARRE (telephone), dans le SENS DES BOUTONS : a droite = suivant, a gauche = precedent ; petit geste = rien ;
   a gauche en serie = retour ;
7. le lecteur plein ecran la cache.
Usage : python test_nav_flot_ui.py [port]
"""
import os, sys
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = sys.argv[1] if len(sys.argv) > 1 else "8190"
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


GLISSE = """([dx]) => { const n = $('navFlot'), r = n.getBoundingClientRect(), y = r.top + r.height / 2, x0 = r.left + r.width / 2;
  const t = x => new Touch({ identifier: 1, target: n, clientX: x, clientY: y });
  n.dispatchEvent(new TouchEvent('touchstart', { touches: [t(x0)], changedTouches: [t(x0)], bubbles: true }));
  for (let k = 1; k <= 6; k++) n.dispatchEvent(new TouchEvent('touchmove', { touches: [t(x0 + dx * k / 6)], changedTouches: [t(x0 + dx * k / 6)], bubbles: true }));
  n.dispatchEvent(new TouchEvent('touchend', { touches: [], changedTouches: [t(x0 + dx)], bubbles: true })); }"""

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w, h in ((1280, 900), (360, 780)):
        tel = w < 400
        print("=== %d px" % w)
        c = b.new_context(viewport={"width": w, "height": h}, is_mobile=tel, has_touch=tel)
        pg = c.new_page(); errs, ecrit = [], []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        def route(rt):
            r = rt.request
            if r.method == "POST" and not any(k in r.url for k in ("activite", "costs", "fetch_status", "savelog")):
                ecrit.append(r.url); return rt.abort()
            rt.continue_()
        pg.route("**/*", route)
        pg.goto("http://127.0.0.1:%s/manga#k=%s" % (PORT, KEY)); pg.wait_for_timeout(2500)
        pg.evaluate("() => { localStorage.setItem('manga_onglet','tChap'); localStorage.setItem('manga_serie','one-punch-man'); }")
        pg.reload(); pg.wait_for_timeout(4500)
        vis = lambda: pg.evaluate("() => !$('navFlot').hidden")
        pg.evaluate("() => scrollTo(0, 0)"); pg.wait_for_timeout(400)
        check("série, en haut : barre DÉJÀ affichée (v2.54.0 : toujours là)", vis())
        etat = pg.evaluate("() => [...$('navFlot').querySelectorAll('.nf-b')].map(b => b.id + (b.hidden ? ':cache' : b.disabled ? ':grise' : ':actif'))")
        check("série, en haut : 5 boutons, ‹ › et ↑ GRISÉS (jamais masqués)", etat == ["nfRet:actif", "nfPrev:grise", "nfRefr:actif", "nfSuiv:grise", "nfHaut:grise"], etat)
        pg.evaluate("() => scrollTo(0, document.documentElement.scrollHeight)"); pg.wait_for_timeout(500)
        check("série, descendu : barre visible", vis())
        etat = pg.evaluate("() => [...$('navFlot').querySelectorAll('.nf-b')].map(b => b.id + (b.hidden ? ':cache' : b.disabled ? ':grise' : ':actif'))")
        check("série, descendu : ← ↻ ↑ actifs, ‹ › grisés", etat == ["nfRet:actif", "nfPrev:grise", "nfRefr:actif", "nfSuiv:grise", "nfHaut:actif"], etat)
        info = pg.evaluate("() => [$('nfInfoTxt').textContent, getComputedStyle($('nfInfo')).backgroundColor, $('nfInfo').getBoundingClientRect().left < $('nfRet').getBoundingClientRect().left]")
        check("bulle VERTE « où je suis », à gauche des boutons : le nom du manga", info[0] == "One Punch-Man" and info[1] == "rgb(31, 91, 58)" and info[2], info)
        coupes = pg.evaluate("() => [...$('navFlot').querySelectorAll('.nf-b')].filter(b => b.scrollWidth > b.clientWidth + 1).map(b => b.textContent)")
        check("aucun libellé coupé (« ← Séries » entier)", not coupes and pg.inner_text("#nfRet").strip() == "← Séries", (coupes, pg.inner_text("#nfRet")))
        m = pg.evaluate("""() => { const n = $('navFlot').getBoundingClientRect();
            const der = [...document.querySelectorAll('#chapList [data-chap]')].pop().getBoundingClientRect();
            return { barreHaut: Math.round(n.top), barreBas: Math.round(n.bottom), h: Math.round(n.height), finContenu: Math.round(der.bottom), vh: innerHeight }; }""")
        check("PAS DE ZONE CONDAMNÉE (série) : le dernier chapitre finit au-dessus de la barre", m["finContenu"] <= m["barreHaut"], m)
        if tel:
            check("téléphone : barre FINE (≤ 36 px)", m["h"] <= 36, m["h"])
            check("téléphone : ≥ 14 px au-dessus du bas (zone des gestes)", m["vh"] - m["barreBas"] >= 14, m["vh"] - m["barreBas"])
        else:
            check("PC : taille standard (≥ 44 px)", m["h"] >= 44, m["h"])
        # ↻ garde la position
        y0 = pg.evaluate("() => scrollY"); pg.click("#nfRefr"); pg.wait_for_timeout(2500)
        check("↻ (série) : rafraîchit et reste à la même place", abs(pg.evaluate("() => scrollY") - y0) < 40, (y0, pg.evaluate("() => scrollY")))
        # un chapitre au milieu (voisins des deux cotes)
        i = pg.evaluate("() => CHAPS.findIndex(c => c.dir === 'one-punch-man/ch_301')")
        pg.evaluate("i => document.querySelector('#chapList [data-chap=\"' + i + '\"]').click()", i); pg.wait_for_timeout(3000)
        pg.evaluate("() => scrollTo(0, document.documentElement.scrollHeight)"); pg.wait_for_timeout(700)
        btns = pg.evaluate("() => [...$('navFlot').querySelectorAll('.nf-b')].filter(b => !b.hidden).map(b => b.id + ':' + b.textContent)")
        coupes = pg.evaluate("() => [...$('navFlot').querySelectorAll('.nf-b')].filter(b => b.scrollWidth > b.clientWidth + 1).map(b => b.textContent)")
        check("chapitre : aucun libellé coupé", not coupes, coupes)
        attendu = "ch. 301" if tel else "One Punch-Man · ch. 301"
        check("bulle en chapitre : « %s »" % attendu, pg.inner_text("#nfInfoTxt").strip() == attendu, pg.inner_text("#nfInfoTxt"))
        check("chapitre : ← · ‹ · ↻ · › · ↑ avec les numéros voisins", [x.split(":")[0] for x in btns] == ["nfRet", "nfPrev", "nfRefr", "nfSuiv", "nfHaut"]
              and "300" in btns[1] and "302" in btns[3], btns)
        m = pg.evaluate("""() => { const n = $('navFlot').getBoundingClientRect(); const der = [...document.querySelectorAll('#chapDetail figure, #chapDetail .narr-box')].pop();
            const r = [...document.querySelectorAll('main > *')].filter(e => e.offsetParent).map(e => e.getBoundingClientRect().bottom);
            return { barreHaut: Math.round(n.top), finContenu: Math.round(Math.max(...r)), docFin: Math.round(document.documentElement.scrollHeight - scrollY) }; }""")
        check("PAS DE ZONE CONDAMNÉE (chapitre) : la fin du contenu est au-dessus de la barre", m["finContenu"] <= m["barreHaut"], m)
        check("aucun débordement horizontal", pg.evaluate("() => document.documentElement.scrollWidth <= innerWidth"))
        pg.click("#nfHaut"); pg.wait_for_timeout(1200)
        check("↑ : remonte en haut", pg.evaluate("() => scrollY") < 200, pg.evaluate("() => scrollY"))
        pg.evaluate("() => scrollTo(0, document.documentElement.scrollHeight)"); pg.wait_for_timeout(500)
        pg.click("#nfSuiv"); pg.wait_for_timeout(3000)
        check("› : chapitre suivant (302)", pg.evaluate("() => CHAP_OPEN") == "one-punch-man/ch_302", pg.evaluate("() => CHAP_OPEN"))
        if tel:
            pg.evaluate("() => scrollTo(0, document.documentElement.scrollHeight)"); pg.wait_for_timeout(600)
            pg.evaluate(GLISSE, [25]); pg.wait_for_timeout(1500)
            check("glissement COURT sur la barre (25 px) : rien", pg.evaluate("() => CHAP_OPEN") == "one-punch-man/ch_302")
            pg.evaluate(GLISSE, [140]); pg.wait_for_timeout(3000)
            check("glissement à DROITE sur la barre : chapitre SUIVANT (303) — le sens du bouton ›", pg.evaluate("() => CHAP_OPEN") == "one-punch-man/ch_303", pg.evaluate("() => CHAP_OPEN"))
            pg.evaluate("() => scrollTo(0, document.documentElement.scrollHeight)"); pg.wait_for_timeout(600)
            pg.evaluate(GLISSE, [-140]); pg.wait_for_timeout(3000)
            check("glissement à GAUCHE sur la barre : chapitre PRÉCÉDENT (302) — le sens du bouton ‹", pg.evaluate("() => CHAP_OPEN") == "one-punch-man/ch_302", pg.evaluate("() => CHAP_OPEN"))
        pg.evaluate("() => scrollTo(0, document.documentElement.scrollHeight)"); pg.wait_for_timeout(500)
        pg.click("#nfRet"); pg.wait_for_timeout(1500)
        check("← (chapitre) : retour à la série", pg.evaluate("() => !CHAP_OPEN && LIB_SERIE === 'one-punch-man'"))
        if tel:
            pg.evaluate("() => scrollTo(0, document.documentElement.scrollHeight)"); pg.wait_for_timeout(600)
            pg.evaluate(GLISSE, [-140]); pg.wait_for_timeout(1500)
            check("glissement à GAUCHE en série : retour à toutes les séries (le sens de « ← Séries »)", pg.evaluate("() => !LIB_SERIE"))
        if tel:                                  # un titre trop long DEFILE (aller-retour), la barre reste dans l'ecran
            pg.evaluate("() => { localStorage.setItem('manga_serie','solo-levelng-ragnarok'); }"); pg.reload(); pg.wait_for_timeout(4000)
            d = pg.evaluate("() => [$('nfInfo').classList.contains('defile'), $('nfInfoTxt').scrollWidth > $('nfInfo').clientWidth - 20, Math.round($('navFlot').getBoundingClientRect().right) <= innerWidth]")
            check("titre long : il défile, et la barre reste dans l'écran", all(d), d)
        # lecteur : la barre se retire
        pg.evaluate("() => { localStorage.setItem('manga_serie','claymore'); }"); pg.reload(); pg.wait_for_timeout(4000)
        i = pg.evaluate("() => CHAPS.findIndex(c => c.dir === 'claymore/ch_1')")
        pg.evaluate("i => document.querySelector('#chapList [data-chap=\"' + i + '\"]').click()", i); pg.wait_for_timeout(3000)
        pg.evaluate("() => scrollTo(0, document.documentElement.scrollHeight)"); pg.wait_for_timeout(500)
        pg.evaluate("() => document.querySelector('#narrRuns [data-ecoute]').click()"); pg.wait_for_timeout(2000)
        check("lecteur ouvert : barre cachée (il recouvre l'écran)", not vis())
        pg.evaluate("() => $('lecFermer').click()"); pg.wait_for_timeout(1200)
        check("aucune erreur JS", not errs, errs[:3])
        check("aucune écriture", not ecrit, ecrit[:3])
        pg.evaluate("() => localStorage.removeItem('manga_serie')")
        c.close()
    # v2.59.0 (Quang : Fold 8 DÉPLIÉ → « les boutons sur deux lignes ») : fermé 476, déplié portrait 704, paysage 933
    for w, h in ((476, 900), (704, 900), (933, 700)):
        c = b.new_context(viewport={"width": w, "height": h}, is_mobile=True, has_touch=True); pg = c.new_page()
        pg.route("**/*", lambda r: r.abort() if r.request.method == "POST" else r.continue_())
        pg.goto("http://127.0.0.1:%s/manga#k=%s" % (PORT, KEY)); pg.wait_for_timeout(2500)
        pg.evaluate("() => { localStorage.setItem('manga_onglet','tChap'); localStorage.setItem('manga_serie','one-punch-man'); }")
        pg.reload(); pg.wait_for_timeout(4000)
        i = pg.evaluate("() => CHAPS.findIndex(c => c.dir === 'one-punch-man/ch_301')")
        pg.evaluate("i => document.querySelector('#chapList [data-chap=\"' + i + '\"]').click()", i); pg.wait_for_timeout(3000)
        r = pg.evaluate("() => { const bs = [...$('navFlot').children].filter(e => !e.hidden && e.id !== 'nfIndic'); const n = $('navFlot').getBoundingClientRect();"
                        " return [new Set(bs.map(e => Math.round(e.getBoundingClientRect().top))).size, Math.round(n.left) >= 0 && Math.round(n.right) <= innerWidth]; }")
        check("Fold %d px : barre sur UNE ligne, dans l'écran" % w, r == [1, True], r)
        pg.evaluate("() => localStorage.removeItem('manga_serie')"); c.close()
    b.close()

print("\nVERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
