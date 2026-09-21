# -*- coding: utf-8 -*-
"""Patch du proxy 8190 : recherche dans le TEXTE des narrations (Manga Studio v1.83.0, 22/09/2026).

« le chapitre ou Blue sort de son armure » : cherche dans titre + narration de chaque page, sans accents ni
casse, TOUS les mots sur la meme page. Un seul resultat par (chapitre, page) : plusieurs essais racontent la
meme page ; on garde de preference une narration avec voix. Corbeille ignoree. 30 resultats au plus.
Rejouable : python patch_recherche_texte.py <chemin du proxy>. Suppose patch_bibliotheque.py applique.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "def manga_recherche_texte(" in s:
    print("deja patche")
    sys.exit(0)


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


rep('''# --- Narration des chapitres (v1.67.0) -----------------------------------------------''',
    '''# --- Recherche dans le texte des narrations (Manga Studio v1.83.0) --------------------
def _norm_rech(t):
    t = unicodedata.normalize("NFD", t or "")
    t = "".join(c for c in t if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"[^0-9a-z]+", " ", t).strip()


def manga_recherche_texte(q):
    mots = [m for m in _norm_rech(q).split() if len(m) >= 2]
    if not mots:
        return {"items": []}
    racine = os.path.normpath(MANGA_SOURCES)
    vus, out = {}, []
    for slug in sorted(os.listdir(racine)) if os.path.isdir(racine) else []:
        sd = os.path.join(racine, slug)
        if slug.startswith(("_", ".")) or not os.path.isdir(sd):
            continue
        for ch in sorted(os.listdir(sd)):
            nd = os.path.join(sd, ch, "narration")
            if not ch.startswith("ch_") or not os.path.isdir(nd):
                continue
            for tag in sorted(os.listdir(nd)):
                np_ = os.path.join(nd, tag, "narration.json")
                if not os.path.isfile(np_):
                    continue
                try:
                    with open(np_, encoding="utf-8") as f:
                        n = json.load(f)
                except Exception:
                    continue
                for pg in n.get("pages") or []:
                    txt = (pg.get("narration") or "").strip()
                    if not txt or not all(m in _norm_rech(txt) for m in mots):
                        continue
                    cle = (slug + "/" + ch, pg.get("page"))
                    avec_voix = bool(pg.get("audio"))
                    if cle in vus and (vus[cle]["voix"] or not avec_voix):
                        continue
                    i = _norm_rech(txt).find(mots[0])
                    debut = max(0, int(i * len(txt) / max(1, len(_norm_rech(txt)))) - 60)
                    hit = {"dir": slug + "/" + ch, "slug": slug, "chapter": ch[3:], "title": n.get("title") or slug,
                           "tag": tag, "page": pg.get("page"), "voix": avec_voix,
                           "extrait": ("…" if debut else "") + txt[debut:debut + 180] + ("…" if len(txt) > debut + 180 else "")}
                    if cle in vus:
                        out[out.index(vus[cle])] = hit
                    else:
                        out.append(hit)
                    vus[cle] = hit
    out.sort(key=lambda h: not h["voix"])            # ce qui s'ECOUTE d'abord ; les essais sans voix ensuite
    return {"items": out[:30], "total": len(out)}


# --- Narration des chapitres (v1.67.0) -----------------------------------------------''')

rep('''        elif self.path.split("?", 1)[0] == "/manga/costs":''',
    '''        elif self.path.split("?", 1)[0] == "/manga/recherche_texte":      # Manga Studio v1.83.0
            self._json(200, manga_recherche_texte((parse_qs(urlparse(self.path).query).get("q") or [""])[0]))
        elif self.path.split("?", 1)[0] == "/manga/costs":''')

open(p, "w", encoding="utf-8").write(s)
print("patch recherche texte OK")
