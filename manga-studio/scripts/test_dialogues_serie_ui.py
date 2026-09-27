# -*- coding: utf-8 -*-
"""Banc D10 (v2.82.0, maquette_dialogues_serie_v1 validee 27/09 02h28) : bouton 🎭 Dialogues de la SERIE et son panneau, sur
l'APP REELLE (8190, One Punch-Man : ch.5 prets + video, ch.302 a mettre en voix + FR partiel). Page = le HTML donne
(interception) ; les lancements payants (voix, lot) sont INTERCEPTES : 0 appel paye.
Usage : python test_dialogues_serie_ui.py [html]        (html = page v2.81.8 -> doit sortir ROUGE)"""
import json, os, sys
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(HERE, "..", "manga_studio.html")
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PAGE = open(HTML, encoding="utf-8").read()
OK, KO = [], []


def check(n, c, d=""):
    (OK if c else KO).append(n); print(("  [OK] " if c else "  [KO] ") + n + (" -- " + str(d)[:170] if d else ""), flush=True)


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True, args=["--mute-audio"])
    for w, h in ((1280, 900), (933, 700), (704, 900), (476, 900), (360, 780)):
        print("=== %d px" % w)
        ctx = b.new_context(viewport={"width": w, "height": h}, is_mobile=w < 500, has_touch=w < 500)
        pg = ctx.new_page(); errs = []; lances = []; boites = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("dialog", lambda d: (boites.append(d.message), d.dismiss() if len(boites) % 2 else d.accept()))

        def route(rt):
            u = rt.request.url.split("#")[0].split("?")[0]
            if rt.request.method == "GET" and u.rstrip("/").endswith("/manga"):
                return rt.fulfill(status=200, content_type="text/html; charset=utf-8", body=PAGE)
            if rt.request.method == "POST" and (u.endswith("/manga/dialogues_lancer") or u.endswith("/manga/dialogues_lot")):
                lances.append((u.rsplit("/", 1)[1], json.loads(rt.request.post_data or "{}")))
                return rt.fulfill(status=200, content_type="application/json", body='{"ok": true}')
            return rt.continue_()
        pg.route("**/*", route)
        pg.goto("http://127.0.0.1:8190/manga#k=" + KEY); pg.wait_for_timeout(2500)
        pg.evaluate("() => { localStorage.setItem('manga_serie','one-punch-man'); localStorage.setItem('manga_onglet','tChap'); }"); pg.reload()
        pg.wait_for_function("() => typeof RESUME !== 'undefined' && RESUME && RESUME.chapitres", timeout=30000); pg.wait_for_timeout(1500)
        vis = pg.evaluate("() => { const b = document.getElementById('btnDlgSerie'); return b ? b.getBoundingClientRect().width > 0 : false }")
        check("bouton 🎭 Dialogues visible dans la fiche de la série", vis)
        if not vis:
            ctx.close(); continue
        check("compteur = 2 chapitres avec dialogues", pg.evaluate("() => !$('dlgsNb').hidden && $('dlgsNb').textContent") == "2", pg.evaluate("() => $('dlgsNb').textContent"))
        if w <= 520:
            check("téléphone : « Site » passe dans ⋯ (bouton masqué, entrée de menu présente)",
                  pg.evaluate("() => getComputedStyle($('btnSerieSite')).display === 'none' && !!$('btnSiteMenu')"))
        check("badge 🎭 sur le ch. 5 dans la liste", "🎭" in pg.evaluate("() => { const r = RESUME.chapitres['one-punch-man/ch_5']; return r && r.dlg ? '🎭' : '' }"))
        pg.click("#btnDlgSerie"); pg.wait_for_timeout(3500)
        check("panneau ouvert, séparé du panneau Vidéos", pg.evaluate("() => !$('dlgsBox').hidden && $('vidBox').hidden"))
        lignes = pg.evaluate("() => [...document.querySelectorAll('#dlgsListe .dlgs-l')].map(x => x.innerText.replace(/\\s+/g, ' '))")
        check("filtre « Avec dialogues » par défaut : 2 lignes", len(lignes) == 2, lignes)
        l5 = next((x for x in lignes if "Chapitre 5 " in x + " "), "")
        check("ch. 5 : prêts · 12 répliques · p. 13-15 · vidéo à jour · ▶ Lire / ▶ Vidéo / ⬇ / ✏",
              all(t in l5 for t in ("prêts", "12 répliques", "p. 13-15", "vidéo à jour", "Lire", "Vidéo", "⬇", "✏")), l5)
        l302 = next((x for x in lignes if "Chapitre 302" in x), "")
        check("ch. 302 : à mettre en voix · p. 2-3 · crédits · FR partiel · 🔊 Générer", all(t in l302 for t in ("à mettre en voix", "p. 2-3", "crédits", "FR partiel", "Générer")), l302)
        res = pg.evaluate("() => $('dlgsResume').innerText")
        check("résumé : 1 prêt · 1 à mettre en voix · non commencés · crédits restants", "1 chapitre prêt" in res and "1 à mettre en voix" in res and "non commencé" in res and "crédits" in res, res)
        check("distribution du manga + « ✏ Régler les voix »", "Distribution du manga" in pg.evaluate("() => $('dlgsDist').innerText") and pg.evaluate("() => !!$('dlgsDist').querySelector('[data-dlgs=corr]')"))
        pg.click("#dlgsFTous"); pg.wait_for_timeout(400)
        n_tous = pg.evaluate("() => document.querySelectorAll('#dlgsListe .dlgs-l').length"); n_ser = pg.evaluate("() => CHAPS.filter(c => c.dir.startsWith('one-punch-man/')).length")
        check("« Tous » : un chapitre par ligne (%d)" % n_ser, n_tous == n_ser, n_tous)
        pg.click("#dlgsFAvec"); pg.wait_for_timeout(300)
        deb = pg.evaluate("() => document.documentElement.scrollWidth > document.documentElement.clientWidth || [...document.querySelectorAll('#dlgsBox *')].some(e => e.scrollWidth > e.clientWidth + 1 && getComputedStyle(e).overflowX !== 'visible')")
        check("aucun débordement (page ni conteneur)", not deb)
        pg.screenshot(path=os.path.join(os.environ.get("TEMP", "."), "dlgs_%d.png" % w), full_page=False)
        # actions
        pg.evaluate("() => document.querySelector('#dlgsListe [data-dlgs=gen]').click()"); pg.wait_for_timeout(600)
        check("🔊 Générer : confirmation avec les crédits ; refusée = rien lancé", boites and "crédits" in boites[-1] and not lances, (boites[-1:], lances))
        pg.evaluate("() => document.querySelector('#dlgsListe [data-dlgs=gen]').click()"); pg.wait_for_timeout(600)
        check("acceptée = voix lancées pour le ch. 302", lances and lances[-1] == ("dialogues_lancer", {"d": "one-punch-man/ch_302", "action": "voix"}), lances)
        pg.fill("#dlgsDe", "1"); pg.fill("#dlgsA", "10")
        pg.click("#dlgsPrep"); pg.wait_for_timeout(500); pg.click("#dlgsPrep"); pg.wait_for_timeout(600)
        check("plusieurs chapitres : confirmation puis lot (1 → 10, préparer)", lances[-1] == ("dialogues_lot", {"serie": "one-punch-man", "de": 1, "a": 10, "action": "preparer"}), lances[-1:])
        pg.evaluate("() => document.querySelector('#dlgsListe [data-dlgs=video]').click()"); pg.wait_for_timeout(1500)
        check("▶ Vidéo : la vidéo des dialogues du ch. 5", pg.evaluate("() => !$('vidLecteur').hidden && decodeURIComponent($('vidLecVideo').src).includes('ch_5/dialogues/video/dialogues')"))
        pg.evaluate("() => $('vidLecFermer').click()"); pg.wait_for_timeout(300)
        pg.evaluate("() => document.querySelector('#dlgsListe [data-dlgs=lire]').click()"); pg.wait_for_timeout(2500)
        check("▶ Lire : le lecteur des dialogues du ch. 5", pg.evaluate("() => !dlgLec.hidden && DLL.d === 'one-punch-man/ch_5'"))
        pg.evaluate("() => $('dllFermer').click()"); pg.wait_for_timeout(300)
        pg.evaluate("() => document.querySelector('#dlgsListe .dlgs-l [data-dlgs=corr]').click()"); pg.wait_for_timeout(4500)
        check("✏ : le chapitre s'ouvre et son écran de correction", pg.evaluate("() => !$('dlgPrep').hidden && DLG.d === 'one-punch-man/ch_5'"))
        pg.evaluate("() => $('dlgpRet').click()"); pg.wait_for_timeout(300)
        check("0 erreur JS", not errs, errs)
        ctx.close()
print("VERDICT : %d OK / %d KO" % (len(OK), len(KO)))
