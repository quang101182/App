# -*- coding: utf-8 -*-
"""Rend aux cases les images d'origine devenues orphelines. (28/07/2026)

Signale par Quang : « le lot remplace litteralement les images qui etaient
presentes avant ». Verifie en base : ses cases regenerees ne portaient plus
qu'UN essai.

La cause n'etait pas le lot. Avant la v1.48.0, une case gardait TOUJOURS le meme
nom de fichier (`<id>.png`) et `versions` n'existait pas : ces cases ont donc un
`file` mais aucun historique. A la premiere regeneration, `versions` repartait
de [] et l'image d'origine n'y entrait jamais -- elle restait sur le DISQUE,
simplement plus atteignable depuis l'app.

L'app ne repetera plus l'erreur (v1.65.0). Ce script repare le PASSE : pour
chaque case, si un fichier lui appartient sur le disque sans figurer dans ses
essais, il l'y remet -- en tete, puisque c'est le plus ancien.

Il ne SUPPRIME jamais rien et n'ecrit qu'apres confirmation.

Usage :
    python reparer_essais.py             montre ce qui serait fait (rien n'est ecrit)
    python reparer_essais.py --ecrire    applique
"""
import argparse
import io
import json
import os
import sys
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PROXY = os.environ.get("MANGA_PROXY", "http://127.0.0.1:8190")
SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"


def api(chemin, data=None):
    req = urllib.request.Request(
        PROXY + chemin,
        data=json.dumps(data).encode("utf-8") if data is not None else None,
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + open(SECRET_FILE).read().strip()})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ecrire", action="store_true")
    args = ap.parse_args()

    projets = (api("/manga/projects").get("items") or [])
    total, repares = 0, 0
    for pr in projets:
        # ⚠ La route rend `{"files": [...]}`, PAS `{"items": [...]}` comme ses
        # voisines. Ecrit avec `items`, ce script trouvait 0 orpheline sur 35
        # cases -- un zero rassurant et faux. Une liste vide n'est pas une preuve
        # d'absence : c'est souvent la preuve qu'on a mal demande.
        rep = api("/manga/files?slug=" + pr["slug"])
        brut = rep.get("files")
        if brut is None:
            print("ARRET : /manga/files ne rend pas de liste `files` (clés : %s)"
                  % ", ".join(rep.keys()))
            return 2
        fichiers = [f.get("path") or f.get("name") or "" for f in brut]
        pages = (api("/manga/pages?project=" + pr["id"]).get("items") or [])
        for pg in pages:
            for c in (api("/manga/panels?page=" + pg["id"]).get("items") or []):
                rec = c.get("recipe") or {}
                versions = rec.get("versions") or []
                connus = set(v.get("file") for v in versions if v)
                if c.get("file"):
                    connus.add(c["file"])
                # Un fichier « appartient » a la case si son nom porte son id.
                a_elle = [f for f in fichiers if c["id"] in f]
                perdus = [f for f in a_elle if f not in connus]
                total += 1
                if not perdus:
                    continue
                repares += 1
                print("  case %s (%s) : %d image(s) orpheline(s)"
                      % (c["id"], pr["slug"], len(perdus)))
                for f in perdus:
                    print("      + " + f)
                if args.ecrire:
                    # En TETE et par ordre de nom : les plus anciennes d'abord.
                    # `ts: 0` les marque comme anterieures a l'historique.
                    nouvelles = [{"file": f, "seed": rec.get("seed"),
                                  "ts": 0, "recupere": True}
                                 for f in sorted(perdus)]
                    rec["versions"] = nouvelles + versions
                    c["recipe"] = rec
                    api("/manga/panels", c)

    print("\n%d case(s) examinee(s), %d avec des images orphelines." % (total, repares))
    if repares and not args.ecrire:
        print("Rien n'a ete ecrit. Relance avec --ecrire pour les rendre aux cases.")
    elif repares:
        print("Images rendues : elles reapparaissent sous la case, dans les essais.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
