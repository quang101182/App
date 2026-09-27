# -*- coding: utf-8 -*-
"""Banc R18 phase 1 (v2.89.0) : ⭐ vitesses par defaut des voix, par genre et PAR APPLICATION. ISOLE : instance 8191 sur une
COPIE d'OPM ch.5 -- son _reglages.json est celui de la copie (les reglages reels des 2 applications ne sont JAMAIS touches,
verifie). Ecran ✏ : diction d'un HOMME a 1,2 + ☆ -> defaut hommes enregistre, ★ affiche, application aux autres hommes
(confirmation acceptee) ; ecoute 1,3 + ☆ -> gratuit ; puis un NOUVEAU personnage homme recoit 1,2 / 1,3 (dialogues.py).
0 credit (rien n'est genere). Usage : python test_defauts_voix_ui.py <html> <proxy>        (html v2.88.0 -> ROUGE)"""
import hashlib, json, os, shutil, subprocess, sys, tempfile, time, urllib.request
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
HTML, PROXY = (os.path.abspath(x) for x in sys.argv[1:3])
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
DONNEES = os.path.expanduser(r"~\Documents\MangaStudio-donnees")
SRC = os.path.join(DONNEES, "sources")
PAGE = open(HTML, encoding="utf-8").read()
OK, KO = [], []


def check(n, c, d=""):
    (OK if c else KO).append(n); print(("  [OK] " if c else "  [KO] ") + n + (" -- " + str(d)[:180] if d else ""), flush=True)


def empreinte(f):
    return hashlib.sha1(open(f, "rb").read()).hexdigest() if os.path.isfile(f) else None


