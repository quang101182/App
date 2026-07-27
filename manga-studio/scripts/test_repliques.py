# -*- coding: utf-8 -*-
"""💬 Repliques : l'app ECRIT le dialogue, et ne detruit jamais le tien.

Quang, 27/07 : « on peut generer des images, mais on ne genere pas de bulle de
texte ? » Poser une bulle et ecrire dedans existait depuis la v1.2.0 -- ce qui
manquait, c'est que l'app propose la REPLIQUE. Elle sait pourtant deja lire les
dialogues des cases precedentes : 💡 3 suites s'en sert.

Ce que le banc verifie :

  - le contexte envoye au modele contient les cases PRECEDENTES *et* leurs
    dialogues, l'action de la case a ecrire, et QUI est present (le casting
    sait ce que le prompt ne dit pas toujours) ;
  - la consigne exige des repliques COURTES : une bulle de manga ne tient pas
    un paragraphe ;
  - le bouton vit dans ⚙ Affiner, pas dans la rangee (regle 12.0) ;
  - ⚠ LE POINT QUI COMPTE : une replique choisie AJOUTE une bulle. Elle
    n'ecrase JAMAIS un texte deja ecrit. Une replique ecrite a la main qui
    disparait, c'est la perte qu'on ne pardonne pas a un outil de creation ;
  - deux repliques posees ne se superposent pas exactement.

La reponse du modele est FIGEE : ce qui est teste, c'est la chaine de l'app,
pas l'inspiration d'un modele de langue un jour donne. Zero GPU.

Usage:
    python test_repliques.py [--headed]
    python test_repliques.py --muter    # DOIT virer au rouge
"""
import argparse
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
APP_URL = "http://127.0.0.1:8190/manga"
NOM = "_rep_%d" % os.getpid()

PROPOSEES = ["Tu n'aurais pas du venir ici.",
             "Alors c'est toi, le fameux maitre ?",
             "Recule. Je ne le redirai pas."]

cas = []


def verifie(nom, ok, detail=""):
    cas.append((nom, bool(ok), detail))
    print(("  OK   " if ok else "  ECHEC") + " " + nom + ((" — " + detail) if detail else ""),
          flush=True)
    return ok


