# -*- coding: utf-8 -*-
"""La galerie est-elle UTILISABLE ? (demande Quang, 27/07)

« J'ai une galerie, mais je ne peux rien faire dessus. » — elle affichait des
vignettes, et c'est tout : pas d'agrandissement, pas de selection, pas de
suppression.

Ce banc verifie les trois gestes, sur un telephone (360 px), en pilotant l'app
comme un utilisateur. Il travaille sur des images JETABLES qu'il cree lui-meme
dans le projet de test : un banc de suppression ne doit jamais pouvoir effacer
le travail de Quang, meme en cas de bug.

Usage:
    python test_galerie_live.py [--headed]
"""
import argparse
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
APP_URL = "http://127.0.0.1:8190/manga"
PROJ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SLUG = "_test_galerie"
LARGEUR, HAUTEUR = 360, 780
N = 4


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    args = ap.parse_args()
    from PIL import Image, ImageDraw
    from playwright.sync_api import sync_playwright

    dossier = os.path.join(PROJ, "output", SLUG)
    os.makedirs(dossier, exist_ok=True)
    for i in range(N):
        im = Image.new("RGB", (300, 420), "white")
        ImageDraw.Draw(im).text((10, 10), "jetable %d" % i, fill="black")
        im.save(os.path.join(dossier, "jetable_%d.png" % i))
    print("images jetables ecrites : %d dans output/%s/" % (N, SLUG))

    secret = open(SECRET_FILE, encoding="utf-8").read().strip()
    erreurs, res = [], {}
    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=not args.headed, channel="msedge")
        pg = br.new_page(viewport={"width": LARGEUR, "height": HAUTEUR},
                         has_touch=True, is_mobile=True)
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)

        # On fixe le slug directement : creer un projet ne suffisait pas, le
        # backend RE-SLUGIFIE le nom (« _test_galerie » devenait autre chose) et
        # la galerie lisait donc un dossier vide. La galerie ne depend que du slug.
        pg.evaluate("""(slug) => { S.proj = { slug: slug, name: slug }; }""", SLUG)
        # On CLIQUE l'onglet, on ne se contente pas d'appeler refreshGal() : sinon
        # la section reste masquee et rien n'est cliquable. Un banc qui remplit un
        # DOM invisible teste des donnees, pas une interface.
        pg.click('button[data-tab="tGal"]')
        pg.wait_for_timeout(1500)

        res["vignettes"] = pg.evaluate("() => document.querySelectorAll('#gal figure').length")
        print("vignettes affichees                : %d/%d" % (res["vignettes"], N))

        # 1. plein ecran
        pg.click("#gal figure:first-child img")
        pg.wait_for_timeout(500)
        res["lb_ouvert"] = pg.evaluate("() => !document.getElementById('lightbox').hidden")
        # L'image doit VRAIMENT etre plus grande qu'une vignette, sinon
        # « plein ecran » n'est qu'un mot : on mesure, on ne suppose pas.
        res["lb_large"] = pg.evaluate("""() => {
            const v = document.querySelector('#gal figure img').getBoundingClientRect();
            const g = document.getElementById('lbImg').getBoundingClientRect();
            return g.width > v.width * 1.5;
        }""")
        nom1 = pg.inner_text("#lbName")
        pg.click("#lbNext")
        pg.wait_for_timeout(400)
        res["lb_suivant"] = pg.inner_text("#lbName") != nom1
        pg.click("#lbClose")
        pg.wait_for_timeout(300)
        res["lb_ferme"] = pg.evaluate("() => document.getElementById('lightbox').hidden")
        print("plein ecran : ouvre %s · plus grand %s · suivant %s · ferme %s"
              % (res["lb_ouvert"], res["lb_large"], res["lb_suivant"], res["lb_ferme"]))

        # 2. selection multiple
        pg.check("#gal figure:nth-child(1) [data-pick]")
        pg.check("#gal figure:nth-child(2) [data-pick]")
        pg.wait_for_timeout(300)
        res["btn_txt"] = pg.inner_text("#btnGalDel")
        res["sel_visible"] = pg.evaluate(
            "() => document.querySelectorAll('#gal figure.sel').length")
        print("selection : bouton = %r · %d vignette(s) marquee(s)"
              % (res["btn_txt"], res["sel_visible"]))

        # cocher ne doit PAS ouvrir le plein ecran (piege classique du clic imbrique)
        res["pas_de_lb"] = pg.evaluate("() => document.getElementById('lightbox').hidden")
        print("cocher n'ouvre pas le plein ecran  : %s" % res["pas_de_lb"])

        # 3. suppression (la boite de confirmation est acceptee, comme le ferait Quang)
        pg.on("dialog", lambda d: d.accept())
        pg.click("#btnGalDel")
        pg.wait_for_timeout(1800)
        res["restantes_ui"] = pg.evaluate("() => document.querySelectorAll('#gal figure').length")
        br.close()

    restantes_disque = len([f for f in os.listdir(dossier) if f.endswith(".png")])
    print("apres suppression : %d vignette(s) a l'ecran, %d fichier(s) sur le DISQUE"
          % (res["restantes_ui"], restantes_disque))
    print("erreurs JS : %d" % len(erreurs))

    # Le disque fait foi : une UI qui retire la vignette sans effacer le fichier
    # serait un faux vert -- exactement le defaut deja paye sur le rangement des cases.
    vert = (res["vignettes"] == N and res["lb_ouvert"] and res["lb_large"]
            and res["lb_suivant"] and res["lb_ferme"] and res["sel_visible"] == 2
            and res["pas_de_lb"] and res["restantes_ui"] == N - 2
            and restantes_disque == N - 2 and not erreurs)
    print("\nVERDICT : %s" % ("VERT — agrandir, selectionner, supprimer : les trois marchent."
                              if vert else "ROUGE — voir les lignes ci-dessus."))
    for f in os.listdir(dossier):
        os.remove(os.path.join(dossier, f))
    os.rmdir(dossier)
    return 0 if vert else 1


if __name__ == "__main__":
    sys.exit(main())
