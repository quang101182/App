# -*- coding: utf-8 -*-
"""BANC (24/09/2026, question Quang : « quelle est la taille minimale de la fenetre pour que ca fonctionne ? »).

Capture le MEME chapitre MangaDex (OPM ch.301 depuis la page 3 : 18 pages attendues) dans la fenetre dediee, a
plusieurs tailles de fenetre (bords compris), vers un dossier TEMPORAIRE (jamais sources/). La fenetre est remise a sa
position/taille d'origine a la fin. 0 $ (aucun service payant).
Usage : python banc_taille_fenetre.py 900x1000 516x600 516x400 ...
"""
import json, os, shutil, subprocess, sys, tempfile, time, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from cdp_mini import Onglet

CDP = "http://127.0.0.1:9223"
URL = "https://mangadex.org/chapter/30f3755a-7dcf-4594-964d-58e2c9e93716/3"
ATTENDU = 18


def onglet():
    l = json.load(urllib.request.urlopen(CDP + "/json/list"))
    return [x for x in l if x["type"] == "page" and "mangadex.org" in x["url"]][0]


def navigateur(fn):
    v = json.load(urllib.request.urlopen(CDP + "/json/version"))
    with Onglet(v["webSocketDebuggerUrl"]) as o:
        return fn(o)


p0 = onglet()
wid = navigateur(lambda o: o.cmd("Browser.getWindowForTarget", targetId=p0["id"])["windowId"])
avant = navigateur(lambda o: o.cmd("Browser.getWindowBounds", windowId=wid)["bounds"])
res = []
try:
    for taille in sys.argv[1:]:
        w, h = [int(x) for x in taille.split("x")]
        navigateur(lambda o: o.cmd("Browser.setWindowBounds", windowId=wid, bounds={"left": avant["left"] if w <= 900 else 2400,
                                                                                   "top": 100, "width": w, "height": h}))
        p = onglet()
        with Onglet(p["webSocketDebuggerUrl"]) as o:
            o.cmd("Page.navigate", url=URL)
        time.sleep(8)
        with Onglet(onglet()["webSocketDebuggerUrl"]) as o:
            vp = json.loads(o.cmd("Runtime.evaluate", expression="JSON.stringify([innerWidth, innerHeight])", returnByValue=True)["result"]["value"])
        out = tempfile.mkdtemp(prefix="banc_fen_")
        r = subprocess.run([sys.executable, os.path.join(HERE, "manga_fetch.py"), "capture", "--tab", "30f3755a", "--title",
                            "banc taille fenetre", "--chapter", "301", "--out", out], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=600, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        n = 0
        for racine, _d, fs in os.walk(out):
            n += sum(1 for f in fs if f.startswith("page_"))
        shutil.rmtree(out, ignore_errors=True)
        dern = [l for l in (r.stdout + r.stderr).splitlines() if l.strip()][-1:]
        res.append((taille, vp, n))
        print("fenetre %-9s -> interieur %4dx%-4d : %2d/%d pages %s   %s" % (taille, vp[0], vp[1], n, ATTENDU,
              "OK" if n == ATTENDU else "ECHEC", dern[0][:90] if dern else ""), flush=True)
finally:
    navigateur(lambda o: o.cmd("Browser.setWindowBounds", windowId=wid, bounds={k: avant[k] for k in ("left", "top", "width", "height")}))
    with Onglet(onglet()["webSocketDebuggerUrl"]) as o:
        o.cmd("Page.navigate", url="https://mangadex.org/")
    print("fenetre remise a", navigateur(lambda o: o.cmd("Browser.getWindowBounds", windowId=wid)["bounds"]))
