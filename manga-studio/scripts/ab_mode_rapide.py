# -*- coding: utf-8 -*-
"""Preuve A/B du MODE RAPIDE de manga-fetch 0.7.4 (25/09/2026) : le MEME chapitre capture deux fois dans la fenetre de capture,
A = attente fixe d'avant (MANGA_FETCH_RAPIDE=0), B = mode rapide. Dossiers TEMPORAIRES (jamais la bibliotheque).
Verdict : memes fichiers, octet pour octet (empreinte SHA-1 de chaque page, decoupage webtoon compris) + durees.
Usage : python ab_mode_rapide.py <port CDP> <adresse du chapitre> [n° de chapitre]
"""
import hashlib, json, os, shutil, subprocess, sys, tempfile, time, urllib.request
from urllib.parse import quote

PORT, URL = sys.argv[1], sys.argv[2]
NUM = sys.argv[3] if len(sys.argv) > 3 else "1"
PY = os.path.join(os.environ["LOCALAPPDATA"], "manga-fetch", "venv", "Scripts", "python.exe")
MF = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "manga-fetch", "manga_fetch.py")


def empreintes(d):
    out = {}
    for racine, _, fichiers in os.walk(d):
        for f in fichiers:
            if f == "manifest.json":
                continue
            p = os.path.join(racine, f)
            out[os.path.relpath(p, d).replace("\\", "/")] = hashlib.sha1(open(p, "rb").read()).hexdigest()
    return out


def capturer(rapide, dest):
    t = json.load(urllib.request.urlopen(urllib.request.Request(
        "http://127.0.0.1:%s/json/new?%s" % (PORT, quote(URL, safe="")), method="PUT")))    # adresse ENTIERE (les & compris)
    time.sleep(8)
    env = dict(os.environ, MANGA_FETCH_RAPIDE="1" if rapide else "0", PYTHONIOENCODING="utf-8",
               MANGA_CAPTURE_PORT=PORT)
    t0 = time.time()
    r = subprocess.run([PY, MF, "capture", "--tab", t["url"], "--title", "banc ab", "--chapter", NUM, "--page-1", "--force",
                        "--out", dest], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=3600)
    dt = time.time() - t0
    try: urllib.request.urlopen("http://127.0.0.1:%s/json/close/%s" % (PORT, t["id"]))
    except Exception: pass
    lignes = [l for l in r.stdout.splitlines() if any(k in l for k in ("Mode", "OK :", "ECHEC", "Notes", "Webtoon"))]
    return dt, lignes, r.returncode


racine = tempfile.mkdtemp(prefix="banc_ab_")
try:
    res = {}
    for nom, rapide in (("A (attente fixe)", False), ("B (mode rapide)", True)):
        d = os.path.join(racine, nom[0]); os.makedirs(d)
        dt, lignes, code = capturer(rapide, d)
        res[nom] = (dt, empreintes(d), lignes, code)
        print("%s : %.0f s, code %d, %d fichiers" % (nom, dt, code, len(res[nom][1])))
        for l in lignes: print("   ", l[:170])
    (ta, ea, _, _), (tb, eb, _, _) = res.values()
    identiques = ea == eb and len(ea) > 0
    diff = sorted(set(ea) ^ set(eb)) + sorted(k for k in set(ea) & set(eb) if ea[k] != eb[k])
    print("VERDICT : %s ; %d fichiers ; A %.0f s -> B %.0f s (x%.1f)%s" % (
        "IDENTIQUES octet pour octet" if identiques else "DIFFERENTS", len(ea), ta, tb, ta / max(tb, 1),
        "" if identiques else " ; ecarts : %s" % diff[:6]))
    sys.exit(0 if identiques else 1)
finally:
    shutil.rmtree(racine, ignore_errors=True)
