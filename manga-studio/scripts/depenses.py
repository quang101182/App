"""Registre des DEPENSES, en ajout seul (v1.0.0, 24/09/2026 -- remarque Quang : « encore ce matin j'etais a plus de 30 $ ce
mois, l'affichage a saute a 18,71 $ »).

Cause : le compteur additionnait les couts ecrits dans les fichiers PRESENTS (narration.json, traduction.json). Refaire
une traduction ECRASAIT la depense precedente, supprimer un chapitre ou vider la corbeille l'effacait. Or ces sommes ont
ete payees. Ici : une ligne par passage paye, jamais modifiee ni effacee (sources/_depenses.jsonl).
  noter(type, d, tag, moteur, paye, **detail)   -> ajoute une ligne
  lire()                                         -> toutes les lignes
Une narration qui REUTILISE une analyse n'inscrit que ce qu'elle paie elle-meme (recit, voix, noms), jamais l'analyse
recopiee.
"""
import json, os, time

VERSION = "1.0.0"
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.environ.get("MANGA_SOURCES_DIR") or os.path.join(HERE, "..", "sources"))
REGISTRE = os.environ.get("MANGA_DEPENSES") or os.path.join(SRC, "_depenses.jsonl")   # bancs : fichier jetable


def noter(type_, d, tag, moteur, paye, **detail):
    if not paye:
        return
    ligne = dict(t=time.strftime("%Y-%m-%dT%H:%M:%S"), type=type_, d=d, tag=tag, moteur=moteur,
                 paye=round(float(paye), 5), **detail)
    try:
        with open(REGISTRE, "a", encoding="utf-8") as f:            # « a » : ajout atomique d'une ligne courte
            f.write(json.dumps(ligne, ensure_ascii=False) + "\n")
    except OSError:
        pass


def lire():
    out = []
    try:
        with open(REGISTRE, encoding="utf-8") as f:
            for l in f:
                try:
                    out.append(json.loads(l))
                except ValueError:
                    continue
    except OSError:
        pass
    return out
