# -*- coding: utf-8 -*-
"""Banc v2.4.1 : la MUSIQUE de la serie reglee depuis le profil (« ⚙ Profil et traitement »), Quang 22/09 15h48.

Serie jetable sources/banc-prof-mus/ (1 chapitre de 3 pages). 1280 et 360 px :
« Importer un fichier… » du profil = vrai import (un echantillon de voix de sources/_apercus, 7 s) -> le morceau
apparait dans la liste du profil ; le cocher = selection de la SERIE (musique/choix.json) ; « Prendre dans Generate
Studio » ouvre la playlist DANS le profil ; la fiche du chapitre retrouve sa propre playlist a sa place (pas de vol) ;
rien ne deborde. Tout est efface a la fin.
Usage : python test_profil_musique_ui.py [port] [dossier_captures]
"""
import json, os, shutil, sys
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
CAP = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sources"))
BANC = os.path.join(SRC, "banc-prof-mus")
ECH = os.path.join(SRC, "_apercus", "Charon.mp3")
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""), flush=True)


def prepare():
    shutil.rmtree(BANC, ignore_errors=True)
    cs, cd = os.path.join(SRC, "one-punch-man", "ch_298"), os.path.join(BANC, "ch_1")
    os.makedirs(cd)
    man = json.load(open(os.path.join(cs, "manifest.json"), encoding="utf-8"))
    man.update(pages=man["pages"][1:4], chapter="1", slug="banc-prof-mus", title="banc prof mus")
    for p in man["pages"]:
        shutil.copy(os.path.join(cs, p["file"]), os.path.join(cd, p["file"]))
    json.dump(man, open(os.path.join(cd, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def main():
    prepare()
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(channel="msedge", headless=True)
            for w, h in ((1280, 1300), (360, 1500)):
                print("=== %d px" % w)
                pg = b.new_page(viewport={"width": w, "height": h}); errs = []
                pg.on("pageerror", lambda e: errs.append(str(e)))
                pg.on("dialog", lambda dl: dl.accept())
                pg.goto("http://127.0.0.1:%d/manga/#k=" % PORT + KEY); pg.wait_for_timeout(2500)
                pg.click('nav button[data-tab="tChap"]'); pg.wait_for_timeout(1200)
                pg.evaluate("() => refreshChaps()"); pg.wait_for_timeout(1200)
                pg.evaluate("() => ouvrirSerie('banc-prof-mus')"); pg.wait_for_timeout(1200)
                pg.click("#btnSuivi"); pg.wait_for_timeout(2500)
                vide = pg.evaluate("() => document.getElementById('profMusEtat').textContent")
                if w == 1280:
                    check("série sans musique : invitation à en ajouter", "Aucun morceau" in vide, vide)
                    with pg.expect_file_chooser() as fc:
                        pg.evaluate("s => { const e = document.querySelector(s); if (!e) return; const d = e.closest('details'); if (d && !d.open) d.open = true; const m = e.closest('.menu-plus'); if (m && m.querySelector('.menu-pan').hidden) m.querySelector('.plus').click(); }", "#profMusImport"); pg.click("#profMusImport")
                    fc.value.set_files(ECH); pg.wait_for_timeout(4000)
                    items = pg.evaluate("() => Array.from(document.querySelectorAll('#profMusListe [data-pm-coche]')).map(c => [c.dataset.pmCoche, c.checked])")
                    check("import depuis le profil : le morceau apparaît", len(items) == 1, items)
                    if items and not items[0][1]:
                        pg.click('#profMusListe [data-pm-coche]'); pg.wait_for_timeout(2500)
                    choix = json.load(open(os.path.join(BANC, "musique", "choix.json"), encoding="utf-8")) if os.path.isfile(os.path.join(BANC, "musique", "choix.json")) else {}
                    check("coché = sélection de la série (choix.json)", len(choix.get("serie") or []) == 1, choix)
                    check("état : « 1 coché(s) »", "1 coché" in pg.evaluate("() => document.getElementById('profMusEtat').textContent"))
                pg.evaluate("s => { const e = document.querySelector(s); if (!e) return; const d = e.closest('details'); if (d && !d.open) d.open = true; const m = e.closest('.menu-plus'); if (m && m.querySelector('.menu-pan').hidden) m.querySelector('.plus').click(); }", "#profMusGs"); pg.click("#profMusGs"); pg.wait_for_timeout(3500)
                gs = pg.evaluate("() => [document.getElementById('gsBox').parentNode.id, !document.getElementById('gsBox').hidden, document.querySelectorAll('#gsListe .gs-it').length]")
                check("Generate Studio s'ouvre DANS le profil", gs[0] == "profGsPlace" and gs[1], gs)
                m = pg.evaluate("""() => ({page: document.documentElement.scrollWidth - document.documentElement.clientWidth,
                    dehors: Array.from(document.querySelectorAll('#suiviBox *')).filter(e => e.offsetParent && e.getBoundingClientRect().right > innerWidth + 1).length})""")
                check("rien ne déborde", m["page"] <= 0 and m["dehors"] == 0, m)
                pg.query_selector("#suiviBox").screenshot(path=os.path.join(CAP, "profmus_%d.png" % w))
                # la fiche du chapitre recupere SA playlist
                pg.evaluate("() => openChap(CHAPS.findIndex(c => c.dir === 'banc-prof-mus/ch_1'))"); pg.wait_for_timeout(2500)
                pg.evaluate("() => document.getElementById('musGs').click()"); pg.wait_for_timeout(3000)
                gs = pg.evaluate("() => [document.getElementById('gsBox').closest('.mus-box') !== null, !document.getElementById('gsBox').hidden, MUS_CIBLE]")
                check("fiche du chapitre : la playlist revient à sa place", gs == [True, True, None], gs)
                check("aucune erreur JS", not errs, errs)
                pg.close()
            b.close()
    finally:
        shutil.rmtree(BANC, ignore_errors=True)
    print("\nVERDICT : %d/%d" % (len(OK), len(OK) + len(KO)) + ("" if not KO else "  -- KO : " + " ; ".join(KO)))
    return 0 if not KO else 1


if __name__ == "__main__":
    sys.exit(main())
