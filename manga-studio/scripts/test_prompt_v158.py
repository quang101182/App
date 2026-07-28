# -*- coding: utf-8 -*-
"""Le prompt construit par l'app respecte-t-il ce que Quang a ecrit ? (v1.58.0)

Ne teste PAS une reimplementation : il appelle `promptFinal()` DANS la page,
celle qui sert a la generation ET a l'apercu. Un banc qui recopie la logique
qu'il verifie ne verifie que lui-meme (lecon payee le 21/07 sur Jarvis).

Les cas viennent des VRAIES cases de Quang (base studio_content.db, 28/07) et
du banc de traduction. Chacun porte le defaut qu'il doit interdire :

  A. gros plan sur une partie du corps  -> aucune identite (ni tenue, ni cheveux)
     Reel : « close-up, his hands, clenched fists » partait avec
     `1man, short hair, 30 years old` -- de quoi elargir le cadre.
  B. gros plan sur le visage            -> les traits, PAS la tenue
     Reel : une scene nue partait avec `sailor uniform`.
  C. case sans personne                 -> no humans, zero comptage, zero identite
     Reel : « aucun personnage » ressortait en `1girl, ..., no humans`.
  D. negation                           -> au NEGATIF, jamais en tag positif
     Reel : « pas de tete » -> `no head, no face` (5 cas sur 14 au banc).
  E. comptage                           -> un seul, jamais deux qui se contredisent
     Reel : « Le dernier eleve » case 11 partait avec `2people` ET `1girl, 1boy`.
  F. style                              -> dedoublonne (Magic woman : 31 tags, 3 doublons)
  G. la phrase de l'utilisateur         -> conservee, jamais ecrasee

Usage:
    python test_prompt_v158.py
    python test_prompt_v158.py --muter    # DOIT virer au rouge
"""
import argparse
import io
import json
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
APP_URL = "http://127.0.0.1:8190/manga"

# Les deux fiches reelles du projet, telles qu'elles sont en base.
KIMIKO = {"id": "K", "name": "Kimiko", "role": "second", "refs": ["kimiko.png"],
          "tags": "1girl, black hair, short hair, sharp eyes, pale skin, sailor uniform"}
JO = {"id": "J", "name": "Jo", "role": "second", "refs": ["jo.png"],
      "tags": "1man, short hair, 30 years old"}

STYLE = ("masterpiece, best quality, very aesthetic, absurdres, monochrome, "
         "greyscale, manga, screentone, halftone, lineart, monochrome, screentone")

# (id, tags de la case, casting, ce qui DOIT etre absent, ce qui DOIT etre present)
CAS = [
    ("A-mains", "close-up, hands, clenched hands", ["J"],
     ["short hair", "30 years old"], ["close-up", "hands"]),
    ("A-pieds", "extreme close-up, toes on penis, bondage", ["K"],
     ["sailor uniform", "black hair", "pale skin"], ["toes"]),
    ("B-visage", "close-up, her eyes, determined expression", ["K"],
     ["sailor uniform"], ["black hair", "sharp eyes"]),
    ("C-vide", "empty dojo, morning light through windows, no people", ["K", "J"],
     ["sailor uniform", "1girl", "2people", "solo", "1man"], ["no humans"]),
    ("C-vide2", "1girl, classroom window, rain, no humans", ["K"],
     ["1girl", "sailor uniform", "solo"], ["no humans", "classroom window"]),
    ("D-negation", "close-up, toes resting on him, no head, no face", [],
     ["no head", "no face"], ["close-up", "toes"]),
    ("E-comptage", "1girl, 1boy, standing, guard up", ["K", "J"],
     ["2people"], ["1girl", "1boy"]),
    ("F-large", "wide shot, dojo, two characters facing each other", ["K", "J"],
     [], ["sailor uniform", "30 years old"]),
]

resultats = []


def verifie(nom, ok, detail=""):
    resultats.append((nom, bool(ok)))
    print(("  OK    " if ok else "  ECHEC") + " " + nom + ((" — " + detail) if detail else ""))
    return ok


JS_PREPARE = """(d) => {
  // On pose le decor du projet : la recette et les fiches. On ne remplace AUCUNE
  // fonction -- c'est bien `promptFinal` de la page qui repondra.
  //
  // WARN Piege paye a l'ecriture de ce banc, et il est generique : `CHARS` est
  // declare `let` et `S` `const` -- des liaisons LEXICALES, qui ne sont PAS des
  // proprietes de `window`. Ecrire `window.CHARS = [...]` cree une variable
  // homonyme que la page ne lit jamais : le casting restait VIDE, et les cas
  // « ce tag doit etre absent » passaient au vert pour la mauvaise raison.
  // On MUTE donc les objets existants, on ne les remplace pas.
  CHARS.length = 0; d.chars.forEach(c => CHARS.push(c));
  S.proj = { id: 'banc', slug: 'banc', recipe: { style: d.style, theme: '', ident: '',
             trigger: '', neg: 'bad quality, worst quality' } };
  S.page = { id: 'pg', layout: { cols: 2, casting: [] } };
  S.panels = [];
  return CHARS.length;
}"""

