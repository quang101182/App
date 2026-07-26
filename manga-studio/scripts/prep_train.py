# -*- coding: utf-8 -*-
"""Prepare l'arborescence kohya + les captions, puis affiche la commande d'entrainement.

Captions : on met le TRIGGER + ce qui VARIE (cadrage, expression, fond).
On ne decrit PAS ce qui est constant (coiffure, uniforme, ecarpe) : c'est
justement ce que le trigger doit absorber. Decrire un attribut constant
revient a apprendre au modele a le considerer comme detachable du personnage.
"""
import os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "dataset")
ROOT = os.path.join(HERE, "lora_train")
TRIGGER = "zqmg1rl"
REPEATS = 6
DST = os.path.join(ROOT, "img", "%d_%s" % (REPEATS, TRIGGER))

sys.path.insert(0, HERE)
from manga_dataset import VARI  # noqa: E402


def main():
    if os.path.isdir(ROOT):
        shutil.rmtree(ROOT)
    os.makedirs(DST)
    os.makedirs(os.path.join(ROOT, "out"))
    os.makedirs(os.path.join(ROOT, "log"))

    n = 0
    for i, (pose, bg) in enumerate(VARI):
        src = os.path.join(SRC, "ds_%02d.png" % i)
        if not os.path.isfile(src):
            continue
        shutil.copy2(src, os.path.join(DST, "ds_%02d.png" % i))
        cap = "%s, 1girl, solo, monochrome, greyscale, manga, %s, %s" % (TRIGGER, pose, bg)
        with open(os.path.join(DST, "ds_%02d.txt" % i), "w", encoding="utf-8") as f:
            f.write(cap)
        n += 1

    steps = n * REPEATS
    print("dataset : %d images x %d repeats = %d steps/epoch" % (n, REPEATS, steps))
    print("8 epochs = %d steps au total" % (steps * 8))
    print("trigger  : %s" % TRIGGER)
    print("dossier  : %s" % DST)
    return n


if __name__ == "__main__":
    main()