PREPARE = """async ([nom]) => {
    const rep = await api('/manga/projects', {name: nom, slug: nom, recipe: {}});
    const proj = ((await api('/manga/projects')).items || []).find(x => x.id === rep.id);
    const cree = await api('/manga/pages', {projectId: proj.id, title: nom,
                                            chapter: '1', idx: 0, layout: {cols: 2}});
    const page = ((await api('/manga/pages?project=' + proj.id)).items || [])
                   .find(x => x.id === cree.id);
    const textes = ['un vieux maitre balaie la cour, plan large',
                    'une silhouette pousse le portail'];
    for (let i = 0; i < textes.length; i++){
        await api('/manga/panels', {pageId: page.id, kind: 'dialogue',
                                    prompt: textes[i], idx: i});
    }
    const c = await api('/manga/chars', {name: 'Kenji' + nom,
        tags: 'old master', role: 'heros'});
    S.proj = proj; S.page = page;
    // Le personnage joue sur la planche : son nom doit arriver dans le contexte.
    S.proj.recipe = Object.assign({}, S.proj.recipe, {casting: [c.id]});
    await api('/manga/projects', S.proj);
    S.page.layout = Object.assign({}, S.page.layout, {casting: [c.id]});
    await api('/manga/pages', S.page);
    await loadChars();
    S.panels = ((await api('/manga/panels?page=' + page.id)).items || [])
                 .sort((a, b) => a.idx - b.idx);
    // La case 1 a DEJA un dialogue ecrit a la main : il ne doit jamais dispraitre.
    S.panels[0].bubbles = [{id: 'bManuel', text: 'ECRIT A LA MAIN', x: .5, y: .2,
                            w: .4, h: .16, shape: 'oval', size: .042}];
    await api('/manga/panels', S.panels[0]);
    renderPlate();
    return {proj: proj.id, ch: c.id, p0: S.panels[0].id, p1: S.panels[1].id};
}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--muter", action="store_true",
                    help="la replique ECRASE la bulle existante : DOIT virer au rouge")
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright

    secret = open(SECRET_FILE, encoding="utf-8").read().strip()
    erreurs, demandes = [], []

    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=not args.headed, channel="msedge")
        pg = br.new_page(viewport={"width": 390, "height": 820},
                         is_mobile=True, has_touch=True)
        pg.on("pageerror", lambda e: erreurs.append(str(e)))

        def repond(route):
            try:
                demandes.append(json.loads(route.request.post_data or "{}"))
            except Exception:
                demandes.append({})
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps({"prompt": "\n".join(PROPOSEES)}))
        pg.route("**/enhance", repond)

        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_timeout(3000)
        d = pg.evaluate(PREPARE, [NOM])

        if args.muter:
            # MUTATION : la replique remplit la PREMIERE bulle au lieu d'en
            # creer une. Rien ne plante, une jolie replique s'affiche -- et le
            # texte ecrit a la main a disparu sans un mot.
            pg.evaluate("""() => {
                const vrai = addBubble;
                window.addBubble = async (p, shape) => {
                    if ((p.bubbles || []).length) { S.selBub = p.bubbles[0].id; return; }
                    return vrai(p, shape);
                };
            }""")

        sel = '[data-pid="%s"]' % d["p0"]
        # ---------- 1. le bouton est dans ⚙, pas dans la rangee ----------
        VIS = "els => els.filter(e => e.offsetParent !== null)"
        verifie("le bouton n'encombre pas la case fermee",
                pg.eval_on_selector_all(sel + ' [data-act="repliques"]', VIS + ".length") == 0)
        pg.click(sel + ' [data-act="affiner"]')
        pg.wait_for_timeout(500)
        verifie("il est dans le panneau ⚙ Affiner",
                pg.eval_on_selector_all(sel + ' .affiner [data-act="repliques"]',
                                        VIS + ".length") == 1)

        # ---------- 2. ce qui est DEMANDE au modele ----------
        pg.click(sel + ' [data-act="repliques"]')
        pg.wait_for_timeout(2500)
        verifie("une demande est partie", len(demandes) == 1, "%d" % len(demandes))
        idee = (demandes[0].get("idea") or "") if demandes else ""
        verifie("le contexte porte l'action de la case", "balaie la cour" in idee, idee[:80])
        verifie("... et QUI est present (le casting)", "Kenji" in idee, idee[:80])
        verifie("... et il exige des repliques COURTES",
                "COURTES" in idee or "12 mots" in idee, idee[-120:])

        # ---------- 3. trois propositions affichees ----------
        n = pg.eval_on_selector_all(sel + " [data-replique]", "els => els.length")
        verifie("trois repliques proposees", n == 3, "%d" % n)

        # ---------- 4. LE POINT QUI COMPTE : ca AJOUTE, ca n'ecrase pas ----------
        avant = pg.evaluate("(id) => { const p = S.panels.find(x => x.id === id);"
                            " return (p.bubbles || []).map(b => b.text); }", d["p0"])
        pg.click(sel + ' [data-replique]')
        pg.wait_for_timeout(1800)
        apres = pg.evaluate("(id) => { const p = S.panels.find(x => x.id === id);"
                            " return (p.bubbles || []).map(b => b.text); }", d["p0"])
        verifie("le texte ecrit A LA MAIN est toujours la",
                "ECRIT A LA MAIN" in apres, str(apres))
        verifie("la replique s'ajoute (une bulle de plus)",
                len(apres) == len(avant) + 1, "%d -> %d bulle(s)" % (len(avant), len(apres)))
        verifie("c'est bien la replique choisie qui est posee",
                PROPOSEES[0] in apres, str(apres))

        # ---------- 5. elle est enregistree, pas seulement affichee ----------
        pg.reload(wait_until="domcontentloaded")
        pg.wait_for_timeout(3000)
        pg.evaluate("(id) => ouvrirProjet(id)", d["proj"])
        pg.wait_for_timeout(2500)
        relu = pg.evaluate("(id) => { const p = S.panels.find(x => x.id === id);"
                           " return p ? (p.bubbles || []).map(b => b.text) : []; }", d["p0"])
        verifie("la replique survit au rechargement",
                PROPOSEES[0] in relu and "ECRIT A LA MAIN" in relu, str(relu))

        # ---------- 6. deux repliques ne se superposent pas ----------
        pg.click(sel + ' [data-act="affiner"]')
        pg.wait_for_timeout(500)
        pg.click(sel + ' [data-act="repliques"]')
        pg.wait_for_timeout(2500)
        pg.click(sel + ' [data-replique]')
        pg.wait_for_timeout(1800)
        ys = pg.evaluate("(id) => { const p = S.panels.find(x => x.id === id);"
                         " return (p.bubbles || []).map(b => b.y); }", d["p0"])
        verifie("deux repliques posees ne se superposent pas exactement",
                len(set(ys)) == len(ys), str(ys))

        try:
            pg.evaluate("(id) => api('/manga/chars', {delete: id})", d["ch"])
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
