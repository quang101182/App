# -*- coding: utf-8 -*-
"""Banc v2.69.0 (suite) : SELECTEUR RAPIDE dans le LECTEUR NARRE et la VISIONNEUSE (contextes non couverts par test_selecteur_ui).
APP REELLE, lecture seule. Narration : titre / glisser la barre vers le haut, chapitre courant, sans narration = grise + raison,
aller a un autre chapitre narre (choix de voix s'il y en a plusieurs), n° absent, lecture « a l'aveugle » = pas de sommaire,
Echap ne ferme QUE le selecteur. Visionneuse : « Aller a la page (N) », n° exact, page absente -> la plus proche, glisser, G, Echap.
360 / 476 / 704 / 933 / 1280 px.
Usage : python test_selecteur_narr_pages_ui.py [port] [serie] [--mutation]      (defaut 8190 one-punch-man ;
  --mutation : app servie SABOTEE (visionneuse non branchee + garde « a l'aveugle » retiree), 360 px seul -> doit sortir ROUGE)
"""
import os, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
MUT = "--mutation" in sys.argv; sys.argv = [a for a in sys.argv if a != "--mutation"]
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
SERIE = sys.argv[2] if len(sys.argv) > 2 else "one-punch-man"
SABOTAGES = [('if (!$("lightbox").hidden) return selCtxPages();', ''),                       # visionneuse non branchee
             ('return LEC.aveugle ? null : selCtxNarr();', 'return selCtxNarr();')]          # a l'aveugle : sommaire ouvert
def saboter(route):
    r = route.fetch(); t = r.text()
    for a, z in SABOTAGES:
        assert a in t, "ancre de sabotage introuvable : " + a
        t = t.replace(a, z)
    route.fulfill(response=r, body=t)
OK, KO = [], []
def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail)[:200] if detail else ""), flush=True)
def glisser(pg, sel, dx, dy):
    pg.evaluate("""([sel, dx, dy]) => { const el = document.querySelector(sel), r = el.getBoundingClientRect(), x = r.left + r.width / 2, y = r.top + r.height / 2;
      const T = (a, b) => new Touch({ identifier: 1, target: el, clientX: a, clientY: b });
      el.dispatchEvent(new TouchEvent('touchstart', { touches: [T(x, y)], bubbles: true }));
      el.dispatchEvent(new TouchEvent('touchmove', { touches: [T(x + dx / 2, y + dy / 2)], bubbles: true }));
      el.dispatchEvent(new TouchEvent('touchend', { touches: [], changedTouches: [T(x + dx, y + dy)], bubbles: true })); }""", [sel, dx, dy])
DANS_ECRAN = """() => { const r = $('selFeuille').getBoundingClientRect(); return [r.left >= -1, r.right <= innerWidth + 1, r.bottom <= innerHeight + 1,
    r.top >= -1, document.documentElement.scrollWidth <= innerWidth]; }"""
