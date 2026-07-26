# -*- coding: utf-8 -*-
"""Prepare l'arborescence kohya + les captions, puis affiche la commande d'entrainement.

Captions : on met le TRIGGER + ce qui VARIE (cadrage, expression, fond).
On ne decrit PAS ce qui est constant (coiffure, uniforme, ecarpe) : c'est
justement ce que le trigger doit absorber. Decrire un attribut constant
revient a apprendre au modele a le considerer comme detachable du personnage.
"""
import argparse, io, os, shutil, sys

# Sortie forcee en UTF-8 : les autres scripts du projet le font, celui-ci ne le
# faisait pas -- et il ecrit des chemins qui peuvent contenir des accents.
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "lora_train")


def depuis_vari(dst, trigger):
    """Dataset v1 : les captions sont RECONSTRUITES depuis la table des variations."""
    sys.path.insert(0, HERE)
    from manga_dataset import VARI  # noqa: E402
    # Le dataset est a la RACINE du projet, pas dans scripts/. Le chemin etait
    # reste `HERE/dataset` apres le rangement des scripts dans scripts/ :
    # prep_train.py ne trouvait plus rien, en silence, depuis ce jour-la.
    src_dir = os.path.join(HERE, "..", "dataset")
    n = 0
    for i, (pose, bg) in enumerate(VARI):
        src = os.path.join(src_dir, "ds_%02d.png" % i)
        if not os.path.isfile(src):
            continue
        shutil.copy2(src, os.path.join(dst, "ds_%02d.png" % i))
        cap = "%s, 1girl, solo, monochrome, greyscale, manga, %s, %s" % (trigger, pose, bg)
        with open(os.path.join(dst, "ds_%02d.txt" % i), "w", encoding="utf-8") as f:
            f.write(cap)
        n += 1
    return n


def depuis_dossier(src_dir, dst):
    """Dataset deja constitue (paires image + .txt) — c'est ce que produit la
    boucle de validation de l'app : les cases jugees bonnes, avec leur caption."""
    n = 0
    for f in sorted(os.listdir(src_dir)):
        base, ext = os.path.splitext(f)
        if ext.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
            continue
        cap = os.path.join(src_dir, base + ".txt")
        if not os.path.isfile(cap):
            print("  (ignoree, pas de caption) %s" % f)
            continue
        shutil.copy2(os.path.join(src_dir, f), os.path.join(dst, "ds_%02d%s" % (n, ext)))
        shutil.copy2(cap, os.path.join(dst, "ds_%02d.txt" % n))
        n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="", help="dossier de dataset (defaut : le dataset v1)")
    ap.add_argument("--trigger", default="zqmg1rl")
    ap.add_argument("--repeats", type=int, default=6)
    a = ap.parse_args()

    dst = os.path.join(ROOT, "img", "%d_%s" % (a.repeats, a.trigger))
    if os.path.isdir(ROOT):
        shutil.rmtree(ROOT)
    os.makedirs(dst)
    os.makedirs(os.path.join(ROOT, "out"))
    os.makedirs(os.path.join(ROOT, "log"))

    n = depuis_dossier(a.src, dst) if a.src else depuis_vari(dst, a.trigger)
    if not n:
        print("AUCUNE image : rien a entrainer.")
        return 0

    steps = n * a.repeats
    print("dataset : %d images x %d repeats = %d steps/epoch" % (n, a.repeats, steps))
    print("8 epochs = %d steps au total" % (steps * 8))
    print("trigger  : %s" % a.trigger)
    print("dossier  : %s" % dst)
    if n < 20:
        # Message en ASCII pur : un seul caractere non-ASCII fait planter ce script
        # sur une console Windows cp1252, et le banc qui lit sa sortie conclut alors
        # a un echec d'entrainement qui n'a jamais eu lieu.
        print("\nATTENTION : %d images seulement. En dessous de ~20-30, un LoRA de"
              " personnage apprend surtout le bruit du dataset." % n)
    return n


if __name__ == "__main__":
    main()
