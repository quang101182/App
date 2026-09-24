# -*- coding: utf-8 -*-
"""Banc v2.13.0 (Quang 24/09 15h11) : la jauge VRAM VENTILEE (couleurs = moteurs de l'app, gris = systeme), app reelle.

Un VRAI processus CUDA (venv du proxy) prend 1,5 Go et se declare « voix » ; un processus factice (qui dort) declare
« cases » 400 Mo. Verifie : GET /manga/vram les voit ; la barre a un segment ORANGE (voix), un JAUNE (cases) et un GRIS
en dernier, largeurs = parts / total ; un toucher ouvre la legende (noms + Go + « Système et autres applis » + « Libre »),
un toucher ailleurs la ferme ; 360 px sans debordement ; quand tout s'arrete, il ne reste que le gris. Aucune ecriture
hors de sources/_gpu/ (nettoye a la fin). Captures : scripts/vram_1280.png, vram_360.png.
"""
import json, os, subprocess, sys, time, urllib.request
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
URL = "http://127.0.0.1:8190/manga/#k=" + KEY
PYV = os.environ.get("MANGA_PY", "D:/Download/02-Apps-Web/kohya-trainer/.venv/Scripts/python.exe")
GPU = os.path.normpath(os.path.join(HERE, "..", "sources", "_gpu"))
CREATE = getattr(subprocess, "CREATE_NO_WINDOW", 0)
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""), flush=True)


def api(chemin):
    return json.load(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8190" + chemin,
                                                                   headers={"Authorization": "Bearer " + KEY}), timeout=30))


voix = subprocess.Popen([PYV, "-c", "import sys; sys.path.insert(0, r'%s'); import torch, time, declaration_gpu as d; "
                         "d.declarer('voix'); x = torch.empty(int(1.5*1024**3), dtype=torch.uint8, device='cuda'); x.fill_(1); "
                         "torch.cuda.synchronize(); time.sleep(90)" % HERE], creationflags=CREATE)
faux = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(90)"], creationflags=CREATE)
ffaux = os.path.join(GPU, "%d.json" % faux.pid)
try:
    os.makedirs(GPU, exist_ok=True)
    for _ in range(40):                                   # chargement de torch + CUDA
        time.sleep(1)
        json.dump({"nom": "cases", "mo": 400, "pid": faux.pid, "t": time.time()}, open(ffaux, "w"))
        try:
            if json.load(open(os.path.join(GPU, "%d.json" % voix.pid))).get("mo"):
                break
        except Exception:
            pass
    time.sleep(5)
    json.dump({"nom": "cases", "mo": 400, "pid": faux.pid, "t": time.time()}, open(ffaux, "w"))
    v = api("/manga/vram")
    parts = {x["cle"]: x["mo"] for x in v.get("parts") or []}
    check("le serveur voit « voix » 1536 Mo et « cases » 400 Mo", parts.get("voix") == 1536 and parts.get("cases") == 400, v.get("parts"))
    check("gris = utilisé - parts", v["systeme"] == v["used"] - sum(parts.values()), (v["used"], v["systeme"]))
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        pg = b.new_page(viewport={"width": 1280, "height": 800}); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(URL); pg.wait_for_timeout(2500)
        json.dump({"nom": "cases", "mo": 400, "pid": faux.pid, "t": time.time()}, open(ffaux, "w"))
        pg.evaluate("() => majVram(true)"); pg.wait_for_timeout(2500)
        segs = pg.evaluate("""() => [...document.querySelectorAll('#vramBar i')].map(i => [getComputedStyle(i).backgroundColor,
                                   parseFloat(i.style.width)])""")
        coul = [c for c, _w in segs]
        check("version affichée = celle du fichier", pg.inner_text("#verBadge") == "v" + __import__("banc_outils").version_app())
        check("segments : orange (voix), jaune (cases), GRIS en dernier",
              coul[:2] == ["rgb(232, 145, 45)", "rgb(250, 204, 21)"] and coul[-1] == "rgb(107, 114, 128)", coul)
        vv = pg.evaluate("() => VRAM")
        attendu = [round(x["mo"] * 100 / vv["total"], 2) for x in vv["parts"]] + [round(vv["systeme"] * 100 / vv["total"], 2)]
        check("largeurs = parts / total", [round(w, 2) for _c, w in segs] == attendu, (segs, attendu))
        pg.click(".vram"); pg.wait_for_timeout(500)
        leg = pg.inner_text("#vramPanel") if pg.is_visible("#vramPanel") else ""
        check("toucher la jauge -> légende : Voix locale, Découpage des cases, Système, Libre",
              all(k in leg for k in ("Voix locale", "1,5 Go", "Découpage des cases", "Système et autres applis", "Libre")), leg[:200])
        pg.screenshot(path=os.path.join(HERE, "vram_1280.png"), clip={"x": 640, "y": 0, "width": 640, "height": 330})
        pg.mouse.click(200, 500); pg.wait_for_timeout(400)
        check("toucher ailleurs -> légende fermée", pg.is_hidden("#vramPanel"))
        pg.set_viewport_size({"width": 360, "height": 800}); pg.wait_for_timeout(600)
        pg.click(".vram"); pg.wait_for_timeout(500)
        r = pg.evaluate("() => { const a = $('vramPanel').getBoundingClientRect(); return [a.left, a.right, document.documentElement.scrollWidth]; }")
        check("360 px : légende dans l'écran, page sans débordement", r[0] >= 0 and r[1] <= 360 and r[2] <= 360, r)
        pg.screenshot(path=os.path.join(HERE, "vram_360.png"))
        pg.keyboard.press("Escape")
        # tout s'arrete -> il ne reste que le gris
        voix.kill(); faux.kill(); voix.wait(); faux.wait()
        time.sleep(6)
        pg.evaluate("() => majVram(true)"); pg.wait_for_timeout(2500)
        coul2 = pg.evaluate("() => [...document.querySelectorAll('#vramBar i')].map(i => getComputedStyle(i).backgroundColor)")
        check("moteurs arrêtés -> seul le gris reste", coul2 == ["rgb(107, 114, 128)"], coul2)
        check("aucune erreur JS", not errs, errs[:2])
        b.close()
finally:
    for x in (voix, faux):
        if x.poll() is None:
            x.kill()
    for f in (ffaux, os.path.join(GPU, "%d.json" % voix.pid)):
        try: os.remove(f)
        except OSError: pass
print("\n%d/%d" % (len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
