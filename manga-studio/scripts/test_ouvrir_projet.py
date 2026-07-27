# -*- coding: utf-8 -*-
"""Reprendre un travail en cours : ouvrir un projet deja cree.

Quang, 27/07 : « je ne vois aucun moyen de charger un projet deja en cours ou
deja cree ». Ce n'etait pas un malentendu -- l'onglet Projets, le seul endroit
ou l'on va pour reprendre un travail, ne proposait que « supprimer ». Ouvrir
n'etait possible que par une liste deroulante en haut d'un AUTRE onglet, qui
changeait l'etat sans changer l'ecran.

Ce que le banc verifie :
  - chaque projet NON ouvert propose « Ouvrir », et celui qui l'est se signale ;
  - ouvrir charge les planches du projet ET amene sur la planche (charger sans
    montrer, c'est exactement le defaut d'origine) ;
  - le choix survit a un rechargement ;
  - la galerie peut regarder un AUTRE projet SANS deplacer l'atelier : consulter
    n'est pas ouvrir.

Zero GPU : aucune image n'est generee, on manipule projets, planches et ecran.

Usage:
    python test_ouvrir_projet.py [--headed]
    python test_ouvrir_projet.py --muter    # DOIT virer au rouge
"""
import argparse
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
APP_URL = "http://127.0.0.1:8190/manga"
LARGEUR, HAUTEUR = 360, 780
A = "_ouvrirA_%d" % os.getpid()
B = "_ouvrirB_%d" % os.getpid()

cas = []


def verifie(nom, ok, detail=""):
    cas.append((nom, bool(ok), detail))
    print(("  OK   " if ok else "  ECHEC") + " " + nom + ((" — " + detail) if detail else ""))
    return ok


CREER = """async ([nom, nbPages]) => {
    const proj = await api('/manga/projects', {name: nom, slug: nom});
    for (let i = 0; i < nbPages; i++){
        await api('/manga/pages', {projectId: proj.id, title: nom + '-' + i,
                                   chapter: '1', idx: i, layout: {cols: 2}});
    }
    return proj.id;
}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--muter", action="store_true",
                    help="ouvrir ne montre plus la planche : DOIT virer au rouge")
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
        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)

        # A a 1 planche, B en a 3 : le nombre de planches prouve que le PROJET a
        # bien ete charge, pas seulement son nom affiche.
        ids.append(pg.evaluate(CREER, [A, 1]))
        ids.append(pg.evaluate(CREER, [B, 3]))
        pg.evaluate("loadProjects()")
        pg.wait_for_timeout(1200)

        if args.muter:
            # MUTATION : on charge le projet mais on ne va PAS sur sa planche --
            # le defaut exact que Quang a vecu. Tout le reste reste juste.
            pg.evaluate("""() => {
                const vrai = ouvrirProjet;
                window.ouvrirProjet = async (id) => {
                    const p = S.projects.find(x => x.id === id);
                    if (!p) return;
                    S.proj = p; localStorage.setItem('manga_proj', p.id);
                    await loadPages(); renderProjList();
                };
            }""")

        # --- ouvrir A, puis verifier que la liste le signale ---
        pg.evaluate("(id) => (window.ouvrirProjet || ouvrirProjet)(id)", ids[0])
        pg.wait_for_timeout(1200)
        pg.click('nav button[data-tab="tProj"]')
        pg.wait_for_timeout(400)

        html = pg.eval_on_selector("#projList", "el => el.innerHTML")
        verifie("le projet ouvert est signale « ouvert »", "ouvert</span>" in html)
        nb_ouvrir = pg.eval_on_selector_all("#projList [data-openproj]", "els => els.length")
        total = pg.evaluate("S.projects.length")
        verifie("un bouton « Ouvrir » sur chaque autre projet",
                nb_ouvrir == total - 1, "%d boutons pour %d projets" % (nb_ouvrir, total))

        # --- ouvrir B PAR LE BOUTON, comme un utilisateur ---
        pg.click('#projList [data-openproj="%s"]' % ids[1])
        pg.wait_for_timeout(1500)
        courant = pg.evaluate("S.proj && S.proj.name")
        verifie("le clic ouvre bien l'autre projet", courant == B, "projet courant : %s" % courant)
        nb_pages = pg.evaluate("S.pages.length")
        verifie("ses planches sont chargees", nb_pages == 3, "%d planche(s)" % nb_pages)
        sur_planche = pg.eval_on_selector("#tPlate", "el => el.classList.contains('sel')")
        verifie("on ARRIVE sur la planche (charger sans montrer ne sert a rien)",
                sur_planche is True)
        sel = pg.eval_on_selector("#selProj", "el => el.value")
        verifie("la liste deroulante suit le meme projet", sel == ids[1])

        # --- persistance du choix ---
        pg.reload(wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)
        apres = pg.evaluate("S.proj && S.proj.name")
        verifie("le projet ouvert survit au rechargement", apres == B, "relu : %s" % apres)

        # --- la galerie regarde ailleurs SANS deplacer l'atelier ---
        pg.click('nav button[data-tab="tGal"]')
        pg.wait_for_timeout(1500)
        vu = pg.eval_on_selector("#galProj", "el => el.value")
        verifie("la galerie s'ouvre sur le projet de travail", vu == B, "affiche %s" % vu)
        pg.select_option("#galProj", A)
        pg.wait_for_timeout(1200)
        etat = pg.eval_on_selector("#galState", "el => el.textContent")
        verifie("la galerie montre l'autre projet", A in etat, etat)
        toujours = pg.evaluate("S.proj && S.proj.name")
        verifie("consulter n'est PAS ouvrir : l'atelier n'a pas bouge",
                toujours == B, "projet de travail : %s" % toujours)

        for pid in ids:
            try:
                pg.evaluate("(id) => api('/manga/projects', {delete: id})", pid)
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
