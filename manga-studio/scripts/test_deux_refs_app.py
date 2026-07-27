# -*- coding: utf-8 -*-
"""L'app applique-t-elle VRAIMENT deux references, et bornees a leur moitie ?

`test_deux_refs.py` a repondu a la question de fond, GPU en main : deux
references masquees gauche/droite tiennent les deux identites (6/6 a poids 0,6),
la une seule reference n'y arrive qu'une fois sur six -- elle CONTAMINE le second
personnage. Ce banc-ci verifie que l'application envoie bien ce graphe-la.

Il ne genere rien : il intercepte `runGraph` et lit le graphe reellement transmis
a ComfyUI (meme methode que `test_compositions.py`). Zero GPU, donc rejouable a
chaque modification -- et c'est la lecon du 27/07 : « un banc couteux qu'on ne
rejoue pas ne protege plus rien ».

Ce qu'il verifie :
  1. deux personnages castes, chacun avec son image  -> DEUX LoadImage distincts,
     deux IPAdapter CHAINES, deux `attn_mask` DIFFERENTS, poids 0,6 ;
  2. les masques couvrent chacun une moitie, et la reunion fait toute la case ;
  3. un seul personnage avec image -> UN IPAdapter, AUCUN masque, poids 0,4
     (le reglage mesure le 27/07, qu'on ne veut pas casser en passant) ;
  4. un personnage RETIRE de cette case n'y laisse plus son visage -- la v1.51.0
     avait corrige les tags, pas l'image de reference ;
  5. aucun personnage avec image -> aucun noeud IPAdapter du tout.

Usage:
    python test_deux_refs_app.py [--headed]
    python test_deux_refs_app.py --muter     # DOIT virer au rouge
"""
import argparse
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
APP_URL = "http://127.0.0.1:8190/manga"
LARGEUR, HAUTEUR = 360, 780
NOM = "_duoref_%d" % os.getpid()
DEMO = "_demo/1_planche_pc.png"

cas = []


def verifie(nom, ok, detail=""):
    cas.append((nom, bool(ok), detail))
    print(("  OK   " if ok else "  ECHEC") + " " + nom + ((" — " + detail) if detail else ""))
    return ok


def ipa_de(g):
    """Les IPAdapterAdvanced du graphe, dans l'ordre de la chaine du modele."""
    n = g["nodes"]
    ids = [k for k, v in n.items() if v.get("class_type") == "IPAdapterAdvanced"]
    # L'ordre de la chaine : celui dont le `model` ne vient pas d'un autre IPA est
    # le premier. On ne se fie pas au numero du noeud, qui n'est qu'une convention.
    def amont(k):
        m = n[k]["inputs"].get("model")
        return m[0] if isinstance(m, list) else None
    prem = [k for k in ids if amont(k) not in ids]
    ordre, cur = [], (prem[0] if prem else None)
    while cur:
        ordre.append(cur)
        suiv = [k for k in ids if amont(k) == cur]
        cur = suiv[0] if suiv else None
    return [(k, n[k]["inputs"]) for k in ordre]


def image_de(g, ipa_inputs):
    """Le nom de fichier charge par le LoadImage branche sur cet IPAdapter."""
    ld = ipa_inputs.get("image")
    if not isinstance(ld, list):
        return None
    return g["nodes"].get(ld[0], {}).get("inputs", {}).get("image")


