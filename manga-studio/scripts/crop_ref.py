# -*- coding: utf-8 -*-
"""Recadre une image de reference sur le VISAGE — avant de la donner a IPAdapter.

Pourquoi ça existe (mesure du 28/07, sur les vraies fiches de Quang)
--------------------------------------------------------------------
IPAdapter PLUS ne transfere pas que l'identite : il transfere aussi la
COMPOSITION de l'image qu'on lui montre. Les references de Jo et de Kimiko sont
elles-memes des planches de personnage (plusieurs vues, fond vide) -- la case
generee heritait donc d'un grand visage flottant et d'echelles incoherentes,
meme apres nettoyage des tags.

La parade est celle que le banc `test_ipadapter.py` appliquait deja pour CHOISIR
sa reference : ce qui compte, c'est la part de l'image occupee par le visage. Ici
on ne se contente plus de choisir, on RECADRE — un portrait serre ne peut pas
imposer une mise en page a plusieurs vues, il n'en a pas.

Ce que ça fait, et ce que ça ne fait pas
----------------------------------------
- prend le PLUS GRAND visage (sur une planche de design, c'est le portrait
  principal -- pas la silhouette en pied, ou le visage fait 3 % de l'image) ;
- decoupe un CARRE centre sur lui, elargi pour prendre les cheveux et le haut du
  buste (c'est ce qui identifie un personnage de manga, pas le seul visage) ;
- ne touche NI a la couleur (la conversion N&B se fait cote client, ailleurs)
  NI au fichier d'origine.
- aucun visage trouve -> il le DIT et ne recadre rien. Un recadrage au hasard
  serait pire que pas de recadrage : on couperait le sujet sans le savoir.

Usage:
    python crop_ref.py <image> [--out fichier.png] [--taille 768] [--json]
"""
import argparse
import io
import json
import os
import sys

# ⚠ Le wrapper UTF-8 ne se pose QU'EN execution directe. Pose a l'import, il
# remplace le wrapper deja installe par le banc appelant, qui devient orphelin,
# est collecte, et FERME le flux commun : le banc mourait sur son premier print
# avec « I/O operation on closed file ». Un module importable ne touche pas au
# stdout de celui qui l'importe.
if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

FACE = r"C:\Users\quang\Documents\ComfyUI\models\ultralytics\bbox\face_yolov8m.pt"
# Combien de largeurs de visage on garde autour de lui. 3,2 a ete choisi pour
# tenir tete + cheveux + epaules : en dessous on coupe la coiffure (qui identifie
# un personnage de manga au moins autant que les traits), au-dessus on laisse
# revenir le fond et les autres vues de la planche.
LARGEUR_VISAGES = 3.2
# Le visage n'est pas au centre du cadre : on le place au tiers haut, comme un
# cadrage de portrait, pour que le buste entre sous lui.
HAUT = 0.34


def recadre(src, dest=None, taille=768, conf=0.35):
    from PIL import Image
    from ultralytics import YOLO
    if not os.path.isfile(FACE):
        return {"ok": False, "raison": "detecteur de visage absent : %s" % FACE}
    im = Image.open(src).convert("RGB")
    W, H = im.size
    r = YOLO(FACE).predict(src, conf=conf, verbose=False)[0]
    if not len(r.boxes):
        return {"ok": False, "raison": "aucun visage detecte", "w": W, "h": H}
    b = max(r.boxes, key=lambda b: (b.xyxy[0][2] - b.xyxy[0][0])
            * (b.xyxy[0][3] - b.xyxy[0][1]))
    x1, y1, x2, y2 = [float(t) for t in b.xyxy[0]]
    fw, fh = x2 - x1, y2 - y1
    part_avant = (fw * fh) / float(W * H)
    cote = max(fw * LARGEUR_VISAGES, fh * LARGEUR_VISAGES * 0.8)
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    gx = cx - cote / 2
    gy = cy - cote * HAUT
    # Bornage : on GLISSE le cadre dans l'image plutot que de le rogner, pour ne
    # pas rendre un rectangle alors qu'on a promis un carre. Si l'image est plus
    # petite que le cadre voulu, on reduit le cadre -- sans jamais sortir.
    # ⚠ On arrondit le COTE une bonne fois, puis on ne calcule plus qu'avec des
    # entiers. Une premiere version tronquait chaque coin separement
    # (`int(gx)`, `int(gx + cote)`) : le « carre » sortait en 369x370, et le banc
    # l'a vu. Un cadre carre doit l'etre par construction, pas par chance.
    cote = int(min(cote, W, H))
    gx = int(max(0, min(gx, W - cote)))
    gy = int(max(0, min(gy, H - cote)))
    crop = im.crop((gx, gy, gx + cote, gy + cote))
    part_apres = (fw * fh) / float(cote * cote)
    if taille and crop.width > taille:
        crop = crop.resize((taille, taille), Image.LANCZOS)
    if dest is None:
        base, ext = os.path.splitext(src)
        dest = base + "_crop" + (ext or ".png")
    crop.save(dest)
    return {"ok": True, "dest": dest, "source": [W, H],
            "visage_avant": round(part_avant, 4), "visage_apres": round(part_apres, 4),
            "cote": int(cote)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--out")
    ap.add_argument("--taille", type=int, default=768)
    ap.add_argument("--conf", type=float, default=0.35)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    res = recadre(a.image, a.out, a.taille, a.conf)
    if a.json:
        print(json.dumps(res, ensure_ascii=False))
    elif res["ok"]:
        print("recadre -> %s (visage : %.1f %% -> %.1f %% de l'image)"
              % (res["dest"], 100 * res["visage_avant"], 100 * res["visage_apres"]))
    else:
        print("PAS RECADRE : %s" % res["raison"])
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
