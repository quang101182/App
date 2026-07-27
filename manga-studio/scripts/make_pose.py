# -*- coding: utf-8 -*-
"""Fabrique des squelettes OpenPose SYNTHETIQUES, pour imposer un cadrage.

Pourquoi synthetiser plutot qu'extraire d'une image : une pose extraite herite du
cadrage de l'image dont elle vient. Or c'est precisement le cadrage qu'on cherche
a changer -- mesure du 27/07 : ni le dataset ni les prompts n'obtiennent un vrai
plan en pied, le modele de base resiste.

Ici, la position et l'echelle du squelette dans la toile SONT le cadrage :
un corps entier de la tete aux pieds occupe la hauteur => plan en pied, forcement.
C'est deterministe, gratuit, et ca ne depend d'aucun modele.

Format : COCO-18, la convention que le ControlNet openpose attend.
  0 nez · 1 cou · 2-4 bras D · 5-7 bras G · 8-10 jambe D · 11-13 jambe G
  14-15 yeux · 16-17 oreilles

Usage:
    python make_pose.py                 # ecrit les 4 cadrages dans poses/
    python make_pose.py --show          # + une planche contact
"""
import argparse
import io
import math
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "poses")
W, H = 832, 1216

# Palette OpenPose canonique. Le ControlNet a ete entraine dessus : changer les
# couleurs, c'est lui parler une autre langue.
LIMBS = [(1, 2), (1, 5), (2, 3), (3, 4), (5, 6), (6, 7), (1, 8), (8, 9), (9, 10),
         (1, 11), (11, 12), (12, 13), (1, 0), (0, 14), (14, 16), (0, 15), (15, 17)]
LIMB_COL = [(255, 0, 0), (255, 85, 0), (255, 170, 0), (255, 255, 0), (170, 255, 0),
            (85, 255, 0), (0, 255, 0), (0, 255, 85), (0, 255, 170), (0, 255, 255),
            (0, 170, 255), (0, 85, 255), (0, 0, 255), (85, 0, 255), (170, 0, 255),
            (255, 0, 255), (255, 0, 170)]
PT_COL = [(255, 0, 0), (255, 85, 0), (255, 170, 0), (255, 255, 0), (170, 255, 0),
          (85, 255, 0), (0, 255, 0), (0, 255, 85), (0, 255, 170), (0, 255, 255),
          (0, 170, 255), (0, 85, 255), (0, 0, 255), (85, 0, 255), (170, 0, 255),
          (255, 0, 255), (255, 0, 170), (255, 0, 85)]

# Corps de reference, en unites relatives : x centre sur 0, y de 0 (sommet du
# crane) a 1 (plante des pieds). Proportions ~7,5 tetes, silhouette debout.
CORPS = {
    0:  (0.000, 0.075),   # nez
    1:  (0.000, 0.150),   # cou
    2:  (-0.075, 0.165), 3: (-0.115, 0.290), 4: (-0.130, 0.410),   # bras droit
    5:  (0.075, 0.165),  6: (0.115, 0.290),  7: (0.130, 0.410),    # bras gauche
    8:  (-0.050, 0.500), 9: (-0.055, 0.730), 10: (-0.058, 0.960),  # jambe droite
    11: (0.050, 0.500), 12: (0.055, 0.730), 13: (0.058, 0.960),    # jambe gauche
    14: (-0.022, 0.062), 15: (0.022, 0.062),                        # yeux
    16: (-0.048, 0.070), 17: (0.048, 0.070),                        # oreilles
}

# Corps AGENOUILLE, meme convention : y de 0 (crane) a 1 (genou pose au sol).
# Ajoute le 27/07 apres une mesure sans appel : demande en TEXTE (« the man kneels
# at her feet »), le modele produit la femme debout et OUBLIE l'homme -- 0/3. Ce
# qui casse une scene de domination n'est pas l'anatomie, c'est le rapport de
# force, et un rapport de force est une GEOMETRIE : qui est haut, qui est bas.
# Un squelette le dit sans ambiguite la ou une phrase echoue.
CORPS_GENOUX = {
    0:  (0.000, 0.100),   # nez
    1:  (0.000, 0.210),   # cou
    2:  (-0.100, 0.230), 3: (-0.150, 0.420), 4: (-0.160, 0.600),   # bras droit
    5:  (0.100, 0.230),  6: (0.150, 0.420),  7: (0.160, 0.600),    # bras gauche
    # Cuisse VERTICALE (hanche au-dessus du genou) puis tibia HORIZONTAL vers
    # l'arriere, cheville au sol a la meme hauteur que le genou. Premiere version
    # ratee : la cheville etait a peine decalee, et le squelette ressemblait a un
    # petit personnage DEBOUT -- ce que le ControlNet aurait fidelement reproduit.
    8:  (-0.070, 0.680), 9: (-0.075, 1.000), 10: (-0.300, 1.005),  # jambe D repliee
    11: (0.070, 0.680), 12: (0.075, 1.000), 13: (0.290, 1.005),    # jambe G repliee
    14: (-0.028, 0.085), 15: (0.028, 0.085),
    16: (-0.060, 0.095), 17: (0.060, 0.095),
}