def live(args):
    """Une VRAIE case a deux personnages, generee par l'app elle-meme.

    Les deux references sont celles que `test_deux_refs.py` a deja deposees dans
    ComfyUI/input (deja en N&B) : on mesure la chaine de l'app, pas la fabrication
    des references. Le banc rend le chemin de l'image pour qu'on la REGARDE --
    « un banc qui ne regarde jamais l'ecran valide des chiffres, pas un resultat ».
    """
    from playwright.sync_api import sync_playwright
    secret = open(SECRET_FILE, encoding="utf-8").read().strip()
    REF_A, REF_B = "manga_ref__nb_ds_00.png", "manga_ref__nb_refB_0.png"
    erreurs = []
    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=not args.headed, channel="msedge")
        pg = br.new_page(viewport={"width": LARGEUR, "height": HAUTEUR},
                         is_mobile=True, has_touch=True)
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        pg.on("dialog", lambda d: d.accept())
        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)
        pg.set_default_timeout(240000)
        pg.evaluate("() => { OPT.autoEnhance = false; }")
        out = pg.evaluate("""async ([nom, refA, refB]) => {
            const proj = await api('/manga/projects', {name: nom, slug: nom});
            const cree = await api('/manga/pages', {projectId: proj.id, title: nom,
                                                    chapter: '1', idx: 0, layout: {cols: 1}});
            const page = ((await api('/manga/pages?project=' + proj.id)).items || [])
                           .find(x => x.id === cree.id);
            const a = await api('/manga/chars', {name: nom+'A',
                tags: '1girl, short messy black hair, blunt bangs, sharp eyes, '
                    + 'black sailor uniform with scarf, slender build', refs: [refA]});
            const b = await api('/manga/chars', {name: nom+'B',
                tags: '1girl, very long wavy light hair, round soft face, '
                    + 'white lab coat, tall', refs: [refB]});
            CHARS = (await api('/manga/chars')).items || [];
            S.proj = proj; S.page = page;
            S.page.layout = Object.assign({}, page.layout, {casting: [a.id, b.id]});
            await api('/manga/pages', S.page);
            const p = await api('/manga/panels', {pageId: page.id, kind: 'dialogue',
                idx: 0, prompt: '2girls, standing side by side, facing viewer, '
                              + 'upper body, indoor classroom background'});
            S.panels = ((await api('/manga/panels?page=' + page.id)).items || [])
                         .sort((x, y) => x.idx - y.idx);
            renderPlate();
            await genPanel(S.panels[0]);
            const apres = ((await api('/manga/panels?page=' + page.id)).items || [])[0];
            return {proj: proj.id, chars: [a.id, b.id], file: apres.file,
                    ecran: document.body.innerText.slice(0, 4000)};
        }""", [NOM, REF_A, REF_B])
        print("image produite : %s" % out["file"])
        print("l'ecran dit : %s"
              % ("; ".join(l for l in out["ecran"].split("\n") if "🖼" in l) or "(rien)"))
        pg.evaluate("""async ([proj, chars]) => {
            for (const c of chars) await api('/manga/chars', {delete: c});
        }""", [out["proj"], out["chars"]])
        br.close()
    print("erreurs JS : %s" % (erreurs or "aucune"))
    return 0 if out["file"] and not erreurs else 1


