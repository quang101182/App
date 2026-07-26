# -*- coding: utf-8 -*-
"""Monte une planche de DEMO peuplee, et en capture l'app (PC + mobile).

But : montrer a quoi ressemble Manga Studio, sans que Quang ait a cliquer.
La planche reste dans la base : elle lui sert de bac a sable quand il ouvre l'app.

Reutilise les images deja produites par le banc de phase 4 — on ne regenere rien.

Usage: python make_demo_page.py [--no-shots]
"""
import argparse
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
PROJ_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
APP_URL = "http://127.0.0.1:8190/manga"
SLUG = "banc-phase4"
SHOTS = os.path.join(PROJ_DIR, "output", "_demo")

# Un mini-recit, pour que la planche se LISE au lieu d'aligner six images.
# alterne ambiance / dialogue, comme la regle des deux types de cases l'impose.
SCENARIO = [
    ("Salle 2-B. Personne.", "oval",    0.30, 0.14, 0.46),
    ("Elle est vraiment partie…", "oval", 0.62, 0.16, 0.50),
    ("Je n'ai pas su lui dire.", "thought", 0.36, 0.20, 0.48),
    ("Trois ans, et pas un mot.", "oval", 0.60, 0.15, 0.52),
    ("", None, 0, 0, 0),
    ("Demain, je lui dis.", "oval",     0.50, 0.78, 0.54),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-shots", action="store_true")
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright

    secret = open(SECRET_FILE, encoding="utf-8").read().strip()
    outdir = os.path.join(PROJ_DIR, "output", SLUG)
    srcs = sorted(f for f in os.listdir(outdir)
                  if f.endswith(".png") and not f.startswith("_")
                  and not f.endswith(("_fond.png", "_depth.png")))
    if len(srcs) < 6:
        print("ECHEC: il faut 6 cases dans output/%s (trouve %d)" % (SLUG, len(srcs)))
        return 2
    os.makedirs(SHOTS, exist_ok=True)

    bubbles = []
    for i, (txt, shape, bx, by, bw) in enumerate(SCENARIO):
        bubbles.append([] if not shape else [{
            "id": "demo%d" % i, "shape": shape, "x": bx, "y": by, "w": bw, "h": 0.12,
            "text": txt, "size": 0.040, "bold": False,
            "tail": {"x": max(0.05, bx - 0.18), "y": min(0.95, by + 0.24)},
        }])

    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=True)
        pg = br.new_page(viewport={"width": 1500, "height": 1200})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_selector("#selProj", timeout=15000)
        pg.wait_for_timeout(1200)

        page_id = pg.evaluate("""async ([srcs, bubs]) => {
            const k = localStorage.getItem('manga_key');
            const H = {'Content-Type':'application/json', Authorization:'Bearer '+k};
            const P = (u,b) => fetch(location.origin+u,{method:'POST',headers:H,body:JSON.stringify(b)}).then(r=>r.json());
            const projs = await (await fetch(location.origin+'/manga/projects',{headers:H})).json();
            const proj = projs.items.find(p => p.slug === 'banc-phase4');
            // une seule planche de demo : on remplace celle d'avant plutot que d'empiler
            const pages = await (await fetch(location.origin+'/manga/pages?project='+proj.id,{headers:H})).json();
            for (const old of pages.items.filter(x => x.title === 'Démonstration'))
                await P('/manga/pages', {delete: old.id});
            const pgr = await P('/manga/pages', {projectId: proj.id, chapter:'1', idx:0,
                title:'Démonstration', layout:{cols:2},
                master:{decor:'empty school classroom, wooden desks in rows, large windows'}});
            const kinds = ['ambiance','dialogue','ambiance','dialogue','ambiance','dialogue'];
            for (let i = 0; i < 6; i++)
                await P('/manga/panels', {pageId: pgr.id, idx:i, kind:kinds[i],
                    prompt:'case '+(i+1), file:'banc-phase4/'+srcs[i], bubbles: bubs[i],
                    verdict: i===1 ? 'ok' : (i===4 ? 'ko' : ''),
                    recipe:{seed:80000+i, ckpt:'waiIllustriousSDXL_v170.safetensors',
                            lora:'zqmg1rl_v1', loraW:0.8, steps:30, cfg:5.5}});
            localStorage.setItem('manga_proj', proj.id);
            localStorage.setItem('manga_page', pgr.id);
            return pgr.id; }""", [srcs[:6], bubbles])
        print("planche de demo : %s (6 cases, %d bulles)"
              % (page_id, sum(len(b) for b in bubbles)))

        if args.no_shots:
            br.close(); return 0

        # --- captures PC ---
        pg.reload(wait_until="domcontentloaded")
        pg.wait_for_selector(".panel img", timeout=20000)
        pg.wait_for_timeout(2500)
        pg.evaluate("() => window.scrollTo(0, 260)")
        pg.wait_for_timeout(400)
        pg.screenshot(path=os.path.join(SHOTS, "1_planche_pc.png"))
        print("  capture PC : planche")

        pg.click('nav button[data-tab="tProj"]'); pg.wait_for_timeout(900)
        pg.screenshot(path=os.path.join(SHOTS, "3_recette_pc.png"))
        print("  capture PC : projet + recette")

        pg.click('nav button[data-tab="tGal"]'); pg.wait_for_timeout(2500)
        pg.screenshot(path=os.path.join(SHOTS, "4_galerie_pc.png"))
        print("  capture PC : galerie")
        br.close()

        # --- capture MOBILE (360 px = largeur du Honor) ---
        br = pw.chromium.launch(headless=True)
        m = br.new_page(viewport={"width": 360, "height": 800},
                        device_scale_factor=2, is_mobile=True, has_touch=True)
        m.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        m.wait_for_selector(".panel img", timeout=20000)
        m.wait_for_timeout(2500)
        m.evaluate("() => window.scrollTo(0, 300)")
        m.wait_for_timeout(400)
        m.screenshot(path=os.path.join(SHOTS, "2_planche_mobile.png"))
        print("  capture MOBILE 360px : planche")
        br.close()

    if errs:
        print("ERREURS JS : %s" % errs)
        return 1
    print("captures -> %s" % SHOTS)
    return 0


if __name__ == "__main__":
    sys.exit(main())