JS_CAS = """(c) => {
  // WARN Le decor se repose A CHAQUE CAS, et ce n'est pas de la prudence
  // decorative : l'app charge ses fiches en asynchrone et REASSIGNE `CHARS`
  // (`CHARS = await api(...)`). Un decor pose une fois avant la boucle est
  // donc efface en cours de route -- les premiers cas passaient, les derniers
  // echouaient, et le banc accusait l'app d'un defaut qui etait le sien.
  CHARS.length = 0; c.chars.forEach(x => CHARS.push(x));
  S.proj = { id: 'banc', slug: 'banc', recipe: { style: c.style, theme: '', ident: '',
             trigger: '', neg: 'bad quality, worst quality' } };
  S.page = { id: 'pg', layout: { cols: 2, casting: [] } };
  const p = { id: 'x', kind: 'dialogue', prompt: c.phrase,
              recipe: { tags: c.tags, casting: c.casting } };
  return { final: promptFinal(p),
           fiches: CHARS.length,
           niveau: sceneSansPersonne(p) ? -1 : echelleIdentite(p),
           neg: separeNegations(c.tags).negatif,
           phrase: p.prompt };
}"""


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
        pg = br.new_page(viewport={"width": 360, "height": 780})
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        pg.set_default_timeout(60000)
        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_function("typeof promptFinal === 'function'")

        if args.muter:
            # MUTATION : on redonne a l'identite son ancien comportement (toujours
            # complete, quelle que soit l'echelle). Les cas A et B DOIVENT tomber.
            pg.evaluate("() => { window.filtreIdentite = (b) => b; }")

        n_fiches = pg.evaluate(JS_PREPARE, {"chars": [KIMIKO, JO], "style": STYLE})
        # Temoin positif : sans lui, un decor vide rend VERTS tous les cas qui
        # attendent une absence -- exactement ce qui est arrive au 1er jet.
        if not verifie("le décor du banc est monté (2 fiches visibles par la page)",
                       n_fiches == 2, "CHARS.length = %s" % n_fiches):
            print("\nARRET : le banc ne peut rien prouver sans son décor.")
            br.close()
            return 2

        for nom, tags, casting, absents, presents in CAS:
            r = pg.evaluate(JS_CAS, {"phrase": "phrase francaise de Quang, intacte",
                                     "tags": tags, "casting": casting,
                                     "chars": [KIMIKO, JO], "style": STYLE})
            final = r["final"].lower()
            manquants = [x for x in presents if x.lower() not in final]
            intrus = [x for x in absents if x.lower() in final]
            ok = not manquants and not intrus and r["fiches"] == 2
            detail = ""
            if intrus:
                detail += "présent alors qu'interdit : %s. " % ", ".join(intrus)
            if manquants:
                detail += "absent alors qu'attendu : %s." % ", ".join(manquants)
            verifie(nom, ok, detail or r["final"][:90])
            # G : la phrase n'est jamais touchee par la construction du prompt.
            verifie(nom + " (phrase intacte)",
                    r["phrase"] == "phrase francaise de Quang, intacte")

        # F : le style ne doit plus porter ses doublons.
        r = pg.evaluate(JS_CAS, {"phrase": "x", "tags": "wide shot", "casting": [],
                                 "chars": [KIMIKO, JO], "style": STYLE})
        n_mono = r["final"].lower().count("monochrome")
        n_scr = r["final"].lower().count("screentone")
        verifie("F-dedoublonnage du style", n_mono == 1 and n_scr == 1,
                "monochrome x%d, screentone x%d (le style en declare 2 de chaque)"
                % (n_mono, n_scr))

        # D : ce qui est nie doit se retrouver dans le negatif, pas nulle part.
        neg = pg.evaluate("() => separeNegations('close-up, no head, no face, toes').negatif")
        verifie("D-négations récupérées au négatif",
                "head" in neg and "face" in neg, "négatif = " + neg)
        # ... et `no humans` reste au POSITIF : c'est un vrai tag danbooru.
        pos = pg.evaluate("() => separeNegations('empty room, no humans').positif")
        verifie("D-`no humans` conservé au positif", "no humans" in pos, pos)

        verifie("aucune erreur JS", not erreurs, "; ".join(erreurs[:2]))
        br.close()

    ko = [n for n, ok in resultats if not ok]
    print("\n%d/%d" % (len(resultats) - len(ko), len(resultats)))
    if args.muter:
        # Le banc mute DOIT echouer. S'il passe, c'est LUI qui est casse.
        if ko:
            print("MUTATION : rouge comme attendu (%d cas tombent) — le banc mord." % len(ko))
            return 0
        print("MUTATION : VERTE = le banc ne teste rien. A reparer AVANT de croire ses OK.")
        return 1
    return 1 if ko else 0


if __name__ == "__main__":
    sys.exit(main())
