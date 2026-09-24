"""Banc v2.9.2 (Quang 24/09) : une serie = un DOSSIER, meme sans chapitre.

Serie jetable zz-essai-vide : titre.json + une musique, AUCUN chapitre. Attendus (smartphone 380 px) :
  - bibliotheque : la carte « Essai Vide » est la, « 0 chapitre » + « aucun chapitre », sans image cassee
  - capture : le menu des series la propose (« 0 ch. »)
  - ouverture de la serie : pas d'erreur, la musique est listee dans le profil
  - « 🗑 Supprimer la série » la retire EN ENTIER (dossier a la corbeille)
Usage : python test_serie_vide_ui.py
"""
import json, os, shutil, sys
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT, S = 8190, "zz-essai-vide"
SRC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sources"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import banc_outils as bo
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


bo.supprimer_serie(S)
os.makedirs(os.path.join(SRC, S, "musique"))
json.dump({"titre": "Essai Vide"}, open(os.path.join(SRC, S, "titre.json"), "w", encoding="utf-8"))
mp3 = next(os.path.join(r, f) for r, _, fs in os.walk(SRC) if "musique" in r and "_corbeille" not in r for f in fs if f.endswith(".mp3"))
shutil.copy2(mp3, os.path.join(SRC, S, "musique", "Essai Vide 1.mp3"))
try:
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        pg = b.new_page(viewport={"width": 380, "height": 800}); errs, dialogues = [], []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("dialog", lambda d: (dialogues.append(d.message), d.accept()))
        pg.goto("http://127.0.0.1:%d/manga#k=%s" % (PORT, KEY)); pg.wait_for_timeout(2500)
        check("version affichee = celle du fichier", pg.inner_text("#verBadge") == "v" + bo.version_app())
        pg.click('nav button[data-tab="tChap"]'); pg.wait_for_timeout(1500)
        pg.fill("#libRech", "Essai Vide") if pg.locator("#libRech").count() else None
        pg.wait_for_timeout(800)
        carte = pg.locator('[data-serie="%s"]' % S)
        check("bibliotheque : la carte de la serie sans chapitre est la", carte.count() == 1)
        txt = carte.inner_text() if carte.count() else ""
        check("carte : « 0 chapitre » et « aucun chapitre »", "0 chapitre" in txt and "aucun chapitre" in txt, txt.replace("\n", " | "))
        check("carte : pas d'image cassee", pg.evaluate("(s) => !document.querySelector('[data-serie=\"' + s + '\"] img')", S))
        # menu de la capture
        sugg = pg.evaluate("() => { CAP_SUGG_Q = 'essai vide'; capSuggRendre(); return $('capSugg').textContent"
                           " + ' // ' + JSON.stringify(capSuggListes().vis.map(x => x.title)); }")
        check("capture : le menu propose la serie (0 ch.)", "Essai Vide" in sugg and "0 ch." in sugg, sugg.replace("\n", " | ")[:120])
        # ouverture + profil
        pg.evaluate("() => ouvrirSerie('%s')" % S); pg.wait_for_timeout(2000)
        check("serie ouverte : titre", pg.inner_text("#libSerie").startswith("Essai Vide"), pg.inner_text("#libSerie"))
        pg.click("#btnSuivi"); pg.wait_for_timeout(2500)
        check("profil : la musique est listee", "Essai Vide 1" in pg.inner_text("#profMusListe"), pg.inner_text("#profMusListe")[:80])
        # suppression de la serie ENTIERE
        pg.click("#btnSerieDel"); pg.wait_for_timeout(2500)
        check("confirmation : « TOUTE la série »", any("TOUTE la série" in d for d in dialogues), dialogues[-1:])
        check("dossier retire (corbeille)", not os.path.isdir(os.path.join(SRC, S)))
        pg.wait_for_timeout(800)
        check("la carte a disparu de la bibliotheque", pg.locator('[data-serie="%s"]' % S).count() == 0)
        check("aucune erreur JS", not errs, errs[:2])
        b.close()
finally:
    bo.supprimer_serie(S)
print("\n%d/%d" % (len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
