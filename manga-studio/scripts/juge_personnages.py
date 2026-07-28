# -*- coding: utf-8 -*-
"""Compter les PERSONNAGES d'une case — et prouver que l'outil sait le faire.

Pourquoi ce fichier existe (28/07/2026) : le banc du duo a conclu « 0/5 » avec
un detecteur de VISAGES, sur des images qui montraient toutes DEUX personnages —
simplement en plan trop large pour qu'un visage soit detectable. La mesure ne
disait pas « pas de personnage », elle disait « pas de visage ». Deuxieme fois
en deux jours qu'un instrument non calibre fait conclure a l'envers.

D'ou la regle appliquee ici : **`--calibrer` d'abord, usage ensuite**. L'outil
est confronte a des images dont le compte est connu (verifie a l'oeil), et il
DECLARE s'il en est capable. S'il echoue, il le dit et rend un code d'erreur —
il ne rend jamais un chiffre auquel on ne peut pas se fier.

Usage:
    python juge_personnages.py --calibrer          verifie l'outil sur des cas connus
    python juge_personnages.py img1.png img2.png   compte (JSON sur stdout)
"""
import argparse
import io
import json
import os
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PY_COMFY = r"C:\Users\quang\Documents\ComfyUI\.venv\Scripts\python.exe"
# yolov8 COCO : la classe 0 est « person ». Il est entraine sur des photos, pas
# sur du manga -- c'est precisement ce que la calibration doit trancher.
MODELE = "yolov8m.pt"
SEUIL = 0.25

CODE = """
import sys, json
from ultralytics import YOLO
y = YOLO(sys.argv[1])
seuil = float(sys.argv[2])
out = {}
for f in sys.argv[3:]:
    n = 0
    for r in y(f, verbose=False, conf=seuil, classes=[0]):
        n += len(r.boxes or [])
    out[f] = n
print("JSON:" + json.dumps(out))
"""


def compte(fichiers, modele=MODELE, seuil=SEUIL):
    """Rend {chemin: nb_personnes}. Vide = l'outil n'a pas pu conclure."""
    if not os.path.isfile(PY_COMFY):
        print("ARRET : le python de ComfyUI est introuvable (%s)" % PY_COMFY)
        return {}
    try:
        r = subprocess.run([PY_COMFY, "-c", CODE, modele, str(seuil)] + list(fichiers),
                           capture_output=True, timeout=1800)
        sortie = r.stdout.decode("utf-8", "replace")
        ligne = [l for l in sortie.splitlines() if l.startswith("JSON:")]
        if not ligne:
            print("ARRET : sortie inattendue du detecteur :")
            print((sortie or r.stderr.decode("utf-8", "replace"))[-500:])
            return {}
        return json.loads(ligne[-1][5:])
    except Exception as e:
        print("ARRET : detection impossible (%s)" % e)
        return {}


# Cas de calibration : le compte est VERIFIE A L'OEIL sur la planche-contact du
# 28/07 (scripts/essai_out/duo_contact.png). Deux silhouettes face a face au
# centre d'un dojo pour V1/V2/V3/V5 ; une foule de spectateurs pour V4.
CALIB = [
    ("essai_out/duo/V1-2people_880000.png", 2),
    ("essai_out/duo/V2-1boy1girl_880001.png", 2),
    ("essai_out/duo/V3-2boys_880000.png", 2),
    ("essai_out/duo/V5-temoin_880000.png", 2),
    ("essai_out/duo/V4-multiple_880001.png", 5),   # foule : « au moins 5 »
    ("essai_out/sans_visage/C-recadrage_424242.png", 1),   # un seul, gros plan
]


def calibrer():
    ici = os.path.dirname(os.path.abspath(__file__))
    cas = [(os.path.join(ici, f), n) for f, n in CALIB]
    manquants = [f for f, _ in cas if not os.path.isfile(f)]
    if manquants:
        print("ARRET : images de calibration absentes (rejoue les bancs qui les produisent) :")
        for m in manquants[:4]:
            print("   " + m)
        return 2
    vus = compte([f for f, _ in cas])
    if not vus:
        return 2
    print("=" * 70)
    print("CALIBRATION — l'outil retrouve-t-il des comptes CONNUS ?")
    print("=" * 70)
    bons = 0
    for f, attendu in cas:
        n = vus.get(f, -1)
        # « au moins » pour la foule : compter 12 ou 18 spectateurs est correct.
        ok = (n >= attendu) if attendu >= 5 else (n == attendu)
        bons += 1 if ok else 0
        print("  %-46s attendu %s · vu %s   %s"
              % (os.path.basename(f), attendu, n, "OK" if ok else "ECART"))
    print("\n  %d/%d" % (bons, len(cas)))
    if bons >= len(cas) - 1:
        print("  => UTILISABLE : il retrouve les comptes connus sur du manga N&B.")
        return 0
    print("  => INUTILISABLE EN L'ETAT. Ne PAS s'en servir pour conclure :")
    print("     un instrument qui rate des cas connus fera conclure a l'envers,")
    print("     exactement comme le detecteur de visages l'a fait le 28/07.")
    return 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calibrer", action="store_true")
    ap.add_argument("images", nargs="*")
    args = ap.parse_args()
    if args.calibrer:
        return calibrer()
    if not args.images:
        ap.print_help()
        return 2
    vus = compte(args.images)
    if not vus:
        return 2
    print(json.dumps(vus, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
