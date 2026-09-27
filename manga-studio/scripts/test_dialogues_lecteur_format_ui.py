# -*- coding: utf-8 -*-
"""Banc R2 (v2.81.8, Quang 27/09 02h30 : « la barre de navigation en bas ne ressemble pas a toute l'application […] meme les
fonctions de swipe ») : le lecteur des Dialogues a le FORMAT du lecteur de narration. On MESURE les deux lecteurs cote a cote
(meme chapitre : OPM ch.5, narre ET avec dialogues) et on joue les gestes au vrai tactile (CDP Input.dispatchTouchEvent).
ISOLE : instance 8191 (proxy donne) sur une COPIE d'OPM ch.5 ; page = le HTML donne. 0 credit.
Usage : python test_dialogues_lecteur_format_ui.py <html> <proxy>        (html = page v2.81.7 -> doit sortir ROUGE)"""
import json, os, shutil, subprocess, sys, tempfile, time, urllib.request
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
HTML, PROXY = (os.path.abspath(x) for x in sys.argv[1:3])
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
SRC = r"C:\Users\quang\Documents\MangaStudio-donnees\sources"
PAGE = open(HTML, encoding="utf-8").read()
OK, KO = [], []


def check(n, c, d=""):
    (OK if c else KO).append(n); print(("  [OK] " if c else "  [KO] ") + n + (" -- " + str(d)[:170] if d else ""), flush=True)


T = tempfile.mkdtemp(prefix="dlg_format_")
os.makedirs(os.path.join(T, "one-punch-man"))
shutil.copytree(os.path.join(SRC, "one-punch-man", "ch_5"), os.path.join(T, "one-punch-man", "ch_5"), ignore=shutil.ignore_patterns("video", "*.mp4"))
for f in ("serie.json", "dialogues_distribution.json", "suivi.json"):
    shutil.copy(os.path.join(SRC, "one-punch-man", f), os.path.join(T, "one-punch-man", f))
srv = subprocess.Popen([sys.executable, os.path.join(HERE, "proxy_8191.py"), PROXY], env=dict(os.environ, MANGA_SOURCES_DIR=T),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

MESURE = """sel => { const L = document.querySelector(sel); const q = s => L.querySelector(s);
  const r = e => e ? e.getBoundingClientRect() : null, top = q('.lec-top'), ctl = q('.lec-ctl'), bar = q('.lec-bar'), f = q('.lec-top .retour');
  const bt = ctl ? [...ctl.querySelectorAll(':scope > .btn')].map(b => Math.round(b.getBoundingClientRect().height)) : [];
  return { top: !!top && L.firstElementChild === top, fermer_gauche: f ? r(f).left - r(top).left < 40 : false, fermer_bleu: f ? f.classList.contains('retour') : false,
           h_top: top ? Math.round(r(top).height) : 0, h_bar: bar ? Math.round(r(bar).height) : 0, h_ctl: ctl ? Math.round(r(ctl).height) : 0,
           boutons: bt, pri: !!(ctl && ctl.querySelector('.btn.pri')), vol: !!(ctl && ctl.querySelector('input.lec-vol')),
           reglages: !!(ctl && [...ctl.querySelectorAll('.btn')].some(b => b.textContent.includes('⚙'))), sous_centre: getComputedStyle(q('.lec-sous')).textAlign,
           ctl_en_bas: ctl ? innerHeight - r(ctl).bottom < 30 : false }; }"""


def glisser(cdp, x0, y0, x1, y1):
    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x0, "y": y0}]})
    for k in range(1, 9):
        cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x0 + (x1 - x0) * k / 8, "y": y0 + (y1 - y0) * k / 8}]})
        time.sleep(0.02)
    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})


