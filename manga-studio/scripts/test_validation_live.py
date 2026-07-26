# -*- coding: utf-8 -*-
"""Banc PHASE 6 — la boucle de validation.

Ce que la phase 6 promet : Quang note ✅/❌, et le valide alimente (a) une
bibliotheque de recettes rejouables, (b) le dataset du LoRA suivant.
Et surtout : **l'app propose, elle n'impose jamais**.

Ce banc verifie les trois, et le dernier point est le plus important a tester :
une boucle d'apprentissage qui s'applique toute seule serait une REGRESSION par
rapport a la decision Generate Studio du 29/06.

Le controle qui compte vraiment : le dataset ecrit doit etre **consommable par
l'entraineur**. Un dossier d'images sans captions valides ne sert a rien, et
personne ne s'en apercevrait avant de lancer 40 minutes de GPU.

Usage: python test_validation_live.py [--headed]
"""
import argparse
import io
import os
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
PROJ_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
APP_URL = "http://127.0.0.1:8190/manga"
SLUG = "banc-phase4"       # d'ou viennent les images
PROJ_TEST = "banc-valid"   # projet DEDIE : sinon les cases validees par les autres
                           # bancs entrent dans le compte et le verdict devient faux
TRIGGER = "zqmg1rl"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright

    secret = open(SECRET_FILE, encoding="utf-8").read().strip()
    outdir = os.path.join(PROJ_DIR, "output", SLUG)
    srcs = sorted(f for f in os.listdir(outdir)
                  if f.endswith(".png") and not f.startswith("_")
                  and not f.endswith(("_fond.png", "_depth.png")))[:4]
    if len(srcs) < 4:
        print("ECHEC: il faut 4 cases dans output/%s" % SLUG)
        return 2

    js_errors = []
    print("=== BANC PHASE 6 — boucle de validation ===")

    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=not args.headed)
        pg = br.new_page(viewport={"width": 1500, "height": 1100})
        pg.on("pageerror", lambda e: js_errors.append(str(e)))
        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_selector("#selProj", timeout=15000)
        pg.wait_for_timeout(1200)

        print("\n[1] planche de travail : 3 cases générées + 1 vide")
        pg.evaluate("""async (srcs) => {
            const k = localStorage.getItem('manga_key');
            const H = {'Content-Type':'application/json', Authorization:'Bearer '+k};
            const P=(u,b)=>fetch(location.origin+u,{method:'POST',headers:H,body:JSON.stringify(b)}).then(r=>r.json());
            let projs = await (await fetch(location.origin+'/manga/projects',{headers:H})).json();
            let proj = projs.items.find(p => p.slug === 'banc-valid');
            if (proj) await P('/manga/projects', {delete: proj.id});   // on repart propre
            const cree = await P('/manga/projects', {name:'banc validation', slug:'banc-valid',
                                                     recipe:{trigger:'zqmg1rl'}});
            proj = {id: cree.id, slug: 'banc-valid'};
            const pgr = await P('/manga/pages',{projectId:proj.id,chapter:'6',idx:0,
                title:'banc validation',layout:{cols:2},master:{}});
            const actions = ['sitting at a desk, bored, upper body',
                             'close-up, surprised, looking at viewer',
                             'standing by the window, three-quarter view'];
            for (let i=0;i<3;i++)
                await P('/manga/panels',{pageId:pgr.id,idx:i,kind:'dialogue',prompt:actions[i],
                    file:'banc-phase4/'+srcs[i], verdict:'',
                    recipe:{seed:9000+i, loraW:0.8, ckpt:'wai', steps:30}});
            await P('/manga/panels',{pageId:pgr.id,idx:3,kind:'dialogue',prompt:'',file:'',verdict:''});
            localStorage.setItem('manga_proj',proj.id);
            localStorage.setItem('manga_page',pgr.id); }""", srcs)
        pg.reload(wait_until="domcontentloaded")
        pg.wait_for_selector(".panel", timeout=20000)
        pg.wait_for_timeout(2000)

        print("[2] notation : 2 ✅ et 1 ❌")
        cards = pg.query_selector_all(".panel")
        cards[0].query_selector('[data-act="ok"]').click(); pg.wait_for_timeout(500)
        cards = pg.query_selector_all(".panel")
        cards[1].query_selector('[data-act="ok"]').click(); pg.wait_for_timeout(500)
        cards = pg.query_selector_all(".panel")
        cards[2].query_selector('[data-act="ko"]').click(); pg.wait_for_timeout(700)

        print("[3] onglet Validé")
        pg.click('nav button[data-tab="tVal"]')
        pg.wait_for_timeout(2500)
        etat = pg.text_content("#valState")
        vignettes = pg.eval_on_selector_all("#valList figure", "e => e.length")
        print("    %s · %d recette(s) affichée(s)" % (etat, vignettes))

        print("[4] réutilisation d'une recette (elle doit être COPIÉE, pas appliquée d'office)")
        avant = pg.evaluate("""async () => {
            const k = localStorage.getItem('manga_key');
            const r = await fetch(location.origin+'/manga/panels?page='+localStorage.getItem('manga_page'),
                {headers:{Authorization:'Bearer '+k}});
            return (await r.json()).items.map(p => ({idx:p.idx, prompt:p.prompt, seed:(p.recipe||{}).seed})); }""")
        pg.query_selector("#valList [data-reuse]").click()
        pg.wait_for_timeout(1200)
        apres = pg.evaluate("""async () => {
            const k = localStorage.getItem('manga_key');
            const r = await fetch(location.origin+'/manga/panels?page='+localStorage.getItem('manga_page'),
                {headers:{Authorization:'Bearer '+k}});
            return (await r.json()).items.map(p => ({idx:p.idx, prompt:p.prompt, seed:(p.recipe||{}).seed,
                                                     herite:(p.recipe||{}).herite_de})); }""")
        vide_rempli = bool(apres[3]["prompt"]) and bool(apres[3].get("herite"))
        # AUCUNE autre case ne doit avoir bouge : l'app propose, elle n'impose pas.
        touchees = sum(1 for i in range(3)
                       if avant[i]["prompt"] != apres[i]["prompt"] or avant[i]["seed"] != apres[i]["seed"])
        # ...et le seed doit etre RENOUVELE, sinon on rejoue la meme image.
        seed_neuf = apres[3]["seed"] != avant[0]["seed"]
        print("    case vide remplie : %s · autres cases modifiées : %d · seed renouvelé : %s"
              % ("oui" if vide_rempli else "NON", touchees, "oui" if seed_neuf else "NON"))

        print("[5] écriture du dataset")
        pg.fill("#dsTrigger", TRIGGER)
        pg.click("#btnDataset")
        pg.wait_for_timeout(2500)
        sortie = pg.text_content("#dsOut")
        print("    %s" % (sortie or "").replace("\n", " ")[:150])

        app_err = pg.evaluate("() => MangaLog.errors().map(e => e.msg)")
        pg.evaluate("""async () => {
            const k = localStorage.getItem('manga_key');
            const H = {'Content-Type':'application/json', Authorization:'Bearer '+k};
            const projs = await (await fetch(location.origin+'/manga/projects',{headers:H})).json();
            const p = projs.items.find(x => x.slug === 'banc-valid');
            if (p) await fetch(location.origin+'/manga/projects',{method:'POST',headers:H,
                     body: JSON.stringify({delete: p.id})});
            localStorage.removeItem('manga_proj'); localStorage.removeItem('manga_page'); }""")
        br.close()

    # ===== LE dataset est-il CONSOMMABLE par l'entraineur ? =====
    ds = os.path.join(PROJ_DIR, "dataset_%s" % PROJ_TEST)
    images = sorted(f for f in os.listdir(ds)) if os.path.isdir(ds) else []
    pngs = [f for f in images if f.endswith(".png")]
    txts = [f for f in images if f.endswith(".txt")]
    apparies = sum(1 for p in pngs if p[:-4] + ".txt" in txts)
    caps = []
    for t in txts:
        caps.append(open(os.path.join(ds, t), encoding="utf-8").read().strip())
    trigger_partout = all(c.startswith(TRIGGER) for c in caps) if caps else False
    # Le piege du LoRA v1 : ne JAMAIS decrire un attribut constant du personnage.
    constants = ("sailor", "scarf", "black hair", "bangs", "amber eyes", "écharpe")
    fuite = [c for c in caps if any(k in c.lower() for k in constants)]

    # Preuve finale : l'entraineur accepte-t-il ce dossier ?
    prep = subprocess.run([sys.executable, os.path.join(PROJ_DIR, "scripts", "prep_train.py"),
                           "--src", ds, "--trigger", TRIGGER],
                          capture_output=True, text=True, timeout=180)
    prep_ok = prep.returncode == 0 and "images x" in (prep.stdout or "")

    print("\n================= VERDICT =================")
    print("cases validées vues par l'app     : %s" % etat)
    print("recettes affichées                : %d" % vignettes)
    print("recette copiée dans la case vide  : %s" % ("oui" if vide_rempli else "NON"))
    print("autres cases modifiées d'office   : %d  (doit être 0 — l'app propose)" % touchees)
    print("seed renouvelé à la copie         : %s" % ("oui" if seed_neuf else "NON"))
    print("--- dataset écrit ---")
    print("images / captions / appariées     : %d / %d / %d" % (len(pngs), len(txts), apparies))
    print("trigger en tête de chaque caption : %s" % ("oui" if trigger_partout else "NON"))
    print("captions décrivant un attribut CONSTANT : %d  (doit être 0)" % len(fuite))
    for c in caps:
        print("   %s" % c)
    print("l'entraîneur accepte le dossier   : %s" % ("oui" if prep_ok else "NON"))
    if not prep_ok:
        print("   %s" % (prep.stdout or prep.stderr)[-300:])
    print("erreurs JS                        : %d" % len(js_errors))
    print("erreurs journal                   : %d" % len(app_err))

    ok = (vignettes == 2 and vide_rempli and touchees == 0 and seed_neuf
          and len(pngs) == 2 and apparies == 2 and trigger_partout and not fuite
          and prep_ok and not js_errors and not app_err)
    print("\n%s" % ("*** PHASE 6 : LA BOUCLE TOURNE, ET ELLE N'IMPOSE RIEN ***" if ok
                    else "*** PHASE 6 : NON ATTEINT ***"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
