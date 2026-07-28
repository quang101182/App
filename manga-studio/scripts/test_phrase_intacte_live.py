# -*- coding: utf-8 -*-
"""La phrase de Quang survit-elle a une VRAIE generation ? (v1.58.0)

Le banc `test_prompt_v158.py` verifie la construction du prompt sur des cases
fabriquees. Celui-ci fait le chemin complet, comme l'utilisateur : il ecrit une
PHRASE EXPLICATIVE francaise dans une case, clique Generer, attend l'image, et
verifie ce qu'il reste a l'ecran.

Ce qu'il prouve, et que rien d'autre ne prouve :
  1. le champ de la case contient toujours SA PHRASE apres generation
     (jusqu'a la v1.57.0 elle etait remplacee par des tags anglais) ;
  2. les tags reellement envoyes sont visibles SOUS la phrase, en anglais ;
  3. une negation (« sans voir son visage ») n'est PAS dans le positif ;
  4. la page ne deborde pas a 360 px avec cette ligne en plus ;
  5. une capture, parce qu'un banc d'UI qui ne regarde jamais l'ecran a deja
     laisse passer trois defauts en phase 5.

Usage:
    python test_phrase_intacte_live.py            2 cases, ~60 s de GPU
    python test_phrase_intacte_live.py --sans-gpu ne genere pas d'image
"""
import argparse
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
APP_URL = "http://127.0.0.1:8190/manga"
NOM = "_phrase_%d" % os.getpid()
SORTIE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "essai_out")

# Les phrases sont ecrites comme Quang ecrit : explicatives, pas en tags.
CAS = [
    ("gros plan tres rapproche sur ses mains crispees, on ne doit pas voir son visage",
     ["hand"], ["sailor uniform", "black hair"]),
    ("le dojo est vide au petit matin, aucun personnage, juste la lumiere des fenetres",
     ["no humans"], ["1girl", "sailor uniform", "solo"]),
]

cas = []


