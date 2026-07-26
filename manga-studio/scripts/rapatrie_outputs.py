# -*- coding: utf-8 -*-
"""Rapatrie les sorties MANGA hors du dossier output de Generate Studio.

Pourquoi : les scripts de la phase d'exploration (26/07) ecrivaient leurs images
directement a la racine de C:\\Users\\quang\\Documents\\ComfyUI\\output, la ou
Generate Studio range les siennes (friday_*, studio_*, muse_*, series_*).
Resultat : 62 fichiers a nous melanges a 850 fichiers a Quang.

Ce script DEPLACE (il ne copie pas, il ne supprime pas) les fichiers dont le
prefixe appartient au chantier manga vers App/manga-studio/output/_exploration/.

Il refuse de bouger un prefixe qu'il ne connait pas : la liste est explicite,
jamais deduite. Un fichier ambigu reste ou il est plutot que d'etre deplace a tort.

Usage:
    python rapatrie_outputs.py --dry-run   (defaut : montre sans rien bouger)
    python rapatrie_outputs.py --apply
"""
import argparse
import os
import re
import shutil
import sys

SRC = r"C:\Users\quang\Documents\ComfyUI\output"
DEST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output", "_exploration")

# Prefixes ECRITS PAR LES SCRIPTS DU CHANTIER MANGA (26/07). Liste close, verifiee
# script par script : manga_test.py -> mangatest_, manga_dataset.py -> ds_ + ref_,
# manga_sheet.py -> sheet_, manga_test_lora.py -> loratest_, manga_scene.py -> fond_/depth_/case_,
# inpaint_zone.py -> inpaint_.
MINE = {"ds", "case", "sheet", "mangatest", "inpaint", "loratest", "ref", "depth", "fond"}

# Prefixes de Quang, listes ici uniquement pour que le refus soit EXPLICITE dans le
# rapport (et qu'une relecture voie qu'ils ont ete consideres puis ecartes).
HIS = {"friday", "studio", "muse", "series"}


def prefix_of(name):
    """'case_00014_.png' -> 'case' ; 'friday_anat_0003_.png' -> 'friday_anat'."""
    return re.sub(r"[_-]?\d+_?\.\w+$", "", name) or name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="deplace pour de vrai")
    args = ap.parse_args()

    if not os.path.isdir(SRC):
        print("ERREUR: dossier source introuvable: %s" % SRC)
        return 2

    moved, skipped, unknown = [], 0, {}
    for name in sorted(os.listdir(SRC)):
        path = os.path.join(SRC, name)
        if not os.path.isfile(path):
            continue
        p = prefix_of(name)
        if p in MINE:
            moved.append(name)
        elif p.split("_")[0] in HIS:
            skipped += 1
        else:
            unknown[p] = unknown.get(p, 0) + 1

    print("=== RAPATRIEMENT DES SORTIES MANGA ===")
    print("source : %s" % SRC)
    print("cible  : %s" % os.path.normpath(DEST))
    print("")
    print("a deplacer (prefixes manga) : %d" % len(moved))
    by_prefix = {}
    for n in moved:
        by_prefix.setdefault(prefix_of(n), []).append(n)
    for p in sorted(by_prefix):
        print("   %-12s %d" % (p, len(by_prefix[p])))
    print("laisses en place (Generate Studio) : %d" % skipped)
    if unknown:
        print("NON RECONNUS -> laisses en place par prudence :")
        for p, n in sorted(unknown.items()):
            print("   %-12s %d" % (p, n))

    if not args.apply:
        print("\n(dry-run : rien n'a bouge. Relancer avec --apply)")
        return 0

    os.makedirs(DEST, exist_ok=True)
    ok, fail = 0, []
    for name in moved:
        try:
            dst = os.path.join(DEST, name)
            if os.path.exists(dst):          # jamais ecraser en silence
                base, ext = os.path.splitext(name)
                dst = os.path.join(DEST, base + "_dup" + ext)
            shutil.move(os.path.join(SRC, name), dst)
            ok += 1
        except Exception as ex:
            fail.append((name, str(ex)))
    print("\ndeplaces : %d" % ok)
    if fail:
        print("ECHECS : %d" % len(fail))
        for n, e in fail:
            print("   %s -> %s" % (n, e))
        return 1
    reste = len([f for f in os.listdir(SRC) if os.path.isfile(os.path.join(SRC, f))])
    print("restant a la racine output/ (= Generate Studio seul) : %d" % reste)
    return 0


if __name__ == "__main__":
    sys.exit(main())
