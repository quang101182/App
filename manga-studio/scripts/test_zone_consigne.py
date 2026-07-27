# -*- coding: utf-8 -*-
"""Reparer une zone en DISANT ce qu'on veut — et sans rien dire.

Quang, 27/07 : « corriger une image sans expliquer en quoi consiste la
correction, ou avec le bouton de zone on cible une zone et on explique ce qu'on
veut corriger ».

Les deux tiennent dans UN bouton et un champ facultatif : vide, « ↻ la zone »
retente la meme chose autrement ; rempli, il dit quoi dessiner la.

Ce que le banc verifie, et pourquoi :

  - le champ n'apparait QUE si une zone est tracee, et il vit dans ⚙ Affiner :
    la refonte v1.31.0 interdit d'ajouter quoi que ce soit a la rangee ;
  - SANS consigne, le moteur recoit le prompt de la case (comportement d'avant) ;
  - AVEC consigne, le moteur recoit la consigne **plus le style et l'identite** —
    c'est le point qui separe « repare ca » de « dessine n'importe quoi la » :
    envoyer la seule consigne ferait perdre a la zone le rendu N&B et le
    personnage, et la reparation se verrait comme une piece rapportee ;
  - une consigne francaise est TRADUITE avant de partir (le moteur ne lit que
    l'anglais : une consigne francaise n'est pas mal comprise, elle est ignoree) ;
  - la zone ET sa consigne survivent au rechargement. C'est le vrai piege de ce
    chantier : la table `manga_panels` a des colonnes FIXES, et tout champ pose
    hors de `recipe` est accepte par l'API puis jete a l'ecriture. `p.zone` etait
    dans ce cas depuis la v1.26.1 -- le rectangle disparaissait au rechargement,
    sans la moindre erreur.

Zero GPU : le graphe envoye a ComfyUI est intercepte, on lit ce qui PART.

Usage:
    python test_zone_consigne.py [--headed]
    python test_zone_consigne.py --muter    # DOIT virer au rouge
"""
import argparse
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
APP_URL = "http://127.0.0.1:8190/manga"
NOM = "_zone_%d" % os.getpid()

cas = []


def verifie(nom, ok, detail=""):
    cas.append((nom, bool(ok), detail))
    print(("  OK   " if ok else "  ECHEC") + " " + nom + ((" — " + detail) if detail else ""),
          flush=True)
    return ok


# Une case generee, avec une zone deja tracee, dans un projet qui a un style et
# une identite -- sans quoi on ne pourrait pas voir qu'ils SURVIVENT a la consigne.
PREPARE = """async ([nom]) => {
    // ⚠ `api()` renvoie {ok, id}, PAS l'objet : le mettre tel quel dans S.proj
    // laisse l'app sans recette (piege deja documente dans REVALIDATION §3, et
    // ce banc est tombe dedans a sa premiere execution). On RELIT le projet.
    // Le style porte un mot IMPROBABLE : « screentone » est deja dans le style
    // par defaut, le chercher aurait donne un vert sans valeur.
    const rep = await api('/manga/projects', {name: nom, slug: nom,
        recipe: {style: 'kabukigravure, black and white',
                 trigger: 'zqmg1rl', ident: 'short hair, scar'}});
    const proj = ((await api('/manga/projects')).items || []).find(x => x.id === rep.id);
    const cree = await api('/manga/pages', {projectId: proj.id, title: nom,
                                            chapter: '1', idx: 0, layout: {cols: 2}});
    const page = ((await api('/manga/pages?project=' + proj.id)).items || [])
                   .find(x => x.id === cree.id);
    await api('/manga/panels', {pageId: page.id, kind: 'dialogue',
                                prompt: 'a girl running in a corridor', idx: 0});
    S.proj = proj; S.page = page;
    S.panels = ((await api('/manga/panels?page=' + page.id)).items || []);
    const p = S.panels[0];
    p.file = nom + '/case.png';
    p.zone = {x: .2, y: .2, w: .3, h: .3};
    p.recipe = Object.assign({}, p.recipe, {zone: p.zone});
    await api('/manga/panels', p);
    renderPlate();
    return {proj: proj.id, pid: p.id};
}"""

# On coupe juste avant le moteur : le graphe est capture, rien n'est dessine.
STUBS = """() => {
    window.__graphes = [];
    window.uploadToComfy = async () => 'stub.png';
    window.runGraph = async (wf) => { window.__graphes.push(wf);
                                      return [{filename:'o.png', subfolder:'', type:'output'}]; };
    window.harvest = async () => 'x/o.png';
}"""

# Le positive du graphe d'inpaint, quel que soit le numero du noeud.
LIRE_POSITIF = """() => {
    const wf = window.__graphes[window.__graphes.length - 1];
    if (!wf) return null;
    const textes = Object.values(wf)
        .filter(n => n.class_type === 'CLIPTextEncode')
        .map(n => (n.inputs && n.inputs.text) || '');
    return textes.join(' ||| ');
}"""