REELS = [os.path.join(SRC, "_reglages.json"), os.path.join(DONNEES, "prive", "_reglages.json")]
avant = [empreinte(f) for f in REELS]
T = tempfile.mkdtemp(prefix="defauts_")
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
    dist0 = json.load(open(os.path.join(SD, "dialogues_distribution.json"), encoding="utf-8"))
    hommes = [p["nom"] for p in dist0["persos"] if (p.get("genre") or "").lower() == "homme"]
    check("la copie a plusieurs personnages hommes (%s)" % ", ".join(hommes), len(hommes) >= 2)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        pg = b.new_context(viewport={"width": 1280, "height": 900}).new_page(); errs = []; boites = []
        pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("dialog", lambda d: (boites.append(d.message), d.accept()))
        pg.route("**/*", lambda rt: rt.fulfill(status=200, content_type="text/html; charset=utf-8", body=PAGE)
                 if rt.request.method == "GET" and rt.request.url.split("#")[0].split("?")[0].rstrip("/").endswith("/manga") else rt.continue_())
        pg.goto("http://127.0.0.1:8191/manga#k=" + KEY); pg.wait_for_timeout(2000)
        pg.evaluate("() => localStorage.setItem('manga_serie','one-punch-man')"); pg.reload()
        pg.wait_for_function("() => typeof RESUME !== 'undefined' && RESUME && RESUME.chapitres", timeout=30000); pg.wait_for_timeout(800)
        pg.evaluate("() => openChap(CHAPS.findIndex(c => c.dir === 'one-punch-man/ch_5'))")
        pg.wait_for_function("() => DLG.e && DLG.e.doc && DLG.plan", timeout=20000); pg.wait_for_timeout(800)
        af0 = pg.evaluate("() => DLG.plan.a_faire")
        pg.evaluate("() => dlgPrepOuvrir()"); pg.wait_for_timeout(3000)
        i = pg.evaluate("n => dlgPersos().findIndex(p => p.nom === n)", hommes[0])
        carte = '#dlgPrep .dlgp-carte[data-p="%d"]' % i
        check("écran ✏ : ☆ à côté de la diction et de l'écoute", pg.locator(carte + " [data-defaut]").count() == 2)
        c = pg.locator(carte + ' input[data-k="vitesse"]'); c.fill("1.2"); c.dispatch_event("input"); c.dispatch_event("change"); pg.wait_for_timeout(1500)
        pg.click(carte + ' [data-defaut="vitesse"]'); pg.wait_for_timeout(3500)
        reg = json.load(open(os.path.join(T, "_reglages.json"), encoding="utf-8"))
        check("diction 1,2 = défaut des HOMMES de cette application (_reglages.json de l'instance)", reg.get("defauts", {}).get("voix_h_vitesse") == 1.2, reg.get("defauts"))
        check("confirmation « appliquer aux autres hommes » avec l'avertissement crédits", boites and "autres hommes" in boites[-1] and "crédits" in boites[-1], boites[-1:])
        d1 = json.load(open(os.path.join(SD, "dialogues_distribution.json"), encoding="utf-8"))
        check("tous les hommes du manga passent à 1,2", all(p.get("vitesse") == 1.2 for p in d1["persos"] if p["nom"] in hommes),
              [(p["nom"], p.get("vitesse")) for p in d1["persos"] if p["nom"] in hommes])
        af1 = pg.evaluate("() => DLG.plan.a_faire")
        check("leurs voix sont annoncées « à refaire » : %s -> %s" % (af0, af1), af1 > af0)
        i = pg.evaluate("n => dlgPersos().findIndex(p => p.nom === n)", hommes[0]); carte = '#dlgPrep .dlgp-carte[data-p="%d"]' % i
        check("★ plein : la valeur affichée EST le défaut", pg.locator(carte + ' [data-defaut="vitesse"]').inner_text() == "★")
        c = pg.locator(carte + ' input[data-k="ecoute"]'); c.fill("1.3"); c.dispatch_event("input"); c.dispatch_event("change"); pg.wait_for_timeout(1500)
        pg.click(carte + ' [data-defaut="ecoute"]'); pg.wait_for_timeout(3500)
        reg = json.load(open(os.path.join(T, "_reglages.json"), encoding="utf-8"))
        check("écoute 1,3 = défaut des hommes, fusionné (la diction reste)", reg["defauts"].get("voix_h_ecoute") == 1.3 and reg["defauts"].get("voix_h_vitesse") == 1.2, reg["defauts"])
        check("confirmation de l'écoute : « Gratuit »", "Gratuit" in boites[-1], boites[-1:])
        check("écoute : aucune voix de plus à refaire", pg.evaluate("() => DLG.plan.a_faire") == af1)
        check("0 erreur JS", not errs, errs)
    # un NOUVEAU personnage homme recoit les defauts de CETTE application
    r = subprocess.run([os.environ.get("MANGA_PY", r"D:\Download\02-Apps-Web\kohya-trainer\.venv\Scripts\python.exe"), "-c",
                        "import sys; sys.path.insert(0, r'%s'); import dialogues as dl; d = {'persos': [], 'narrateur': {}}; "
                        "dl.fusionner_distribution(d, [{'nom': 'Nouveau', 'genre': 'homme'}, {'nom': 'Nouvelle', 'genre': 'femme'}], [{'id': 'a', 'genre': 'male'}, {'id': 'b', 'genre': 'female'}]); "
                        "print([(p['nom'], p['vitesse'], p.get('ecoute', 1)) for p in d['persos']])" % HERE],
                       capture_output=True, text=True, env=dict(os.environ, MANGA_SOURCES_DIR=T))
    check("nouveau personnage homme : 1,2 / 1,3 ; femme : inchangée (1,1 / 1)", "('Nouveau', 1.2, 1.3)" in r.stdout and "('Nouvelle', 1.1, 1)" in r.stdout, (r.stdout + r.stderr)[-200:])
    check("réglages RÉELS des 2 applications intacts", [empreinte(f) for f in REELS] == avant)
finally:
    srv.kill(); time.sleep(1); shutil.rmtree(T, ignore_errors=True)
    try:
        os.remove(os.path.expanduser(r"~\Documents\ComfyUI\_studio_llm_proxy_8191.py"))
    except Exception:
        pass
print("VERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
