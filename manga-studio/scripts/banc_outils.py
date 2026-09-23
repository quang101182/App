# -*- coding: utf-8 -*-
"""Outils communs des bancs (23/09/2026) : la version ATTENDUE lue dans l'app (plus de numero en dur, qui cassait les
bancs a chaque version) et des series d'ESSAI copiees depuis la bibliotheque puis supprimees (un banc ne doit plus
dependre d'une copie laissee par une session precedente)."""
import json, os, re, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, "..", "sources"))


def version_app():
    s = open(os.path.join(HERE, "..", "manga_studio.html"), encoding="utf-8").read()
    return re.search(r'const VERSION = "([0-9.]+)"', s).group(1)


def copier_serie(src, dst, chapitres, pages_max=None, avec=("musique", "serie.json")):
    """sources/<src>/<ch> -> sources/<dst>/<ch> (pages, manifeste, narrations...) ; pages_max = seulement les N premieres."""
    supprimer_serie(dst)
    for ch in chapitres:
        a, b = os.path.join(SRC, src, ch), os.path.join(SRC, dst, ch)
        if pages_max is None:
            shutil.copytree(a, b, ignore=shutil.ignore_patterns("video", "*.progress.json"))
        else:
            os.makedirs(b)
            m = json.load(open(os.path.join(a, "manifest.json"), encoding="utf-8"))
            m["pages"] = m["pages"][:pages_max]
            for p in m["pages"]:
                shutil.copy2(os.path.join(a, p["file"]), os.path.join(b, p["file"]))
            json.dump(m, open(os.path.join(b, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False)
            for sous in ("narration", "traduction"):          # la narration sert aux videos (pages absentes : ignorees)
                if os.path.isdir(os.path.join(a, sous)):
                    shutil.copytree(os.path.join(a, sous), os.path.join(b, sous))
    for x in avec:
        f = os.path.join(SRC, src, x)
        if os.path.isdir(f):
            shutil.copytree(f, os.path.join(SRC, dst, x))
        elif os.path.isfile(f):
            shutil.copy2(f, os.path.join(SRC, dst, x))


def supprimer_serie(dst):
    """La serie d'essai ET ce qu'elle a pu mettre a la corbeille (jamais rien d'autre)."""
    if not dst.startswith("zz-"):
        raise SystemExit("refus : une serie d'essai commence par zz-")
    shutil.rmtree(os.path.join(SRC, dst), ignore_errors=True)
    cb = os.path.join(SRC, "_corbeille")
    for n in (os.listdir(cb) if os.path.isdir(cb) else []):
        if "_" + dst + "__" in n or n.endswith("_" + dst):
            shutil.rmtree(os.path.join(cb, n), ignore_errors=True)
