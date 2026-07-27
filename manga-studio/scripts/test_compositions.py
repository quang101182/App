# -*- coding: utf-8 -*-
"""Les EFFETS DE BORD : ce qui n'avait jamais ete teste ENSEMBLE.

Chaque fonction de l'app a ete mesuree isolement. Les compositions, non -- et
c'est exactement la que se logent les defauts. Le 27/07, la premiere combinaison
essayee (sequence + casting de 2) a livre le defaut le plus grave de la journee.

Ce banc ne genere RIEN : il intercepte `runGraph` et lit le GRAPHE reellement
envoye a ComfyUI. C'est plus severe qu'une image a juger -- on voit le
ControlNet, son poids, son image, et le prompt exact -- et ca coute zero GPU,
donc ca peut tourner a chaque modification.

Combinaisons couvertes :
  A. sequence sur une planche qui a un FOND MAITRE (openpose et depth s'excluent)
  B. traduction + casting + comptage, tous actifs en meme temps
  C. export d'une planche aux formats HETEROGENES (cases + vignettes)
  D. deux appareils sur le MEME projet : qui gagne ?

Usage:
    python test_compositions.py [--headed]
    python test_compositions.py --muter     # DOIT virer au rouge
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
NOM = "_compo_%d" % os.getpid()
DEMO = "_demo/1_planche_pc.png"
REPONSE_LLM = {"prompt": "2people, master hitting girl, classroom"}

cas = []


def verifie(nom, ok, detail=""):
    cas.append((nom, bool(ok), detail))
    print(("  OK   " if ok else "  ECHEC") + " " + nom + ((" — " + detail) if detail else ""))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--muter", action="store_true")
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright

    secret = open(SECRET_FILE, encoding="utf-8").read().strip()
    erreurs = []
    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=not args.headed, channel="msedge")
        pg = br.new_page(viewport={"width": LARGEUR, "height": HAUTEUR},
                         is_mobile=True, has_touch=True)
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        pg.on("dialog", lambda d: d.accept())
        pg.route("**/enhance", lambda r: r.fulfill(
            status=200, content_type="application/json", body=json.dumps(REPONSE_LLM)))
        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)

        # On intercepte le graphe AU LIEU de generer. `harvest` est neutralise de
        # meme : rien ne doit toucher ni ComfyUI ni le disque.
        pg.evaluate("""() => {
            window.__graphes = [];
            runGraph = async (nodes, label) => {
                window.__graphes.push({label: label, nodes: nodes});
                return ['fake.png'];
            };
            harvest = async (img, nom) => '_demo/1_planche_pc.png';
            uploadToComfy = async () => 'squelette_simule.png';
        }""")

        if args.muter:
            # MUTATION : le squelette de sequence n'est plus transmis -- la pose
            # disparait du graphe sans que rien ne le signale a l'ecran.
            pg.evaluate("""() => {
                const vrai = wfPanel;
                wfPanel = (r, pos, seed, prefix, depth, pose, pw) =>
                    vrai(r, pos, seed, prefix, depth, null, pw);
            }""")

        base = pg.evaluate("""async ([nom, demo]) => {
            const proj = await api('/manga/projects', {name: nom, slug: nom});
            const cree = await api('/manga/pages', {projectId: proj.id, title: nom,
                                                    chapter: '1', idx: 0, layout: {cols: 2}});
            const page = ((await api('/manga/pages?project=' + proj.id)).items || [])
                           .find(x => x.id === cree.id);
            const amb = await api('/manga/panels', {pageId: page.id, kind: 'ambiance',
                                                    prompt: 'empty classroom at dusk', idx: 0});
            const dia = await api('/manga/panels', {pageId: page.id, kind: 'dialogue',
                                                    prompt: 'she runs', idx: 1, file: demo});
            S.proj = proj; S.page = page;
            // Fond maitre SIMULE : on teste la composition, pas la generation du fond.
            S.page.master = {decor: 'empty classroom, wooden desks', seed: 1,
                             fond: demo, depth: demo, depthInput: 'depth_simule.png'};
            await api('/manga/pages', S.page);
            S.panels = ((await api('/manga/panels?page=' + page.id)).items || [])
                         .sort((a, b) => a.idx - b.idx);
            renderPlate();
            return {proj: proj.id, page: page.id, amb: amb.id, dia: dia.id};
        }""", [NOM, DEMO])

        def graphes():
            return pg.evaluate("window.__graphes")

        def cn_de(g):
            """Le ControlNet reellement pose dans le graphe : nom, image, poids."""
            for k, n in g["nodes"].items():
                if "ControlNet" in str(n.get("class_type", "")) and "Apply" in str(n.get("class_type", "")):
                    return n.get("inputs", {})
            return {}

        print("\n--- A. case AMBIANCE : le fond maitre est-il vraiment impose ? ---")
        pg.evaluate("() => { window.__graphes = []; }")
        pg.evaluate("async (id) => genPanel(S.panels.find(x => x.id === id))", base["amb"])
        pg.wait_for_timeout(2500)
        g = graphes()
        verifie("la case ambiance a bien ete envoyee au moteur", len(g) == 1, "%d graphe(s)" % len(g))
        if g:
            cn = cn_de(g[0])
            noms = json.dumps(g[0]["nodes"])
            verifie("case ambiance : le ControlNet depth est applique",
                    "depth" in noms.lower(), "poids=%s" % cn.get("strength"))
            verifie("case ambiance : le decor du fond maitre est dans le prompt",
                    "wooden desks" in noms, "")

        print("\n--- A-bis. SEQUENCE sur cette meme planche a fond maitre ---")
        # openpose et depth s'excluent : un seul ControlNet est applique. On veut
        # savoir LEQUEL gagne, et si les vignettes gardent le decor du fond maitre.
        pg.evaluate("() => { window.__graphes = []; }")
        pg.evaluate("async (id) => sequence(S.panels.find(x => x.id === id), 'coup', 2)",
                    base["dia"])
        pg.wait_for_timeout(3500)
        gs = graphes()
        verifie("la sequence a envoye 2 vignettes", len(gs) == 2, "%d graphe(s)" % len(gs))
        if gs:
            noms = json.dumps(gs[0]["nodes"])
            cn = cn_de(gs[0])
            verifie("vignette : c'est le SQUELETTE qui est applique, pas le depth",
                    "openpose" in noms.lower(), "cn=%s" % str(cn.get("strength")))
            verifie("vignette : le squelette pese bien 0,9",
                    abs(float(cn.get("strength") or 0) - 0.9) < 0.01,
                    "poids=%s" % cn.get("strength"))
            # La case de depart est un `dialogue` : elle n'a jamais eu le decor.
            # On verifie surtout qu'aucun depth ne se glisse en plus du squelette.
            verifie("vignette : AUCUN depth ne se superpose au squelette",
                    "depth_simule" not in noms, "")

        print("\n--- A-ter. sequence lancee depuis une case AMBIANCE ---")
        # C'est le cas qui devrait le plus mal se passer : une case « ambiance »
        # n'existe QUE par son fond maitre, et `sequence()` cree ses vignettes en
        # `kind: 'dialogue'` (code en dur). Le decor est-il perdu en route ?
        pg.evaluate("() => { window.__graphes = []; }")
        amb_seq = pg.evaluate("""async (id) => {
            const p = S.panels.find(x => x.id === id);
            const avant = S.panels.length;
            await sequence(p, 'coup', 2);
            const filles = S.panels.filter(x => (x.recipe||{}).sequence
                                                && x.idx > p.idx && x.idx <= p.idx + 2);
            return {creees: S.panels.length - avant, kinds: filles.map(x => x.kind)};
        }""", base["amb"])
        pg.wait_for_timeout(3000)
        ga = graphes()
        noms_a = json.dumps(ga[0]["nodes"]) if ga else ""
        verifie("une sequence part bien depuis une case ambiance",
                amb_seq["creees"] > 0, "%s vignette(s)" % amb_seq["creees"])
        verifie("ses vignettes sont des cases « dialogue »",
                set(amb_seq["kinds"]) == {"dialogue"}, "kinds=%s" % amb_seq["kinds"])
        # CONSTAT, pas un verdict : le decor du fond maitre n'est ajoute au prompt
        # que pour les cases `ambiance`. Les vignettes etant `dialogue`, elles le
        # PERDENT. C'est defendable (le squelette et le depth s'excluent de toute
        # facon) mais ce n'est dit nulle part a l'ecran.
        decor_perdu = "wooden desks" not in noms_a
        print("     constat : le décor du fond maître est %s dans les vignettes"
              % ("PERDU" if decor_perdu else "conservé"))
        verifie("les vignettes gardent au moins le texte de la case de depart",
                "classroom" in noms_a.lower(), "")

        print("\n--- B. traduction + casting + comptage, tous actifs ---")
        pg.evaluate("() => { window.__graphes = []; OPT.autoEnhance = false; }")
        combo = pg.evaluate("""async ([nom, pid]) => {
            const a = await api('/manga/chars', {name: nom+'A', tags: 'kmk, 1girl, sailor uniform'});
            const b = await api('/manga/chars', {name: nom+'B', tags: 'mst, 1boy, old man'});
            CHARS = (await api('/manga/chars')).items || [];
            S.page.layout = Object.assign({}, S.page.layout, {casting: [a.id, b.id]});
            await api('/manga/pages', S.page);
            const p = S.panels.find(x => x.id === pid);
            p.prompt = 'le maitre frappe la fille';       // FRANCAIS, 2 sujets
            p.recipe = {};
            renderPlate();
            await genPanel(p);
            return {chars: [a.id, b.id], prompt: p.prompt, nbPersos: (p.recipe||{}).nbPersos};
        }""", [NOM, base["dia"]])
        pg.wait_for_timeout(2000)
        gc = graphes()
        pos = ""
        if gc:
            for n in gc[-1]["nodes"].values():
                t = str(n.get("inputs", {}).get("text", ""))
                if "kmk" in t or "hitting" in t or "maitre" in t:
                    pos = t
                    break
        verifie("le texte francais a ete traduit avant d'atteindre le moteur",
                "maitre" not in pos.lower(), pos[:70])
        verifie("le comptage releve AVANT traduction est conserve",
                combo["nbPersos"] == 2, "nbPersos=%s" % combo["nbPersos"])
        verifie("les DEUX personnages du casting sont dans le prompt envoye",
                "kmk" in pos and "mst" in pos, pos[:80])
        verifie("« solo » n'atteint pas le moteur", "solo" not in pos.lower())
        verifie("un tag de comptage est bien present",
                "2people" in pos or "2girls" in pos or "1boy 1girl" in pos, pos[:60])

        print("\n--- C. export d'une planche aux formats HETEROGENES ---")
        # cases classiques + vignettes de sequence : les hauteurs different.
        expo = pg.evaluate("""async () => {
            const cv = await buildPlateCanvas();
            return {w: cv.width, h: cv.height, cases: S.panels.length};
        }""")
        verifie("la planche s'assemble malgre des formats melanges",
                expo["w"] > 0 and expo["h"] > 0,
                "%sx%s pour %s cases" % (expo["w"], expo["h"], expo["cases"]))

        print("\n--- D. deux appareils sur le MEME projet : qui gagne ? ---")
        duel = pg.evaluate("""async (pid) => {
            // « PC » et « telephone » lisent la meme case, puis ecrivent chacun.
            const items = (await api('/manga/panels?page=' + S.page.id)).items || [];
            const vuePC  = JSON.parse(JSON.stringify(items.find(x => x.id === pid)));
            const vueTel = JSON.parse(JSON.stringify(items.find(x => x.id === pid)));
            vuePC.prompt  = 'ecrit par le PC';
            await api('/manga/panels', vuePC);
            vueTel.prompt = 'ecrit par le telephone';
            await api('/manga/panels', vueTel);
            const apres = (await api('/manga/panels?page=' + S.page.id)).items || [];
            return (apres.find(x => x.id === pid) || {}).prompt;
        }""", base["dia"])
        verifie("le DERNIER ecrivain gagne, sans erreur ni doublon",
                duel == "ecrit par le telephone", "en base : %r" % duel)
        print("     (constat, pas un defaut : aucune fusion, aucun avertissement —"
              " le travail du premier est perdu en silence)")

        pg.evaluate("""async ([proj, chars]) => {
            await api('/manga/projects', {delete: proj});
            for (const c of chars) await api('/manga/chars', {delete: c});
        }""", [base["proj"], combo["chars"]])
        br.close()

    verifie("aucune erreur JS", not erreurs, "; ".join(erreurs[:2]))

    rates = [c for c in cas if not c[1]]
    print("\n=== %d/%d verifications passees ===" % (len(cas) - len(rates), len(cas)))
    if args.muter:
        if rates:
            print("MUTATION : le banc vire au rouge — il sait donc echouer. OK")
            return 0
        print("MUTATION : le banc reste VERT sans squelette dans le graphe. A reecrire.")
        return 1
    for nom, _, det in rates:
        print("  - " + nom + ((" (" + det + ")") if det else ""))
    return 1 if rates else 0


if __name__ == "__main__":
    sys.exit(main())
