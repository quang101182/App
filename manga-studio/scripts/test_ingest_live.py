# -*- coding: utf-8 -*-
"""Banc INGESTION : une vraie page de Quang devient une planche relettrable.

C'est le chemin complet du mode traduction :
    page japonaise -> YOLO (cases + bulles) -> Pixtral (OCR + traduction 2 passes)
    -> planche dans l'app, une case par cadre, une bulle FRANCAISE posee LA OU
       elle a ete trouvee.

Ce qui est verifie, et pourquoi :
  - les cases sont decoupees ET servies (une case sans fichier lisible est inutile) ;
  - chaque bulle est rattachee a la bonne case et porte du francais ;
  - les bulles atterrissent DANS leur case (coordonnees entre 0 et 1) — une bulle
    a 1,4 serait hors cadre, invisible, et le relettrage serait a refaire a la main ;
  - le tout survit a un rechargement, et s'exporte.

Usage: python test_ingest_live.py [--page <chemin>] [--headed]
"""
import argparse
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
PROJ_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
APP_URL = "http://127.0.0.1:8190/manga"
DEFAUT = r"D:\Download\02-Apps-Web\01-Term_mob_files_send\Screenshot_2.png"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", default=DEFAUT)
    ap.add_argument("--headed", action="store_true")
    args = ap.parse_args()
    if not os.path.isfile(args.page):
        print("ECHEC: page introuvable : %s" % args.page)
        return 2

    from playwright.sync_api import sync_playwright
    secret = open(SECRET_FILE, encoding="utf-8").read().strip()
    js_errors = []

    print("=== BANC INGESTION ===")
    print("page : %s" % os.path.basename(args.page))

    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=not args.headed)
        pg = br.new_page(viewport={"width": 1500, "height": 1100})
        pg.on("pageerror", lambda e: js_errors.append(str(e)))
        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_selector("#selProj", timeout=15000)
        pg.wait_for_timeout(1200)

        print("\n[1] analyse de la page (détection + traduction)")
        pg.click('nav button[data-tab="tIng"]')
        pg.wait_for_timeout(400)
        pg.set_input_files("#ingFile", args.page)
        pg.check("#ingTrad")
        pg.click("#btnIngest")
        try:
            pg.wait_for_selector("#ingResCard:not([hidden])", timeout=600000)
            pg.wait_for_function(
                "() => !document.getElementById('ingState').textContent.includes('…')",
                timeout=600000)
        except Exception:
            print("    ECHEC : %s" % pg.text_content("#ingState"))
            print("    journal :", pg.evaluate("() => MangaLog.dump(12).map(l=>l.msg)"))
            br.close(); return 1
        etat = pg.text_content("#ingState")
        vignettes = pg.eval_on_selector_all("#ingRes img", "e => e.length")
        chargees = pg.eval_on_selector_all("#ingRes img", "e => e.filter(i=>i.naturalWidth>0).length")
        print("    %s · %d vignette(s), %d chargée(s)" % (etat, vignettes, chargees))

        print("[2] création de la planche")
        pg.click("#btnIngCreate")
        pg.wait_for_selector(".panel", timeout=30000)
        pg.wait_for_timeout(2500)

        print("[3] rechargement complet")
        pg.reload(wait_until="domcontentloaded")
        pg.wait_for_selector(".panel img", timeout=25000)
        pg.wait_for_timeout(2500)

        etat_final = pg.evaluate("""async () => {
            const k = localStorage.getItem('manga_key');
            const r = await fetch(location.origin+'/manga/panels?page='+localStorage.getItem('manga_page'),
                {headers:{Authorization:'Bearer '+k}});
            const items = (await r.json()).items;
            const imgs = [...document.querySelectorAll('.panel img')];
            return {
              cases: items.length,
              casesAvecFichier: items.filter(p => p.file).length,
              imagesChargees: imgs.filter(i => i.naturalWidth > 0).length,
              bulles: items.reduce((n,p) => n + (p.bubbles||[]).length, 0),
              bullesAvecTexte: items.reduce((n,p) => n + (p.bubbles||[]).filter(b => (b.text||'').trim()).length, 0),
              horsCadre: items.reduce((n,p) => n + (p.bubbles||[]).filter(
                  b => b.x < 0 || b.x > 1 || b.y < 0 || b.y > 1).length, 0),
              rendues: document.querySelectorAll('g.bub').length,
              // Le japonais s'ecrit verticalement : sa boite est en portrait. Reprise
              // telle quelle, elle donne du francais a un mot par ligne. On EXIGE donc
              // des bulles en paysage, et au moins 2 mots par ligne en moyenne.
              enPortrait: items.reduce((n,p) => n + (p.bubbles||[]).filter(b => b.w <= b.h).length, 0),
              motsParLigne: (() => {
                const g = [...document.querySelectorAll('g.bub')];
                if (!g.length) return 0;
                let mots = 0, lignes = 0;
                g.forEach(x => { const sp = x.querySelectorAll('tspan');
                  lignes += sp.length;
                  sp.forEach(s => { mots += (s.textContent.trim().split(/\s+/).filter(Boolean)).length; }); });
                return lignes ? +(mots/lignes).toFixed(2) : 0; })(),
              titre: document.getElementById('selPage').selectedOptions[0]?.text,
              extraits: items.flatMap(p => (p.bubbles||[]).map(b => b.text)).filter(Boolean).slice(0,6)
            }; }""")

        # [4] Export : la planche remontee doit retrouver la GEOMETRIE de la page
        # d'origine. Une grille de cases n'est pas une page relettree.
        print("[4] export de la planche remontée")
        export_png = os.path.join(PROJ_DIR, "output", "_demo", "8_page_relettree.png")
        try:
            with pg.expect_download(timeout=120000) as dl:
                pg.click("#btnExport")
            dl.value.save_as(export_png)
        except Exception as ex:
            print("    ECHEC export : %s" % ex)
            export_png = None

        shot = os.path.join(PROJ_DIR, "output", "_demo", "7_ingestion.png")
        os.makedirs(os.path.dirname(shot), exist_ok=True)
        pg.evaluate("() => window.scrollTo(0, 340)")
        pg.wait_for_timeout(300)
        pg.screenshot(path=shot)

        # Position ATTENDUE de chaque bulle dans la page exportee, en fractions.
        # C'est ce qui permet de verifier qu'aucune n'a ete recouverte.
        attendues = pg.evaluate("""async () => {
            const k = localStorage.getItem('manga_key');
            const r = await fetch(location.origin+'/manga/panels?page='+localStorage.getItem('manga_page'),
                {headers:{Authorization:'Bearer '+k}});
            const out = [];
            for (const p of (await r.json()).items){
              const bx = p.recipe && p.recipe.box; if (!bx) continue;
              for (const b of (p.bubbles||[]))
                out.push({ x: bx[0] + b.x*bx[2], y: bx[1] + b.y*bx[3],
                           w: Math.max(0.02, b.w*bx[2]*0.5), h: Math.max(0.02, b.h*bx[3]*0.5),
                           t: (b.text||'').slice(0,24) });
            }
            return out; }""")

        app_err = pg.evaluate("() => MangaLog.errors().map(e => e.msg)")
        # on garde la planche : elle sert a regarder le resultat
        br.close()

    e = etat_final
    print("\n================= VERDICT =================")
    print("planche                          : %s" % e["titre"])
    print("cases créées                     : %d (avec fichier : %d)" % (e["cases"], e["casesAvecFichier"]))
    print("images de case réellement servies: %d / %d" % (e["imagesChargees"], e["cases"]))
    print("bulles posées                    : %d (avec texte : %d)" % (e["bulles"], e["bullesAvecTexte"]))
    print("bulles hors cadre                : %d" % e["horsCadre"])
    print("bulles rendues à l'écran         : %d" % e["rendues"])
    print("bulles restées en portrait       : %d  (le japonais est vertical, le français non)" % e["enPortrait"])
    print("mots par ligne (moyenne)         : %.2f  (< 1,6 = texte haché)" % e["motsParLigne"])
    from PIL import Image as _I
    # Chaque bulle est-elle VISIBLE dans l'export ? Une bulle enregistree en base
    # mais recouverte par une case dessinee ensuite passe tous les autres controles.
    visibles = 0
    if export_png and os.path.isfile(export_png):
        ex = _I.open(export_png).convert("L")
        EW, EH = ex.size
        for b in attendues:
            x1 = int(max(0, (b["x"] - b["w"]/2) * EW)); x2 = int(min(EW, (b["x"] + b["w"]/2) * EW))
            y1 = int(max(0, (b["y"] - b["h"]/2) * EH)); y2 = int(min(EH, (b["y"] + b["h"]/2) * EH))
            if x2 - x1 < 4 or y2 - y1 < 4:
                continue
            px = list(ex.crop((x1, y1, x2, y2)).getdata())
            clairs = sum(1 for v in px if v > 200) / len(px)
            sombres = sum(1 for v in px if v < 90) / len(px)
            ok_b = clairs > 0.55 and sombres > 0.01     # aplat blanc PORTANT du texte
            visibles += 1 if ok_b else 0
            print("   bulle %-26s clairs %3.0f%% sombres %4.1f%%  %s"
                  % (b["t"], clairs*100, sombres*100, "visible" if ok_b else "RECOUVERTE"))
    geo_ok = False
    if export_png and os.path.isfile(export_png):
        ew, eh = _I.open(export_png).size
        # rapport de forme de la page source, a 3 % pres
        src_w, src_h = _I.open(args.page).size
        geo_ok = abs((ew/eh) - (src_w/src_h)) / (src_w/src_h) < 0.03
        print("export : %dx%d (page source %dx%d) -> meme format : %s"
              % (ew, eh, src_w, src_h, "oui" if geo_ok else "NON"))
    else:
        print("export : ABSENT")
    print("bulles visibles dans l'export    : %d / %d" % (visibles, len(attendues)))
    print("erreurs JS                       : %d" % len(js_errors))
    print("erreurs journal de l'app         : %d" % len(app_err))
    print("\nquelques répliques :")
    for t in e["extraits"]:
        print("   %s" % t)
    for x in js_errors + app_err:
        print("   ERREUR %s" % x)

    ok = (e["cases"] >= 3 and e["casesAvecFichier"] == e["cases"]
          and e["imagesChargees"] == e["cases"]
          and e["bullesAvecTexte"] >= 3 and e["horsCadre"] == 0
          and e["rendues"] == e["bulles"]
          and e["enPortrait"] == 0 and e["motsParLigne"] >= 1.6 and geo_ok
          and visibles == len(attendues)
          and not js_errors and not app_err)
    print("\n%s" % ("*** INGESTION : PAGE REELLE DEVENUE PLANCHE RELETTRABLE ***" if ok
                    else "*** INGESTION : NON ATTEINT ***"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
