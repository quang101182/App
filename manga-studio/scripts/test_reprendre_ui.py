# -*- coding: utf-8 -*-
"""Banc v2.62.0 : bouton « ▶ Reprendre » + fenetre « 🕘 Reprendre » (maquette_reprendre_v1, validee 25/09 14h43).
APP REELLE (8190), aux 5 largeurs du HANDOFF : 360, 476 (Fold ferme), 704 (Fold deplie portrait), 933x700 (Fold deplie
paysage), 1280. Tout POST est BLOQUE et compte (un navigateur pilote n'ecrit pas l'historique : 0 attendu).
L'historique est injecte en memoire (BIB.lectures) -- jamais ecrit dans le fichier de Quang.
1. bibliotheque : « ▶ » grise ; toucher court = un message, pas de fenetre ;
2. serie : « ▶24 » (<= 480 px) / « ▶ ch. 24 » ; barre sur UNE ligne, dans l'ecran, fine sur telephone, >= 14 px du bas ;
3. toucher = le chapitre, A SA PAGE ; puis dans ce chapitre « ▶ » = celui d'AVANT, et retour d'un geste (va-et-vient) ;
4. defiler jusqu'a une page la note (en memoire) ;
5. appui long (meme hors manga) = fenetre : la plus recente en haut, largeur selon le format, jamais plus haute que l'ecran ;
   Echap, « ← Fermer » de la barre et le bouton de la fenetre la ferment ; toucher une ligne = y aller ;
6. aucun debordement horizontal ; aucun POST ; aucune erreur JS.
Usage : python test_reprendre_ui.py [port]
"""
import os, sys, time
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = sys.argv[1] if len(sys.argv) > 1 else "8190"
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


DOWN = """([typ]) => { const b = $('nfRep'), r = b.getBoundingClientRect(); window._p = [r.left + r.width / 2, r.top + r.height / 2];
  b.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, pointerType: typ, button: 0, clientX: _p[0], clientY: _p[1] })); }"""
UP = """([typ]) => $('nfRep').dispatchEvent(new PointerEvent('pointerup', { bubbles: true, pointerType: typ, clientX: _p[0], clientY: _p[1] }))"""

# une serie d'au moins 3 chapitres (A = 2e, avec >= 6 pages ; B = 1er) + les autres series en historique plus ancien
FIXTURE = """() => {
  const S = mesSeries().filter(s => s.chaps.length >= 3 && !(BIB.masquees || []).includes(s.slug));
  const s = S.find(x => { const o = x.chaps.slice().sort((a, b) => parseFloat(CHAPS[a].chapter) - parseFloat(CHAPS[b].chapter)); return CHAPS[o[1]].pages >= 6; });
  const o = s.chaps.slice().sort((a, b) => parseFloat(CHAPS[a].chapter) - parseFloat(CHAPS[b].chapter));
  const A = CHAPS[o[1]], B = CHAPS[o[0]], now = Date.now() / 1000;
  BIB.lectures = {};
  BIB.lectures[s.slug] = { d: A.dir, page: 4, t: now - 7200, appareil: 'Fold', prec: { d: B.dir, page: 0 } };
  mesSeries().filter(x => x.chaps.length && x.slug !== s.slug && !(BIB.masquees || []).includes(x.slug)).forEach((x, k) => {
    BIB.lectures[x.slug] = { d: CHAPS[x.chaps[0]].dir, page: k % 3 ? 0 : 7, t: now - 86400 * (k + 1), appareil: k % 2 ? 'PC' : 'Fold' }; });
  return { slug: s.slug, A: A.dir, chA: A.chapter, B: B.dir, chB: B.chapter, n: Object.keys(BIB.lectures).length };
}"""
BARRE = """() => { const n = $('navFlot'), r = n.getBoundingClientRect(), b = [...n.querySelectorAll('.nf-b:not([hidden]), .nf-info')];
  const tops = new Set(b.map(x => Math.round(x.getBoundingClientRect().top)));
  return { h: Math.round(r.height), lignes: tops.size, gauche: Math.round(r.left), droite: Math.round(innerWidth - r.right),
           bas: Math.round(innerHeight - r.bottom), deb: document.documentElement.scrollWidth - document.documentElement.clientWidth,
           premier: n.querySelector('.nf-b, .nf-info').id }; }"""
