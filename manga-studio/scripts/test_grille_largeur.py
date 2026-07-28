# -*- coding: utf-8 -*-
"""La planche tient-elle ses COLONNES, et occupe-t-elle l'ecran ? (v1.61.0)

Regression signalee par Quang le 28/07, capture PC a l'appui : « vu que ca ne
s'affiche plus sur deux colonnes ». Cause : le separateur de scene (v1.59.0)
etait pose AVANT CHAQUE case en `grid-column:1/-1` -- chaque case demarrait donc
apres une ligne pleine largeur, soit UNE case par ligne.

⚠ Ce banc MESURE LA GEOMETRIE (`getBoundingClientRect`), il ne lit pas le CSS.
Deux cases sont sur la meme ligne si elles partagent leur `top`, point. Compter
des regles CSS aurait laisse passer exactement ce defaut : le
`grid-template-columns` etait JUSTE pendant tout ce temps.

Il verifie aussi les deux sens de la largeur :
  - planche a 2 colonnes sur grand ecran -> elle s'etale ;
  - planche a 1 colonne -> elle garde la largeur de lecture voulue le 27/07.

Usage:
    python test_grille_largeur.py
    python test_grille_largeur.py --muter     # DOIT virer au rouge
"""
import argparse
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
APP_URL = "http://127.0.0.1:8190/manga"
NOM = "_grille_%d" % os.getpid()
SORTIE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "essai_out")

cas = []


def verifie(nom, ok, detail=""):
    cas.append((nom, bool(ok)))
    print(("  OK    " if ok else "  ECHEC") + " " + nom + ((" — " + detail) if detail else ""))
    return ok


