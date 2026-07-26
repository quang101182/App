# -*- coding: utf-8 -*-
"""Banc PHASE 4 — pilote l'app Manga Studio comme un utilisateur, et MESURE.

Critere de sortie de la ROADMAP :
    « une planche de 6 cases produite de bout en bout dans l'app,
      testee PC et mobile (Samsung reel), 0 erreur JS ».

Ce script couvre le volet PC. Il ne verifie pas "a l'oeil" : il compte.

Il verifie AUSSI la regle posee par Quang le 26/07 — les sorties manga ne
doivent jamais se melanger a celles de Generate Studio. C'est mesure par
difference : le nombre de fichiers a la racine de ComfyUI/output doit etre
STRICTEMENT identique avant et apres, alors qu'on vient de generer 7 images.

Usage:
    python test_app_live.py [--headed] [--keep]
"""
import argparse
import io
import json
import os
import re
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

COMFY_OUT = r"C:\Users\quang\Documents\ComfyUI\output"
SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
PROJ_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
APP_URL = "http://127.0.0.1:8190/manga"

DECOR = ("empty school classroom, wooden desks in rows, large windows on the left, "
         "blackboard at the back, afternoon light from the left, chalk dust")

# 6 cases. Le melange n'est pas decoratif : la phase 2 a mesure que decor fige et
# identite fine sont incompatibles dans une meme case. On teste donc les DEUX chemins.
CASES = [
    ("ambiance", "standing near the door, looking around, full body"),
    ("dialogue", "close-up, surprised expression, looking at viewer"),
    ("ambiance", "sitting at a desk, resting chin on hand, bored, upper body"),
    ("dialogue", "close-up, smiling softly, eyes half closed"),
    ("ambiance", "standing by the window, looking outside, three-quarter view"),
    ("dialogue", "upper body, arms crossed, determined look"),
]


