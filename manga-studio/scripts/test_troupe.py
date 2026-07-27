# -*- coding: utf-8 -*-
"""La troupe d'un manga : trois niveaux, et l'heritage d'une planche neuve.

Quang, 27/07 : « c'est quoi la suite quand je cree des personnages, que je cree
un nouveau projet, comment j'ai inclus ces personnages dans le projet ? »

La question a revele deux manques :
  - le casting appartenait a la PLANCHE seule, donc chaque planche neuve
    repartait vide -- vingt planches de chapitre = vingt fois le meme geste ;
  - la ligne affichait TOUTE la base en cases a cocher, en travers de l'ecran.

Trois niveaux desormais : la BASE (toutes les fiches) -> la TROUPE du projet
-> le CASTING de la planche.

Ce que le banc verifie :
  - la ligne ne montre QUE la troupe, pas la base entiere ;
  - ajouter quelqu'un a la troupe le fait jouer AUSSI sur la planche ouverte
    (sinon le geste est a faire deux fois, et on croit que le clic n'a rien fait) ;
  - une planche NEUVE herite de la troupe -- c'est tout l'objet du chantier ;
  - la nuance qui compte : casting ABSENT = « je suis la troupe », casting VIDE
    = « personne sur cette page ». Decocher tout le monde ne doit PAS faire
    revenir la troupe au prochain chargement ;
  - les tags du personnage arrivent bien dans le prompt de la case ;
  - « Demarrer une planche » ne passe plus par une boite native.

Zero GPU : on lit le graphe envoye au moteur, on ne genere rien.

Usage:
    python test_troupe.py [--headed]
    python test_troupe.py --muter    # DOIT virer au rouge
"""
import argparse
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
APP_URL = "http://127.0.0.1:8190/manga"
NOM = "_troupe_%d" % os.getpid()

cas = []


def verifie(nom, ok, detail=""):
    cas.append((nom, bool(ok), detail))
    print(("  OK   " if ok else "  ECHEC") + " " + nom + ((" — " + detail) if detail else ""),
          flush=True)
    return ok


