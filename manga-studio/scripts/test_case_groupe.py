# -*- coding: utf-8 -*-
"""La case-groupe : une sequence occupe UNE place, sans rien perdre.

Quang, 27/07 : « je trouve ca deroutant quand on cree une sequence […] que chaque
image soit chronologiquement l'une apres l'autre dans la presentation. Je les
imagine plutot regroupees ensemble sur la meme fenetre, avec un bouton pouvant
les faire defiler […] suivant/precedent avec l'affichage du numero d'image. »

Ce que le banc verifie :

  - 6 vignettes + 2 cases normales = 3 blocs a l'ecran, pas 8 ;
  - ◀ ▶ changent la vignette montree, le numero suit, et ca BOUCLE (un bouton
    qui ne repond pas au bout passe pour casse) ;
  - « deplier » rend les 6 cases visibles, « regrouper » les remet ;
  - ⚠ LE POINT QUI COMPTE : les DONNEES ne sont pas fusionnees. L'export lit
    `S.panels` -- il doit toujours voir les 8 cases, sinon le confort d'ecran
    aurait detruit le livrable ;
  - supprimer une vignette ne casse pas le groupe, et l'index affiche se
    recale s'il pointait au-dela de la fin.

Zero GPU : les vignettes sont posees a la main, on mesure un affichage.

Usage:
    python test_case_groupe.py [--headed]
    python test_case_groupe.py --muter    # DOIT virer au rouge
"""
import argparse
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
APP_URL = "http://127.0.0.1:8190/manga"
NOM = "_grp_%d" % os.getpid()

cas = []


def verifie(nom, ok, detail=""):
    cas.append((nom, bool(ok), detail))
    print(("  OK   " if ok else "  ECHEC") + " " + nom + ((" — " + detail) if detail else ""),
          flush=True)
    return ok


