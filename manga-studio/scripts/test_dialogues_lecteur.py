# -*- coding: utf-8 -*-
"""Banc D6 (ROADMAP 4-septdecies) : le LECTEUR des Dialogues, ISOLE (serveur de test 8191 sur une COPIE deja preparee avec ses
voix ; page = copie patchee). 0 credit.
A. ouverture : page traduite affichee, 1re replique, sous-titre + pastille au nom, audio lance
B. halo : couleur du personnage ; le trace de la bulle tombe SUR la bulle (±4 px ecran) a 360 / 704 / 1280 px ; voile present
C. enchainement : la replique suivante arrive seule a la fin de la voix ; ⏭ / ⏮ ; pause
D. pas de debordement, 0 erreur JS ; captures pour relecture a l'oeil
Usage : python test_dialogues_lecteur.py <manga_studio.html patchee> <proxy patche> <dossier sources copie>
"""
import os, subprocess, sys, tempfile, time, urllib.request
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
HTML, PROXY, T = (os.path.abspath(x) for x in sys.argv[1:4])
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
OUT = tempfile.gettempdir()
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail)[:170] if detail else ""), flush=True)


srv = subprocess.Popen([sys.executable, os.path.join(HERE, "proxy_8191.py"), PROXY], env=dict(os.environ, MANGA_SOURCES_DIR=T),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
PAGE = open(HTML, encoding="utf-8").read()
ALIGNE = """() => {
  const x = DLL.liste[DLL.i], img = $('dllImg').getBoundingClientRect(), path = $('dllSvg').querySelectorAll('path')[1];
  const pr = path.getBoundingClientRect();
  const xs = x.contour ? x.contour.map(p => p[0]) : [x.box.x, x.box.x + x.box.w], ys = x.contour ? x.contour.map(p => p[1]) : [x.box.y, x.box.y + x.box.h];
  const att = { l: img.left + Math.min(...xs) * img.width, t: img.top + Math.min(...ys) * img.height, r: img.left + Math.max(...xs) * img.width, b: img.top + Math.max(...ys) * img.height };
  return { ecart: Math.max(Math.abs(pr.left - att.l), Math.abs(pr.top - att.t), Math.abs(pr.right - att.r), Math.abs(pr.bottom - att.b)),
           svg_sur_img: Math.abs($('dllSvg').getBoundingClientRect().width - img.width) < 1.5 && Math.abs($('dllSvg').getBoundingClientRect().left - img.left) < 1.5,
           trait: path.getAttribute('stroke'), qui: x.qui, voile: !!$('dllSvg').querySelector('rect[mask]'),
           nw: $('dllImg').naturalWidth, deborde: document.documentElement.scrollWidth > document.documentElement.clientWidth,
           cadre_ok: $('dllCadre').getBoundingClientRect().bottom <= $('dllScene').getBoundingClientRect().bottom + 1 };
}"""
try:
    for _ in range(60):
        try:
            urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8191/manga/el_solde", headers={"Authorization": "Bearer " + KEY}), timeout=5); break
        except Exception:
            time.sleep(1)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True, args=["--autoplay-policy=no-user-gesture-required"])
        for w, h in ((1280, 900), (704, 900), (360, 780)):
            print("=== %d px" % w)
            ctx = b.new_context(viewport={"width": w, "height": h}, is_mobile=w < 500, has_touch=w < 500)
            pg = ctx.new_page(); errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.route("**/*", lambda rt: rt.fulfill(status=200, content_type="text/html; charset=utf-8", body=PAGE)
                     if rt.request.method == "GET" and rt.request.url.split("#")[0].split("?")[0].rstrip("/").endswith("/manga") else rt.continue_())
            pg.goto("http://127.0.0.1:8191/manga#k=" + KEY); pg.wait_for_timeout(2500)
            pg.evaluate("() => { localStorage.setItem('manga_onglet','tChap'); localStorage.setItem('manga_serie','opm'); }")
            pg.reload(); pg.wait_for_timeout(3500)
            pg.evaluate("() => openChap(CHAPS.findIndex(c => c.dir === 'opm/ch_6'))"); pg.wait_for_timeout(3500)
            pg.evaluate("() => dlgLecteur()"); pg.wait_for_timeout(2500)
            a = pg.evaluate(ALIGNE)
            check("A. lecteur ouvert, page traduite chargee", pg.evaluate("() => !dlgLec.hidden") and a["nw"] > 0, a["nw"])
            sous = pg.evaluate("() => $('dllSous').textContent")
            check("A. sous-titre au nom du personnage", a["qui"].lower()[:4] in sous.lower() or "narrateur" in sous.lower(), sous[:80])
            check("A. audio lance", pg.evaluate("() => decodeURIComponent(DLL.audio.src).includes('/dialogues/voix/') && !DLL.audio.paused"))
            coul = pg.evaluate("() => dllCouleur(DLL.liste[DLL.i].qui)")
            check("B. halo couleur du personnage", a["trait"] == coul, (a["trait"], coul))
            check("B. halo sur la bulle (±4 px)", a["ecart"] <= 4 and a["svg_sur_img"], a)
            check("B. voile de page", a["voile"])
            check("B. cadre dans la scene, pas de debordement", a["cadre_ok"] and not a["deborde"], a)
            pg.screenshot(path=os.path.join(OUT, "dlg_lecteur_%d.png" % w))
            i0 = pg.evaluate("() => DLL.i")
            for _ in range(12):
                pg.wait_for_timeout(1000)
                if pg.evaluate("() => DLL.i") > i0: break
            check("C. replique suivante seule a la fin de la voix", pg.evaluate("() => DLL.i") > i0, pg.evaluate("() => DLL.i"))
            a2 = pg.evaluate(ALIGNE)
            check("C. halo re-aligne sur la nouvelle bulle", a2["ecart"] <= 4, a2["ecart"])
            pg.evaluate("() => $('dllSuiv').click()"); pg.wait_for_timeout(1200)
            j = pg.evaluate("() => DLL.i"); pg.evaluate("() => $('dllPrec').click()"); pg.wait_for_timeout(800)
            check("C. ⏭ puis ⏮", pg.evaluate("() => DLL.i") == j - 1, (j, pg.evaluate("() => DLL.i")))
            pg.evaluate("() => $('dllJouer').click()"); pg.wait_for_timeout(500)
            check("C. pause", pg.evaluate("() => DLL.audio.paused && DLL.pause"))
            check("D. 0 erreur JS", not errs, errs[:3])
            ctx.close()
        b.close()
finally:
    srv.kill()
    try:
        os.remove(os.path.expanduser(r"~\Documents\ComfyUI\_studio_llm_proxy_8191.py"))
    except OSError:
        pass
print("\n%d OK, %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
