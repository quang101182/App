# -*- coding: utf-8 -*-
"""Le clavier du telephone reste-t-il ouvert quand on ecrit dans une case ?

Bug remonte par Quang le 27/07, sur son telephone : « quand je selectionne la
cellule, mon clavier apparait et disparait immediatement ». Impossible d'ecrire
une seule lettre.

CAUSE, trouvee dans le code et non devinee : `window.addEventListener("resize",
() => renderPlate())`. Sur mobile, l'ouverture du clavier virtuel REDIMENSIONNE
la fenetre (la hauteur utile diminue). Le resize rappelait renderPlate, qui
reconstruit toute la planche en `innerHTML` — le textarea qui venait de recevoir
le focus etait donc DETRUIT, et le clavier se refermait dans la foulee.

CE QUE MESURE CE BANC : apres un redimensionnement en HAUTEUR seule (ce que fait
exactement un clavier virtuel), le champ garde-t-il le focus ?
  - focus perdu  -> le clavier se referme chez l'utilisateur : ROUGE
  - focus garde  -> il peut ecrire : VERT

Et il est FALSIFIABLE : `--muter` reinjecte l'ancien comportement dans la page
avant de tester. Le banc DOIT alors virer au rouge. Un test qui ne sait pas
echouer ne prouve rien — c'est la regle payee sur ce projet.

Usage:
    python test_clavier_mobile.py
    python test_clavier_mobile.py --muter      (doit ECHOUER : preuve du test)
"""
import argparse
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
APP_URL = "http://127.0.0.1:8190/manga"
# 360 px = la largeur du telephone de Quang (le Honor), pas celle du Samsung.
LARGEUR, HAUTEUR = 360, 780
HAUTEUR_CLAVIER = 380   # ce qu'il reste de hauteur quand le clavier est ouvert


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--muter", action="store_true",
                    help="reinjecte le bug pour verifier que le banc sait echouer")
    ap.add_argument("--headed", action="store_true")
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright

    secret = open(SECRET_FILE, encoding="utf-8").read().strip()
    erreurs = []
    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=not args.headed, channel="msedge")
        pg = br.new_page(viewport={"width": LARGEUR, "height": HAUTEUR},
                         has_touch=True, is_mobile=True)
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)

        # Une planche jetable, creee par l'API de l'app : le banc ne doit pas
        # dependre d'un projet que Quang aurait supprime entre deux sessions.
        # On passe par la fonction api() de l'app : elle porte le token. Un fetch
        # brut part sans en-tete Authorization et se fait refuser en 401 (paye ici).
        ok = pg.evaluate("""async () => {
            const proj = await api('/manga/projects', {name:'_test_clavier'});
            const id = proj.id || (proj.item && proj.item.id);
            if (!id) return false;
            const p = await api('/manga/pages', {project_id:id, title:'clavier', chapter:1});
            const pid = p.id || (p.item && p.item.id);
            if (!pid) return false;
            await api('/manga/panels', {page_id:pid, kind:'dialogue', prompt:'test', idx:0});
            return true;
        }""")
        if not ok:
            print("ARRET : impossible de creer la planche de test (proxy joignable ?)")
            br.close()
            return 2
        pg.reload(wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)

        champ = pg.query_selector("#plate textarea[data-prompt]")
        if not champ:
            print("ARRET : aucune case affichee -> le banc ne peut RIEN conclure.")
            print("        (une page vide qui passe le test serait un faux vert)")
            br.close()
            return 2

        if args.muter:
            # On remet exactement le comportement d'avant le correctif.
            pg.evaluate("window.addEventListener('resize', () => renderPlate());")
            print("MUTATION ACTIVE : l'ancien comportement est reinjecte.")

        champ.click()
        pg.wait_for_timeout(300)
        avant = pg.evaluate(
            "() => document.activeElement && document.activeElement.hasAttribute('data-prompt')")
        print("focus obtenu sur le champ            : %s" % ("oui" if avant else "NON"))
        if not avant:
            print("ARRET : le champ n'a meme pas pris le focus.")
            br.close()
            return 2

        # Le geste qui compte : la hauteur diminue, la largeur ne bouge pas.
        # C'est exactement la signature d'un clavier virtuel qui s'ouvre.
        pg.set_viewport_size({"width": LARGEUR, "height": HAUTEUR_CLAVIER})
        pg.wait_for_timeout(600)
        apres = pg.evaluate(
            "() => document.activeElement && document.activeElement.hasAttribute('data-prompt')")
        # On verifie aussi que le champ n'a pas ete remplace par un clone : un
        # focus present sur un element neuf ne rendrait pas le clavier a l'user.
        meme = pg.evaluate("""() => {
            const t = document.querySelector('#plate textarea[data-prompt]');
            return !!(t && t === document.activeElement);
        }""")
        print("focus CONSERVE apres redimensionnement: %s" % ("oui" if apres else "NON"))
        print("c'est bien le MEME element (pas un clone) : %s" % ("oui" if meme else "NON"))

        # On tape reellement, comme l'utilisateur : la preuve finale.
        pg.keyboard.type("bonjour")
        texte = pg.evaluate(
            "() => { const t=document.querySelector('#plate textarea[data-prompt]'); return t? t.value : ''; }")
        tape = "bonjour" in texte
        print("texte reellement saisi apres coup     : %s (%r)"
              % ("oui" if tape else "NON", texte[:40]))

        # Menage : on ne laisse pas de projet de test derriere soi.
        pg.evaluate("""async () => {
            const l = await api('/manga/projects');
            const p = (l.projects || l.items || l || []).find(x => x.name === '_test_clavier');
            if (p) await api('/manga/projects', {delete: p.id});
        }""")
        br.close()

    print("\nerreurs JS : %d" % len(erreurs))
    vert = apres and meme and tape and not erreurs
    print("\nVERDICT : %s" % ("VERT — le clavier reste ouvert, on peut ecrire."
                              if vert else
                              "ROUGE — le champ perd le focus : clavier qui se referme."))
    if args.muter:
        print("(mutation active : ce ROUGE est le resultat ATTENDU, il prouve le banc)")
        return 0 if not vert else 1
    return 0 if vert else 1


if __name__ == "__main__":
    sys.exit(main())
