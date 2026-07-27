# -*- coding: utf-8 -*-
"""La sequence de mouvement, de bout en bout, avec de VRAIES generations.

Ce que ce banc protege, par ordre de gravite :

1. La case de DEPART n'est pas sacrifiee. Premiere version : la vignette 1
   reutilisait la case de depart -- Quang y perdait l'image deja generee, et
   deux fichiers se rangeaient dans la meme case (journal du 27/07).
2. Le prompt envoye est en ANGLAIS. La sequence a longtemps ete le seul chemin
   sans garde-fou : trois vignettes ont ete produites sur « Les autres eleves
   chuchotent et se retournent », que le moteur ignore purement (v1.23.0).
3. Les `idx` restent uniques et ordonnes apres insertion, sinon l'ordre de
   lecture devient aleatoire au prochain chargement.
4. Le seed est le MEME sur toute la suite : c'est lui qui garde le dessin.
5. ▶ Jouer defile bien plusieurs vignettes DISTINCTES.

Cout : 2 vignettes reelles (~30 s de GPU). C'est le prix d'un banc qui mesure
la sequence telle qu'elle est vecue, et non un calcul de coordonnees.

Usage:
    python test_sequence_live.py [--headed] [--n 2]
    python test_sequence_live.py --muter     # DOIT virer au rouge
"""
import argparse
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
APP_URL = "http://127.0.0.1:8190/manga"
LARGEUR, HAUTEUR = 360, 780
NOM = "_seqlive_%d" % os.getpid()
# Une phrase FRANCAISE : c'est tout l'interet: la sequence doit la traduire AVANT
# de depenser la moindre generation.
DEPART = "un eleve court dans le couloir"

cas = []


