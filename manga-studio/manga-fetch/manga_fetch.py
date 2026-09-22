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

VERSION = "0.4.1"
# ⚠ ASCII pur, JAMAIS d'em-dash ni d'accent : les headers HTTP sont encodés latin-1
# (crash UnicodeEncodeError mesuré le 21/09 — ne pas "embellir" cette chaîne).
UA = f"manga-fetch/{VERSION} (Manga Studio sourcing, usage personnel)"
MDX_API = "https://api.mangadex.org"
EDGE_CDP = "http://localhost:9223"
EDGE_PROFILE = os.path.join(os.environ.get("LOCALAPPDATA", "."), "manga-fetch-edge")
DATA_DIR = os.path.join(os.environ.get("LOCALAPPDATA", "."), "manga-fetch")
LOG_FILE = os.path.join(DATA_DIR, "fetch.log")
LOG_EVT = os.path.join(DATA_DIR, "events.log")  # journal DÉTAILLÉ (demande Quang 18/18)
DEFAULT_OUT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sources"))
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
    return None, "enchaînement des chapitres non pris en charge sur ce site (MangaDex et MANGA Plus seulement)"


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
            DERNIER["url"] = page.url.split("?")[0].split("#")[0]
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
                    return 0
                print("Remplacement demandé.")
            os.makedirs(dest, exist_ok=True)
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
                nouvelles = page.evaluate("""() => Array.from(document.images)
                    .filter(i => i.naturalWidth > 250 && i.naturalHeight > 500
                        && (i.naturalWidth / i.naturalHeight < 0.93
                            || i.naturalWidth / i.naturalHeight > 1.15))
                    .filter(i => { const r = i.getBoundingClientRect();
                                   return r.bottom > 80 && r.top < window.innerHeight - 80; })
                    .map(i => ({src: i.src, top: Math.round(i.getBoundingClientRect().top + window.scrollY),
                                w: i.naturalWidth, h: i.naturalHeight}))""")
                for im in nouvelles:
                    if im["src"] in vues:
                        continue
                    try:
                        data = extraire_data(im["src"])
                        hsh = hashlib.sha1(data).hexdigest()
                        if hsh in vus_hashes:
                            continue  # même contenu déjà capturé (blob régénéré par le pager)
                        if len(data) < 10000:
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
            h_doc = page.evaluate("() => document.documentElement.scrollHeight")
            h_ecran = page.evaluate("() => window.innerHeight")
            # v0.3.0 : MANGA Plus en mode VERTICAL empile les 54 pages dans un BLOC qui défile,
            # le document faisant la hauteur de l'écran (mesuré 21/09 21h, BORUTO #001 : doc=1273
            # = écran → pris pour « page par page » → 1 seule page capturée, déclarée réussie).
            # On cherche donc aussi le plus grand bloc défilant ; on le marque pour le faire défiler.
            bloc = page.evaluate("""() => {
                let best = null, bh = 0;
                for (const el of document.querySelectorAll('*')) {
                    const oy = getComputedStyle(el).overflowY;
                    if (oy !== 'auto' && oy !== 'scroll') continue;
                    if (el.clientHeight < innerHeight * 0.5) continue;
                    if (el.scrollHeight > bh) { bh = el.scrollHeight; best = el; }
                }
                if (!best || best.scrollHeight <= best.clientHeight * 2.5) return null;
                best.setAttribute('data-mf-defile', '1');
                return [best.scrollHeight, best.clientHeight];
            }""")
            mode_strip = h_doc > h_ecran * 2.5 or bloc is not None
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
                prec, stable = None, 0
                for _ in range(400):
                    if chapitre_quitte():
                        notes.append("fin : le lecteur est passé au chapitre suivant")
                        log_evt("fin", "chapitre suivant atteint (bande défilante)")
                        break
                    collecter()
                    page.evaluate(DEFILE_JS)
                    page.wait_for_timeout(1200)
                    pos = page.evaluate(POS_JS)
                    if prec is not None and pos[0] == prec[0] and pos[1] == prec[1]:
                        stable += 1          # ni position ni hauteur ne bougent : bas atteint
                        if stable >= 4:
                            collecter()
                            break
                    else:
                        stable = 0
                    prec = pos
            else:
                sterile, debut_pager, mode_clic, cote, cotes_essayes = 0, time.time(), False, 0.75, set()
                for _ in range(500):
                    if chapitre_quitte():
                        notes.append("fin : le lecteur est passé au chapitre suivant")
                        log_evt("fin", "chapitre suivant atteint (page par page)")
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
                        break
                    collecter()
                    if len(vues) == n_avant:
                        sterile += 1
                        if sterile >= 5 and len(vues) > 0:
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
                    if time.time() - debut_pager > 720:  # garde-fou global : 12 min
                        notes.append("arrêt sur timeout global (12 min)")
                        break

            # ordre d'insertion du dict = ordre de découverte = ordre de lecture
            # (pager : page par page ; strip : au fil du scroll vers le bas)
            uniques = list(vues.values())

            def echec_propre(msg: str) -> int:
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
            if not any(im["h"] >= 800 for im in uniques):
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
                           chapter=args.chapter, source="capture", source_url=url_depart,
                           pages=pages_meta, notes=notes)
            log_event("capture", url=url_depart, title=args.title, chapter=str(args.chapter),
                      pages=len(pages_meta), echecs=sum(1 for n in notes if "ECHEC" in n))
            log_evt("capture", "terminée", pages=len(pages_meta), notes=len(notes), dossier=dest)
            print(f"OK : {len(pages_meta)}/{len(uniques)} pages -> {dest}")
            if notes:
                print("Notes : " + " ; ".join(notes[:5]))
            return 0 if not notes else 3  # 3 = réussite avec avertissements
        code = un_chapitre(args)
        suite = max(0, min(50, int(getattr(args, "suite", 0) or 0)))
        jusqua = getattr(args, "jusqua", None)
        try:
            jusqua = float(jusqua) if jusqua not in (None, "") else None
        except ValueError:
            jusqua = None
        if not suite and jusqua is None:
            return code
        if code not in (0, 3):
            print("SÉRIE : arrêt — le premier chapitre a échoué.")
            return code
        faits, chap, arret = [str(args.chapter)], str(args.chapter), None
        limite = 50 if jusqua is not None else suite
        while len(faits) - 1 < limite:
            try:
                num, raison = chapitre_suivant(page, DERNIER.get("url", page.url), chap, jusqua,
                                              bool(getattr(args, "sans_intermediaires", False)))
            except Exception as e:
                num, raison = None, f"passage au chapitre suivant impossible ({type(e).__name__}: {str(e)[:120]})"
            if num is None:
                arret = raison
                break
            print(f"=== Chapitre suivant : {num} ===")
            log_evt("série", f"chapitre suivant {num}", onglet=page.url[:100])
            page.bring_to_front()
            a2 = argparse.Namespace(**vars(args))
            a2.chapter, a2.force, a2.page_1, a2.enchaine = num, False, True, True
            c2 = un_chapitre(a2)
            if c2 not in (0, 3):
                arret = f"le chapitre {num} a échoué (code {c2})"
                break
            faits.append(num)
            chap = num
            if c2 == 3:
                code = 3
        if arret is None and jusqua is None:
            arret = f"{suite} chapitre(s) suivant(s) demandé(s) : fait"
        print(f"SÉRIE : {len(faits)} chapitre(s) : {', '.join(faits)}" + (f" — arrêt : {arret}" if arret else ""))
        log_evt("série", "terminée", chapitres=",".join(faits), arret=arret or "")
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

