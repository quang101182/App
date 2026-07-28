# -*- coding: utf-8 -*-
"""Le CASTING et le DECOR suivent-ils la scene ? (v1.60.0)

Suite de `test_scene_contexte.py`, qui ne couvrait que le CONTEXTE. Ici on
verifie les deux choses qui DEFINISSENT une scene : qui est la, et ou on est.

Principe teste : **le casting d'une scene = celui de sa PREMIERE case**, et la
chaine d'heritage complete se lit du plus general au plus precis :
    BASE -> TROUPE (projet) -> PLANCHE -> SCENE (1re case) -> CASE
Chaque palier peut se TAIRE (= herite) ou dire « personne » (= liste vide), et
ces deux-la ne sont pas la meme chose.

Ce que le banc prouve :
  1. une case suit le casting de SA scene, pas celui de la planche ;
  2. deux scenes d'une meme planche ont des castings DIFFERENTS ;
  3. une case garde son casting propre (elle prime sur la scene) ;
  4. une scene qui ne dit rien retombe sur la planche -> les planches d'avant la
     v1.60.0 gardent leur comportement, sans migration (anti-regression) ;
  5. le decor d'une scene ne fuit PAS sur l'autre scene ;
  6. les deux decors s'ecrivent dans des FICHIERS distincts (le meme nom les
     ferait s'ecraser -- piege deja paye sur les versions de case, v1.48.0).

Usage:
    python test_scene_casting_decor.py
    python test_scene_casting_decor.py --muter     # DOIT virer au rouge
"""
import argparse
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
APP_URL = "http://127.0.0.1:8190/manga"
NOM = "_scdec_%d" % os.getpid()
SORTIE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "essai_out")

cas = []


def S_ID(chemin):
    """Le nom de fichier porte-t-il l'id d'une case (donc d'une scene) ?
    Sans ca, deux decors d'une meme planche s'ecrasent en silence."""
    import re
    return bool(re.search(r"_mc[0-9a-z]+_", chemin or ""))


