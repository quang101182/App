# -*- coding: utf-8 -*-
"""La version affichee A L'ECRAN est-elle la bonne ? (incident du 27/07)

Quang : « je crois que tu oublies de versionner a chaque fois le bandeau du haut
de l'application ».

Il avait raison, et la cause etait invisible dans le fichier : la version existe
a TROIS endroits, et le troisieme ECRASE les deux autres au chargement.

    <title>Manga Studio v1.10.0</title>          <- bumpe
    <span id="verBadge">v1.10.0</span>           <- bumpe
    const VERSION = "1.7.0";                     <- OUBLIE
    ...
    $("verBadge").textContent = "v" + VERSION;   <- ecrase les deux precedents

Resultat : le depot disait v1.10.0, l'ecran disait v1.7.0, pendant trois
versions. Relire le fichier ne suffisait pas -- il fallait regarder la PAGE.

Ce script verifie les trois declarations dans le source, puis, si le proxy
tourne, la valeur REELLEMENT AFFICHEE dans le navigateur. C'est cette derniere
qui compte : c'est la seule que Quang voit.

Usage:
    python check_version.py              (source + ecran si le proxy repond)
    python check_version.py --source     (source seulement, sans navigateur)
"""
import argparse
import io
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(os.path.dirname(HERE), "manga_studio.html")
SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
APP_URL = "http://127.0.0.1:8190/manga"


def lire_source():
    s = io.open(APP, encoding="utf-8").read()
    trouve = {
        "title": re.search(r"<title>Manga Studio v([0-9.]+)</title>", s),
        "badge": re.search(r'id="verBadge">v([0-9.]+)<', s),
        "const": re.search(r'const VERSION = "([0-9.]+)"', s),
    }
    return {k: (m.group(1) if m else None) for k, m in trouve.items()}


def lire_ecran():
    """Ce que le navigateur affiche VRAIMENT — la seule valeur qui compte."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None, "playwright absent"
    if not os.path.isfile(SECRET_FILE):
        return None, "secret introuvable"
    secret = open(SECRET_FILE, encoding="utf-8").read().strip()
    try:
        with sync_playwright() as pw:
            br = pw.chromium.launch(headless=True, channel="msedge")
            pg = br.new_page()
            pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
            pg.wait_for_timeout(2000)
            v = pg.evaluate(
                "() => document.getElementById('verBadge').textContent.trim()")
            br.close()
        return v.lstrip("v"), None
    except Exception as e:
        return None, str(e)[:120]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", action="store_true",
                    help="ne pas ouvrir de navigateur")
    args = ap.parse_args()

    src = lire_source()
    print("=== VERSION DANS LE SOURCE ===")
    for cle in ("title", "badge", "const"):
        print("  %-6s : %s" % (cle, src[cle] or "INTROUVABLE"))
    if None in src.values():
        print("\nECHEC : une declaration de version est introuvable.")
        return 2
    if len(set(src.values())) != 1:
        print("\nECHEC : les trois declarations DIVERGENT.")
        print("        `const VERSION` ecrase le titre et le badge au chargement :")
        print("        c'est elle que l'utilisateur verra, quoi que dise le HTML.")
        return 1
    print("  -> les trois concordent : %s" % src["const"])

    if args.source:
        return 0
    print("\n=== VERSION AFFICHEE A L'ECRAN ===")
    vue, err = lire_ecran()
    if vue is None:
        print("  non verifiable (%s)" % err)
        print("  ATTENTION : le source concorde, mais rien ne prouve l'ecran.")
        return 0
    print("  badge affiche : %s" % vue)
    if vue != src["const"]:
        print("\nECHEC : l'ecran affiche %s alors que le source dit %s."
              % (vue, src["const"]))
        print("        (page servie en cache ? proxy a redemarrer ?)")
        return 1
    print("\nOK — source et ecran disent la meme chose : v%s" % vue)
    return 0


if __name__ == "__main__":
    sys.exit(main())
