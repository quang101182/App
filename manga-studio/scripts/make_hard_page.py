# -*- coding: utf-8 -*-
"""Fabrique une planche IRREGULIERE avec VERITE TERRAIN connue, pour mesurer
honnetement la detection de cases.

Pourquoi : la planche generee par SDXL etait une grille 2x4 parfaite. Pixtral
l'a "trouvee" -- mais il aurait pu la deviner sans rien regarder. Un test qu'on
ne peut pas rater ne mesure rien.

Ici : cases de tailles differentes, une case penchee, une case SANS BORDURE
(qui deborde), une case qui saigne au bord de page. On connait les boites
exactes -> on peut calculer l'IoU au lieu de juger a l'oeil.
"""
import json, os, random
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = [os.path.join(HERE, "scene_out", f + ".png") for f in
       ["cn055_c1_entre", "cn055_c2_assise", "cn055_c3_fenetre",
        "cn055_c4_tableau", "cn055_c5_couloir_fond", "cn055_c6_accoudee"]]
W, H = 1000, 1414          # ratio A4
G = 14                     # gouttiere
OUT = os.path.join(HERE, "manga_out")

# (x, y, w, h, style) en pixels — la verite terrain.
LAYOUT = [
    (G,        G,        W - 2 * G,      380, "border"),       # 1 bandeau large
    (G,        410,      430,            360, "border"),       # 2
    (470,      410,      W - 470 - G,    360, "tilt"),         # 3 penchee
    (G,        790,      W - 2 * G,      300, "borderless"),   # 4 sans bordure
    (G,        1110,     480,            W and 290,            "border"),  # 5
    (520,      1110,     W - 520 - G,    290, "bleed"),        # 6 saigne a droite
]


def main():
    page = Image.new("RGB", (W, H), "white")
    dr = ImageDraw.Draw(page)
    truth = []
    for i, (x, y, w, h, style) in enumerate(LAYOUT):
        src = Image.open(SRC[i % len(SRC)]).convert("RGB")
        # recadrage centre pour remplir la case
        r = max(w / src.width, h / src.height)
        src = src.resize((int(src.width * r) + 1, int(src.height * r) + 1), Image.LANCZOS)
        left = (src.width - w) // 2
        top = (src.height - h) // 3
        crop = src.crop((left, top, left + w, top + h))
        if style == "tilt":
            crop = crop.rotate(-4, expand=False, fillcolor=(255, 255, 255))
        if style == "bleed":
            w = W - x  # deborde jusqu'au bord de page
            crop = crop.crop((0, 0, min(w, crop.width), h))
        page.paste(crop, (x, y))
        if style in ("border", "tilt", "bleed"):
            dr.rectangle([x, y, x + crop.width - 1, y + h - 1], outline="black", width=4)
        truth.append({"id": i + 1, "x": x / W, "y": y / H,
                      "w": crop.width / W, "h": h / H, "style": style})
    dest = os.path.join(OUT, "page_hard.png")
    page.save(dest)
    with open(os.path.join(OUT, "page_hard_truth.json"), "w", encoding="utf-8") as f:
        json.dump({"panels": truth}, f, indent=1)
    print("planche irreguliere -> %s (%dx%d), %d cases" % (dest, W, H, len(truth)))
    for t in truth:
        print("  %d %-11s x=%.3f y=%.3f w=%.3f h=%.3f" % (t["id"], t["style"], t["x"], t["y"], t["w"], t["h"]))


if __name__ == "__main__":
    main()
