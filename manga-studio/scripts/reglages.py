"""Reglage GLOBAL « ou tourne ce qui peut tourner sur le PC » (feuille de route 4-nonies, etape 4-bis, 24/09/2026).

Quang : « un menu simple, ergonomique et tres clair, pour que je repere rapidement si je vais lancer quelque chose en
local ou en cloud […] persistance […] a toi de voir si c'est par chapitre, par manga ou global ».
Choix : GLOBAL, cote serveur (sources/_reglages.json) -- ce qui decide, c'est ce que Quang fait sur son PC a ce
moment-la, pas le manga. Le meme reglage vaut sur le PC, le telephone et la nuit.
  mode « cloud » (defaut) : tout en ligne, comme avant.
  mode « pc »             : voix locale (Chatterbox) + effacement local du texte pose sur le dessin (carte graphique).
L'analyse des pages et le recit restent en ligne dans les deux modes (analyse locale mesuree moins fidele, 24/09).
"""
import json, os, sys

VERSION = "1.3.0"

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.environ.get("MANGA_SOURCES_DIR") or os.path.join(HERE, "..", "sources"))
FICHIER = os.environ.get("MANGA_REGLAGES") or os.path.join(SRC, "_reglages.json")
DEFAUT = {"mode": "cloud", "relais_moderation": False,   # v1.2.0 : relais auto vers l'autre moteur en ligne
          "flou_discretion": True}                       # v1.3.0 : flou de la secondaire hors focus (Quang 25/09 : optionnel)


def _brut():
    try:
        with open(FICHIER, encoding="utf-8") as f:
            r = {k: v for k, v in dict(DEFAUT, **json.load(f)).items() if k in DEFAUT}
    except Exception:
        r = dict(DEFAUT)
    if r["mode"] not in ("cloud", "pc"):
        r["mode"] = "cloud"
    r["relais_moderation"] = r.get("relais_moderation") is True
    r["flou_discretion"] = r.get("flou_discretion") is not False       # v1.3.0 : absent = OUI (comportement d'avant)
    return r


def lire():
    """Le reglage + (v1.1.0, 4-undecies) l'ETALONNAGE des couts/durees, pour que l'app affiche les deux estimations
    ☁ / 🖥 avec les memes chiffres que les lots (GET /manga/reglages rend ce dict tel quel)."""
    r = _brut()
    try:
        sys.path.insert(0, HERE)
        import estimation
        r["etalonnage"] = estimation.etalonnage()
    except Exception as e:                      # l'interrupteur doit marcher meme si l'estimation casse
        r["etalonnage_erreur"] = str(e)[:200]
    return r


def ecrire(**kw):
    r = _brut()
    r.update({k: v for k, v in kw.items() if k in DEFAUT})
    if r["mode"] not in ("cloud", "pc"):
        raise ValueError("mode inconnu")
    if not isinstance(r.get("relais_moderation"), bool):
        raise ValueError("relais_moderation : vrai ou faux")
    if not isinstance(r.get("flou_discretion"), bool):
        raise ValueError("flou_discretion : vrai ou faux")
    tmp = FICHIER + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(r, f, ensure_ascii=False)
    os.replace(tmp, FICHIER)
    return lire()


def sur_pc():
    return _brut()["mode"] == "pc"


def relais_moderation():
    """v1.2.0 : une page refusee par la moderation est-elle reprise TOUTE SEULE par l'autre moteur en ligne ?"""
    return _brut()["relais_moderation"]
