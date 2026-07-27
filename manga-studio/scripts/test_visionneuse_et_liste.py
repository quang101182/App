# -*- coding: utf-8 -*-
"""Voir en grand, naviguer, zoomer — et une liste de personnages qui tient.

Quang, 27/07 (capture a l'appui) : « ici c'est tout petit, je ne peux pas
agrandir, zoomer, dezoomer, donc je ne vois pas bien. Il faudrait pouvoir zoomer
et dezoomer, avec les boutons suivant et precedent pour aller plus vite, au lieu
de fermer a chaque image. A aucun moment il n'est indique que trois images seront
generees. Je pense aussi que la carte des personnages, si j'en cree beaucoup,
risque de devenir une liste abominable. »

Ce que le banc MESURE (et pas seulement « le bouton existe ») :

  - le zoom change la taille REELLE de l'image a l'ecran (rectangle mesure),
    et il est ANCRE sur le point vise -- un zoom centre eloigne du doigt ce
    qu'on voulait justement regarder de plus pres ;
  - le pan est BORNE : on ne peut pas pousser l'image hors du cadre et se
    retrouver devant un ecran noir (defaut deja identifie sur la visionneuse
    de planche) ;
  - suivant/precedent changent d'image SANS fermer, et chaque image repart a
    sa taille (un zoom herite desoriente) ;
  - la liste : N fiches = N lignes, une seule ouverte a la fois, et le filtre
    reduit vraiment. La hauteur totale est mesuree, parce que c'est ce que
    Quang appelle « abominable » -- pas un nombre d'elements.

Zero GPU : les vues sont posees a la main dans l'app (des images qui existent
deja suffisent a mesurer une visionneuse).

Usage:
    python test_visionneuse_et_liste.py [--headed]
    python test_visionneuse_et_liste.py --muter    # DOIT virer au rouge
"""
import argparse
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
APP_URL = "http://127.0.0.1:8190/manga"
NOM = "_vis_%d" % os.getpid()

cas = []


def verifie(nom, ok, detail=""):
    cas.append((nom, bool(ok), detail))
    print(("  OK   " if ok else "  ECHEC") + " " + nom + ((" — " + detail) if detail else ""),
          flush=True)
    return ok


# 8 fiches : de quoi voir si la liste tient. Une seule porte des vues.
PREPARE = """async ([nom]) => {
    const ids = [];
    for (let i = 0; i < 8; i++){
        const c = await api('/manga/chars', {name: nom + '-' + i,
            tags: (i === 3 ? 'old master, white beard' : 'girl, short hair'),
            role: i === 0 ? 'heros' : 'secondaire'});
        ids.push(c.id);
    }
    await loadChars();
    return ids;
}"""

# Trois fausses vues qui pointent vers une image REELLE et lisible : on mesure
# une visionneuse, pas un moteur.
# ⚠ `vueURL` est une `const` de module : `window.vueURL = ...` ne la remplace
# PAS (la resolution lexicale gagne — meme piege que `$`). On sert donc une
# vraie image par la ROUTE reseau, ce qui est de toute facon plus fidele.
POSER_VUES = """([id]) => {
    BROUILLONS[id] = ['visage','buste','en pied'].map((n, i) => ({
        cle: ['visage','buste','entier'][i], nom: n,
        img: {filename: '__banc__' + i + '.png', subfolder: '', type: 'output'}
    }));
    CH_OUVERT = id;
    renderChars();
}"""

RECT = "el => { const r = el.getBoundingClientRect(); return {x:r.x, y:r.y, w:r.width, h:r.height}; }"

