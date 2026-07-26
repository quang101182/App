# -*- coding: utf-8 -*-
"""Banc PHASE 5 — bulles et lettrage, pilotes dans l'app.

Critere de sortie de la ROADMAP :
    « bulles repositionnables, texte reeditable apres coup, export PNG/PDF ».

Ce banc ne se contente PAS de cliquer et de conclure. Il verifie que la bulle est
REELLEMENT dans le fichier exporte, en comparant la luminosite de la zone de la
bulle entre l'image source et l'export : une bulle est un aplat blanc avec du
texte noir, donc la zone doit s'eclaircir FRANCHEMENT et contenir des pixels
sombres (le texte). Sans cette mesure, un calque silencieusement absent de
l'export passerait pour un succes — c'est exactement le piege du "rendu a deux
chemins" que l'architecture SVG unique cherche a eviter.

Il reutilise les images deja produites par le banc de phase 4 : le sujet du test
est le LETTRAGE, pas la generation (deja validee, et 2 min de GPU par execution).

Usage:
    python test_lettering_live.py [--headed]
"""
import argparse
import io
import os
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
PROJ_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
APP_URL = "http://127.0.0.1:8190/manga"
SLUG = "banc-phase4"
# Réplique ACCENTUÉE à dessein : une police sous-ensemblée sans les accents
# retomberait glyphe par glyphe sur une police de repli, en silence. Sur une app
# française, c'est le genre d'angle mort qui ne se voit qu'une fois livré.
REPLIQUE = "Il n'y a plus personne…\nJe suis arrivée trop tard, ça m'énerve !"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    args = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
        from PIL import Image
    except ImportError as e:
        print("ECHEC: dependance absente (%s)" % e)
        return 2

    secret = open(SECRET_FILE, encoding="utf-8").read().strip()
    outdir = os.path.join(PROJ_DIR, "output", SLUG)
    sources = sorted(f for f in os.listdir(outdir)
                     if f.endswith(".png") and not f.startswith("_")
                     and not f.endswith(("_fond.png", "_depth.png")))
    if len(sources) < 2:
        print("ECHEC: il faut au moins 2 cases dans output/%s (lance test_app_live.py --keep)" % SLUG)
        return 2
    sources = sources[:2]
    print("=== BANC PHASE 5 — bulles et lettrage ===")
    print("cases reutilisees : %s" % ", ".join(sources))

    js_errors = []
    png_path = os.path.join(outdir, "_lettrage_export.png")
    pdf_path = os.path.join(outdir, "_lettrage_export.pdf")
    for f in (png_path, pdf_path):
        if os.path.exists(f):
            os.remove(f)

    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=not args.headed)
        pg = br.new_page(viewport={"width": 1400, "height": 1100})
        pg.on("pageerror", lambda e: js_errors.append(str(e)))
        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_selector("#selProj", timeout=15000)
        pg.wait_for_timeout(1200)

        # --- planche de travail, montee par l'API : le sujet du test est ailleurs.
        print("\n[1] preparation d'une planche a partir des cases existantes")
        page_id = pg.evaluate("""async (srcs) => {
            const k = localStorage.getItem('manga_key');
            const H = {'Content-Type':'application/json', Authorization:'Bearer '+k};
            const P = (u,b) => fetch(location.origin+u,{method:'POST',headers:H,body:JSON.stringify(b)}).then(r=>r.json());
            const projs = await (await fetch(location.origin+'/manga/projects',{headers:H})).json();
            const proj = projs.items.find(p => p.slug === 'banc-phase4');
            const pgr = await P('/manga/pages', {projectId: proj.id, chapter:'5', idx:0,
                                title:'banc lettrage', layout:{cols:2}, master:{}});
            for (let i = 0; i < srcs.length; i++)
                await P('/manga/panels', {pageId: pgr.id, idx:i, kind:'dialogue',
                        prompt:'case de test', file: 'banc-phase4/'+srcs[i], bubbles: []});
            localStorage.setItem('manga_proj', proj.id);
            localStorage.setItem('manga_page', pgr.id);
            return pgr.id; }""", sources)
        pg.reload(wait_until="domcontentloaded")
        pg.wait_for_selector(".panel img", timeout=15000)
        pg.wait_for_timeout(1500)
        n = pg.eval_on_selector_all(".panel", "e => e.length")
        print("    OK planche %s, %d cases" % (page_id, n))

        # --- 2. poser une bulle -----------------------------------------
        print("[2] pose d'une bulle sur la case 1")
        card = pg.query_selector_all(".panel")[0]
        card.query_selector('[data-act="letter"]').click()
        pg.wait_for_timeout(500)
        card = pg.query_selector_all(".panel")[0]
        card.query_selector('[data-act="addbub"]').click()
        pg.wait_for_timeout(700)
        nb = pg.eval_on_selector_all(".panel:first-child g.bub", "e => e.length")
        print("    bulles dans le calque : %d" % nb)

        card = pg.query_selector_all(".panel")[0]
        ta = card.query_selector("[data-btext]")
        ta.fill(REPLIQUE)
        ta.dispatch_event("input")
        ta.dispatch_event("change")
        pg.wait_for_timeout(800)
        lignes = pg.eval_on_selector_all(".panel:first-child g.bub tspan", "e => e.length")
        print("    texte renvoye a la ligne en %d ligne(s)" % lignes)

        # Le texte tient-il DANS la bulle ? Mesure geometrique, pas coup d'oeil.
        # Ce controle manquait au 1er jet : les repliques debordaient de l'ellipse
        # alors que tous les autres chiffres etaient verts.
        debord = pg.evaluate("""() => {
            const g = document.querySelector('.panel g.bub');
            const sh = g.querySelector('ellipse.shape, rect.shape, polygon.shape');
            const tx = g.querySelector('text');
            if (!sh || !tx) return null;
            const a = sh.getBBox(), b = tx.getBBox();
            return { gauche: +(a.x - b.x).toFixed(1),
                     droite: +((b.x + b.width) - (a.x + a.width)).toFixed(1),
                     haut:   +(a.y - b.y).toFixed(1),
                     bas:    +((b.y + b.height) - (a.y + a.height)).toFixed(1) }; }""")
        tient = debord and max(debord.values()) <= 0
        print("    texte contenu dans la bulle : %s  (debords %s)"
              % ("oui" if tient else "NON", debord))

        card.query_selector('[data-act="tail"]').click()
        pg.wait_for_timeout(600)
        a_queue = pg.eval_on_selector_all(".panel:first-child g.bub path.tail", "e => e.length")
        print("    queue posee : %s" % ("oui" if a_queue else "NON"))

        # --- 3. deplacer (le critere dit "repositionnables") -------------
        print("[3] deplacement de la bulle")
        avant = pg.evaluate("""async () => {
            const k = localStorage.getItem('manga_key');
            const r = await fetch(location.origin+'/manga/panels?page='+localStorage.getItem('manga_page'),
                {headers:{Authorization:'Bearer '+k}});
            const it = (await r.json()).items;
            return it[0].bubbles[0]; }""")
        box = pg.query_selector(".panel:first-child g.bub").bounding_box()
        pg.mouse.move(box["x"] + box["width"]/2, box["y"] + box["height"]/2)
        pg.mouse.down()
        pg.mouse.move(box["x"] + box["width"]/2 + 60, box["y"] + box["height"]/2 + 150, steps=12)
        pg.mouse.up()
        pg.wait_for_timeout(900)
        apres = pg.evaluate("""async () => {
            const k = localStorage.getItem('manga_key');
            const r = await fetch(location.origin+'/manga/panels?page='+localStorage.getItem('manga_page'),
                {headers:{Authorization:'Bearer '+k}});
            const it = (await r.json()).items;
            return it[0].bubbles[0]; }""")
        bouge = abs(apres["x"] - avant["x"]) > 0.01 or abs(apres["y"] - avant["y"]) > 0.01
        print("    position %.3f,%.3f -> %.3f,%.3f  %s"
              % (avant["x"], avant["y"], apres["x"], apres["y"],
                 "DEPLACEE et enregistree" if bouge else "PAS BOUGE"))

        # --- 4. rechargement : le texte survit-il ? ----------------------
        print("[4] rechargement complet (le texte doit etre reeditable apres coup)")
        pg.reload(wait_until="domcontentloaded")
        pg.wait_for_selector(".panel img", timeout=15000)
        pg.wait_for_timeout(1500)
        pg.query_selector_all(".panel")[0].query_selector('[data-act="letter"]').click()
        pg.wait_for_timeout(600)
        survecu = pg.evaluate("""() => {
            const t = document.querySelector('.panel g.bub text');
            return t ? [...t.querySelectorAll('tspan')].map(s=>s.textContent).join('\\n') : null; }""")
        ok_txt = (survecu or "").replace("\n", " ").startswith("Il n'y a plus personne")
        print("    texte relu apres rechargement : %s" % (repr(survecu)[:70]))

        # --- 4-bis. preuve visuelle -------------------------------------
        # Un verdict chiffre ne dit pas si l'ecran est REGARDABLE. Le voile de
        # generation est reste affiche sur chaque case pendant toute la v1.0.1
        # sans qu'aucun chiffre ne s'en apercoive.
        shot = os.path.join(outdir, "_lettrage_ecran.png")
        pg.screenshot(path=shot, full_page=False)
        print("[4-bis] capture de l'ecran -> %s" % os.path.basename(shot))

        # --- 5. exports --------------------------------------------------
        print("[5] exports")
        with pg.expect_download(timeout=90000) as d1:
            pg.click("#btnExport")
        d1.value.save_as(png_path)
        with pg.expect_download(timeout=90000) as d2:
            pg.click("#btnExportPdf")
        d2.value.save_as(pdf_path)
        print("    PNG %d octets · PDF %d octets"
              % (os.path.getsize(png_path), os.path.getsize(pdf_path)))

        app_err = pg.evaluate("() => MangaLog.errors().map(e => e.msg)")
        bub = pg.evaluate("""async () => {
            const k = localStorage.getItem('manga_key');
            const r = await fetch(location.origin+'/manga/panels?page='+localStorage.getItem('manga_page'),
                {headers:{Authorization:'Bearer '+k}});
            return (await r.json()).items[0].bubbles[0]; }""")
        pg.evaluate("""async () => {
            const k = localStorage.getItem('manga_key');
            await fetch(location.origin+'/manga/pages',{method:'POST',
                headers:{'Content-Type':'application/json',Authorization:'Bearer '+k},
                body: JSON.stringify({delete: localStorage.getItem('manga_page')})}); }""")
        br.close()

    # ===== LA MESURE QUI COMPTE : la bulle est-elle DANS le fichier ? =====
    src = Image.open(os.path.join(outdir, sources[0])).convert("L")
    exp = Image.open(png_path).convert("L")
    pad, gut = 36, 24
    cw, ch = src.size
    # zone de la bulle dans la case 1, en coordonnees de l'export
    bx, by = bub["x"] * cw, bub["y"] * ch
    bw, bh = bub["w"] * cw * 0.7, bub["h"] * ch * 0.7   # coeur de la bulle, sans les bords
    box_src = (int(bx-bw/2), int(by-bh/2), int(bx+bw/2), int(by+bh/2))
    box_exp = (box_src[0]+pad, box_src[1]+pad, box_src[2]+pad, box_src[3]+pad)
    z_src, z_exp = src.crop(box_src), exp.crop(box_exp)
    m_src = sum(z_src.getdata()) / (z_src.width * z_src.height)
    px = list(z_exp.getdata())
    m_exp = sum(px) / len(px)
    clairs = sum(1 for v in px if v > 200) / len(px)
    sombres = sum(1 for v in px if v < 80) / len(px)

    pdf_ok = False
    if os.path.isfile(pdf_path):
        head = open(pdf_path, "rb").read(9)
        tail = open(pdf_path, "rb").read()[-400:]
        pdf_ok = head.startswith(b"%PDF-1.4") and b"%%EOF" in tail and os.path.getsize(pdf_path) > 20000

    print("\n================= VERDICT =================")
    print("bulle dans le calque a l'ecran     : %d" % nb)
    print("texte renvoye a la ligne           : %d ligne(s)" % lignes)
    print("queue posee                        : %s" % ("oui" if a_queue else "NON"))
    print("texte contenu dans la bulle        : %s" % ("oui" if tient else "NON"))
    print("repositionnable (et enregistre)    : %s" % ("oui" if bouge else "NON"))
    print("texte survit au rechargement       : %s" % ("oui" if ok_txt else "NON"))
    print("--- la bulle est-elle DANS l'export ? (mesure pixels) ---")
    print("luminosite zone, source            : %.1f / 255" % m_src)
    print("luminosite zone, export            : %.1f / 255" % m_exp)
    print("pixels clairs (aplat de la bulle)  : %.0f %%" % (clairs*100))
    print("pixels sombres (le texte)          : %.1f %%" % (sombres*100))
    print("export PDF valide                  : %s (%d Ko)"
          % ("oui" if pdf_ok else "NON", os.path.getsize(pdf_path)//1024 if os.path.isfile(pdf_path) else 0))
    print("erreurs JS                         : %d" % len(js_errors))
    print("erreurs journal de l'app           : %d" % len(app_err))
    for e in js_errors + app_err:
        print("   %s" % e)

    # Une bulle = un aplat blanc (>70 % de pixels clairs) PORTANT du texte (>1 % de sombres).
    # Les deux conditions ensemble : un aplat sans texte serait un calque muet,
    # du texte sans aplat serait une bulle qui n'a pas ete dessinee.
    bulle_dans_export = clairs > 0.70 and sombres > 0.01
    ok = (nb == 1 and lignes >= 2 and a_queue and bouge and ok_txt and tient
          and bulle_dans_export and pdf_ok and not js_errors and not app_err)
    print("\n%s" % ("*** PHASE 5 : CRITERE DE SORTIE ATTEINT ***" if ok
                    else "*** PHASE 5 : NON ATTEINT ***"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
