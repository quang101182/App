#!/usr/bin/env python3
"""manga-fetch v0.1.0 — sourcing de chapitres pour Manga Studio (narration audio).

Canaux (décisions mesurées le 21/09/2026, cf README) :
  1. mangadex  : download direct via l'API publique (séries non licenciées).
  2. capture   : TOUT lecteur web affiché dans la fenêtre Edge dédiée (CDP, port 9223).
  3. import    : images / archives CBZ déjà sur disque.

Sortie normalisée :  <out>/<slug>/ch_<chapitre>/page_NNN.<ext>  +  manifest.json
Le dossier sources/ est gitignoré : les images téléchargées ne sont JAMAIS versionnées.

Usage :
    python manga_fetch.py search "solo leveling"
    python manga_fetch.py chapters <manga_id> [--lang fr]
    python manga_fetch.py download <manga_id> [--chapter N | --last K | --all] [--lang fr]
    python manga_fetch.py capture [--tab mangadex] --title "Titre" --chapter N
    python manga_fetch.py import <dossier|fichier.cbz> --title "Titre" --chapter N
    python manga_fetch.py verify <dossier chapitre>
    python manga_fetch.py launch-edge
"""

import argparse
import base64
import datetime
import hashlib
import json
import os
import re
import shutil
import sys
import time
import zipfile

import requests

VERSION = "0.8.4"
# ⚠ ASCII pur, JAMAIS d'em-dash ni d'accent : les headers HTTP sont encodés latin-1
# (crash UnicodeEncodeError mesuré le 21/09 — ne pas "embellir" cette chaîne).
UA = f"manga-fetch/{VERSION} (Manga Studio sourcing, usage personnel)"
MDX_API = "https://api.mangadex.org"
# v0.6.5 (24/09, compartiment secret S3) : l'espace prive a SA fenetre (port, profil, journaux, place) ; sans ces
# variables, rien ne change pour l'espace normal.
EDGE_PORT = int(os.environ.get("MANGA_CAPTURE_PORT") or 9223)
EDGE_CDP = "http://localhost:%d" % EDGE_PORT
EDGE_PROFILE = os.environ.get("MANGA_CAPTURE_PROFIL") or os.path.join(os.environ.get("LOCALAPPDATA", "."), "manga-fetch-edge")
DATA_DIR = os.environ.get("MANGA_CAPTURE_DONNEES") or os.path.join(os.environ.get("LOCALAPPDATA", "."), "manga-fetch")
LOG_FILE = os.path.join(DATA_DIR, "fetch.log")
LOG_EVT = os.path.join(DATA_DIR, "events.log")
SERIE_FILET = 300        # v0.8.0 : dernier filet par lancement, tous modes (remplace le plafond de 50 ; Quang 25/09 23h51)
SERIE_SAUT_MAX = 10      # v0.8.0 : un « suivant » qui saute plus loin = lien suspect -> arret de securite
SERIE_PAUSE_MS = 3000    # v0.8.0 : politesse entre deux chapitres (Quang 25/09 23h42 : « ne pas spammer le site »)
ARRET_FICHIER = os.path.join(DATA_DIR, "arret_demande.json")   # v0.7.6 : « ⏹ Arrêter après ce chapitre » (pose par l'app)
PLAFOND_TOURS_PAGER, PLAFOND_S_PAGER = 3000, 3600   # v0.6.3 : garde-fous page par page (~1000 pages, 1 h)
PLAFOND_PAS_ABSOLU = 6000   # v0.6.2 : ~5,3 millions de px a 1273 px d'ecran (~2 h) -- garde-fou, jamais la regle  # journal DÉTAILLÉ (demande Quang 18/18)
DEFAULT_OUT = os.path.normpath(os.environ.get("MANGA_SOURCES_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sources"))
IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".avif"}


# --------------------------------------------------------------------------- utilitaires

def log_event(action: str, **kw) -> None:
    """Journal jsonl persistant (%LOCALAPPDATA%/manga-fetch/fetch.log) — 1 ligne par action."""
    os.makedirs(DATA_DIR, exist_ok=True)
    ligne = {"t": datetime.datetime.now().isoformat(timespec="seconds"), "action": action}
    ligne.update(kw)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(ligne, ensure_ascii=False) + "\n")


def log_evt(categorie: str, message: str, **kw) -> None:
    """Journal DÉTAILLÉ lisible (%LOCALAPPDATA%/manga-fetch/events.log) — une ligne
    horodatée par événement : choix d'onglet, mode, pages collectées/écartées, fins.
    Rotation simple à 1 Mo (garde .1). Ne doit JAMAIS faire échouer l'appelant."""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        if os.path.exists(LOG_EVT) and os.path.getsize(LOG_EVT) > 1_000_000:
            os.replace(LOG_EVT, LOG_EVT + ".1")
        ligne = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + f" [{categorie}] {message}"
        if kw:
            ligne += " " + " ".join(f"{k}={v}" for k, v in kw.items())
        with open(LOG_EVT, "a", encoding="utf-8") as f:
            f.write(ligne + "\n")
    except OSError:
        pass


def slugify(titre: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (titre or "").lower()).strip("-")
    return s[:60] or "sans-titre"


def cle_normale(titre: str) -> str:
    """Clé d'identité d'un titre, INSENSIBLE aux espaces/tirets/majuscules :
    'One Punch Man', 'One-Punch-Man', 'OnePunchMan' → 'onepunchman'
    (demande Quang 18:39 — sinon trois dossiers pour le même manga)."""
    return re.sub(r"[^a-z0-9]", "", (titre or "").lower())


def resoudre_slug(out: str, titre: str) -> str:
    """Slug du titre — RÉUTILISE un dossier existant de même clé : 'OnePunchMan'
    retrouve le dossier 'one-punch-man' déjà créé, au lieu d'en fonder un second."""
    racine = os.path.normpath(out)
    if os.path.isdir(racine):
        cle = cle_normale(titre)
        for d in os.listdir(racine):
            if os.path.isdir(os.path.join(racine, d)) and cle_normale(d) == cle:
                return d
    return slugify(titre)


