# -*- coding: utf-8 -*-
"""Regenerer un LOT de cases choisies. (v1.64.0)

Demande de Quang (28/07) : « un bouton [...] soit je regenere tout, soit je
selectionne [...] une vue miniature des cases, puis je choisis lesquelles -- au
lieu de le faire case par case ».

Et, dans la foulee, le defaut qu'il a signale sur le bouton voisin :
« j'ajoute des cases vides, je clique sur "generer toutes les cases vides", il
dit qu'il n'y a aucune case vide a generer ». Le filtre exigeait un TEXTE (une
case sans description ne peut pas etre dessinee) mais le message n'en disait
rien -- et le LIBELLE parlait de « cases vides ». Les deux mentaient.

Ce banc verifie :
  1. la pop-up s'ouvre et montre UNE vignette par case ;
  2. les cases deja dessinees sont PRE-COCHEES, celles sans texte sont
     desactivees (on ne peut pas dessiner sans description) ;
  3. « tout cocher » / « tout decocher » n'activent jamais l'indesactivable ;
  4. le lot regenere REELLEMENT : nouveau fichier, nouvelle SEED, et l'essai
     precedent est CONSERVE (rien n'est perdu) ;
  5. le refus du bouton voisin NOMME sa raison (les numeros des cases sans texte).

Usage:
    python test_regen_lot.py                 sans GPU (points 1,2,3,5)
    python test_regen_lot.py --live          + une vraie regeneration (point 4)
    python test_regen_lot.py --muter         DOIT virer au rouge
"""
import argparse
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
APP_URL = "http://127.0.0.1:8190/manga"
NOM = "_regen_%d" % os.getpid()
SORTIE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "essai_out")

cas = []


