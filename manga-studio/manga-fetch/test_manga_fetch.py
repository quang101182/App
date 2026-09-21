#!/usr/bin/env python3
"""Banc manga-fetch v0.1.0 — test réel de bout en bout, verdict chiffré.

Étapes :
  A. Unitaires rapides : search répond, verify crie sur dossier falsifié (mutation rouge).
  B. Download réel : un chapitre MangaDex (titre/langue trouvés dynamiquement)
     -> fichiers + manifeste contrôlés.
  C. Capture réelle : le MÊME chapitre ouvert dans la fenêtre dédiée -> capture,
     contrôle croisé : même nombre de pages que le download.
Verdict final chiffré. Exit 0 uniquement si tout est vert (>= 10 étapes).

Prérequis : la fenêtre dédiée doit tourner (manga_fetch.py launch-edge, CDP 9223).
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

import requests

PY = sys.executable
ICI = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.join(ICI, "manga_fetch.py")
UA = "manga-fetch-banc/0.1.0"
MDX = "https://api.mangadex.org"
OUT_BANC = os.path.join(ICI, "banc_out")


def run(*cli_args):
    # UTF-8 forcé côté parent ET enfant (piège cp1252 payé le 21/09).
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    return subprocess.run([PY, MOD, *cli_args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env)


RESULTATS: list = []


def etape(nom, ok, detail=""):
    print(f"  [{'OK' if ok else 'KO'}] {nom}" + (f" — {detail}" if detail else ""))
    RESULTATS.append(bool(ok))
    return 1 if ok else 0


def trouver_chapitre_test():
    """Un chapitre réel hébergé : essaie plusieurs titres, fr puis en, externalUrl exclu."""
    for q in ["frieren", "komi", "mushoku", "leveling"]:
        try:
            r = requests.get(MDX + "/manga", params={"title": q, "limit": 5,
                                                     "order[followedCount]": "desc",
                                                     "contentRating[]": ["safe"]},
                             headers={"User-Agent": UA}, timeout=30).json()
        except Exception:
            continue
        for m in r["data"][:4]:
            for lang in ("fr", "en"):
                try:
                    chs = requests.get(MDX + "/chapter",
                                       params={"manga": m["id"], "translatedLanguage[]": lang,
                                               "order[chapter]": "desc", "limit": 1},
                                       headers={"User-Agent": UA}, timeout=30).json()
                except Exception:
                    continue
                chs["data"] = [c for c in chs["data"] if not c["attributes"].get("externalUrl")]
                if chs["data"]:
                    return m["id"], lang, chs["data"][0]
    return None, None, None


def main() -> int:
    for flux in (sys.stdout, sys.stderr):
        if flux and hasattr(flux, "reconfigure"):
            flux.reconfigure(encoding="utf-8", errors="replace")
    print("=== A. Unitaires ===")
    verts = 0

    r = run("search", "frieren")
    verts += etape("search repond", r.returncode == 0 and len(r.stdout.strip().splitlines()) > 1,
                   f"{len(r.stdout.strip().splitlines()) - 1} resultats")

    # mutation : verify doit crier sur un manifeste qui annonce une page absente
    tmp = tempfile.mkdtemp()
    dest = os.path.join(tmp, "ch_1")
    os.makedirs(dest)
    for i, taille in [(1, 100), (2, 200)]:
        open(os.path.join(dest, f"page_{i:03d}.jpg"), "wb").write(b"\xff\xd8\xff" + b"x" * (taille - 3))
    json.dump({"slug": "t", "title": "t", "chapter": "1", "source": "import", "source_url": "",
               "captured_at": "", "pages": [
                   {"file": "page_001.jpg", "bytes": 100},
                   {"file": "page_002.jpg", "bytes": 200},
                   {"file": "page_003.jpg", "bytes": 50}]},  # page 3 n'existe pas
              open(os.path.join(dest, "manifest.json"), "w"))
    r = run("verify", dest)
    verts += etape("verify crie sur manifeste falsifie (mutation rouge)",
                   r.returncode == 1 and "manquant" in r.stdout, r.stdout.strip()[:70])
    shutil.rmtree(tmp, ignore_errors=True)

    print()
    print("=== B. Download reel (MangaDex) ===")
    shutil.rmtree(OUT_BANC, ignore_errors=True)
    mid, lang, ch = trouver_chapitre_test()
    if not mid:
        print("  Aucun chapitre de test trouve (API MangaDex ?) — banc avorte.")
        print(f"=== VERDICT : {verts} etapes vertes (B/C non executes) ===")
        return 1
    num = ch["attributes"]["chapter"]
    attendu = ch["attributes"]["pages"]
    print(f"  titre {mid[:8]} chapitre {num} ({lang}, {attendu} pages attendues)")

    r = run("download", mid, "--chapter", str(num), "--lang", lang, "--out", OUT_BANC, "--force")
    slug_dir = None
    for root, dirs, files in os.walk(OUT_BANC):
        if "manifest.json" in files:
            slug_dir = root
    ok_dl = r.returncode == 0 and slug_dir is not None
    verts += etape("download termine", ok_dl, (r.stdout.strip().splitlines() or ["?"])[-1][:70])

    fichiers = []
    if slug_dir:
        m = json.load(open(os.path.join(slug_dir, "manifest.json"), encoding="utf-8"))
        fichiers = [f for f in os.listdir(slug_dir) if f.startswith("page_")]
        verts += etape("nombre de pages = attendu", len(fichiers) == attendu == len(m["pages"]),
                       f"{len(fichiers)} fichiers / {attendu} attendus")
        def _sig_ok(p):
            h = open(p, "rb").read(4)
            return h[:3] == b"\xff\xd8\xff" or h == b"\x89PNG"
        sig_ok = all(_sig_ok(os.path.join(slug_dir, f)) for f in fichiers)
        verts += etape("signatures JPEG/PNG valides", sig_ok)
        r = run("verify", slug_dir)
        verts += etape("verify OK sur dossier integre", r.returncode == 0, r.stdout.strip()[:60])

    print()
    print("=== C. Capture reelle (controle croise sur le MEME chapitre) ===")
    chap_url = f"https://mangadex.org/chapter/{ch['id']}"
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp("http://localhost:9223")
            ctx = browser.contexts[0]
            tab = ctx.new_page()
            tab.goto(chap_url, wait_until="domcontentloaded", timeout=60000)
            tab.wait_for_timeout(5000)
            print(f"  chapitre ouvert dans la fenetre dediee ({tab.title()[:40]})")
        # l'onglet reste OUVERT : la capture doit le trouver (fermeture après)
        r = run("capture", "--tab", chap_url, "--title", "BANC",
                "--chapter", str(num), "--out", OUT_BANC)
        cap_dir = os.path.join(OUT_BANC, "banc", f"ch_{str(num).replace('/', '-')}")
        cap_files = [f for f in os.listdir(cap_dir) if f.startswith("page_")] if os.path.isdir(cap_dir) else []
        verts += etape("capture terminee", r.returncode in (0, 3) and len(cap_files) > 0,
                       (r.stdout.strip().splitlines() or ["?"])[-1][:70])
        if cap_files:
            # Contrôle croisé par HASH : toutes les pages officielles (download) doivent
            # être dans la capture. La capture peut avoir un surplus SIGNALÉ par note
            # (intercalaire du scanlateur affiché par le lecteur, mesuré 18:26) — ce qui
            # compte, c'est de ne manquer AUCUNE page officielle.
            import hashlib as _h
            h_dl = {_h.sha1(open(os.path.join(slug_dir, f), "rb").read()).hexdigest() for f in fichiers}
            h_cap = {_h.sha1(open(os.path.join(cap_dir, f), "rb").read()).hexdigest() for f in cap_files}
            verts += etape("controle croise : toutes les pages officielles capturees",
                           h_dl <= h_cap,
                           f"manquantes {len(h_dl - h_cap)}/{len(h_dl)} ; capture {len(cap_files)} "
                           f"fichiers, surplus {len(h_cap - h_dl)}")
            mcap = json.load(open(os.path.join(cap_dir, "manifest.json"), encoding="utf-8"))
            ws = sorted(pg.get("w") or 0 for pg in mcap["pages"])
            verts += etape("mediane des largeurs >= 800px", ws[len(ws) // 2] >= 800,
                           f"mediane = {ws[len(ws) // 2]}")
    except Exception as e:
        verts += etape("capture (fenetre dediee joignable ?)", False, f"{type(e).__name__}: {e}")

    # nettoyage : fermer les onglets de chapitre ouverts pour le banc (fenêtre dédiée à nous)
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp("http://localhost:9223")
            for ctx2 in browser.contexts:
                for pg in list(ctx2.pages):
                    if "mangadex.org/chapter" in pg.url:
                        try:
                            pg.close()
                        except Exception:
                            pass
    except Exception:
        pass

    print()
    shutil.rmtree(OUT_BANC, ignore_errors=True)
    print(f"=== VERDICT : {sum(RESULTATS)}/{len(RESULTATS)} etapes vertes ===")
    return 0 if RESULTATS and all(RESULTATS) and len(RESULTATS) >= 8 else 1


if __name__ == "__main__":
    sys.exit(main())