try:
    for _ in range(60):
        try:
            urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8191/manga/el_solde", headers={"Authorization": "Bearer " + KEY}), timeout=5); break
        except Exception:
            time.sleep(1)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True, args=["--autoplay-policy=no-user-gesture-required", "--mute-audio"])
        for w, h in ((1280, 900), (360, 780)):
            print("=== %d px" % w)
            ctx = b.new_context(viewport={"width": w, "height": h}, is_mobile=w < 500, has_touch=True)
            pg = ctx.new_page(); errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.route("**/*", lambda rt: rt.fulfill(status=200, content_type="text/html; charset=utf-8", body=PAGE)
                     if rt.request.method == "GET" and rt.request.url.split("#")[0].split("?")[0].rstrip("/").endswith("/manga") else rt.continue_())
            pg.goto("http://127.0.0.1:8191/manga#k=" + KEY); pg.wait_for_timeout(2500)
            pg.evaluate("() => localStorage.setItem('manga_serie','one-punch-man')"); pg.reload(); pg.wait_for_timeout(3500)
            pg.evaluate("() => openChap(CHAPS.findIndex(c => c.dir === 'one-punch-man/ch_5'))"); pg.wait_for_timeout(3000)
            # la reference : le lecteur de narration du meme chapitre
            pg.evaluate("() => { const b = document.querySelector('#narrRuns [data-ecoute]'); if (b) b.click(); }"); pg.wait_for_timeout(3000)
            ref = pg.evaluate(MESURE, "#lecteur") if pg.evaluate("() => !$('lecteur').hidden") else None
            if ref:
                cdp0 = ctx.new_cdp_session(pg); rb = pg.locator("#lecteur .lec-ctl").bounding_box()
                glisser(cdp0, rb["x"] + rb["width"] / 2, rb["y"] + 8, rb["x"] + rb["width"] / 2, rb["y"] + 66); pg.wait_for_timeout(700)
                check("(reference) le meme geste vers le bas ouvre le selecteur de la narration", pg.evaluate("() => !$('selFeuille').hidden"))
                pg.evaluate("() => { if (!$('selFeuille').hidden) selFermer(); }")
            pg.evaluate("() => $('lecFermer').click()"); pg.wait_for_timeout(600)
            pg.evaluate("() => dlgLecteur()"); pg.wait_for_timeout(2500)
            dlg = pg.evaluate(MESURE, "#dlgLec")
            check("reference mesuree (lecteur de narration ouvert)", ref is not None, ref)
            ref = ref or {}
            check("barre du HAUT en tete, « ← Fermer » bleu a GAUCHE", dlg["top"] and dlg["fermer_gauche"] and dlg["fermer_bleu"], dlg)
            check("memes hauteurs que la reference (haut / progression / commandes, ±2 px)",
                  all(abs(dlg[k] - ref.get(k, -99)) <= 2 for k in ("h_top", "h_bar", "h_ctl")), {k: (dlg[k], ref.get(k)) for k in ("h_top", "h_bar", "h_ctl")})
            check("memes boutons de commande (tailles) + ⏸ en avant + 🔊 + ⚙ Réglages",
                  dlg["boutons"] == ref.get("boutons") and dlg["pri"] and dlg["vol"] and dlg["reglages"], (dlg["boutons"], ref.get("boutons")))
            check("sous-titre centre comme la reference, commandes en bas", dlg["sous_centre"] == ref.get("sous_centre") == "center" and dlg["ctl_en_bas"])
            titre = pg.evaluate("() => $('dllTitre').textContent")
            check("titre lisible en entier (pas tronque)", pg.evaluate("() => $('dllTitre').scrollWidth <= $('dllTitre').clientWidth + 1"))
            check("titre « 🎭 ch. N », voisins ⏮ ch. / ch. ⏭ presents", "ch. 5" in titre and pg.evaluate("() => !!$('dllChPrev') && !!$('dllChNext')"), titre)
            # barre de progression : cliquer au milieu = aller au milieu
            n = pg.evaluate("() => DLL.liste.length")
            bb = pg.locator("#dllBar").bounding_box()
            pg.mouse.click(bb["x"] + bb["width"] * 0.5, bb["y"] + bb["height"] / 2); pg.wait_for_timeout(900)
            check("barre de progression : cliquer au milieu = etape %d / %d" % (n // 2 + 1, n), pg.evaluate("() => DLL.i") == n // 2, pg.evaluate("() => DLL.i"))
            # reglages : ouvrir, contenu, Echap ferme D'ABORD les reglages
            pg.evaluate("() => $('dllRegBtn').click()"); pg.wait_for_timeout(300)
            reg = pg.evaluate("() => !$('dllReg').hidden && !!$('dllVit') && !!$('dllSousOn') && $('dllCam').type === 'checkbox'")
            check("⚙ Réglages : vitesse, sous-titres, caméra", reg)
            pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
            check("Echap : ferme les reglages, PAS le lecteur", pg.evaluate("() => $('dllReg').hidden && !dlgLec.hidden"))
            # gestes tactiles sur la barre des commandes
            cdp = ctx.new_cdp_session(pg)
            cb = pg.locator("#dllCtl").bounding_box(); cy = cb["y"] + 6; cx = cb["x"] + cb["width"] / 2
            pg.evaluate("() => { DLL.audio.pause(); DLL.i = 3; dllMontrer(); DLL.pause = true; }"); pg.wait_for_timeout(600)
            glisser(cdp, cx - 80, cy, cx + 80, cy); pg.wait_for_timeout(700)
            check("glisser la barre vers la DROITE = ⏭ (réplique suivante)", pg.evaluate("() => DLL.i") == 4, pg.evaluate("() => DLL.i"))
            glisser(cdp, cx + 80, cy, cx - 80, cy); pg.wait_for_timeout(700)
            check("glisser vers la GAUCHE = ⏮", pg.evaluate("() => DLL.i") == 3, pg.evaluate("() => DLL.i"))
            glisser(cdp, cx, cy + 2, cx, cy + 60); pg.wait_for_timeout(700)
            sel = pg.evaluate("() => !$('selFeuille').hidden ? $('selFeuille').textContent.slice(0, 60) : ''")
            check("glisser vers le BAS = selecteur rapide « aller à la page »", "aller à la page" in sel, sel)
            if sel:
                pg.evaluate("() => { const b = [...document.querySelectorAll('#selFeuille [data-k]')].find(x => x.textContent.trim().startsWith('15')); if (b) b.click(); }")
                pg.wait_for_timeout(1200)
                check("choisir la page 15 = le lecteur y va", pg.evaluate("() => DLL.liste[DLL.i].page") == 15, pg.evaluate("() => DLL.liste[DLL.i].page"))
            pg.evaluate("() => { if (!$('selFeuille').hidden) selFermer(); }")
            pg.keyboard.press("g"); pg.wait_for_timeout(500)
            check("touche G = selecteur rapide", pg.evaluate("() => !$('selFeuille').hidden"))
            pg.evaluate("() => selFermer()"); pg.wait_for_timeout(200)
            pg.evaluate("() => { $('dllVol').value = 40; $('dllVol').dispatchEvent(new Event('input')); }")
            check("volume = le volume general memorise (le meme que la narration)", pg.evaluate("() => localStorage.getItem('manga_vol_g') === '40' && Math.abs(DLL.audio.volume - .4) < .01"))
            pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
            check("Echap (sans reglages) : ferme le lecteur", pg.evaluate("() => dlgLec.hidden"))
            check("pas de debordement, 0 erreur JS", not errs and not pg.evaluate("() => document.documentElement.scrollWidth > document.documentElement.clientWidth"), errs)
            pg.evaluate("() => dlgLecteur()"); pg.wait_for_timeout(2000)
            pg.screenshot(path=os.path.join(tempfile.gettempdir(), "dlg_format_%d.png" % w))
            ctx.close()
finally:
    srv.kill()
    shutil.rmtree(T, ignore_errors=True)
    try:
        os.remove(os.path.expanduser(r"~\Documents\ComfyUI\_studio_llm_proxy_8191.py"))
    except Exception:
        pass
print("VERDICT : %d OK / %d KO" % (len(OK), len(KO)))
