# -*- coding: utf-8 -*-
"""Banc R19 (v2.88.0) : voix 100 % FRANCAISES en priorite. (1) dialogues.voix_francaises() sur la VRAIE bibliotheque ElevenLabs ;
(2) un nouveau personnage recoit d'office une voix francaise du bon genre ; (3) ecran ✏ sur une COPIE d'OPM ch.5 (instance
8191, proxy patche 10) : voix groupees « 🇫🇷 Voix françaises » d'abord, accent anglais signale, choix d'une voix francaise
enregistre (ses repliques passent « a refaire », annonce -- AUCUNE voix generee). 0 credit.
Usage : python test_voix_francaises_ui.py <html> <proxy>        (html v2.87.0 -> ROUGE). A lancer avec l'interpreteur de l'APP."""
import json, os, shutil, subprocess, sys, tempfile, time, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from playwright.sync_api import sync_playwright
import dialogues as dl, narrate_chapter as nc
HTML, PROXY = (os.path.abspath(x) for x in sys.argv[1:3])
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
SRC = r"C:\Users\quang\Documents\MangaStudio-donnees\sources"
PAGE = open(HTML, encoding="utf-8").read()
OK, KO = [], []


def check(n, c, d=""):
    (OK if c else KO).append(n); print(("  [OK] " if c else "  [KO] ") + n + (" -- " + str(d)[:180] if d else ""), flush=True)


nc.SECRET = nc._secret()
fr = dl.voix_francaises()
check("bibliothèque : ≥ 40 voix françaises, hommes ET femmes", len(fr) >= 40 and {"male", "female"} <= {v["genre"] for v in fr},
      (len(fr), sorted({v["genre"] for v in fr})))
distrib = {"persos": [], "narrateur": {}}
aj = dl.fusionner_distribution(distrib, [{"nom": "Héros", "genre": "homme"}, {"nom": "Héroïne", "genre": "femme"}], fr)
ids = {v["id"]: v for v in fr}
check("nouveaux personnages : voix FRANÇAISE du bon genre", len(aj) == 2 and all(p["voix_el"] in ids for p in distrib["persos"])
      and ids[distrib["persos"][0]["voix_el"]]["genre"] == "male" and ids[distrib["persos"][1]["voix_el"]]["genre"] == "female",
      [(p["nom"], (ids.get(p["voix_el"]) or {}).get("nom")) for p in distrib["persos"]])

T = tempfile.mkdtemp(prefix="voix_fr_")
SD = os.path.join(T, "one-punch-man"); os.makedirs(SD)
shutil.copytree(os.path.join(SRC, "one-punch-man", "ch_5"), os.path.join(SD, "ch_5"), ignore=shutil.ignore_patterns("narration", "video"))
for f in ("serie.json", "suivi.json", "dialogues_distribution.json"):
    shutil.copy(os.path.join(SRC, "one-punch-man", f), os.path.join(SD, f))
srv = subprocess.Popen([sys.executable, os.path.join(HERE, "proxy_8191.py"), PROXY], env=dict(os.environ, MANGA_SOURCES_DIR=T),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(60):
        try:
            urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8191/manga/el_solde", headers={"Authorization": "Bearer " + KEY}), timeout=5); break
        except Exception:
            time.sleep(1)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        pg = b.new_context(viewport={"width": 1280, "height": 900}).new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("dialog", lambda d: d.accept())
        pg.route("**/*", lambda rt: rt.fulfill(status=200, content_type="text/html; charset=utf-8", body=PAGE)
                 if rt.request.method == "GET" and rt.request.url.split("#")[0].split("?")[0].rstrip("/").endswith("/manga") else rt.continue_())
        pg.goto("http://127.0.0.1:8191/manga#k=" + KEY); pg.wait_for_timeout(2000)
        pg.evaluate("() => localStorage.setItem('manga_serie','one-punch-man')"); pg.reload()
        pg.wait_for_function("() => typeof RESUME !== 'undefined' && RESUME && RESUME.chapitres", timeout=30000); pg.wait_for_timeout(800)
        pg.evaluate("() => openChap(CHAPS.findIndex(c => c.dir === 'one-punch-man/ch_5'))")
        pg.wait_for_function("() => DLG.e && DLG.e.doc && DLG.plan", timeout=20000); pg.wait_for_timeout(800)
        af0 = pg.evaluate("() => DLG.plan.a_faire")
        pg.evaluate("() => dlgPrepOuvrir()"); pg.wait_for_timeout(3000)
        i = pg.evaluate("() => dlgPersos().findIndex(p => p.nom === 'Genos')")
        sel = '#dlgPrep .dlgp-carte[data-p="%d"] select[data-k="voix_el"]' % i
        grp = pg.evaluate("s => [...document.querySelector(s).querySelectorAll('optgroup')].map(g => [g.label, g.children.length])", sel)
        check("liste des voix : « 🇫🇷 Voix françaises » EN TÊTE, puis les autres", len(grp) == 2 and grp[0][0].startswith("🇫🇷") and grp[0][1] >= 40, grp)
        acc = pg.evaluate("i => (document.querySelector('#dlgPrep .dlgp-carte[data-p=\"' + i + '\"] .dlgp-accent') || {}).textContent || ''", i)
        check("Genos (voix anglophone) : « 🇬🇧 accent anglais » signalé", "accent anglais" in acc, acc)
        vfr = pg.evaluate("s => document.querySelector(s).querySelector('optgroup').querySelector('option').value", sel)
        pg.select_option(sel, vfr); pg.wait_for_timeout(2500)
        g = next(x for x in json.load(open(os.path.join(SD, "dialogues_distribution.json"), encoding="utf-8"))["persos"] if x["nom"] == "Genos")
        check("voix française choisie et ENREGISTRÉE pour Genos (tout le manga)", g["voix_el"] == vfr, g["voix_el"])
        af1 = pg.evaluate("() => DLG.plan.a_faire")
        check("ses répliques passent « à refaire » (annoncé, rien généré) : %s -> %s" % (af0, af1), af1 > af0)
        print("   debug :", pg.evaluate("i => [dlgPersos()[i].voix_el, DLG.voix.filter(v => v.id === dlgPersos()[i].voix_el).map(v => v.fr)]", i))
        acc2 = pg.evaluate("i => !!document.querySelector('#dlgPrep .dlgp-carte[data-p=\"' + i + '\"] .dlgp-accent')", i)
        check("plus d'avertissement « accent anglais » pour Genos", not acc2)
        check("0 erreur JS", not errs, errs)
finally:
    srv.kill(); time.sleep(1); shutil.rmtree(T, ignore_errors=True)
    try:
        os.remove(os.path.expanduser(r"~\Documents\ComfyUI\_studio_llm_proxy_8191.py"))
    except Exception:
        pass
print("VERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
