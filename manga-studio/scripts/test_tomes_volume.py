# -*- coding: utf-8 -*-
"""Banc v2.37.0 : tomes automatiques -- un chapitre capture depuis une page de VOLUME (l'adresse le dit) est range dans
« Tome N » des sa capture ; les autres gardent la table MangaDex. APP REELLE (8190), lecture seule.

1. tomeDuLien() sur 12 adresses reelles et pieges (tomodachi, volume-control, devolve, raijin sans signal…) ;
2. Claymore : ch. 4 / 5 / 6 (AnimoFlix « volume-N ») -> Tome 4 / 5 / 6, plus aucun « Hors tome » ; ch. 1-3 inchanges ;
3. One Punch-Man (MangaDex, aucune adresse de volume) : tomes intacts.
Usage : python test_tomes_volume.py [port]
"""
import os, sys
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = sys.argv[1] if len(sys.argv) > 1 else "8190"
OK, KO = [], []
CAS = [["https://animoflix.to/anime/claymore/scan/vf/volume-4/", "4"], ["https://animoflix.to/anime/claymore/scan/vf/volume-12", "12"],
       ["https://site.fr/manga/berserk/tome-07/", "7"], ["https://x.com/read/one-piece/vol_3/page-1", "3"], ["https://x.com/Tomo 5/", "5"],
       ["https://raijin-scans.fr/manga/claymore/1/", ""], ["https://mangadex.org/chapter/1b2c3d4e-volumes", ""],
       ["https://x.com/manga/volume-control/ch-4/", ""], ["https://x.com/tomodachi-game/chapter-12/", ""],
       ["https://x.com/manga/devolve-3/", ""], ["pas une url", ""], [None, ""]]


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    pg = b.new_page(viewport={"width": 1280, "height": 900}); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("http://127.0.0.1:%s/manga#k=%s" % (PORT, KEY)); pg.wait_for_timeout(2500)
    av = pg.evaluate("() => [localStorage.getItem('manga_onglet'), localStorage.getItem('manga_serie')]")
    pg.evaluate("() => { localStorage.setItem('manga_onglet','tChap'); localStorage.setItem('manga_serie','claymore'); }")
    pg.reload(); pg.wait_for_timeout(4000)
    faux = [[u, a, r] for u, a, r in pg.evaluate("cas => cas.map(([u, a]) => [u, a, tomeDuLien(u)])", CAS) if r != a]
    check("tomeDuLien : 12 adresses (dont 6 pièges)", not faux, faux)
    cl = pg.evaluate("() => CHAPS.filter(c => c.dir.startsWith('claymore/')).map(c => [c.chapter, String(c.tome || ''), !!c.volume])")
    vol = {c[0]: c[1] for c in cl if c[2]}
    check("Claymore ch. 4 / 5 / 6 (volumes AnimoFlix) -> tomes 4 / 5 / 6", vol == {"4": "4", "5": "5", "6": "6"}, cl)
    # v2.38.0 (Quang 23h35) : les tomes ne sont plus AFFICHES -- les chapitres dans l'ordre, sans intertitre
    groupes = pg.eval_on_selector_all("#chapList .tome-tete", "e => e.length")
    ordre = pg.eval_on_selector_all("#chapList [data-chap] b", "e => e.map(x => (x.innerText.split('ch. ').pop().match(/[\d.]+/) || ['0'])[0])")
    check("aucun intertitre de tome, chapitres dans l'ordre", groupes == 0 and ordre == sorted(ordre, key=float), (groupes, ordre))
    cols = pg.eval_on_selector_all("#chapList [data-chap]", "e => [...new Set(e.map(x => Math.round(x.getBoundingClientRect().left)))].length")
    check("PC : chapitres sur 2 colonnes", cols == 2, cols)
    check("Claymore ch. 1-3 (sans adresse de volume) : table MangaDex inchangée", all(c[1] == "1" and not c[2] for c in cl if c[0] in ("1", "2", "3")), cl[:3])
    opm = pg.evaluate("() => CHAPS.filter(c => c.dir.startsWith('one-punch-man/')).map(c => !!c.volume)")
    check("One Punch-Man : aucune adresse de volume, rien de changé", opm and not any(opm), len(opm))
    check("aucune erreur JS", not errs, errs[:2])
    pg.evaluate("a => { ['manga_onglet','manga_serie'].forEach((n, i) => a[i] == null ? localStorage.removeItem(n) : localStorage.setItem(n, a[i])); }", av)
    b.close()
print("\nVERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
