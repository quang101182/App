# -*- coding: utf-8 -*-
"""Patch du proxy 8190 : BIBLIOTHEQUE -- fiche de serie fiable + genres (B1), masquees / ouvertes (B2).
Manga Studio v2.6.0, 23/09/2026 (ROADMAP § 4-quinquies).

B1 -- manga_serie_infos :
  * reutilise le mangadex_id deja connu (serie.json) quand aucun titre n'est impose : un rafraichissement ne peut
    plus faire changer une serie d'identite ;
  * recherche par titre : ne retient QUE le resultat dont un titre ou un titre alternatif correspond EXACTEMENT
    (normalise : casse, accents, ponctuation). Mesure du 23/09 : « Black Jack ni Yoroshiku » -> le 1er resultat de
    MangaDex etait une AUTRE serie, la bonne etait 3e, et la suite exclue de la licence 2e. Sinon : erreur, serie.json
    intact, et les titres proches sont cites pour que Quang puisse imposer le bon ;
  * ajoute genres / themes (noms anglais de MangaDex ; l'app les traduit) et public (publicationDemographic).
B2 -- sources/_bibliotheque.json (PAS serie.json : manga_serie_infos le reecrit en entier) :
  GET /manga/bibliotheque -> {masquees: [slug], ouvertes: {slug: horodatage}}
  POST /manga/bibliotheque {action: masquer | afficher | ouverte, slug}
Rejouable : python patch_bibliotheque.py <chemin du proxy>.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "# v2.6.0 : bibliotheque" in s:
    print("deja patche"); sys.exit(0)


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


# ---------------------------------------------------------------- B1
rep('''    try:
        mid = None
        if not data.get("titre"):                  # titre impose par Quang = on ne se fie qu'a lui''',
    '''    try:
        mid = None
        # v2.6.0 : bibliotheque (B1) -- l'identite deja connue ne change plus a chaque rafraichissement
        if not data.get("titre"):
            mid = _serie_json(slug).get("mangadex_id") or None
        if not mid and not data.get("titre"):      # titre impose par Quang = on ne se fie qu'a lui''')
rep('''        if not mid:
            r = _get_json(_MDX + "/manga?limit=1&order%5Brelevance%5D=desc&title=" + quote(titre))
            if r.get("data"):
                mid = r["data"][0]["id"]
        if not mid:
            return {"error": "serie introuvable sur MangaDex : " + titre}''',
    '''        if not mid:
            # v2.6.0 (B1) : le TITRE EXACT, pas le 1er resultat (« Black Jack ni Yoroshiku » -> une autre serie en 1er)
            r = _get_json(_MDX + "/manga?limit=10&order%5Brelevance%5D=desc&title=" + quote(titre))
            proches = []
            for x in r.get("data") or []:
                a = x.get("attributes") or {}
                noms = [t for d_ in [a.get("title") or {}] + list(a.get("altTitles") or []) for t in d_.values() if t]
                if any(_norm_titre(t) == _norm_titre(titre) for t in noms):
                    mid = x["id"]
                    break
                proches.append(next(iter((a.get("title") or {}).values()), "?"))
            if not mid:
                return {"error": "aucune serie MangaDex au titre exact « %s »%s" % (
                    titre, (" -- titres proches : " + " ; ".join(proches[:5])) if proches else "")}''')
rep('''    info = {"mangadex_id": mid, "titre_mangadex": titre_mdx, "titres_alt": alt[:30],''',
    '''    tags = [t.get("attributes") or {} for t in (ma.get("tags") or [])]
    nom_tag = lambda a: (a.get("name") or {}).get("en") or next(iter((a.get("name") or {}).values()), None)
    info = {"mangadex_id": mid, "titre_mangadex": titre_mdx, "titres_alt": alt[:30],
            "genres": sorted(filter(None, (nom_tag(a) for a in tags if a.get("group") == "genre"))),
            "themes": sorted(filter(None, (nom_tag(a) for a in tags if a.get("group") == "theme"))),
            "public": ma.get("publicationDemographic") or None,''')
rep('''def manga_serie_infos(data):''',
    '''def _norm_titre(t):
    """Casse, accents et ponctuation ignores ; les ecritures non latines (kana, hangul...) sont gardees telles quelles."""
    import unicodedata
    t = "".join(c for c in unicodedata.normalize("NFKD", t or "") if not unicodedata.combining(c))
    return re.sub(r"[\\W_]+", "", t.lower())


def manga_serie_infos(data):''')

# ---------------------------------------------------------------- B2
rep('''# --- Renommer une serie (Manga Studio v1.80.0) ---------------------------------------''',
    '''# --- Bibliotheque personnelle (Manga Studio v2.6.0, B2) --------------------------------
MANGA_BIBLIO = os.path.join(MANGA_SOURCES, "_bibliotheque.json")
_BIBLIO_LOCK = threading.Lock()


def _biblio_lire():
    try:
        with open(MANGA_BIBLIO, encoding="utf-8") as f:
            b = json.load(f)
    except Exception:
        b = {}
    return {"masquees": [x for x in b.get("masquees") or [] if isinstance(x, str)],
            "ouvertes": {k: v for k, v in (b.get("ouvertes") or {}).items() if isinstance(v, (int, float))}}


def manga_bibliotheque(data=None):
    if not data:
        return _biblio_lire()
    slug, action = (data.get("slug") or "").strip("/"), data.get("action") or ""
    if not _RE_SERIE.match(slug) or not os.path.isdir(_manga_src_safe(slug) or ""):
        return {"error": "serie introuvable"}
    if action not in ("masquer", "afficher", "ouverte"):
        return {"error": "action inconnue"}
    with _BIBLIO_LOCK:
        b = _biblio_lire()
        if action == "masquer" and slug not in b["masquees"]:
            b["masquees"].append(slug)
        elif action == "afficher":
            b["masquees"] = [x for x in b["masquees"] if x != slug]
        elif action == "ouverte":
            b["ouvertes"][slug] = int(time.time())
        tmp = MANGA_BIBLIO + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(b, f, ensure_ascii=False, indent=1)
        os.replace(tmp, MANGA_BIBLIO)
    return dict(b, ok=True)


# --- Renommer une serie (Manga Studio v1.80.0) ---------------------------------------''')
rep('''        elif self.path.split("?", 1)[0] == "/manga/profil_defaut":         # Manga Studio v2.4.0''',
    '''        elif self.path.split("?", 1)[0] == "/manga/bibliotheque":          # Manga Studio v2.6.0
            self._json(200, manga_bibliotheque())
        elif self.path.split("?", 1)[0] == "/manga/profil_defaut":         # Manga Studio v2.4.0''')
rep('''            elif self.path == "/manga/profil_defaut":          # Manga Studio v2.4.0''',
    '''            elif self.path == "/manga/bibliotheque":           # Manga Studio v2.6.0
                self._json(200, manga_bibliotheque(data))
            elif self.path == "/manga/profil_defaut":          # Manga Studio v2.4.0''')
open(p, "w", encoding="utf-8").write(s)
print("patche")
