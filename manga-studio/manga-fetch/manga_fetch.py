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

VERSION = "0.1.0"
# ⚠ ASCII pur, JAMAIS d'em-dash ni d'accent : les headers HTTP sont encodés latin-1
# (crash UnicodeEncodeError mesuré le 21/09 — ne pas "embellir" cette chaîne).
UA = f"manga-fetch/{VERSION} (Manga Studio sourcing, usage personnel)"
MDX_API = "https://api.mangadex.org"
EDGE_CDP = "http://localhost:9223"
EDGE_PROFILE = os.path.join(os.environ.get("LOCALAPPDATA", "."), "manga-fetch-edge")
DATA_DIR = os.path.join(os.environ.get("LOCALAPPDATA", "."), "manga-fetch")
LOG_FILE = os.path.join(DATA_DIR, "fetch.log")
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
        page = None
        for ctx in browser.contexts:
            for pg in ctx.pages:
                if args.tab in pg.url:
                    page = pg
                    break
            if page:
                break
        if page is None:
            print(f"Aucun onglet contenant '{args.tab}' dans la fenêtre dédiée (CDP {EDGE_CDP}).")
            print("Ouvre le chapitre dans la fenêtre dédiée (launch-edge), puis relance.")
            return 1
        print(f"Onglet : {page.url[:80]}")
        page.bring_to_front()  # un onglet de fond est THROTTLE par le navigateur :
        # son chargement ralentit et la capture part dans le vide (mesuré : « Loading... »)

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
        pages_meta, notes = [], []
        vues: dict = {}           # src -> {ordre, top, w, h, data}
        vus_hashes: set = set()   # dedup par CONTENU : les pagers re-servent une page déjà
        # affichée sous un blob: neuf (mesuré : 30 images collectées pour 22 pages)

        def extraire_data(src: str) -> bytes:
            if src.startswith(("blob:", "data:")):
                b64 = page.evaluate(
                    """async (url) => {
                        const r = await fetch(url);
                        const b = await r.blob();
                        return await new Promise(res => {
                            const fr = new FileReader();
                            fr.onload = () => res(fr.result.split(',')[1]);
                            fr.readAsDataURL(b);
                        });
                    }""", src)
                return base64.b64decode(b64)
            r = requests.get(src, headers={"User-Agent": UA, "Referer": page.url}, timeout=60)
            r.raise_for_status()
            return r.content

        def collecter() -> None:
            """Détecte les images de page visibles/chargées et récupère leur contenu."""
            nouvelles = page.evaluate("""() => Array.from(document.images)
                .filter(i => i.naturalWidth > 250 && i.naturalHeight > 500)
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
                        continue
                    vus_hashes.add(hsh)
                    vues[im["src"]] = {"ordre": len(vues), "top": im["top"],
                                       "w": im["w"], "h": im["h"], "data": data}
                except Exception as e:
                    notes.append(f"{im['src'][:60]} : ECHEC {type(e).__name__}")

        # Mode de lecture : bande défilante (scroll) ou page par page (pager).
        # MangaDex web est un PAGER par défaut : scrollBy n'y avance rien
        # (mesuré : 4 pages capturées sur 22 en scrollant dans le vide).
        h_doc = page.evaluate("() => document.documentElement.scrollHeight")
        h_ecran = page.evaluate("() => window.innerHeight")
        mode_strip = h_doc > h_ecran * 2.5
        print(f"Mode {'bande défilante' if mode_strip else 'page par page'} "
              f"(doc {h_doc}px / écran {h_ecran}px)")

        if mode_strip:
            hauteur_prec, stable = 0, 0
            for _ in range(300):
                collecter()
                page.evaluate("window.scrollBy(0, window.innerHeight * 0.85)")
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
            sterile, debut_pager = 0, time.time()
            for _ in range(400):
                collecter()
                n_avant = len(vues)
                page.keyboard.press("ArrowRight")
                page.wait_for_timeout(1500)
                collecter()
                if len(vues) == n_avant:
                    sterile += 1
                    if sterile >= 5 and len(vues) > 0:
                        break  # plus rien de nouveau ET on a des pages : fin de chapitre
                    if sterile >= 20 and len(vues) == 0:
                        print("Abandon : le lecteur ne charge aucune page "
                              "(rate-limit ? chapitre vide ? onglet cassé ?)")
                        return 2
                else:
                    sterile = 0
                if time.time() - debut_pager > 720:  # garde-fou global : 12 min
                    notes.append("arrêt sur timeout global (12 min)")
                    break

        # ordre de lecture : position verticale en bande défilante, ordre de découverte en pager
        uniques = sorted(vues.values(), key=lambda x: x["top"] if mode_strip else x["ordre"])

        # Cohérence des largeurs : les vraies pages d'un chapitre sont homogènes ; les
        # artefacts du site (bannières, cartes de fin) sont plus ÉTROITS. On écarte ce qui
        # fait moins de 80 % de la largeur médiane — les doubles pages, plus larges, restent.
        # (mesuré : 22 pages à 1600px + 5 artefacts à 984px capturés ensemble)
        if len(uniques) >= 3:
            mediane = sorted(im["w"] for im in uniques)[len(uniques) // 2]
            ecartees = [im for im in uniques if im["w"] < 0.8 * mediane]
            for im in ecartees:
                notes.append(f"écartée (largeur {im['w']} < 80% de la médiane {mediane})")
            uniques = [im for im in uniques if im["w"] >= 0.8 * mediane]
        print(f"{len(uniques)} images de page capturées au fil du défilement.")
        if not uniques:
            print("Aucune image détectée — le chapitre est-il affiché ? (connexion requise sur certains sites)")
            return 2

        # Sauvegarde dans l'ordre de lecture (position verticale)
        dest = chap_dir(args.out, args.title, args.chapter)
        for i, im in enumerate(uniques, 1):
            if len(im["data"]) < 5000:
                notes.append(f"page {i} : image suspecte ({len(im['data'])} octets)")
            nom = save_page(dest, i, im["data"])
            pages_meta.append({"file": nom, "bytes": len(im["data"]), "w": im["w"], "h": im["h"]})
        notes = list(dict.fromkeys(notes))  # une même anomalie ne se répète pas dans le manifeste
        write_manifest(dest, slug=slugify(args.title), title=args.title, chapter=args.chapter,
                       source="capture", source_url=page.url, pages=pages_meta, notes=notes)
        log_event("capture", url=page.url, title=args.title, chapter=str(args.chapter),
                  pages=len(pages_meta), echecs=sum(1 for n in notes if "ECHEC" in n))
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
    s.add_argument("--tab", default="mangadex", help="fragment d'URL de l'onglet à capturer")
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
