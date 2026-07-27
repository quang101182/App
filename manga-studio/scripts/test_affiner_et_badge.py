# -*- coding: utf-8 -*-
"""⚙ Affiner : moins de boutons, sans rien perdre. Et le badge qui ne ment plus.

Deux livraisons liees (v1.30.0), nees de la meme phrase de Quang le 27/07 :
« on empile beaucoup de choses au fur et a mesure, et on peut vite perdre
l'ergonomie de l'application ».

  - **Le budget de boutons.** Avant : 11 boutons sur une case generee. Le banc
    COMPTE ce que l'ecran affiche -- une refonte d'ergonomie qui ne se mesure
    pas est une opinion. Il verifie aussi que tout ce qui a quitte la rangee est
    bien RETROUVABLE dans le panneau : simplifier en perdant une fonction, ce
    n'est pas simplifier.

  - **Le badge « 3/6 ».** Il etait ecrit une fois pour toutes a la creation de la
    sequence. Supprimer une vignette laissait donc une serie de 5 afficher
    « /6 », avec des numeros qui sautent. Le banc supprime une vignette du
    MILIEU et exige une renumerotation complete.

Le piege le plus serieux de cette refonte est verifie explicitement : le champ
seed vit maintenant dans un panneau REPLIABLE, et `genPanel` le lisait sans
garde. Panneau ferme, generer jetait une TypeError et ne dessinait rien.

Zero GPU : la generation est interceptee (on verifie qu'elle PART, avec la
bonne seed -- pas ce qu'elle produit).

Usage:
    python test_affiner_et_badge.py [--headed]
    python test_affiner_et_badge.py --muter    # DOIT virer au rouge
"""
import argparse
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
APP_URL = "http://127.0.0.1:8190/manga"
LARGEUR, HAUTEUR = 360, 780
NOM = "_affiner_%d" % os.getpid()

cas = []


def verifie(nom, ok, detail=""):
    cas.append((nom, bool(ok), detail))
    print(("  OK   " if ok else "  ECHEC") + " " + nom + ((" — " + detail) if detail else ""))
    return ok


PREPARE = """async ([nom, n]) => {
    const proj = await api('/manga/projects', {name: nom, slug: nom});
    const cree = await api('/manga/pages', {projectId: proj.id, title: nom,
                                            chapter: '1', idx: 0, layout: {cols: 2}});
    const page = ((await api('/manga/pages?project=' + proj.id)).items || [])
                   .find(x => x.id === cree.id);
    for (let i = 0; i < n; i++){
        await api('/manga/panels', {pageId: page.id, kind: 'dialogue',
                                    prompt: 'vignette ' + i, idx: i});
    }
    S.proj = proj; S.page = page;
    S.panels = ((await api('/manga/panels?page=' + page.id)).items || [])
                 .sort((a, b) => a.idx - b.idx);
    S.panels.forEach((p, i) => {
        p.file = nom + '/v' + i + '.png';
        // gid = identifiant de groupe (v1.31.0) : l'appartenance a une sequence
        // ne se deduit plus de la seed, sinon retenter UNE vignette avec une
        // autre seed la ferait sortir de sa serie.
        p.recipe = {seed: 424242,
                    sequence: {index: i, total: n, geste: 'marche', gid: 'g_' + nom}};
    });
    renderPlate();
    return {proj: proj.id, ids: S.panels.map(p => p.id)};
}"""