def samsung():
    """La ligne « X a gauche, Y a droite » tient-elle sur le VRAI telephone ?

    Un Edge emule mesure un DOM, pas un ecran. La ligne ajoutee en v1.52.0 porte
    deux noms de personnages : c'est exactement le genre de texte qui deborde a
    360 px et qu'on ne voit pas en 1280.
    """
    from samsung import Phone
    p = Phone()
    print("telephone : app en v%s" % p.version)
    m = p.js("""(async () => {
        const nom = '_duosam';
        const proj = await api('/manga/projects', {name: nom, slug: nom});
        const cree = await api('/manga/pages', {projectId: proj.id, title: nom,
                                                chapter: '1', idx: 0, layout: {cols: 1}});
        const page = ((await api('/manga/pages?project=' + proj.id)).items || [])
                       .find(x => x.id === cree.id);
        const a = await api('/manga/chars', {name: 'Kimiko', tags: '1girl', refs: ['a.png']});
        const b = await api('/manga/chars', {name: 'Jo', tags: '1boy', refs: ['b.png']});
        CHARS = (await api('/manga/chars')).items || [];
        S.proj = proj; S.page = page;
        S.page.layout = Object.assign({}, page.layout, {casting: [a.id, b.id]});
        await api('/manga/pages', S.page);
        await api('/manga/panels', {pageId: page.id, kind: 'dialogue',
                                    prompt: 'deux personnages', idx: 0});
        S.panels = ((await api('/manga/panels?page=' + page.id)).items || []);
        renderPlate();
        const q = document.querySelector('.quila');
        const ligne = [...document.querySelectorAll('.quila span')]
                        .find(s => s.textContent.indexOf('🖼') === 0);
        const r = ligne ? ligne.getBoundingClientRect() : null;
        const out = {texte: ligne ? ligne.textContent : null,
                     droite: r ? r.right : null, larg: document.documentElement.clientWidth,
                     pageDeborde: document.documentElement.scrollWidth
                                  > document.documentElement.clientWidth,
                     quilaDeborde: q ? q.scrollWidth > q.clientWidth + 1 : null};
        await api('/manga/projects', {delete: proj.id});
        await api('/manga/chars', {delete: a.id});
        await api('/manga/chars', {delete: b.id});
        return out;
    })()""", await_promise=True)
    verifie("la ligne d'identite s'affiche sur le telephone", bool(m["texte"]),
            "%s" % m["texte"])
    verifie("elle nomme les deux personnages et leur cote",
            bool(m["texte"]) and "Kimiko" in m["texte"] and "Jo" in m["texte"]
            and "gauche" in m["texte"] and "droite" in m["texte"], "")
    verifie("elle ne sort pas de l'ecran",
            m["droite"] is not None and m["droite"] <= m["larg"] + 1,
            "droite=%s largeur=%s" % (m["droite"], m["larg"]))
    verifie("la PAGE ne scrolle pas horizontalement", not m["pageDeborde"], "")
    verifie("la ligne « Qui est là » ne scrolle pas non plus", not m["quilaDeborde"], "")
    verifie("aucune erreur JS sur le telephone", not p.errors, "; ".join(p.errors[:2]))
    rates = [c for c in cas if not c[1]]
    print("\n=== %d/%d verifications (Samsung reel) ===" % (len(cas) - len(rates), len(cas)))
    return 1 if rates else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--muter", action="store_true")
    ap.add_argument("--live", action="store_true",
                    help="genere VRAIMENT une case a deux personnages (~30 s de GPU) "
                         "et laisse l'image sur le disque : un graphe juste ne prouve "
                         "pas une image juste")
    ap.add_argument("--samsung", action="store_true",
                    help="mesure la ligne d'identite sur le SM-A326B reel")
    args = ap.parse_args()
    if args.live:
        return live(args)
    if args.samsung:
        return samsung()
    from playwright.sync_api import sync_playwright

    secret = open(SECRET_FILE, encoding="utf-8").read().strip()
    erreurs = []
    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=not args.headed, channel="msedge")
        pg = br.new_page(viewport={"width": LARGEUR, "height": HAUTEUR},
                         is_mobile=True, has_touch=True)
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        pg.on("dialog", lambda d: d.accept())
        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)

        pg.evaluate("""() => {
            window.__graphes = [];
            runGraph = async (nodes, label) => {
                window.__graphes.push({label: label, nodes: nodes});
                return ['fake.png'];
            };
            harvest = async () => '_demo/1_planche_pc.png';
            OPT.autoEnhance = false;
        }""")

        if args.muter:
            # MUTATION : on revient au comportement d'AVANT (une seule reference).
            # Le banc doit alors rougir -- sinon il ne mesure pas ce qu'il annonce.
            pg.evaluate("""() => {
                const vrai = refsDuCasting;
                refsDuCasting = (p) => vrai(p).slice(0, 1);
            }""")

        base = pg.evaluate("""async ([nom, demo]) => {
            const proj = await api('/manga/projects', {name: nom, slug: nom});
            const cree = await api('/manga/pages', {projectId: proj.id, title: nom,
                                                    chapter: '1', idx: 0, layout: {cols: 2}});
            const page = ((await api('/manga/pages?project=' + proj.id)).items || [])
                           .find(x => x.id === cree.id);
            // Deux personnages AVEC image, un troisieme SANS : c'est la situation
            // reelle de Quang (Kimiko a une reference, Jo n'en avait pas).
            const a = await api('/manga/chars', {name: nom+'A', tags: 'kmk, 1girl',
                                                 refs: ['refA.png']});
            const b = await api('/manga/chars', {name: nom+'B', tags: 'jo, 1boy',
                                                 refs: ['refB.png']});
            const c = await api('/manga/chars', {name: nom+'C', tags: 'fig, 1other'});
            CHARS = (await api('/manga/chars')).items || [];
            S.proj = proj; S.page = page;
            S.page.layout = Object.assign({}, page.layout, {casting: [a.id, b.id, c.id]});
            await api('/manga/pages', S.page);
            const p = await api('/manga/panels', {pageId: page.id, kind: 'dialogue',
                                                  prompt: 'two people talking', idx: 0});
            S.panels = ((await api('/manga/panels?page=' + page.id)).items || [])
                         .sort((x, y) => x.idx - y.idx);
            renderPlate();
            return {proj: proj.id, page: page.id, panel: p.id, a: a.id, b: b.id, c: c.id};
        }""", [NOM, DEMO])

        def graphes():
            return pg.evaluate("window.__graphes")

        print("\n--- 1. DEUX personnages avec image : deux ancres, chacune bornee ---")
        pg.evaluate("() => { window.__graphes = []; }")
        pg.evaluate("async (id) => genPanel(S.panels.find(x => x.id === id))", base["panel"])
        pg.wait_for_timeout(2500)
        gs = graphes()
        verifie("la case a bien ete envoyee au moteur", len(gs) == 1, "%d graphe(s)" % len(gs))
        if gs:
            g = gs[0]
            ipa = ipa_de(g)
            verifie("DEUX IPAdapter sont appliques", len(ipa) == 2, "%d trouve(s)" % len(ipa))
            if len(ipa) == 2:
                (k1, i1), (k2, i2) = ipa
                im1, im2 = image_de(g, i1), image_de(g, i2)
                verifie("les deux references sont des images DIFFERENTES",
                        im1 and im2 and im1 != im2, "%s / %s" % (im1, im2))
                verifie("elles suivent l'ordre du casting (A puis B)",
                        im1 == "refA.png" and im2 == "refB.png", "%s puis %s" % (im1, im2))
                verifie("chacune est bornee par un attn_mask",
                        bool(i1.get("attn_mask")) and bool(i2.get("attn_mask")),
                        "%s / %s" % (i1.get("attn_mask"), i2.get("attn_mask")))
                verifie("les deux masques sont DISTINCTS (sinon les identites se melangent)",
                        i1.get("attn_mask") != i2.get("attn_mask"), "")
                verifie("le poids du duo est 0,6 (mesure : 6/6, contre 5/6 a 0,4 et 4/6 a 0,8)",
                        abs(float(i1.get("weight", 0)) - 0.6) < 0.001
                        and abs(float(i2.get("weight", 0)) - 0.6) < 0.001,
                        "%s / %s" % (i1.get("weight"), i2.get("weight")))
                verifie("les deux IPAdapter sont CHAINES (le 2e part du 1er)",
                        i2.get("model", [None])[0] == k1, "model=%s" % (i2.get("model"),))
                # Les masques : deux moities complementaires, et leur reunion doit
                # couvrir toute la case -- une bande morte au milieu laisserait une
                # zone sans aucune ancre d'identite.
                n = g["nodes"]
                mk = [v for v in n.values() if v.get("class_type") == "MaskComposite"]
                sol = [v for v in n.values() if v.get("class_type") == "SolidMask"]
                largeurs = [v["inputs"]["width"] for v in sol]
                pleine = [v for v in sol if v["inputs"]["value"] == 0.0]
                demi = [v for v in sol if v["inputs"]["value"] == 1.0]
                verifie("deux masques composes, sur un fond plein cadre",
                        len(mk) == 2 and len(pleine) == 1 and len(demi) == 1,
                        "composites=%d solides=%s" % (len(mk), largeurs))
                if pleine and demi and len(mk) == 2:
                    W = pleine[0]["inputs"]["width"]
                    xs = sorted(v["inputs"]["x"] for v in mk)
                    verifie("les deux moities se touchent et couvrent toute la case",
                            xs[0] == 0 and abs(xs[1] - demi[0]["inputs"]["width"]) <= 1
                            and abs(xs[1] + demi[0]["inputs"]["width"] - W) <= 1,
                            "x=%s largeur demie=%s pleine=%s"
                            % (xs, demi[0]["inputs"]["width"], W))
                    verifie("les masques ont la HAUTEUR de la case",
                            demi[0]["inputs"]["height"] == pleine[0]["inputs"]["height"],
                            "%s vs %s" % (demi[0]["inputs"]["height"],
                                          pleine[0]["inputs"]["height"]))

        print("\n--- 2. UN SEUL personnage avec image : pas de masque, poids 0,4 ---")
        pg.evaluate("() => { window.__graphes = []; }")
        pg.evaluate("""async ([id, b]) => {
            S.page.layout = Object.assign({}, S.page.layout, {casting: [b]});
            await api('/manga/pages', S.page);
            const p = S.panels.find(x => x.id === id);
            p.recipe = Object.assign({}, p.recipe, {casting: null});
            await genPanel(p);
        }""", [base["panel"], base["a"]])
        pg.wait_for_timeout(2500)
        gs = graphes()
        if verifie("la case a ete envoyee", len(gs) == 1, "%d graphe(s)" % len(gs)):
            ipa = ipa_de(gs[0])
            verifie("UN SEUL IPAdapter", len(ipa) == 1, "%d" % len(ipa))
            if ipa:
                i = ipa[0][1]
                verifie("aucun masque quand il n'y a qu'une reference",
                        not i.get("attn_mask"), "%s" % (i.get("attn_mask"),))
                verifie("le poids reste 0,4 (reglage mesure le 27/07, non casse)",
                        abs(float(i.get("weight", 0)) - 0.4) < 0.001, "%s" % i.get("weight"))

        print("\n--- 3. un personnage RETIRE de la case n'y laisse plus son visage ---")
        # Le defaut corrige en v1.52.0 : la reference se choisissait sur le casting
        # de la PLANCHE (`castingPage`), pas de la case. Une case dont on avait
        # retire quelqu'un portait encore son visage, sans que rien ne le dise.
        pg.evaluate("() => { window.__graphes = []; }")
        pg.evaluate("""async ([id, a, b]) => {
            S.page.layout = Object.assign({}, S.page.layout, {casting: [a, b]});
            await api('/manga/pages', S.page);
            const p = S.panels.find(x => x.id === id);
            p.recipe = Object.assign({}, p.recipe, {casting: [b]});   // A retire d'ICI
            await genPanel(p);
        }""", [base["panel"], base["a"], base["b"]])
        pg.wait_for_timeout(2500)
        gs = graphes()
        if gs:
            ipa = ipa_de(gs[0])
            imgs = [image_de(gs[0], i) for _, i in ipa]
            verifie("seule la reference du personnage encore present est appliquee",
                    imgs == ["refB.png"], "%s" % imgs)

        print("\n--- 4. aucune image de reference : aucun noeud IPAdapter ---")
        pg.evaluate("() => { window.__graphes = []; }")
        pg.evaluate("""async ([id, c]) => {
            const p = S.panels.find(x => x.id === id);
            p.recipe = Object.assign({}, p.recipe, {casting: [c]});   // le figurant, sans image
            await genPanel(p);
        }""", [base["panel"], base["c"]])
        pg.wait_for_timeout(2500)
        gs = graphes()
        if gs:
            noms = json.dumps(gs[0]["nodes"])
            verifie("aucun IPAdapter quand personne n'a d'image",
                    "IPAdapter" not in noms, "")

        print("\n--- 5. ce que l'ECRAN en dit (un placement impose doit etre annonce) ---")
        txt = pg.evaluate("""async ([id, a, b]) => {
            const p = S.panels.find(x => x.id === id);
            p.recipe = Object.assign({}, p.recipe, {casting: [a, b]});
            renderPlate();
            return document.body.innerText;
        }""", [base["panel"], base["a"], base["b"]])
        verifie("l'app dit QUI est a gauche et QUI est a droite",
                ("à gauche" in txt and "à droite" in txt), "")
        verifie("elle nomme les deux personnages tenus",
                (NOM + "A") in txt and (NOM + "B") in txt, "")

        pg.evaluate("""async ([proj, chars]) => {
            await api('/manga/projects', {delete: proj});
            for (const c of chars) await api('/manga/chars', {delete: c});
        }""", [base["proj"], [base["a"], base["b"], base["c"]]])
        br.close()

    verifie("aucune erreur JS", not erreurs, "; ".join(erreurs[:2]))

    rates = [c for c in cas if not c[1]]
    print("\n=== %d/%d verifications passees ===" % (len(cas) - len(rates), len(cas)))
    if args.muter:
        if rates:
            print("MUTATION : le banc vire au rouge — il sait donc echouer. OK")
            return 0
        print("MUTATION : le banc reste VERT alors qu'une seule reference est"
              " appliquee. A reecrire.")
        return 1
    for nom, _, det in rates:
        print("  - " + nom + ((" (" + det + ")") if det else ""))
    return 1 if rates else 0


if __name__ == "__main__":
    sys.exit(main())
