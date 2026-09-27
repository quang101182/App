# -*- coding: utf-8 -*-
"""Banc v3.4.0 : musique de fond de la serie sous les Dialogues. App REELLE 8190, lecture seule (tout POST intercepte et
enregistre). Lecteur des Dialogues : 🎵 Musique affichee, musique qui joue, plus basse pendant la voix, coupee par
l'interrupteur, arretee a la fermeture ; video : le choix de musique part avec la demande (musique: true, volume).
Usage : python test_musique_dialogues_ui.py <serie/ch_N avec musique et dialogues> [--page f.html]"""
import os, sys, json
from playwright.sync_api import sync_playwright
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
args = sys.argv[1:]
PAGE = None
if "--page" in args:
    i = args.index("--page"); PAGE = open(args[i + 1], encoding="utf-8").read(); del args[i:i + 2]
CH = args[0]
OK, KO = [], []
def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom); print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail)[:160] if detail else ""), flush=True)
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True, args=["--autoplay-policy=no-user-gesture-required"])
    ctx = b.new_context(viewport={"width": 360, "height": 800}, is_mobile=True, has_touch=True, service_workers="block")
    pg = ctx.new_page(); errs, posts = [], []
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("dialog", lambda d: d.dismiss())
    def route(rt):
        u = rt.request.url.split("#")[0].split("?")[0].rstrip("/")
        if rt.request.method != "GET":
            posts.append((u.split("/manga/")[-1], rt.request.post_data or "")); return rt.fulfill(status=200, body='{"ok":true}', content_type="application/json")
        if PAGE and u.endswith("/manga"): return rt.fulfill(status=200, body=PAGE, content_type="text/html; charset=utf-8")
        return rt.continue_()
    pg.route("**/*", route)
    pg.goto("http://127.0.0.1:8190/manga/#k=" + KEY); pg.wait_for_timeout(2500)
    pg.evaluate("s => { localStorage.setItem('manga_onglet','tChap'); localStorage.setItem('manga_serie', s); localStorage.setItem('manga_mus_on','1'); localStorage.setItem('manga_mus_vol','60'); }", CH.split("/")[0])
    pg.reload(); pg.wait_for_timeout(3500)
    print("     version :", pg.evaluate("() => VERSION"))
    pg.evaluate("d => openChap(CHAPS.findIndex(c => c.dir === d))", CH); pg.wait_for_timeout(3500)
    pg.evaluate("() => clOuvrir('dlg')"); pg.wait_for_timeout(2500)
    check("musique de la serie connue (MUS.effectif)", pg.evaluate("() => (MUS.effectif || []).length > 0"), pg.evaluate("() => MUS.effectif"))
    pg.evaluate("() => dlgLecteur()"); pg.wait_for_timeout(4000)
    r = pg.evaluate("() => ({ l: !$('dllMusL').hidden, on: $('dllMus').checked, timer: !!MP.timer, url: !!MP.url })")
    check("lecteur : ligne « 🎵 Musique » presente, activee, moteur demarre", r["l"] and r["on"] and r["timer"] and r["url"], r)
    mesures = []
    for _ in range(40):
        mesures.append(pg.evaluate("() => ({ g: MP.g, parle: !!(DLL.audio.getAttribute('src') && !DLL.audio.paused && !DLL.audio.ended), joue: MP.els.some(x => !x.paused) })"))
        pg.wait_for_timeout(250)
    joue = any(m["joue"] for m in mesures)
    gp = [m["g"] for m in mesures if m["parle"]]; gs = [m["g"] for m in mesures if not m["parle"]]
    check("la musique JOUE sous les Dialogues", joue and max(m["g"] for m in mesures) > 0.01, max(m["g"] for m in mesures))
    base = 60 / 100 * 0.4
    check("pendant la voix, elle est BAISSEE (gain <= 0,45 x la cible + marge)", bool(gp) and min(gp) <= base * 0.45 + 0.02, (round(min(gp) if gp else -1, 3), round(base * 0.45, 3)))
    pg.evaluate("() => { $('dllMus').click(); }"); pg.wait_for_timeout(4000)
    check("interrupteur coupe : la musique s'eteint", pg.evaluate("() => MP.g < 0.01 && !MUS_ON"), pg.evaluate("() => MP.g"))
    check("meme reglage que la narration (lecMusOn suit)", pg.evaluate("() => $('lecMusOn').checked === MUS_ON"))
    pg.evaluate("() => { $('dllMus').click(); }"); pg.wait_for_timeout(300)
    pg.evaluate("() => $('dllFermer').click()"); pg.wait_for_timeout(1200)
    check("fermeture du lecteur : musique arretee", pg.evaluate("() => !MP.timer && MP.els.every(x => x.paused)"))
    posts.clear()
    pg.evaluate("() => { $('dlgVid').dataset.dpl = ''; DLG.plan = Object.assign({}, DLG.plan, { repliques: {} }); $('dlgVid').disabled = false; $('dlgVid').click(); }"); pg.wait_for_timeout(1500)
    env = [json.loads(x[1]) for x in posts if x[0] == "dialogues_lancer"]
    print("     posts :", [(x[0], x[1][:120]) for x in posts][-4:], "| toast :", pg.evaluate("() => (document.querySelector('.toast, #toast') || {}).textContent || ''"))
    check("video : la demande porte la musique (musique: true, volume 60)", bool(env) and env[-1].get("musique") is True and env[-1].get("volume") == 60, env[-1:] or posts[-2:])
    check("0 erreur JS", not errs, errs[:2])
    b.close()
print("\nVERDICT : %d/%d" % (len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