def verifie(nom, ok, detail=""):
    cas.append((nom, bool(ok), detail))
    print(("  OK   " if ok else "  ECHEC") + " " + nom + ((" — " + detail) if detail else ""))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--n", type=int, default=2, help="nombre de vignettes (defaut 2)")
    ap.add_argument("--muter", action="store_true",
                    help="la sequence ecrase la case de depart et saute la traduction")
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright

    secret = open(SECRET_FILE, encoding="utf-8").read().strip()
    erreurs = []
    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=not args.headed, channel="msedge")
        pg = br.new_page(viewport={"width": LARGEUR, "height": HAUTEUR},
                         is_mobile=True, has_touch=True)
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        pg.on("dialog", lambda d: d.accept())
        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)

        if args.muter:
            # MUTATION : les deux fautes reelles de l'historique, remises ensemble.
            # `preparePrompt` ne fait plus rien (la phrase francaise part telle
            # quelle), et la case de depart redevient la vignette 1.
            pg.evaluate("""() => {
                preparePrompt = async () => {};
                window.__ecrase = true;
            }""")

        # --- une planche a nous, avec une case de depart DEJA generee ---
        etat0 = pg.evaluate("""async ([nom, depart]) => {
            const proj = await api('/manga/projects', {name: nom, slug: nom});
            const cree = await api('/manga/pages', {projectId: proj.id, title: nom,
                                                    chapter: '1', idx: 0, layout: {cols: 2}});
            const page = ((await api('/manga/pages?project=' + proj.id)).items || [])
                           .find(x => x.id === cree.id);
            // Une case de depart AVEC une image : c'est elle qui etait ecrasee.
            const pan = await api('/manga/panels', {pageId: page.id, kind: 'dialogue',
                prompt: depart, idx: 0, file: '_demo/1_planche_pc.png'});
            const suivante = await api('/manga/panels', {pageId: page.id, kind: 'dialogue',
                prompt: 'closing the door', idx: 1});
            S.proj = proj; S.page = page;
            S.panels = ((await api('/manga/panels?page=' + page.id)).items || [])
                         .sort((a, b) => a.idx - b.idx);
            renderPlate(); majApercus();
            return {proj: proj.id, page: page.id, depart: pan.id, suivante: suivante.id,
                    fichierDepart: S.panels[0].file};
        }""", [NOM, DEPART])

        verifie("la case de depart a bien une image avant la sequence",
                bool(etat0["fichierDepart"]), str(etat0["fichierDepart"]))

        # --- lancer la sequence par l'UI, comme un utilisateur ---
        sel = '[data-pid="%s"]' % etat0["depart"]
        pg.click(sel + ' [data-act="sequence"]')
        pg.wait_for_timeout(600)
        gestes = pg.evaluate("(s) => document.querySelectorAll(s + ' [data-seqg]').length", sel)
        verifie("le panneau de gestes s'ouvre INLINE (pas de boite native)",
                gestes > 3, "%s geste(s) proposes" % gestes)

        pg.click(sel + ' [data-seqg="coup"]')
        pg.wait_for_timeout(600)
        pg.click(sel + ' [data-seqn="%d"]' % args.n)

        # --- la traduction doit arriver AVANT la premiere vignette ---
        traduit = None
        for _ in range(40):
            v = pg.evaluate("(id) => (S.panels.find(x => x.id === id) || {}).prompt",
                            etat0["depart"])
            if v and "eleve" not in v.lower():
                traduit = v
                break
            pg.wait_for_timeout(500)
        verifie("le francais est traduit AVANT de generer la moindre vignette",
                traduit is not None, (traduit or "toujours en francais")[:70])

        # --- attendre les vignettes ---
        for _ in range(120):
            n = pg.evaluate("S.panels.filter(x => (x.recipe||{}).sequence && x.file).length")
            if n >= args.n:
                break
            pg.wait_for_timeout(2000)

        fin = pg.evaluate("""(dep) => {
            const P = S.panels;
            const vig = P.filter(x => (x.recipe||{}).sequence);
            const d = P.find(x => x.id === dep) || {};
            return {
              total: P.length,
              vignettes: vig.length,
              avecImage: vig.filter(x => x.file).length,
              idx: P.map(x => x.idx),
              seeds: [...new Set(vig.map(x => (x.recipe||{}).seed))],
              index: vig.map(x => x.recipe.sequence.index).sort((a,b) => a-b),
              departFichier: d.file || null,
              departPrompt: d.prompt || '',
              positifs: vig.map(x => (x.recipe||{}).positive || '')
            };
        }""", etat0["depart"])

        verifie("%d vignettes ont ete creees" % args.n,
                fin["vignettes"] == args.n, "%s vignette(s)" % fin["vignettes"])
        verifie("toutes les vignettes ont leur image",
                fin["avecImage"] == args.n, "%s image(s)" % fin["avecImage"])
        verifie("la case de DEPART garde son image (elle n'est pas sacrifiee)",
                bool(fin["departFichier"]), str(fin["departFichier"]))
        verifie("les idx restent uniques et ordonnes",
                fin["idx"] == sorted(set(fin["idx"])) == fin["idx"], "idx=%s" % fin["idx"])
        verifie("un seul seed sur toute la suite (c'est lui qui garde le dessin)",
                len(fin["seeds"]) == 1, "seeds=%s" % fin["seeds"])
        verifie("les vignettes sont indexees 0..n-1",
                fin["index"] == list(range(args.n)), "index=%s" % fin["index"])

        francais = [m for m in ("eleve", "court", "couloir")
                    if any(m in p.lower() for p in fin["positifs"])]
        verifie("AUCUNE vignette n'a ete generee sur du francais (v1.23.0)",
                not francais, "mots francais trouves : %s" % francais)
        verifie("chaque vignette porte son cadrage de pose",
                all("front view" in p for p in fin["positifs"]),
                (fin["positifs"][0][-40:] if fin["positifs"] else ""))

        # --- ▶ Jouer ---
        vid = pg.evaluate("(S.panels.find(x => (x.recipe||{}).sequence) || {}).id")
        pg.evaluate("""() => {
            window.__vues = [];
            const i = document.getElementById('lbImg');
            new MutationObserver(() => {
                const m = /[?&]p=([^&]*)/.exec(i.getAttribute('src') || '');
                window.__vues.push(m ? decodeURIComponent(m[1]).split('/').pop() : '?');
            }).observe(i, {attributes: true, attributeFilter: ['src']});
        }""")
        pg.click('[data-pid="%s"] [data-act="jouer"]' % vid)
        pg.wait_for_timeout(3000)
        vues = pg.evaluate("window.__vues") or []
        verifie("▶ Jouer ouvre la visionneuse",
                pg.evaluate("!document.getElementById('lightbox').hidden"))
        verifie("▶ Jouer fait defiler des vignettes DISTINCTES",
                len(set(vues)) >= min(2, args.n), "%d distinctes sur %d changements"
                % (len(set(vues)), len(vues)))
        pg.evaluate("document.getElementById('lbClose').click()")
        pg.wait_for_timeout(400)
        verifie("la lecture s'arrete a la fermeture (sinon elle tourne en fond)",
                pg.evaluate("LECT === null"))

        pg.evaluate("async (id) => api('/manga/projects', {delete: id})", etat0["proj"])
        br.close()

    verifie("aucune erreur JS", not erreurs, "; ".join(erreurs[:2]))

    rates = [c for c in cas if not c[1]]
    print("\n=== %d/%d verifications passees ===" % (len(cas) - len(rates), len(cas)))
    if args.muter:
        if rates:
            print("MUTATION : le banc vire au rouge — il sait donc echouer. OK")
            return 0
        print("MUTATION : le banc reste VERT alors que la traduction est desactivee.")
        return 1
    for nom, _, det in rates:
        print("  - " + nom + ((" (" + det + ")") if det else ""))
    return 1 if rates else 0


if __name__ == "__main__":
    sys.exit(main())
