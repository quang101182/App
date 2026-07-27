# -*- coding: utf-8 -*-
"""Lit les journaux de Manga Studio deposes sur le PC.

L'app envoie son journal toute seule (a chaque erreur, toutes les 60 s, et au
depart de la page) dans Documents/ComfyUI/logs/, un fichier PAR APPAREIL :

    log-manga-live-pc.json       depuis le PC
    log-manga-live-mobile.json   depuis le telephone

Pourquoi ce script existe plutot qu'un simple `cat` : le fichier est en UTF-8 et
la console Windows est en cp1252 -- un `cat` rend « clé présente » en « cl� pr�sente »,
ce qui suffit a rendre un diagnostic penible. Et surtout, il remet le CONTEXTE en
tete (version, appareil, projet, etat des cases), qui est souvent la reponse.

Usage:
    python lire_log.py                 les deux appareils, 40 dernieres lignes
    python lire_log.py --n 200         plus de lignes
    python lire_log.py --erreurs       seulement les erreurs
    python lire_log.py --ou mobile     un seul appareil
"""
import argparse
import glob
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

LOGS = r"C:\Users\quang\Documents\ComfyUI\logs"


def lire(chemin, n, erreurs_seules):
    try:
        brut = json.load(io.open(chemin, encoding="utf-8"))
    except Exception as e:
        print("  illisible : %s" % e)
        return
    if not isinstance(brut, list):
        print("  format inattendu (ce n'est pas une liste)")
        return
    ctx = brut[0] if brut and isinstance(brut[0], dict) and brut[0].get("type") == "contexte" else {}
    ev = [x for x in brut if isinstance(x, dict) and x.get("type") != "contexte"]

    if ctx:
        print("  version %s · envoye %s" % (ctx.get("version"), ctx.get("envoye")))
        print("  ecran %s · %s" % (ctx.get("ecran"), (ctx.get("appareil") or "")[:60]))
        print("  projet %s · planche %s" % (ctx.get("projet"), ctx.get("planche")))
        cases = ctx.get("cases") or []
        if cases:
            g = sum(1 for c in cases if c.get("generee"))
            b = sum(1 for c in cases if c.get("bulles"))
            v = sum(1 for c in cases if c.get("verdict"))
            print("  %d case(s) : %d generee(s), %d lettree(s), %d jugee(s)"
                  % (len(cases), g, b, v))
    else:
        print("  (pas de contexte -- journal d'une version anterieure)")

    if erreurs_seules:
        ev = [x for x in ev if x.get("cls") == "e"]
    print("  --- %d evenement(s)%s ---"
          % (len(ev), " (erreurs seules)" if erreurs_seules else ""))
    for l in ev[-n:]:
        marque = {"e": "ERR", "w": "att", "s": " ok"}.get(l.get("cls"), "   ")
        print("  %s %s %s" % (l.get("t", "?")[:12], marque, str(l.get("msg"))[:150]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--erreurs", action="store_true")
    ap.add_argument("--ou", choices=["pc", "mobile"], default=None)
    args = ap.parse_args()

    # Depuis la v1.44.0, chaque NAVIGATEUR a son fichier :
    #   log-manga-live-mobile-<id>.json
    # Avant, tous les telephones partageaient « mobile » et s'ecrasaient : le
    # 27/07, un onglet reste ouvert sur une vieille version a recouvert en boucle
    # le journal de l'incident qu'on cherchait. Le fichier etait a l'heure et
    # racontait la mauvaise session -- le pire cas, parce qu'on le croit bon.
    motif = "log-manga-live-%s*.json" % (args.ou or "")
    fichiers = glob.glob(os.path.join(LOGS, motif))
    # Le PLUS RECENT en dernier : c'est celui qu'on lit en premier a l'ecran.
    fichiers.sort(key=os.path.getmtime)
    # Compatibilite : le premier format n'avait pas de suffixe d'appareil.
    ancien = os.path.join(LOGS, "log-manga-live.json")
    if not args.ou and os.path.isfile(ancien):
        fichiers.append(ancien)
    if not fichiers:
        print("Aucun journal dans %s" % LOGS)
        print("L'app en depose un des qu'elle tourne (ou bouton « Envoyer au PC »).")
        return 1
    for f in fichiers:
        age = os.path.getmtime(f)
        import datetime
        print("\n=== %s  (ecrit %s) ==="
              % (os.path.basename(f),
                 datetime.datetime.fromtimestamp(age).strftime("%d/%m %H:%M:%S")))
        lire(f, args.n, args.erreurs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
