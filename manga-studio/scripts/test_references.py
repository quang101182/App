# -*- coding: utf-8 -*-
"""Images de reference sur les fiches de personnages (IPAdapter) — v1.25.0.

Le chantier n°1 de la revalidation : la table `chars` portait `refs[]` depuis le
debut, mais rien dans l'UI ne permettait d'y mettre une image. Un personnage ne
tenait donc qu'a ~50 % (texte seul) au lieu du verrou mesure a 0,839.

Le reglage n'a RIEN d'evident et il est mesure (`test_ipadapter.py`, 27/07) :
  - preset « PLUS FACE (portraits) », dont le nom invite pourtant a le choisir :
    DETRUIT le rendu (noir 0,112 contre 0,599 au temoin) ;
  - poids 0,8 : la planche VIRE AU BLEU.
  - retenu : PLUS (high strength) / poids 0,4 / end_at 0,5 / reference en N&B.

Le piege central, et ce que ce banc surveille avant tout : **IPAdapter transfere
la PALETTE de sa reference**, et le negatif textuel (« monochrome, greyscale »)
ne pese RIEN contre une image. D'ou la conversion en niveaux de gris cote client,
AVANT l'upload -- le seul endroit ou la couleur ne peut pas revenir.

Le banc donne donc expres une reference EN COULEUR FRANCHE et verifie que ce qui
arrive sur le disque est gris. Une reference deja N&B ne prouverait rien.

Usage:
    python test_references.py [--headed] [--reel]   # --reel : genere vraiment
    python test_references.py --muter               # DOIT virer au rouge
"""
import argparse
import io
import json
import os
import sys
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
APP_URL = "http://127.0.0.1:8190/manga"
LARGEUR, HAUTEUR = 360, 780
NOM = "_refs_%d" % os.getpid()
ICI = os.path.dirname(os.path.abspath(__file__))
REF_COULEUR = os.path.join(ICI, "refs_out", "ref_couleur.png")

cas = []


def verifie(nom, ok, detail=""):
    cas.append((nom, bool(ok), detail))
    print(("  OK   " if ok else "  ECHEC") + " " + nom + ((" — " + detail) if detail else ""))
    return ok