def verifie(nom, ok, detail=""):
    cas.append((nom, bool(ok)))
    print(("  OK    " if ok else "  ECHEC") + " " + nom + ((" — " + detail) if detail else ""))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--muter", action="store_true")
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright
    os.makedirs(SORTIE, exist_ok=True)

    secret = open(SECRET_FILE, encoding="utf-8").read().strip()
    erreurs = []
    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=not args.headed, channel="msedge")
        pg = br.new_page(viewport={"width": 360, "height": 900})
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        pg.set_default_timeout(120000)
        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_function("typeof ouvrirRegen === 'function'")

        if args.muter:
            # MUTATION : le lot ne tire plus de seed neuve (il regenererait la
            # MEME image). Le point 4 DOIT tomber -- et lui seul.
            # MUTATION : le lot ne tire plus de seed neuve -- il garde celle de
            # l'essai precedent, donc il redessine LA MEME image. Le point 4
            # doit tomber. (Premier jet : la mutation forcait seed=1234 DANS
            # genPanel -- la seed changeait quand meme, le banc restait vert et
            # ne prouvait rien. Une mutation doit retirer le comportement, pas
            # le remplacer par un autre qui y ressemble.)
            pg.evaluate("() => { window.seedNeuve = p => (p.recipe && p.recipe.seed) || 1; }")

        # 3 cases : deux decrites, une SANS texte (le cas de Quang).
        base = pg.evaluate("""async (nom) => {
            const proj = await api('/manga/projects', {name: nom, slug: nom});
            const cree = await api('/manga/pages', {projectId: proj.id, title: nom,
                                     chapter: '1', idx: 0, layout: {cols: 2}});
            const page = ((await api('/manga/pages?project=' + proj.id)).items || [])
                           .find(x => x.id === cree.id);
            S.proj = proj; S.page = page;
            const t = ['un dojo vide au petit matin', 'une main serree sur un sabre', ''];
            for (let i = 0; i < 3; i++)
              await api('/manga/panels', {pageId: page.id, kind: 'dialogue', idx: i,
                                          prompt: t[i], recipe: {}});
            S.panels = ((await api('/manga/panels?page=' + page.id)).items || []);
            // La case 1 a « deja » une image : c'est elle qui doit etre pre-cochee.
            S.panels[0].file = 'xxx/faux_essai.png';
            S.panels[0].recipe = {seed: 111, versions: [{file: 'xxx/faux_essai.png', ts: 1, seed: 111}]};
            renderPlate();
            return {proj: proj.id, page: page.id};
        }""", NOM)

        # --- 5 : le refus du bouton voisin nomme sa raison -------------------
        # ⚠ On met la planche dans l'etat OU LE REFUS DOIT ARRIVER : plus aucune
        # case generable. Premier jet : la case 2 avait un texte, `genAll` a donc
        # fait son travail -- il a genere pour de vrai (30 s de GPU) -- et le banc
        # a conclu « il ne nomme pas la case fautive ». Un banc qui ne dresse pas
        # l'etat qu'il teste mesure autre chose que ce qu'il croit.
        msg = pg.evaluate("""async () => {
            const memoire = S.panels[1].file;
            S.panels[1].file = 'xxx/faux_essai2.png';   // plus rien a generer
            let vu = '';
            const vrai = toast; window.toast = t => { vu = t; };
            await genAll();
            window.toast = vrai;
            S.panels[1].file = memoire;                 // on remet l'etat d'avant
            renderPlate();
            return vu;
        }""")
        verifie("« Générer les cases décrites » nomme la case fautive",
                "3" in msg and ("écris" in msg or "texte" in msg), msg)

        # --- 1 & 2 : la pop-up ----------------------------------------------
        pg.evaluate("() => ouvrirRegen()")
        pg.wait_for_timeout(250)
        vu = pg.evaluate("""() => {
            const g = document.getElementById('regenGrid');
            const l = [...g.querySelectorAll('[data-rid]')];
            return { ouvert: !document.getElementById('regen').hidden,
                     vignettes: l.length,
                     cochees: l.filter(x => x.querySelector('input').checked).length,
                     desactivees: l.filter(x => x.querySelector('input').disabled).length,
                     etat: document.getElementById('regenState').textContent };
        }""")
        verifie("la pop-up s'ouvre", vu["ouvert"])
        verifie("une vignette par case", vu["vignettes"] == 3, "%d" % vu["vignettes"])
        verifie("la case déjà dessinée est PRÉ-COCHÉE, elle seule",
                vu["cochees"] == 1, "%d cochée(s)" % vu["cochees"])
        verifie("la case sans texte est désactivée",
                vu["desactivees"] == 1, "%d désactivée(s)" % vu["desactivees"])
        verifie("le compteur dit ce qui est sélectionné", "1" in vu["etat"], vu["etat"])

        # --- 3 : tout cocher n'active pas l'indesactivable -------------------
        pg.click("#regenAll")
        pg.wait_for_timeout(150)
        ap_ = pg.evaluate("""() => {
            const l = [...document.querySelectorAll('#regenGrid [data-rid] input')];
            return { coches: l.filter(x => x.checked).length,
                     desactive_coche: l.filter(x => x.disabled && x.checked).length };
        }""")
        verifie("« tout cocher » prend les cases descriptibles (2 sur 3)",
                ap_["coches"] == 2, "%d" % ap_["coches"])
        verifie("… et n'active JAMAIS une case sans texte",
                ap_["desactive_coche"] == 0)
        pg.click("#regenNone")
        pg.wait_for_timeout(150)
        verifie("« tout décocher » vide la sélection",
                pg.evaluate("() => casesRegenChoisies().length") == 0)

        # --- 4 : la regeneration REELLE --------------------------------------
        if args.live:
            pg.evaluate("""async () => {
                // On repart d'une case VRAIMENT generee, sinon on mesure un faux.
                const p = S.panels[1];
                document.getElementById('regen').hidden = true;
                await genPanel(p);
            }""")
            pg.wait_for_function("() => S.panels[1].file && !S.panels[1].file.includes('faux')",
                                 timeout=300000)
            avant = pg.evaluate("""() => ({ file: S.panels[1].file,
                                            seed: S.panels[1].recipe.seed,
                                            versions: (S.panels[1].recipe.versions||[]).length })""")
            # ⚠ ON OUVRE LE TIROIR « Affiner » de la case : c'est LA condition qui
            # revele le defaut. Tiroir ferme, `genPanel` tire lui-meme une seed et
            # tout semble marcher ; tiroir ouvert, le champ porte l'ancienne valeur
            # et gagne -- le lot redessinait la MEME image sans rien dire.
            pg.evaluate("""() => { S.affiner = S.panels[1].id; renderPlate(); }""")
            pg.wait_for_timeout(200)
            pg.evaluate("() => ouvrirRegen()")
            pg.wait_for_timeout(250)
            pg.evaluate("""() => {
                document.querySelectorAll('#regenGrid [data-rid]').forEach(l => {
                  const c = l.querySelector('input');
                  c.checked = (l.dataset.rid === S.panels[1].id) && !c.disabled;
                });
                majRegenState();
            }""")
            pg.click("#regenGo")
            pg.wait_for_function("""(f) => S.panels[1].file && S.panels[1].file !== f""",
                                 arg=avant["file"], timeout=300000)
            apres = pg.evaluate("""() => ({ file: S.panels[1].file,
                                            seed: S.panels[1].recipe.seed,
                                            versions: (S.panels[1].recipe.versions||[]).length })""")
            verifie("le lot produit une NOUVELLE image", apres["file"] != avant["file"],
                    apres["file"])
            verifie("avec une SEED neuve (sinon on redessine la même)",
                    apres["seed"] != avant["seed"],
                    "%s -> %s%s" % (avant["seed"], apres["seed"],
                                    "  [MUTE]" if args.muter else ""))
            verifie("et l'essai précédent est CONSERVÉ",
                    apres["versions"] > avant["versions"],
                    "%d -> %d essais" % (avant["versions"], apres["versions"]))

        # Rien ne doit deborder a 360 px avec la pop-up ouverte.
        pg.evaluate("() => ouvrirRegen()")
        pg.wait_for_timeout(250)
        deb = pg.evaluate("""() => {
            const d = document.documentElement;
            return d.scrollWidth - d.clientWidth; }""")
        verifie("rien ne déborde à 360 px, pop-up ouverte", deb <= 0, "+%d px" % deb)
        pg.screenshot(path=os.path.join(
            SORTIE, "regen_popup%s.png" % ("_MUTE" if args.muter else "")))

        pg.evaluate("async (p) => { await api('/manga/projects', {delete: p}); }",
                    base["proj"])
        br.close()

    verifie("aucune erreur JS", not erreurs, "; ".join(erreurs[:2]))
    ko = [n for n, ok in cas if not ok]
    print("\n%d/%d" % (len(cas) - len(ko), len(cas)))
    if args.muter:
        if ko:
            print("MUTATION : rouge comme attendu (%d cas) — le banc mord." % len(ko))
            return 0
        print("MUTATION : VERTE = le banc ne teste pas la seed. A réparer.")
        return 1
    for n in ko:
        print("  - " + n)
    return 1 if ko else 0


if __name__ == "__main__":
    sys.exit(main())