PNG_8x8 = ("iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAYAAADED76LAAAAHElEQVQoU2NkYGD4z0AEYBxV"
           "SFJgFI0GDQwMDAwAHzcCAWvbLbEAAAAASUVORK5CYII=")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--muter", action="store_true",
                    help="la consigne remplace TOUT le prompt : DOIT virer au rouge")
    args = ap.parse_args()
    import base64
    from playwright.sync_api import sync_playwright

    secret = open(SECRET_FILE, encoding="utf-8").read().strip()
    erreurs, traductions = [], []

    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=not args.headed, channel="msedge")
        pg = br.new_page(viewport={"width": 360, "height": 780},
                         is_mobile=True, has_touch=True)
        pg.on("pageerror", lambda e: erreurs.append(str(e)))

        # L'image de la case : un vrai PNG, pour que le navigateur en lise les
        # dimensions (le masque en depend). Aucun fichier n'existe sur disque.
        pg.route("**/manga/file*", lambda r: r.fulfill(
            status=200, content_type="image/png", body=base64.b64decode(PNG_8x8)))

        # La traduction est FIGEE : ce qui est teste, c'est que l'app la demande
        # et l'utilise, pas l'humeur d'un modele de langue un jour donne.
        def trad(route):
            try:
                traductions.append(json.loads(route.request.post_data or "{}"))
            except Exception:
                traductions.append({})
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps({"prompt": "an open hand, no ring"}))
        pg.route("**/enhance", trad)

        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_timeout(3000)
        d = pg.evaluate(PREPARE, [NOM])
        pg.evaluate(STUBS)
        sel = '[data-pid="%s"]' % d["pid"]

        if args.muter:
            # MUTATION : la consigne devient TOUT le prompt. La zone se redessine
            # tres bien -- mais sans le style ni le personnage, donc la retouche
            # jure avec le reste de la case. Rien ne plante, l'ecran ne dit rien.
            pg.evaluate("""() => { window.promptZone = (p) =>
                ((p.recipe && p.recipe.zonePromptEn) || '').trim() || promptFinal(p); }""")

        # ---------- 1. le champ est dans ⚙, pas dans la rangee ----------
        VISIBLES = "els => els.filter(e => e.offsetParent !== null)"
        verifie("le champ n'encombre pas la case fermee",
                pg.eval_on_selector_all(sel + " [data-zonetxt]", VISIBLES + ".length") == 0)
        pg.click(sel + ' [data-act="affiner"]')
        pg.wait_for_timeout(500)
        verifie("il est dans le panneau ⚙ Affiner",
                pg.eval_on_selector_all(sel + " .affiner [data-zonetxt]",
                                        VISIBLES + ".length") == 1)

        # ---------- 2. SANS consigne : le prompt de la case ----------
        pg.click(sel + ' [data-act="zonego"]')
        pg.wait_for_timeout(2500)
        pos = pg.evaluate(LIRE_POSITIF)
        verifie("sans consigne, le moteur recoit le prompt de la case",
                pos is not None and "running in a corridor" in pos,
                (pos or "")[:70])
        verifie("aucune traduction demandee pour une zone sans consigne",
                len(traductions) == 0, "%d appel(s)" % len(traductions))

        # ---------- 3. AVEC consigne (en francais) ----------
        pg.fill(sel + " [data-zonetxt]", "une main ouverte, sans bague")
        pg.dispatch_event(sel + " [data-zonetxt]", "change")
        pg.wait_for_timeout(700)
        pg.click(sel + ' [data-act="zonego"]')
        pg.wait_for_timeout(3000)
        verifie("la consigne francaise est traduite avant de partir",
                len(traductions) == 1, "%d appel(s) de traduction" % len(traductions))
        pos = pg.evaluate(LIRE_POSITIF)
        verifie("le moteur recoit la CONSIGNE",
                pos is not None and "open hand" in pos, (pos or "")[:70])
        verifie("... et le STYLE du projet est conserve",
                pos is not None and "kabukigravure" in pos, (pos or "")[:70])
        verifie("... et l'IDENTITE du personnage aussi",
                pos is not None and "zqmg1rl" in pos, (pos or "")[:70])
        verifie("l'action d'origine a bien cede la place",
                pos is not None and "running in a corridor" not in pos, (pos or "")[:70])

        # ---------- 4. on ne retraduit pas la meme consigne ----------
        pg.click(sel + ' [data-act="zonego"]')
        pg.wait_for_timeout(2500)
        verifie("une consigne inchangee n'est pas retraduite a chaque essai",
                len(traductions) == 1, "%d appel(s)" % len(traductions))

        # ---------- 5. LE PIEGE : survivre au rechargement ----------
        pg.reload(wait_until="domcontentloaded")
        pg.wait_for_timeout(3500)
        # L'app rouvre le projet MEMORISE, qui n'est pas celui du banc.
        pg.evaluate("(id) => ouvrirProjet(id)", d["proj"])
        pg.wait_for_timeout(2000)
        etat = pg.evaluate("""(pid) => {
            const p = S.panels.find(x => x.id === pid);
            return p ? {zone: !!p.zone, consigne: (p.recipe || {}).zonePrompt || ""} : null;
        }""", d["pid"])
        verifie("la zone tracee survit au rechargement",
                bool(etat and etat["zone"]), str(etat))
        verifie("la consigne survit au rechargement",
                bool(etat and "main ouverte" in etat["consigne"]), str(etat))

        # ---------- 6. vider le champ redonne « retenter sans rien dire » ----------
        pg.evaluate(STUBS)
        pg.click(sel + ' [data-act="affiner"]')
        pg.wait_for_timeout(500)
        pg.fill(sel + " [data-zonetxt]", "")
        pg.dispatch_event(sel + " [data-zonetxt]", "change")
        pg.wait_for_timeout(600)
        pg.click(sel + ' [data-act="zonego"]')
        pg.wait_for_timeout(2500)
        pos = pg.evaluate(LIRE_POSITIF)
        verifie("champ vide : on retrouve le prompt de la case",
                pos is not None and "running in a corridor" in pos
                and "open hand" not in pos, (pos or "")[:70])

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
