# -*- coding: utf-8 -*-
"""Rend au disque ce qui n'appartient plus a aucun projet. (28/07/2026)

Signale par Quang : « la base de donnees des images conserve les images meme si
je supprime des projets [...] le repertoire manga est vraiment contamine de
vieilles donnees, ce n'est pas du tout acceptable ».

Deux dossiers, et il avait raison sur les deux :

  manga-studio/output/<slug>/   les images RANGEES, celles que l'app montre.
                                Un projet supprime laissait le sien derriere lui.
  ComfyUI/output/manga/<...>/   l'ATELIER de ComfyUI. Le harvest DEPLACE l'image
                                retenue, mais tout le reste y reste : deuxiemes
                                images d'un lot, generations de bancs jamais
                                rapatriees. 702 Mo au moment du signalement --
                                dont ~216 Mo produits par MES bancs du jour.

L'app ne laissera plus de trace (le proxy efface les deux dossiers a la
suppression d'un projet). Ce script s'occupe du PASSE.

Trois familles, et elles ne se valent pas :
  ORPHELIN   un dossier dont le slug n'existe plus en base  -> a supprimer
  BANC       un dossier de test (prefixe _, ou motif <nom>-<pid>) -> a supprimer
  ATELIER    ComfyUI/output/manga/* -> regenerable par construction

⚠ RIEN n'est supprime sans `--faire`. Les projets VIVANTS ne sont jamais
touches, meme avec `--faire`.

Usage :
    python menage_sorties.py              montre (rien n'est efface)
    python menage_sorties.py --faire      efface
    python menage_sorties.py --atelier    inclut ComfyUI/output/manga
"""
import argparse
import io
import json
import os
import shutil
import sys
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ICI = os.path.dirname(os.path.abspath(__file__))
OUT_APP = os.path.normpath(os.path.join(ICI, "..", "output"))
OUT_COMFY = r"C:\Users\quang\Documents\ComfyUI\output\manga"
PROXY = os.environ.get("MANGA_PROXY", "http://127.0.0.1:8190")
SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"


def slugs_vivants():
    """Les projets qui existent ENCORE. Rend None si on n'a pas pu demander --
    et dans ce cas on n'efface rien : sans cette liste, tout serait 'orphelin'."""
    try:
        req = urllib.request.Request(
            PROXY + "/manga/projects",
            headers={"Authorization": "Bearer "
                     + io.open(SECRET_FILE, encoding="utf-8").read().strip()})
        with urllib.request.urlopen(req, timeout=30) as r:
            items = json.load(r).get("items")
        if items is None:
            return None
        return set((p.get("slug") or "").strip() for p in items if p.get("slug"))
    except Exception as e:
        print("ARRET : impossible de lister les projets (%s)" % e)
        return None


def poids(chemin):
    n, o = 0, 0
    for _, _, fs in os.walk(chemin):
        for f in fs:
            n += 1
            try:
                o += os.path.getsize(os.path.join(_, f)) if False else 0
            except Exception:
                pass
    # os.walk donne le dossier en 1er element ; on le refait proprement :
    n, o = 0, 0
    for dossier, _, fs in os.walk(chemin):
        for f in fs:
            n += 1
            try:
                o += os.path.getsize(os.path.join(dossier, f))
            except Exception:
                pass
    return n, o


def est_banc(nom):
    """Un dossier de test : prefixe '_' (bancs et explorations) ou '<mot>-<pid>'."""
    if nom.startswith("_"):
        return True
    bout = nom.rsplit("-", 1)
    return len(bout) == 2 and bout[1].isdigit() and len(bout[1]) >= 4


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--faire", action="store_true")
    ap.add_argument("--atelier", action="store_true",
                    help="inclut ComfyUI/output/manga (regenerable)")
    args = ap.parse_args()

    vivants = slugs_vivants()
    if vivants is None:
        print("Rien n'a ete efface : sans la liste des projets, tout paraitrait orphelin.")
        return 2
    print("Projets vivants : " + (", ".join(sorted(vivants)) or "(aucun)"))

    lots = []
    for nom in sorted(os.listdir(OUT_APP)) if os.path.isdir(OUT_APP) else []:
        d = os.path.join(OUT_APP, nom)
        if not os.path.isdir(d):
            continue
        if nom in vivants:
            continue                                   # jamais un projet vivant
        lots.append(("BANC" if est_banc(nom) else "ORPHELIN", d, nom))
    if args.atelier and os.path.isdir(OUT_COMFY):
        for nom in sorted(os.listdir(OUT_COMFY)):
            d = os.path.join(OUT_COMFY, nom)
            # ⚠ Un projet VIVANT est intouchable ici AUSSI. Son dossier d'atelier
            # est vide la plupart du temps (le harvest a deplace l'image), mais
            # pas TOUJOURS : pendant une generation, l'image y est encore. Une
            # regle de securite qui ne vaut que dans un dossier sur deux n'est
            # pas une regle de securite.
            if os.path.isdir(d) and nom not in vivants:
                lots.append(("ATELIER", d, nom))

    if not lots:
        print("\nRien a nettoyer.")
        return 0

    total_n, total_o = 0, 0
    resistants = []
    print("")
    for genre, d, nom in lots:
        n, o = poids(d)
        total_n += n
        total_o += o
        print("  %-9s %-26s %4d fichier(s)  %6.1f Mo" % (genre, nom, n, o / 1048576.0))
        if args.faire:
            shutil.rmtree(d, ignore_errors=True)
            # ⚠ `ignore_errors=True` avale l'echec : sans ce controle, le script
            # annonce « EFFACES » alors qu'un dossier a resiste (vu le 28/07 --
            # `banc-phase4`, vide mais tenu par un autre processus). Un outil qui
            # ne verifie pas son propre geste RAPPORTE une action, pas un fait.
            if os.path.isdir(d):
                restes, _ = poids(d)
                resistants.append((nom, restes))

    print("\n  %d dossier(s), %d fichier(s), %.1f Mo" % (len(lots), total_n, total_o / 1048576.0))
    if args.faire:
        if resistants:
            print("  -> EFFACES, SAUF %d dossier(s) qu'un autre processus tenait :"
                  % len(resistants))
            for nom, restes in resistants:
                print("       %-26s %s" % (nom, ("VIDE, coquille seule" if not restes
                                                 else "%d fichier(s) ENCORE LA" % restes)))
            print("     (ferme l'explorateur / ComfyUI et relance, ou supprime a la main)")
        else:
            print("  -> EFFACES, verifie : plus aucun de ces dossiers n'existe.")
    else:
        print("  -> rien n'a ete efface. Relance avec --faire (et --atelier pour ComfyUI).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
