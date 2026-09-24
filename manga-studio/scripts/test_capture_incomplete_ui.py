"""Banc v2.9.2 (24/09) : une capture ARRETEE avant la fin (note « ECHEC » de manga-fetch >= 0.6.2) se voit dans l'app.

Serie jetable zz-essai-capko : ch.1 complet, ch.2 avec la note ECHEC. Attendus : « ⛔ capture incomplète » sur la carte du
ch.2 SEULEMENT ; dans la fiche du ch.2, le resume dit « Capture INCOMPLÈTE » et les notes sont DEPLIEES ; ch.1 inchange.
Usage : python test_capture_incomplete_ui.py
"""
import json, os, shutil, sys
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT, S = 8190, "zz-essai-capko"
SRC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sources"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import banc_outils as bo
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


bo.supprimer_serie(S)
m0 = json.load(open(os.path.join(SRC, "claymore", "ch_1", "manifest.json"), encoding="utf-8"))
for ch, notes in (("ch_1", []), ("ch_2", ["ECHEC : capture ARRÊTÉE avant la fin (400 pas, position 356000 sur 903320 px) -- relancer avec --force"])):
    d = os.path.join(SRC, S, ch); os.makedirs(d)
    m = dict(m0, slug=S, title="Essai Capture", chapter=ch[3:], pages=m0["pages"][:3], notes=notes)
    for p in m["pages"]:
        shutil.copy2(os.path.join(SRC, "claymore", "ch_1", p["file"]), os.path.join(d, p["file"]))
    json.dump(m, open(os.path.join(d, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False)
open(os.path.join(SRC, S, "pochette.jpg"), "wb").write(open(os.path.join(SRC, S, "ch_1", m0["pages"][0]["file"]), "rb").read())
json.dump({"mangadex_id": "x", "maj": "2099-01-01 00:00", "chapitres": {}}, open(os.path.join(SRC, S, "serie.json"), "w"))  # pas d'appel reseau
try:
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        pg = b.new_page(viewport={"width": 380, "height": 800}); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto("http://127.0.0.1:%d/manga#k=%s" % (PORT, KEY)); pg.wait_for_timeout(2500)
        check("version affichee = celle du fichier", pg.inner_text("#verBadge") == "v" + bo.version_app())
        pg.click('nav button[data-tab="tChap"]'); pg.wait_for_timeout(1000)
        pg.evaluate("() => ouvrirSerie('%s')" % S); pg.wait_for_timeout(2000)
        cartes = pg.evaluate("() => [...document.querySelectorAll('#chapList [data-chap]')].map(b => [CHAPS[+b.dataset.chap].chapter, b.innerText])")
        ko = {c: "capture incomplète" in t for c, t in cartes}
        check("carte ch.2 : « ⛔ capture incomplète »", ko.get("2") is True, cartes)
        check("carte ch.1 : rien", ko.get("1") is False)
        for ch, attendu in (("2", True), ("1", False)):
            pg.evaluate("async () => { await openChap(CHAPS.findIndex(c => c.dir === '%s/ch_%s')); }" % (S, ch)); pg.wait_for_timeout(1500)
            somme, ouvert, cache = pg.inner_text("#chapNotesSum"), pg.evaluate("() => $('chapNotesBox').open"), pg.evaluate("() => $('chapNotesBox').hidden")
            if attendu:
                check("fiche ch.2 : « Capture INCOMPLÈTE », notes depliees", "INCOMPLÈTE" in somme and ouvert and not cache, (somme, ouvert))
            else:
                check("fiche ch.1 : pas de bloc d'avertissement (et pas d'etat « deplie » herite)", cache and not ouvert, (somme, ouvert, cache))
        check("aucune erreur JS", not errs, errs[:2])
        b.close()
finally:
    bo.supprimer_serie(S)
print("\n%d/%d" % (len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