PREPARE = """async ([nom]) => {
    const rep = await api('/manga/projects', {name: nom, slug: nom,
        recipe: {style: 'kabukigravure, black and white'}});
    const proj = ((await api('/manga/projects')).items || []).find(x => x.id === rep.id);
    const cree = await api('/manga/pages', {projectId: proj.id, title: nom,
                                            chapter: '1', idx: 0, layout: {cols: 2}});
    const page = ((await api('/manga/pages?project=' + proj.id)).items || [])
                   .find(x => x.id === cree.id);
    await api('/manga/panels', {pageId: page.id, kind: 'dialogue',
                                prompt: 'walking in a corridor', idx: 0});
    // Trois fiches en base : la ligne ne doit PAS toutes les afficher.
    const a = await api('/manga/chars', {name: nom + '-A', tags: 'tagdelaou', role: 'heros'});
    const b = await api('/manga/chars', {name: nom + '-B', tags: 'tagdelabe', role: 'secondaire'});
    const c = await api('/manga/chars', {name: nom + '-C', tags: 'tagdelace', role: 'figurant'});
    S.proj = proj; S.page = page;
    await loadChars();
    S.panels = ((await api('/manga/panels?page=' + page.id)).items || []);
    renderPlate(); renderCasting();
    return {proj: proj.id, page: page.id, pid: S.panels[0].id, a: a.id, b: b.id, c: c.id};
}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--muter", action="store_true",
                    help="une planche neuve n'herite plus : DOIT virer au rouge")
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright

    secret = open(SECRET_FILE, encoding="utf-8").read().strip()
    erreurs, prompts = [], []

    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=not args.headed, channel="msedge")
        pg = br.new_page(viewport={"width": 390, "height": 820},
                         is_mobile=True, has_touch=True)
        pg.on("pageerror", lambda e: erreurs.append(str(e)))

        def voir(route):
            try:
                wf = (json.loads(route.request.post_data or "{}").get("prompt")) or {}
                for n in wf.values():
                    if n.get("class_type") == "CLIPTextEncode":
                        prompts.append(n.get("inputs", {}).get("text", ""))
                        break
            except Exception:
                pass
            route.fulfill(status=200, content_type="application/json",
                          body='{"prompt_id": "_banc_"}')
        pg.route("**/comfy/prompt", voir)

        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_timeout(3000)
        d = pg.evaluate(PREPARE, [NOM])

        # MUTATION : on retire l'HERITAGE, c'est-a-dire le comportement d'avant
        # le chantier -- une planche ne connait que son propre casting.
        #
        # Deux versions de cette mutation ont d'abord echoue a rougir, et les
        # deux erreurs valent d'etre notees :
        #  1. `window.troupeProjet = ...` ne remplace pas une `const` de module
        #     (la resolution lexicale l'emporte) -- le code mute n'etait jamais
        #     appele. Les deux fonctions sont donc des DECLARATIONS depuis la
        #     v1.39.0, ce qui les rend remplacables ;
        #  2. retirer `casting` a l'ECRITURE ne cassait rien non plus : l'app
        #     herite a la LECTURE, donc une planche sans casting suivait quand
        #     meme la troupe. C'etait une bonne nouvelle sur le code, et une
        #     mauvaise sur le banc -- il visait le mauvais maillon.
        #  3. et il a fallu muter les DEUX : l'app herite a l'ecriture (une
        #     planche neuve nait avec la troupe) ET a la lecture (une planche
        #     sans casting suit la troupe). Casser un seul des deux ne change
        #     rien pour l'utilisateur -- ce qui est une bonne nouvelle sur le
        #     code, et la preuve qu'une mutation doit viser le COMPORTEMENT,
        #     pas une ligne.
        if args.muter:
            pg.evaluate("""() => {
                window.castingPage = () =>
                    (S.page && S.page.layout && S.page.layout.casting) || [];
            }""")

            def sans_casting(route):
                try:
                    body = json.loads(route.request.post_data or "{}")
                    if isinstance(body.get("layout"), dict):
                        body["layout"].pop("casting", None)
                    route.continue_(post_data=json.dumps(body))
                    return
                except Exception:
                    pass
                route.continue_()
            pg.route("**/manga/pages", sans_casting)

        # ⚠ Depuis la v1.50.0, la troupe vit dans l'onglet PROJET : c'est un
        # reglage du manga, alors que le choix d'usage se fait case par case
        # (pastilles « Qui est la »). Le banc suit ce deplacement.
        pg.click('nav button[data-tab="tProj"]')
        pg.wait_for_timeout(800)

        # ---------- 1. la ligne ne montre pas la base entiere ----------
        cases = pg.eval_on_selector_all("#casting [data-cast]", "els => els.length")
        verifie("aucune case a cocher tant que la troupe est vide",
                cases == 0, "%d case(s) pour 3 fiches en base" % cases)
        verifie("un bouton propose d'ajouter quelqu'un",
                pg.eval_on_selector_all("#btnTroupe", "els => els.length") == 1)

        # ---------- 2. ajouter a la troupe = jouer aussi sur la planche ----------
        pg.click("#btnTroupe")
        pg.wait_for_timeout(400)
        pg.click('[data-troupeadd="%s"]' % d["a"])
        pg.wait_for_timeout(1200)
        verifie("le personnage entre dans la troupe du manga",
                pg.evaluate("troupeProjet().length") == 1,
                str(pg.evaluate("troupeProjet()")))
        coche = pg.eval_on_selector('#casting [data-cast="%s"]' % d["a"], "el => el.checked")
        verifie("... et il joue tout de suite sur la planche ouverte", coche is True)

        # ---------- 3. ses tags arrivent dans la case ----------
        pg.click('nav button[data-tab="tPlate"]')
        pg.wait_for_timeout(800)
        pg.click('[data-pid="%s"] [data-act="gen"]' % d["pid"])
        pg.wait_for_timeout(2500)
        env = " ||| ".join(prompts)
        verifie("les tags du personnage arrivent dans le prompt",
                "tagdelaou" in env, env[:100])
        verifie("les fiches HORS troupe n'y sont pas",
                "tagdelabe" not in env and "tagdelace" not in env, env[:100])

        # ---------- 4. une planche NEUVE herite ----------
        pg.click("#btnNewPage")
        pg.wait_for_timeout(2000)
        herite = pg.evaluate("castingPage()")
        verifie("une planche neuve herite de la troupe",
                d["a"] in (herite or []), str(herite))

        # ---------- 5. absent ≠ vide ----------
        pg.evaluate("""async () => {
            S.page.layout = Object.assign({}, S.page.layout, {casting: []});
            await api('/manga/pages', S.page);
        }""")
        pg.wait_for_timeout(1000)
        # ⚠ On note l'id de LA planche du banc AVANT de recharger : apres, `S.page`
        # est deja la planche memorisee (celle de Quang), et on le lirait donc
        # trop tard -- l'argument aurait ete evalue sur le mauvais objet.
        page_banc = pg.evaluate("S.page && S.page.id")
        pg.reload(wait_until="domcontentloaded")
        pg.wait_for_timeout(3000)
        # ⚠ Apres un rechargement, l'app rouvre le projet et la planche MEMORISES
        # -- ceux de Quang, pas ceux du banc. Ce test mesurait donc le casting
        # d'une planche qui n'etait pas la sienne, et il n'est passe que tant que
        # cette planche-la etait vide. « Un banc vise ses objets par leur NOM,
        # jamais par l'etat de l'app » (piege deja paye sur ce projet).
        vide = pg.evaluate("""async ([proj, page]) => {
            await ouvrirProjet(proj);
            S.page = (S.pages || []).find(x => x.id === page) || S.page;
            await loadPanels();
            return castingPage();
        }""", [d["proj"], page_banc])
        verifie("une planche VIDEE volontairement le reste apres rechargement",
                vide == [], str(vide))

        # ---------- 6. retirer de la troupe ----------
        pg.evaluate("(id) => { S.proj = S.projects.find(p => p.id === id); }", d["proj"])
        pg.wait_for_timeout(300)
        pg.click('nav button[data-tab="tProj"]')
        pg.wait_for_timeout(600)
        pg.evaluate("() => renderCasting()")
        pg.wait_for_timeout(300)
        n_av = pg.evaluate("troupeProjet().length")
        pg.click('[data-troupedel="%s"]' % d["a"])
        pg.wait_for_timeout(1200)
        verifie("on peut retirer quelqu'un du manga",
                pg.evaluate("troupeProjet().length") == n_av - 1,
                "%d -> %d" % (n_av, pg.evaluate("troupeProjet().length")))

        # ---------- 7. plus de boite native pour demarrer ----------
        pg.click('nav button[data-tab="tProj"]')
        pg.wait_for_timeout(600)
        verifie("le nombre de cases se regle a l'ecran (plus de prompt natif)",
                pg.eval_on_selector_all("#npCases", "els => els.length") == 1)
        boites = []
        pg.on("dialog", lambda dl: (boites.append(dl.type), dl.dismiss()))
        pg.click("#btnDemarrer")            # champ nom VIDE : doit refuser poliment
        pg.wait_for_timeout(1200)
        verifie("sans nom, il refuse SANS boite native",
                not boites, "boites vues : %s" % boites)

        for cid in (d["a"], d["b"], d["c"]):
            try:
                pg.evaluate("(id) => api('/manga/chars', {delete: id})", cid)
            except Exception:
                pass
        try:
            pg.evaluate("(id) => api('/manga/projects', {delete: id})", d["proj"])
        except Exception:
            pass
        pg.wait_for_timeout(400)
        br.close()

    verifie("aucune erreur JS", not erreurs, "; ".join(erreurs[:3]))
    rouges = [c for c in cas if not c[1]]
    print("\n%d verification(s), %d echec(s)" % (len(cas), len(rouges)))
    if args.muter:
        print("MUTATION : un rouge est le resultat ATTENDU.")
    return 1 if rouges else 0


if __name__ == "__main__":
    sys.exit(main())