def ext_depuis_magic(data: bytes) -> str:
    if data[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if data[:4] == b"\x89PNG":
        return ".png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    if data[:3] == b"GIF":
        return ".gif"
    return ".bin"  # inconnu : on garde, le banc/verify le signalera


def save_page(dossier: str, idx: int, data: bytes) -> str:
    os.makedirs(dossier, exist_ok=True)
    nom = f"page_{idx:03d}{ext_depuis_magic(data)}"
    with open(os.path.join(dossier, nom), "wb") as f:
        f.write(data)
    return nom


def write_manifest(dossier: str, *, slug: str, title: str, chapter: str, source: str,
                   source_url: str, pages: list, notes: list | None = None) -> str:
    manifest = {
        "slug": slug, "title": title, "chapter": str(chapter), "source": source,
        "source_url": source_url, "captured_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "pages": pages, "notes": notes or [],
    }
    p = os.path.join(dossier, "manifest.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    return p


def chap_dir(out: str, title: str, chapter) -> str:
    return os.path.join(out, resoudre_slug(out, title), f"ch_{str(chapter).replace('/', '-')}")


# --------------------------------------------------------------------------- canal 1 : MangaDex

def md_get(path: str, params: dict | None = None):
    r = requests.get(MDX_API + path, params=params, headers={"User-Agent": UA}, timeout=30)
    r.raise_for_status()
    return r.json()


def md_search(requete: str) -> list[dict]:
    """Recherche par titre. Retourne [{id, titre, langues, fr}] triés par followedCount."""
    r = md_get("/manga", {"title": requete, "limit": 12,
                          "order[followedCount]": "desc",
                          "contentRating[]": ["safe", "suggestive"]})
    out = []
    for m in r["data"]:
        t = m["attributes"]["title"]
        nom = t.get("fr") or t.get("en") or t.get("ja") or next(iter(t.values()), "?")
        langues = m["attributes"].get("availableTranslatedLanguages", [])
        out.append({"id": m["id"], "titre": nom, "langues": langues, "fr": "fr" in langues})
    return out


def md_chapters(manga_id: str, lang: str) -> list[dict]:
    """Chapitres HÉBERGÉS (externalUrl exclu : ce sont des liens sortants, ex. MANGA Plus)."""
    chapitres, offset = [], 0
    while True:
        r = md_get("/chapter", {"manga": manga_id, "translatedLanguage[]": lang,
                                "order[chapter]": "desc", "limit": 100, "offset": offset})
        batch = [c for c in r["data"] if not c["attributes"].get("externalUrl")]
        chapitres.extend(batch)
        total = r["total"]
        offset += 100
        if offset >= total or not r["data"]:
            break
    return chapitres


def md_download(manga_id: str, args) -> int:
    chapitres = md_chapters(manga_id, args.lang)
    if not chapitres:
        print(f"Aucun chapitre hébergé en '{args.lang}'. Essaie --lang en.")
        return 1
    # sélection : --all, --chapter N, ou --last K (défaut 1) sur les plus récents
    if args.all:
        sel = chapitres
    elif args.chapter is not None:
        sel = [c for c in chapitres if c["attributes"].get("chapter") == str(args.chapter)]
        if not sel:
            print(f"Chapitre {args.chapter} introuvable en '{args.lang}'. "
                  f"Dispo : {', '.join((c['attributes'].get('chapter') or '?') for c in chapitres[:10])}")
            return 1
    else:
        sel = chapitres[: max(1, args.last)][::-1]  # du plus ancien au plus récent

    try:
        titres = md_get("/manga/" + manga_id)["data"]["attributes"]["title"]
    except Exception as e:
        print(f"Titre introuvable pour {manga_id} ({type(e).__name__}) — vérifie l'id via 'search'.")
        return 1
    titre = titres.get("fr") or titres.get("en") or next(iter(titres.values()), manga_id)
    total_pages = 0
    for c in sel:
        a = c["attributes"]
        num = a.get("chapter") or ""
        # chapitres sans numéro (extras, oneshots) : suffixe par id court, sinon ils
        # s'écrasent tous dans ch_0 (review Groq 21/09 — perte de données réelle)
        cle = num if str(num).strip() else f"x-{c['id'][:6]}"
        dest = chap_dir(args.out, titre, cle)
        if os.path.exists(os.path.join(dest, "manifest.json")) and not args.force:
            print(f"ch_{cle} : déjà présent, ignoré (--force pour retélécharger)")
            continue
        print(f"ch_{cle} ({a['translatedLanguage']}, {a.get('pages', '?')} pages)...")
        r = md_get(f"/at-home/server/{c['id']}")
        base, hsh, files = r["baseUrl"], r["chapter"]["hash"], r["chapter"]["data"]
        pages_meta = []
        for i, fn in enumerate(files, 1):
            img = requests.get(f"{base}/data/{hsh}/{fn}", headers={"User-Agent": UA}, timeout=60).content
            nom = save_page(dest, i, img)
            pages_meta.append({"file": nom, "bytes": len(img)})
            total_pages += 1
            time.sleep(0.4)  # politesse : l'at-home de MangaDex est partagé
        write_manifest(dest, slug=slugify(titre), title=titre, chapter=cle,
                       source="mangadex", source_url=f"https://mangadex.org/chapter/{c['id']}",
                       pages=pages_meta)
        print(f"  -> {dest} ({len(files)} pages)")
    log_event("download", manga_id=manga_id, lang=args.lang, chapitres=len(sel), pages=total_pages)
    print(f"OK : {len(sel)} chapitre(s), {total_pages} pages au total.")
    return 0


# --------------------------------------------------------------------------- canal 2 : capture


# --------------------------------------------------------------------------- capture en série (v0.4.0)
# Vérifié site par site le 22/09/2026 AVANT d'écrire ce code :
#  - MangaDex : le lecteur passe seul au suivant, mais on ne s'y fie pas (il peut changer de langue
#    ou de groupe) : l'API publique donne les chapitres de la série DANS LA LANGUE du chapitre lu.
#  - MANGA Plus : aucun passage automatique ; le bouton « To Chapter #002 » du lecteur ne réagit pas
#    à un clic scripté. La page de la série (/titles/<id>) liste les chapitres GRATUITS, et un clic
#    sur l'un d'eux ouvre /viewer/<id> (Claymore : #001-#004 puis #155 seulement).
# Règle commune : le plus petit numéro > au chapitre courant. Un TROU (ex. 4 -> 155) arrête la
# série, sauf si « jusqu'au ch. Y » le couvre (borne donnée explicitement).

def _num(s) -> float:
    try:
        return float(str(s).replace(",", "."))
    except ValueError:
        return -1.0


def _format_num(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else str(x)


RE_FINAL = re.compile(r"(?<![a-z])(final(?:e)?|the end|end|fin|completed?|termin[ée]e?)(?![a-z])", re.I)
RE_FIN_SAISON = re.compile(r"(season|saison|part|partie|arc|vol(?:ume)?|tome)[\s_.-]*\d*[\s_.-]*(final(?:e)?|end|fin)", re.I)


def marque_final(page) -> str:
    """v0.7.5 : le dernier chapitre porte-t-il « Final » / « End » / « Fin » (titre de l'onglet, adresse) ? Une fin de SAISON,
    de partie ou de tome ne compte pas (« chapter-40-season-1-finale »). Rend le mot trouve, ou ""."""
    try:
        brut = [page.title() or "", re.sub(r"[-_/]+", " ", page.url or "")]
    except Exception:
        return ""
    # seulement ce qui SUIT le numero du chapitre (« Chap 54 - Final ») : un NOM de serie « The End of Days » ne compte pas
    suites = []
    for t in brut:
        m = re.search(r"(?<![a-z])(chap(?:ter|itre)?|ch|ep(?:isode)?)\.?\s*\d+(?:[.,]\d+)?", t, re.I)
        if m:
            suites.append(t[m.end():])
    texte = " ".join(suites)
    if RE_FIN_SAISON.search(texte):
        return ""
    m = RE_FINAL.search(texte)
    return m.group(1) if m else ""


def _empreintes(dossier: str) -> set:
    """v0.8.0 : empreintes (sha1) des images d'un chapitre."""
    e = set()
    try:
        for f in os.listdir(dossier):
            if os.path.splitext(f)[1].lower() in IMG_EXTS:
                with open(os.path.join(dossier, f), "rb") as fh:
                    e.add(hashlib.sha1(fh.read()).hexdigest())
    except OSError:
        pass
    return e


def _meme_contenu(out: str, title: str, precedent: str, courant: str):
    """v0.8.0 : le chapitre `courant` reprend-il les images du `precedent` (site qui ressert la meme page) ?
    Retourne une explication courte, ou None. Seuil : >= 80 % des images du courant deja dans le precedent."""
    a = _empreintes(chap_dir(out, title, courant))
    if len(a) < 2:
        return None
    b = _empreintes(chap_dir(out, title, precedent))
    communes = len(a & b)
    return f"{communes}/{len(a)} images identiques" if communes >= 0.8 * len(a) else None


def _mettre_de_cote(dossier: str, pourquoi: str):
    """v0.8.0 : un chapitre faux est RENOMME a cote (« _<pourquoi>_<nom>_<t> »), jamais efface. Nom du dossier, ou None."""
    if not os.path.isdir(dossier):
        return None
    cible = os.path.join(os.path.dirname(dossier), f"_{pourquoi}_{os.path.basename(dossier)}_{int(time.time())}")
    try:
        os.rename(dossier, cible)
        return os.path.basename(cible)
    except OSError:
        return None


def _choisir_suivant(dispo: dict, courant: str, jusqua, entiers: bool = False):
    """dispo = {numéro (str) : cible}. Retourne (numéro, cible, None) ou (None, None, raison)."""
    c = _num(courant)
    # v0.4.1 : « ignorer les chapitres intermédiaires » (Quang 22/09 14h47 : pas de 298.5 entre 298 et 299)
    apres = sorted((n for n in dispo if _num(n) > c and (not entiers or _num(n).is_integer())), key=_num)
    if not apres:
        return None, None, f"aucun chapitre après le {courant} sur ce site"
    n = apres[0]
    if jusqua is not None and _num(n) > jusqua:
        return None, None, f"le chapitre suivant ({n}) dépasse la borne demandée ({_format_num(jusqua)})"
    if jusqua is None and _num(n) > int(c) + 1:
        return None, None, (f"le chapitre {_format_num(int(c) + 1)} n'est pas disponible sur ce site "
                            f"(le suivant proposé est le {n})")
    return n, dispo[n], None


def md_chapitres_serie(chapter_uuid: str):
    """({numéro : uuid}, langue) des chapitres de la série, dans la langue du chapitre donné."""
    info = md_get(f"/chapter/{chapter_uuid}")["data"]
    lang = info["attributes"].get("translatedLanguage") or "en"
    manga = next(r["id"] for r in info["relationships"] if r["type"] == "manga")
    agg = md_get(f"/manga/{manga}/aggregate", {"translatedLanguage[]": lang})
    dispo = {}
    for vol in (agg.get("volumes") or {}).values():
        for num, ch in (vol.get("chapters") or {}).items():
            if _num(num) >= 0 and ch.get("id"):
                dispo.setdefault(num, ch["id"])
    return dispo, lang


def _url_chapitre(u: str) -> str:
    """Adresse d'un chapitre sans la page ni l'ancre. v0.5.2 : sur webtoons.com, le chapitre EST dans la requete
    (viewer?title_no=T&episode_no=N) -- la couper rendait l'enchainement impossible et source_url inutilisable."""
    u = u.split("#")[0]
    return u if "webtoons.com/" in u else u.split("?")[0]


# v0.6.0 (23/09/2026, manga-scantrad.io, decision Quang 23h27) : une serie y melange des VOLUMES ENTIERS (.../vol-1/ :
# 193 bandes) et des CHAPITRES (.../vol-16-chapitre-179-5/). Numerotation : un volume entier = « ch. N » (N = son numero),
# un chapitre garde SON numero (179.5). L'enchainement suit l'ordre du site : vol-0 ... vol-15, puis 179.5 ... 200.
RE_VOL = re.compile(r"^vol-(\d+)(?:-(?:chapitre|chapter|ch)-(\d+)(?:-(\d+))?)?$", re.I)


def _vol_cle(slug: str):
    """slug -> (cle de tri, numero affiche) ; None si le slug n'est pas de cette forme."""
    m = RE_VOL.match(slug)
    if not m:
        return None
    vol = int(m.group(1))
    if m.group(2) is None:
        return (vol, -1.0), _format_num(vol)                         # volume entier : avant ses chapitres
    n = float(m.group(2) + ("." + m.group(3) if m.group(3) else ""))
    return (vol, n), _format_num(n)


def vol_suivant(slugs, courant_slug: str, jusqua=None, entiers: bool = False):
    """Parmi les slugs du site (ordre quelconque), le suivant de courant_slug -> (numero, slug, None) ou (None, None, raison)."""
    connus = sorted({s for s in slugs if _vol_cle(s)}, key=lambda s: _vol_cle(s)[0])
    if courant_slug not in connus:
        return None, None, "chapitre courant introuvable dans la liste du site (%s)" % courant_slug
    for s in connus[connus.index(courant_slug) + 1:]:
        num = _vol_cle(s)[1]
        if entiers and not _num(num).is_integer():
            continue
        if jusqua is not None and _num(num) > jusqua:
            return None, None, "le chapitre suivant (%s) dépasse la borne demandée (%s)" % (num, _format_num(jusqua))
        return num, s, None
    return None, None, "aucun volume ni chapitre après « %s » sur ce site" % courant_slug


def enchainement_possible(url: str):
    """v0.6.8 (24/09) : ce site permet-il d'enchainer les chapitres ? Memes formats que chapitre_suivant() ci-dessous,
    et meme reponse que capEnchainement() dans manga_studio.html (banc scripts/test_enchainement.py).
    « chapter-N » = possible si la page liste les autres chapitres (verifie au moment du passage)."""
    url = url or ""
    if re.search(r"mangadex\.org/chapter/[0-9a-f-]{36}", url): return True, "MangaDex (même langue)"
    if "mangaplus.shueisha.co.jp/viewer/" in url: return True, "MANGA Plus (chapitres gratuits)"
    if "webtoons.com/" in url and "title_no=" in url: return True, "WEBTOON"
    if re.match(r"(https?://[^?#]+?/)(vol-\d+(?:-(?:chapitre|chapter|ch)-\d+(?:-\d+)?)?)/?(?:[?#].*)?$", url, re.I):
        return True, "volumes « vol-N »"
    if re.match(r"(https?://[^?#]+?/)(chapter|chapitre|ch)[-_/](\d+(?:[.-]\d+)?)/?(?:[?#].*)?$", url, re.I):
        return True, "adresses « chapter-N »"          # v0.7.2 : aussi « chapter/N » (site de la secondaire, 25/09)
    return False, ""


def _suivant_par_page(page, url_chapitre: str, courant: str, jusqua, entiers: bool = False):
    """v0.7.0 (Quang 24/09 19h10 : « si tu es sur de pouvoir de maniere fiable leur apprendre a suivre »). DERNIER
    recours, pour les sites dont l'adresse ne se devine pas (identifiant interne). Deux reperes lus DANS la page :
      1. une LISTE DEROULANTE des chapitres -- retenue seulement si elle CONTIENT le chapitre en cours (sinon ce n'est
         pas elle) ; le suivant est choisi comme partout (_choisir_suivant : borne, intermediaires) ;
      2. sinon un lien « chapitre suivant » (rel=next ou texte explicite) vers une AUTRE page du meme site ;
         numero = courant + 1.
    Le passage ne compte que si l'adresse a VRAIMENT change. Retourne (numero, None), (None, raison) ou None (rien)."""
    if page.url.split("#")[0] != url_chapitre.split("#")[0]:
        page.goto(url_chapitre, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(3000)
    avant = page.url.split("#")[0]
    listes = page.evaluate(r"""() => [...document.querySelectorAll('select')].map((s, i) => {
        const o = [...s.options].map(x => [((x.text || '').match(/(\d+(?:[.,]\d+)?)/) || [])[1] || null, x.value]);
        return {i, o: o.filter(x => x[0] !== null && x[1]), n: s.options.length}; })
        .filter(s => s.n >= 3 && s.o.length >= s.n * 0.8)""")
    for s in listes:
        dispo = {}
        for num, val in s["o"]:
            dispo.setdefault(_format_num(float(num.replace(",", "."))), val)
        if _format_num(_num(courant)) not in dispo:
            continue
        n, val, raison = _choisir_suivant(dispo, courant, jusqua, entiers)
        if n is None:
            return None, raison + " (liste des chapitres de la page)"
        # 1-a (24/09) : l'option du chapitre EN COURS porte l'identifiant qui figure dans l'adresse (liste cachee pilotee
        # par un widget : changer sa valeur ne declenche rien, constate). On remplace cet identifiant -- et le numero
        # « Chapitre-N » s'il y est -- par ceux du suivant ; valide seulement si la page d'arrivee porte le nouvel id.
        v_cour = dispo[_format_num(_num(courant))]
        if len(str(v_cour)) >= 4 and str(v_cour) in avant:
            cible = avant.replace(str(v_cour), str(val))
            cible = re.sub(r"(?i)(chapitre|chapter|ch)([-_])" + re.escape(_format_num(_num(courant))) + r"(?=\D)",
                           lambda m: m.group(1) + m.group(2) + n, cible, count=1)
            page.goto(cible, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(2500)
            if str(val) in page.url and page.url.split("#")[0] != avant:
                return n, None
            return None, "l'adresse du chapitre %s (construite depuis la liste de la page) ne mène pas au bon chapitre" % n
        page.evaluate("([i, v]) => { const s = document.querySelectorAll('select')[i]; s.value = v;"
                      " s.dispatchEvent(new Event('input', {bubbles: true})); s.dispatchEvent(new Event('change', {bubbles: true})); }",
                      [s["i"], val])
        for _ in range(30):
            page.wait_for_timeout(500)
            if page.url.split("#")[0] != avant:
                page.wait_for_load_state("domcontentloaded")
                page.wait_for_timeout(2000)
                return n, None
        return None, "la liste des chapitres de la page n'a pas ouvert le chapitre %s" % n
    lien = page.evaluate(r"""(avant) => { const h = location.host;
        const ok = a => a && a.href && new URL(a.href).host === h && a.href.split('#')[0] !== avant;
        const r = document.querySelector('a[rel~=next]'); if (ok(r)) return r.href;
        const a = [...document.querySelectorAll('a[href]')].find(x => ok(x) &&
            /^(chapitre suivant|chap(\.|itre)? suiv(\.|ant)|next chapter|next ch(\.|apter)?)\b/i.test((x.innerText || x.title || '').trim()));
        return a ? a.href : null; }""", avant)
    if not lien:
        return _suivant_par_bouton(page, avant, courant, jusqua, entiers)       # v0.7.2
    n = _format_num(int(_num(courant)) + 1)
    if jusqua is not None and _num(n) > jusqua:
        return None, f"le chapitre suivant ({n}) dépasse la borne demandée ({_format_num(jusqua)})"
    page.goto(lien, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(2000)
    return (n, None) if page.url.split("#")[0] != avant else (None, "le lien « chapitre suivant » n'a mené nulle part")


def _suivant_par_bouton(page, avant: str, courant: str, jusqua, entiers: bool = False):
    """v0.7.2 (un site de la secondaire, 25/09) : un BOUTON (ou lien sans adresse) « NEXT Ch. 2 » / « Suivant chap. 2 ». On ne le
    touche que s'il ANNONCE un numero ; on clique, on attend une autre adresse, et on VERIFIE que l'arrivee porte ce
    numero (adresse ou titre). Chapitres intermediaires (2.5) sautes si « entiers ». Aucun repere : None (le dire)."""
    for _ in range(5):                                  # au plus 5 intermediaires sautes d'affilee
        cible = page.evaluate(r"""() => {
            const txt = e => (e.innerText || e.getAttribute('aria-label') || e.title || '').replace(/\s+/g, ' ').trim();
            const re = /^(next|suivant|chapitre suivant|next chapter)\b.*?\b(?:ch(?:ap(?:ter|itre)?)?\.?|chapitre|chapter|#)\s*(\d+(?:[.,]\d+)?)/i;
            const e = [...document.querySelectorAll('button, a, [role=button]')].find(x => re.test(txt(x)) && !x.disabled
                && x.getAttribute('aria-disabled') !== 'true');
            if (!e) return null;
            e.setAttribute('data-mf-suivant', '1');
            return txt(e).match(re)[2].replace(',', '.'); }""")
        if not cible:
            return None
        n = _format_num(float(cible))
        if _num(n) <= _num(courant):
            return None, "le bouton « suivant » annonce le chapitre %s, pas après le %s" % (n, courant)
        if jusqua is not None and _num(n) > jusqua:
            return None, f"le chapitre suivant ({n}) dépasse la borne demandée ({_format_num(jusqua)})"
        page.click("[data-mf-suivant]")
        for _ in range(40):
            page.wait_for_timeout(500)
            if page.url.split("#")[0] != avant:
                break
        else:
            return None, "le bouton « suivant » (ch. %s) n'a ouvert aucune autre page" % n
        page.wait_for_load_state("domcontentloaded"); page.wait_for_timeout(2500)
        num = re.escape(n)
        if not (re.search(r"(?:chapter|chapitre|ch|episode)[-_/ ]?0*" + num + r"(?:\D|$)", page.url, re.I)
                or re.search(r"(?:chapter|chapitre|ch\.?|episode|#)\s*0*" + num + r"(?:\D|$)", page.title() or "", re.I)):
            return None, "le bouton « suivant » a mené à une page qui ne porte pas le chapitre %s (%s)" % (n, page.url)
        if entiers and float(n) != int(float(n)):
            courant, avant = n, page.url.split("#")[0]            # intermediaire : on passe au suivant
            continue
        return n, None
    return None, "trop de chapitres intermédiaires d'affilée"


SUIVANT_ESSAIS, SUIVANT_PAUSE_MS = 3, 15000


def _erreur_passagere(e) -> bool:
    """v0.8.4 : un delai depasse / une coupure reseau (le site ralentit un instant) -- pas une erreur de logique."""
    t = type(e).__name__ + " " + str(e)
    return "Timeout" in t or "net::ERR" in t or "ERR_" in t


def chapitre_suivant_tenace(page, url_chapitre: str, courant: str, jusqua, entiers: bool = False, essais=None, pause_ms=None):
    """v0.8.4 (26/09/2026, Quang : TBATE ch.2 -> 30 arrete net au passage au ch.3, « Page.goto: Timeout 45000ms » ; le meme
    ch.3 s'ouvrait en 3 s dix minutes plus tard) : un ralentissement passager du site ne tue plus la serie -- jusqu'a
    SUIVANT_ESSAIS tentatives espacees de 15 s. Une erreur de LOGIQUE remonte tout de suite (rien n'est masque)."""
    essais = essais or SUIVANT_ESSAIS
    pause_ms = SUIVANT_PAUSE_MS if pause_ms is None else pause_ms
    for k in range(1, essais + 1):
        try:
            return chapitre_suivant(page, url_chapitre, courant, jusqua, entiers)
        except Exception as e:
            if k >= essais or not _erreur_passagere(e):
                raise
            log_evt("série", f"passage au chapitre suivant : essai {k} échoué ({type(e).__name__}), nouvel essai dans {pause_ms // 1000} s")
            print(f"Passage au chapitre suivant : essai {k}/{essais} échoué ({type(e).__name__}) — nouvel essai dans {pause_ms // 1000} s.")
            page.wait_for_timeout(pause_ms)


def chapitre_suivant(page, url_chapitre: str, courant: str, jusqua, entiers: bool = False):
    """Amène l'onglet au chapitre qui suit `courant`. Retourne (numéro, None) ou (None, raison)."""
    m = re.search(r"mangadex\.org/chapter/([0-9a-f-]{36})", url_chapitre)
    if m:
        dispo, lang = md_chapitres_serie(m.group(1))
        n, cid, raison = _choisir_suivant(dispo, courant, jusqua, entiers)
        if n is None:
            return None, f"MangaDex : {raison} (langue {lang})"
        page.goto(f"https://mangadex.org/chapter/{cid}", wait_until="domcontentloaded", timeout=45000)
        return n, None
    if "mangaplus.shueisha.co.jp/viewer/" in url_chapitre:
        if page.url.split("?")[0] != url_chapitre:
            page.goto(url_chapitre, wait_until="domcontentloaded", timeout=45000)
        titre_url = None
        for _ in range(15):
            page.wait_for_timeout(1000)
            titre_url = page.evaluate(
                "() => (Array.from(document.querySelectorAll('a')).map(a => a.href)"
                ".find(h => /\\/titles\\/\\d+/.test(h)) || null)")
            if titre_url:
                break
        if not titre_url:
            return None, "MANGA Plus : lien vers la page de la série introuvable dans le lecteur"
        page.goto(titre_url, wait_until="domcontentloaded", timeout=45000)
        items = []
        for _ in range(20):
            page.wait_for_timeout(1000)
            items = page.evaluate(
                "() => Array.from(document.querySelectorAll('[class*=chapterListItem]'))"
                ".map(e => ((e.innerText || '').match(/#(\\d+)/) || [])[1]).filter(Boolean)")
            if items:
                break
        dispo = {str(int(x)): x for x in items}
        n, brut, raison = _choisir_suivant(dispo, courant, jusqua, entiers)
        if n is None:
            return None, "MANGA Plus : " + raison + " (seuls les chapitres gratuits y sont listés)"
        avant = page.url
        page.evaluate("(num) => { const e = Array.from(document.querySelectorAll('[class*=chapterListItem]'))"
                      ".find(x => ((x.innerText || '').match(/#(\\d+)/) || [])[1] === num);"
                      " (e.querySelector('[class*=title]') || e).click(); }", brut)
        for _ in range(30):
            page.wait_for_timeout(500)
            if "/viewer/" in page.url and page.url != avant:
                # le lecteur se RECHARGE juste après le clic (mesuré 22/09 : « Execution context
                # was destroyed » au 1er evaluate) -> on rouvre proprement son adresse.
                page.goto(page.url.split("?")[0], wait_until="domcontentloaded", timeout=45000)
                # Un chapitre LISTÉ gratuit peut ne servir AUCUNE page sur le web (Claymore #004,
                # mesuré 22/09 : compteur « 1 / 0 », API 200 mais vide). On le dit tout de suite
                # au lieu de laisser la capture échouer au bout de 2 min 30.
                for _ in range(30):
                    page.wait_for_timeout(1000)
                    try:
                        nb = page.evaluate(
                            "() => [Array.from(document.images).filter(i => i.naturalHeight > 800).length,"
                            " +((document.body.innerText.match(/\\d+ \\/ (\\d+)/) || [0, -1])[1])]")
                    except Exception:
                        continue
                    if nb[0] > 0 or nb[1] > 0:
                        return n, None
                return None, (f"MANGA Plus : le chapitre #{brut} est listé mais n'affiche aucune page "
                              "sur le web (réservé à l'application ou à un abonnement ?)")
        return None, f"MANGA Plus : le clic sur le chapitre #{brut} n'a pas ouvert le lecteur"
    # v0.5.2 : webtoons.com (Originals et Canvas) -- .../viewer?title_no=T&episode_no=N. ⚠ episode_no est un numero
    # INTERNE, avec des trous : ImpTown (22/09) passe de episode_no=1 a 3, affiche comme 2e episode (le 2 a ete retire).
    # La seule verite est le bouton « episode suivant » du lecteur (a._nextEpisode) ; on numerote dans CET ordre.
    if "webtoons.com/" in url_chapitre and "title_no=" in url_chapitre:
        if page.url.split("#")[0] != url_chapitre:
            page.goto(url_chapitre, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(3000)
        suiv = page.evaluate("() => { const a = document.querySelector('a._nextEpisode, a.pg_next._nextEpisode');"
                             " return a && /episode_no=/.test(a.href) ? a.href.split('#')[0] : null; }")
        if not suiv:
            return None, "WEBTOON : pas d'épisode suivant (dernier épisode publié)"
        n = _format_num(int(_num(courant)) + 1)
        if jusqua is not None and _num(n) > jusqua:
            return None, f"WEBTOON : l'épisode suivant ({n}) dépasse la borne demandée ({_format_num(jusqua)})"
        page.goto(suiv, wait_until="domcontentloaded", timeout=45000)
        return n, None
    # v0.6.0 : volumes entiers + chapitres « vol-N-chapitre-M » (manga-scantrad.io)
    mv = re.match(r"(https?://[^?#]+?/)(vol-\d+(?:-(?:chapitre|chapter|ch)-\d+(?:-\d+)?)?)/?(?:[?#].*)?$", url_chapitre, re.I)
    if mv:
        base, slug = mv.group(1), mv.group(2).lower()
        if page.url.split("?")[0].split("#")[0].rstrip("/") != url_chapitre.split("?")[0].split("#")[0].rstrip("/"):
            page.goto(url_chapitre, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(3000)
        slugs = page.evaluate("(base) => [...document.querySelectorAll('select option')].map(o => o.value)"
                              ".concat([...document.querySelectorAll('a[href]')].map(a => a.href)"
                              ".filter(h => h.startsWith(base)).map(h => h.slice(base.length).split(/[/?#]/)[0]))", base)
        n, s2, raison = vol_suivant([x.lower() for x in slugs], slug, jusqua, entiers)
        if n is None:
            return None, raison
        page.goto(base + s2 + "/", wait_until="domcontentloaded", timeout=45000)
        return n, None
    # v0.5.1 : GENERIQUE -- les sites de scans (WordPress « Madara » et cie : raijin-scans.fr, 22/09) listent sur la page
    # du chapitre les liens de TOUS les chapitres de la serie, a adresse reguliere .../chapter-12/ ou .../chapitre-12-5/.
    m = re.match(r"(https?://[^?#]+?/)(chapter|chapitre|ch)([-_/])(\d+(?:[.-]\d+)?)/?(?:[?#].*)?$", url_chapitre, re.I)
    if m:
        base, mot, sep = m.group(1), m.group(2).lower(), m.group(3)
        if page.url.split("?")[0].split("#")[0].rstrip("/") != url_chapitre.split("?")[0].split("#")[0].rstrip("/"):
            page.goto(url_chapitre, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(3000)
        liens = page.evaluate("(base) => Array.from(document.querySelectorAll('a[href]')).map(a => a.href)"
                              ".filter(h => h.startsWith(base))", base)
        dispo = {}
        motif = re.compile(re.escape(base) + mot + re.escape(sep) + r"(\d+(?:[.-]\d+)?)/?(?:[?#].*)?$", re.I)
        for h in liens:
            mm = motif.match(h)
            if mm:
                dispo.setdefault(_format_num(float(mm.group(1).replace("-", "."))), h.split("#")[0])
        if not dispo:
            r = _suivant_par_page(page, url_chapitre, courant, jusqua, entiers)   # v0.7.2 : bouton « NEXT Ch. N »
            return r if r is not None else (None, "aucun lien vers d'autres chapitres sur la page (site non pris en charge)")
        n, url, raison = _choisir_suivant(dispo, courant, jusqua, entiers)
        if n is None:
            # v0.7.2 (site de la secondaire, ch.2) : les « liens de la page » peuvent n'etre que le chapitre COURANT (lien
            # d'accessibilite « #main-content ») -> avant de conclure, le bouton « suivant » de la page
            r = _suivant_par_page(page, url_chapitre, courant, jusqua, entiers)
            return r if r is not None and r[0] is not None else (None, raison + " (liens de la page)")
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        return n, None
    r = _suivant_par_page(page, url_chapitre, courant, jusqua, entiers)     # v0.7.0 : liste de la page / lien « suivant »
    if r is not None:
        return r
    return None, "enchaînement impossible sur ce site : ni format d'adresse connu, ni liste des chapitres, ni lien « chapitre suivant »"



# --------------------------------------------------------------------------- webtoons (v0.5.0)
# Un webtoon (manhwa) arrive en BANDES de 800 x ~10 000 px (Solo Leveling: Ragnarok ch.1, MangaDex, mesure 22/09) :
# un modele de lecture reduit une telle image a ~160 px de large (bulles illisibles), la detection des bulles et la
# video 9:16 aussi. On les DECOUPE en pages, UNE FOIS, a la capture : toute la suite (narration, traduction, video,
# visionneuse) retrouve des pages normales sans rien changer. Regles, mesurees sur les 26 bandes de ce chapitre :
#  - les bandes sont d'abord RECOLLEES bout a bout : l'editeur les coupe n'importe ou, parfois au milieu d'une case ;
#  - on coupe dans une ligne STRICTEMENT unie (ecart <= 24 niveaux sur toute la largeur) : un contour de bulle de
#    2 px suffit a la rendre « occupee » (v1 ignorait 2 % des pixels -> coupes A TRAVERS des encadres de texte) ;
#  - la gouttiere la plus proche de 1,5 x la largeur, les longues etant preferees ; sinon (rare : 5 coupes sur 128)
#    la ligne la moins occupee, jamais dans le texte d'apres le controle visuel ;
#  - pas de page de moins de 0,45 x la cible en fin de chapitre.
# Les bandes d'origine sont gardees dans <chapitre>/originaux/ (rien n'est perdu).
DECOUPE_RATIO = 3.0            # une image plus de 3 fois plus haute que large = une bande
DECOUPE_TOL = 24
# v0.5.2 (22/09) : webtoons.com sert un episode en MORCEAUX de 800 x 1280 px (ratio 1,6 < 3), coupes a hauteur fixe
# AU MILIEU des cases (ImpTown ep.1 : 11 raccords sur 16 traversent une case). Sur ces sites, TOUT le chapitre est
# un ruban : recolle puis recoupe aux gouttieres, comme une bande.
RUBAN_SITES = ("webtoons.com",)


def _coupes_webtoon(ptp, occ, largeur, vd=None):
    import numpy as np
    h, H = len(ptp), int(largeur * 1.5)
    def _runs(calme, mini=4):
        runs, i = [], 0
        while i < h:
            if calme[i]:
                j = i
                while j < h and calme[j]:
                    j += 1
                if j - i >= mini:
                    runs.append((i, j))
                i = j
            else:
                i += 1
        return (np.array([(a + b) / 2 for a, b in runs]) if runs else np.zeros(0),
                np.array([b - a for a, b in runs]) if runs else np.zeros(0))
    centres, longs = _runs(ptp <= DECOUPE_TOL)
    if vd is not None and len(centres):
        # v0.8.2 (26/09, verifie a l'oeil : une bulle a pointes coupee entre ses deux lignes de texte -- une ligne passait
        # ENTRE les pointes, toute blanche, 4 a 6 lignes « strictes » entourees de texte : instabilite 4 389 contre 0 pour un
        # vrai espace). Une gouttiere stricte COURTE (< 12 lignes) n'est gardee que si son voisinage (± 20 lignes) est stable.
        cv = np.convolve(vd.astype(np.float64), np.ones(41), mode="same")
        garde = (longs >= 12) | (cv[np.clip(centres.astype(int), 0, h - 1)] <= 0.02 * largeur)
        centres, longs = centres[garde], longs[garde]
    # v0.8.2 (26/09, ch. vecu : fond « papier » a rayures VERTICALES entre les cases -> 11 000 px sans gouttiere stricte,
    # 12 coupes forcees en plein dessin, bulles comprises -- verifie a l'oeil). 2e recours AVANT de forcer : une zone
    # VERTICALEMENT STABLE -- aucun pixel ne change d'une ligne a la suivante (`vd` = pixels qui changent de plus de
    # DECOUPE_TOL), sur >= 40 lignes. Un fond raye, uni ou degrade horizontal l'est ; une bulle (contour courbe) ou un
    # dessin ne l'est pas. Jamais prioritaire : les gouttieres strictes d'abord, un webtoon deja bon ne change pas.
    centres2, longs2 = _runs(vd <= 0, 40) if vd is not None else (np.zeros(0), np.zeros(0))
    cuts, forcees, y = [], [], 0
    while h - y > int(H * 1.5):
        fin, choix = h - int(H * 0.45), None
        for borne in (2.2, 3.2, 4.5, 7.0):                     # v0.8.2 : une page plus haute plutot qu'une coupe dans le dessin
            m = (centres >= y + H * 0.5) & (centres <= min(y + H * borne, fin))
            if m.any():
                idx = np.where(m)[0]
                sc = np.abs(centres[idx] - (y + H)) - 0.6 * np.minimum(longs[idx], 250)
                choix = int(centres[idx[int(np.argmin(sc))]])
                break
        if choix is None:
            for borne in (2.2, 3.2, 4.5, 7.0):
                m = (centres2 >= y + H * 0.5) & (centres2 <= min(y + H * borne, fin))
                if m.any():
                    idx = np.where(m)[0]
                    sc = np.abs(centres2[idx] - (y + H)) - 0.6 * np.minimum(longs2[idx], 250)
                    choix = int(centres2[idx[int(np.argmin(sc))]])
                    break
        if choix is None:
            a, b = y + int(H * 0.8), min(fin, y + int(H * 2.2))
            if vd is not None:
                # v0.8.2 (26/09, verifie a l'oeil : une bulle coupee ENTRE ses deux lignes de texte -- la ligne la plus « vide »
                # isolement) : on force la ou les 41 lignes AUTOUR sont les plus stables. Entre deux lignes de texte, le voisinage
                # est du texte : evite. Un aplat ou un degrade, lui, est stable.
                v = np.convolve(vd.astype(np.float64), np.ones(41), mode="same")
                choix = a + int(np.argmin(v[a:b] + occ[a:b] * 0.1))
            else:
                choix = a + int(np.argmin(occ[a:b]))
            forcees.append(choix)
        cuts.append(choix)
        y = choix
    return cuts, forcees


def _bords_page(chemin: str):
    """v0.8.2 : (1re ligne, derniere ligne) d'une image, en niveaux de gris."""
    from PIL import Image
    import numpy as np
    with Image.open(chemin) as im:
        g = im.convert("L")
        a = np.asarray(g, dtype=np.int16)
    return a[0], a[-1]


def _coupe_dans_dessin(page_a, page_b) -> bool:
    """v0.8.2 (mesure, pas detection) : le raccord page A -> page B tranche-t-il le dessin ? Non s'il tombe dans une zone
    VERTICALEMENT STABLE (8 dernieres lignes de A et 8 premieres de B sans aucun pixel qui change : espace raye, uni…)."""
    import numpy as np
    stable = lambda z: not (np.abs(np.diff(z, axis=0)) > DECOUPE_TOL).any()
    if stable(page_a[-8:]) and stable(page_b[:8]):
        return False
    return _raccord_continu((page_a[0], page_a[-1]), (page_b[0], page_b[-1]))


def _raccord_continu(haut_de, bas_de) -> bool:
    """v0.8.2 : le dessin continue-t-il de l'image A (bas) a l'image B (haut) ? Bord non uni (ecart a la mediane > DECOUPE_TOL
    sur > 2 % de la largeur) ET lignes voisines ressemblantes (ecart moyen < 18)."""
    import numpy as np
    bas, haut = haut_de[1], bas_de[0]
    if len(bas) != len(haut):
        return False
    plein = lambda r: int((np.abs(r - np.median(r)) > DECOUPE_TOL).sum()) > 0.02 * len(r)
    return (plein(bas) or plein(haut)) and float(np.abs(bas - haut).mean()) < 18


def decouper_bandes(dossier: str) -> dict | None:
    """Decoupe les bandes webtoon d'un chapitre (sur place). None si rien a faire."""
    mp = os.path.join(dossier, "manifest.json")
    man = json.load(open(mp, encoding="utf-8"))
    pages = man.get("pages") or []
    from PIL import Image
    dims = []
    for pg in pages:
        with Image.open(os.path.join(dossier, pg["file"])) as im:
            dims.append(im.size)
    est_bande = [h / w > DECOUPE_RATIO for w, h in dims]
    # v0.8.2 (26/09, Quang : « des bulles decoupees en plein milieu ») : un site peut trancher son ruban en TUILES courtes
    # (mesure : 720x700 ratio 0,97 ; un autre site 2,08) -- aucune ne depasse DECOUPE_RATIO, le ruban restait coupe la ou le
    # site l'avait tranche, en plein dessin. Critere independant de la forme : un RUBAN, c'est un dessin qui CONTINUE d'une
    # image a la suivante. Une suite d'au moins 5 images consecutives de meme largeur (>= 500 px) dont >= 50 % des raccords
    # continuent le dessin (bord non uni ET derniere ligne de l'une ~ premiere ligne de l'autre) est un ruban -> recolle puis
    # recoupe aux gouttieres. Des pages de manga (chaque page = une autre image) ne continuent pas : elles n'y entrent pas.
    bords_pg = [_bords_page(os.path.join(dossier, pg["file"])) for pg in pages]
    k = 0
    while k < len(dims):
        j = k
        while j + 1 < len(dims) and dims[j + 1][0] == dims[k][0]:
            j += 1
        if j - k + 1 >= 5 and dims[k][0] >= 500:
            suit = sum(_raccord_continu(bords_pg[m], bords_pg[m + 1]) for m in range(k, j))
            if suit >= 0.5 * (j - k):          # mesure 26/09 : vrais rubans 62-83 %, pages bonus d'un manga 33 %
                for m in range(k, j + 1):
                    est_bande[m] = True
        k = j + 1
    if any(s in (man.get("source_url") or "") for s in RUBAN_SITES):
        est_bande = [True] * len(dims)
    if not any(est_bande) or man.get("decoupe"):
        return None
    import numpy as np
    # les bandes CONSECUTIVES forment un seul ruban (une page normale au milieu le coupe en deux rubans)
    groupes, cur = [], []
    for k, b in enumerate(est_bande):
        if b:
            cur.append(k)
        elif cur:
            groupes.append(cur); cur = []
    if cur:
        groupes.append(cur)
    orig = os.path.join(dossier, "originaux")
    os.makedirs(orig, exist_ok=True)
    nouvelles, n_forcees, par_page = [], 0, {}
    for g in groupes:
        largeur = dims[g[0]][0]
        ptp, occ, vds, bornes, y, prec = [], [], [], [], 0, None
        for k in g:
            with Image.open(os.path.join(dossier, pages[k]["file"])) as im:
                im = im.convert("L")
                if im.width != largeur:                       # largeurs melangees : on aligne sur la 1re
                    im = im.resize((largeur, round(im.height * largeur / im.width)))
                a = np.asarray(im, dtype=np.int16)
            med = np.median(a, axis=1, keepdims=True)
            ptp.append(a.max(axis=1) - a.min(axis=1))
            occ.append((np.abs(a - med) > DECOUPE_TOL).sum(axis=1))
            v = np.zeros(a.shape[0], dtype=np.int32)                       # v0.8.2 : stabilite verticale (raccords compris)
            v[1:] = (np.abs(np.diff(a, axis=0)) > DECOUPE_TOL).sum(axis=1)
            v[0] = (np.abs(a[0] - prec) > DECOUPE_TOL).sum() if prec is not None else largeur
            vds.append(v); prec = a[-1]
            bornes.append((y, y + a.shape[0], k)); y += a.shape[0]
        cuts, forcees = _coupes_webtoon(np.concatenate(ptp), np.concatenate(occ), largeur, np.concatenate(vds))
        n_forcees += len(forcees)
        tr = [0] + cuts + [y]
        tranches = []
        for a0, b0 in zip(tr, tr[1:]):
            morceau = Image.new("RGB", (largeur, b0 - a0), "white")
            for a, b, k in bornes:
                lo, hi = max(a, a0), min(b, b0)
                if lo < hi:
                    with Image.open(os.path.join(dossier, pages[k]["file"])) as im:
                        im = im.convert("RGB")
                        if im.width != largeur:
                            im = im.resize((largeur, round(im.height * largeur / im.width)))
                        morceau.paste(im.crop((0, lo - a, largeur, hi - a)), (0, lo - a0))
            tranches.append(morceau)
        par_page[g[0]] = tranches
        for k in g[1:]:
            par_page[k] = []
    # nouvelle sequence : pages normales telles quelles, rubans remplaces par leurs tranches
    tmp = os.path.join(dossier, "_decoupe_tmp")
    shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
    for k, pg in enumerate(pages):
        src = os.path.join(dossier, pg["file"])
        if k in par_page:
            for t in par_page[k]:
                nom = "page_%03d.jpg" % (len(nouvelles) + 1)
                t.save(os.path.join(tmp, nom), "JPEG", quality=92)
                nouvelles.append({"file": nom, "bytes": os.path.getsize(os.path.join(tmp, nom)), "w": t.width, "h": t.height,
                                  "de": pg["file"]})
        else:
            nom = "page_%03d%s" % (len(nouvelles) + 1, os.path.splitext(pg["file"])[1])
            shutil.copy2(src, os.path.join(tmp, nom))
            nouvelles.append(dict(pg, file=nom))
    for pg in pages:                                            # originaux de cote, puis les nouvelles pages
        os.replace(os.path.join(dossier, pg["file"]), os.path.join(orig, pg["file"]))
    for nv in nouvelles:
        os.replace(os.path.join(tmp, nv["file"]), os.path.join(dossier, nv["file"]))
    shutil.rmtree(tmp, ignore_errors=True)
    nb = sum(est_bande)
    info = {"bandes": nb, "pages": sum(len(v) for v in par_page.values()), "coupes_hors_gouttiere": n_forcees,
            "version": VERSION, "originaux": "originaux/" + " (manifeste d'origine : originaux/manifest.json)"}
    json.dump(man, open(os.path.join(orig, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    man["pages"] = nouvelles
    man["decoupe"] = info
    man.setdefault("notes", []).append("webtoon : %d bandes découpées en %d pages (%d coupe(s) hors gouttière) — originaux/ gardés"
                                       % (nb, info["pages"], n_forcees))
    json.dump(man, open(mp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log_evt("webtoon", "bandes découpées", bandes=nb, pages=info["pages"], forcees=n_forcees, dossier=dossier)
    print("Webtoon : %d bandes découpées en %d pages (%d coupe(s) hors gouttière), originaux gardés." % (nb, info["pages"], n_forcees))
    return info


def capture(args) -> int:
    from playwright.sync_api import sync_playwright  # import tardif : seule la capture en dépend

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(EDGE_CDP)

        def est_visible(pg) -> bool:
            try:
                return pg.evaluate("() => document.visibilityState") == "visible"
            except Exception:
                return False

        def score_pages(pg) -> int:
            """Nb d'images de page (hautes, portrait) dans l'onglet — -1 si injoignable."""
            try:
                return pg.evaluate(
                    "() => Array.from(document.images)"
                    ".filter(i => i.naturalHeight > 800 && i.naturalWidth > 250"
                    " && i.naturalWidth / i.naturalHeight < 0.93).length")
            except Exception:
                return -1

        def onglet_fenetre_active(candidats):
            """L'onglet actif de la fenêtre Edge que l'utilisateur regarde.

            CDP ne sait pas quelle fenêtre est au premier plan (chaque fenêtre Edge a
            son onglet actif, tous 'visibility=visible'). L'OS, si : on prend les
            fenêtres Edge dans l'ordre Z de Windows (la plus récemment active d'abord
            — au moment de la capture, le premier plan est la console du .bat), et on
            la matche aux fenêtres du navigateur piloté par leurs coordonnées
            (bounds CDP en DIP, corrigés du DPI). Retourne la page ou None."""
            try:
                import ctypes
                from ctypes import wintypes
                user32 = ctypes.windll.user32

                def classe(h):
                    b = ctypes.create_unicode_buffer(64)
                    user32.GetClassNameW(h, b, 64)
                    return b.value

                order = []
                foreground = user32.GetForegroundWindow()
                if foreground and classe(foreground) == "Chrome_WidgetWin_1":
                    order.append(foreground)  # Edge est au premier plan : priorité absolue
                @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
                def cb(h, _):
                    if (user32.IsWindowVisible(h) and classe(h) == "Chrome_WidgetWin_1"
                            and h not in order):
                        order.append(h)
                    return True
                user32.EnumWindows(cb, 0)

                for h in order:  # Z-order décroissant = la plus récemment active d'abord
                    rect = wintypes.RECT()
                    user32.GetWindowRect(h, ctypes.byref(rect))
                    dpi = user32.GetDpiForWindow(h) or 96
                    k = dpi / 96.0
                    # MEILLEUR match par distance (position + taille), pas « premier sous
                    # tolérance » : les fenêtres Edge s'ouvrent en CASCADE (~22 px
                    # d'écart) — le premier-match prenait la MAUVAISE fenêtre (mesuré
                    # 18:03 : l'onglet de la fenêtre d'avant capturé au lieu de l'actif).
                    meilleur, dmin = None, None
                    for pg in candidats:
                        try:
                            sess = pg.context.new_cdp_session(pg)
                            b = sess.send("Browser.getWindowForTarget").get("bounds", {})
                            d = (abs(b.get("left", -99999) * k - rect.left)
                                 + abs(b.get("top", -99999) * k - rect.top)
                                 + 0.5 * abs(b.get("width", -1) * k - (rect.right - rect.left))
                                 + 0.5 * abs(b.get("height", -1) * k - (rect.bottom - rect.top)))
                            if dmin is None or d < dmin:
                                meilleur, dmin = pg, d
                        except Exception:
                            continue
                    if meilleur is not None and dmin is not None and dmin < 120:
                        return meilleur
                return None
            except Exception:
                return None

        tous = [pg for ctx in browser.contexts for pg in ctx.pages]
        if args.tab:
            candidats = [pg for pg in tous if args.tab in pg.url]
        else:
            # MODE PAR DÉFAUT : les onglets ACTIFS (affichés). ⚠ Chaque FENÊTRE Edge a
            # son onglet actif : avec plusieurs fenêtres, plusieurs candidats 'visible'.
            candidats = [pg for pg in tous if est_visible(pg)]
        if not candidats:
            print(f"Aucun onglet{' contenant ' + args.tab if args.tab else ' actif'} "
                  f"dans la fenêtre dédiée (CDP {EDGE_CDP}).")
            print("Ouvre le chapitre (onglet affiché) puis relance.")
            return 1
        methode_choix = "unique"
        if len(candidats) > 1 and not args.tab:
            # Mode interactif : la fenêtre Edge que l'utilisateur regarde (détection OS,
            # Z-order + match des bounds). ⚠ Ne JAMAIS l'appliquer en mode --tab (script) :
            # elle court-circuiterait le ciblage précis (régression mesurée sur le banc).
            actif = onglet_fenetre_active(candidats)
            if actif is not None:
                page = actif
                methode_choix = "fenêtre-active-OS"
                print("Onglet actif détecté (fenêtre Edge que tu regardes) :")
                print(f"  {page.url[:88]}")
            else:
                # Repli : départage par le contenu — l'onglet qui contient des images
                # de page est le chapitre ; « nouvel onglet », home, ntp n'en ont aucune.
                gagnants = [pg for pg in candidats if score_pages(pg) > 0]
                if len(gagnants) == 1:
                    page = gagnants[0]
                    methode_choix = "scoring-contenu"
                    print("Onglet choisi automatiquement (seul à contenir un chapitre) :")
                    print(f"  {page.url[:88]}")
                else:
                    methode_choix = "question"
                    liste = gagnants if gagnants else candidats
                    print("=" * 58)
                    print("Plusieurs onglets candidats :")
                    for i, pg in enumerate(liste, 1):
                        print(f"  {i}) {pg.url[:88]}")
                    try:
                        rep = input("Lequel capturer ? (numéro, Entrée = 1) : ").strip()
                        page = liste[int(rep) - 1] if rep.isdigit() and 1 <= int(rep) <= len(liste) else liste[0]
                    except (EOFError, ValueError):
                        page = liste[0]  # mode automatisé (stdin fermé) : premier candidat
        else:
            page = candidats[0]
        # v0.4.0 : UN chapitre = ce bloc. La capture en SÉRIE (--suite / --jusqua) le rejoue
        # chapitre après chapitre sur le MÊME onglet, que chapitre_suivant() fait avancer.
        DERNIER: dict = {}

        def un_chapitre(args) -> int:
            DERNIER["url"] = _url_chapitre(page.url)
            DERNIER["deja_la"] = False
            DERNIER["echec"] = ""
            print(f"Onglet : {page.url[:80]}")
            log_evt("capture", "démarrage", titre=args.title, chapitre=str(args.chapter),
                    methode_onglet=methode_choix, onglet=page.url[:100])
            page.bring_to_front()  # un onglet de fond est THROTTLE par le navigateur :
            # son chargement ralentit et la capture part dans le vide (mesuré : « Loading... »)

            # CONFIRMATION VISUELLE en interactif : la sélection automatique peut se tromper
            # silencieusement (mesuré 18:47 : « fenêtre-active-OS » a pris la page titre
            # laissée par un banc → 2 images de Frieren écrites dans le ch_301 d'OPM).
            # Une frappe élimine toute la classe d'erreurs de sélection.
            if not args.tab and not getattr(args, "enchaine", False):
                try:
                    if sys.stdin and sys.stdin.isatty():
                        rep = input("  Capturer CET onglet ? (Entrée = oui, autre touche = annuler) : ").strip()
                        if rep:
                            print("Capture annulée — l'onglet n'était pas le bon.")
                            log_evt("annulation", "onglet refusé à la confirmation", onglet=page.url[:100])
                            return 0
                except EOFError:
                    pass

            # MangaDex pagine par URL (/chapter/<uuid>/<n>) : si l'onglet est au MILIEU du
            # chapitre, on capture DEPUIS CETTE PAGE — choix délibéré de l'utilisateur
            # (sauter crédits/sommaire : « les premières images ne servent à rien », 18:03).
            # --page-1 force le retour au début si on veut tout.
            u = page.url.split("?")[0].split("#")[0]
            base, _, num_page = u.rpartition("/")
            note_depart = None
            if "/chapter/" in base and num_page.isdigit() and int(num_page) > 1:
                if getattr(args, "page_1", False):
                    print(f"Retour à la page 1 (l'onglet était page {num_page})...")
                    page.goto(base, wait_until="domcontentloaded", timeout=45000)
                    page.bring_to_front()
                    log_evt("départ", f"retour page 1 (était page {num_page})")
                else:
                    print(f"Capture depuis la page {num_page} — les pages 1 à {int(num_page) - 1} "
                          f"ne seront pas capturées (--page-1 pour commencer au début).")
                    note_depart = (f"capture démarrée à la page {num_page} "
                                   f"(pages 1-{int(num_page) - 1} absentes volontairement)")
                    log_evt("départ", f"page {num_page} (pages 1-{int(num_page) - 1} exclues)")

            # attendre que le lecteur ait chargé sa première page (<= 90 s)
            for _ in range(90):
                try:
                    pret = page.evaluate(
                        "() => Array.from(document.images)"
                        ".some(i => i.naturalHeight > 800 && i.naturalWidth > 250)")
                except Exception:
                    pret = False  # v0.4.0 : la page se recharge encore (lecteur SPA) -> on réessaie
                if pret:
                    break
                page.wait_for_timeout(1000)

            # Défilement progressif AVEC collecte à la volée.
            # ⚠ Les lecteurs virtualisés (MangaDex inclus) DÉCHARGENT les images hors écran :
            # scroller tout puis collecter ne ramasse que ce qui reste à l'écran
            # (mesuré : 4 pages sur 22). On attrape chaque page PENDANT qu'elle vit.
            dest = chap_dir(args.out, args.title, args.chapter)
            # anti-doublon : chapitre déjà capturé ? (demande Quang 18:39 — ne pas
            # recharger silencieusement un manga/chapitre déjà présent)
            mp_exist = os.path.join(dest, "manifest.json")
            if os.path.exists(mp_exist) and not args.force:
                try:
                    ancien = json.load(open(mp_exist, encoding="utf-8"))
                    info = (f"{len(ancien.get('pages', []))} pages, "
                            f"capturé le {ancien.get('captured_at', '?')[:16]}")
                except Exception:
                    info = "manifeste illisible"
                print(f"DÉJÀ PRÉSENT : « {args.title} » ch. {args.chapter} ({info}).")
                remplacer = ""
                try:
                    if sys.stdin and sys.stdin.isatty():
                        remplacer = input("Le remplacer ? (o/N) : ").strip().lower()
                except EOFError:
                    remplacer = ""
                if remplacer != "o":
                    print("Capture ignorée — l'existant est conservé "
                          "(--force pour remplacer sans demander).")
                    log_evt("doublon", "capture ignorée (chapitre déjà présent)", dossier=dest)
                    DERNIER["deja_la"] = True                  # v0.8.0 : le bilan de serie le distingue d'une capture
                    return 0
                print("Remplacement demandé.")
            os.makedirs(dest, exist_ok=True)
            # v0.6.1 (24/09, demande Quang) : le titre TAPE est connu des le depart -- le manifeste (qui le porte)
            # n'est ecrit qu'en fin de capture, et l'app affichait le nom du dossier (« solo-leveling ») d'ici la.
            # Fichier a part : le manifeste signifie « chapitre capture » (anti-doublon ci-dessus).
            try:
                with open(os.path.join(os.path.dirname(dest), "titre.json"), "w", encoding="utf-8") as f:
                    json.dump({"titre": args.title}, f, ensure_ascii=False)
            except OSError:
                pass
            notes: list = []
            if note_depart:
                notes.append(note_depart)
            vues: dict = {}           # src -> {file, bytes, top, w, h} — ordre d'insertion = lecture
            vus_hashes: set = set()   # dedup par CONTENU : les pagers re-servent une page déjà
            # affichée sous un blob: neuf (mesuré : 30 images collectées pour 22 pages).
            # SAUVEGARDE INCRÉMENTALE : chaque page est écrite dès sa collecte — un arrêt
            # brutal (kill, crash) ne perd plus tout (incident ch.1→ch.7 du 21/09 : 0 page
            # sauvée parce que tout vivait en mémoire jusqu'à la fin).

            FETCH_JS = """async (url) => {
                const r = await fetch(url);
                const b = await r.blob();
                return await new Promise(res => {
                    const fr = new FileReader();
                    fr.onload = () => res(fr.result.split(',')[1]);
                    fr.readAsDataURL(b);
                });
            }"""

            CANVAS_JS = """(url) => {
                const i = Array.from(document.images).find(x => x.src === url);
                if (!i || !i.naturalWidth) return null;
                const c = document.createElement('canvas');
                c.width = i.naturalWidth; c.height = i.naturalHeight;
                c.getContext('2d').drawImage(i, 0, 0);
                return c.toDataURL('image/png').split(',')[1];
            }"""
            MASQUE_JS = """(masquer) => {
                if (masquer) {
                    for (const el of document.querySelectorAll('body *')) {
                        const pos = getComputedStyle(el).position;
                        if ((pos === 'fixed' || pos === 'sticky') && !el.querySelector('img')) {
                            el.setAttribute('data-mf-masque', el.style.visibility || '');
                            el.style.visibility = 'hidden';
                        }
                    }
                } else {
                    for (const el of document.querySelectorAll('[data-mf-masque]')) {
                        el.style.visibility = el.getAttribute('data-mf-masque');
                        el.removeAttribute('data-mf-masque');
                    }
                }
            }"""

            CDP_RES = {}                                    # v0.7.3 : session CDP ouverte a la 1re image refusee
            MODE_BANDE = [False]                            # v0.7.3 : fixe une fois le mode de lecture connu
            ECARTEES = set()                                # v0.7.4 : images vues mais ecartees volontairement
            def extraire_data(src: str) -> bytes:
                """Pleine résolution si possible (fetch page / requests), sinon SCREENSHOT de
                l'élément. Certains sites bloquent fetch(blob:) par CSP alors que l'image
                s'affiche parfaitement (MANGA Plus, mesuré 21/09) : le screenshot est la
                parade universelle — qualité = affichage, ce qui suffit à la narration."""
                if src.startswith(("blob:", "data:")):
                    try:
                        return base64.b64decode(page.evaluate(FETCH_JS, src))
                    except Exception:
                        pass  # CSP ou blob révoqué → canvas
                    # v0.3.0 : l'image AFFICHÉE redessinée dans un canvas = pleine résolution, sans
                    # rien de l'écran. Un blob: est de même origine, le canvas n'est pas « taché ».
                    # Avant : screenshot à la taille d'affichage (801 px au lieu de 1060) ET barres du
                    # lecteur MANGA Plus incrustées en haut et en bas de chaque page (vu par Quang 21/09).
                    try:
                        b64 = page.evaluate(CANVAS_JS, src)
                        if b64:
                            return base64.b64decode(b64)
                    except Exception:
                        pass  # canvas refusé → screenshot
                else:
                    try:
                        r = requests.get(src, headers={"User-Agent": UA, "Referer": page.url}, timeout=60)
                        r.raise_for_status()
                        return r.content
                    except Exception:
                        pass
                    # v0.7.3 (25/09) : serveur d'images derriere Cloudflare -> 403 a tout client hors navigateur, pas de
                    # CORS (fetch refuse, canvas « tache ») ; le screenshot, lui, fait DEFILER la page jusqu'a l'image :
                    # 26 pages en 8 min puis plafond a 5 664 px sur 193 573. Le navigateur a DEJA l'image : on la lui
                    # redemande (CDP Page.getResourceContent) -> le fichier ORIGINAL, instantane, sans bouger.
                    # Mesure : 144 images sur 145 ; la derniere passe au screenshot.
                    try:
                        if CDP_RES.get("s") is None:
                            CDP_RES["s"] = page.context.new_cdp_session(page)
                            CDP_RES["s"].send("Page.enable")
                        fid = CDP_RES["s"].send("Page.getFrameTree")["frameTree"]["frame"]["id"]
                        rc = CDP_RES["s"].send("Page.getResourceContent", {"frameId": fid, "url": src})
                        data = base64.b64decode(rc["content"]) if rc.get("base64Encoded") else rc["content"].encode("latin-1")
                        if len(data) > 1000:
                            return data
                    except Exception:
                        pass
                el = None
                try:
                    el = page.query_selector(f'img[src="{src}"]')
                except Exception:
                    pass
                if el is None:
                    raise RuntimeError("élément introuvable pour le screenshot")
                # dernier recours : masquer les barres flottantes du lecteur le temps de la prise
                page.evaluate(MASQUE_JS, True)
                try:
                    return el.screenshot()  # PNG à la taille d'affichage
                finally:
                    page.evaluate(MASQUE_JS, False)

            def collecter() -> None:
                """Détecte les images de page AFFICHÉES, les récupère et les ÉCRIT aussitôt."""
                # Filtre VISIBLE à l'écran (avec marge 80 px) : le lecteur GARDE en mémoire
                # les pages déjà visitées (préchargées autour de la page courante) — sans
                # ce filtre, la page d'AVANT la page de départ était capturée (mesuré 18:16).
                # + zone morte des ratios CARRÉS (0.93-1.15) : une page de manga est portrait
                # (~0.7) ou double (~1.4), jamais carrée — mais avatars et logos le sont.
                # v0.7.3 (25/09) : en BANDE DEFILANTE, une bande COURTE ou presque carree de la MEME largeur que les pages
                # deja prises est un morceau de l'histoire (bulles de dialogue : 10 bandes sur 145 perdues sur un site,
                # 122 a 638 px de haut). Avatars et bannieres n'ont pas cette largeur : le filtre d'origine reste pour eux.
                _larg = [v["w"] for v in vues.values()]
                larg_col = max(set(_larg), key=_larg.count) if (MODE_BANDE[0] and len(_larg) >= 3) else 0
                # v0.8.1 (26/09, ch. vecu par Quang : 210 bandes de 720x700, ratio 1,03) : l'amorcage exigeait 3 pages DEJA
                # prises a cette largeur -- or une bande presque carree ne passe jamais le filtre d'origine -> 1 page, ECHEC.
                # Tant que 3 pages ne sont pas prises, la largeur de colonne se lit sur le DOCUMENT : >= 5 images d'au moins
                # 500 px de large, hors commentaires, a la meme largeur (avatars, logos et vignettes n'y arrivent pas).
                if MODE_BANDE[0] and not larg_col:
                    larg_col = -1
                nouvelles = page.evaluate("""(W) => { if (W === -1) { const n = {};
                        [...document.images].filter(i => i.naturalWidth >= 500 && i.naturalHeight >= 60
                            && !i.closest('#comments, .comments, .comments-list-wrapper, .comment, [id^="comment"], .disqus, #disqus_thread'))
                          .forEach(i => { n[i.naturalWidth] = (n[i.naturalWidth] || 0) + 1; });
                        const e = Object.entries(n).sort((a, b) => b[1] - a[1]);
                        W = e.length && e[0][1] >= 5 ? +e[0][0] : 0; }
                    return Array.from(document.images)
                    .filter(i => (i.naturalWidth > 250 && i.naturalHeight > 500
                        && (i.naturalWidth / i.naturalHeight < 0.93
                            || i.naturalWidth / i.naturalHeight > 1.15))
                        || (W > 0 && i.naturalWidth === W && i.naturalHeight >= 60))
                    .filter(i => { const r = i.getBoundingClientRect();
                                   return r.bottom > 80 && r.top < window.innerHeight - 80; })
                    // v0.5.1 : une page est AFFICHEE en grand ; les avatars des commentaires (raijin-scans 22/09 :
                    // 5 « pages » = avatars de 736x1288 montres en 50 px) ne le sont pas, et vivent dans les commentaires
                    .filter(i => i.getBoundingClientRect().width >= 180
                        && !i.closest('#comments, .comments, .comments-list-wrapper, .comment, [id^="comment"], .disqus, #disqus_thread'))
                    .map(i => ({src: i.src, top: Math.round(i.getBoundingClientRect().top + window.scrollY),
                                w: i.naturalWidth, h: i.naturalHeight})); }""", larg_col)
                for im in nouvelles:
                    if im["src"] in vues:
                        continue
                    try:
                        data = extraire_data(im["src"])
                        hsh = hashlib.sha1(data).hexdigest()
                        # v0.8.2 : en bande defilante, une petite tuile de la LARGEUR DE LA COLONNE est un espace entre deux
                        # cases (tuile blanche, 2-10 Ko) -- l'ecarter supprimait les gouttieres et forcait des coupes en plein
                        # dessin au decoupage (mesure 26/09 : 27 tuiles sur 213). Elle est gardee ; le decoupage la recoupe.
                        # Les espaces sont souvent IDENTIQUES entre eux : ils echappent aussi a la deduplication par contenu
                        # (adresses distinctes = tuiles distinctes ; le pager qui ressert un blob, lui, change de taille).
                        _lc = [v["w"] for v in vues.values()]
                        _col = max(set(_lc), key=_lc.count) if _lc else 0
                        espace = MODE_BANDE[0] and _col >= 500 and im["w"] == _col and len(data) < 10000
                        if hsh in vus_hashes and not espace:
                            ECARTEES.add(im["src"])
                            continue  # même contenu déjà capturé (blob régénéré par le pager)
                        if len(data) < 10000 and not espace:
                            ECARTEES.add(im["src"])
                            # aucune page de manga ne fait < 10 Ko : logos, boutons,
                            # cartes de fin de chapitre
                            notes.append(f"écartée ({len(data)} octets) : {im['src'][:50]}")
                            log_evt("écartée", f"trop petite ({len(data)} octets)", src=im["src"][:60])
                            continue
                        vus_hashes.add(hsh)
                        nom = save_page(dest, len(vues) + 1, data)
                        vues[im["src"]] = {"file": nom, "bytes": len(data),
                                           "top": im["top"], "w": im["w"], "h": im["h"]}
                        log_evt("page", f"{len(vues)} collectée", fichier=nom,
                                octets=len(data), dim=f"{im['w']}x{im['h']}")
                    except Exception as e:
                        notes.append(f"{im['src'][:60]} : ECHEC {type(e).__name__}")
                        log_evt("échec", f"extraction {type(e).__name__}", src=im["src"][:60])

            # Mode de lecture : bande défilante (scroll) ou page par page (pager).
            # MangaDex web est un PAGER par défaut : scrollBy n'y avance rien
            # (mesuré : 4 pages capturées sur 22 en scrollant dans le vide).
            # v0.7.1 (24/09) : attendre que la page ait FINI de se construire avant de juger le mode. Enchainee, une page
            # est capturee a la seconde ou elle s'ouvre : volume 5 lu a 1 337 px (au lieu de ~25 000) -> « page par
            # page » a tort -> 1 page puis echec. Hauteur stable 3 lectures de suite (0,5 s), 12 s au plus.
            def _stabiliser():
                _h, _stable, _t0 = -1, 0, time.time()
                while _stable < 3 and time.time() - _t0 < 12:
                    page.wait_for_timeout(500)
                    _hh = page.evaluate("() => document.documentElement.scrollHeight")
                    _stable = _stable + 1 if _hh == _h else 0
                    _h = _hh
            _stabiliser()
            # v0.7.1 (24/09, animoflix) : la page d'un volume est d'abord un ACCUEIL (couverture + « Lire Volume 5 ») ; les
            # scans n'apparaissent qu'apres ce clic. Seulement s'il n'y a AUCUNE image de page a l'ecran : ailleurs, rien ne change.
            if not page.evaluate("() => [...document.images].some(i => i.naturalHeight >= 800 && i.getBoundingClientRect().width >= 180)"):
                _clic = page.evaluate(r"""() => { const b = [...document.querySelectorAll('button, a, [role=button]')].find(x =>
                    /^(lire|read|commencer la lecture|start reading)\b/i.test((x.innerText || '').trim()) && x.getBoundingClientRect().width > 0);
                    if (!b) return null; b.click(); return (b.innerText || '').trim().slice(0, 40); }""")
                if _clic:
                    print("Page d'accueil : clic sur « %s »" % _clic)
                    log_evt("navigation", "bouton de lecture clique", bouton=_clic)
                    page.wait_for_timeout(1500)
                    _stabiliser()
            h_doc = page.evaluate("() => document.documentElement.scrollHeight")
            h_ecran = page.evaluate("() => window.innerHeight")
            # v0.3.0 : MANGA Plus en mode VERTICAL empile les 54 pages dans un BLOC qui défile,
            # le document faisant la hauteur de l'écran (mesuré 21/09 21h, BORUTO #001 : doc=1273
            # = écran → pris pour « page par page » → 1 seule page capturée, déclarée réussie).
            # On cherche donc aussi le plus grand bloc défilant ; on le marque pour le faire défiler.
            bloc = page.evaluate("""() => {
                // v0.6.7 : effacer la marque d'une capture PRECEDENTE sur le meme onglet (sinon le defilement vise
                // encore l'ancien bloc : 2e essai du 24/09, bloc refuse mais toujours marque -> page immobile).
                document.querySelectorAll('[data-mf-defile]').forEach(e => e.removeAttribute('data-mf-defile'));
                let best = null, bh = 0;
                for (const el of document.querySelectorAll('*')) {
                    const oy = getComputedStyle(el).overflowY;
                    if (oy !== 'auto' && oy !== 'scroll') continue;
                    if (el.clientHeight < innerHeight * 0.5) continue;
                    // v0.4.2 : BODY/HTML annoncent souvent « overflow:auto » mais c'est la FENETRE qui defile
                    // (webtoon MangaDex 22/09 : body marque, body.scrollBy sans effet -> 2 pages sur 26).
                    if (el === document.body || el === document.documentElement) continue;
                    if (el.scrollHeight <= bh) continue;
                    const avant = el.scrollTop; el.scrollTop = avant + 5;       // defile-t-il VRAIMENT ?
                    let bouge = el.scrollTop !== avant;
                    if (!bouge) { el.scrollTop = avant - 5; bouge = el.scrollTop !== avant; }   // deja tout en bas (22/09)
                    el.scrollTop = avant;
                    if (bouge) { bh = el.scrollHeight; best = el; }
                }
                if (!best || best.scrollHeight <= best.clientHeight * 2.5) return null;
                // v0.6.7 (24/09) : un bloc plus COURT que la page n'est pas le lecteur (panneau, commentaires) : c'est
                // la fenetre qui defile (webtoon de 232 747 px, bloc de 3 036 px -> 1 page capturee puis arret).
                // MANGA Plus reste couvert : sa page a la hauteur de l'ecran, son bloc tout le chapitre.
                if (best.scrollHeight < document.documentElement.scrollHeight) return null;
                best.setAttribute('data-mf-defile', '1');
                return [best.scrollHeight, best.clientHeight];
            }""")
            mode_strip = h_doc > h_ecran * 2.5 or bloc is not None
            MODE_BANDE[0] = mode_strip
            print(f"Mode {'bande défilante' if mode_strip else 'page par page'} "
                  f"(doc {h_doc}px / écran {h_ecran}px" + (f" / bloc défilant {bloc[0]}px)" if bloc else ")"))
            log_evt("mode", "bande défilante" if mode_strip else "page par page",
                    doc=h_doc, ecran=h_ecran, bloc=(bloc[0] if bloc else None))
            # position et défilement : dans le bloc s'il existe, sinon dans la fenêtre
            POS_JS = ("() => { const e = document.querySelector('[data-mf-defile]');"
                      " return e ? [e.scrollTop, e.scrollHeight, e.clientHeight]"
                      " : [window.scrollY, document.documentElement.scrollHeight, innerHeight]; }")
            DEFILE_JS = ("() => { const e = document.querySelector('[data-mf-defile]');"
                         " if (e) e.scrollBy(0, e.clientHeight * 0.7); else window.scrollBy(0, innerHeight * 0.7); }")

            # Fin de chapitre = l'URL change de CHAPITRE. ⚠ MangaDex pagine par URL
            # (/chapter/<id>/2, /3... — mesuré 21/09) : l'URL change à chaque PAGE.
            # Un changement ne compte donc que si ce n'est PAS « départ + numéro de page ».
            # Incident déclencheur : MangaDex charge le chapitre SUIVANT tout seul au scroll/
            # flèche (ch.1→ch.7 du 21/09 : la boucle d'images nouvelles ne s'arrêtait jamais).
            url_depart = page.url.split("?")[0].split("#")[0]
            url_source = _url_chapitre(page.url)      # v0.5.2 : webtoons.com garde title_no / episode_no

            def _chapitre_path(u: str) -> str:
                """Path réduit à l'identifiant de CHAPITRE (sans le numéro de PAGE final).
                MangaDex : /chapter/<uuid 36>/<n>. ⚠ ne retirer le segment numérique final
                QUE s'il est précédé d'un segment long non numérique (UUID) — sinon
                /viewer/1000233 (MANGA Plus) perdrait son identifiant de chapitre.
                (bug 18:13 : départ page 4 → passage en page 5 lu comme « chapitre
                suivant » → arrêt après 4 pages au lieu de finir le chapitre.)"""
                base, _, dernier = u.rpartition("/")
                if dernier.isdigit():
                    av = base.rpartition("/")[2]
                    if len(av) >= 20 and not av.isdigit():
                        return base
                return u

            def chapitre_quitte() -> bool:
                return _chapitre_path(page.url.split("?")[0].split("#")[0]) != _chapitre_path(url_depart)

            if mode_strip:
                pos0 = page.evaluate(POS_JS)
                if getattr(args, "page_1", False) and pos0[0] > 0:
                    page.evaluate("() => { const e = document.querySelector('[data-mf-defile]');"
                                  " if (e) e.scrollTo(0, 0); else window.scrollTo(0, 0); }")
                    page.wait_for_timeout(1500)
                    log_evt("départ", "retour en haut du défilement (--page-1)")
                elif pos0[0] > pos0[2] * 0.5:
                    notes.append("capture démarrée en cours de défilement (le début du chapitre "
                                 "n'est pas capturé ; --page-1 pour tout prendre)")
                    log_evt("départ", "en cours de défilement", position=pos0[0])
                # v0.6.2 (24/09, Solo Leveling vol.1) : le plafond FIXE de 400 pas (x 70 % d'ecran ~ 356 000 px)
                # arretait un volume webtoon de 903 000 px a 39 %, EN SILENCE (« terminée », 0 note). Le plafond
                # suit maintenant la hauteur reelle (relue a chaque pas : elle grandit au chargement) ; s'il est
                # atteint quand meme, c'est ecrit en toutes lettres.
                # v0.7.4 (25/09, Quang : « gagner du temps, mais sur a 100 % ») : MODE RAPIDE, automatique et prudent.
                # Si TOUTES les images de la page sont DEJA chargees au depart (mesure : un site de la secondaire 145/145, manga-scantrad
                # 14/14 ; ni AnimoFlix ni MANGA Plus), l'attente fixe de 1,2 s par pas devient 0,4 s -- et elle remonte
                # jusqu'a 1,2 s (comme avant) des qu'une image a l'ecran n'est pas prete ou que la page change de hauteur
                # (connexion lente). Jamais plus lent qu'avant. A la fin : toute image de la largeur des pages non prise
                # = ECHEC ecrit (alerte « capture incomplete » de l'app). Coupe-circuit : MANGA_FETCH_RAPIDE=0.
                IMGS_JS = """() => [...document.images].filter(i => !i.closest('#comments, .comments, .comments-list-wrapper, .comment, [id^="comment"], .disqus, #disqus_thread')
                    && (i.currentSrc || i.src) && !(i.currentSrc || i.src).startsWith('data:'))"""
                depart = page.evaluate("() => { const t = (" + IMGS_JS + ")(); return [t.length, t.filter(i => i.complete && i.naturalWidth > 0).length,"
                                       " t.filter(i => i.naturalWidth > 250 && i.naturalHeight > 500).length]; }")
                rapide = os.environ.get("MANGA_FETCH_RAPIDE", "1") != "0" and depart[2] >= 3 and depart[1] == depart[0]
                PRET_JS = ("() => { const t = (" + IMGS_JS + ")().filter(i => { const r = i.getBoundingClientRect();"
                           " return r.bottom >= 0 && r.top <= innerHeight; }); return t.every(i => i.complete && i.naturalWidth > 0); }")
                log_evt("mode", "rapide (page préchargée)" if rapide else "attente fixe 1,2 s",
                        images=depart[0], chargees=depart[1], pages=depart[2])
                if rapide:
                    print("Mode rapide : les %d images de la page sont déjà chargées" % depart[0])
                TAILLE_JS = "() => [innerWidth, innerHeight]"
                taille0 = page.evaluate(TAILLE_JS)
                prec, stable, pas, fini = None, 0, 0, False
                while True:
                    if chapitre_quitte():
                        notes.append("fin : le lecteur est passé au chapitre suivant")
                        log_evt("fin", "chapitre suivant atteint (bande défilante)")
                        fini = True
                        break
                    collecter()
                    h_avant = page.evaluate(POS_JS)[1]
                    page.evaluate(DEFILE_JS)
                    if rapide and page.evaluate(TAILLE_JS) != taille0:
                        # fenetre REDIMENSIONNEE pendant la capture (mesure 25/09 : 1 bande perdue en rapide, 0 a l'attente
                        # fixe) -> retour a l'attente d'avant pour tout le chapitre, et un pas en ARRIERE pour reprendre
                        rapide = False
                        page.evaluate("() => { const e = document.querySelector('[data-mf-defile]');"
                                      " if (e) e.scrollBy(0, -e.clientHeight * 0.7); else window.scrollBy(0, -innerHeight * 0.7); }")
                        log_evt("mode", "fenêtre redimensionnée : attente fixe 1,2 s pour la suite du chapitre")
                        print("Fenêtre redimensionnée : retour à l'attente normale pour ce chapitre")
                    if rapide:
                        page.wait_for_timeout(400)
                        for _ in range(8):                    # jusqu'a 1,2 s au total : l'attente d'avant
                            if page.evaluate(PRET_JS) and page.evaluate(POS_JS)[1] == h_avant:
                                break
                            page.wait_for_timeout(100)
                    else:
                        page.wait_for_timeout(1200)
                    pos = page.evaluate(POS_JS)
                    pas += 1
                    if prec is not None and pos[0] == prec[0] and pos[1] == prec[1]:
                        stable += 1          # ni position ni hauteur ne bougent : bas atteint
                        if stable >= 4:
                            collecter()
                            fini = True
                            break
                    else:
                        stable = 0
                    prec = pos
                    plafond = min(PLAFOND_PAS_ABSOLU, max(400, int(pos[1] / max(1, pos[2] * 0.7) * 1.5) + 50))
                    if pas >= plafond:
                        break
                if rapide and fini and vues:
                    _l = [v["w"] for v in vues.values()]
                    W = max(set(_l), key=_l.count)
                    manque = page.evaluate("(W) => (" + IMGS_JS + ")().filter(i => i.naturalWidth === W && i.naturalHeight >= 60)"
                                           ".map(i => i.src)", W)
                    manque = [u for u in dict.fromkeys(manque) if u not in vues and u not in ECARTEES]
                    if manque:
                        notes.append("ECHEC : mode rapide -- %d image(s) de la page non capturée(s) -- relancer avec --force "
                                     "(MANGA_FETCH_RAPIDE=0 pour l'attente d'avant)" % len(manque))
                        log_evt("fin", "CONTROLE mode rapide : images manquantes", n=len(manque), exemple=manque[0][:80])
                    else:
                        log_evt("contrôle", "mode rapide : toutes les images de la page sont capturées", pages=len(vues))
                if not fini:
                    notes.append("ECHEC : capture ARRÊTÉE avant la fin (%d pas, position %d sur %d px) -- "
                                 "relancer avec --force" % (pas, pos[0], pos[1]))
                    log_evt("fin", "PLAFOND DE DEFILEMENT atteint avant le bas", pas=pas, position=pos[0], hauteur=pos[1])
            else:
                # v0.6.3 (24/09) : comme la bande defilante, la fin normale = plus rien de nouveau ou chapitre
                # suivant. Les anciennes limites (500 pages, 12 min) coupaient un gros tome EN SILENCE (« terminée ») :
                # elles deviennent des garde-fous larges, et les atteindre = ECHEC ecrit.
                sterile, debut_pager, mode_clic, cote, cotes_essayes = 0, time.time(), False, 0.75, set()
                fini, tours = False, 0
                while True:
                    tours += 1
                    if chapitre_quitte():
                        notes.append("fin : le lecteur est passé au chapitre suivant")
                        log_evt("fin", "chapitre suivant atteint (page par page)")
                        fini = True
                        break
                    collecter()
                    n_avant = len(vues)
                    if not mode_clic and sterile >= 2:
                        # Les flèches ne font rien (MANGA Plus n'écoute pas le clavier,
                        # mesuré 21/09) → navigation par CLIC.
                        mode_clic = True
                        log_evt("navigation", "bascule en clic (flèches sans effet)")
                    if mode_clic:
                        # v0.3.0 : le sens dépend du SITE (Quang 21/09 : sur MANGA Plus, clic à
                        # GAUCHE = avancer, sens japonais ; l'inverse de MangaDex). Droite d'abord ;
                        # si rien ne vient, gauche. Le côté qui a donné une page est gardé.
                        # (v0.2 ne cliquait qu'UNE fois puis revenait aux flèches.)
                        if sterile >= 4 and 0.25 not in cotes_essayes:
                            cote, sterile = 0.25, 2
                            log_evt("navigation", "clic à gauche (sens de lecture japonais ?)")
                        cotes_essayes.add(cote)
                        x, y = page.evaluate(f"() => [Math.round(innerWidth * {cote}), Math.round(innerHeight * 0.5)]")
                        page.mouse.click(x, y)
                    else:
                        page.keyboard.press("ArrowRight")
                    page.wait_for_timeout(1600)
                    if chapitre_quitte():
                        notes.append("fin : le lecteur est passé au chapitre suivant")
                        log_evt("fin", "chapitre suivant atteint (après pression)")
                        fini = True
                        break
                    collecter()
                    if len(vues) == n_avant:
                        sterile += 1
                        if sterile >= 5 and len(vues) > 0:
                            fini = True
                            break  # plus rien de nouveau ET on a des pages : fin de chapitre
                        if sterile >= 20 and len(vues) == 0:
                            print("Abandon : le lecteur ne charge aucune page "
                                  "(rate-limit ? chapitre vide ? onglet cassé ?)")
                            log_evt("abandon", "aucune page chargée après 20 itérations",
                                    onglet=page.url[:100])
                            shutil.rmtree(dest, ignore_errors=True)
                            return 2
                    else:
                        sterile = 0
                    if tours >= PLAFOND_TOURS_PAGER or time.time() - debut_pager > PLAFOND_S_PAGER:
                        break
                if not fini:
                    notes.append("ECHEC : capture ARRÊTÉE avant la fin (%d pages en %d tours, %d min) -- relancer avec --force"
                                 % (len(vues), tours, (time.time() - debut_pager) // 60))
                    log_evt("fin", "GARDE-FOU page par page atteint avant la fin", pages=len(vues), tours=tours,
                            s=int(time.time() - debut_pager))

            # ordre d'insertion du dict = ordre de découverte = ordre de lecture
            # (pager : page par page ; strip : au fil du scroll vers le bas)
            uniques = list(vues.values())

            def echec_propre(msg: str) -> int:
                DERNIER["echec"] = msg                        # v0.8.3 : lu par la serie (chapitre annonce sans image)
                print(msg)
                print(f"Le dossier partiel est retiré : {dest}")
                log_evt("échec", msg, dossier=dest)
                shutil.rmtree(dest, ignore_errors=True)
                return 2

            # Garde-fou : une page de manga fait plus de 800 px de haut. Si RIEN ne dépasse,
            # l'onglet capturé n'était pas un chapitre (page d'accueil, mauvais onglet).
            if not uniques:
                return echec_propre("ÉCHEC : aucune image détectée — le chapitre est-il affiché ?")
            if len(uniques) < 3:
                # v0.3.0 : BORUTO #001 (54 p.) sortait en « terminée pages=1 » — une capture
                # tronquée ne doit jamais être présentée comme réussie.
                return echec_propre(f"ÉCHEC : capture tronquée — {len(uniques)} page(s) seulement. "
                                    "Le lecteur n'a pas avancé : mode d'affichage non reconnu ?")
            # v0.8.2 (26/09, ch. 21 vecu : 222 tuiles de 720x700 capturees en entier puis rejetees) : un ruban en TUILES n'a
            # aucune image de 800 px. Il passe si >= 5 images de la meme largeur (>= 500 px) cumulent >= 4000 px de haut --
            # ce qu'aucune page d'accueil ni aucun mauvais onglet ne font.
            _lu = [im["w"] for im in uniques]
            _cu = max(set(_lu), key=_lu.count)
            _ruban = [im for im in uniques if im["w"] == _cu]
            ruban_tuiles = MODE_BANDE[0] and _cu >= 500 and len(_ruban) >= 5 and sum(im["h"] for im in _ruban) >= 4000
            if not any(im["h"] >= 800 for im in uniques) and not ruban_tuiles:
                return echec_propre("ÉCHEC : aucune image de page (hauteur >= 800 px) — "
                                    "l'onglet capturé ne semble pas contenir de chapitre "
                                    "(page d'accueil ? mauvais onglet ?)")

            # Largeurs atypiques : NOTE seulement, JAMAIS de suppression — une page étroite
            # peut être légitime (vraie page 567px supprimée par l'ancien filtre, mesuré
            # 18:22 grâce au journal détaillé). L'humain vérifie avec l'information.
            if len(uniques) >= 3:
                mediane = sorted(im["w"] for im in uniques)[len(uniques) // 2]
                for src, im in vues.items():
                    if im["w"] < 0.8 * mediane:
                        notes.append(f"page étroite ({im['w']}px vs médiane {mediane}) — à vérifier")
                        log_evt("note", "page étroite (gardée)", fichier=im["file"],
                                w=im["w"], mediane=mediane)

            # ⚠ PAS de détection de « doublons de résolution » par les dimensions : un
            # scanlateur mélange des largeurs au même ratio (800px ET 960px dans le même
            # chapitre OPM, mesuré 18:29) — le détecteur a supprimé de VRAIES pages
            # (5 capturées au lieu de 16). Si un vrai doublon data-saver survient un jour,
            # il faudra une comparaison de CONTENU, jamais les dimensions seules.

            pages_meta = [{"file": im["file"], "bytes": im["bytes"], "w": im["w"], "h": im["h"]}
                          for im in uniques]
            print(f"{len(uniques)} images de page capturées au fil du défilement.")
            notes = list(dict.fromkeys(notes))  # une même anomalie ne se répète pas dans le manifeste
            # source_url = l'URL de DÉPART (url_depart) : page.url a pu changer en fin de
            # capture (le lecteur passe au chapitre suivant → l'URL enregistrée était
            # parfois celle du chapitre d'APRÈS — bug découvert 18:39)
            write_manifest(dest, slug=resoudre_slug(args.out, args.title), title=args.title,
                           chapter=args.chapter, source="capture", source_url=url_source,
                           pages=pages_meta, notes=notes)
            log_event("capture", url=url_depart, title=args.title, chapter=str(args.chapter),
                      pages=len(pages_meta), echecs=sum(1 for n in notes if "ECHEC" in n))
            log_evt("capture", "terminée", pages=len(pages_meta), notes=len(notes), dossier=dest)
            print(f"OK : {len(pages_meta)}/{len(uniques)} pages -> {dest}")
            try:
                decouper_bandes(dest)                          # v0.5.0 : webtoon -> pages
            except Exception as e:
                notes.append(f"découpage webtoon impossible : {type(e).__name__} {str(e)[:80]}")
                log_evt("webtoon", f"découpage impossible {type(e).__name__}", err=str(e)[:120])
            if notes:
                print("Notes : " + " ; ".join(notes[:5]))
            return 0 if not notes else 3  # 3 = réussite avec avertissements
        code = un_chapitre(args)
        suite = max(0, min(SERIE_FILET, int(getattr(args, "suite", 0) or 0)))   # v0.8.0 : 50 -> 300
        jusqua = getattr(args, "jusqua", None)
        try:
            jusqua = float(jusqua) if jusqua not in (None, "") else None
        except ValueError:
            jusqua = None
        fin = bool(getattr(args, "jusqua_fin", False))      # v0.8.0 : « jusqu'au dernier paru »
        if fin:
            jusqua = float("inf")                            # aucune borne : les trous de numerotation sont toleres (comme --jusqua)
        if not suite and jusqua is None:
            return code
        if code not in (0, 3):
            print("SÉRIE : arrêt — le premier chapitre a échoué.")
            return code
        faits, chap, arret = [str(args.chapter)], str(args.chapter), None
        deja_la = [str(args.chapter)] if DERNIER.get("deja_la") else []
        while jusqua is not None or len(faits) - 1 < suite:   # v0.8.0 : plus de plafond de 50 ; filet commun ci-dessous
            # v0.7.5 (Quang 25/09 22h01) : l'objectif ATTEINT s'arrete ICI. Avant, on cherchait quand meme le suivant : au
            # dernier chapitre paru (objectif 54, rien apres) le bilan disait « aucun chapitre apres le 54 » -> « objectif non
            # tenu » et une notification « le ch. 54 n'est pas encore paru » alors qu'il venait d'etre capture.
            if not fin and jusqua is not None and _num(chap) >= jusqua:
                arret = f"jusqu'au ch. {_format_num(jusqua)} : fait"
                break
            # v0.7.6 (maquette_arret_v1, validee 25/09) : « ⏹ Arrêter après ce chapitre » -- lu ENTRE deux chapitres, jamais au
            # milieu. On repere quand meme le SUIVANT (numero + adresse) : c'est lui que la reprise existante rouvrira.
            if os.path.exists(ARRET_FICHIER):
                try: os.remove(ARRET_FICHIER)
                except OSError: pass
                try:
                    num, raison = chapitre_suivant(page, DERNIER.get("url", page.url), chap, jusqua,
                                                  bool(getattr(args, "sans_intermediaires", False)))
                except Exception as e:
                    num, raison = None, f"chapitre suivant introuvable ({type(e).__name__})"
                if num is not None:
                    log_evt("série", f"chapitre suivant {num}", onglet=page.url)
                    arret = f"arrêtée à ta demande après le ch. {chap} — reprise au ch. {num}"
                else:
                    arret = f"arrêtée à ta demande après le ch. {chap} — {raison}"
                log_evt("série", "arrêt demandé", apres=chap)
                break
            page.wait_for_timeout(SERIE_PAUSE_MS)              # v0.8.0 : politesse, chapitres sautes compris
            try:
                num, raison = chapitre_suivant_tenace(page, DERNIER.get("url", page.url), chap, jusqua,   # v0.8.4 : 3 essais
                                                      bool(getattr(args, "sans_intermediaires", False)))
            except Exception as e:
                num, raison = None, f"passage au chapitre suivant impossible ({type(e).__name__}: {str(e)[:120]})"
            if num is None:
                arret = raison
                if raison and "aucun chapitre après" in raison:        # v0.8.0 : MangaDex prefixe « MangaDex : »
                    fin = marque_final(page)                     # v0.7.5 : « Final » sur la page du dernier chapitre ?
                    if fin:
                        arret += f" — le ch. {chap} est marqué « {fin} » (série terminée)"
                        log_evt("série", "chapitre FINAL reconnu", chapitre=chap, marque=fin)
                break
            if num in faits or _num(num) <= _num(chap):       # v0.8.0 : jamais en arriere (garde explicite)
                arret = f"arrêt de sécurité : le site propose le ch. {num} après le {chap} (retour en arrière)"
                log_evt("sécurité", "retour en arrière", apres=chap, propose=num)
                break
            if fin and _num(num) - _num(chap) > SERIE_SAUT_MAX:
                log_evt("série", f"chapitre suivant {num}", onglet=page.url[:100])     # adresse pour la reprise
                arret = (f"arrêt de sécurité : le site propose le ch. {num} juste après le {chap} (saut suspect)"
                         f" — reprise au ch. {num}")
                log_evt("sécurité", "saut suspect", apres=chap, propose=num)
                break
            if len(faits) > SERIE_FILET:                     # v0.8.0 : dernier filet, TOUS les modes (Quang 23h51) = 300 d'ecart
                log_evt("série", f"chapitre suivant {num}", onglet=page.url[:100])
                arret = f"arrêt de sécurité : {SERIE_FILET} chapitres en un lancement — reprise au ch. {num}"
                log_evt("sécurité", "filet atteint", chapitres=len(faits), suivant=num)
                break
            print(f"=== Chapitre suivant : {num} ===")
            log_evt("série", f"chapitre suivant {num}", onglet=page.url[:100])
            page.bring_to_front()
            a2 = argparse.Namespace(**vars(args))
            a2.chapter, a2.force, a2.page_1, a2.enchaine = num, False, True, True
            c2 = un_chapitre(a2)
            if c2 not in (0, 3) and fin and DERNIER.get("echec", "").startswith("ÉCHEC : aucune image détectée"):
                # v0.8.3 (26/09, ch. vecu : le site ANNONCE le ch. 25 mais sa page n'a aucune image -- pas encore publie) :
                # en « jusqu'au dernier paru », c'est la fin de ce qui est lisible, pas une panne. Seul ce cas-la (AUCUNE
                # image) : une capture tronquee, un echec de controle, restent des echecs.
                arret = f"aucun chapitre après le {chap} sur ce site (le ch. {num} est annoncé mais sans aucune image : pas encore publié ?)"
                log_evt("série", "chapitre annoncé sans image = fin du lisible", apres=chap, annonce=num)
                break
            if c2 not in (0, 3):
                arret = f"le chapitre {num} a échoué (code {c2})"
                break
            if DERNIER.get("deja_la"):
                deja_la.append(num)
            else:
                ident = _meme_contenu(args.out, args.title, chap, num)
                if ident:                                     # v0.8.0 : le site a resservi le chapitre precedent
                    cote = _mettre_de_cote(chap_dir(args.out, args.title, num), "doublon")
                    arret = (f"arrêt de sécurité : le ch. {num} a les mêmes images que le {chap} ({ident})"
                             f" — reprise au ch. {num}")
                    log_evt("sécurité", "contenu identique", chapitre=num, precedent=chap, mis_de_cote=cote or "")
                    break
            faits.append(num)
            chap = num
            if c2 == 3:
                code = 3
        if arret is None and jusqua is None:
            arret = f"{suite} chapitre(s) suivant(s) demandé(s) : fait"
        if deja_la:
            print("DEJA LA : " + ", ".join(deja_la))           # v0.8.0 : lu par le proxy (bilan « N capturés, M déjà là »)
        print(f"SÉRIE : {len(faits)} chapitre(s) : {', '.join(faits)}" + (f" — arrêt : {arret}" if arret else ""))
        log_evt("série", "terminée", chapitres=",".join(faits), deja_la=",".join(deja_la), arret=arret or "")
        if fin:                                               # v0.8.0 : tenu = le site n'a plus de suite
            demande_non_tenue = "aucun chapitre après" not in (arret or "")
        else:
            demande_non_tenue = ((jusqua is not None and _num(faits[-1]) < jusqua)
                                 or (jusqua is None and len(faits) - 1 < suite))
        return 3 if (code == 3 or demande_non_tenue) else 0


# --------------------------------------------------------------------------- canal 3 : import

def import_src(args) -> int:
    src = os.path.abspath(args.chemin)
    dest = chap_dir(args.out, args.title, args.chapter)
    pages_meta, notes = [], []
    if zipfile.is_zipfile(src):  # CBZ (ou zip d'images)
        with zipfile.ZipFile(src) as z:
            noms = sorted(n for n in z.namelist() if os.path.splitext(n)[1].lower() in IMG_EXTS)
            for i, n in enumerate(noms, 1):
                data = z.read(n)
                nom = save_page(dest, i, data)
                pages_meta.append({"file": nom, "bytes": len(data)})
    elif os.path.isdir(src):
        fichiers = sorted(f for f in os.listdir(src)
                          if os.path.splitext(f)[1].lower() in IMG_EXTS
                          and os.path.isfile(os.path.join(src, f)))  # pas les sous-dossiers
        for i, f in enumerate(fichiers, 1):
            data = open(os.path.join(src, f), "rb").read()
            nom = save_page(dest, i, data)
            pages_meta.append({"file": nom, "bytes": len(data)})
    elif os.path.isfile(src):
        data = open(src, "rb").read()
        nom = save_page(dest, 1, data)
        pages_meta.append({"file": nom, "bytes": len(data)})
    else:
        print(f"Introuvable : {src}")
        return 1
    if not pages_meta:
        print("Aucune image trouvée dans la source.")
        return 1
    write_manifest(dest, slug=slugify(args.title), title=args.title, chapter=args.chapter,
                   source="import", source_url=src, pages=pages_meta, notes=notes)
    log_event("import", src=src, pages=len(pages_meta))
    print(f"OK : {len(pages_meta)} pages -> {dest}")
    return 0


# --------------------------------------------------------------------------- vérification

def verify(dossier: str) -> int:
    """Contrôle manifeste <-> fichiers + complétude contre l'API MangaDex si applicable.
    Sortie 0 = intègre, 1 = incohérence."""
    mp = os.path.join(dossier, "manifest.json")
    if not os.path.exists(mp):
        print(f"KO : pas de manifest.json dans {dossier}")
        return 1
    m = json.load(open(mp, encoding="utf-8"))
    problemes = []
    for pg in m["pages"]:
        p = os.path.join(dossier, pg["file"])
        if not os.path.exists(p):
            problemes.append(f"manquant : {pg['file']}")
        elif os.path.getsize(p) != pg["bytes"]:
            problemes.append(f"taille != : {pg['file']} ({os.path.getsize(p)} != {pg['bytes']})")
        elif pg["file"].endswith(".bin"):
            problemes.append(f"format inconnu : {pg['file']}")
    orphelins = [f for f in os.listdir(dossier)
                 if os.path.splitext(f)[1].lower() in IMG_EXTS
                 and f not in {pg["file"] for pg in m["pages"]}]
    problemes += [f"orphelin : {f}" for f in orphelins]
    if problemes:
        print(f"KO ({len(problemes)}) : " + " ; ".join(problemes[:8]))
        return 1
    print(f"OK : {len(m['pages'])} pages cohérentes avec le manifeste.")

    # Complétude : contre le compte OFFICIEL MangaDex quand la source est un chapitre
    # (demande Quang 18:39 : « le piège, c'est de vérifier si le chapitre est complet »)
    u = (m.get("source_url") or "").split("?")[0].rstrip("/")
    if "mangadex.org/chapter/" in u:
        try:
            morceaux = u.split("/chapter/")[1].split("/")
            cid = morceaux[0] if len(morceaux) == 1 else morceaux[0]
            r = requests.get(f"https://api.mangadex.org/chapter/{cid}",
                             headers={"User-Agent": UA}, timeout=15)
            r.raise_for_status()
            officiel = r.json()["data"]["attributes"]["pages"]
            depart = 1
            for n in m.get("notes", []):
                dm = re.search(r"démarrée à la page (\d+)", n)
                if dm:
                    depart = int(dm.group(1))
            attendu = max(0, officiel - (depart - 1))
            verdict = "COMPLET" if len(m["pages"]) >= attendu else f"INCOMPLET ({len(m['pages'])}/{attendu})"
            print(f"Complétude : {len(m['pages'])} pages capturées / {attendu} attendues "
                  f"(chapitre officiel : {officiel} pages, départ page {depart}) → {verdict}")
        except Exception as e:
            print(f"(complétude non vérifiée : {type(e).__name__})")
    return 0


def lister_sources(out: str, titres_seuls: bool = False) -> int:
    """Vue des mangas déjà présents dans sources/ (demande Quang 18:39)."""
    if not os.path.isdir(out):
        print(f"Aucun dossier {out} — rien de capturé pour l'instant.")
        return 0
    total_ch, total_pg = 0, 0
    for d in sorted(os.listdir(out)):
        chemin = os.path.join(out, d)
        if not os.path.isdir(chemin):
            continue
        chapitres = sorted(c for c in os.listdir(chemin) if c.startswith("ch_"))
        if not chapitres:
            continue
        if titres_seuls:
            print(f"  {d} ({len(chapitres)} chapitre{'s' if len(chapitres) > 1 else ''})")
            total_ch += len(chapitres)
            continue
        print(f"{d} :")
        for c in chapitres:
            mp = os.path.join(chemin, c, "manifest.json")
            if os.path.exists(mp):
                m = json.load(open(mp, encoding="utf-8"))
                n = len(m.get("pages", []))
                extra = f" | {len(m.get('notes', []))} note(s)" if m.get("notes") else ""
                print(f"   ch. {c[3:]:>5} | {n:>3} pages | {m.get('captured_at', '?')[:10]} "
                      f"| {m.get('source', '?')}{extra}")
                total_pg += n
            else:
                fichiers = [f for f in os.listdir(os.path.join(chemin, c)) if f.startswith("page_")]
                print(f"   ch. {c[3:]:>5} | {len(fichiers):>3} pages | SANS MANIFESTE "
                      f"(capture interrompue ?)")
                total_pg += len(fichiers)
            total_ch += 1
    print(f"\nTotal : {total_ch} chapitre(s), {total_pg} page(s) dans {out}")
    return 0


# --------------------------------------------------------------------------- fenêtre dédiée


def profil_sans_synchro(profil):
    """S3 (24/09) : un profil Edge qui ne se connecte PAS au compte Microsoft et ne synchronise RIEN (sinon son
    historique remonterait sur les autres appareils de Quang : constate, Edge le proposait d'office). A appeler
    navigateur ferme ; complete par --disable-sync. Verifie le 24/09 : edge://settings/profiles/sync -> « Pas en
    cours de synchronisation »."""
    f = os.path.join(profil, "Default", "Preferences")
    os.makedirs(os.path.dirname(f), exist_ok=True)
    try:
        p = json.load(open(f, encoding="utf-8"))
    except Exception:
        p = {}
    p.setdefault("signin", {}).update(allowed=False, allowed_on_next_startup=False)
    p.setdefault("sync", {}).update(requested=False)
    p["sync"].pop("has_setup_completed", None); p["sync"].pop("keep_everything_synced", None)
    json.dump(p, open(f, "w", encoding="utf-8"))


def launch_edge() -> int:
    for cible in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                  r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"):
        if os.path.exists(cible):
            break
    else:
        print("Edge introuvable.")
        return 1
    os.makedirs(EDGE_PROFILE, exist_ok=True)
    # v0.6.9 (Quang 24/09 19h10) : TOUTE fenetre de capture, principale comprise (elle synchronisait tout sur le compte
    # Microsoft). MANGA_CAPTURE_SANS_SYNCHRO=0 pour revenir a l'ancien comportement.
    sans_synchro = os.environ.get("MANGA_CAPTURE_SANS_SYNCHRO", "1") != "0"
    if sans_synchro:
        profil_sans_synchro(EDGE_PROFILE)
    # v0.6.4 (Quang 24/09) : la fenetre s'OUVRE a la place choisie par Quang (sur le cote, en partie hors de l'ecran,
    # assez grande pour capturer : mesure 24/09). Meme fichier que les boutons « Ranger » / « Memoriser » de l'app
    # (scripts/cdp_mini.py). Ensuite, plus rien ne bouge sans un clic de Quang.
    place = {"left": 2389, "top": 1344, "width": 1052, "height": 1360}
    try:
        with open(os.path.join(DATA_DIR, "fenetre.json"),
                  encoding="utf-8") as f:
            place.update(json.load(f).get("place") or {})
    except Exception:
        pass
    import subprocess
    subprocess.Popen([cible, "--remote-debugging-port=%d" % EDGE_PORT,
                      # anti-occlusion : une fenêtre COUVERTE par d'autres continue
                      # d'être rendue (sinon Edge la throttle et la capture casse)
                      "--disable-features=CalculateNativeWinOcclusion",
                      f"--user-data-dir={EDGE_PROFILE}",
                      *(["--disable-sync"] if sans_synchro else []),
                      "--no-first-run", "--no-default-browser-check",
                      "--window-size=%d,%d" % (place["width"], place["height"]),
                      "--window-position=%d,%d" % (place["left"], place["top"]),
                      "https://mangadex.org/"])
    print("Fenêtre dédiée lancée (CDP port %d, profil persistant)." % EDGE_PORT)
    return 0


# --------------------------------------------------------------------------- CLI

def main() -> int:
    # UTF-8 forcé : sous Windows, un print français en console cp1252 tue le script
    # (piège payé le 21/09 — ne pas le retirer).
    for flux in (sys.stdout, sys.stderr):
        if flux and hasattr(flux, "reconfigure"):
            flux.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=f"manga-fetch v{VERSION} — sourcing pour Manga Studio")
    ap.add_argument("--version", action="version", version=f"manga-fetch {VERSION}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search", help="rechercher un titre sur MangaDex")
    s.add_argument("requete")

    s = sub.add_parser("chapters", help="lister les chapitres hébergés d'un titre")
    s.add_argument("manga_id")
    s.add_argument("--lang", default="fr")

    s = sub.add_parser("download", help="télécharger des chapitres (MangaDex)")
    s.add_argument("manga_id")
    s.add_argument("--chapter", type=str, default=None)
    s.add_argument("--last", type=int, default=1)
    s.add_argument("--all", action="store_true")
    s.add_argument("--lang", default="fr")
    s.add_argument("--out", default=DEFAULT_OUT)
    s.add_argument("--force", action="store_true")

    s = sub.add_parser("capture", help="capturer le chapitre affiché dans la fenêtre dédiée")
    s.add_argument("--tab", default=None,
                   help="filtre d'URL, pour les scripts (défaut : l'onglet ACTIF de la fenêtre)")
    s.add_argument("--page-1", action="store_true",
                   help="revenir à la page 1 avant de capturer (défaut : depuis la page affichée)")
    s.add_argument("--force", action="store_true",
                   help="remplacer un chapitre déjà capturé sans demander")
    s.add_argument("--suite", type=int, default=0,
                   help="v0.4.0 : capturer AUSSI les N chapitres suivants (MangaDex, MANGA Plus)")
    s.add_argument("--sans-intermediaires", action="store_true",
                   help="v0.4.1 : sauter les chapitres à décimale (298.5...) pendant l'enchaînement")
    s.add_argument("--jusqua", default=None,
                   help="v0.4.0 : enchaîner jusqu'au chapitre Y inclus (les trous sont sautés)")
    s.add_argument("--jusqua-fin", action="store_true",
                   help="v0.8.0 : enchaîner jusqu'au dernier chapitre paru sur le site (sécurités : saut > 10, "
                        "contenu identique, filet de 300 chapitres, pause de 3 s entre deux chapitres)")
    s.add_argument("--title", required=True)
    s.add_argument("--chapter", required=True)
    s.add_argument("--out", default=DEFAULT_OUT)

    s = sub.add_parser("import", help="importer images/CBZ déjà sur disque")
    s.add_argument("chemin")
    s.add_argument("--title", required=True)
    s.add_argument("--chapter", required=True)
    s.add_argument("--out", default=DEFAULT_OUT)

    s = sub.add_parser("decouper", help="v0.5.0 : découper les bandes webtoon d'un chapitre en pages")
    s.add_argument("dossier")

    s = sub.add_parser("verify", help="contrôler manifeste <-> fichiers")
    s.add_argument("dossier")

    s = sub.add_parser("liste", help="vue des mangas déjà présents dans sources/")
    s.add_argument("--titres", action="store_true", help="une ligne par titre (pour le .bat)")

    sub.add_parser("launch-edge", help="(re)lancer la fenêtre Edge dédiée")

    args = ap.parse_args()
    if args.cmd == "search":
        res = md_search(args.requete)
        for r in res:
            fr = " [FR]" if r["fr"] else ""
            print(f"  {r['id']} | {r['titre'][:50]}{fr} | {len(r['langues'])} langues")
        return 0 if res else 1
    if args.cmd == "chapters":
        for c in md_chapters(args.manga_id, args.lang)[:30]:
            a = c["attributes"]
            print(f"  ch {a.get('chapter') or '?'} | {a['translatedLanguage']} | {a['pages']} pages | {c['id'][:8]}")
        return 0
    if args.cmd == "download":
        return md_download(args.manga_id, args)
    if args.cmd == "capture":
        return capture(args)
    if args.cmd == "import":
        return import_src(args)
    if args.cmd == "decouper":
        r = decouper_bandes(args.dossier)
        if r is None:
            print("Rien à découper (pas de bande, ou déjà découpé).")
        return 0
    if args.cmd == "verify":
        return verify(args.dossier)
    if args.cmd == "liste":
        return lister_sources(DEFAULT_OUT, getattr(args, "titres", False))
    if args.cmd == "launch-edge":
        return launch_edge()
    return 1


if __name__ == "__main__":
    sys.exit(main())