def verifie(nom, ok, detail=""):
    cas.append((nom, bool(ok), detail))
    print(("  OK    " if ok else "  ECHEC") + " " + nom + ((" — " + detail) if detail else ""))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--sans-gpu", action="store_true")
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright
    os.makedirs(SORTIE, exist_ok=True)

    secret = open(SECRET_FILE, encoding="utf-8").read().strip()
    erreurs = []
    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=not args.headed, channel="msedge")
        pg = br.new_page(viewport={"width": 360, "height": 900},
                         is_mobile=True, has_touch=True)
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        pg.set_default_timeout(180000)
        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)

        base = pg.evaluate("""async (nom) => {
            const proj = await api('/manga/projects', {name: nom, slug: nom});
            const cree = await api('/manga/pages', {projectId: proj.id, title: nom,
                                                    chapter: '1', idx: 0, layout: {cols: 1}});
            const page = ((await api('/manga/pages?project=' + proj.id)).items || [])
                           .find(x => x.id === cree.id);
            // Une fiche AVEC une tenue : c'est elle qui polluait les gros plans.
            const k = await api('/manga/chars', {name: 'Kimiko',
                      tags: '1girl, black hair, short hair, sharp eyes, sailor uniform'});
            CHARS = (await api('/manga/chars')).items || [];
            S.proj = proj; S.page = page;
            S.page.layout = Object.assign({}, page.layout, {casting: [k.id]});
            await api('/manga/pages', S.page);
            return {proj: proj.id, page: page.id, k: k.id};
        }""", NOM)

        for i, (phrase, doivent, interdits) in enumerate(CAS):
            pid = pg.evaluate("""async ([page, phrase]) => {
                const p = await api('/manga/panels', {pageId: page, kind: 'dialogue',
                                                      idx: 0, prompt: phrase});
                S.panels = ((await api('/manga/panels?page=' + page)).items || []);
                renderPlate();
                return p.id;
            }""", [base["page"], phrase])

            if args.sans_gpu:
                pg.evaluate("""async (id) => {
                    const p = S.panels.find(x => x.id === id);
                    await preparePrompt(p);      // traduction seule, zero GPU
                }""", pid)
            else:
                pg.click('[data-pid="%s"] [data-act="gen"]' % pid)
                pg.wait_for_function(
                    """(id) => { const p = (S.panels||[]).find(x => x.id === id);
                                 return p && p.file; }""", arg=pid, timeout=300000)

            r = pg.evaluate("""(id) => {
                const p = S.panels.find(x => x.id === id);
                const c = document.querySelector('[data-pid="' + id + '"]');
                const champ = c && c.querySelector('[data-prompt]');
                const tagsEl = c && c.querySelector('[data-tags]');
                return { phrase: p.prompt,
                         champ: champ ? champ.value : null,
                         tags: (p.recipe && p.recipe.tags) || '',
                         tagsVisibles: tagsEl ? tagsEl.value : null,
                         negAuto: (p.recipe && p.recipe.negAuto) || '',
                         envoye: promptFinal(p),
                         negEnvoye: (p.recipe && p.recipe.negative) || '',
                         file: p.file || '' };
            }""", pid)

            n = "cas %d" % (i + 1)
            verifie(n + " — la phrase est intacte dans l'objet",
                    r["phrase"] == phrase, r["phrase"][:70])
            verifie(n + " — la phrase est intacte À L'ÉCRAN",
                    r["champ"] == phrase, (r["champ"] or "(champ absent)")[:70])
            verifie(n + " — des tags anglais ont été produits",
                    bool(r["tags"].strip()) and r["tags"] != phrase, r["tags"][:80])
            verifie(n + " — la ligne de tags est VISIBLE dans la case",
                    r["tagsVisibles"] is not None and r["tagsVisibles"].strip() != "",
                    "(ligne absente du DOM)" if r["tagsVisibles"] is None else "affichée")
            env = r["envoye"].lower()
            manque = [x for x in doivent if x.lower() not in env]
            intrus = [x for x in interdits if x.lower() in env]
            verifie(n + " — ce qui part au moteur est conforme",
                    not manque and not intrus,
                    ("manque : %s. " % ", ".join(manque) if manque else "")
                    + ("interdit présent : %s" % ", ".join(intrus) if intrus else ""))
            if not args.sans_gpu:
                verifie(n + " — une image a bien été produite", bool(r["file"]), r["file"])
            print("      envoyé : " + r["envoye"][:150])
            if r["negAuto"]:
                print("      au négatif : " + r["negAuto"][:100])

            # Aucun debordement horizontal AVEC la ligne de tags a l'ecran.
            deb = pg.evaluate("""() => {
                const d = document.documentElement;
                const inners = [...document.querySelectorAll('*')]
                  .filter(e => e.scrollWidth > e.clientWidth + 1
                            && getComputedStyle(e).overflowX !== 'visible')
                  .map(e => e.tagName + '.' + (e.className || '').toString().slice(0, 30));
                return { page: d.scrollWidth - d.clientWidth, inners: inners.slice(0, 3) };
            }""")
            verifie(n + " — rien ne déborde à 360 px",
                    deb["page"] <= 0 and not deb["inners"],
                    "page +%dpx %s" % (deb["page"], deb["inners"]))

            # ⚠ La capture doit CADRER la case, pas le haut de la page. Le 1er jet
            # photographiait le selecteur de projet : une capture qui ne montre
            # pas l'objet teste ne prouve rien, et se lit pourtant comme une preuve.
            carte = pg.locator('[data-pid="%s"]' % pid)
            carte.scroll_into_view_if_needed()
            pg.wait_for_timeout(300)
            carte.screenshot(path=os.path.join(SORTIE, "phrase_intacte_cas%d.png" % (i + 1)))
            pg.evaluate("async (id) => { await api('/manga/panels', {delete: id}); }", pid)

        pg.evaluate("""async ([proj, k]) => {
            await api('/manga/projects', {delete: proj});
            await api('/manga/chars', {delete: k});
        }""", [base["proj"], base["k"]])
        br.close()

    verifie("aucune erreur JS", not erreurs, "; ".join(erreurs[:2]))
    rates = [c for c in cas if not c[1]]
    print("\n=== %d/%d ===" % (len(cas) - len(rates), len(cas)))
    print("captures : " + SORTIE)
    return 1 if rates else 0


if __name__ == "__main__":
    sys.exit(main())
