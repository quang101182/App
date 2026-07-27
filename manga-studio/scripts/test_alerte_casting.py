# -*- coding: utf-8 -*-
"""L'app previent-elle quand le texte d'une case ne colle pas a son casting ?

Defaut trouve le 28/07 en lisant le prompt REELLEMENT envoye : une case qui
disait « plan large du dojo VIDE » portait quand meme « 2people, 1girl…, 1man… ».
Le casting s'applique a toutes les cases, meme celles qui ne parlent que d'un
personnage — ou d'aucun. Douze cases, douze fois la meme composition a deux corps.

⚠ L'alerte AVERTIT, elle ne refuse rien. La meme heuristique de texte avait ete
jugee « trop faillible pour retirer un bouton » (v1.24.0), et ce jugement tient :
ce qui change, c'est le cout d'un faux positif — une phrase de trop a l'ecran,
au lieu d'un geste rendu impossible.

Ce banc verifie donc les DEUX sens, et le second compte autant :
  - elle apparait quand le texte et le casting divergent (decor, ou un seul
    personnage evoque pour deux castes) ;
  - elle SE TAIT quand tout va bien (duo evoque, casting d'un seul, case vide).

Usage:
    python test_alerte_casting.py [--headed]
    python test_alerte_casting.py --muter     # DOIT virer au rouge
"""
import argparse
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
APP_URL = "http://127.0.0.1:8190/manga"
NOM = "_alerte_%d" % os.getpid()

cas = []

# (texte de la case, personnages castes, l'alerte doit-elle apparaitre ?, pourquoi)
CAS = [
    ("plan large du dojo vide au petit matin", 2, True,  "décor + 2 castés"),
    ("gros plan sur le visage de l'homme, yeux fermes", 2, True, "1 seul évoqué / 2 castés"),
    ("gros plan sur ses yeux a elle, regard determine", 2, True, "1 seule évoquée / 2 castés"),
    ("les deux se font face au centre du dojo", 2, False, "duo évoqué → rien à dire"),
    ("elle s'elance, coup de pied saute", 1, False, "1 évoquée, 1 castée → cohérent"),
    ("plan large du dojo vide", 0, False, "personne casté → rien à dire"),
    ("ils s'affrontent, garde haute", 2, False, "duo évoqué (affrontent)"),
]


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
        pg = br.new_page(viewport={"width": 360, "height": 780},
                         is_mobile=True, has_touch=True)
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        pg.on("dialog", lambda d: d.accept())
        pg.set_default_timeout(120000)
        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)

        if args.muter:
            # MUTATION : l'alerte se tait toujours. Le banc doit rougir sur les
            # trois cas ou elle DOIT parler.
            pg.evaluate("() => { alerteCasting = () => ''; }")

        base = pg.evaluate("""async (nom) => {
            const proj = await api('/manga/projects', {name: nom, slug: nom});
            const cree = await api('/manga/pages', {projectId: proj.id, title: nom,
                                                    chapter: '1', idx: 0, layout: {cols: 1}});
            const page = ((await api('/manga/pages?project=' + proj.id)).items || [])
                           .find(x => x.id === cree.id);
            const a = await api('/manga/chars', {name: 'Kimiko', tags: '1girl, black hair'});
            const b = await api('/manga/chars', {name: 'Jo', tags: '1man, short hair'});
            CHARS = (await api('/manga/chars')).items || [];
            S.proj = proj; S.page = page;
            S.page.layout = Object.assign({}, page.layout, {casting: [a.id, b.id]});
            await api('/manga/pages', S.page);
            const p = await api('/manga/panels', {pageId: page.id, kind: 'dialogue',
                                                  idx: 0, prompt: ''});
            S.panels = ((await api('/manga/panels?page=' + page.id)).items || []);
            renderPlate();
            return {proj: proj.id, a: a.id, b: b.id, panel: p.id};
        }""", NOM)

        for texte, nb, attendu, pourquoi in CAS:
            castes = [base["a"], base["b"]][:nb]
            vu = pg.evaluate("""([id, texte, castes]) => {
                const p = S.panels.find(x => x.id === id);
                p.prompt = texte;
                p.recipe = Object.assign({}, p.recipe, {casting: castes});
                renderPlate();
                const el = document.querySelector('[data-pid="' + id + '"] [data-apercu]');
                return el ? el.textContent : '';
            }""", [base["panel"], texte, castes])
            present = "⚠" in vu
            verifie("« %s » (%s)" % (texte[:38], pourquoi),
                    present == attendu,
                    ("alerte affichée" if present else "aucune alerte")
                    + (" — attendu : " + ("oui" if attendu else "non")))
            if present and attendu:
                verifie("   … et elle nomme les personnages concernés",
                        "Kimiko" in vu or "Jo" in vu, "")

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
        print("MUTATION : le banc reste VERT alors que l'alerte est muette. A reecrire.")
        return 1
    for nom, _, det in rates:
        print("  - " + nom + ((" (" + det + ")") if det else ""))
    return 1 if rates else 0


if __name__ == "__main__":
    sys.exit(main())
