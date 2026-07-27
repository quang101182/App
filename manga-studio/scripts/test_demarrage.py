# -*- coding: utf-8 -*-
"""« Demarrer une planche » cree-t-il un ensemble qui se TIENT ?

Le piege que ce banc existe pour attraper : la base attend `projectId` et
`pageId` en camelCase. Avec `project_id`, la planche est creee ORPHELINE --
elle existe, la requete rend 200, aucune erreur nulle part, et l'app affiche
« 0 case ». Un defaut muet, donc le pire genre.

Le banc ne se contente pas de compter des cases a l'ecran : il RELIT la base
par l'API, comme le fera le prochain chargement de l'app. Une planche orpheline
passe le premier controle et rate le second.

Usage:
    python test_demarrage.py [--headed]
    python test_demarrage.py --muter     # DOIT virer au rouge
"""
import argparse
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
APP_URL = "http://127.0.0.1:8190/manga"
LARGEUR, HAUTEUR = 360, 780
NOM = "_demarrage_%d" % os.getpid()
N_CASES = 3

cas = []


def verifie(nom, ok, detail=""):
    cas.append((nom, bool(ok), detail))
    print(("  OK   " if ok else "  ECHEC") + " " + nom + ((" — " + detail) if detail else ""))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--muter", action="store_true",
                    help="remet le `project_id` snake_case : le banc DOIT virer au rouge")
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright

    secret = open(SECRET_FILE, encoding="utf-8").read().strip()
    erreurs = []
    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=not args.headed, channel="msedge")
        pg = br.new_page(viewport={"width": LARGEUR, "height": HAUTEUR},
                         is_mobile=True, has_touch=True)
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)

        # On repond aux deux boites natives du bouton (nom, puis nombre de cases).
        reponses = [str(N_CASES)]
        pg.on("dialog", lambda d: d.accept(reponses.pop(0) if reponses else ""))

        if args.muter:
            # MUTATION : la faute d'origine. `api` est enveloppee pour retomber en
            # snake_case sur la creation de planche -- exactement le bug muet.
            pg.evaluate("""() => {
                const vrai = window.api || api;
                window.__api = vrai;
                api = async (route, body) => {
                    if (route === '/manga/pages' && body && body.projectId){
                        const b = Object.assign({}, body);
                        b.project_id = b.projectId; delete b.projectId;
                        return vrai(route, b);
                    }
                    return vrai(route, body);
                };
            }""")

        # Le champ vit dans l'onglet Projet : il faut y aller AVANT de le remplir
        # (un `fill` sur un champ masque attend indefiniment sans rien dire).
        pg.click('nav button[data-tab="tProj"]')
        pg.wait_for_timeout(600)
        pg.fill("#npName", NOM)
        pg.click("#btnDemarrer")
        pg.wait_for_timeout(4000)

        # --- 1. ce que l'app montre ---
        vues = pg.evaluate("document.querySelectorAll('#plate > *').length")
        verifie("l'app bascule sur l'onglet Planche",
                pg.evaluate("document.getElementById('tPlate').offsetParent !== null"))
        verifie("les %d cases demandees sont a l'ecran" % N_CASES,
                vues == N_CASES, "%s case(s)" % vues)

        # --- 2. ce que la BASE contient vraiment ---
        # C'est le controle qui compte : une planche orpheline s'affiche tres bien
        # dans la session qui vient de la creer, et disparait au rechargement.
        etat = pg.evaluate("""async (nom) => {
            const projs = (await api('/manga/projects')).items || [];
            const proj = projs.find(p => p.name === nom);
            if (!proj) return {proj: null};
            // ⚠ La LECTURE utilise `?project=` / `?page=` (l'ECRITURE, elle,
            // veut `projectId`/`pageId` en camelCase). Ne pas confondre les deux.
            const pages = (await api('/manga/pages?project=' + proj.id)).items || [];
            const pg0 = pages[0];
            const panels = pg0 ? ((await api('/manga/panels?page=' + pg0.id)).items || []) : [];
            return {proj: proj.id, pages: pages.length,
                    page: pg0 ? pg0.id : null, panels: panels.length,
                    idx: panels.map(x => x.idx).sort((a, b) => a - b)};
        }""", NOM)
        verifie("le projet existe en base", etat.get("proj") is not None)
        verifie("la planche est RATTACHEE au projet (piege projectId)",
                etat.get("pages") == 1, "%s planche(s) rendue(s) par le projet" % etat.get("pages"))
        verifie("les %d cases sont rattachees a la planche" % N_CASES,
                etat.get("panels") == N_CASES, "%s case(s) en base" % etat.get("panels"))
        verifie("les cases portent des idx uniques et ordonnes",
                etat.get("idx") == list(range(N_CASES)), "idx=%s" % (etat.get("idx"),))

        # --- 3. ce qui survit a un RECHARGEMENT ---
        pg.reload(wait_until="domcontentloaded")
        pg.wait_for_timeout(3000)
        apres = pg.evaluate("document.querySelectorAll('#plate > *').length")
        verifie("les cases sont encore la apres rechargement",
                apres == N_CASES, "%s case(s)" % apres)

        if etat.get("proj"):
            pg.evaluate("async (id) => api('/manga/projects', {delete: id})", etat["proj"])
        br.close()

    verifie("aucune erreur JS", not erreurs, "; ".join(erreurs[:2]))

    rates = [c for c in cas if not c[1]]
    print("\n=== %d/%d verifications passees ===" % (len(cas) - len(rates), len(cas)))
    if args.muter:
        if rates:
            print("MUTATION : le banc vire au rouge — il sait donc echouer. OK")
            return 0
        print("MUTATION : le banc reste VERT avec le bug d'origine remis. A reecrire.")
        return 1
    for nom, _, det in rates:
        print("  - " + nom + ((" (" + det + ")") if det else ""))
    return 1 if rates else 0


if __name__ == "__main__":
    sys.exit(main())
