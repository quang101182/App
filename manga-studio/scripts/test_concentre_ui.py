# -*- coding: utf-8 -*-
"""Banc v3.5.4 (S5) : alerte « presque tout au meme personnage ». App REELLE 8190 (page substituee si --page), lecture seule
(tout POST intercepte). Les repliques de la plage sont REMPLACEES en memoire (jamais sur disque) pour chaque cas :
A. 9 sur 10 au meme -> bandeau, texte exact ; B. « c’est normal » -> retire, ne revient pas au rendu suivant (memorise) ;
C. 5/5 partage -> rien ; D. repliques corrigees par Quang -> rien ; E. moins de 6 -> rien ; F. « vérifier » -> verification ouverte.
Usage : python test_concentre_ui.py <serie/ch_N avec une plage preparee> [--page f.html] [--360]"""
import os, sys
from playwright.sync_api import sync_playwright
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
a = sys.argv[1:]; PAGE = None
if "--page" in a:
    i = a.index("--page"); PAGE = open(a[i + 1], encoding="utf-8").read(); del a[i:i + 2]
L = 360 if "--360" in a else 704
a = [x for x in a if not x.startswith("--")]; CH = a[0]
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail)[:160] if detail else ""), flush=True)


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    pg = b.new_context(viewport={"width": L, "height": 900}, is_mobile=L < 800, service_workers="block").new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    def route(rt):
        u = rt.request.url.split("#")[0].split("?")[0].rstrip("/")
        if rt.request.method != "GET": return rt.fulfill(status=200, body='{"ok":true}', content_type="application/json")
        if PAGE and u.endswith("/manga"): return rt.fulfill(status=200, body=PAGE, content_type="text/html; charset=utf-8")
        return rt.continue_()
    pg.route("**/*", route)
    pg.goto("http://127.0.0.1:8190/manga/#k=" + KEY); pg.wait_for_timeout(2000)
    pg.evaluate("s => { localStorage.setItem('manga_onglet','tChap'); localStorage.setItem('manga_serie', s); localStorage.removeItem('manga_dlg_normal'); }", CH.split("/")[0])
    pg.reload(); pg.wait_for_timeout(3000)
    print("     version :", pg.evaluate("() => VERSION"))
    pg.evaluate("d => openChap(CHAPS.findIndex(c => c.dir === d))", CH); pg.wait_for_timeout(3000)
    pg.evaluate("() => clOuvrir('dlg')"); pg.wait_for_timeout(2500)
    k = pg.evaluate("() => dplListe()[0]")
    pg.evaluate("k => dplChoisir(k)", k); pg.wait_for_timeout(600)
    persos = pg.evaluate("() => DLG.e.distribution.persos.map(p => p.nom)")
    def poser(liste):             # liste de (qui, corrige?) -> repliques de la plage, en memoire
        pg.evaluate("""([k, l]) => { const [a] = dplBornes(k); DLG.e.doc = Object.assign({}, DLG.e.doc, { repliques: l.map((q, i) => ({ cle: a + '-' + (i + 1), page: a, id: i + 1,
                        qui: q[0], lire: true, texte: 'x', corrige: q[1] ? { qui: q[0] } : {} })) }); dlgRendre(); }""", [k, liste])
        pg.wait_for_timeout(400)
        return pg.evaluate("() => { const d = document.querySelector('#dlgEtat .dpl-s5'); return d ? d.textContent : ''; }")
    t = poser([(persos[0], False)] * 9 + [(persos[1], False)])
    check("A. 9 sur 10 au meme personnage -> bandeau", "9 répliques sur 10" in t and persos[0] in t, t)
    pg.evaluate("() => document.querySelector('[data-s5=ok]').click()"); pg.wait_for_timeout(300)
    t2 = pg.evaluate("() => { dlgRendre(); return !!document.querySelector('#dlgEtat .dpl-s5'); }")
    check("B. « c’est normal » -> retire, ne revient pas (memorise)", not t2 and k in pg.evaluate("() => localStorage.getItem('manga_dlg_normal') || ''"))
    pg.evaluate("() => localStorage.removeItem('manga_dlg_normal')")
    check("C. 5 / 5 partage -> aucun bandeau", poser([(persos[0], False)] * 5 + [(persos[1], False)] * 5) == "")
    check("D. repliques corrigees par Quang -> aucun bandeau", poser([(persos[0], True)] * 10) == "")
    check("E. moins de 6 repliques -> aucun bandeau", poser([(persos[0], False)] * 5) == "")
    poser([(persos[0], False)] * 10)
    pg.evaluate("() => document.querySelector('[data-s5=voir]').click()"); pg.wait_for_timeout(2500)
    check("F. « vérifier qui parle » -> verification des bulles ouverte", pg.evaluate("() => !$('dlvBox').hidden"))
    pg.evaluate("() => { DLV.pages.forEach(p => p.modif = 0); $('dlvFermer').click(); }")
    check("aucun debordement horizontal", not pg.evaluate("() => document.documentElement.scrollWidth > document.documentElement.clientWidth"))
    check("0 erreur JS", not errs, errs[:2])
    b.close()
print("\nVERDICT : %d/%d" % (len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
