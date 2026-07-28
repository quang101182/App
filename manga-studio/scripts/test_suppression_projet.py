# -*- coding: utf-8 -*-
"""Supprimer un projet supprime-t-il VRAIMENT ses images ? (28/07/2026)

Signale par Quang : « la base conserve les images meme si je supprime des
projets [...] le repertoire manga est vraiment contamine de vieilles donnees ».

Le comportement d'origine etait assume dans le code (« effacer une fiche ne doit
jamais effacer des images »). Son avis le renverse : un projet supprime qu'on
retrouve en fouillant le disque n'est pas supprime.

Ce banc verifie les DEUX sens, et le second compte autant :
  1. supprimer un projet efface ses images dans les DEUX dossiers -- celui que
     l'app montre ET l'atelier de ComfyUI, invisible et jamais nettoye ;
  2. il n'efface RIEN d'autre : le projet voisin est intact apres coup.

Le point 2 est le vrai enjeu. Une suppression qui deborde de son perimetre est
le seul defaut de cette famille qu'on ne peut pas rattraper.

Usage:
    python test_suppression_projet.py
"""
import io
import json
import os
import sys
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PROXY = os.environ.get("MANGA_PROXY", "http://127.0.0.1:8190")
SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
OUT_APP = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        "..", "output"))
OUT_COMFY = r"C:\Users\quang\Documents\ComfyUI\output\manga"

cas = []


def verifie(nom, ok, detail=""):
    cas.append((nom, bool(ok)))
    print(("  OK    " if ok else "  ECHEC") + " " + nom + ((" — " + detail) if detail else ""))
    return ok


def api(chemin, data=None):
    req = urllib.request.Request(
        PROXY + chemin,
        data=json.dumps(data).encode("utf-8") if data is not None else None,
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer "
                 + io.open(SECRET_FILE, encoding="utf-8").read().strip()})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def pose(slug, n=2):
    """Cree les dossiers et y met des fichiers, dans les DEUX emplacements."""
    for base in (OUT_APP, OUT_COMFY):
        d = os.path.join(base, slug)
        os.makedirs(d, exist_ok=True)
        for i in range(n):
            io.open(os.path.join(d, "img%d.png" % i), "wb").write(b"\x89PNG-faux")


def compte(slug):
    total = 0
    for base in (OUT_APP, OUT_COMFY):
        d = os.path.join(base, slug)
        for _, _, fs in os.walk(d):
            total += len(fs)
    return total


def main():
    cible = "_supprtest_%d" % os.getpid()
    voisin = "_voisintest_%d" % os.getpid()
    pr = api("/manga/projects", {"name": cible, "slug": cible})
    pv = api("/manga/projects", {"name": voisin, "slug": voisin})
    pose(cible, 3)
    pose(voisin, 2)

    verifie("le décor est monté (3 images pour la cible, 2 pour le voisin)",
            compte(cible) == 6 and compte(voisin) == 4,
            "cible %d · voisin %d" % (compte(cible), compte(voisin)))

    r = api("/manga/projects", {"delete": pr["id"]})
    verifie("la suppression RAPPORTE combien de fichiers elle a effacés",
            isinstance(r.get("files_deleted"), int) and r["files_deleted"] == 6,
            "files_deleted = %s" % r.get("files_deleted"))
    verifie("plus aucune image du projet supprimé, dans les DEUX dossiers",
            compte(cible) == 0, "%d fichier(s) restant(s)" % compte(cible))
    verifie("… et le dossier lui-même a disparu de l'app",
            not os.path.isdir(os.path.join(OUT_APP, cible)))
    verifie("… et de l'atelier ComfyUI",
            not os.path.isdir(os.path.join(OUT_COMFY, cible)))

    # LE test qui compte : la suppression n'a pas deborde.
    verifie("le projet VOISIN est intact", compte(voisin) == 4,
            "%d fichier(s)" % compte(voisin))
    restants = [p.get("slug") for p in (api("/manga/projects").get("items") or [])]
    verifie("… et il est toujours en base", voisin in restants)

    # Un slug vide ne doit RIEN effacer (sinon il viserait la racine).
    avant = len(os.listdir(OUT_APP))
    try:
        api("/manga/projects", {"delete": "id-qui-nexiste-pas"})
    except Exception:
        pass
    verifie("supprimer un projet inconnu n'efface rien",
            len(os.listdir(OUT_APP)) == avant,
            "%d -> %d entrée(s)" % (avant, len(os.listdir(OUT_APP))))

    api("/manga/projects", {"delete": pv["id"]})
    ko = [n for n, ok in cas if not ok]
    print("\n%d/%d" % (len(cas) - len(ko), len(cas)))
    for n in ko:
        print("  - " + n)
    return 1 if ko else 0


if __name__ == "__main__":
    sys.exit(main())
