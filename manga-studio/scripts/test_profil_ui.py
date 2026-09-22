# -*- coding: utf-8 -*-
"""Banc v2.4.0 (etape 27, phase 3) : le panneau « ⚙ Profil de la série » + « Tout traiter », dans l'app, comme Quang.

Cree sources/banc-profil-ui/ (2 chapitres de 3 pages copies d'OPM 298-299, VO vi) ; le defaut general est SAUVE puis
RESTAURE. 360 px : panneau lisible sans debordement, capture ecran. 1280 px : profil par defaut annonce, puces
d'etat (2 chapitres a faire), choisir « traduction en français » enregistre le profil et grise 🌐 « a faire », toucher une
puce = « ma selection », « Lancer » refuse = rien d'envoye, ⭐ = defaut general, puis un VRAI lot depuis le bouton
(1 chapitre, Gemini, fr, karaoke, video) : l'item « ⚙ Traitement » apparait, le bilan dit ✅, toutes les icones de la puce
passent en couleur. Captures : scratch/profil_1280.png, profil_360.png. ~0,06 $.
Usage : python test_profil_ui.py [port] [dossier_captures]
"""
import json, os, shutil, sys, time
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
CAP = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sources"))
DEF = os.path.join(SRC, "_profil_defaut.json")
BANC = os.path.join(SRC, "banc-profil-ui")
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""), flush=True)