# Une SCENE a deux corps. Chaque acteur : (corps, x_centre, y_haut, y_bas) en
# fractions de la toile. La hauteur occupee EST le rapport de force : celle qui
# domine tient toute la hauteur, celui qui est soumis en occupe la moitie basse.
SCENES_DUO = {
    "femdom_debout_genoux": [
        (CORPS, 0.63, 0.030, 0.985),   # elle, debout, pleine hauteur
        (CORPS_GENOUX, 0.28, 0.420, 0.985),   # lui, a genoux (~0,6x sa taille debout)
    ],
    "femdom_contre_plongee": [
        # Meme rapport, cadre plus serre : elle deborde par le haut (contre-plongee),
        # il occupe le tiers bas. Le hors-champ fait partie de la mise en scene.
        (CORPS, 0.58, -0.120, 0.900),
        (CORPS_GENOUX, 0.28, 0.560, 0.985),
    ],
    "duo_debout": [
        # Temoin : deux corps debout, aucun rapport de force. Sert a distinguer
        # « le ControlNet fait apparaitre 2 personnes » de « il impose une posture ».
        (CORPS, 0.34, 0.040, 0.985),
        (CORPS, 0.66, 0.040, 0.985),
    ],
}


# Un cadrage, c'est : quelle PART du corps est visible, et quelle hauteur elle
# occupe dans la toile. Rien d'autre.
CADRAGES = {
    #  nom          y_haut  y_bas   (portion du corps visible, 0=crane 1=pieds)
    "fullbody":    (0.00, 1.00),
    "cowboy":      (0.00, 0.62),    # jusqu'a mi-cuisse
    "upperbody":   (0.00, 0.44),    # jusqu'a la taille
    "closeup":     (0.00, 0.17),    # tete et cou
}


def squelette(y_haut, y_bas, marge=0.04, decal_x=0.0):
    """Place le corps pour que la portion [y_haut, y_bas] remplisse la toile."""
    span = max(1e-3, y_bas - y_haut)
    ech = (1.0 - 2 * marge) / span            # facteur d'echelle vertical
    pts = {}
    for i, (x, y) in CORPS.items():
        px = (0.5 + decal_x + x * ech * (H / float(W))) * W
        py = (marge + (y - y_haut) * ech) * H
        pts[i] = (px, py)
    return pts


def placer(corps, cx, y_haut, y_bas):
    """Place un corps ENTIER entre deux hauteurs de la toile, centre sur cx.

    Contrairement a squelette(), qui recadre sur une PORTION du corps, ici on
    pose un personnage complet a une place et une taille voulues : c'est ce qu'il
    faut pour composer une scene a plusieurs acteurs.
    """
    ech = (y_bas - y_haut)
    pts = {}
    for i, (x, y) in corps.items():
        pts[i] = ((cx + x * ech * (H / float(W))) * W, (y_haut + y * ech) * H)
    return pts


def dessine_pts(groupes):
    """Dessine un ou plusieurs squelettes sur la MEME toile."""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(im)
    ep = max(4, int(H * 0.010))
    r = max(4, int(H * 0.007))
    for pts in groupes:
        visible = {i for i, (x, y) in pts.items() if -20 <= y <= H + 20}
        for (a, b), col in zip(LIMBS, LIMB_COL):
            if a in visible and b in visible:
                d.line([pts[a], pts[b]], fill=col, width=ep)
        for i in sorted(visible):
            x, y = pts[i]
            d.ellipse([x - r, y - r, x + r, y + r], fill=PT_COL[i])
    return im


def dessine(pts, y_bas):
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(im)
    # Un point sous le bas du cadre n'existe pas pour le modele : on le coupe,
    # sinon le squelette « deborde » et le ControlNet tire vers un plan plus large.
    visible = {i for i, (x, y) in pts.items() if -20 <= y <= H + 20}
    ep = max(4, int(H * 0.010))
    for (a, b), col in zip(LIMBS, LIMB_COL):
        if a in visible and b in visible:
            d.line([pts[a], pts[b]], fill=col, width=ep)
    r = max(4, int(H * 0.007))
    for i in sorted(visible):
        x, y = pts[i]
        d.ellipse([x - r, y - r, x + r, y + r], fill=PT_COL[i])
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", action="store_true")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    faits = []
    for nom, (yh, yb) in CADRAGES.items():
        im = dessine(squelette(yh, yb), yb)
        p = os.path.join(OUT, "pose_%s.png" % nom)
        im.save(p)
        faits.append(p)
        print("  %-11s -> %s" % (nom, os.path.basename(p)))
    for nom, acteurs in SCENES_DUO.items():
        im = dessine_pts([placer(c, cx, yh, yb) for c, cx, yh, yb in acteurs])
        p = os.path.join(OUT, "duo_%s.png" % nom)
        im.save(p)
        faits.append(p)
        print("  %-22s -> %s (%d acteurs)"
              % (nom, os.path.basename(p), len(acteurs)))
    if a.show:
        from PIL import Image
        n = len(faits)
        sheet = Image.new("RGB", (n * 220, 322), (20, 20, 20))
        for i, p in enumerate(faits):
            t = Image.open(p); t.thumbnail((220, 322)); sheet.paste(t, (i * 220, 0))
        sp = os.path.join(OUT, "_planche.png")
        sheet.save(sp)
        print("planche : %s" % sp)
    return 0


if __name__ == "__main__":
    sys.exit(main())
