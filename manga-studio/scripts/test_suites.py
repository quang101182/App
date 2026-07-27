# -*- coding: utf-8 -*-
"""💡 3 suites : proposer la case suivante a partir du RECIT deja ecrit.

C'est la premiere brique du mode chapitre automatique, et la seule qui traite
la continuite sans depenser un watt de GPU : la suite se deduit des cases
PRECEDENTES (jusqu'a 5), pas de la derniere image.

Ce que le banc verifie :
  - le contexte envoye contient bien les cases precedentes, DANS L'ORDRE, avec
    leurs dialogues -- une suite deduite d'une seule case n'est pas une suite ;
  - 3 propositions, distinctes, non numerotees ;
  - un clic en reprend une : elle remplace le texte de la case, le panneau se
    referme, l'apercu suit, et la case est enregistree.

La reponse du LLM est FIGEE (routee par Playwright) : ce qui est teste, c'est
la chaine de l'app, pas l'inspiration d'un modele de langue un jour donne.

Usage:
    python test_suites.py [--headed]
    python test_suites.py --muter     # DOIT virer au rouge
"""
import argparse
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
APP_URL = "http://127.0.0.1:8190/manga"
LARGEUR, HAUTEUR = 360, 780
NOM = "_suites_%d" % os.getpid()

PROPOSITIONS = [
    "Le professeur se retourne lentement vers la classe, gros plan sur son regard.",
    "Un carnet tombe au sol dans un silence total, plan serre sur les pages.",
    "La fenetre explose et une silhouette atterrit sur le bureau, plan large.",
]
# Le LLM numerote souvent ses reponses : l'app doit nettoyer. On le lui impose.
REPONSE = {"prompt": "1. " + PROPOSITIONS[0] + "\n- " + PROPOSITIONS[1]
                     + "\n3) " + PROPOSITIONS[2]}

cas = []
vues_requetes = []


