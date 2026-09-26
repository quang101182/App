# -*- coding: utf-8 -*-
"""Banc v2.80.0. APP REELLE (8190), One Punch-Man, 1280 px puis 360 px. Tout POST bloque (historique de lecture intact).
(Quang 26/09 21h21 : « comme si je lisais un livre ») la visionneuse des PAGES D'UN CHAPITRE ne reboucle plus :
A. barre = « ch. N · p. k/M » (plus de « k/M · p. k » en double)
B. apres la derniere page -> p.1 du chapitre SUIVANT (et le chapitre derriere suit) ; avant la p.1 -> DERNIERE page du precedent
C. par › , par ‹ , par le glissement de la barre (360 px) et par un double clic rapide (un seul passage)
D. bouts de la serie : ni boucle ni saut (message) ; un trou de numeros est dit dans le message
E. les autres listes (galerie...) gardent leur boucle
Usage : python test_visionneuse_livre_ui.py [port] [--ancien]   (--ancien = sert le .bak v2.79.3 : doit etre ROUGE)
"""
import os, sys
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
PORT = ARGS[0] if ARGS else "8190"
ANCIEN = "--ancien" in sys.argv
BAK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "manga_studio.html.bak-20260926-livre")
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


GLISSE = """([dx]) => { const r = $('lbName').getBoundingClientRect(), y = r.top + r.height / 2, x0 = r.left + r.width / 2;
  const t = x => new Touch({ identifier: 1, target: $('lbName'), clientX: x, clientY: y });
  $('lbName').dispatchEvent(new TouchEvent('touchstart', { touches: [t(x0)], changedTouches: [t(x0)], bubbles: true }));
  for (let k = 1; k <= 6; k++) $('lbName').dispatchEvent(new TouchEvent('touchmove', { touches: [t(x0 + dx * k / 6)], changedTouches: [t(x0 + dx * k / 6)], bubbles: true }));
  $('lbName').dispatchEvent(new TouchEvent('touchend', { touches: [], changedTouches: [t(x0 + dx)], bubbles: true })); }"""
