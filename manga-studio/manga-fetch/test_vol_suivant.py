"""Banc v0.6.0 (23/09/2026) : enchainement volumes entiers + chapitres de manga-scantrad.io. Liste REELLE relevee sur la
page Solo Leveling vol-1 le 23/09 (38 entrees du menu, ordre du site = decroissant). Aucun reseau."""
import sys
import manga_fetch as mf
OK = KO = 0
def check(c, n):
    global OK, KO
    OK, KO = (OK + 1, KO) if c else (OK, KO + 1); print(("  OK  " if c else "  KO  ") + n)
SITE = ["vol-16-chapitre-%d" % n for n in range(200, 179, -1)] + ["vol-16-chapitre-179-5"] + ["vol-%d" % n for n in range(15, -1, -1)]
SITE += ["List style", "compact", "vol-1", ""]                                   # bruit du menu, doublon
check(len({s for s in SITE if mf._vol_cle(s)}) == 38, "38 entrees reconnues")
check(mf.vol_suivant(SITE, "vol-1")[:2] == ("2", "vol-2"), "vol-1 -> ch. 2 = vol-2")
check(mf.vol_suivant(SITE, "vol-0")[:2] == ("1", "vol-1"), "vol-0 -> vol-1")
check(mf.vol_suivant(SITE, "vol-15")[:2] == ("179.5", "vol-16-chapitre-179-5"), "vol-15 -> 179.5 (le 1er chapitre separe)")
check(mf.vol_suivant(SITE, "vol-15", entiers=True)[:2] == ("180", "vol-16-chapitre-180"), "sans intermediaires : vol-15 -> 180")
check(mf.vol_suivant(SITE, "vol-16-chapitre-199")[:2] == ("200", "vol-16-chapitre-200"), "199 -> 200")
check(mf.vol_suivant(SITE, "vol-16-chapitre-200")[0] is None, "200 = dernier -> stop, avec raison : %s" % mf.vol_suivant(SITE, "vol-16-chapitre-200")[2])
check(mf.vol_suivant(SITE, "vol-4", jusqua=4)[0] is None, "borne 4 depuis vol-4 -> stop")
check(mf.vol_suivant(SITE, "vol-3", jusqua=4)[:2] == ("4", "vol-4"), "borne 4 depuis vol-3 -> vol-4")
check(mf.vol_suivant(SITE, "vol-99")[0] is None, "slug inconnu -> refus explicite")
print("\n%d/%d" % (OK, OK + KO)); sys.exit(1 if KO else 0)
