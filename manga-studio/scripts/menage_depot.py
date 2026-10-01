# -*- coding: utf-8 -*-
"""Menage du DOSSIER DU DEPOT manga-studio (01/10/2026). DEPLACE, n'efface jamais.

Deplace vers C:/Users/quang/Documents/MangaStudio-donnees/_archives/menage-<date>/ (arborescence conservee) :
  1. les copies *.bak* dont le fichier d'origine est VERSIONNE dans git (l'historique git les contient deja) ;
     une copie d'un fichier NON versionne reste en place (c'est peut-etre sa seule trace) ;
  2. les captures *.png NON suivies laissees par les bancs (ils les regenerent).
Ne touche pas : maquettes, dossiers d'essais (*_out/), modeles, sources/, output/, donnees.

Usage : python menage_depot.py            -> a blanc (liste + volumes, rien ne bouge)
        python menage_depot.py --appliquer
Retour arriere : recopier le dossier d'archive par-dessus manga-studio/ (meme arborescence)."""
import os, shutil, subprocess, sys, time

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCH = os.path.join(os.path.expanduser(r"~\Documents\MangaStudio-donnees\_archives"), "menage-" + time.strftime("%Y-%m-%d"))
SAUTER = {"sources", "output", "dataset_v2", "node_modules", ".git"}


def git(*a):
    return subprocess.run(["git", "-C", RACINE] + list(a), capture_output=True, text=True, encoding="utf-8").stdout


suivis = set(p.strip() for p in git("ls-files", "-z").split("\0") if p.strip())
non_suivis = set(p.strip() for p in git("ls-files", "--others", "--exclude-standard", "-z").split("\0") if p.strip())

choix, gardes = [], []
for d, dirs, fs in os.walk(RACINE):
    dirs[:] = [x for x in dirs if x not in SAUTER and not os.path.islink(os.path.join(d, x))]
    for f in fs:
        rel = os.path.relpath(os.path.join(d, f), RACINE).replace("\\", "/")
        if ".bak" in f:
            orig = rel.split(".bak")[0]
            (choix if orig in suivis and rel not in suivis else gardes).append(rel)
        elif f.lower().endswith(".png") and rel in non_suivis:
            choix.append(rel)

taille = sum(os.path.getsize(os.path.join(RACINE, r)) for r in choix)
print("a deplacer : %d fichiers, %.1f Mo -> %s" % (len(choix), taille / 1e6, ARCH))
print("  dont .bak : %d | captures png : %d" % (sum(".bak" in r for r in choix), sum(".bak" not in r for r in choix)))
print(".bak GARDES (original non versionne) : %d" % len(gardes))
for r in gardes: print("   garde :", r)
if "--appliquer" not in sys.argv:
    print("\n(a blanc -- rien n'a bouge ; --appliquer pour deplacer)"); sys.exit(0)

for r in choix:
    dst = os.path.join(ARCH, r)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.move(os.path.join(RACINE, r), dst)
reste = [r for r in choix if os.path.exists(os.path.join(RACINE, r))]
arrive = [r for r in choix if os.path.exists(os.path.join(ARCH, r))]
print("deplaces : %d / %d ; encore en place : %d" % (len(arrive), len(choix), len(reste)))
sys.exit(1 if reste or len(arrive) != len(choix) else 0)
