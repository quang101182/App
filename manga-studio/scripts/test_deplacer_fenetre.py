# -*- coding: utf-8 -*-
"""Banc (25/09/2026, question Quang : « si je DEPLACE la fenetre pendant une capture ? ») : le meme chapitre capture deux fois
dans la fenetre de capture -- R = reference, rien ne bouge ; D = la fenetre est DEPLACEE toutes les 2 s pendant toute la capture
(position seulement, jamais la taille). Verdict : memes fichiers octet pour octet. La fenetre est remise a sa place exacte.
Dossiers TEMPORAIRES (jamais la bibliotheque). Usage : python test_deplacer_fenetre.py <port CDP> <adresse> <n°>
"""
import hashlib, json, os, shutil, subprocess, sys, tempfile, threading, time, urllib.request
from urllib.parse import quote
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cdp_mini

PORT, URL, NUM = sys.argv[1], sys.argv[2], sys.argv[3]
PY = os.path.join(os.environ["LOCALAPPDATA"], "manga-fetch", "venv", "Scripts", "python.exe")
MF = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "manga-fetch", "manga_fetch.py")


def empreintes(d):
    return {os.path.relpath(os.path.join(r, f), d): hashlib.sha1(open(os.path.join(r, f), "rb").read()).hexdigest()
            for r, _, fs in os.walk(d) for f in fs if f != "manifest.json"}


def capturer(dest, bouger):
    t = json.load(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:%s/json/new?%s" % (PORT, quote(URL, safe="")), method="PUT")))
    time.sleep(8)
    nav = json.load(urllib.request.urlopen("http://127.0.0.1:%s/json/version" % PORT))["webSocketDebuggerUrl"]
    arret, mesures = threading.Event(), []
    with cdp_mini.Onglet(nav) as b:
        wid = b.cmd("Browser.getWindowForTarget", targetId=t["id"])["windowId"]
        b0 = b.cmd("Browser.getWindowBounds", windowId=wid)["bounds"]

        def deplacer():
            k = 0
            while not arret.wait(3 if bouger == "taille" else 2):
                k += 1
                if bouger == "taille":           # v2 (Quang 21h52) : REDIMENSIONNER sur le meme ecran, jamais sous la taille sure
                    w, h = (b0["width"] - 150, b0["height"] - 150) if k % 2 else (b0["width"], b0["height"])
                    b.cmd("Browser.setWindowBounds", windowId=wid, bounds={"width": max(w, 700), "height": max(h, 900)})
                    mesures.append(("taille", w, h)); continue
                dx, dy = (60, 0) if k % 4 == 1 else (60, 40) if k % 4 == 2 else (0, 40) if k % 4 == 3 else (0, 0)
                b.cmd("Browser.setWindowBounds", windowId=wid, bounds={"left": b0["left"] + dx, "top": b0["top"] + dy})
                bb = b.cmd("Browser.getWindowBounds", windowId=wid)["bounds"]
                mesures.append((bb["width"], bb["height"]))
        th = threading.Thread(target=deplacer, daemon=True)
        if bouger: th.start()
        t0 = time.time()
        r = subprocess.run([PY, MF, "capture", "--tab", t["url"], "--title", "banc deplacer", "--chapter", NUM, "--page-1", "--force",
                            "--out", dest], capture_output=True, text=True, encoding="utf-8", errors="replace",
                           env=dict(os.environ, PYTHONIOENCODING="utf-8", MANGA_CAPTURE_PORT=PORT), timeout=3600)
        dt = time.time() - t0
        arret.set(); th.join(5) if bouger else None
        b.cmd("Browser.setWindowBounds", windowId=wid, bounds={"left": b0["left"], "top": b0["top"],
                                                               "width": b0["width"], "height": b0["height"]})   # remise a sa place
        fin = b.cmd("Browser.getWindowBounds", windowId=wid)["bounds"]
    try: urllib.request.urlopen("http://127.0.0.1:%s/json/close/%s" % (PORT, t["id"]))
    except Exception: pass
    ok = [l for l in r.stdout.splitlines() if "OK :" in l or "ECHEC" in l]
    if not ok:
        print("   [sortie sans OK] code %s :" % r.returncode, " | ".join((r.stdout + r.stderr).strip().splitlines()[-6:])[:600])
    taille_stable = all(m == (b0["width"], b0["height"]) for m in mesures if m[0] != "taille")
    print("   fenetre de depart %dx%d" % (b0["width"], b0["height"]))
    return dt, ok, len(mesures), taille_stable, (fin["left"], fin["top"], fin["width"], fin["height"]) == (b0["left"], b0["top"], b0["width"], b0["height"])


racine = tempfile.mkdtemp(prefix="banc_deplacer_")
try:
    MODE = sys.argv[4] if len(sys.argv) > 4 else "position"          # « position » ou « taille »
    R = os.path.join(racine, "R"); D = os.path.join(racine, "D"); os.makedirs(R); os.makedirs(D)
    tr, okr, _, _, _ = capturer(R, False)
    td, okd, n, stable, remis = capturer(D, MODE)
    er, ed = empreintes(R), empreintes(D)
    print("R (immobile) : %.0f s %s" % (tr, okr))
    print("D (" + ("redimensionnee" if MODE == "taille" else "deplacee") + " %d fois) : %.0f s %s ; taille jamais changee : %s ; remise a sa place : %s" % (n, td, okd, stable, remis))
    ident = er == ed and len(er) > 0
    print("VERDICT : %s (%d fichiers)" % ("IDENTIQUES octet pour octet" if ident else "DIFFERENTS", len(er)))
    sys.exit(0 if ident and n > 5 and stable and remis else 1)
finally:
    shutil.rmtree(racine, ignore_errors=True)
