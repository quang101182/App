# -*- coding: utf-8 -*-
"""La chaine du prompt, de bout en bout : francais -> traduction -> casting -> comptage.

C'est la partie de l'app qui a produit le plus de bugs, et TOUJOURS le meme :
un bug d'ORDRE. Ce qui est vrai de la phrase de Quang cesse de l'etre une fois
qu'elle a ete remplacee par des tags anglais -- et le calcul qui en depend est
fait apres.

Trois incidents, la meme cause :
  27/07 (v1.19.0) : « deux maitres » -> le LLM rend « solo, martial arts master ».
                    Corrige : le NOMBRE se derive du texte francais, il ne se
                    demande pas au LLM.
  27/07 (v1.22.1) : le bouton ✨ Ameliorer ne rafraichissait pas l'apercu --
                    ecrire .value par JS ne declenche pas l'evenement `input`.
                    L'apercu, seule fenetre sur ce qui part au moteur, mentait.
  27/07 (v1.22.2) : le meme bouton comptait les personnages APRES traduction,
                    donc sur un texte ou « maitre » et « fille » n'existent plus.
                    La traduction AUTOMATIQUE, elle, comptait avant : un chemin
                    sur deux etait protege.
  27/07 (v1.23.0) : la SEQUENCE, troisieme chemin, n'avait aucun garde-fou : trois
                    vignettes generees sur une phrase francaise que le moteur a
                    ignoree. Corrige en separant TRADUIRE (obligatoire, fidele,
                    sur tous les chemins) de AMELIORER (facultatif, enrichit),
                    derriere UN seul point de passage : `preparePrompt`.

Le banc appelle le VRAI bouton de l'app, avec la reponse du LLM figee (routee par
Playwright) : ce qui est teste, c'est l'ordre des operations, pas l'humeur d'un
modele de langue.

Usage:
    python test_prompt_chaine.py [--headed]
    python test_prompt_chaine.py --muter     # DOIT virer au rouge
"""
import argparse
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
APP_URL = "http://127.0.0.1:8190/manga"
LARGEUR, HAUTEUR = 360, 780          # le telephone de Quang, pas le Samsung (384)
NOM = "_chaine_%d" % os.getpid()

# Ce que le LLM rend VRAIMENT sur « le maitre frappe la fille » -- mesure deux fois
# sur deux : il emet « solo » malgre une consigne explicite de ne jamais l'emettre.
REPONSE_LLM = {"prompt": "solo, master hitting girl, slap, manga panel, "
                         "black and white, monochrome, lineart"}

cas = []


