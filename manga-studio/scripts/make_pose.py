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
