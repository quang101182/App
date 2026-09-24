"""Banc v2.8.5 (24/09) : a l'ouverture d'une serie, tomes/dates et pochette se lancent SEULS -- et jamais pendant une capture.

Serie jetable zz-essai-auto (3 pages de Solo Leveling ch.1, slug reecrit : sinon elle se fondrait dans la vraie serie).
  1. chapitre SANS manifeste (capture en cours) -> ouverture : ni serie.json ni pochette crees, titre = titre.json
  2. manifeste pose (capture finie) + rechargement -> pochette.* et serie.json crees seuls, tome du ch.1 renseigne
  3. un 2e chapitre capture APRES la recherche -> rechargement -> tomes relances (maj avance, ch.2 present)
Usage : python test_auto_tomes_pochette_ui.py   (appels : AniList + MangaDex, gratuits)
"""
import json, os, shutil, sys, time
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = 8190
S = "zz-essai-auto"
SRC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sources"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import banc_outils as bo
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


def chapitre(ch, num, manifeste):
    d = os.path.join(SRC, S, ch); os.makedirs(d, exist_ok=True)
    # pages prises dans claymore/ch_1 (serie stable) ; le TITRE reste « Solo Leveling » : c'est lui que MangaDex/AniList cherchent
    m = json.load(open(os.path.join(SRC, "claymore", "ch_1", "manifest.json"), encoding="utf-8"))
    m.update(slug=S, title="Solo Leveling", chapter=str(num), pages=m["pages"][:3], captured_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
             source_url="", notes=[])
    for p in m["pages"]:
        shutil.copy2(os.path.join(SRC, "claymore", "ch_1", p["file"]), os.path.join(d, p["file"]))
    if manifeste:
        json.dump(m, open(os.path.join(d, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False)
    return m


def serie_json():
    f = os.path.join(SRC, S, "serie.json")
    return json.load(open(f, encoding="utf-8")) if os.path.isfile(f) else None


pochette = lambda: [f for f in os.listdir(os.path.join(SRC, S)) if f.startswith("pochette.")]

bo.supprimer_serie(S)
try:
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        pg = b.new_page(viewport={"width": 1280, "height": 900}); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))

        def ouvrir(attente=6000):
            pg.goto("http://127.0.0.1:%d/manga#k=%s" % (PORT, KEY)); pg.wait_for_timeout(2500)
            pg.click('nav button[data-tab="tChap"]'); pg.wait_for_timeout(1000)
            pg.evaluate("() => ouvrirSerie('%s')" % S); pg.wait_for_timeout(attente)

        print("1. capture en cours (pas de manifeste)")
        m1 = chapitre("ch_1", 1, manifeste=False)
        json.dump({"titre": "Solo Leveling"}, open(os.path.join(SRC, S, "titre.json"), "w", encoding="utf-8"))
        ouvrir()
        check("version affichee = celle du fichier", pg.inner_text("#verBadge") == "v" + bo.version_app())
        check("titre affiche = titre saisi (pas le nom de dossier)", pg.inner_text("#libSerie").startswith("Solo Leveling"), pg.inner_text("#libSerie"))
        check("aucune recherche de tomes pendant la capture", serie_json() is None)
        check("aucune pochette pendant la capture", not pochette())

        print("2. capture finie (manifeste pose)")
        json.dump(m1, open(os.path.join(SRC, S, "ch_1", "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False)
        ouvrir(9000)
        sj = serie_json()
        check("pochette posee seule", bool(pochette()), pochette())
        check("tomes et dates cherches seuls", bool(sj and sj.get("mangadex_id")), sj and sj.get("titre_mangadex"))
        check("tome du ch.1 renseigne", bool(sj and (sj.get("chapitres") or {}).get("1")), sj and sj.get("chapitres"))
        maj1 = sj and sj.get("maj")

        print("3. nouveau chapitre capture apres la recherche")
        time.sleep(61)                                    # maj est a la minute : le ch.2 doit etre visiblement posterieur
        chapitre("ch_2", 2, manifeste=True)
        ouvrir(9000)
        sj = serie_json()
        check("tomes relances (maj avance)", bool(sj and sj.get("maj") != maj1), (maj1, sj and sj.get("maj")))
        check("ch.2 connu de la fiche", bool(sj and "2" in (sj.get("chapitres") or {})), sj and sj.get("chapitres"))
        check("aucune erreur JS", not errs, errs[:2])
        b.close()
finally:
    bo.supprimer_serie(S)
print("\n%d/%d" % (len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