def launch_edge() -> int:
    for cible in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                  r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"):
        if os.path.exists(cible):
            break
    else:
        print("Edge introuvable.")
        return 1
    os.makedirs(EDGE_PROFILE, exist_ok=True)
    import subprocess
    subprocess.Popen([cible, "--remote-debugging-port=9223",
                      # anti-occlusion : une fenêtre COUVERTE par d'autres continue
                      # d'être rendue (sinon Edge la throttle et la capture casse)
                      "--disable-features=CalculateNativeWinOcclusion",
                      f"--user-data-dir={EDGE_PROFILE}",
                      "--no-first-run", "--no-default-browser-check",
                      "--window-size=1100,1500", "--window-position=60,40",
                      "https://mangadex.org/"])
    print("Fenêtre dédiée lancée (CDP port 9223, profil persistant).")
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
    s.add_argument("--title", required=True)
    s.add_argument("--chapter", required=True)
    s.add_argument("--out", default=DEFAULT_OUT)

    s = sub.add_parser("import", help="importer images/CBZ déjà sur disque")
    s.add_argument("chemin")
    s.add_argument("--title", required=True)
    s.add_argument("--chapter", required=True)
    s.add_argument("--out", default=DEFAULT_OUT)

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
    if args.cmd == "verify":
        return verify(args.dossier)
    if args.cmd == "liste":
        return lister_sources(DEFAULT_OUT, getattr(args, "titres", False))
    if args.cmd == "launch-edge":
        return launch_edge()
    return 1


if __name__ == "__main__":
    sys.exit(main())
