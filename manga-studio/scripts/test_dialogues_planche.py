# -*- coding: utf-8 -*-
"""Les dialogues de TOUTE la planche : poses au bon endroit, sans rien ecraser ?

Quang, 28/07 : « il faudra aussi generer les bulles de texte de dialogue. Fais
les choses en deux temps » — les images d'abord, le texte ensuite.

Le bouton 💬 par case existait deja (v1.40.0), mais il ecrit une replique
ISOLEE : douze cases traitees une a une donnent douze phrases qui ne se
repondent pas. Le bouton de planche envoie le DECOUPAGE COMPLET et recoit tout
d'un coup.

La reponse du modele est FIGEE dans ce banc (route `/enhance` interceptee). Ce
n'est pas de la triche : ce qu'on mesure ici, c'est ce que l'APP fait d'une
reponse — le decoupage envoye, le placement des bulles, et surtout ce qu'elle
REFUSE de faire. La qualite d'ecriture du modele, elle, ne se teste pas par un
banc, elle se lit.

Ce qu'il verifie :
  1. le decoupage envoye porte le numero, le texte ET le casting de chaque case
     (sans ca, le modele fait parler quelqu'un qui n'est pas la — exactement le
     defaut des images corrige en v1.56.0) ;
  2. les repliques atterrissent dans la BONNE case ;
  3. ⛔ une case qui a deja du texte n'est jamais touchee ;
  4. une case sans personne ne recoit rien, meme si le modele en propose ;
  5. deux repliques dans une case ne se superposent pas (x et y differents) ;
  6. aucune erreur JS.

Usage:
    python test_dialogues_planche.py [--headed]
    python test_dialogues_planche.py --muter     # DOIT virer au rouge
"""
import argparse
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
APP_URL = "http://127.0.0.1:8190/manga"
NOM = "_dial_%d" % os.getpid()

