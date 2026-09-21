# -*- coding: utf-8 -*-
"""Patch du proxy 8190 : tomes et dates des series (Manga Studio v1.77.0, 21/09/2026).

Suppose patch_bibliotheque.py deja applique (reutilise _RE_SERIE, _manga_src_safe, manga_source_pages).
Rejouable : python patch_tomes.py <chemin du proxy>. Ancres verifiees, sinon ARRET sans rien ecrire.

Sources (verifiees le 21/09) : MangaDex = tome de chaque chapitre (/manga/<id>/aggregate), couvertures par
tome (/cover, uploads.mangadex.org/covers/<id>/<fichier>.512.jpg), annee + statut ; AniList = annee de FIN,
retenue seulement si son annee de DEBUT concorde avec MangaDex (sinon ce n'est peut-etre pas la meme serie).
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "def manga_serie_infos(" in s:
    print("deja patche")
    sys.exit(0)
if "def manga_source_delete(" not in s:
    raise SystemExit("patch_bibliotheque.py doit etre applique avant")


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


# 1) chaque chapitre de la liste porte son tome, et les infos de sa serie
rep('''                        "cover": info["pages"][0]["path"], "pochette": _pochette(slug)})''',
    '''                        "cover": info["pages"][0]["path"], "pochette": _pochette(slug),
                        "tome": _serie_json(slug).get("chapitres", {}).get(_ch_cle(info["chapter"] or ch[3:])),
                        "serie_info": {k: v for k, v in _serie_json(slug).items() if k != "chapitres"} or None})''')

# 2) les fonctions, juste avant le bloc narration
rep('''# --- Narration des chapitres (v1.67.0) -----------------------------------------------''',
    '''# --- Tomes et dates des series (Manga Studio v1.77.0) --------------------------------
# sources/<slug>/serie.json : {mangadex_id, titre_mangadex, annee_debut, annee_fin, statut, tomes_total,
# chapitres: {"301": null, "1": "1"}, couvertures: {"1": "<slug>/tomes/tome_1.jpg"}, maj}
_MDX = "https://api.mangadex.org"
_RE_MDX_CHAP = re.compile(r"mangadex\\.org/chapter/([0-9a-f-]{36})")


def _ch_cle(ch):
    """'1', '1.0', ' 1 ' -> '1' ; '300.5' -> '300.5' : la cle commune aux manifestes et a MangaDex."""
    try:
        f = float(str(ch).strip())
        return str(int(f)) if f == int(f) else str(f)
    except (TypeError, ValueError):
        return str(ch).strip()


def _serie_json(slug):
    sd = _manga_src_safe(slug)
    try:
        with open(os.path.join(sd, "serie.json"), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _get_json(url, body=None, timeout=20):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"User-Agent": "manga-studio", "Accept": "application/json",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def manga_serie_infos(data):
    """Retrouve la serie sur MangaDex (par l'URL exacte d'un chapitre capture sur MangaDex, sinon par le
    titre), en tire le tome de chacun de NOS chapitres, les couvertures de ces tomes, l'annee et le statut."""
    slug = (data.get("slug") or "").strip("/")
    sd = _manga_src_safe(slug) if _RE_SERIE.match(slug) else None
    if not sd or not os.path.isdir(sd):
        return {"error": "serie introuvable"}
    chaps = [manga_source_pages(slug + "/" + c) for c in sorted(os.listdir(sd))
             if c.startswith("ch_") and os.path.isdir(os.path.join(sd, c))]
    chaps = [c for c in chaps if c]
    titre = (data.get("titre") or next((c["title"] for c in chaps if c.get("title")), slug.replace("-", " "))).strip()
    try:
        mid = None
        if not data.get("titre"):                  # titre impose par Quang = on ne se fie qu'a lui
            for c in chaps:
                m = _RE_MDX_CHAP.search(c.get("source_url") or "")
                if m:
                    try:
                        d = _get_json(_MDX + "/chapter/" + m.group(1))["data"]
                        mid = next(r["id"] for r in d["relationships"] if r["type"] == "manga")
                        break
                    except Exception:
                        pass
        if not mid:
            r = _get_json(_MDX + "/manga?limit=1&order%5Brelevance%5D=desc&title=" + quote(titre))
            if r.get("data"):
                mid = r["data"][0]["id"]
        if not mid:
            return {"error": "serie introuvable sur MangaDex : " + titre}
        ma = _get_json(_MDX + "/manga/" + mid)["data"]["attributes"]
        titre_mdx = (ma.get("title") or {}).get("en") or next(iter((ma.get("title") or {}).values()), None)
        agg = _get_json(_MDX + "/manga/" + mid + "/aggregate").get("volumes") or {}
        tome_de = {}
        for vol, v in agg.items():                 # un vrai tome l'emporte sur « none » (autre groupe)
            for ch in (v.get("chapters") or {}):
                if vol != "none":
                    tome_de[_ch_cle(ch)] = vol
        nos = {_ch_cle(c["chapter"]): tome_de.get(_ch_cle(c["chapter"])) for c in chaps}
        fin, statut = None, ma.get("status")
        try:
            q = {"query": "query($s:String){Media(search:$s,type:MANGA){startDate{year} endDate{year}}}",
                 "variables": {"s": titre_mdx or titre}}
            an = (_get_json("https://graphql.anilist.co", q).get("data") or {}).get("Media") or {}
            if (an.get("startDate") or {}).get("year") == ma.get("year"):
                fin = (an.get("endDate") or {}).get("year")
        except Exception:
            pass
        couv, besoin = {}, sorted({v for v in nos.values() if v})
        if besoin:
            par_vol = {}
            for x in _get_json(_MDX + "/cover?limit=100&order%5Bvolume%5D=asc&manga%5B%5D=" + mid).get("data") or []:
                a = x.get("attributes") or {}
                v = a.get("volume")
                if v in besoin and (v not in par_vol or a.get("locale") == "ja"):
                    par_vol[v] = a.get("fileName")
            os.makedirs(os.path.join(sd, "tomes"), exist_ok=True)
            for v, fn in par_vol.items():
                dest = os.path.join(sd, "tomes", "tome_%s.jpg" % re.sub(r"[^0-9A-Za-z.]", "_", v))
                if not os.path.isfile(dest):
                    req = urllib.request.Request("https://uploads.mangadex.org/covers/%s/%s.512.jpg" % (mid, fn),
                                                 headers={"User-Agent": "manga-studio"})
                    with urllib.request.urlopen(req, timeout=30) as r:
                        img = r.read(10 * 1024 * 1024)
                    with open(dest, "wb") as f:
                        f.write(img)
                couv[v] = slug + "/tomes/" + os.path.basename(dest)
    except Exception as e:
        return {"error": "tomes et dates : %s" % e}
    info = {"mangadex_id": mid, "titre_mangadex": titre_mdx, "annee_debut": ma.get("year"), "annee_fin": fin,
            "statut": statut, "tomes_total": ma.get("lastVolume") or None, "chapitres": nos, "couvertures": couv,
            "maj": time.strftime("%Y-%m-%d %H:%M")}
    tmp = os.path.join(sd, "serie.json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=1)
    os.replace(tmp, os.path.join(sd, "serie.json"))
    return dict(info, ok=True)


# --- Narration des chapitres (v1.67.0) -----------------------------------------------''')

# 3) supprimer UNE NARRATION (demande Quang 21/09 23h19 : « ai-je la possibilite de supprimer un audio ? »)
rep('''    pages = [str(x) for x in (data.get("pages") or [])]
    if slug:''',
    '''    pages = [str(x) for x in (data.get("pages") or [])]
    tag = (data.get("narration") or "").strip()
    if tag:                                        # v1.77.0 : {d, narration: tag} = une narration du chapitre
        nd = _narr_dir(d, tag) if d and _RE_TAG.match(tag) else None
        if not nd or not os.path.isdir(nd):
            return {"error": "narration introuvable"}
        occ = _source_occupee(nd)
        if occ:
            return {"error": "impossible pour l'instant : " + occ}
        dest = os.path.join(MANGA_CORBEILLE, time.strftime("%Y%m%d-%H%M%S") + "_" + d.replace("/", "__") + "__" + tag)
        os.makedirs(MANGA_CORBEILLE, exist_ok=True)
        shutil.move(nd, dest)
        return {"ok": True, "quoi": "narration", "corbeille": os.path.relpath(dest, MANGA_SOURCES)}
    if slug:''')

# 4) la route POST
rep('''            elif self.path == "/manga/pochette":               # Manga Studio v1.76.0''',
    '''            elif self.path == "/manga/serie_infos":            # Manga Studio v1.77.0
                self._json(200, manga_serie_infos(data))
            elif self.path == "/manga/pochette":               # Manga Studio v1.76.0''')

open(p, "w", encoding="utf-8").write(s)
print("patch tomes OK")
