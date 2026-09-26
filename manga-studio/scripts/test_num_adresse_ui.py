# -*- coding: utf-8 -*-
"""Banc v2.77.0 : numero de chapitre SUGGERE d'apres l'adresse de la page (chapDeLaPage, v2.64.0). Tableau d'adresses
(formats connus + volume entier « vol-N » ajoute en v2.77.0) : aucune regression sur les anciens formats. APP REELLE, lecture seule.
Usage : python test_num_adresse_ui.py [port] [--mutation]   (--mutation : app v2.76.0 servie -> doit sortir ROUGE)
"""
import os, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
MUT = "--mutation" in sys.argv; sys.argv = [a for a in sys.argv if a != "--mutation"]
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
ICI = os.path.dirname(os.path.abspath(__file__))
CAS = [   # (adresse, titre de l'onglet, numero attendu)
    ("https://manga-scantrad.io/manga/solo-leveling/vol-2/", "Solo Leveling vf", "2"),              # v2.77.0 (Quang 14h57)
    ("https://manga-scantrad.io/manga/solo-leveling/vol-15", "", "15"),
    ("https://manga-scantrad.io/manga/solo-leveling/vol-0/", "", "0"),
    ("https://manga-scantrad.io/manga/solo-leveling/vol-02/?style=list", "", "2"),
    ("https://manga-scantrad.io/manga/solo-leveling/vol-16-chapitre-179-5/", "", "179.5"),          # deja lu avant v2.77.0
    ("https://raijin-scans.fr/manga/x/chapter-37/", "", "37"),
    ("https://site.example/manga/x/chapter/4", "", "4"),
    ("https://www.webtoons.com/fr/x/y/ep/viewer?title_no=1&episode_no=12", "", "12"),
    ("https://site.example/x/chapter-12-5/", "", "12.5"),
    ("https://site.example/x/chapter-1-ch265736/", "", "1"),
    ("https://mangadex.org/chapter/3f9b2c1e-1111-2222-3333-444455556666", "Chapter 143 - Solo", "143"),  # uuid : pas un numero
    ("https://site.example/manga/volcano-hero/", "", ""),                                           # « vol » dans un nom : rien
]
OK, KO = [], []
def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail)[:200] if detail else ""), flush=True)

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    pg = b.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    if MUT:
        pg.route("**/manga", lambda route: route.fulfill(status=200, content_type="text/html; charset=utf-8",
                 body=open(os.path.join(ICI, "..", "manga_studio.html.bak-20260926-v2770"), encoding="utf-8").read()))   # = v2.76.0
    pg.goto("http://127.0.0.1:%d/manga#k=%s" % (PORT, KEY)); pg.wait_for_timeout(3500)
    for url, titre, attendu in CAS:
        n = pg.evaluate("([url, title]) => chapDeLaPage({ url, title })", [url, titre])
        check("%-62s → « %s »" % (url.split("//")[1][:62], attendu), n == attendu, "obtenu « %s »" % n)
    check("aucune erreur JS", not errs, errs[:3])
    b.close()
print("\nVERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