def verifie(nom, ok, detail=""):
    cas.append((nom, bool(ok), detail))
    print(("  OK   " if ok else "  ECHEC") + " " + nom + ((" — " + detail) if detail else ""))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--muter", action="store_true",
                    help="annule les parades d'ordre : le banc DOIT virer au rouge")
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright

    secret = open(SECRET_FILE, encoding="utf-8").read().strip()
    erreurs_js = []
    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=not args.headed, channel="msedge")
        pg = br.new_page(viewport={"width": LARGEUR, "height": HAUTEUR},
                         is_mobile=True, has_touch=True)
        pg.on("pageerror", lambda e: erreurs_js.append(str(e)))

        # La reponse du LLM est FIGEE : un banc dont le verdict depend d'un modele
        # de langue ne mesure pas l'app, il mesure la meteo.
        pg.route("**/enhance", lambda route: route.fulfill(
            status=200, content_type="application/json", body=json.dumps(REPONSE_LLM)))

        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)

        if args.muter:
            # MUTATION : on remet exactement les deux fautes corrigees les 27/07.
            # nbPersonnages ne sait plus compter, et l'apercu ne se rafraichit plus.
            pg.evaluate("""() => {
                window.nbPersonnages = () => 0;
                window.majApercu = () => {};
            }""")

        print("\n--- fonctions pures ---")
        n = pg.evaluate("(t) => nbPersonnages(t)", "le maitre frappe la fille")
        verifie("« le maitre frappe la fille » compte 2 personnages", n == 2, "compte=%s" % n)
        n2 = pg.evaluate("(t) => nbPersonnages(t)", "deux maitres en arts martiaux")
        verifie("« deux maitres » compte 2", n2 == 2, "compte=%s" % n2)
        n3 = pg.evaluate("(t) => nbPersonnages(t)", "une eleve leve la main")
        verifie("une seule personne ne force rien", n3 == 0, "compte=%s" % n3)
        n4 = pg.evaluate("(t) => nbPersonnages(t)", "deux heures plus tard, un maitre entre")
        verifie("« deux heures » n'est pas deux personnages", n4 == 0, "compte=%s" % n4)
        fr = pg.evaluate("(t) => sembleFrancais(t)", "le maitre frappe la fille")
        en = pg.evaluate("(t) => sembleFrancais(t)",
                         "solo, school classroom, black and white, lineart")
        verifie("le francais est detecte", fr is True)
        verifie("des tags anglais propres ne sont PAS retraduits", en is False)

        print("\n--- promptFinal : le texte qui part vraiment au moteur ---")
        # ⚠ `CHARS` est un `let` et `castingPage` un `const` de portee script : ni
        # l'un ni l'autre n'existe sur `window`. Un stub `window.CHARS = [...]`
        # est donc IGNORE en silence -- le banc mesurait alors une app sans aucun
        # personnage et rendait un rouge qui n'accusait que lui-meme.
        # On passe par le vrai chemin : le casting vit dans S.page.layout.casting.
        pg.evaluate("""() => {
            S.proj = {id: 'x', slug: 'x', recipe: {}};
            S.page = {id: 'y', layout: {cols: 2, casting: []}};
            CHARS = [
                {id: 'c1', name: 'Kimiko', trigger: 'kmk', tags: '1girl, sailor uniform'},
                {id: 'c2', name: 'Maitre',  trigger: 'mst', tags: '1boy, old man'}];
        }""")
        verifie("le stub de personnages est bien VU par l'app",
                pg.evaluate("CHARS.length") == 2,
                "CHARS=%s" % pg.evaluate("CHARS.length"))

        def final(panel, casting=None):
            return pg.evaluate("""([p, cast]) => {
                S.page.layout.casting = cast || [];
                return promptFinal(p); }""", [panel, casting or []])

        t = final({"kind": "dialogue", "prompt": "le maitre frappe la fille", "recipe": {}})
        verifie("2 sujets FR : « solo » retire du prompt final", "solo" not in t.lower(), t[:80])
        verifie("2 sujets FR : un tag de comptage est injecte", "2people" in t, t[:80])

        t = final({"kind": "dialogue", "prompt": "une eleve leve la main", "recipe": {}})
        verifie("1 personne : aucun comptage force", "2people" not in t, t[:60])

        # Le cas du 27/07 : le texte est DEJA traduit (donc plus comptable), mais le
        # nombre a ete releve avant. C'est `recipe.nbPersos` qui doit tenir seul.
        t = final({"kind": "dialogue", "prompt": REPONSE_LLM["prompt"],
                   "recipe": {"nbPersos": 2}})
        verifie("texte traduit + nbPersos memorise : « solo » retire",
                "solo" not in t.lower(), t[:80])
        verifie("texte traduit + nbPersos memorise : comptage injecte",
                "2people" in t, t[:80])

        t = final({"kind": "dialogue", "prompt": "action", "recipe": {}}, casting=["c1", "c2"])
        verifie("casting de 2 : les tags des DEUX personnages arrivent",
                "kmk" in t and "mst" in t, t[:90])
        verifie("casting de 2 : « solo » retire", "solo" not in t.lower(), t[:90])

        t = final({"kind": "dialogue", "prompt": "action", "sansPerso": True, "recipe": {}},
                  casting=[])
        verifie("case sans personnage : aucune identite injectee",
                "kmk" not in t and "mst" not in t, t[:70])

        print("\n--- le VRAI bouton ✨ Ameliorer (reponse LLM figee) ---")
        pid = pg.evaluate("""async (nom) => {
            const proj = await api('/manga/projects', {name: nom, slug: nom});
            const pageR = await api('/manga/pages', {projectId: proj.id, title: nom,
                                                     chapter: '1', idx: 0, layout: {cols: 2}});
            const pan = await api('/manga/panels', {pageId: pageR.id, kind: 'dialogue',
                                                    prompt: '', idx: 0});
            S.proj = proj; S.page = pageR;
            S.panels = [{id: pan.id, page_id: pageR.id, kind: 'dialogue',
                         prompt: 'le maitre frappe la fille', bubbles: [], recipe: {}}];
            renderPlate(); majApercus();
            return pan.id;
        }""", NOM)

        sel = '[data-pid="%s"]' % pid
        avant = pg.inner_text(sel + " [data-apercu]")
        verifie("avant : l'apercu annonce que le francais SERA traduit",
                "traduit" in avant.lower(), avant[-70:])

        pg.click(sel + ' [data-act="ameliorer"]')
        pg.wait_for_timeout(1500)

        champ = pg.input_value(sel + " [data-prompt]")
        apercu = pg.inner_text(sel + " [data-apercu]")
        verifie("le champ contient bien la traduction",
                "master hitting girl" in champ, champ[:60])
        verifie("l'apercu a SUIVI le champ (bug v1.22.1)",
                "master hitting girl" in apercu, apercu[:90])
        verifie("l'annonce de traduction a disparu une fois traduit (v1.22.1)",
                "sera traduit" not in apercu.lower())
        verifie("le « solo » rendu par le LLM ne part PAS au moteur (bug v1.22.2)",
                "solo" not in apercu.lower(), apercu[:90])
        verifie("le comptage a survecu a la traduction (bug v1.22.2)",
                "2people" in apercu, apercu[:90])

        print("\n--- traduction OBLIGATOIRE, meme amelioration decochee (v1.23.0) ---")
        # Le cas exact du 27/07 : autoEnhance decoche, texte francais, et un chemin
        # qui depense N generations. La phrase ne doit PAS atteindre le moteur.
        traduit = pg.evaluate("""async () => {
            OPT.autoEnhance = false;
            const p = S.panels[0];
            p.prompt = 'les deux maitres se saluent avant le combat';
            p.recipe = {};
            const champ = document.querySelector('[data-pid="' + p.id + '"] [data-prompt]');
            if (champ) champ.value = p.prompt;
            await preparePrompt(p);
            return {prompt: p.prompt, nbPersos: (p.recipe||{}).nbPersos,
                    final: promptFinal(p)};
        }""")
        verifie("le texte a ete traduit malgre l'amelioration decochee",
                "maitres" not in traduit["prompt"].lower(), traduit["prompt"][:70])
        verifie("le comptage releve AVANT la traduction est conserve",
                traduit["nbPersos"] == 2, "nbPersos=%s" % traduit["nbPersos"])
        verifie("le prompt final n'a plus un mot de francais",
                not any(m in traduit["final"].lower()
                        for m in ("maitres", "saluent", "avant le combat")),
                traduit["final"][-70:])

        # `preparePrompt` doit etre LE point de passage : s'il cessait d'etre appele
        # par un chemin, ce chemin retomberait dans le bug d'origine sans bruit.
        appels = pg.evaluate("""() => {
            const src = document.documentElement.innerHTML;
            return (src.match(/await preparePrompt\\(/g) || []).length;
        }""")
        verifie("les chemins de generation passent tous par preparePrompt",
                appels >= 2, "%s appel(s) — attendu : genPanel + sequence" % appels)

        pg.evaluate("""async (id) => { await api('/manga/projects', {delete: id}); }""",
                    pg.evaluate("S.proj.id"))
        br.close()

    verifie("aucune erreur JS", not erreurs_js, "; ".join(erreurs_js[:2]))

    rates = [c for c in cas if not c[1]]
    print("\n=== %d/%d verifications passees ===" % (len(cas) - len(rates), len(cas)))
    if args.muter:
        if rates:
            print("MUTATION : le banc vire au rouge — il sait donc echouer. OK")
            return 0
        print("MUTATION : le banc reste VERT alors que les parades sont annulees.")
        print("Il ne prouve rien. A reecrire.")
        return 1
    for nom, _, det in rates:
        print("  - " + nom + ((" (" + det + ")") if det else ""))
    return 1 if rates else 0


if __name__ == "__main__":
    sys.exit(main())