def verifie(nom, ok, detail=""):
    cas.append((nom, bool(ok)))
    print(("  OK    " if ok else "  ECHEC") + " " + nom + ((" — " + detail) if detail else ""))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--muter", action="store_true")
    ap.add_argument("--live", action="store_true",
                    help="génère réellement un décor de scène (~30 s de GPU)")
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright
    os.makedirs(SORTIE, exist_ok=True)

    secret = open(SECRET_FILE, encoding="utf-8").read().strip()
    erreurs = []
    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=not args.headed, channel="msedge")
        pg = br.new_page(viewport={"width": 360, "height": 900})
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        pg.set_default_timeout(120000)
        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_function("typeof castingScene === 'function'")

        if args.muter:
            # MUTATION : le casting redevient celui de la planche, comme avant la
            # v1.60.0. Les cas 1, 2 et 3 DOIVENT tomber ; le 4 (compat) doit
            # rester vert -- c'est justement lui qui dit que rien n'a regresse.
            pg.evaluate("() => { window.castingScene = () => castingPage(); }")

        # Planche : 4 cases. Scene 1 = dojo (Kimiko), scene 2 = couloir (Jo).
        base = pg.evaluate("""async (nom) => {
            const proj = await api('/manga/projects', {name: nom, slug: nom});
            const cree = await api('/manga/pages', {projectId: proj.id, title: nom,
                                                    chapter: '1', idx: 0, layout: {cols: 1}});
            const page = ((await api('/manga/pages?project=' + proj.id)).items || [])
                           .find(x => x.id === cree.id);
            const k = await api('/manga/chars', {name: 'Kimiko' + nom, tags: '1girl, black hair'});
            const j = await api('/manga/chars', {name: 'Jo' + nom, tags: '1man, short hair'});
            const f = await api('/manga/chars', {name: 'Figu' + nom, tags: '1other, hood'});
            CHARS = (await api('/manga/chars')).items || [];
            S.proj = proj; S.page = page;
            // La PLANCHE caste le figurant : c'est le palier de repli.
            S.page.layout = Object.assign({}, page.layout, {casting: [f.id]});
            await api('/manga/pages', S.page);
            const mk = async (i, prompt, recipe) =>
              (await api('/manga/panels', {pageId: page.id, kind: 'dialogue',
                                           idx: i, prompt: prompt, recipe: recipe})).id;
            const c0 = await mk(0, 'le dojo, le maitre entre',      {casting: [k.id]});
            const c1 = await mk(1, 'elle avance',                   {});
            const c2 = await mk(2, 'le couloir du lycee',           {debutScene: true, casting: [j.id]});
            const c3 = await mk(3, 'il ouvre la porte',             {});
            S.panels = ((await api('/manga/panels?page=' + page.id)).items || []);
            renderPlate();
            return {proj: proj.id, page: page.id, k: k.id, j: j.id, f: f.id,
                    ids: [c0, c1, c2, c3]};
        }""", NOM)

        lu = pg.evaluate("() => S.panels.map(p => castingCase(p))")
        verifie("le décor du banc est monté (4 cases, 3 fiches)",
                len(lu) == 4, "%d case(s)" % len(lu))

        # 1 & 2 : chaque scene a son casting
        verifie("la case 2 suit le casting de SA scène (Kimiko), pas la planche",
                lu[1] == [base["k"]], "casting lu : %s" % lu[1])
        verifie("la scène 2 a un casting DIFFÉRENT (Jo)",
                lu[3] == [base["j"]], "casting lu : %s" % lu[3])
        verifie("les deux scènes ne se mélangent pas",
                lu[1] != lu[3] and base["j"] not in lu[1] and base["k"] not in lu[3])

        # 3 : une case garde son casting propre
        pg.evaluate("""(j) => { S.panels[1].recipe =
            Object.assign({}, S.panels[1].recipe, {casting: [j]}); }""", base["j"])
        lu2 = pg.evaluate("() => castingCase(S.panels[1])")
        verifie("le casting PROPRE d'une case prime sur celui de sa scène",
                lu2 == [base["j"]], "%s" % lu2)
        pg.evaluate("""() => { const r = Object.assign({}, S.panels[1].recipe);
                               delete r.casting; S.panels[1].recipe = r; }""")

        # 4 : ANTI-REGRESSION -- une scene muette retombe sur la planche
        pg.evaluate("""() => { const r = Object.assign({}, S.panels[0].recipe);
                               delete r.casting; S.panels[0].recipe = r; }""")
        lu3 = pg.evaluate("() => castingCase(S.panels[1])")
        verifie("une scène qui ne dit rien retombe sur la PLANCHE (compat v1.59)",
                lu3 == [base["f"]], "casting lu : %s (attendu le figurant)" % lu3)
        pg.evaluate("""(k) => { S.panels[0].recipe =
            Object.assign({}, S.panels[0].recipe, {casting: [k]}); }""", base["k"])

        # 5 : le decor de scene ne fuit pas
        pg.evaluate("""() => {
            S.page.master = {decor: 'planche générique', depthInput: 'p.png', depth: 'p2.png'};
            S.panels[2].recipe = Object.assign({}, S.panels[2].recipe,
              {sceneMaster: {decor: 'couloir du lycee', depthInput: 'c.png', depth: 'c2.png'}});
        }""")
        dec = pg.evaluate("() => S.panels.map(p => masterScene(p).decor)")
        verifie("la scène 2 utilise SON décor",
                dec[2] == "couloir du lycee" and dec[3] == "couloir du lycee", "%s" % dec)
        verifie("la scène 1 garde celui de la planche (elle n'a pas le sien)",
                dec[0] == "planche générique" and dec[1] == "planche générique", "%s" % dec)

        # ... et il entre bien dans le prompt d'une case « ambiance »
        pg.evaluate("() => { S.panels[3].kind = 'ambiance'; S.panels[1].kind = 'ambiance'; }")
        pf = pg.evaluate("() => [promptFinal(S.panels[1]), promptFinal(S.panels[3])]")
        verifie("le bon décor entre dans le prompt de chaque scène",
                "planche générique" in pf[0] and "couloir du lycee" in pf[1]
                and "couloir" not in pf[0], "%s || %s" % (pf[0][-60:], pf[1][-60:]))

        # 6 : deux decors, deux noms de fichier
        noms = pg.evaluate("""() => {
            const a = [];
            S.sceneCible = null;  a.push((S.page.id));
            S.sceneCible = S.panels[2].id; a.push(S.page.id + '_' + S.sceneCible);
            S.sceneCible = null;
            return a;
        }""")
        verifie("les deux décors s'écrivent sous des noms DIFFÉRENTS",
                noms[0] != noms[1], "%s vs %s" % (noms[0], noms[1]))

        # Le panneau annonce pour qui il travaille.
        etat = pg.evaluate("""() => {
            S.sceneCible = S.panels[2].id; majCibleDecor();
            const vu = { txt: $('mstCibleTxt').textContent,
                         cache: $('mstCible').hidden,
                         bouton: $('btnMaster').textContent };
            S.sceneCible = null; majCibleDecor();
            vu.apres = $('mstCible').hidden;
            return vu;
        }""")
        verifie("le panneau de décor annonce qu'il vise une scène",
                (not etat["cache"]) and "scène" in etat["txt"]
                and "scène" in etat["bouton"] and etat["apres"] is True,
                "%s / %s" % (etat["txt"][:60], etat["bouton"]))

        # --- LIVE : le chemin le plus risque, celui qui ECRIT ----------------
        # Tout ce qui precede lit. Ici on genere pour de vrai (~30 s de GPU) et
        # on verifie ou le decor ATTERRIT : sur la scene, jamais sur la planche.
        # Un banc qui ne teste que la lecture laisserait passer l'erreur la plus
        # couteuse -- ecraser le fond maitre de la planche sans le dire.
        if args.live:
            # ⚠ ON EFFACE LE DECOR FACTICE DES TESTS PRECEDENTS AVANT D'ATTENDRE.
            # Premier jet : l'attente portait sur `sceneMaster.depthInput`, un
            # champ que le decor factice du test 5 possedait DEJA -- elle rendait
            # donc la main instantanement, et le banc lisait le faux decor en
            # croyant lire le vrai. Trois « echecs » qui n'existaient pas, et la
            # generation, elle, etait juste. Un banc doit remettre son decor a
            # zero entre deux cas, et attendre un temoin qu'il vient de VIDER.
            pg.evaluate("""() => {
                S.page.master = null;
                const r = Object.assign({}, S.panels[2].recipe);
                delete r.sceneMaster;
                S.panels[2].recipe = r;
                S.sceneCible = S.panels[2].id;
                $('mstPrompt').value = 'empty school corridor, lockers, tiled floor';
                majCibleDecor();
            }""")
            pg.click("#btnMaster")
            pg.wait_for_function(
                """() => { const p = S.panels[2];
                           return !!(p.recipe && p.recipe.sceneMaster
                                     && p.recipe.sceneMaster.fond); }""",
                timeout=300000)
            ou = pg.evaluate("""() => ({
                scene: (S.panels[2].recipe.sceneMaster || {}),
                planche: S.page.master || null })""")
            verifie("le décor généré atterrit sur la SCÈNE", bool(ou["scene"].get("fond")),
                    ou["scene"].get("fond", ""))
            verifie("… et PAS sur la planche (elle n'avait pas de fond maître)",
                    not ou["planche"], "%s" % (ou["planche"] or "aucun"))
            verifie("le fichier porte l'id de la scène (pas d'écrasement possible)",
                    S_ID(ou["scene"].get("fond", "")), ou["scene"].get("fond", ""))
            rechargee = pg.evaluate("""async () => {
                const l = ((await api('/manga/panels?page=' + S.page.id)).items || []);
                return !!(l[2] && l[2].recipe && l[2].recipe.sceneMaster
                          && l[2].recipe.sceneMaster.depthInput);
            }""")
            verifie("il survit à un rechargement (il est en base)", rechargee)

        pg.evaluate("""async ([proj, k, j, f]) => {
            await api('/manga/projects', {delete: proj});
            for (const id of [k, j, f]) await api('/manga/chars', {delete: id});
        }""", [base["proj"], base["k"], base["j"], base["f"]])
        br.close()

    verifie("aucune erreur JS", not erreurs, "; ".join(erreurs[:2]))
    ko = [n for n, ok in cas if not ok]
    print("\n%d/%d" % (len(cas) - len(ko), len(cas)))
    if args.muter:
        if ko:
            print("MUTATION : rouge comme attendu (%d cas) — le banc mord." % len(ko))
            return 0
        print("MUTATION : VERTE = le banc ne teste pas l'héritage de scène.")
        return 1
    for n in ko:
        print("  - " + n)
    return 1 if ko else 0


if __name__ == "__main__":
    sys.exit(main())