def png_test():
    """Un vrai PNG 240x240, fabrique ici : une image cassee mesure 0 px et ferait
    accuser le zoom d'un defaut qui n'est pas le sien."""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (240, 240), (34, 34, 34))
    ImageDraw.Draw(im).ellipse((40, 40, 200, 200), fill=(238, 238, 238))
    b = io.BytesIO(); im.save(b, "PNG")
    return b.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--muter", action="store_true",
                    help="le zoom redevient centre et non borne : DOIT virer au rouge")
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright

    secret = open(SECRET_FILE, encoding="utf-8").read().strip()
    erreurs = []

    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=not args.headed, channel="msedge")
        pg = br.new_page(viewport={"width": 390, "height": 820},
                         is_mobile=True, has_touch=True)
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        corps = png_test()
        pg.route("**/comfy/view*", lambda r: r.fulfill(
            status=200, content_type="image/png", body=corps))
        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_timeout(3000)
        ids = pg.evaluate(PREPARE, [NOM])
        pg.click('nav button[data-tab="tPerso"]')
        pg.wait_for_timeout(1200)

        if args.muter:
            # MUTATION : zoom CENTRE et pan NON BORNE -- exactement les deux
            # defauts de la visionneuse de planche. L'image grossit tres bien,
            # elle part juste ailleurs que sous le doigt, et on peut la perdre.
            pg.evaluate("""() => {
                window.zoomBorner = () => {};
                window.zoomVers = (k2, px, py) => {
                    Z.k = Math.min(6, Math.max(1, k2));
                    zoomAppliquer();
                };
            }""")

        # ---------- 1. la liste : N fiches = N lignes ----------
        lignes = pg.eval_on_selector_all("[data-chopen]", "els => els.length")
        total = pg.evaluate("CHARS.length")
        verifie("chaque fiche tient sur UNE ligne", lignes == total,
                "%d ligne(s) pour %d fiche(s)" % (lignes, total))
        h = pg.eval_on_selector("#charList", "el => el.getBoundingClientRect().height")
        verifie("la liste repliee reste courte (< 70 px par fiche)",
                h < 70 * total, "%.0f px pour %d fiches" % (h, total))
        verifie("aucune fiche n'est ouverte au depart",
                pg.eval_on_selector_all("[data-chdraw]", "els => els.length") == 0)

        # ---------- 2. une seule fiche ouverte a la fois ----------
        pg.click('[data-chopen="%s"]' % ids[0])
        pg.wait_for_timeout(500)
        verifie("toucher une ligne l'ouvre",
                pg.eval_on_selector_all("[data-chdraw]", "els => els.length") == 1)
        pg.click('[data-chopen="%s"]' % ids[5])
        pg.wait_for_timeout(500)
        verifie("en ouvrir une autre referme la premiere",
                pg.eval_on_selector_all("[data-chdraw]", "els => els.length") == 1)

        # ---------- 3. le nombre d'images est annonce ----------
        txt = pg.eval_on_selector("[data-chdraw]", "el => el.textContent")
        verifie("le bouton annonce le nombre de vues", "3" in txt, txt.strip())

        # ---------- 4. le filtre reduit vraiment ----------
        pg.fill("#chFiltre", NOM + "-3")
        pg.wait_for_timeout(600)
        verifie("le filtre ne laisse qu'une fiche",
                pg.eval_on_selector_all("[data-chopen]", "els => els.length") == 1)
        verifie("le champ garde le focus (sinon on ne peut pas taper 2 lettres)",
                pg.evaluate("document.activeElement && document.activeElement.id") == "chFiltre")
        pg.fill("#chFiltre", "")
        pg.wait_for_timeout(600)

        # ---------- 5. la visionneuse : navigation SANS fermer ----------
        pg.evaluate(POSER_VUES, [ids[3]])
        pg.wait_for_timeout(600)
        pg.click('[data-chvue="%s"][data-i="1"]' % ids[3])
        pg.wait_for_timeout(700)
        verifie("toucher une vue l'ouvre en grand",
                pg.eval_on_selector("#lightbox", "el => !el.hidden") is True)
        nom1 = pg.eval_on_selector("#lbName", "el => el.textContent")
        verifie("elle s'ouvre sur la vue touchee (2/3)", "2/3" in nom1, nom1)
        pg.click("#lbNext")
        pg.wait_for_timeout(500)
        nom2 = pg.eval_on_selector("#lbName", "el => el.textContent")
        verifie("« suivant » change d'image SANS fermer",
                "3/3" in nom2 and pg.eval_on_selector("#lightbox", "el => !el.hidden"),
                nom2)
        pg.click("#lbPrev"); pg.click("#lbPrev")
        pg.wait_for_timeout(500)
        verifie("« precedent » revient en arriere",
                "1/3" in pg.eval_on_selector("#lbName", "el => el.textContent"))
        verifie("l'action de garde est proposee dans la visionneuse",
                pg.eval_on_selector("#lbAct", "el => !el.hidden && el.textContent")
                and "garder" in pg.eval_on_selector("#lbAct", "el => el.textContent"))

        # ---------- 6. LE ZOOM, mesure ----------
        # Une image pas encore chargee mesure 0 px : on l'attend, sinon le banc
        # accuse le zoom d'un defaut qui n'est pas le sien.
        pg.wait_for_function("() => { const i = document.getElementById('lbImg');"
                             " return i && i.naturalWidth > 0 && i.getBoundingClientRect().width > 10; }",
                             timeout=8000)
        av = pg.eval_on_selector("#lbImg", RECT)
        pg.click("#lbZoomP")
        pg.wait_for_timeout(400)
        ap_ = pg.eval_on_selector("#lbImg", RECT)
        verifie("zoomer AGRANDIT vraiment l'image",
                ap_["w"] > av["w"] * 1.3, "%.0f px -> %.0f px" % (av["w"], ap_["w"]))
        pg.click("#lbZoom")          # retour 1:1
        pg.wait_for_timeout(400)
        r0 = pg.eval_on_selector("#lbImg", RECT)
        verifie("« 1:1 » redonne la taille d'origine",
                abs(r0["w"] - av["w"]) < 2, "%.0f px" % r0["w"])

        # zoom ANCRE : on vise le coin haut-gauche de l'image ; il doit y rester.
        cible = {"x": r0["x"] + 12, "y": r0["y"] + 12}
        pg.evaluate("([x, y]) => zoomVers(3, x, y)", [cible["x"], cible["y"]])
        pg.wait_for_timeout(400)
        r1 = pg.eval_on_selector("#lbImg", RECT)
        # ⚠ TOLERANCE SERREE, et c'est la mutation qui l'a impose : a 25 px,
        # un zoom CENTRE passait encore (il derape ici de 24 px). Un seuil
        # confortable ne mesure plus rien -- c'est le piege deja paye sur ce
        # projet. 8 px absorbe les arrondis, pas une erreur de formule.
        verifie("le zoom est ANCRE sur le point vise (pas sur le centre)",
                abs(r1["x"] - (cible["x"] - 12 * 3)) < 8,
                "coin attendu %.0f, obtenu %.0f" % (cible["x"] - 12 * 3, r1["x"]))

        # pan BORNE : on pousse tres loin, l'image doit rester visible
        pg.evaluate("() => { Z.tx = -99999; Z.ty = -99999; zoomBorner(); zoomAppliquer(); }")
        pg.wait_for_timeout(300)
        r2 = pg.eval_on_selector("#lbImg", RECT)
        cadre = pg.eval_on_selector("#lbWrap", RECT)
        visible = (r2["x"] + r2["w"] > cadre["x"] + 20) and (r2["x"] < cadre["x"] + cadre["w"] - 20)
        verifie("le pan est BORNE : l'image ne peut pas sortir du cadre",
                visible, "image x=%.0f..%.0f, cadre x=%.0f..%.0f"
                % (r2["x"], r2["x"] + r2["w"], cadre["x"], cadre["x"] + cadre["w"]))

        # ---------- 7. chaque image repart a sa taille ----------
        pg.evaluate("() => zoomVers(3, null, null)")
        pg.wait_for_timeout(300)
        pg.click("#lbNext")
        pg.wait_for_timeout(500)
        verifie("changer d'image remet le zoom a 1:1",
                abs(pg.evaluate("Z.k") - 1) < 0.01, "k=%s" % pg.evaluate("Z.k"))

        pg.click("#lbClose")
        pg.wait_for_timeout(300)
        verifie("fermer ferme", pg.eval_on_selector("#lightbox", "el => el.hidden") is True)

        for cid in ids:
            try:
                pg.evaluate("(id) => api('/manga/chars', {delete: id})", cid)
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
