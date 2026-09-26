# -*- coding: utf-8 -*-
"""Banc v2.67.2 (Quang 26/09 03h38) : le nom propose d'apres l'onglet ne garde ni « Reading … » ni les entites HTML (&quot;).
APP REELLE (8190), appels directs a devinerTitre() + libelle de la liste des onglets. Quelques secondes, rien n'est ecrit.
Usage : python test_titre_onglet_ui.py [port]
"""
import os, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
CAS = [  # titre de l'onglet -> nom attendu (hors bibliotheque : la page de test n'a aucun de ces titres)
    ("Reading No to Obsession, Yes to Love - Chapter 01 by &quot;M — manhwaread", "No to Obsession, Yes to Love"),
    ("Read online Tower of Dawn Chapter 12 | site", "Tower of Dawn"),
    ("Lire Le Voyage Chapitre 3 - scans", "Le Voyage"),
    ("Lecture en ligne La Forêt Ch. 7", "La Forêt"),
    ("Reading the Room", "Reading the Room"),                              # pas une page de chapitre : intact
    ("Ready Player Two - Chapter 4", "Ready Player Two"),                   # « Ready » n'est pas « Read »
    ("Tom &amp; Jerry - Episode 2", "Tom & Jerry"),
]
OK, KO = [], []
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    pg = b.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("http://127.0.0.1:%d/manga#k=%s" % (PORT, KEY)); pg.wait_for_timeout(3500)
    for t, attendu in CAS:
        r = pg.evaluate("(t) => devinerTitre(t).titre", t)
        (OK if r == attendu else KO).append(t)
        print(("  [OK] " if r == attendu else "  [KO] ") + "%r -> %r" % (t[:50], r))
    lib = pg.evaluate("""async () => { const a0 = api;
        api = (p, b) => p === '/manga/fetch_tabs' ? Promise.resolve({ edge: true, tabs: [{ url: 'https://exemple.invalid/serie/chapter-1',
              title: 'A &quot;B&quot; - Chapter 1' }] }) : a0(p, b);
        try { await refreshCapTabs(); } finally { api = a0; }
        return $('capTab').options[0].textContent.split(' — ')[0]; }""")
    (OK if lib == 'A "B" - Chapter 1' else KO).append("libelle")
    print(("  [OK] " if lib == 'A "B" - Chapter 1' else "  [KO] ") + "libellé d'onglet décodé : %r" % lib)
    (OK if not errs else KO).append("js"); print(("  [OK] " if not errs else "  [KO] ") + "aucune erreur JS", errs[:2])
    b.close()
print("\nVERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
