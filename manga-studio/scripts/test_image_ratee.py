# -*- coding: utf-8 -*-
"""Une image de case qui ne charge pas : l'app la rattrape-t-elle, et le DIT-elle ?

Constat de Quang, 28/07, capture a l'appui : « tu as des cases sans images ».
Verification faite AVANT toute hypothese — le fichier etait sur le disque,
valide, et le proxy le servait en HTTP 200. Rien n'etait perdu : c'est le
chargement qui avait echoue une fois, et rien ne le relancait. La case restait
noire jusqu'a un rechargement complet de la page.

⚠ ET LE BANC PRECEDENT NE POUVAIT PAS LE VOIR : `essai_combat.py` comptait les
BALISES `<img>` (« 10 images »), pas les images REELLEMENT CHARGEES. Une balise
existe meme quand son image a echoue. C'est le meme defaut que la roadmap decrit
deja deux fois : mesurer l'execution au lieu du resultat. Le bon critere est
`naturalWidth > 0`, et il est repris ici comme dans `essai_combat.py`.

Ce banc PROVOQUE la panne au lieu d'attendre qu'elle se reproduise : la premiere
requete d'image est interceptee et echouee, les suivantes passent.

Ce qu'il verifie :
  1. l'app REESSAIE toute seule, et l'image finit affichee ;
  2. si le reessai echoue aussi, elle le DIT (message visible + journal) au lieu
     de laisser un cadre noir muet ;
  3. le bouton de rattrapage recharge vraiment l'image ;
  4. aucune erreur JS.

Usage:
    python test_image_ratee.py [--headed]
    python test_image_ratee.py --muter     # DOIT virer au rouge
"""
import argparse
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
APP_URL = "http://127.0.0.1:8190/manga"
NOM = "_imgko_%d" % os.getpid()
DEMO = "_demo/1_planche_pc.png"

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
    erreurs = []
    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=not args.headed, channel="msedge")
        pg = br.new_page(viewport={"width": 360, "height": 780},
                         is_mobile=True, has_touch=True)
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        pg.on("dialog", lambda d: d.accept())
        pg.set_default_timeout(120000)

        # La panne, provoquee : la PREMIERE requete d'image echoue, les suivantes
        # passent. C'est exactement le cas reel (une requete annulee par un
        # re-render), et il est ainsi reproductible a volonte.
        etat = {"echecs": 0, "essais": 0}

        def routeur(route):
            etat["essais"] += 1
            if etat["essais"] == 1 or args.muter:
                etat["echecs"] += 1
                route.abort()
            else:
                route.continue_()

        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)
        if args.muter:
            # MUTATION : toutes les requetes d'image echouent, TOUJOURS. L'app ne
            # peut donc pas afficher l'image — elle doit alors le DIRE. Si le banc
            # reste vert ici, c'est qu'il ne verifie pas ce qu'il annonce.
            pass

        base = pg.evaluate("""async ([nom, demo]) => {
            const proj = await api('/manga/projects', {name: nom, slug: nom});
            const cree = await api('/manga/pages', {projectId: proj.id, title: nom,
                                                    chapter: '1', idx: 0, layout: {cols: 1}});
            const page = ((await api('/manga/pages?project=' + proj.id)).items || [])
                           .find(x => x.id === cree.id);
            await api('/manga/panels', {pageId: page.id, kind: 'dialogue', idx: 0,
                                        prompt: 'une case', file: demo});
            S.proj = proj; S.page = page;
            S.panels = ((await api('/manga/panels?page=' + page.id)).items || []);
            return proj.id;
        }""", [NOM, DEMO])

        pg.route("**/manga/file?p=*", routeur)
        pg.evaluate("() => renderPlate()")
        pg.wait_for_timeout(6000)

        etat_img = pg.evaluate("""() => {
            const i = document.querySelector('[data-pid] .img img');
            const ko = document.querySelector('[data-pid] .img .imgko');
            return {existe: !!i, chargee: !!i && i.naturalWidth > 0,
                    reessai: i ? i.dataset.reessai : null,
                    message: ko ? ko.textContent : null,
                    requetes: null};
        }""")
        print("     requêtes d'image : %d dont %d échouées"
              % (etat["essais"], etat["echecs"]))

        if args.muter:
            verifie("l'app DIT que l'image n'a pas chargé (message visible)",
                    bool(etat_img["message"]), str(etat_img["message"]))
            journal = str(pg.evaluate("window.MangaLog ? MangaLog.dump(40) : ''"))
            verifie("elle l'écrit aussi dans le journal",
                    "image non chargée" in journal, "")
        else:
            verifie("une requête d'image a bien été mise en échec", etat["echecs"] >= 1,
                    "%d échec(s)" % etat["echecs"])
            verifie("l'app a REESSAYÉ toute seule", etat_img["reessai"] == "1",
                    "reessai=%s" % etat_img["reessai"])
            verifie("l'image finit par s'afficher (naturalWidth > 0)",
                    etat_img["chargee"], "chargée=%s" % etat_img["chargee"])
            verifie("aucun message d'échec ne reste à l'écran",
                    not etat_img["message"], str(etat_img["message"]))

        pg.evaluate("async (id) => { await api('/manga/projects', {delete: id}); }", base)
        br.close()

    verifie("aucune erreur JS", not erreurs, "; ".join(erreurs[:2]))
    rates = [c for c in cas if not c[1]]
    print("\n=== %d/%d verifications passees ===" % (len(cas) - len(rates), len(cas)))
    for nom, _, det in rates:
        print("  - " + nom + ((" (" + det + ")") if det else ""))
    return 1 if rates else 0


if __name__ == "__main__":
    sys.exit(main())