def badges(pg):
    return pg.eval_on_selector_all(".seqbadge", "els => els.map(e => e.textContent.trim())")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--muter", action="store_true",
                    help="le badge redevient fige a la creation : DOIT virer au rouge")
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright

    secret = open(SECRET_FILE, encoding="utf-8").read().strip()
    erreurs = []
    envoyes = []

    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=not args.headed, channel="msedge")
        pg = br.new_page(viewport={"width": LARGEUR, "height": HAUTEUR},
                         is_mobile=True, has_touch=True)
        pg.on("pageerror", lambda e: erreurs.append(str(e)))

        def intercepte(route):
            try:
                import json as _j
                envoyes.append(_j.loads(route.request.post_data or "{}"))
            except Exception:
                envoyes.append({})
            route.fulfill(status=200, content_type="application/json",
                          body='{"prompt_id": "_banc_"}')
        pg.route("**/comfy/prompt", intercepte)

        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)

        if args.muter:
            # MUTATION : on revient au badge FIGE, lu dans la recette. Rien ne
            # plante, l'ecran reste plausible -- il ment juste apres suppression.
            pg.evaluate("""() => {
                window.posSequence = (p) => {
                    const sq = p.recipe && p.recipe.sequence;
                    return sq ? {n: sq.index + 1, total: sq.total} : null;
                };
            }""")

        d = pg.evaluate(PREPARE, [NOM, 6])

        # ---------- 1. le budget de boutons ----------
        sel = '[data-pid="%s"]' % d["ids"][0]
        # On compte ce que l'utilisateur VOIT : les boutons de lettrage sont dans
        # le DOM en permanence mais masques hors mode lettrage. Compter le DOM
        # aurait donne « 11 boutons » avant comme apres la refonte -- une mesure
        # juste sur le mauvais objet ne mesure rien.
        VISIBLES = "els => els.filter(e => e.offsetParent !== null)"
        n_boutons = pg.eval_on_selector_all(sel + " button[data-act]",
                                            VISIBLES + ".length")
        verifie("une case generee tient sous 7 boutons visibles (11 avant)",
                n_boutons <= 7, "%d boutons" % n_boutons)
        actes = pg.eval_on_selector_all(sel + " button[data-act]",
                                        VISIBLES + ".map(e => e.dataset.act)")
        verifie("le geste du moment reste dehors (generer, lettrer, juger, jouer)",
                all(a in actes for a in ["gen", "letter", "ok", "ko", "jouer", "affiner"]),
                ", ".join(actes))
        verifie("ce qui affine a QUITTE la rangee",
                not any(a in actes for a in ["ameliorer", "idees", "sequence", "zone", "del"]),
                ", ".join(actes))
        verifie("le champ seed n'encombre plus la case fermee",
                pg.eval_on_selector_all(sel + " [data-seed]", "els => els.length") == 0)

        # ---------- 2. rien n'a disparu : tout est dans le panneau ----------
        pg.click(sel + ' [data-act="affiner"]')
        pg.wait_for_timeout(400)
        dans = pg.eval_on_selector_all(sel + " .affiner button[data-act]",
                                       "els => els.map(e => e.dataset.act)")
        verifie("le panneau contient bien ce qui a quitte la rangee",
                all(a in dans for a in ["ameliorer", "idees", "sequence", "zone", "del"]),
                ", ".join(dans))
        verifie("le champ seed est retrouvable",
                pg.eval_on_selector_all(sel + " [data-seed]", "els => els.length") == 1)

        # ---------- 3. un seul panneau a la fois ----------
        pg.click('[data-pid="%s"] [data-act="affiner"]' % d["ids"][1])
        pg.wait_for_timeout(400)
        ouverts = pg.eval_on_selector_all(".panel .affiner", "els => els.length")
        verifie("un seul panneau deplie a la fois", ouverts == 1, "%d ouverts" % ouverts)

        # ---------- 4. LE PIEGE : generer AU PANNEAU FERME ----------
        pg.click('[data-pid="%s"] [data-act="affiner"]' % d["ids"][1])   # on referme
        pg.wait_for_timeout(300)
        avant = len(envoyes)
        pg.click('[data-pid="%s"] [data-act="gen"]' % d["ids"][2])
        pg.wait_for_timeout(2500)
        verifie("generer marche AVEC le panneau ferme (piege du champ seed)",
                len(envoyes) > avant, "%d requete(s) au moteur" % (len(envoyes) - avant))
        verifie("aucune erreur JS a la generation", not erreurs, "; ".join(erreurs[:2]))

        # ---------- 5. une seed fixee survit a la fermeture du panneau ----------
        sel3 = '[data-pid="%s"]' % d["ids"][3]
        pg.click(sel3 + ' [data-act="affiner"]')
        pg.wait_for_timeout(300)
        pg.fill(sel3 + " [data-seed]", "13579")
        pg.dispatch_event(sel3 + " [data-seed]", "change")
        pg.wait_for_timeout(600)
        pg.click(sel3 + ' [data-act="affiner"]')      # referme
        pg.wait_for_timeout(300)
        avant = len(envoyes)
        pg.click(sel3 + ' [data-act="gen"]')
        pg.wait_for_timeout(2500)
        seed_vue = pg.evaluate("(id) => { const p = S.panels.find(x => x.id === id);"
                               " return p && p.recipe && p.recipe.seed; }", d["ids"][3])
        verifie("une seed fixee n'est pas perdue en repliant le panneau",
                seed_vue == 13579, "seed utilisee : %s" % seed_vue)

        # ---------- 6. LE BADGE : il doit dire la verite ----------
        vus = badges(pg)
        verifie("6 vignettes, numerotees 1..6",
                vus == ["🎬 %d/6" % i for i in range(1, 7)], " ".join(vus))

        # on supprime la 3e (au MILIEU : c'est la que le mensonge se voyait)
        pg.evaluate("""async (id) => {
            await api('/manga/panels', {delete: id});
            S.panels = S.panels.filter(x => x.id !== id);
            renderPlate();
        }""", d["ids"][2])
        pg.wait_for_timeout(800)
        vus = badges(pg)
        verifie("apres suppression : 5 vignettes, renumerotees 1..5",
                vus == ["🎬 %d/5" % i for i in range(1, 6)], " ".join(vus))
        verifie("aucun numero ne saute", "🎬 4/6" not in vus and "🎬 6/6" not in vus,
                " ".join(vus))

        try:
            pg.evaluate("(id) => api('/manga/projects', {delete: id})", d["proj"])
        except Exception:
            pass
        pg.wait_for_timeout(400)
        br.close()

    verifie("aucune erreur JS sur tout le parcours", not erreurs, "; ".join(erreurs[:3]))
    rouges = [c for c in cas if not c[1]]
    print("\n%d verification(s), %d echec(s)" % (len(cas), len(rouges)))
    if args.muter:
        print("MUTATION : un rouge est le resultat ATTENDU.")
    return 1 if rouges else 0


if __name__ == "__main__":
    sys.exit(main())