FEN = """() => { const f = $('repFen'), r = f.getBoundingClientRect(), l = $('repListe');
  return { vis: !f.hidden, w: Math.round(r.width), cx: Math.round(r.left + r.width / 2), top: Math.round(r.top), bas: Math.round(r.bottom),
           lignes: l.querySelectorAll('[data-rep]').length, prem: (l.querySelector('[data-rep]') || {}).dataset?.rep,
           defile: l.scrollHeight > l.clientHeight + 2, debL: l.scrollWidth - l.clientWidth,
           deb: document.documentElement.scrollWidth - document.documentElement.clientWidth,
           texte: (l.querySelector('[data-rep]') || {}).innerText || '' }; }"""

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w, h in ((360, 780), (476, 860), (704, 900), (933, 700), (1280, 900)):
        tel = w <= 480; mob = w < 1000; typ = "touch" if mob else "mouse"
        print("=== %d x %d" % (w, h))
        c = b.new_context(viewport={"width": w, "height": h}, is_mobile=mob, has_touch=mob)
        pg = c.new_page(); errs, posts = [], []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        def route(rt):
            r = rt.request
            if r.method == "POST" and not any(k in r.url for k in ("activite", "costs", "savelog")):
                posts.append(r.url.split("?")[0]); return rt.abort()
            rt.continue_()
        pg.route("**/*", route)
        pg.goto("http://127.0.0.1:%s/manga#k=%s" % (PORT, KEY)); pg.wait_for_timeout(2500)
        pg.evaluate("() => { localStorage.setItem('manga_onglet','tChap'); localStorage.removeItem('manga_serie'); }")
        pg.reload(); pg.wait_for_timeout(4500)
        fx = pg.evaluate(FIXTURE); pg.evaluate("() => nfMaj()")
        rep = lambda: pg.evaluate("() => [$('nfRep').textContent, $('nfRep').classList.contains('off')]")
        fen = lambda: pg.evaluate(FEN)
        def appui(ms):
            pg.evaluate(DOWN, [typ]); pg.wait_for_timeout(ms); pg.evaluate(UP, [typ]); pg.wait_for_timeout(500)
        # 1. bibliotheque
        check("bibliothèque : « ▶ » grisé, sans numéro", rep() == ["▶", True], rep())
        pg.click("#nfRep", force=True); pg.wait_for_timeout(400)
        check("… toucher court : un message, pas de fenêtre", not fen()["vis"] and "appui long" in pg.inner_text("#toast"), pg.inner_text("#toast"))
        # 2. serie
        pg.evaluate("s => ouvrirSerie(s)", fx["slug"]); pg.wait_for_timeout(1200)
        attendu = ("▶" if tel else "▶ ch. ") + fx["chA"]
        check("série : « %s » ambré, actif" % attendu, rep() == [attendu, False], rep())
        br = pg.evaluate(BARRE)
        check("barre : « ▶ » tout à gauche, UNE ligne, dans l'écran, pas de débordement",
              br["premier"] == "nfRep" and br["lignes"] == 1 and br["gauche"] >= 0 and br["droite"] >= 0 and br["deb"] == 0, br)
        if w <= 640:
            check("téléphone : barre fine (<= 36 px), >= 14 px du bas", br["h"] <= 36 and br["bas"] >= 14, br)
        # 3. toucher = le chapitre A, a sa page ; puis va-et-vient avec B
        pg.click("#nfRep"); pg.wait_for_timeout(3500)
        pos = pg.evaluate("() => { const f = document.querySelector('#chapPages figure[data-page=\"4\"]'); return [CHAP_OPEN, f ? Math.round(f.getBoundingClientRect().top) : null]; }")
        check("toucher : chapitre %s ouvert À SA PAGE (p. 5 en haut de l'écran)" % fx["chA"], pos[0] == fx["A"] and pos[1] is not None and -40 <= pos[1] <= 160, pos)
        att_b = ("▶" if tel else "▶ ch. ") + fx["chB"]
        check("dans le chapitre : « ▶ » = celui d'AVANT (%s)" % att_b, rep() == [att_b, False], rep())
        pg.click("#nfRep"); pg.wait_for_timeout(3500)
        att_a = ("▶" if tel else "▶ ch. ") + fx["chA"]
        check("… un geste : retour au ch. %s, et « ▶ » propose le %s (va-et-vient)" % (fx["chB"], fx["chA"]),
              pg.evaluate("() => CHAP_OPEN") == fx["B"] and rep() == [att_a, False], [pg.evaluate("() => CHAP_OPEN"), rep()])
        # 4. defiler : la 1re page de la rangee du haut est notee ; la visionneuse note chaque page ; bibCharger ne l'efface pas
        pg.wait_for_timeout(1600)
        att = pg.evaluate("""() => { const figs = [...document.querySelectorAll('#chapPages figure')], n = Math.min(5, figs.length - 1);
          scrollTo(0, scrollY + figs[n].getBoundingClientRect().top - 10); const t = figs[n].getBoundingClientRect().top;
          return +figs.find(f => Math.abs(f.getBoundingClientRect().top - t) < 4).dataset.page; }""")
        pg.wait_for_timeout(900)
        lu = pg.evaluate("s => (BIB.lectures[s] || {}).page", fx["slug"])
        check("défiler : la 1re page de la rangée du haut est notée (%s)" % att, lu == att, lu)
        pg.evaluate("() => document.querySelector('#chapPages figure[data-page=\"1\"]').click()"); pg.wait_for_timeout(400)
        pg.evaluate("() => lbShow(LB + 1)"); pg.wait_for_timeout(300)
        lu = pg.evaluate("s => (BIB.lectures[s] || {}).page", fx["slug"])
        pg.evaluate("() => lbClose()"); pg.wait_for_timeout(300)
        check("visionneuse : la page regardée est notée (p. 3 → 2)", lu == 2, lu)
        pg.evaluate("() => bibCharger()"); pg.wait_for_timeout(1200)
        lu = pg.evaluate("s => (BIB.lectures[s] || {}).page", fx["slug"])
        check("recharger la bibliothèque du serveur n'efface pas la page notée ici", lu == 2, lu)
        # 5. fenetre
        pg.evaluate("() => { $('btnChapClose').click(); ouvrirSerie(null); }"); pg.wait_for_timeout(800)
        appui(900)
        f = fen()
        check("appui long HORS manga : la fenêtre s'ouvre, %d lignes, la plus récente en haut" % fx["n"],
              f["vis"] and f["lignes"] == fx["n"] and f["prem"] == fx["B"], f)
        check("… ligne : nom, « il y a / à l'instant · sur le … », « ch. N »", "sur le" in f["texte"] and "ch. " + fx["chB"] in f["texte"], f["texte"].replace("\n", " | "))
        if w < 704:
            check("… largeur écran − 20 px", abs(f["w"] - (w - 20)) <= 2, f["w"])
        else:
            check("… centrée, ~460 px", abs(f["w"] - 460) <= 2 and abs(f["cx"] - w / 2) <= 2, [f["w"], f["cx"]])
        check("… tient en hauteur (%s)" % ("défile" if f["defile"] else "sans défiler"), f["top"] >= 0 and f["bas"] <= h, [f["top"], f["bas"], h])
        check("… aucun débordement horizontal (page et liste)", f["deb"] == 0 and f["debL"] <= 0, [f["deb"], f["debL"]])
        check("… la barre dit « ← Fermer »", pg.evaluate("() => $('nfRet').textContent") == "← Fermer" and not pg.evaluate("() => $('nfRet').disabled"))
        pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
        check("Échap ferme", not fen()["vis"])
        appui(900); pg.click("#nfRet"); pg.wait_for_timeout(300)
        check("« ← Fermer » de la barre ferme", not fen()["vis"])
        appui(900); pg.click("#repFermer"); pg.wait_for_timeout(300)
        check("le bouton de la fenêtre ferme", not fen()["vis"])
        appui(900)
        d2 = pg.evaluate("() => document.querySelectorAll('#repListe [data-rep]')[1].dataset.rep")
        pg.evaluate("() => document.querySelectorAll('#repListe [data-rep]')[1].click()"); pg.wait_for_timeout(3500)
        check("toucher une ligne : y aller (%s)" % d2, pg.evaluate("() => CHAP_OPEN") == d2 and not fen()["vis"], pg.evaluate("() => CHAP_OPEN"))
        pg.screenshot(path=os.path.join(os.path.dirname(__file__), "reprendre_%d.png" % w))
        appui(900); pg.screenshot(path=os.path.join(os.path.dirname(__file__), "reprendre_fen_%d.png" % w)); pg.keyboard.press("Escape")
        check("RIEN n'est parti (aucun POST : l'historique de Quang intact)", not posts, posts[:4])
        check("aucune erreur JS", not errs, errs[:3])
        pg.evaluate("() => localStorage.removeItem('manga_serie')")
        c.close()
    b.close()

print("\nVERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