def verifie(nom, ok, detail=""):
    cas.append((nom, bool(ok), detail))
    print(("  OK   " if ok else "  ECHEC") + " " + nom + ((" — " + detail) if detail else ""))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--muter", action="store_true",
                    help="le contexte se reduit a la derniere case : DOIT virer au rouge")
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright

    secret = open(SECRET_FILE, encoding="utf-8").read().strip()
    erreurs = []
    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=not args.headed, channel="msedge")
        pg = br.new_page(viewport={"width": LARGEUR, "height": HAUTEUR},
                         is_mobile=True, has_touch=True)
        pg.on("pageerror", lambda e: erreurs.append(str(e)))

        def repond(route):
            try:
                vues_requetes.append(json.loads(route.request.post_data or "{}"))
            except Exception:
                vues_requetes.append({})
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps(REPONSE))
        pg.route("**/enhance", repond)

        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)

        # --- une planche de 4 cases racontant quelque chose ---
        cible = pg.evaluate("""async ([nom, mute]) => {
            const proj = await api('/manga/projects', {name: nom, slug: nom});
            const cree = await api('/manga/pages', {projectId: proj.id, title: nom,
                                                    chapter: '1', idx: 0, layout: {cols: 2}});
            const page = ((await api('/manga/pages?project=' + proj.id)).items || [])
                           .find(x => x.id === cree.id);
            const textes = ['la cloche sonne dans une classe vide',
                            'une eleve entre en courant',
                            'elle pose un carnet sur le bureau',
                            ''];
            for (let i = 0; i < textes.length; i++){
                await api('/manga/panels', {pageId: page.id, kind: 'dialogue',
                                            prompt: textes[i], idx: i});
            }
            S.proj = proj; S.page = page;
            S.panels = ((await api('/manga/panels?page=' + page.id)).items || [])
                         .sort((a, b) => a.idx - b.idx);
            S.panels[1].bubbles = [{id: 'b1', text: 'Je suis en retard !', x: .5, y: .2,
                                    w: .4, h: .2, shape: 'oval'}];
            renderPlate();
            return {proj: proj.id, pid: S.panels[3].id};
        }""", [NOM, bool(args.muter)])

        if args.muter:
            # MUTATION : le recit est ampute -- il ne reste que la case juste
            # avant. C'est exactement ce qui rendait les suites incoherentes, et
            # ca ne se voit NULLE PART ailleurs que dans la requete envoyee :
            # trois propositions plausibles s'affichent quand meme.
            pg.evaluate("""(pid) => {
                const cible = S.panels.find(x => x.id === pid);
                const avant = S.panels[S.panels.indexOf(cible) - 1];
                S.panels = [avant, cible];
                renderPlate();
            }""", cible["pid"])

        sel = '[data-pid="%s"]' % cible["pid"]
        pg.click(sel + ' [data-act="idees"]')
        pg.wait_for_timeout(2000)

        print("\n--- ce que l'app a VRAIMENT demande au modele ---")
        idea = (vues_requetes[-1] or {}).get("idea", "") if vues_requetes else ""
        print("   " + idea.replace("\n", " | ")[:200])
        verifie("les cases precedentes sont envoyees en contexte",
                "cloche sonne" in idea, "1re case %s" % ("presente" if "cloche" in idea else "ABSENTE"))
        verifie("le contexte porte PLUSIEURS cases, pas seulement la derniere",
                sum(m in idea for m in ("cloche sonne", "entre en courant", "carnet")) >= 3,
                "%d/3 cases retrouvees" % sum(m in idea for m in
                                              ("cloche sonne", "entre en courant", "carnet")))
        verifie("les dialogues des cases sont joints au contexte",
                "en retard" in idea)
        verifie("les cases sont numerotees dans l'ordre de lecture",
                idea.find("cloche") < idea.find("carnet"))

        print("\n--- les propositions a l'ecran ---")
        idees = pg.evaluate("(s) => [...document.querySelectorAll(s + ' [data-idee]')]"
                            ".map(b => b.dataset.idee)", sel)
        verifie("3 propositions sont affichees", len(idees) == 3, "%d" % len(idees))
        verifie("elles sont distinctes", len(set(idees)) == len(idees))
        verifie("la numerotation du modele a ete nettoyee",
                all(not i[:3].strip().startswith(("1", "2", "3", "-", "*")) for i in idees),
                idees[0][:40] if idees else "")

        print("\n--- reprendre une proposition en un clic ---")
        avant = pg.input_value(sel + " [data-prompt]")
        pg.click(sel + ' [data-idee="%s"]' % idees[1].replace('"', '&quot;'))
        pg.wait_for_timeout(1200)
        apres = pg.input_value(sel + " [data-prompt]")
        verifie("le texte de la case est remplace par la proposition",
                apres == idees[1] and apres != avant, apres[:60])
        verifie("le panneau se referme apres la reprise",
                pg.evaluate("(s) => document.querySelector(s + ' [data-idees]').hidden", sel))
        verifie("l'apercu suit la reprise",
                idees[1][:20] in pg.inner_text(sel + " [data-apercu]"))
        enreg = pg.evaluate("""async ([pid, pageid]) => {
            const items = (await api('/manga/panels?page=' + pageid)).items || [];
            return (items.find(x => x.id === pid) || {}).prompt;
        }""", [cible["pid"], pg.evaluate("S.page.id")])
        verifie("la reprise est ENREGISTREE (elle survit au rechargement)",
                enreg == idees[1], (enreg or "")[:60])

        pg.evaluate("async (id) => api('/manga/projects', {delete: id})", cible["proj"])
        br.close()

    verifie("aucune erreur JS", not erreurs, "; ".join(erreurs[:2]))

    rates = [c for c in cas if not c[1]]
    print("\n=== %d/%d verifications passees ===" % (len(cas) - len(rates), len(cas)))
    if args.muter:
        if rates:
            print("MUTATION : le banc vire au rouge — il sait donc echouer. OK")
            return 0
        print("MUTATION : le banc reste VERT avec un contexte ampute. A reecrire.")
        return 1
    for nom, _, det in rates:
        print("  - " + nom + ((" (" + det + ")") if det else ""))
    return 1 if rates else 0


if __name__ == "__main__":
    sys.exit(main())
