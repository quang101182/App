# -*- coding: utf-8 -*-
"""Recadrer la reference sur le visage change-t-il la case produite ?

Constat du 28/07, vu a l'oeil sur les vraies fiches de Quang : IPAdapter PLUS ne
transfere pas que l'identite, il transfere la COMPOSITION de l'image montree. Les
references de Jo et Kimiko etant des PLANCHES DE PERSONNAGE (plusieurs vues, fond
vide), la case heritait de leur mise en page -- grand visage flottant, echelles
incoherentes, et parfois trois ou quatre tetes la ou on en demandait deux.

Ce banc mesure ce que vaut le recadrage (`crop_ref.py`), sur les MEMES images,
avec le meme graphe duo masque que `test_deux_refs.py` (importe, jamais recopie).

LA MESURE PRINCIPALE N'EST PAS L'IDENTITE, C'EST LE NOMBRE DE VISAGES
----------------------------------------------------------------------
On demande deux personnages ; une planche de design en produit trois ou quatre.
Le compte de visages est donc la mesure DIRECTE du defaut constate -- et elle est
objective, la ou « ca fait planche de design » ne l'est pas. L'identite (chaque
visage plus proche de SA reference) est reportee en second, avec la reserve deja
ecrite le 27/07 : l'instrument separe deux designs eloignes, pas une identite fine.

⚠ Les etalons d'identite sont les references RECADREES dans les deux bras : un
etalon qui changerait avec le bras ne comparerait plus rien.

Usage:
    C:/Users/quang/Documents/ComfyUI/.venv/Scripts/python.exe test_crop_ref.py
    ... --seeds 6
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from test_ipadapter import QUAL, BW, SEED, Visages, upload  # noqa: E402
from test_deux_refs import juge, run, visages_tries  # noqa: E402
from crop_ref import recadre  # noqa: E402

OUT = os.path.join(HERE, "duo_refs_out")
IN_COMFY = r"C:\Users\quang\Documents\ComfyUI\input"
# Les vraies fiches de Quang, telles qu'elles sont sur le disque.
REF_KIMIKO = os.path.join(IN_COMFY, "ref_mh19fa2e0f510038_1785163796125.png")
REF_JO = os.path.join(IN_COMFY, "ref_mh19fa4741f984a3_1785170563690.png")
# Tags NETTOYES (le style et le « character design » retires) : sans ca, c'est le
# TEXTE qui impose une planche de personnage, et on ne mesurerait plus l'image.
SCENE = (QUAL + BW + "2people, standing side by side, facing viewer, upper body, "
         "talking, indoor room background, "
         "1girl, black hair, short hair, sharp eyes, japanese school uniform, "
         "and 1man, short hair, 30 years old, short stature, stubble")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=6)
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    for p in (REF_KIMIKO, REF_JO):
        if not os.path.isfile(p):
            print("ARRET : reference introuvable : %s" % p)
            return 2

    print("=== recadrage des deux references ===")
    crops = {}
    for nom, src in (("kimiko", REF_KIMIKO), ("jo", REF_JO)):
        dest = os.path.join(OUT, "_crop_%s.png" % nom)
        r = recadre(src, dest)
        if not r["ok"]:
            print("ARRET : %s non recadrable (%s)" % (nom, r["raison"]))
            return 2
        crops[nom] = dest
        print("  %-7s visage %.1f %% -> %.1f %% de l'image"
              % (nom, 100 * r["visage_avant"], 100 * r["visage_apres"]))

    vis = Visages()
    # Etalons : les visages des references RECADREES (les seules ou le visage est
    # assez grand pour que CLIP en tire autre chose que du fond).
    embK, embJ = vis.emb(crops["kimiko"]), vis.emb(crops["jo"])
    if embK is None or embJ is None:
        print("ARRET : aucun visage detecte sur les references recadrees.")
        return 2
    sep = 1.0 - float(vis.np.dot(embK, embJ))
    print("  ecart entre les deux etalons : %.3f (cosinus %.3f)"
          % (sep, float(vis.np.dot(embK, embJ))))

    bras = {
        "brut":    [upload(REF_KIMIKO, en_nb=True), upload(REF_JO, en_nb=True)],
        "recadre": [upload(crops["kimiko"], en_nb=True), upload(crops["jo"], en_nb=True)],
    }
    if bras["brut"][0] == bras["recadre"][0] or bras["brut"][1] == bras["recadre"][1]:
        print("ARRET : brut et recadre portent le meme nom cote ComfyUI —"
              " le banc ne mesurerait qu'un seul bras.")
        return 2

    res = {}
    for nom, refs in bras.items():
        print("\n-- bras %s" % nom)
        res[nom] = []
        for k in range(args.seeds):
            p = run("crop_%s_s%d" % (nom, k), SEED + k, refs, True, 0.6, SCENE)
            if not p:
                res[nom].append(None)
                continue
            # Combien de visages en tout ? C'est LA mesure du defaut constate.
            tous = visages_tries(vis, p, n=8)
            j = juge(vis, p, [embK], [embJ])
            j["visages"] = len(tous)
            res[nom].append(j)

    print("\n=========== RECADRER LA REFERENCE, CE QUE CA CHANGE ===========")
    print("On demande DEUX personnages. Une planche de design en produit 3 ou 4.")
    print("%-9s | %-14s | %-12s | %-8s | %-6s"
          % ("bras", "exactement 2", "visages (moy)", "chacun a", "sat"))
    print("%-9s | %-14s | %-12s | %-8s | %-6s"
          % ("", "visages", "", "sa place", ""))
    print("-" * 62)
    for nom in bras:
        v = [x for x in res[nom] if x]
        if not v:
            print("%-9s | (aucune image)" % nom)
            continue
        deux = sum(1 for x in v if x["visages"] == 2)
        moy = sum(x["visages"] for x in v) / len(v)
        q2 = sum(1 for x in v if x.get("q2"))
        sat = [x["sat"] for x in v if x.get("sat") is not None]
        print("%-9s | %d/%-12d | %-12.2f | %d/%-6d | %-6s"
              % (nom, deux, len(v), moy, q2, len(v),
                 "%.3f" % (sum(sat) / len(sat)) if sat else "-"))
    print("-" * 62)
    print("\ndetail :")
    for nom in bras:
        for k, x in enumerate(res[nom]):
            if not x:
                print("  %-9s s%d : (echec)" % (nom, k))
            else:
                print("  %-9s s%d : %d visage(s)%s"
                      % (nom, k, x["visages"],
                         ("  gauche K%.3f/J%.3f  droite K%.3f/J%.3f %s"
                          % (x["gA"], x["gB"], x["dA"], x["dB"],
                             "Q2v" if x["q2"] else "Q2x")) if x["n"] >= 2 else ""))
    print("\nimages -> %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
