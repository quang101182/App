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

VERSION = "0.1.9"
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
    return os.path.join(out, slugify(title), f"ch_{str(chapter).replace('/', '-')}")


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
        print(f"Onglet : {page.url[:80]}")
        log_evt("capture", "démarrage", titre=args.title, chapitre=str(args.chapter),
                methode_onglet=methode_choix, onglet=page.url[:100])
        page.bring_to_front()  # un onglet de fond est THROTTLE par le navigateur :
        # son chargement ralentit et la capture part dans le vide (mesuré : « Loading... »)

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
            pret = page.evaluate(
                "() => Array.from(document.images)"
                ".some(i => i.naturalHeight > 800 && i.naturalWidth > 250)")
            if pret:
                break
            page.wait_for_timeout(1000)

        # Défilement progressif AVEC collecte à la volée.
        # ⚠ Les lecteurs virtualisés (MangaDex inclus) DÉCHARGENT les images hors écran :
        # scroller tout puis collecter ne ramasse que ce qui reste à l'écran
        # (mesuré : 4 pages sur 22). On attrape chaque page PENDANT qu'elle vit.
        dest = chap_dir(args.out, args.title, args.chapter)
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

        def extraire_data(src: str) -> bytes:
            """Pleine résolution si possible (fetch page / requests), sinon SCREENSHOT de
            l'élément. Certains sites bloquent fetch(blob:) par CSP alors que l'image
            s'affiche parfaitement (MANGA Plus, mesuré 21/09) : le screenshot est la
            parade universelle — qualité = affichage, ce qui suffit à la narration."""
            if src.startswith(("blob:", "data:")):
                try:
                    return base64.b64decode(page.evaluate(FETCH_JS, src))
                except Exception:
                    pass  # CSP ou blob révoqué → screenshot
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
            return el.screenshot()  # PNG à la taille d'affichage

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
        mode_strip = h_doc > h_ecran * 2.5
        print(f"Mode {'bande défilante' if mode_strip else 'page par page'} "
              f"(doc {h_doc}px / écran {h_ecran}px)")
        log_evt("mode", "bande défilante" if mode_strip else "page par page",
                doc=h_doc, ecran=h_ecran)

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
            hauteur_prec, stable = 0, 0
            for _ in range(300):
                if chapitre_quitte():
                    notes.append("fin : le lecteur est passé au chapitre suivant")
                    log_evt("fin", "chapitre suivant atteint (bande défilante)")
                    break
                collecter()
                page.evaluate("window.scrollBy(0, window.innerHeight * 0.7)")
                page.wait_for_timeout(1200)
                h = page.evaluate("() => document.documentElement.scrollHeight")
                if h == hauteur_prec:
                    stable += 1
                    if stable >= 4:
                        break
                else:
                    stable = 0
                    hauteur_prec = h
        else:
            sterile, debut_pager, mode_clic = 0, time.time(), False
            for _ in range(500):
                if chapitre_quitte():
                    notes.append("fin : le lecteur est passé au chapitre suivant")
                    log_evt("fin", "chapitre suivant atteint (page par page)")
                    break
                collecter()
                n_avant = len(vues)
                if not mode_clic and sterile >= 2:
                    # Les flèches ne font rien (MANGA Plus n'écoute pas le clavier,
                    # mesuré 21/09) → navigation par CLIC à droite de l'écran.
                    x, y = page.evaluate("() => [Math.round(innerWidth * 0.75), Math.round(innerHeight * 0.5)]")
                    page.mouse.click(x, y)
                    mode_clic = True
                    log_evt("navigation", "bascule en clic (flèches sans effet)")
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
        write_manifest(dest, slug=slugify(args.title), title=args.title, chapter=args.chapter,
                       source="capture", source_url=page.url, pages=pages_meta, notes=notes)
        log_event("capture", url=page.url, title=args.title, chapter=str(args.chapter),
                  pages=len(pages_meta), echecs=sum(1 for n in notes if "ECHEC" in n))
        log_evt("capture", "terminée", pages=len(pages_meta), notes=len(notes), dossier=dest)
        print(f"OK : {len(pages_meta)}/{len(uniques)} pages -> {dest}")
        if notes:
            print("Notes : " + " ; ".join(notes[:5]))
        return 0 if not notes else 3  # 3 = réussite avec avertissements


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
    """Contrôle manifeste <-> fichiers. Sortie 0 = intègre, 1 = incohérence."""
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
    if args.cmd == "launch-edge":
        return launch_edge()
    return 1


if __name__ == "__main__":
    sys.exit(main())
