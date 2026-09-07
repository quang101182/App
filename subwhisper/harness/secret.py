# -*- coding: utf-8 -*-
"""Fournit la cle du gateway aux harnesses, SANS jamais l'imprimer ni la versionner.

Ordre de recherche :
  1. la variable d'environnement SUBWHISPER_GATEWAY_KEY ;
  2. le fichier designe par SUBWHISPER_SECRET_FILE ;
  3. le coffre local par defaut (poste de Quang).

⚠️ Ce fichier est dans un depot PUBLIC : il ne contient aucune valeur, seulement
le moyen d'aller la chercher. Ne jamais y ecrire de cle, meme temporairement.
"""
import io
import os
import pathlib
import re

COFFRE_DEFAUT = "D:/Download/02-Apps-Web/.secrets/worker_secret.txt"


def worker_secret() -> str:
    val = os.environ.get("SUBWHISPER_GATEWAY_KEY", "").strip()
    if val:
        return val

    chemin = pathlib.Path(os.environ.get("SUBWHISPER_SECRET_FILE", COFFRE_DEFAUT))
    if not chemin.exists():
        raise RuntimeError(
            "cle du gateway introuvable : ni SUBWHISPER_GATEWAY_KEY dans "
            f"l'environnement, ni le fichier {chemin}."
        )
    for ligne in io.open(chemin, encoding="utf-8", errors="replace"):
        s = ligne.strip()
        if not s or s.startswith("#"):
            continue
        m = re.search(r"[A-Za-z0-9_\-]{24,}", s)
        if m:
            return m.group(0)
    raise RuntimeError(f"aucune cle exploitable dans {chemin}")
