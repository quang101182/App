# -*- coding: utf-8 -*-
"""Banc v2.60.0 : CHAPITRE COMPACT (maquette_chapitre_compact_v1, validee par Quang 25/09 13h41). APP REELLE (8190), Claymore
ch.1 (narre, video faite), 1280 px puis 360 px. Tout POST bloque ; les boutons d'origine sont ESPIONNES (rien ne part).
1. replie par defaut : 4 lignes, ordre narration → traduction → musique → video (v2.78.0), hauteur < 300 px (≈ 850 avant) ;
2. chaque ligne : etat en une phrase + action ; telephone : etat sur 2 lignes au plus ;
3. toucher une ligne la deplie (les reglages d'avant sont la) ; en deplier une autre replie la premiere ; memorise ;
4. les actions de ligne cliquent le bouton d'ORIGINE (Narrer, Traduire) ; ← Fermer de la barre replie le bloc.
Usage : python test_chapitre_compact_ui.py [port]
"""
import os, sys
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = sys.argv[1] if len(sys.argv) > 1 else "8190"
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


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
        pg.evaluate("() => { localStorage.setItem('manga_onglet','tChap'); localStorage.setItem('manga_serie','claymore'); localStorage.removeItem('manga_chap_bloc'); }")
        pg.reload(); pg.wait_for_timeout(4000)
        i = pg.evaluate("() => CHAPS.findIndex(c => c.dir === 'claymore/ch_1')")
        pg.evaluate("i => document.querySelector('#chapList [data-chap=\"' + i + '\"]').click()", i); pg.wait_for_timeout(4000)
        m = pg.evaluate("""() => ({ ordre: [...document.querySelectorAll('#chapDetail .cl-tete')].map(h => h.dataset.cl),
            ouverts: [...document.querySelectorAll('#chapDetail .cl-box.cl-ouv')].length,
            haut: Math.round(document.querySelector('#chapVid').getBoundingClientRect().bottom - document.querySelector('#chapDetail .bloc-narr').getBoundingClientRect().top),
            reglagesCaches: !$('narrEngine').checkVisibility(), etats: [...document.querySelectorAll('#chapDetail .cl-etat')].map(e => e.textContent),
            lignes: [...document.querySelectorAll('#chapDetail .cl-etat')].map(e => Math.round(e.getBoundingClientRect().height / parseFloat(getComputedStyle(e).lineHeight))) })""")
        check("replié par défaut : 4 lignes, dans l'ordre du travail", m["ordre"] == ["narr", "trad", "mus", "vid"] and m["ouverts"] == 0, m["ordre"])
        check("hauteur des 4 blocs < 300 px (≈ 850 avant)", m["haut"] < 300, m["haut"])
        check("les réglages sont repliés (moteur de lecture caché)", m["reglagesCaches"])
        check("chaque ligne a un état", all(e.strip() for e in m["etats"]), m["etats"])
        check("narration : état « narration prête »", "narration" in m["etats"][0] and "prête" in m["etats"][0], m["etats"][0])
        if tel:
            check("téléphone : état sur 2 lignes au plus", max(m["lignes"]) <= 2, m["lignes"])
        check("aucun débordement horizontal", pg.evaluate("() => document.documentElement.scrollWidth <= innerWidth"))
        # 3. deplier / une seule / memorise
        pg.evaluate("() => document.querySelector('.cl-tete[data-cl=\"narr\"] .cl-etat').click()"); pg.wait_for_timeout(500)
        check("toucher la ligne Narration la déplie : les réglages d'avant sont là", pg.evaluate("() => $('narrEngine').checkVisibility() && $('btnNarrer').checkVisibility()"))
        pg.evaluate("() => document.querySelector('.cl-tete[data-cl=\"trad\"] .cl-etat').click()"); pg.wait_for_timeout(500)
        o = pg.evaluate("() => [...document.querySelectorAll('#chapDetail .cl-box.cl-ouv')].map(b => b.querySelector('.cl-tete').dataset.cl)")
        check("déplier Traduction replie Narration (une seule ouverte)", o == ["trad"], o)
        pg.reload(); pg.wait_for_timeout(4000)
        i = pg.evaluate("() => CHAPS.findIndex(c => c.dir === 'claymore/ch_1')")
        pg.evaluate("i => document.querySelector('#chapList [data-chap=\"' + i + '\"]').click()", i); pg.wait_for_timeout(3500)
        o = pg.evaluate("() => [...document.querySelectorAll('#chapDetail .cl-box.cl-ouv')].map(b => b.querySelector('.cl-tete').dataset.cl)")
        check("mémorisé sur l'appareil (Traduction toujours dépliée)", o == ["trad"], o)
        # 4. ← Fermer
        pg.evaluate("() => scrollTo(0, document.documentElement.scrollHeight)"); pg.wait_for_timeout(500)
        check("barre : « ← Fermer » tant qu'un bloc est déplié", pg.inner_text("#nfRet").strip() == "← Fermer", pg.inner_text("#nfRet"))
        pg.click("#nfRet"); pg.wait_for_timeout(500)
        check("« ← Fermer » replie le bloc (le chapitre reste ouvert)", pg.evaluate("() => !document.querySelector('#chapDetail .cl-box.cl-ouv') && CHAP_OPEN === 'claymore/ch_1'"))
        # 5. actions de ligne = boutons d'ORIGINE (espionnes)
        pg.evaluate("() => { window._espion = []; ['btnNarrer', 'btnTraduire'].forEach(id => { $(id).onclick = () => _espion.push(id); $(id).disabled = false; }); clMaj(); }")
        pg.wait_for_timeout(300)
        pg.evaluate("() => document.querySelector('.cl-tete[data-cl=\"narr\"] [data-cl-act=\"btnNarrer\"]').click()")
        pg.evaluate("() => document.querySelector('.cl-tete[data-cl=\"trad\"] [data-cl-act=\"btnTraduire\"]').click()")
        esp = pg.evaluate("() => _espion")
        check("« Narrer » / « Traduire » de la ligne = boutons d'origine (mêmes confirmations)", esp == ["btnNarrer", "btnTraduire"], esp)
        check("… sans déplier la ligne", not pg.evaluate("() => !!document.querySelector('#chapDetail .cl-box.cl-ouv')"))
        check("RIEN n'est parti (aucun POST)", not posts, posts[:4])
        check("aucune erreur JS", not errs, errs[:3])
        pg.evaluate("() => { localStorage.removeItem('manga_serie'); localStorage.removeItem('manga_chap_bloc'); }")
        c.close()
    b.close()

print("\nVERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
