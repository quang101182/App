# -*- coding: utf-8 -*-
"""Une case tient-elle dans un ecran de telephone ? (probleme signale le 27/07)

Quang : « la hauteur de l'ensemble fait que je n'arrive pas a voir, au moment ou
je clique en bas, la coche en haut a droite […] je dois defiler pour voir l'image
puis le bas avec les boutons. »

Mesure AVANT correctif, a 360x780 :
    une case = 726 px (0,9 ecran), et il fallait 708 px visibles pour voir a la
    fois le badge de verdict (en haut de l'image) et le bouton qui le pose (tout
    en bas). Impossible.

Deux correctifs, mesures ici :
  1. sur telephone, l'image est bornee en hauteur -- SANS toucher a son ratio,
     car les bulles sont posees en fractions de la case : casser le ratio les
     aurait decalees du dessin ;
  2. le verdict s'affiche AUSSI sur le bouton touche, donc le retour d'action
     arrive la ou est le doigt, sans avoir a remonter.

Le banc verifie les deux, et le second compte plus que le premier : meme si une
case devenait trop haute un jour, un retour local reste lisible.

Usage:
    python test_ergonomie_case.py [--headed]
"""
import argparse
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
APP_URL = "http://127.0.0.1:8190/manga"
LARGEUR, HAUTEUR = 360, 780      # le telephone de Quang
NOM = "_ergo_%d" % os.getpid()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--muter", action="store_true",
                    help="annule les regles mobiles : le banc DOIT virer au rouge")
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
        pg.evaluate("""async (nom) => {
            const proj = await api('/manga/projects', {name: nom});
            const p = await api('/manga/pages', {project_id: proj.id, title:'e', chapter:1});
            // Une VRAIE image : mesurer une case vide donnait 51 px de haut (le
            // placeholder) et un vert imperiteux -- le probleme de Quang vient
            // justement d'une case AVEC son image.
            const pan = await api('/manga/panels',
                {page_id: p.id, kind:'dialogue', prompt:'test', idx:0,
                 file: '_demo/1_planche_pc.png'});
            S.proj = {id: proj.id, slug: nom};
            S.page = {id: p.id, layout:{cols:2}};
            S.panels = [{id: pan.id, page_id: p.id, kind:'dialogue', prompt:'test',
                         file: '_demo/1_planche_pc.png', bubbles: [], recipe: {}}];
            renderPlate();
        }""", NOM)
        if args.muter:
            # On remet l'etat d'avant : image pleine largeur, editeur non compacte,
            # champ de prompt visible pendant le lettrage.
            pg.add_style_tag(content="@media (max-width:700px){"
                             " .panel .img{max-width:100%!important}"
                             " .bubed{padding:8px!important;gap:6px!important}"
                             " .bubed textarea{min-height:56px!important}"
                             " .panel.lettering [data-prompt]{display:block!important}}")
            print("MUTATION ACTIVE : les regles mobiles sont annulees.")
        pg.wait_for_timeout(2000)

        m = pg.evaluate("""() => {
            const pan = document.querySelector('.panel');
            const R = e => { const b = e.getBoundingClientRect();
                             return {h: Math.round(b.height), top: Math.round(b.top),
                                     bot: Math.round(b.bottom)}; };
            return {vp: innerHeight,
                    panel: R(pan), img: R(pan.querySelector('.img')),
                    ok: R(pan.querySelector('[data-act=ok]')),
                    badge: R(pan.querySelector('.verdict'))};
        }""")
        hauteur = m["panel"]["h"]
        besoin = m["ok"]["bot"] - m["badge"]["top"]
        print("hauteur d'une case      : %d px  (%.2f ecran)" % (hauteur, hauteur / m["vp"]))
        print("  dont image            : %d px" % m["img"]["h"])
        if m["img"]["h"] < 120:
            print("ARRET : l'image ne s'est pas affichee (%d px) -> le banc mesurerait"
                  " un placeholder et rendrait un vert sans valeur." % m["img"]["h"])
            br.close()
            return 2
        print("visible requis pour voir la coche ET le bouton : %d px (ecran %d)"
              % (besoin, m["vp"]))

        # LE CAS QUI FAIT MAL, celui que Quang decrit : l'editeur de bulle ouvert.
        # Il ajoute une zone de texte, une rangee de reglages et la barre de bulles
        # SOUS l'image. C'est la que la case devenait ingerable.
        pg.click('.panel [data-act="letter"]')
        pg.wait_for_timeout(400)
        pg.click('.panel [data-act="addbub"]')
        pg.wait_for_timeout(800)
        h2 = pg.evaluate("""() => Math.round(
            document.querySelector('.panel').getBoundingClientRect().height)""")
        print("hauteur AVEC l'editeur de bulle ouvert : %d px  (%.2f ecran)"
              % (h2, h2 / m["vp"]))

        # LE critere, celui de l'utilisateur -- et non un pourcentage invente :
        # la case amenee en haut de l'ecran, voit-on l'IMAGE et le BOUTON ensemble ?
        # C'est exactement le geste decrit (« je clique en bas, je ne vois pas la
        # coche en haut »). Un seuil arbitraire aurait declare rouge a 1 px pres.
        ensemble = pg.evaluate("""() => {
            const pan = document.querySelector('.panel');
            pan.scrollIntoView({block:'start'});
            const img = pan.querySelector('.img').getBoundingClientRect();
            const ok  = pan.querySelector('[data-act=ok]').getBoundingClientRect();
            return {img_visible: img.top >= 0 && img.bottom <= innerHeight,
                    bouton_visible: ok.bottom <= innerHeight && ok.top >= 0,
                    manque: Math.max(0, Math.round(ok.bottom - innerHeight))};
        }""")
        print("case en haut de l'ecran -> image visible %s, bouton visible %s%s"
              % (ensemble["img_visible"], ensemble["bouton_visible"],
                 "" if not ensemble["manque"]
                 else " (il manque %d px)" % ensemble["manque"]))

        # Le retour local : on touche le bouton, il doit CHANGER visiblement.
        pg.click('.panel [data-act="ok"]')
        pg.wait_for_timeout(600)
        etat = pg.evaluate("""() => {
            const b = document.querySelector('.panel [data-act=ok]');
            const c = getComputedStyle(b);
            return {classe: b.classList.contains('on'), fond: c.backgroundColor,
                    badge: document.querySelector('.panel .verdict').textContent};
        }""")
        pg.click('.panel [data-act="ok"]')
        pg.wait_for_timeout(600)
        apres2 = pg.evaluate("""() => ({
            classe: document.querySelector('.panel [data-act=ok]').classList.contains('on'),
            badge: document.querySelector('.panel .verdict').textContent})""")
        print("apres 1 clic  : bouton en surbrillance %s · badge %r"
              % (etat["classe"], etat["badge"]))
        print("apres 2 clics : bouton en surbrillance %s · badge %r (l'annulation est voulue)"
              % (apres2["classe"], apres2["badge"]))

        pg.evaluate("""async () => { const l = await api('/manga/projects');
            for (const p of (l.items || []))
                if (p.name && p.name.startsWith('_ergo_'))
                    await api('/manga/projects', {delete: p.id}); }""")
        br.close()

    print("erreurs JS : %d" % len(erreurs))
    # Les DEUX etats comptent : la case au repos et la case en cours de lettrage.
    # Ne mesurer que la premiere aurait laisse passer exactement le cas signale.
    tient = ensemble["img_visible"] and ensemble["bouton_visible"]
    local = etat["classe"] and etat["badge"] == "✅" and not apres2["classe"]
    print("\ncase sous 75 %% de l'ecran        : %s" % ("OUI" if tient else "NON"))
    print("retour d'action LA OU EST LE DOIGT: %s" % ("OUI" if local else "NON"))
    vert = tient and local and not erreurs
    print("\nVERDICT : %s" % ("VERT — la case tient a l'ecran et le verdict se voit"
                              " sans remonter." if vert else
                              "ROUGE — voir les lignes ci-dessus."))
    if args.muter:
        print("(mutation active : ce ROUGE est le resultat ATTENDU, il prouve le banc)")
        return 0 if not vert else 1
    return 0 if vert else 1


if __name__ == "__main__":
    sys.exit(main())