FEUILLE = "() => !$('selFeuille').hidden"

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    lisibles = None
    for w, h in (((360, 780),) if MUT else ((360, 780), (476, 820), (704, 820), (933, 700), (1280, 900))):
        print("== %d px" % w)
        pg = b.new_page(viewport={"width": w, "height": h}, is_mobile=w < 500, has_touch=True); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        if MUT: pg.route("**/manga", saboter)
        pg.goto("http://127.0.0.1:%d/manga#k=%s" % (PORT, KEY)); pg.wait_for_timeout(4000)
        pg.click('nav button[data-tab="tChap"]'); pg.wait_for_timeout(1500)
        if lisibles is None:                         # chapitres de la serie avec une narration avec voix (une seule fois : c'est lent)
            lisibles = pg.evaluate("""async (s) => { const l = CHAPS.filter(c => c.dir.startsWith(s + '/')).sort((a, b) => chapNum(a) - chapNum(b));
                const out = []; for (const c of l) { const n = await narrAvecVoix(c.dir); if (n) out.push([c.dir, String(c.chapter), n.tag]); } return out; }""", SERIE)
            print("  chapitres narrés :", len(lisibles))
        if len(lisibles) < 2:
            check("au moins 2 chapitres narrés", False, lisibles); break
        (d1, n1, t1), (d2, n2, t2) = lisibles[0], lisibles[1]
        # ---------- A. lecteur narre
        pg.evaluate("async ([d, t]) => { await openChap(CHAPS.findIndex(c => c.dir === d)); await ouvrirLecteur([t]); $('lecAudio').pause(); }", [d1, t1])
        pg.wait_for_timeout(2000)
        pg.evaluate("() => $('lecTitre').click()"); pg.wait_for_timeout(400)
        st = pg.evaluate("() => [!$('selFeuille').hidden, $('selTitre').textContent, (document.querySelector('#selGrille .cour') || {}).dataset?.k, $('selNum').placeholder]")
        check("narration : titre → « Narration — aller au chapitre », courant en vert", st[0] and st[1].startswith("Narration") and st[2] == d1 and "chapitre" in st[3], st)
        check("narration : feuille dans l'écran, pas de débordement", all(pg.evaluate(DANS_ECRAN)), pg.evaluate(DANS_ECRAN))
        off = pg.evaluate("() => document.querySelectorAll('#selGrille .sel-c.off:not(.trou)').length")
        if off:
            pg.evaluate("() => document.querySelector('#selGrille .sel-c.off:not(.trou)').click()"); pg.wait_for_timeout(200)
            inf = pg.evaluate("() => $('selInfo').textContent")
            check("narration : chapitre sans narration grisé → raison, rien ne s'ouvre", "⚠" in inf and "narration" in inf and pg.evaluate(FEUILLE), inf)
        else:
            print("  (tous les chapitres de la série sont narrés : cas « sans narration » non exerçable ici)")
        nf = pg.evaluate("() => [document.querySelectorAll('#selGrille .sel-c').length, (()=>{ document.querySelector('#selFiltres [data-f=narr]').click(); return document.querySelectorAll('#selGrille .sel-c').length; })()]")
        check("narration : filtre « avec narration » ne garde que les lançables", nf[1] <= nf[0] and nf[1] >= 2 and pg.evaluate("() => !document.querySelector('#selGrille .sel-c.off')"), nf)
        pg.evaluate("() => document.querySelector('#selFiltres [data-f=tous]').click()")
        pg.fill("#selNum", "99999"); pg.keyboard.press("Enter"); pg.wait_for_timeout(300)
        check("narration : n° absent → « absent — le plus proche »", "absent" in pg.evaluate("() => $('selInfo').textContent"))
        pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
        check("narration : Échap ferme le sélecteur SEULEMENT (le lecteur reste)", pg.evaluate("() => $('selFeuille').hidden && !$('lecteur').hidden"))
        glisser(pg, "#lecteur .lec-ctl", 0, -120); pg.wait_for_timeout(400)
        check("narration : glisser la barre du lecteur vers le haut → ouvert", pg.evaluate(FEUILLE))
        pg.evaluate("(d) => document.querySelector('#selGrille .sel-c[data-k=\"' + d + '\"]').click()", d2); pg.wait_for_timeout(2500)
        if pg.evaluate("() => !!document.querySelector('#selInfo [data-ver]')"):
            print("  plusieurs voix pour ch.%s : choix proposé" % n2)
            pg.evaluate("() => document.querySelector('#selInfo [data-ver]').click()"); pg.wait_for_timeout(3000)
        e = pg.evaluate("() => [CHAP_OPEN, !$('lecteur').hidden, $('selFeuille').hidden, $('lecTitre').textContent]")
        check("narration : choisir ch.%s → son lecteur s'ouvre" % n2, e[0] == d2 and e[1] and e[2], e)
        pg.evaluate("() => $('lecAudio').pause()")
        pg.keyboard.press("g"); pg.wait_for_timeout(300)
        check("narration : touche G → ouvert, courant = ch.%s" % n2, pg.evaluate("(d) => !$('selFeuille').hidden && (document.querySelector('#selGrille .cour') || {}).dataset?.k === d", d2))
        pg.keyboard.press("Escape"); pg.wait_for_timeout(200)
        pg.evaluate("() => $('lecFermer').click()"); pg.wait_for_timeout(600)
        # lecture « a l'aveugle » : pas de sommaire
        pg.evaluate("async ([d, t]) => { await openChap(CHAPS.findIndex(c => c.dir === d)); await ouvrirLecteur([t], true); $('lecAudio').pause(); }", [d1, t1])
        pg.wait_for_timeout(1500)
        pg.evaluate("() => $('lecTitre').click()"); pg.wait_for_timeout(300)
        glisser(pg, "#lecteur .lec-ctl", 0, -120); pg.wait_for_timeout(300)
        check("narration à l'aveugle : ni titre ni glisser n'ouvrent le sommaire", pg.evaluate("() => $('selFeuille').hidden && !$('lecteur').hidden"))
        pg.evaluate("() => $('lecFermer').click()"); pg.wait_for_timeout(600)
        # ---------- B. visionneuse
        pg.evaluate("async (d) => { await openChap(CHAPS.findIndex(c => c.dir === d)); }", d1); pg.wait_for_timeout(1500)
        pg.evaluate("() => document.querySelectorAll('#chapPages figure img')[0].click()"); pg.wait_for_timeout(1200)
        n = pg.evaluate("() => LB_LISTE.length")
        check("visionneuse ouverte (%d pages)" % n, pg.evaluate("() => !$('lightbox').hidden") and n >= 3, n)
        pg.evaluate("() => $('lbName').click()"); pg.wait_for_timeout(400)
        st = pg.evaluate("() => [$('selTitre').textContent, $('selNum').placeholder, document.querySelectorAll('#selGrille .sel-c').length, (document.querySelector('#selGrille .cour') || {}).textContent, $('selFiltres').hidden]")
        check("pages : « Aller à la page (N) », N cases, page 1 en vert, sans filtres", st[0] == "Aller à la page (%d)" % n and "page" in st[1] and st[2] == n and st[3] == "1" and st[4], st)
        check("pages : feuille dans l'écran, pas de débordement", all(pg.evaluate(DANS_ECRAN)), pg.evaluate(DANS_ECRAN))
        cible = min(3, n)
        pg.fill("#selNum", str(cible)); pg.keyboard.press("Enter"); pg.wait_for_timeout(700)
        check("pages : « %d » + Entrée → page %d, sélecteur fermé, visionneuse ouverte" % (cible, cible),
              pg.evaluate("() => [LB + 1, $('selFeuille').hidden, !$('lightbox').hidden, $('lbName').textContent.split(' ')[0]]") == [cible, True, True, "%d/%d" % (cible, n)],
              pg.evaluate("() => [LB + 1, $('lbName').textContent]"))
        glisser(pg, "#lightbox .lbbar", 0, -120); pg.wait_for_timeout(400)
        check("pages : glisser la barre vers le haut → ouvert, page %d en vert" % cible, pg.evaluate(FEUILLE) and pg.evaluate("() => (document.querySelector('#selGrille .cour') || {}).textContent") == str(cible))
        pg.fill("#selNum", str(n + 50)); pg.keyboard.press("Enter"); pg.wait_for_timeout(300)
        inf = pg.evaluate("() => $('selInfo').textContent")
        check("pages : page absente → « page … absent — le plus proche : p. %d »" % n, "absent" in inf and ("p. %d" % n) in inf, inf)
        pg.evaluate("() => document.querySelector('#selInfo [data-k]').click()"); pg.wait_for_timeout(600)
        check("pages : toucher « le plus proche » → dernière page", pg.evaluate("() => LB + 1") == n and pg.evaluate("() => $('selFeuille').hidden"))
        pg.keyboard.press("g"); pg.wait_for_timeout(300)
        g = pg.evaluate(FEUILLE)
        pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
        check("pages : G ouvre", g)
        check("pages : G ouvre, Échap ne ferme QUE le sélecteur", pg.evaluate("() => $('selFeuille').hidden && !$('lightbox').hidden"))
        pg.evaluate("() => $('lbClose').click()"); pg.wait_for_timeout(300)
        check("aucune erreur JS", not errs, errs[:3])
        pg.close()
    b.close()
print("\nVERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