# 2 cases normales, puis 6 vignettes d'une meme sequence.
PREPARE = """async ([nom]) => {
    const rep = await api('/manga/projects', {name: nom, slug: nom, recipe: {}});
    const proj = ((await api('/manga/projects')).items || []).find(x => x.id === rep.id);
    const cree = await api('/manga/pages', {projectId: proj.id, title: nom,
                                            chapter: '1', idx: 0, layout: {cols: 2}});
    const page = ((await api('/manga/pages?project=' + proj.id)).items || [])
                   .find(x => x.id === cree.id);
    for (let i = 0; i < 8; i++){
        await api('/manga/panels', {pageId: page.id, kind: 'dialogue',
                                    prompt: 'case ' + i, idx: i});
    }
    S.proj = proj; S.page = page;
    S.panels = ((await api('/manga/panels?page=' + page.id)).items || [])
                 .sort((a, b) => a.idx - b.idx);
    S.panels.forEach((p, i) => {
        p.file = nom + '/c' + i + '.png';
        if (i >= 2){
            p.recipe = {seed: 4242, sequence: {index: i - 2, total: 6,
                                               geste: 'marche', gid: 'g_' + nom}};
        }
    });
    renderPlate();
    return {proj: proj.id, gid: 'g_' + nom, ids: S.panels.map(p => p.id)};
}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--muter", action="store_true",
                    help="le groupe FUSIONNE les cases (les autres disparaissent) : DOIT rougir")
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright

    secret = open(SECRET_FILE, encoding="utf-8").read().strip()
    erreurs = []

    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=not args.headed, channel="msedge")
        pg = br.new_page(viewport={"width": 390, "height": 820},
                         is_mobile=True, has_touch=True)
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_timeout(3000)
        d = pg.evaluate(PREPARE, [NOM])

        if args.muter:
            # MUTATION : le regroupement va jusqu'aux DONNEES -- les 5 autres
            # vignettes sont retirees de la planche. A l'ecran c'est identique,
            # et c'est bien le probleme : l'export perd 5 cases en silence.
            pg.evaluate("""([gid]) => {
                const soeurs = S.panels.filter(p => p.recipe && p.recipe.sequence
                                                 && p.recipe.sequence.gid === gid);
                const garde = soeurs[0];
                S.panels = S.panels.filter(p => !soeurs.includes(p) || p === garde);
                renderPlate();
            }""", [d["gid"]])

        # ---------- 1. une sequence = UN bloc ----------
        blocs = pg.eval_on_selector_all("#plate > .panel, #plate > .groupe", "els => els.length")
        verifie("8 cases dont 6 en sequence = 3 blocs a l'ecran",
                blocs == 3, "%d bloc(s)" % blocs)
        cases_vues = pg.eval_on_selector_all("#plate .panel", "els => els.length")
        verifie("une seule vignette de la sequence est montree",
                cases_vues == 3, "%d case(s) visible(s)" % cases_vues)

        # ---------- 2. LE POINT QUI COMPTE : les donnees restent entieres ----------
        verifie("la planche contient TOUJOURS 8 cases (l'export lit S.panels)",
                pg.evaluate("S.panels.length") == 8,
                "%d case(s) en memoire" % pg.evaluate("S.panels.length"))

        # ---------- 3. naviguer dans le groupe ----------
        n0 = pg.eval_on_selector(".groupe .grpbar b", "el => el.textContent")
        verifie("le groupe s'ouvre sur la 1re vignette", "1/6" in n0, n0)
        pg.click('[data-grp="next"]')
        pg.wait_for_timeout(400)
        n1 = pg.eval_on_selector(".groupe .grpbar b", "el => el.textContent")
        verifie("« suivant » avance d'une vignette", "2/6" in n1, n1)
        montre = pg.eval_on_selector(".groupe .panel", "el => el.dataset.pid")
        verifie("... et c'est bien la 2e case qui est affichee",
                montre == d["ids"][3], montre)
        pg.click('[data-grp="prev"]'); pg.wait_for_timeout(300)
        pg.click('[data-grp="prev"]'); pg.wait_for_timeout(400)
        n2 = pg.eval_on_selector(".groupe .grpbar b", "el => el.textContent")
        verifie("« precedent » boucle au bout de la serie", "6/6" in n2, n2)

        # ---------- 4. deplier / regrouper ----------
        pg.click('[data-grp="deplier"]')
        pg.wait_for_timeout(600)
        verifie("« deplier » montre les 6 cases",
                pg.eval_on_selector_all("#plate .panel", "els => els.length") == 8,
                "%d case(s)" % pg.eval_on_selector_all("#plate .panel", "els => els.length"))
        pg.click('[data-grp="replier"]')
        pg.wait_for_timeout(600)
        verifie("« regrouper » les remet dans un bloc",
                pg.eval_on_selector_all("#plate .panel", "els => els.length") == 3)

        # ---------- 5. REORDONNER (v1.42.0) ----------
        # On revient sur la 1re vignette, puis on la pousse d'un cran.
        # ⚠ Boucle BORNEE : sous mutation le groupe ne contient qu'une vignette,
        # « 1/6 » n'arrive jamais et la version non bornee tournait a l'infini --
        # le banc mourait sur un timeout au lieu d'annoncer un echec.
        for _ in range(8):
            if "1/6" in pg.eval_on_selector(".groupe .grpbar b", "el => el.textContent"):
                break
            pg.click('[data-grp="next"]'); pg.wait_for_timeout(250)
        avant_ordre = pg.evaluate("""(gid) => S.panels
            .filter(p => p.recipe && p.recipe.sequence && p.recipe.sequence.gid === gid)
            .sort((a, b) => a.recipe.sequence.index - b.recipe.sequence.index)
            .map(p => p.id)""", d["gid"])
        # ⚠ On CONSTATE l'absence des boutons au lieu de mourir dessus : sous
        # mutation la sequence n'a qu'une vignette, donc ils ne sont pas rendus.
        # Un banc qui touche a une UI mouvante doit savoir echouer proprement.
        a_boutons = pg.eval_on_selector_all('[data-grp="gauche"]', "els => els.length") == 1
        verifie("« plus tot » est desactive sur la 1re vignette",
                a_boutons and pg.eval_on_selector('[data-grp="gauche"]',
                                                  "el => el.disabled") is True,
                "boutons de deplacement absents" if not a_boutons else "")
        if a_boutons:
            pg.click('[data-grp="droite"]')
            pg.wait_for_timeout(1500)
        apres_ordre = pg.evaluate("""(gid) => S.panels
            .filter(p => p.recipe && p.recipe.sequence && p.recipe.sequence.gid === gid)
            .sort((a, b) => a.recipe.sequence.index - b.recipe.sequence.index)
            .map(p => p.id)""", d["gid"])
        assez = len(avant_ordre) >= 2 and len(apres_ordre) >= 2
        verifie("la vignette a bien echange sa place avec la suivante",
                assez and apres_ordre[0] == avant_ordre[1]
                and apres_ordre[1] == avant_ordre[0],
                "%s -> %s" % (avant_ordre[:2], apres_ordre[:2]))
        verifie("on continue de VOIR la vignette deplacee",
                "2/6" in pg.eval_on_selector(".groupe .grpbar b", "el => el.textContent"),
                pg.eval_on_selector(".groupe .grpbar b", "el => el.textContent"))
        # ⚠ L'ORDRE DE LA PLANCHE doit suivre, sinon l'ecran dit l'inverse du PNG :
        # `buildPlateCanvas` lit S.panels dans l'ordre, que la base trie par `idx`.
        ordre_planche = pg.evaluate("""(ids) => S.panels
            .filter(p => ids.includes(p.id))
            .sort((a, b) => (a.idx || 0) - (b.idx || 0))
            .map(p => p.id)""", avant_ordre[:2])
        verifie("l'ordre de la PLANCHE suit (donc l'export aussi)",
                assez and len(ordre_planche) >= 1
                and ordre_planche[0] == avant_ordre[1], str(ordre_planche))

        # on remet la sequence dans son ordre d'origine
        if a_boutons:
            pg.click('[data-grp="gauche"]')
            pg.wait_for_timeout(1500)

        # ---------- 6. supprimer une vignette ne casse rien ----------
        pg.evaluate("""(id) => {
            S.panels = S.panels.filter(p => p.id !== id);
            renderPlate();
        }""", d["ids"][4])
        pg.wait_for_timeout(600)
        n3 = pg.eval_on_selector(".groupe .grpbar b", "el => el.textContent")
        verifie("apres suppression, le groupe compte 5 vignettes", "/5" in n3, n3)
        verifie("l'index affiche se recale s'il depassait la fin",
                "6/5" not in n3 and "0/" not in n3, n3)
        verifie("aucune erreur JS", not erreurs, "; ".join(erreurs[:2]))

        try:
            pg.evaluate("(id) => api('/manga/projects', {delete: id})", d["proj"])
        except Exception:
            pass
        pg.wait_for_timeout(400)
        br.close()

    rouges = [c for c in cas if not c[1]]
    print("\n%d verification(s), %d echec(s)" % (len(cas), len(rouges)))
    if args.muter:
        print("MUTATION : un rouge est le resultat ATTENDU.")
    return 1 if rouges else 0


if __name__ == "__main__":
    sys.exit(main())
