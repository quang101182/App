# -*- coding: utf-8 -*-
"""Banc des 5 FORMES de bulle : le texte tient-il dans chacune ?

Pourquoi ce banc existe : le banc de lettrage ne verifiait la contenance que sur
UNE forme (l'ovale). La bulle de pensee dessine une ellipse a 0,86 x 0,82 de sa
boite — le reste etant occupe par les bosses — et le texte debordait donc sur les
bosses. Vert sur tous les chiffres, evident sur la planche exportee.

Une forme non testee est une forme cassee qui s'ignore.

Usage: python test_bubble_shapes.py [--headed]
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

# Un texte assez long pour FORCER plusieurs lignes : une bulle d'un mot tient
# toujours, et ne prouve donc rien.
TXT = "Je n'aurais jamais cru la revoir ici, après tout ce temps."
FORMES = ["oval", "rect", "thought", "burst", "none"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright

    secret = open(SECRET_FILE, encoding="utf-8").read().strip()
    outdir = os.path.join(PROJ_DIR, "output", SLUG)
    srcs = sorted(f for f in os.listdir(outdir)
                  if f.endswith(".png") and not f.startswith("_")
                  and not f.endswith(("_fond.png", "_depth.png")))[:len(FORMES)]
    if len(srcs) < len(FORMES):
        print("ECHEC: il faut %d cases dans output/%s" % (len(FORMES), SLUG))
        return 2

    bubs = [[{"id": "s%d" % i, "shape": f, "x": 0.5, "y": 0.35, "w": 0.62, "h": 0.14,
              "text": TXT, "size": 0.038, "bold": False, "tail": None}]
            for i, f in enumerate(FORMES)]

    js_errors = []
    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=not args.headed)
        pg = br.new_page(viewport={"width": 1500, "height": 1100})
        pg.on("pageerror", lambda e: js_errors.append(str(e)))
        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_selector("#selProj", timeout=15000)
        pg.wait_for_timeout(1200)

        pg.evaluate("""async ([srcs, bubs]) => {
            const k = localStorage.getItem('manga_key');
            const H = {'Content-Type':'application/json', Authorization:'Bearer '+k};
            const P=(u,b)=>fetch(location.origin+u,{method:'POST',headers:H,body:JSON.stringify(b)}).then(r=>r.json());
            const projs = await (await fetch(location.origin+'/manga/projects',{headers:H})).json();
            const proj = projs.items.find(p => p.slug === 'banc-phase4');
            const pgr = await P('/manga/pages',{projectId:proj.id,chapter:'9',idx:0,
                title:'banc formes',layout:{cols:3},master:{}});
            for (let i=0;i<srcs.length;i++)
                await P('/manga/panels',{pageId:pgr.id,idx:i,kind:'dialogue',prompt:'forme',
                    file:'banc-phase4/'+srcs[i], bubbles: bubs[i]});
            localStorage.setItem('manga_proj',proj.id);
            localStorage.setItem('manga_page',pgr.id); }""", [srcs, bubs])
        pg.reload(wait_until="domcontentloaded")
        pg.wait_for_selector(".panel img", timeout=20000)
        pg.wait_for_timeout(2500)

        mesures = pg.evaluate("""() => [...document.querySelectorAll('.panel')].map((p, i) => {
            const g = p.querySelector('g.bub');
            if (!g) return null;
            const tx = g.querySelector('text');
            // la forme de REFERENCE est la 1re dessinee : pour la pensee c'est
            // l'ellipse interieure, celle qui doit contenir le texte.
            const sh = g.querySelector('.core') || g.querySelector('.shape');
            if (!tx) return null;
            const b = tx.getBBox();
            if (!sh) return { forme: 'none', sansForme: true,
                              lignes: tx.querySelectorAll('tspan').length };
            const a = sh.getBBox();
            return { lignes: tx.querySelectorAll('tspan').length,
                     gauche: +(a.x - b.x).toFixed(1),
                     droite: +((b.x+b.width) - (a.x+a.width)).toFixed(1),
                     haut:   +(a.y - b.y).toFixed(1),
                     bas:    +((b.y+b.height) - (a.y+a.height)).toFixed(1) }; })""")

        shot = os.path.join(PROJ_DIR, "output", "_demo", "6_formes.png")
        os.makedirs(os.path.dirname(shot), exist_ok=True)
        pg.evaluate("() => window.scrollTo(0, 320)")
        pg.wait_for_timeout(300)
        pg.screenshot(path=shot)

        pg.evaluate("""async () => {
            const k = localStorage.getItem('manga_key');
            await fetch(location.origin+'/manga/pages',{method:'POST',
              headers:{'Content-Type':'application/json',Authorization:'Bearer '+k},
              body: JSON.stringify({delete: localStorage.getItem('manga_page')})}); }""")
        br.close()

    print("=== BANC DES FORMES DE BULLE ===")
    print("texte : %r" % TXT)
    tous_ok = True
    for f, m in zip(FORMES, mesures):
        if m is None:
            print("  %-8s AUCUNE BULLE" % f); tous_ok = False; continue
        if m.get("sansForme"):
            # « recitatif » n'a pas de contour : rien a contenir, on verifie juste
            # qu'il se decoupe en lignes au lieu de sortir en un bloc unique.
            ok = m["lignes"] >= 2
            print("  %-8s %d ligne(s), pas de contour (recitatif)  %s"
                  % (f, m["lignes"], "OK" if ok else "ECHEC"))
            tous_ok = tous_ok and ok
            continue
        marge = max(m["gauche"], m["droite"], m["haut"], m["bas"])
        ok = marge <= 0
        print("  %-8s %d ligne(s)  debord max %+7.1f  %s"
              % (f, m["lignes"], marge, "OK" if ok else "ECHEC  " + str(m)))
        tous_ok = tous_ok and ok

    print("\nerreurs JS : %d" % len(js_errors))
    for e in js_errors:
        print("   %s" % e)
    ok = tous_ok and not js_errors
    print("\n%s" % ("*** LES 5 FORMES CONTIENNENT LEUR TEXTE ***" if ok
                    else "*** AU MOINS UNE FORME DEBORDE ***"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
