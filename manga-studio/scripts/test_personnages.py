# -*- coding: utf-8 -*-
"""La base de personnages et le CASTING d'une planche.

Quang, 27/07 : « je ne comprends pas a quel moment je peux selectionner les
personnages que j'aurai dans ma base de donnees [...] c'est plus un controle
qu'un aleatoire. »

Une fiche est GLOBALE (reutilisable d'un manga a l'autre) ; le CASTING dit qui
joue sur CETTE planche. Ce banc suit le chemin complet : creer une fiche, la
cocher, verifier que ses tags arrivent VRAIMENT dans le prompt envoye au
moteur, decocher, verifier qu'ils disparaissent, puis supprimer la fiche.

Le point qui compte : deux personnages coches doivent produire DEUX jeux de
tags ET faire disparaitre « solo ». Sans ca, une scene a deux ne montre qu'un
corps -- exactement ce que Quang a obtenu le 27/07.

Usage:
    python test_personnages.py [--headed]
    python test_personnages.py --muter     # DOIT virer au rouge
"""
import argparse
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
APP_URL = "http://127.0.0.1:8190/manga"
LARGEUR, HAUTEUR = 360, 780
NOM = "_perso_%d" % os.getpid()
A = {"nom": "Kimiko" + str(os.getpid()), "tags": "kmk1girl, sailor uniform, long black hair"}
B = {"nom": "Maitre" + str(os.getpid()), "tags": "mst1boy, old man, beard, kimono"}

cas = []


