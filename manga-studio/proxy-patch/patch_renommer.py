# -*- coding: utf-8 -*-
"""Patch du proxy 8190 : renommer une serie (Manga Studio v1.80.0, 21/09/2026).

Le dossier d'une serie = slugify(titre) de manga-fetch. Changer le TITRE sans le DOSSIER ferait fonder a la
prochaine capture (sous le nouveau titre) un second dossier pour la meme serie. On renomme donc les deux :
titre + slug dans chaque manifest.json, champ « chapitre » des narrations, puis le dossier lui-meme.
Rejouable : python patch_renommer.py <chemin du proxy>. Suppose patch_bibliotheque.py applique.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "def manga_serie_renommer(" in s:
    print("deja patche")
    sys.exit(0)
if "def manga_source_delete(" not in s:
    raise SystemExit("patch_bibliotheque.py doit etre applique avant")


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


rep('''# --- Narration des chapitres (v1.67.0) -----------------------------------------------''',
    '''# --- Renommer une serie (Manga Studio v1.80.0) ---------------------------------------
def _slugify_mf(titre):
    """COPIE EXACTE de manga_fetch.slugify : un ecart = la prochaine capture fonde un 2e dossier."""
    s = re.sub(r"[^a-z0-9]+", "-", (titre or "").lower()).strip("-")
    return s[:60] or "sans-titre"


def _ecrire_json(chemin, obj):
    tmp = chemin + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, chemin)


def manga_serie_renommer(data):
    slug = (data.get("slug") or "").strip("/")
    titre = " ".join((data.get("titre") or "").split())[:120]
    sd = _manga_src_safe(slug) if _RE_SERIE.match(slug) else None
    if not sd or not os.path.isdir(sd):
        return {"error": "serie introuvable"}
    if not titre:
        return {"error": "titre vide"}
    occ = _source_occupee(sd)
    if occ:
        return {"error": "impossible pour l'instant : " + occ}
    nouveau = _slugify_mf(titre)
    cible = _manga_src_safe(nouveau)
    if nouveau != slug and (not cible or os.path.exists(cible)):
        return {"error": "une autre serie porte deja ce nom de dossier (%s)" % nouveau}
    n = 0
    for ch in sorted(os.listdir(sd)):
        cd = os.path.join(sd, ch)
        mp = os.path.join(cd, "manifest.json")
        if not ch.startswith("ch_") or not os.path.isfile(mp):
            continue
        with open(mp, encoding="utf-8") as f:
            man = json.load(f)
        man["title"], man["slug"] = titre, nouveau
        _ecrire_json(mp, man)
        n += 1
        nd = os.path.join(cd, "narration")
        for tag in (os.listdir(nd) if os.path.isdir(nd) else []):
            np_ = os.path.join(nd, tag, "narration.json")
            if os.path.isfile(np_):
                try:
                    with open(np_, encoding="utf-8") as f:
                        nar = json.load(f)
                    nar["chapitre"] = nouveau + "/" + ch
                    nar["title"] = titre
                    _ecrire_json(np_, nar)
                except Exception:
                    pass                            # une narration illisible ne bloque pas le renommage
    sj = os.path.join(sd, "serie.json")            # couvertures des tomes : chemins prefixes par le slug
    if nouveau != slug and os.path.isfile(sj):
        try:
            with open(sj, encoding="utf-8") as f:
                inf = json.load(f)
            inf["couvertures"] = {k: nouveau + v[len(slug):] if v.startswith(slug + "/") else v
                                  for k, v in (inf.get("couvertures") or {}).items()}
            _ecrire_json(sj, inf)
        except Exception:
            pass
    if nouveau != slug:
        os.rename(sd, cible)
    return {"ok": True, "slug": nouveau, "ancien": slug, "titre": titre, "chapitres": n}


# --- Narration des chapitres (v1.67.0) -----------------------------------------------''')

rep('''            elif self.path == "/manga/pochette":               # Manga Studio v1.76.0''',
    '''            elif self.path == "/manga/serie_renommer":         # Manga Studio v1.80.0
                self._json(200, manga_serie_renommer(data))
            elif self.path == "/manga/pochette":               # Manga Studio v1.76.0''')

open(p, "w", encoding="utf-8").write(s)
print("patch renommer OK")
