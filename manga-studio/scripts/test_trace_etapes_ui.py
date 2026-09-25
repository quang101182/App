# -*- coding: utf-8 -*-
"""Banc v2.47.0 : le LECTEUR montre la trace de moderation de CHAQUE etape (narrate 2.12.0 + traduire_chapitre 2.0.0).
APP REELLE, 1280 px puis 360 px, sur une vraie narration ouverte dans le lecteur.
- recit relaye : « ✍ récit par Kimi (refusé par DeepSeek) » ; recit refuse partout : « ⛔ récit refusé » ;
- traduction affichee relayee : « 🌐 traduite par Kimi (refusée par Gemini) » ; refusee : « ⛔ traduction refusée … en VO » ;
- en VO (aucune traduction affichee) : rien sur la traduction ; page sans aucune trace : rien du tout ;
- l'analyse (v2.44.0) et le recit se cumulent sur la meme ligne.
Les traces sont POSEES dans la page du lecteur (aucun fichier touche, aucun appel paye) ; TRADS / TRAD_VUE restaures.
Usage : python test_trace_etapes_ui.py [port] [serie]
"""
import os, sys
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = sys.argv[1] if len(sys.argv) > 1 else "8190"
SERIE = sys.argv[2] if len(sys.argv) > 2 else "claymore"
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


INFO = """(t) => { const p = LEC.n.pages[LEC.i]; const sv = [p.trace, p.trace_recit, TRADS, TRAD_VUE];
  p.trace = t.trace; p.trace_recit = t.recit; if (t.trads !== undefined){ TRADS = t.trads; TRAD_VUE = t.vue; }
  montrerPage(); const txt = $('lecInfo').textContent, lg = document.documentElement.scrollWidth;
  [p.trace, p.trace_recit, TRADS, TRAD_VUE] = sv; montrerPage(); return [txt, lg, innerWidth]; }"""

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w, h in ((1280, 900), (360, 780)):
        print("=== %d px" % w)
        c = b.new_context(viewport={"width": w, "height": h}, has_touch=(w < 400), is_mobile=(w < 400))
        pg = c.new_page(); errs, ecrit = [], []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("request", lambda r: ecrit.append(r.url) if r.method == "POST" and "/manga/" in r.url and not any(k in r.url for k in ("activite", "costs")) else None)
        pg.goto("http://127.0.0.1:%s/manga#k=%s" % (PORT, KEY)); pg.wait_for_timeout(2500)
        pg.evaluate("s => { localStorage.setItem('manga_onglet','tChap'); localStorage.setItem('manga_serie', s); }", SERIE)
        pg.reload(); pg.wait_for_timeout(3500)
        check("version = VERSION du code", pg.inner_text("#verBadge").strip() == "v" + pg.evaluate("() => VERSION"))
        i_ = pg.evaluate("s => CHAPS.findIndex(c => c.dir === s + '/ch_1')", SERIE)      # seul chapitre narre de Claymore
        pg.click('#chapList [data-chap="%d"]' % i_); pg.wait_for_selector("#chapDetail:not([hidden])", timeout=15000); pg.wait_for_timeout(2500)
        pg.evaluate("() => document.querySelector('#narrRuns [data-ecoute]').click()"); pg.wait_for_timeout(2500)
        check("lecteur ouvert sur une vraie narration", pg.evaluate("() => !!(LEC && LEC.n && LEC.n.pages.length)"))
        num = pg.evaluate("() => LEC.n.pages[LEC.i].page")
        R = {"lu_par": "kimi", "refuse_par": [{"moteur": "deepseek"}], "comment": "relais automatique"}
        t, lg, iw = pg.evaluate(INFO, {"trace": None, "recit": R})
        check("récit relayé : « ✍ récit par Kimi (refusé par DeepSeek) »", "✍ récit par Kimi (refusé par DeepSeek)" in t, t)
        t, _, _ = pg.evaluate(INFO, {"trace": None, "recit": {"lu_par": None, "refuse_par": [{"moteur": "deepseek"}, {"moteur": "kimi"}, {"moteur": "gemini"}]}})
        check("récit refusé partout : « ⛔ récit refusé » + les trois moteurs", "⛔ récit refusé par DeepSeek, Kimi, Gemini" in t, t)
        t, _, _ = pg.evaluate(INFO, {"trace": {"lu_par": "kimi", "refuse_par": [{"moteur": "gemini"}], "comment": "relais automatique"}, "recit": R})
        check("analyse + récit sur la même ligne", "🔁 lue par Kimi (refusée par Gemini)" in t and "✍ récit par Kimi" in t, t)
        TR = [{"langue": "zz", "etat": "fini", "pages": {}, "stats": {"relais": [{"page": num, "de": "gemini", "vers": "kimi"}]}}]
        t, lg, iw = pg.evaluate(INFO, {"trace": None, "recit": None, "trads": TR, "vue": "zz"})
        check("traduction affichée relayée : « 🌐 traduite par Kimi (refusée par Gemini) »", "🌐 traduite par Kimi (refusée par Gemini)" in t, t)
        check("ligne d'info : aucun débordement horizontal", lg <= iw, (lg, iw))
        TM = [{"langue": "zz", "etat": "fini", "pages": {}, "stats": {"moderation": [{"page": num, "moteur": "pixtral"}]}}]
        t, _, _ = pg.evaluate(INFO, {"trace": None, "recit": None, "trads": TM, "vue": "zz"})
        check("traduction refusée : « ⛔ traduction refusée (Pixtral) — en VO »", "⛔ traduction refusée (Pixtral) — en VO" in t, t)
        t, _, _ = pg.evaluate(INFO, {"trace": None, "recit": None, "trads": TR, "vue": ""})
        check("en VO : rien sur la traduction", "traduite" not in t and "traduction" not in t, t)
        TA = [{"langue": "zz", "etat": "fini", "pages": {}, "stats": {"relais": [{"page": num + 1000, "de": "gemini", "vers": "kimi"}]}}]
        t, _, _ = pg.evaluate(INFO, {"trace": None, "recit": None, "trads": TA, "vue": "zz"})
        check("page sans aucune trace : rien d'ajouté", "·" not in t.split(")")[-1] and "🔁" not in t and "✍" not in t and "🌐" not in t, t)
        pg.evaluate("() => $('lecFermer').click()"); pg.wait_for_timeout(300)
        check("aucune erreur JS", not errs, errs[:3])
        check("rien écrit (lecture seule)", not ecrit, ecrit[:3])
        c.close()
    b.close()

print("\nVERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