ETAT = """() => ({ nom: $('lbName').textContent, lb: LB, n: LB_LISTE.length, ouvert: !$('lightbox').hidden,
  chap: CHAP_OPEN, titre: $('chapTitle').textContent, toast: (document.querySelector('#toast') || {}).textContent || '' })"""

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w, h in ((1280, 900), (360, 780)):
        tel = w < 400
        print("=== %d px%s" % (w, " (ANCIEN .bak)" if ANCIEN else ""))
        c = b.new_context(viewport={"width": w, "height": h}, is_mobile=tel, has_touch=tel)
        pg = c.new_page(); errs, posts = [], []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        def route(rt):
            r = rt.request
            if r.method == "POST" and not any(k in r.url for k in ("activite", "costs", "savelog")):
                posts.append(r.url.split("?")[0]); return rt.abort()
            if ANCIEN and r.method == "GET" and r.url.split("#")[0].split("?")[0].rstrip("/").endswith("/manga"):
                return rt.fulfill(status=200, content_type="text/html; charset=utf-8", body=open(BAK, encoding="utf-8").read())
            rt.continue_()
        pg.route("**/*", route)
        pg.goto("http://127.0.0.1:%s/manga#k=%s" % (PORT, KEY)); pg.wait_for_timeout(2500)
        pg.evaluate("() => { localStorage.setItem('manga_onglet','tChap'); localStorage.setItem('manga_serie','one-punch-man'); localStorage.removeItem('manga_chap_bloc'); }")
        pg.reload(); pg.wait_for_timeout(4500)
        # la serie dans l'ordre des numeros (meme regle que ⏮ ⏭)
        serie = pg.evaluate("""() => CHAPS.filter(c => serieDe(c.dir) === 'one-punch-man')
            .sort((a, b) => chapNum(a) - chapNum(b)).map(c => ({ dir: c.dir, ch: c.chapter }))""")
        print("  serie :", " ".join(x["ch"] for x in serie))
        idx = lambda d: pg.evaluate("d => CHAPS.findIndex(c => c.dir === d)", d)
        def ouvrir(d, page):
            pg.evaluate("i => document.querySelector('#chapList [data-chap=\"' + i + '\"]').click()", idx(d)); pg.wait_for_timeout(3000)
            pg.evaluate("k => document.querySelectorAll('#chapPages figure')[k].click()", page); pg.wait_for_timeout(800)
        etat = lambda: pg.evaluate(ETAT)
        suiv = lambda: (pg.click("#lbNext"), pg.wait_for_timeout(2600))
        prec = lambda: (pg.click("#lbPrev"), pg.wait_for_timeout(2600))

        # milieu de serie : A / B / C
        k = next(i for i, x in enumerate(serie) if x["ch"] == "299")
        A, B = serie[k], serie[k + 1]
        n = pg.evaluate("d => api('/manga/source_pages?d=' + encodeURIComponent(d)).then(j => j.pages.length)", A["dir"])
        ouvrir(A["dir"], n - 2)
        e = etat()
        check("A. barre = « ch. %s · p. %d/%d »" % (A["ch"], n - 1, n), e["nom"] == "ch. %s · p. %d/%d" % (A["ch"], n - 1, n), e["nom"])
        suiv(); e = etat()
        check("A. derniere page atteinte, toujours ch. " + A["ch"], e["lb"] == n - 1 and e["chap"] == A["dir"], e["nom"])
        suiv(); e = etat()
        check("B. › apres la derniere -> ch. %s p.1 (visionneuse ouverte)" % B["ch"],
              e["ouvert"] and e["chap"] == B["dir"] and e["lb"] == 0 and e["nom"].startswith("ch. %s · p. 1/" % B["ch"]), e)
        check("B. le chapitre DERRIERE a suivi", e["titre"].endswith("chapitre " + B["ch"]), e["titre"])
        check("B. message « Chapitre %s »" % B["ch"], ("Chapitre " + B["ch"]) in e["toast"], e["toast"])
        prec(); e = etat()
        check("B. ‹ avant la p.1 -> DERNIERE page du ch. " + A["ch"], e["chap"] == A["dir"] and e["lb"] == e["n"] - 1 == n - 1, e["nom"])
        # double clic rapide : un seul passage
        pg.evaluate("() => { $('lbNext').click(); $('lbNext').click(); }"); pg.wait_for_timeout(2800)
        e = etat()
        check("C. double clic rapide = UN passage (ch. %s p.1, pas p.2)" % B["ch"], e["chap"] == B["dir"] and e["lb"] == 0, e["nom"])
        if tel:
            pg.evaluate(GLISSE, [-120]); pg.wait_for_timeout(2800); e = etat()
            check("C. glisser la barre vers la gauche sur p.1 -> ch. %s derniere page" % A["ch"], e["chap"] == A["dir"] and e["lb"] == n - 1, e["nom"])
            pg.evaluate(GLISSE, [120]); pg.wait_for_timeout(2800); e = etat()
            check("C. glisser vers la droite sur la derniere -> ch. %s p.1" % B["ch"], e["chap"] == B["dir"] and e["lb"] == 0, e["nom"])
        pg.click("#lbClose"); pg.wait_for_timeout(500)

        # D. bouts de la serie
        der = serie[-1]
        nd = pg.evaluate("d => api('/manga/source_pages?d=' + encodeURIComponent(d)).then(j => j.pages.length)", der["dir"])
        ouvrir(der["dir"], nd - 1); suiv(); e = etat()
        check("D. dernier chapitre, derniere page, › -> reste (pas de boucle)", e["chap"] == der["dir"] and e["lb"] == nd - 1 and e["ouvert"], e["nom"])
        check("D. message « Dernier chapitre »", "Dernier chapitre" in e["toast"], e["toast"])
        pg.click("#lbClose"); pg.wait_for_timeout(500)
        pre = serie[0]
        ouvrir(pre["dir"], 0); prec(); e = etat()
        check("D. 1er chapitre, p.1, ‹ -> reste", e["chap"] == pre["dir"] and e["lb"] == 0 and e["ouvert"], e["nom"])
        check("D. message « Premier chapitre »", "Premier chapitre" in e["toast"], e["toast"])
        pg.click("#lbClose"); pg.wait_for_timeout(500)
        # trou de numeros (le 1er ecart > 1 de la serie)
        t = next((i for i in range(len(serie) - 1)
                  if float(serie[i + 1]["ch"]) - float(serie[i]["ch"]) > 1), None)
        if t is not None:
            X, Y = serie[t], serie[t + 1]
            nx = pg.evaluate("d => api('/manga/source_pages?d=' + encodeURIComponent(d)).then(j => j.pages.length)", X["dir"])
            ouvrir(X["dir"], nx - 1); suiv(); e = etat()
            check("D. trou ch.%s -> ch.%s : message dit l'absence" % (X["ch"], Y["ch"]),
                  e["chap"] == Y["dir"] and "absent" in e["toast"], e["toast"])
            pg.click("#lbClose"); pg.wait_for_timeout(500)

        # E. une autre liste garde sa boucle
        e = pg.evaluate("""() => { ouvrirVisionneuse([{ url: 'data:,', nom: 'a' }, { url: 'data:,', nom: 'b' }], 1);
            $('lbNext').click(); const r = { lb: LB, nom: $('lbName').textContent }; lbClose(); return r; }""")
        check("E. autre liste : › sur la derniere -> 1re (boucle gardee)", e["lb"] == 0 and e["nom"] == "1/2 · a", e)

        check("0 erreur JS", not errs, errs[:3])
        print("  POST bloques :", sorted(set(posts)))
        c.close()
    b.close()
print("\n%d OK, %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
