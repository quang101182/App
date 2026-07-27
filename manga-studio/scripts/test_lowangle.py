# -*- coding: utf-8 -*-
"""Qu'est-ce qui cassait vraiment la scene de domination ?

Le 27/07 (test_duo.py, n3), la scene femdom sortait sans l'homme a genoux : 0/3.
J'en ai conclu que « le rapport de force ne passe pas par le texte » et j'ai
construit des squelettes openpose a deux corps pour l'imposer.

Or, en rejouant la scene pour comparer, le TEXTE SEUL a produit exactement la
scene voulue -- femme debout dominante, homme a genoux, tete levee. 3/3. La seule
difference avec la version qui echouait : j'avais retire « low angle shot from
below » du prompt.

Ce banc departage les deux explications, parce qu'elles ne menent pas au meme
travail :
    A. « le rapport de force ne s'ecrit pas »  -> il faut ControlNet openpose
    B. « c'est le terme de CADRAGE qui casse » -> il suffit de ne pas l'ecrire

Une seule variable change entre les deux bras : la presence de ce terme.

Usage:
    C:/Users/quang/Documents/ComfyUI/.venv/Scripts/python.exe test_lowangle.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# On ne re-enveloppe PAS sys.stdout ici : le module importe le fait deja, et
# empiler deux TextIOWrapper sur le meme flux ferme le premier -> toute la sortie
# du banc plantait sur « I/O operation on closed file ».
import test_femdom_pose as T   # noqa: E402  (reutilise son workflow et ses prompts)

SCENE_NUE = T.SCENE
SCENE_LOW = T.SCENE.replace("looking up,", "looking up, low angle shot from below,")


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=8)
    args = ap.parse_args()
    from ultralytics import YOLO
    yolo = YOLO(T.FACE)
    compte = lambda p: len(yolo.predict(p, conf=0.35, verbose=False)[0].boxes)
    os.makedirs(T.OUT, exist_ok=True)

    print("Hypothese A : le rapport de force ne s'ecrit pas (il faut une pose)")
    print("Hypothese B : c'est « low angle shot from below » qui casse la scene\n")
    resultats = {}
    for nom, scene in (("sans_lowangle", SCENE_NUE), ("avec_lowangle", SCENE_LOW)):
        T.SCENE = scene
        vals = []
        print("-- %s" % nom)
        for k in range(args.seeds):
            p = T.run("hyp_%s_s%d" % (nom, k), T.SEED + k * 111)
            if p:
                vals.append(compte(p))
        resultats[nom] = vals
        # Le denominateur est le nombre d'images REELLEMENT produites, pas une
        # constante : afficher « 3/3 » quand on a lance 8 tirages est un chiffre
        # faux, et un chiffre faux dans un banc vaut moins que pas de chiffre.
        print("   visages %s -> deux personnages %d/%d\n"
              % ("/".join(map(str, vals)),
                 sum(1 for v in vals if v >= 2), len(vals)))

    a = sum(1 for v in resultats["sans_lowangle"] if v >= 2)
    b = sum(1 for v in resultats["avec_lowangle"] if v >= 2)
    print("=" * 58)
    n = args.seeds
    print("sans « low angle » : %d/%d     avec : %d/%d" % (a, n, b, n))
    if abs(a - b) <= 1:
        print("=> ECART D'UNE IMAGE AU PLUS : c'est du BRUIT, on ne tranche pas.")
        print("   (le piege deja paye : conclure d'un ecart qu'un seul tirage annule)")
        return 0
    if a > b:
        print("=> HYPOTHESE B retenue : c'est le terme de CADRAGE qui faisait")
        print("   disparaitre le second personnage, pas le rapport de force.")
        print("   Consequence : ne pas melanger cadrage et mise en scene dans le")
        print("   meme prompt -- le cadrage se contraint autrement (openpose).")
    elif b > a:
        print("=> inattendu : « low angle » AIDE. L'echec du 27/07 avait une")
        print("   autre cause, encore inconnue. Ne rien conclure.")
    else:
        print("=> les deux bras se valent : « low angle » n'explique pas l'echec")
        print("   du 27/07. La cause reste a trouver -- ne pas la deviner.")
    print("\nimages -> %s" % T.OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
