# -*- coding: utf-8 -*-
"""Banc R7 (v2.82.4, Quang 27/09 03h41 : « le lecteur video ne respecte pas du tout l'autre lecteur video ») : une video des
Dialogues s'ouvre dans LE lecteur video de l'app (#vidLecteur). On ouvre la video de NARRATION du meme chapitre (reference), on
mesure, puis celle des DIALOGUES : memes elements, memes hauteurs. App REELLE 8190, OPM ch.5, lecture seule.
Usage : python test_dialogues_video_lecteur_ui.py [html]        (html = page v2.82.3 -> doit sortir ROUGE)"""
import os, sys
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(HERE, "..", "manga_studio.html")
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PAGE = open(HTML, encoding="utf-8").read()
OK, KO = [], []
def check(n, c, d=""):
    (OK if c else KO).append(n); print(("  [OK] " if c else "  [KO] ") + n + (" -- " + str(d)[:170] if d else ""), flush=True)
MES = """() => { const L = $('vidLecteur'); if (L.hidden) return null; const h = s => { const e = L.querySelector(s); return e && e.offsetParent ? Math.round(e.getBoundingClientRect().height) : 0; };
  return { tete: h('.vid-lec-tete'), bas: h('.vid-bas'), prog: h('#vidProg'), pp: h('#vidPP'), m10: h('#vidM10'), p10: h('#vidP10'), menu: !!L.querySelector('#vidMenu'),
           natif: !!document.querySelector('video[controls]:not([hidden])') && !document.querySelector('video[controls]').closest('[hidden]') }; }"""
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True, args=["--mute-audio", "--autoplay-policy=no-user-gesture-required"])
    for w, h in ((1280, 900), (360, 780)):
        print("=== %d px" % w)
        ctx = b.new_context(viewport={"width": w, "height": h}, is_mobile=w < 500, has_touch=w < 500)
        pg = ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.route("**/*", lambda rt: rt.fulfill(status=200, content_type="text/html; charset=utf-8", body=PAGE)
                 if rt.request.method == "GET" and rt.request.url.split("#")[0].split("?")[0].rstrip("/").endswith("/manga") else rt.continue_())
        pg.goto("http://127.0.0.1:8190/manga#k=" + KEY); pg.wait_for_timeout(2500)
        pg.evaluate("() => localStorage.setItem('manga_serie','one-punch-man')"); pg.reload(); pg.wait_for_timeout(3500)
        pg.evaluate("() => vidCharger('one-punch-man')"); pg.wait_for_timeout(3000)
        pg.evaluate("() => { const i = VIDS.chapitres.findIndex(c => (c.videos || []).length && String(c.chapitre) === '5'); if (i >= 0) vidOuvrir(i); }"); pg.wait_for_timeout(2500)
        ref = pg.evaluate(MES)
        check("reference : la video de NARRATION du ch.5 dans #vidLecteur", ref is not None, ref)
        pg.evaluate("() => $('vidLecFermer').click()"); pg.wait_for_timeout(500)
        pg.evaluate("() => openChap(CHAPS.findIndex(c => c.dir === 'one-punch-man/ch_5'))"); pg.wait_for_timeout(3500)
        pg.evaluate("() => { const v = Object.values(dlgVideos(DLG.e.doc, DLG.plan))[0]; if (v) dlgVidMontrer(v.v); }"); pg.wait_for_timeout(2500)
        dlg = pg.evaluate(MES)
        check("la video des DIALOGUES s'ouvre dans LE MEME lecteur (#vidLecteur)", dlg is not None and "/dialogues/video/" in pg.evaluate("() => decodeURIComponent($('vidLecVideo').src)"), dlg)
        if dlg and ref:
            check("memes elements et hauteurs (en-tete, barre du bas, temps, −10 / ⏸ / +10, ⋯)", all(abs(dlg[k] - ref[k]) <= 2 for k in ("tete", "bas", "prog", "pp", "m10", "p10")) and dlg["menu"],
                  {k: (dlg[k], ref[k]) for k in ("tete", "bas", "prog", "pp", "m10", "p10")})
            check("aucun lecteur aux commandes du navigateur", not dlg["natif"])
            check("titre « 🎭 … ch. 5 »", pg.evaluate("() => $('vidLecTitre').textContent").startswith("🎭") and "ch. 5" in pg.evaluate("() => $('vidLecTitre').textContent"))
            check("une seule video de dialogues dans la serie : aucun voisin (et jamais une video de narration)", pg.evaluate("() => $('vidLecPrev').hidden && $('vidLecNext').hidden"))
            pg.evaluate("() => { const e = $('vidLecVideo'); e.currentTime = Math.max(0, e.duration - 0.3); }"); pg.wait_for_timeout(2500)
            check("fin de video : pas d'enchainement sur une video de narration", pg.evaluate("() => $('vidSuite').hidden && $('vidLecVideo').src.includes('dialogues')"))
            pg.evaluate("() => $('vidPP').click()"); pg.wait_for_timeout(600)
            check("les commandes de l'app pilotent la video (⏸/▶)", pg.evaluate("() => !$('vidLecVideo').paused || $('vidLecVideo').currentTime < 1"))
        pg.evaluate("() => $('vidLecFermer').click()"); pg.wait_for_timeout(400)
        pg.evaluate("() => { const i = VIDS.chapitres.findIndex(c => (c.videos || []).length && String(c.chapitre) === '5'); if (i >= 0) vidOuvrir(i); }"); pg.wait_for_timeout(2000)
        check("apres une video de dialogues, la NARRATION retrouve sa liste (voisins de narration)",
              pg.evaluate("() => VID.dlg === null && (!$('vidLecNext').hidden || !$('vidLecPrev').hidden) && !decodeURIComponent($('vidLecVideo').src).includes('/dialogues/')"))
        check("0 erreur JS", not errs, errs)
        ctx.close()
print("VERDICT : %d OK / %d KO" % (len(OK), len(KO)))