def verifie(nom, ok, detail=""):
    cas.append((nom, bool(ok), detail))
    print(("  OK   " if ok else "  ECHEC") + " " + nom + ((" — " + detail) if detail else ""))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--muter", action="store_true",
                    help="le casting cesse d'alimenter le prompt : DOIT virer au rouge")
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright

    secret = open(SECRET_FILE, encoding="utf-8").read().strip()
    erreurs = []
    ids = []
    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=not args.headed, channel="msedge")
        pg = br.new_page(viewport={"width": LARGEUR, "height": HAUTEUR},
                         is_mobile=True, has_touch=True)
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        pg.on("dialog", lambda d: d.accept())
        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)

        if args.muter:
            # MUTATION : le casting n'alimente plus le prompt. C'est le defaut
            # « le personnage coche ne change rien a l'image », qui ne se voit
            # nulle part ailleurs que dans le prompt final.
            pg.evaluate("() => { tagsCasting = () => []; }")

        # --- une planche a nous ---
        # ⚠ `/manga/pages` en ECRITURE rend {ok, id} -- PAS une planche. Et l'upsert
        # serveur reecrit TOUS les champs : mettre cette reponse dans S.page fait
        # que le prochain enregistrement (le casting) renvoie une planche SANS
        # projectId, donc ORPHELINE, en silence. On relit la planche apres l'avoir
        # creee, exactement comme le fait `loadPages` dans l'app.
        page_id = pg.evaluate("""async (nom) => {
            const proj = await api('/manga/projects', {name: nom, slug: nom});
            const cree = await api('/manga/pages', {projectId: proj.id, title: nom,
                                                    chapter: '1', idx: 0, layout: {cols: 2}});
            const pageR = ((await api('/manga/pages?project=' + proj.id)).items || [])
                            .find(x => x.id === cree.id);
            const pan = await api('/manga/panels', {pageId: pageR.id, kind: 'dialogue',
                                                    prompt: 'walking in the street', idx: 0});
            S.proj = proj; S.page = pageR;
            S.panels = [{id: pan.id, page_id: pageR.id, kind: 'dialogue',
                         prompt: 'walking in the street', bubbles: [], recipe: {}}];
            renderPlate();
            return pageR.id;
        }""", NOM)

        print("\n--- creer deux fiches, par l'UI ---")
        pg.click('nav button[data-tab="tPerso"]')
        pg.wait_for_timeout(500)
        for f in (A, B):
            pg.fill("#chName", f["nom"])
            pg.fill("#chTags", f["tags"])
            pg.click("#btnNewChar")
            pg.wait_for_timeout(900)
        noms = pg.evaluate("CHARS.map(c => c.name)")
        verifie("les deux fiches sont creees",
                A["nom"] in noms and B["nom"] in noms, "%d fiche(s) en base" % len(noms))
        # ⚠ Par NOM, un a un : la base contient deja d'autres fiches, et l'ordre de
        # CHARS n'est pas l'ordre de creation. Un `filter` rendait les deux ids
        # inverses -- le banc accusait alors l'app d'un desordre qui etait le sien.
        ids = [pg.evaluate("(n) => (CHARS.find(c => c.name === n) || {}).id", A["nom"]),
               pg.evaluate("(n) => (CHARS.find(c => c.name === n) || {}).id", B["nom"])]
        verifie("les deux fiches sont retrouvees par leur nom",
                all(ids), "ids=%s" % (ids,))

        print("\n--- le casting de la planche ---")
        pg.click('nav button[data-tab="tPlate"]')
        pg.wait_for_timeout(700)
        boites = pg.evaluate("document.querySelectorAll('#casting input[data-cast]').length")
        verifie("les fiches apparaissent dans « Qui joue sur cette planche »",
                boites >= 2, "%s case(s) a cocher" % boites)

        def final():
            return pg.evaluate("promptFinal(S.panels[0])")

        sans = final()
        verifie("sans casting : aucun tag de personnage dans le prompt",
                "kmk1girl" not in sans and "mst1boy" not in sans, sans[-60:])

        # cocher LE PREMIER
        pg.check('#casting input[data-cast="%s"]' % ids[0])
        pg.wait_for_timeout(900)
        un = final()
        verifie("1 personnage coche : ses tags arrivent dans le prompt",
                "kmk1girl" in un, un[-80:])
        verifie("1 personnage coche : le second n'y est PAS", "mst1boy" not in un)

        # cocher LE SECOND aussi
        pg.check('#casting input[data-cast="%s"]' % ids[1])
        pg.wait_for_timeout(900)
        deux = final()
        verifie("2 personnages : les tags des DEUX arrivent",
                "kmk1girl" in deux and "mst1boy" in deux, deux[-100:])
        verifie("2 personnages : « solo » ne part pas au moteur",
                "solo" not in deux.lower())
        verifie("2 personnages : l'ordre du casting est respecte",
                "kmk1girl" in deux and "mst1boy" in deux
                and deux.index("kmk1girl") < deux.index("mst1boy"))

        # le casting doit SURVIVRE au rechargement : il vit sur la planche.
        pg.reload(wait_until="domcontentloaded")
        pg.wait_for_timeout(3000)
        # Une mutation posee dans la page MEURT avec elle : sans ce rappel, tout ce
        # qui suit un rechargement echapperait au controle et le banc se croirait
        # falsifiable alors qu'il ne l'est qu'a moitie.
        if args.muter:
            pg.evaluate("() => { tagsCasting = () => []; }")
        # ⚠ Apres rechargement, `S.proj` est le dernier projet OUVERT, pas forcement
        # le notre : on relit la planche par son id, pas par l'etat de l'app.
        garde = pg.evaluate("""async ([nom, pid]) => {
            const projs = (await api('/manga/projects')).items || [];
            const proj = projs.find(p => p.name === nom);
            if (!proj) return -1;
            const pages = (await api('/manga/pages?project=' + proj.id)).items || [];
            const p = pages.find(x => x.id === pid);
            return ((p && p.layout && p.layout.casting) || []).length;
        }""", [NOM, page_id])
        verifie("le casting est enregistre sur la planche (survit au rechargement)",
                garde == 2, "%s personnage(s) retenu(s)" % garde)

        # --- decocher le SECOND (on garde A) ---
        moins = pg.evaluate("""async ([nom, pid, garde]) => {
            const projs = (await api('/manga/projects')).items || [];
            const proj = projs.find(p => p.name === nom);
            const pages = (await api('/manga/pages?project=' + proj.id)).items || [];
            const page = pages.find(x => x.id === pid);
            page.layout = Object.assign({}, page.layout, {casting: [garde]});
            await api('/manga/pages', page);
            S.proj = proj; S.page = page;
            S.panels = [{id: 'x', kind: 'dialogue', prompt: 'walking in the street', recipe: {}}];
            return promptFinal(S.panels[0]);
        }""", [NOM, page_id, ids[0]])
        verifie("decoche : les tags du personnage retire disparaissent",
                "mst1boy" not in moins and "kmk1girl" in moins, moins[-80:])

        # --- supprimer les fiches ---
        pg.evaluate("""async ([ids, nom]) => {
            for (const id of ids) await api('/manga/chars', {delete: id});
            const projs = (await api('/manga/projects')).items || [];
            const proj = projs.find(p => p.name === nom);
            if (proj) await api('/manga/projects', {delete: proj.id});
        }""", [ids, NOM])
        pg.wait_for_timeout(600)
        reste = pg.evaluate("""async (n) => {
            const c = (await api('/manga/chars')).items || [];
            return c.filter(x => n.includes(x.name)).length;
        }""", [A["nom"], B["nom"]])
        verifie("les fiches supprimees ne sont plus en base",
                reste == 0, "%s fiche(s) restante(s)" % reste)
        br.close()

    verifie("aucune erreur JS", not erreurs, "; ".join(erreurs[:2]))

    rates = [c for c in cas if not c[1]]
    print("\n=== %d/%d verifications passees ===" % (len(cas) - len(rates), len(cas)))
    if args.muter:
        if rates:
            print("MUTATION : le banc vire au rouge — il sait donc echouer. OK")
            return 0
        print("MUTATION : le banc reste VERT alors que le casting n'alimente plus rien.")
        return 1
    for nom, _, det in rates:
        print("  - " + nom + ((" (" + det + ")") if det else ""))
    return 1 if rates else 0


if __name__ == "__main__":
    sys.exit(main())
