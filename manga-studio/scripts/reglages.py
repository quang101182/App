"""Reglage GLOBAL « ou tourne ce qui peut tourner sur le PC » (feuille de route 4-nonies, etape 4-bis, 24/09/2026).

Quang : « un menu simple, ergonomique et tres clair, pour que je repere rapidement si je vais lancer quelque chose en
local ou en cloud […] persistance […] a toi de voir si c'est par chapitre, par manga ou global ».
Choix : GLOBAL, cote serveur (sources/_reglages.json) -- ce qui decide, c'est ce que Quang fait sur son PC a ce
moment-la, pas le manga. Le meme reglage vaut sur le PC, le telephone et la nuit.
  mode « cloud » (defaut) : tout en ligne, comme avant.
  mode « pc »             : voix locale (Chatterbox) + effacement local du texte pose sur le dessin (carte graphique).
L'analyse des pages et le recit restent en ligne dans les deux modes (analyse locale mesuree moins fidele, 24/09).
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, "..", "sources"))
FICHIER = os.environ.get("MANGA_REGLAGES") or os.path.join(SRC, "_reglages.json")
DEFAUT = {"mode": "cloud"}


def lire():
    try:
        with open(FICHIER, encoding="utf-8") as f:
            r = dict(DEFAUT, **json.load(f))
    except Exception:
        r = dict(DEFAUT)
    if r["mode"] not in ("cloud", "pc"):
        r["mode"] = "cloud"
    return r


def ecrire(**kw):
    r = lire()
    r.update({k: v for k, v in kw.items() if k in DEFAUT})
    if r["mode"] not in ("cloud", "pc"):
        raise ValueError("mode inconnu")
    tmp = FICHIER + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(r, f, ensure_ascii=False)
    os.replace(tmp, FICHIER)
    return r


def sur_pc():
    return lire()["mode"] == "pc"