# La reponse FIGEE. Elle contient expres deux pieges : une replique pour la case
# de decor (1, personne n'y est) et une pour la case deja ecrite (4).
REPONSE = {"prompt": "\n".join([
    "1 | Kimiko | Il n'y a personne ici.",
    "2 | Kimiko | Tu es en retard.",
    "2 | Jo | J'ai pris le temps de reflechir.",
    "3 | Jo | Alors montre-moi ce que tu as appris.",
    "4 | Kimiko | Cette replique ne doit PAS ecraser la mienne.",
])}

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
    erreurs, envoye = [], {}
    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=not args.headed, channel="msedge")
        pg = br.new_page(viewport={"width": 360, "height": 780},
                         is_mobile=True, has_touch=True)
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        pg.on("dialog", lambda d: d.accept())
        pg.set_default_timeout(120000)

        def faux_enhance(route):
            try:
                envoye["idea"] = json.loads(route.request.post_data or "{}").get("idea", "")
            except Exception:
                envoye["idea"] = ""
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps(REPONSE))

        pg.route("**/enhance", faux_enhance)
        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)

        if args.muter:
            # MUTATION : les garde-fous sautent — toute case peut recevoir un
            # dialogue. Le banc DOIT alors rougir deux fois : la case 4 (écrite
            # à la main) serait doublée, et la case 1 (un décor) se mettrait à
            # parler. Une mutation doit viser le COMPORTEMENT, pas une ligne.
            pg.evaluate("() => { peutRecevoirDialogue = () => true; }")

        base = pg.evaluate("""async (nom) => {
            const proj = await api('/manga/projects', {name: nom, slug: nom});
            const cree = await api('/manga/pages', {projectId: proj.id, title: nom,
                                                    chapter: '1', idx: 0, layout: {cols: 1}});
            const page = ((await api('/manga/pages?project=' + proj.id)).items || [])
                           .find(x => x.id === cree.id);
            const a = await api('/manga/chars', {name: 'Kimiko', tags: '1girl'});
            const b = await api('/manga/chars', {name: 'Jo', tags: '1man'});
            CHARS = (await api('/manga/chars')).items || [];
            S.proj = proj; S.page = page;
            S.page.layout = Object.assign({}, page.layout, {casting: [a.id, b.id]});
            await api('/manga/pages', S.page);
            const mk = async (idx, prompt, casting, bulle) => {
                const p = await api('/manga/panels', {pageId: page.id, kind: 'dialogue',
                    idx: idx, prompt: prompt,
                    recipe: {casting: casting},
                    bubbles: bulle ? [{id: 'bx', text: bulle, x: .5, y: .12, w: .5,
                                       h: .18, shape: 'oval', size: .02}] : []});
                return p.id;
            };
            const ids = [];
            ids.push(await mk(0, 'plan large du dojo vide', [], null));
            ids.push(await mk(1, 'les deux se font face', [a.id, b.id], null));
            ids.push(await mk(2, 'gros plan sur lui', [b.id], null));
            ids.push(await mk(3, 'elle repond', [a.id], 'MA REPLIQUE A MOI'));
            S.panels = ((await api('/manga/panels?page=' + page.id)).items || [])
                         .sort((x, y) => x.idx - y.idx);
            renderPlate();
            return {proj: proj.id, a: a.id, b: b.id, ids: ids};
        }""", NOM)

        pg.click("#btnDialogues")
        pg.wait_for_timeout(6000)

        idea = envoye.get("idea", "")
        verifie("le découpage envoyé numérote les cases", "Case 1 :" in idea and "Case 4 :" in idea, "")
        verifie("il porte le casting de CHAQUE case",
                "[présents : Kimiko, Jo]" in idea and "[personne]" in idea, "")
        verifie("il signale les cases déjà écrites",
                "DEJA ecrit" in idea, "")

        etat = pg.evaluate("""async () => {
            const items = (await api('/manga/panels?page=' + S.page.id)).items || [];
            items.sort((a, b) => a.idx - b.idx);
            return items.map(p => ({idx: p.idx,
                bulles: (p.bubbles || []).map(b => ({t: b.text, x: b.x, y: b.y}))}));
        }""")
        for e in etat:
            print("     case %d : %s" % (e["idx"] + 1,
                  [b["t"][:38] for b in e["bulles"]] or "(aucune)"))

        c1, c2, c3, c4 = etat[0], etat[1], etat[2], etat[3]
        verifie("la case de DÉCOR ne reçoit aucune réplique",
                not c1["bulles"], "%d bulle(s)" % len(c1["bulles"]))
        verifie("la case à deux personnages reçoit ses 2 répliques",
                len(c2["bulles"]) == 2, "%d bulle(s)" % len(c2["bulles"]))
        verifie("la réplique de Jo est bien dans la case 3",
                len(c3["bulles"]) == 1 and "montre-moi" in (c3["bulles"][0]["t"] or ""),
                str([b["t"] for b in c3["bulles"]]))
        verifie("⛔ la case DÉJÀ écrite n'a pas été touchée",
                len(c4["bulles"]) == 1 and c4["bulles"][0]["t"] == "MA REPLIQUE A MOI",
                str([b["t"] for b in c4["bulles"]]))
        if len(c2["bulles"]) == 2:
            b1, b2 = c2["bulles"]
            verifie("les 2 répliques d'une même case ne se superposent pas",
                    abs(b1["x"] - b2["x"]) > 0.1 or abs(b1["y"] - b2["y"]) > 0.1,
                    "x %.2f/%.2f  y %.2f/%.2f" % (b1["x"], b2["x"], b1["y"], b2["y"]))

        pg.evaluate("""async ([proj, a, b]) => {
            await api('/manga/projects', {delete: proj});
            await api('/manga/chars', {delete: a});
            await api('/manga/chars', {delete: b});
        }""", [base["proj"], base["a"], base["b"]])
        br.close()

    verifie("aucune erreur JS", not erreurs, "; ".join(erreurs[:2]))
    rates = [c for c in cas if not c[1]]
    print("\n=== %d/%d verifications passees ===" % (len(cas) - len(rates), len(cas)))
    if args.muter:
        if rates:
            print("MUTATION : le banc vire au rouge — il sait donc echouer. OK")
            return 0
        print("MUTATION : le banc reste VERT sans garde-fou. A reecrire.")
        return 1
    for nom, _, det in rates:
        print("  - " + nom + ((" (" + det + ")") if det else ""))
    return 1 if rates else 0


if __name__ == "__main__":
    sys.exit(main())