def damier_couleur():
    """Une reference volontairement SATUREE : rouge et bleu francs."""
    from PIL import Image
    os.makedirs(os.path.dirname(REF_COULEUR), exist_ok=True)
    im = Image.new("RGB", (600, 800))
    px = im.load()
    for y in range(800):
        for x in range(600):
            px[x, y] = (220, 40, 40) if (x // 60 + y // 60) % 2 else (40, 60, 220)
    im.save(REF_COULEUR)
    return REF_COULEUR


def saturation(im):
    from PIL import Image
    im = im.convert("RGB")
    px = list(im.getdata())[::503]
    return sum(max(p) - min(p) for p in px) / len(px)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--reel", action="store_true",
                    help="genere vraiment une case (~30 s de GPU) et mesure sa saturation")
    ap.add_argument("--muter", action="store_true",
                    help="la conversion N&B est annulee : le banc DOIT virer au rouge")
    args = ap.parse_args()
    from PIL import Image
    from playwright.sync_api import sync_playwright

    secret = open(SECRET_FILE, encoding="utf-8").read().strip()
    ref_src = damier_couleur()
    print("reference source : saturation %.1f (elle est FRANCHEMENT coloree)"
          % saturation(Image.open(ref_src)))
    erreurs = []
    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=not args.headed, channel="msedge")
        pg = br.new_page(viewport={"width": LARGEUR, "height": HAUTEUR},
                         is_mobile=True, has_touch=True)
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        pg.on("dialog", lambda d: d.accept())
        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)

        if not args.reel:
            pg.evaluate("""() => { window.__g = [];
                runGraph = async (n) => { window.__g.push(n); return ['fake.png']; };
                harvest = async () => '_demo/1_planche_pc.png'; }""")
        else:
            pg.evaluate("() => { window.__g = []; }")

        if args.muter:
            # MUTATION : on rend la conversion transparente. La reference part en
            # COULEUR, et IPAdapter transferera sa palette a toute la planche.
            pg.evaluate("""() => {
                enNoirEtBlanc = async (file) => file;
            }""")

        st = pg.evaluate("""async (nom) => {
            const c = await api('/manga/chars', {name: nom, tags: 'kmk, 1girl, sailor uniform'});
            const proj = await api('/manga/projects', {name: nom, slug: nom});
            const cree = await api('/manga/pages', {projectId: proj.id, title: nom,
                          chapter: '1', idx: 0, layout: {cols: 2, casting: [c.id]}});
            const page = ((await api('/manga/pages?project=' + proj.id)).items || [])
                           .find(x => x.id === cree.id);
            await api('/manga/panels', {pageId: page.id, kind: 'dialogue',
                       prompt: 'standing in a corridor, looking at viewer', idx: 0});
            S.proj = proj; S.page = page; CHARS = (await api('/manga/chars')).items || [];
            S.panels = ((await api('/manga/panels?page=' + page.id)).items || []);
            renderPlate(); renderChars();
            return {proj: proj.id, char: c.id, pid: S.panels[0].id};
        }""", NOM)

        print("\n--- sans reference : rien ne doit changer ---")
        pg.evaluate("() => { window.__g = []; }")
        if not args.reel:
            pg.evaluate("async (id) => genPanel(S.panels.find(x => x.id === id))", st["pid"])
            pg.wait_for_timeout(2000)
            verifie("aucun IPAdapter dans le graphe quand la fiche n'a pas d'image",
                    "IPAdapter" not in json.dumps(pg.evaluate("window.__g")))

        print("\n--- ajouter une image par le VRAI champ de la fiche ---")
        pg.click('nav button[data-tab="tPerso"]')
        pg.wait_for_timeout(600)
        verifie("la fiche propose d'ajouter une image de reference",
                pg.evaluate("(id) => !!document.querySelector('input[data-chref=\"'+id+'\"]')",
                            st["char"]))
        pg.set_input_files('input[data-chref="%s"]' % st["char"], ref_src)
        pg.wait_for_timeout(5000)
        refs = pg.evaluate("(id) => (CHARS.find(c => c.id === id) || {}).refs || []", st["char"])
        verifie("la reference est enregistree sur la fiche", len(refs) == 1, str(refs))
        verifie("une vignette de la reference s'affiche dans la fiche",
                pg.evaluate("document.querySelectorAll('#charList img').length") >= 1)

        print("\n--- le piege : la couleur ne doit PAS survivre a l'upload ---")
        url = ("http://127.0.0.1:8190/comfy/view?filename=" + refs[0]
               + "&type=input&_k=" + secret)
        montee = Image.open(io.BytesIO(urllib.request.urlopen(url).read()))
        sat = saturation(montee)
        verifie("la reference stockee est en NIVEAUX DE GRIS",
                sat < 2.0, "saturation %.2f (source : ~150)" % sat)
        verifie("la reference est bornee en taille",
                max(montee.size) <= 1024, "%sx%s" % montee.size)

        print("\n--- le graphe envoye au moteur ---")
        pg.click('nav button[data-tab="tPlate"]')
        pg.wait_for_timeout(600)
        pg.evaluate("() => { window.__g = []; }")
        pg.evaluate("async (id) => genPanel(S.panels.find(x => x.id === id))", st["pid"])
        if args.reel:
            for _ in range(60):
                if pg.evaluate("(id) => !!(S.panels.find(x => x.id === id) || {}).file", st["pid"]):
                    break
                pg.wait_for_timeout(2000)
        else:
            pg.wait_for_timeout(2500)

        g = pg.evaluate("window.__g")
        ipa, loader, ks = {}, {}, {}
        if g:
            for n in g[-1].values():
                ct = n.get("class_type")
                if ct == "IPAdapterAdvanced":
                    ipa = n["inputs"]
                elif ct == "IPAdapterUnifiedLoader":
                    loader = n["inputs"]
                elif ct == "KSampler":
                    ks = n["inputs"]
        verifie("l'IPAdapter est bien pose dans le graphe", bool(ipa))
        verifie("preset = PLUS (high strength), PAS « PLUS FACE » qui detruit le rendu",
                loader.get("preset") == "PLUS (high strength)", str(loader.get("preset")))
        verifie("poids = 0,4 (a 0,8 la planche vire au bleu)",
                abs(float(ipa.get("weight") or 0) - 0.4) < 0.001, str(ipa.get("weight")))
        verifie("end_at = 0,5 (l'ancre se pose au DEBUT du debruitage)",
                abs(float(ipa.get("end_at") or 0) - 0.5) < 0.001, str(ipa.get("end_at")))
        verifie("le KSampler consomme bien la sortie de l'IPAdapter",
                (ks.get("model") or [None])[0] == "22", str(ks.get("model")))

        if args.reel:
            f = pg.evaluate("(id) => (S.panels.find(x => x.id === id) || {}).file", st["pid"])
            verifie("ComfyUI a ACCEPTE le graphe et rendu une image", bool(f), str(f))
            if f:
                chemin = os.path.join(ICI, "..", "output", *f.split("/"))
                s2 = saturation(Image.open(chemin))
                verifie("la case rendue reste monochrome (le piege du virage couleur)",
                        s2 < 8.0, "saturation %.2f" % s2)

        print("\n--- retirer la reference ---")
        pg.click('nav button[data-tab="tPerso"]')
        pg.wait_for_timeout(600)
        pg.click('[data-chref-del="%s"]' % st["char"])
        pg.wait_for_timeout(1500)
        verifie("la reference se retire de la fiche",
                pg.evaluate("(id) => ((CHARS.find(c => c.id === id) || {}).refs || []).length",
                            st["char"]) == 0)

        pg.evaluate("""async ([p, c]) => { await api('/manga/projects', {delete: p});
                                           await api('/manga/chars', {delete: c}); }""",
                    [st["proj"], st["char"]])
        br.close()

    verifie("aucune erreur JS", not erreurs, "; ".join(erreurs[:2]))

    rates = [c for c in cas if not c[1]]
    print("\n=== %d/%d verifications passees ===" % (len(cas) - len(rates), len(cas)))
    if args.muter:
        if rates:
            print("MUTATION : le banc vire au rouge — il sait donc echouer. OK")
            return 0
        print("MUTATION : le banc reste VERT alors que la reference part EN COULEUR.")
        return 1
    for nom, _, det in rates:
        print("  - " + nom + ((" (" + det + ")") if det else ""))
    return 1 if rates else 0


if __name__ == "__main__":
    sys.exit(main())