def prepare():
    shutil.rmtree(BANC, ignore_errors=True)
    for i, src in ((1, "one-punch-man/ch_298"), (2, "one-punch-man/ch_299")):
        cs, cd = os.path.join(SRC, src), os.path.join(BANC, "ch_%d" % i)
        os.makedirs(cd)
        man = json.load(open(os.path.join(cs, "manifest.json"), encoding="utf-8"))
        man.update(pages=man["pages"][1:4], chapter=str(i), slug="banc-profil-ui", title="banc profil ui")
        for p in man["pages"]:
            shutil.copy(os.path.join(cs, p["file"]), os.path.join(cd, p["file"]))
        json.dump(man, open(os.path.join(cd, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def nettoie_file():
    fd = os.path.join(SRC, "_videos_file")
    for f in (os.listdir(fd) if os.path.isdir(fd) else []):
        if f.endswith(".json") and not f.startswith("_"):
            try:
                if json.load(open(os.path.join(fd, f), encoding="utf-8")).get("d", "").startswith("banc-profil-ui/"):
                    for x in (f, f[:-5] + ".log"):
                        try: os.remove(os.path.join(fd, x))
                        except OSError: pass
            except Exception:
                pass


def ouvre(pg):
    pg.goto("http://127.0.0.1:%d/manga/#k=" % PORT + KEY); pg.wait_for_timeout(2500)
    pg.click('nav button[data-tab="tChap"]'); pg.wait_for_timeout(1200)
    pg.evaluate("() => { refreshChaps && refreshChaps(); }"); pg.wait_for_timeout(1500)
    pg.evaluate("() => ouvrirSerie('banc-profil-ui')"); pg.wait_for_timeout(1500)
    pg.click("#btnSuivi"); pg.wait_for_timeout(2500)


def main():
    sauve = open(DEF, "rb").read() if os.path.isfile(DEF) else None
    prepare()
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(channel="msedge", headless=True)
            # --- 360 px
            pg = b.new_page(viewport={"width": 360, "height": 1400}); errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            ouvre(pg)
            m = pg.evaluate("""() => ({page: document.documentElement.scrollWidth - document.documentElement.clientWidth,
                dehors: Array.from(document.querySelectorAll('#suiviBox *')).filter(e => e.offsetParent && e.getBoundingClientRect().right > innerWidth + 1).length})""")
            check("360 px : rien ne déborde", m["page"] <= 0 and m["dehors"] == 0, m)
            pg.query_selector("#suiviBox").screenshot(path=os.path.join(CAP, "profil_360.png"))
            check("360 px : aucune erreur JS", not errs, errs)
            pg.close()
            # --- 1280 px
            pg = b.new_page(viewport={"width": 1280, "height": 1300}); errs, dialogues, envois = [], [], []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.on("request", lambda rq: envois.append(rq.post_data) if "/manga/suivi_lancer" in rq.url else None)
            reponse = {"v": False}
            pg.on("dialog", lambda dl: (dialogues.append(dl.message), dl.accept() if reponse["v"] else dl.dismiss()))
            ouvre(pg)
            check("panneau ouvert, profil par défaut annoncé", "réglages par défaut" in pg.evaluate("() => document.getElementById('profEtat').textContent"))
            puces = pg.evaluate("() => Array.from(document.querySelectorAll('#lotPuces .lot-puce')).map(b => [b.dataset.d, b.classList.contains('sel')])")
            check("2 puces, sélectionnées (« pas terminés »)", puces == [["banc-profil-ui/ch_1", True], ["banc-profil-ui/ch_2", True]], puces)
            check("estimation : 2 chapitres", "2</b> chapitre" in pg.evaluate("() => document.getElementById('lotEstim').innerHTML"))
            pg.select_option("#suiviMoteur", "gemini"); pg.wait_for_timeout(2500)
            pg.select_option("#profTrad", "fr"); pg.wait_for_timeout(2500)
            cfg = json.load(open(os.path.join(BANC, "suivi.json"), encoding="utf-8")) if os.path.isfile(os.path.join(BANC, "suivi.json")) else {}
            check("« traduction en français » enregistrée dans le profil", cfg.get("traduction") == "fr" and cfg.get("moteur") == "gemini", cfg)
            check("… profil personnalisé (plus « par défaut »)", pg.evaluate("() => document.getElementById('profEtat').textContent") == "")
            ic = pg.evaluate("() => document.querySelector('#lotPuces .lot-puce i[title^=\"traduction\"]').className")
            check("puce : 🌐 à faire (gris)", ic == "faire", ic)
            pg.click('#lotPuces .lot-puce[data-d="banc-profil-ui/ch_2"]'); pg.wait_for_timeout(400)
            st = pg.evaluate("() => [LOT_PORTEE, Array.from(document.querySelectorAll('#lotPuces .lot-puce.sel')).map(b => b.dataset.d)]")
            check("toucher une puce → « ma sélection », ch.1 seul", st == ["sel", ["banc-profil-ui/ch_1"]], st)
            pg.click("#suiviLancer"); pg.wait_for_timeout(800)
            check("« Lancer » refusé : rien d'envoyé", not envois and dialogues and "ch. 1" in dialogues[-1], (envois, dialogues[-1:]))
            reponse["v"] = True
            pg.click("#profDefSet"); pg.wait_for_timeout(2500)
            d = json.load(open(DEF, encoding="utf-8")) if os.path.isfile(DEF) else {}
            check("⭐ réglages par défaut = ce profil (sans « actif »)", d.get("traduction") == "fr" and d.get("moteur") == "gemini" and d.get("actif") is False, d)
            pg.query_selector("#suiviBox").screenshot(path=os.path.join(CAP, "profil_1280.png"))
            # VRAI lot depuis le bouton (ch.1)
            pg.click("#suiviLancer"); pg.wait_for_timeout(3000)
            corps = json.loads(envois[-1]) if envois else {}
            check("lot envoyé : ch.1, lot, sans refaire", corps.get("chapitres") == ["banc-profil-ui/ch_1"] and corps.get("lot") is True
                  and corps.get("refaire") is False, corps)
            vu_act, t0, fin = set(), time.time(), ""
            while time.time() - t0 < 900:
                a = pg.evaluate("() => (ACT.items || []).filter(x => x.type === 'lot').map(x => x.etape)")
                vu_act.update(x for x in a if x)
                fin = pg.evaluate("() => document.getElementById('suiviPassage').textContent")
                if fin.startswith("Dernier passage"):
                    break
                pg.wait_for_timeout(3000)
            check("activité : « ⚙ Traitement » a suivi les étapes", {"narration", "traduction"} <= vu_act, sorted(vu_act))
            check("bilan : ✅ 1 chapitre", "✅ 1 chapitre" in fin and "❌" not in fin, fin)
            icones = pg.evaluate("""() => Array.from(document.querySelectorAll('#lotPuces .lot-puce[data-d="banc-profil-ui/ch_1"] i'))
                .map(i => i.className)""")
            check("puce ch.1 : narration, karaoké, traduction, vidéo = faits", icones[:3] == ["fait", "fait", "fait"] and icones[4] in ("fait",), icones)
            pg.query_selector("#suiviBox").screenshot(path=os.path.join(CAP, "profil_1280_apres.png"))
            check("1280 px : aucune erreur JS", not errs, errs)
            b.close()
    finally:
        nettoie_file()
        shutil.rmtree(BANC, ignore_errors=True)
        if sauve is None:
            try: os.remove(DEF)
            except OSError: pass
        else:
            open(DEF, "wb").write(sauve)
    check("défaut général restauré", (open(DEF, "rb").read() if os.path.isfile(DEF) else None) == sauve)
    print("\nVERDICT : %d/%d" % (len(OK), len(OK) + len(KO)) + ("" if not KO else "  -- KO : " + " ; ".join(KO)))
    return 0 if not KO else 1


if __name__ == "__main__":
    sys.exit(main())