def count_root(path):
    return len([f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--keep", action="store_true", help="ne supprime pas le projet de test")
    args = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ECHEC: playwright absent (pip install playwright)")
        return 2

    secret = open(SECRET_FILE, encoding="utf-8").read().strip()
    slug = "banc-phase4"
    outdir = os.path.join(PROJ_DIR, "output", slug)

    before_root = count_root(COMFY_OUT)
    print("=== BANC PHASE 4 — planche de 6 cases dans l'app ===")
    print("fichiers a la racine de ComfyUI/output AVANT : %d" % before_root)

    js_errors, console_errors = [], []
    t0 = time.time()

    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=not args.headed)
        pg = br.new_page(viewport={"width": 1400, "height": 1000})
        pg.on("pageerror", lambda e: js_errors.append(str(e)))
        pg.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)

        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_selector("#selProj", timeout=15000)
        pg.wait_for_timeout(1500)

        # --- 1. projet -------------------------------------------------
        print("\n[1] creation du projet")
        pg.click('nav button[data-tab="tProj"]')
        pg.fill("#npName", "banc phase4")
        pg.click("#btnNewProj")
        pg.wait_for_timeout(1800)
        # L'etat interne de l'app n'est pas expose globalement : on relit par l'API.
        # Mesurer ce qui est REELLEMENT enregistre, pas ce que l'UI croit afficher.
        projs = pg.evaluate("""async () => {
            const r = await fetch(location.origin + '/manga/projects',
                {headers:{Authorization:'Bearer '+localStorage.getItem('manga_key')}});
            return (await r.json()).items; }""")
        proj = [p for p in projs if p["slug"] == slug]
        if not proj:
            print("    ECHEC: projet '%s' introuvable (slugs vus: %s)"
                  % (slug, [p["slug"] for p in projs]))
            br.close()
            return 1
        print("    OK projet slug=%s" % slug)

        # --- 2. planche ------------------------------------------------
        print("[2] creation de la planche")
        pg.click('nav button[data-tab="tPlate"]')
        pg.wait_for_timeout(600)
        pg.click("#btnNewPage")
        pg.wait_for_timeout(1500)
        pg.fill("#pgTitle", "banc 6 cases")
        pg.dispatch_event("#pgTitle", "change")
        pg.wait_for_timeout(500)

        # --- 3. fond maitre --------------------------------------------
        print("[3] fond maitre (decor + carte de profondeur) — peut prendre ~60 s")
        pg.fill("#mstPrompt", DECOR)
        pg.click("#btnMaster")
        try:
            pg.wait_for_function(
                "() => document.getElementById('mstState').textContent.includes('prêt')",
                timeout=240000)
            print("    OK fond maitre pret (%.0fs)" % (time.time() - t0))
        except Exception:
            print("    ECHEC fond maitre — etat: %s"
                  % pg.text_content("#mstState"))
            print("    journal:", pg.evaluate("() => MangaLog.dump(15).map(l=>l.msg)"))
            br.close()
            return 1

        # --- 4. les 6 cases ---------------------------------------------
        print("[4] ajout des 6 cases")
        for kind, prompt in CASES:
            pg.click("#btnAddPanel")
            pg.wait_for_timeout(400)
        n = pg.eval_on_selector_all(".panel", "els => els.length")
        if n != 6:
            print("    ECHEC: %d cases creees au lieu de 6" % n)
            br.close()
            return 1
        for i, (kind, prompt) in enumerate(CASES):
            card = pg.query_selector_all(".panel")[i]
            card.query_selector("[data-kind]").select_option(kind)
            card.query_selector("[data-prompt]").fill(prompt)
            card.query_selector("[data-prompt]").dispatch_event("change")
            pg.wait_for_timeout(250)
        print("    OK 6 cases (%d ambiance / %d dialogue)"
              % (sum(1 for k, _ in CASES if k == "ambiance"),
                 sum(1 for k, _ in CASES if k == "dialogue")))

        # --- 5. generation ----------------------------------------------
        print("[5] generation en serie — compter ~20 s par case")
        pg.click("#btnGenAll")
        try:
            pg.wait_for_function(
                "() => document.querySelectorAll('.panel img').length >= 6",
                timeout=900000)
        except Exception:
            done = pg.eval_on_selector_all(".panel img", "e => e.length")
            print("    ECHEC: %d/6 cases generees" % done)
            print("    journal:", pg.evaluate("() => MangaLog.dump(25).map(l=>l.msg)"))
            br.close()
            return 1
        dur = time.time() - t0
        print("    OK 6/6 cases generees (total %.0fs)" % dur)

        # --- 6. export ---------------------------------------------------
        print("[6] export de la planche")
        with pg.expect_download(timeout=60000) as dl:
            pg.click("#btnExport")
        d = dl.value
        exp = os.path.join(PROJ_DIR, "output", slug, "_planche_export.png")
        d.save_as(exp)
        exp_ok = os.path.isfile(exp) and os.path.getsize(exp) > 50000
        print("    %s export %s (%d octets)"
              % ("OK" if exp_ok else "ECHEC", os.path.basename(exp),
                 os.path.getsize(exp) if os.path.isfile(exp) else 0))

        app_log = pg.evaluate("() => MangaLog.dump(400).map(l => l.cls + '|' + l.msg)")
        if not args.keep:
            pg.evaluate("""async () => {
                const k = localStorage.getItem('manga_key');
                const r = await fetch(location.origin + '/manga/projects',
                    {headers:{Authorization:'Bearer '+k}});
                const p = (await r.json()).items.find(x => x.slug === 'banc-phase4');
                if (p) await fetch(location.origin + '/manga/projects', {method:'POST',
                    headers:{'Content-Type':'application/json',Authorization:'Bearer '+k},
                    body: JSON.stringify({delete: p.id})}); }""")
        br.close()

    # ================= VERDICT CHIFFRE =================
    after_root = count_root(COMFY_OUT)
    files = [f for f in os.listdir(outdir)] if os.path.isdir(outdir) else []
    # On compte les CASES, distinctement du fond maitre et de sa carte de profondeur.
    # Le raccourci "len(pngs)-2" masquait le vrai defaut : les images etaient dans le
    # dossier d'un autre projet, et la soustraction rendait quand meme un nombre.
    pngs = [f for f in files if f.endswith(".png") and not f.startswith("_")]
    cases = [f for f in pngs if not f.endswith(("_fond.png", "_depth.png"))]
    master = [f for f in pngs if f.endswith(("_fond.png", "_depth.png"))]
    manga_leftover = 0
    md = os.path.join(COMFY_OUT, "manga")
    for root, _, fs in os.walk(md):
        manga_leftover += len(fs)
    log_err = [l for l in app_log if l.startswith("e|")]

    print("\n================= VERDICT =================")
    print("cases dans output/%-16s: %d / 6" % (slug, len(cases)))
    print("fond maitre + profondeur           : %d / 2" % len(master))
    print("fichiers du dossier                : %s" % (", ".join(sorted(files)[:10]) or "(vide)"))
    print("export de planche                  : %s" % ("OK" if exp_ok else "ECHEC"))
    print("erreurs JS (pageerror)             : %d" % len(js_errors))
    print("erreurs console                    : %d" % len(console_errors))
    print("erreurs dans le journal de l'app   : %d" % len(log_err))
    print("--- ISOLATION vis-a-vis de Generate Studio ---")
    print("racine ComfyUI/output AVANT        : %d" % before_root)
    print("racine ComfyUI/output APRES        : %d  %s"
          % (after_root, "IDENTIQUE (aucune fuite)" if after_root == before_root
             else "!! %+d FICHIERS ONT FUITE !!" % (after_root - before_root)))
    print("residus dans ComfyUI/output/manga/ : %d %s"
          % (manga_leftover, "(tout a ete deplace)" if manga_leftover == 0 else "!! non recoltes !!"))

    for e in js_errors:
        print("  JS: %s" % e)
    for e in log_err:
        print("  LOG: %s" % e)

    ok = (len(cases) == 6 and len(master) == 2 and exp_ok and not js_errors and not log_err
          and after_root == before_root and manga_leftover == 0)
    print("\n%s" % ("*** PHASE 4 : CRITERE DE SORTIE ATTEINT ***" if ok
                    else "*** PHASE 4 : NON ATTEINT ***"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