# Combien de cases partagent la meme ligne ? On tolere 4 px : une bordure ou un
# badge de 1 px ne fait pas une nouvelle ligne.
JS_LIGNES = """() => {
  const cartes = [...document.querySelectorAll('#plate [data-pid]')];
  const lignes = [];
  cartes.forEach(c => {
    const t = c.getBoundingClientRect().top;
    const l = lignes.find(x => Math.abs(x.top - t) < 4);
    if (l) l.n++; else lignes.push({top: t, n: 1});
  });
  return { cases: cartes.length, lignes: lignes.map(l => l.n),
           parLigneMax: Math.max(0, ...lignes.map(l => l.n)),
           largeurPlate: document.getElementById('plate').getBoundingClientRect().width,
           largeurFenetre: window.innerWidth };
}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--muter", action="store_true")
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright
    os.makedirs(SORTIE, exist_ok=True)

    secret = open(SECRET_FILE, encoding="utf-8").read().strip()
    erreurs = []
    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=not args.headed, channel="msedge")
        # L'ecran de Quang, pas un mobile : c'est la qu'il a vu le defaut.
        pg = br.new_page(viewport={"width": 1400, "height": 950})
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        pg.set_default_timeout(120000)
        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_function("typeof applyPlateColumns === 'function'")

        if args.muter:
            # MUTATION : on remet le separateur AVANT CHAQUE case, le defaut exact
            # de la v1.59.0. Le banc DOIT retomber a 1 case par ligne.
            pg.evaluate("() => { window.ouvreUneScene = () => true; }")

        base = pg.evaluate("""async (nom) => {
            const proj = await api('/manga/projects', {name: nom, slug: nom});
            const cree = await api('/manga/pages', {projectId: proj.id, title: nom,
                                     chapter: '1', idx: 0, layout: {cols: 2}});
            const page = ((await api('/manga/pages?project=' + proj.id)).items || [])
                           .find(x => x.id === cree.id);
            S.proj = proj; S.page = page;
            for (let i = 0; i < 6; i++){
              await api('/manga/panels', {pageId: page.id, kind: 'dialogue', idx: i,
                        prompt: 'case ' + (i + 1),
                        recipe: i === 3 ? {debutScene: true} : {}});
            }
            S.panels = ((await api('/manga/panels?page=' + page.id)).items || []);
            renderPlate();
            return {proj: proj.id, page: page.id};
        }""", NOM)

        g = pg.evaluate(JS_LIGNES)
        verifie("les 6 cases sont rendues", g["cases"] == 6, "%d" % g["cases"])
        verifie("la planche est bien sur 2 COLONNES (mesuré, pas déduit du CSS)",
                g["parLigneMax"] == 2, "cases par ligne : %s" % g["lignes"])
        # 6 cases, une coupure a la 4e : 2+1 puis 2+1 -> 4 lignes, jamais 6.
        verifie("la frontière de scène coupe la ligne, les autres cases non",
                len(g["lignes"]) == 4, "%d ligne(s) : %s" % (len(g["lignes"]), g["lignes"]))
        # ⚠ v1.61.0 : Quang a demande de REVENIR a la largeur initiale — « respecter
        # la largeur de l'application, par exemple par rapport au bandeau du haut,
        # et ne pas la faire depasser ». Le contenu s'etalait a 1600 px pendant que
        # le bandeau restait a 760 : deux largeurs pour une meme page. Ce qu'il
        # avait perdu, c'etaient les COLONNES, pas la largeur.
        entete = pg.evaluate(
            "() => document.querySelector('.hdrin').getBoundingClientRect().width")
        verifie("la planche ne dépasse PAS la largeur du bandeau du haut",
                g["largeurPlate"] <= entete + 30,
                "planche %d px · bandeau %d px" % (g["largeurPlate"], entete))

        # Un seul séparateur affiché : celui de la vraie frontière.
        n_sep = pg.evaluate("() => document.querySelectorAll('#plate .scenesep').length")
        verifie("un seul séparateur à l'écran (la frontière), pas un par case",
                n_sep == 1, "%d séparateur(s)" % n_sep)

        # Le geste reste accessible partout, depuis le tiroir Affiner.
        boutons = pg.evaluate(
            "() => document.querySelectorAll('#plate [data-scenecut]').length")
        verifie("couper une scène reste possible depuis chaque case",
                boutons >= 5, "%d bouton(s) « couper/rattacher »" % boutons)

        pg.screenshot(path=os.path.join(
            SORTIE, "grille_2col%s.png" % ("_MUTE" if args.muter else "")))

        # --- 1 colonne : la largeur de lecture voulue le 27/07 doit revenir ---
        pg.evaluate("""async () => {
            S.page.layout = Object.assign({}, S.page.layout, {cols: 1});
            await api('/manga/pages', S.page);
            renderPlate();
        }""")
        pg.wait_for_timeout(300)
        g1 = pg.evaluate(JS_LIGNES)
        verifie("en 1 colonne aussi, la largeur de lecture est tenue (≤ 760 px)",
                g1["largeurPlate"] <= 760,
                "%d px" % g1["largeurPlate"])

        # --- telephone : rien ne change pour lui -----------------------------
        pg.set_viewport_size({"width": 360, "height": 780})
        pg.evaluate("""async () => {
            S.page.layout = Object.assign({}, S.page.layout, {cols: 2});
            await api('/manga/pages', S.page);
            renderPlate();
        }""")
        pg.wait_for_timeout(300)
        gm = pg.evaluate(JS_LIGNES)
        verifie("sur 360 px, une seule case par ligne (inchangé)",
                gm["parLigneMax"] == 1, "cases par ligne : %s" % gm["lignes"])
        deb = pg.evaluate("""() => {
            const d = document.documentElement;
            return d.scrollWidth - d.clientWidth; }""")
        verifie("rien ne déborde à 360 px", deb <= 0, "+%d px" % deb)

        # --- `hidden` cache-t-il VRAIMENT ? (piege paye 3 fois ici) ----------
        # Un `display` d'auteur ecrase le `display:none` implicite de `hidden`.
        # On le verifie sur un element PORTEUR d'un `display` (.row), pas sur un
        # element neutre : un test sur un cas facile ne prouverait rien.
        cache = pg.evaluate("""() => {
            const d = document.createElement('div');
            d.className = 'row'; d.hidden = true; d.textContent = 'x';
            document.body.appendChild(d);
            const vu = getComputedStyle(d).display;
            const rect = d.getBoundingClientRect();
            d.remove();
            return { display: vu, h: rect.height };
        }""")
        verifie("un élément .row marqué `hidden` est réellement caché",
                cache["display"] == "none" and cache["h"] == 0,
                "display=%s hauteur=%s" % (cache["display"], cache["h"]))

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
        print("MUTATION : VERTE = le banc ne mesure pas la grille.")
        return 1
    for n in ko:
        print("  - " + n)
    return 1 if ko else 0


if __name__ == "__main__":
    sys.exit(main())
