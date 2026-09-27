# -*- coding: utf-8 -*-
"""Banc R6 (v2.82.3, Quang 27/09 03h35 : « ce format qui deborde en haut et en bas, sans liberte, ne respectant pas la largeur de
l'application ») : l'ecran ✏ des Dialogues = une FENETRE de l'app (.modal-in, comme « Suivi & coûts »). App REELLE 8190, OPM ch.5,
lecture seule. Usage : python test_dialogues_prep_gabarit_ui.py [html]        (html = page v2.82.2 -> doit sortir ROUGE)"""
import os, sys
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(HERE, "..", "manga_studio.html")
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PAGE = open(HTML, encoding="utf-8").read()
OK, KO = [], []
def check(n, c, d=""):
    (OK if c else KO).append(n); print(("  [OK] " if c else "  [KO] ") + n + (" -- " + str(d)[:170] if d else ""), flush=True)
MES = """() => { const box = document.querySelector('#dlgPrep .modal-in'), r = e => e.getBoundingClientRect();
  if (!box) return null; const b = r(box), dans = e => { const x = r(e); return x.left >= b.left - 1 && x.right <= b.right + 1 && x.top >= b.top - 1 && x.bottom <= b.bottom + 1; };
  const c = $('dlgpCorps'), deb = [...document.querySelectorAll('#dlgPrep *')].filter(e => e.scrollWidth > e.clientWidth + 1 && ['auto', 'scroll'].includes(getComputedStyle(e).overflowX)).length;
  return { w: Math.round(b.width), gauche: Math.round(b.left), droite: Math.round(innerWidth - b.right), haut_dans: dans($('dlgpRet')) && dans($('dlgpSolde')),
           pied_dans: !$('dlgpPied').offsetParent || dans($('dlgpPied')), defile: c.scrollHeight > c.clientHeight + 5, hauteur: Math.round(b.height), ih: innerHeight,
           deborde: document.documentElement.scrollWidth > document.documentElement.clientWidth || deb > 0 }; }"""
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w, h in ((1280, 900), (933, 700), (704, 900), (476, 900), (360, 780)):
        print("=== %d px" % w)
        ctx = b.new_context(viewport={"width": w, "height": h}, is_mobile=w < 500, has_touch=w < 500)
        pg = ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.route("**/*", lambda rt: rt.fulfill(status=200, content_type="text/html; charset=utf-8", body=PAGE)
                 if rt.request.method == "GET" and rt.request.url.split("#")[0].split("?")[0].rstrip("/").endswith("/manga") else rt.continue_())
        pg.goto("http://127.0.0.1:8190/manga#k=" + KEY); pg.wait_for_timeout(2500)
        pg.evaluate("() => localStorage.setItem('manga_serie','one-punch-man')"); pg.reload(); pg.wait_for_timeout(3500)
        pg.evaluate("() => openChap(CHAPS.findIndex(c => c.dir === 'one-punch-man/ch_5'))"); pg.wait_for_timeout(3500)
        pg.evaluate("() => dlgPrepOuvrir()"); pg.wait_for_timeout(2500)
        m = pg.evaluate(MES)
        check("une FENETRE (.modal-in), pas un plein ecran", m is not None, m)
        if not m:
            ctx.close(); continue
        check("largeur de l'app : <= 760 px, centree", m["w"] <= 760 and abs(m["gauche"] - m["droite"]) <= 2, m)
        check("en-tete (← Chapitre, solde) DANS la fenetre", m["haut_dans"])
        check("pied (Générer…) DANS la fenetre", m["pied_dans"])
        check("hauteur bornee, seul le contenu defile", m["hauteur"] <= m["ih"] * 0.9 + 2 and m["defile"], m)
        pg.evaluate("() => { $('dlgpCorps').scrollTop = 800; }"); pg.wait_for_timeout(300)
        check("apres defilement, l'en-tete reste visible", pg.evaluate("() => { const r = $('dlgpRet').getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight; }"))
        check("aucun debordement (page ni conteneur)", not m["deborde"])
        pg.screenshot(path=os.path.join(os.environ.get("TEMP", "."), "prep_gabarit_%d.png" % w))
        if w > 760:
            pg.mouse.click(8, h // 2); pg.wait_for_timeout(500)
            check("toucher a cote = fermer", pg.evaluate("() => $('dlgPrep').hidden"))
        check("0 erreur JS", not errs, errs)
        ctx.close()
print("VERDICT : %d OK / %d KO" % (len(OK), len(KO)))
