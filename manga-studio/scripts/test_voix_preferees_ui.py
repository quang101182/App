# -*- coding: utf-8 -*-
"""Banc R24 (v2.94.0) : separations VISIBLES dans la liste des voix, voix PREFEREES (par application), ecoute du narrateur.
ISOLE : instance 8191 sur une COPIE d'OPM ch.5 (son _reglages.json) ; reglages reels des 2 applications verifies intacts ;
l'ecoute d'essai est INTERCEPTEE (0 credit). Usage : python test_voix_preferees_ui.py <html> <proxy>   (html v2.93.0 -> ROUGE)"""
import hashlib, json, os, shutil, subprocess, sys, tempfile, time, urllib.request
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
HTML, PROXY = (os.path.abspath(x) for x in sys.argv[1:3])
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
DONNEES = os.path.expanduser(r"~\Documents\MangaStudio-donnees"); SRC = os.path.join(DONNEES, "sources")
PAGE = open(HTML, encoding="utf-8").read()
OK, KO = [], []


def check(n, c, d=""):
    (OK if c else KO).append(n); print(("  [OK] " if c else "  [KO] ") + n + (" -- " + str(d)[:180] if d else ""), flush=True)


emp = lambda f: hashlib.sha1(open(f, "rb").read()).hexdigest() if os.path.isfile(f) else None
REELS = [os.path.join(SRC, "_reglages.json"), os.path.join(DONNEES, "prive", "_reglages.json")]
avant = [emp(f) for f in REELS]
T = tempfile.mkdtemp(prefix="voixfav_")
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
    ecoutes = []
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        pg = b.new_context(viewport={"width": 390, "height": 850}, is_mobile=True, has_touch=True).new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("dialog", lambda d: d.accept())

        def route(rt):
            u = rt.request.url.split("#")[0].split("?")[0]
            if rt.request.method == "GET" and u.rstrip("/").endswith("/manga"):
                return rt.fulfill(status=200, content_type="text/html; charset=utf-8", body=PAGE)
            if rt.request.method == "POST" and u.endswith("/manga/dialogues_ecouter"):
                ecoutes.append(json.loads(rt.request.post_data or "{}"))
                return rt.fulfill(status=200, content_type="application/json", body='{"error": "banc : ecoute interceptee"}')
            return rt.continue_()
        pg.route("**/*", route)
        pg.goto("http://127.0.0.1:8191/manga#k=" + KEY); pg.wait_for_timeout(2000)
        pg.evaluate("() => localStorage.setItem('manga_serie','one-punch-man')"); pg.reload()
        pg.wait_for_function("() => typeof RESUME !== 'undefined' && RESUME && RESUME.chapitres", timeout=30000); pg.wait_for_timeout(800)
        pg.evaluate("() => openChap(CHAPS.findIndex(c => c.dir === 'one-punch-man/ch_5'))")
        pg.wait_for_function("() => DLG.e && DLG.e.doc", timeout=20000); pg.wait_for_timeout(800)
        pg.evaluate("() => dlgPrepOuvrir()"); pg.wait_for_timeout(3500)
        sel = '#dlgPrep .dlgp-carte[data-p="0"] select[data-k="voix_el"]'
        seps = pg.evaluate("s => [...document.querySelector(s).options].filter(o => o.disabled).map(o => o.textContent)", sel)
        check("séparations VISIBLES (lignes) : « 🇫🇷 Voix françaises » puis « Autres voix »", len(seps) == 2 and "Voix françaises" in seps[0] and "Autres voix" in seps[1], seps)
        vfr = pg.evaluate("s => [...document.querySelector(s).options].find(o => !o.disabled && DLG.voix.some(v => v.id === o.value && v.fr && v.genre === 'male')).value", sel)
        pg.select_option(sel, vfr); pg.wait_for_timeout(2500)
        pg.click('#dlgPrep .dlgp-carte[data-p="0"] [data-fav]'); pg.wait_for_timeout(2500)
        reg = json.load(open(os.path.join(T, "_reglages.json"), encoding="utf-8"))
        check("☆ : voix PRÉFÉRÉE enregistrée pour CETTE application", reg.get("voix_favorites") == [vfr], reg.get("voix_favorites"))
        opts = pg.evaluate("s => [...document.querySelector(s).options].slice(0, 3).map(o => [o.disabled, o.value, o.textContent.slice(0, 30)])", sel)
        check("liste : « ⭐ Mes voix préférées » EN TÊTE, avec elle", opts[0][0] and "préférées" in opts[0][2] and opts[1][1] == vfr, opts)
        check("★ plein à côté de la voix", pg.inner_text('#dlgPrep .dlgp-carte[data-p="0"] [data-fav]') == "★")
        # narrateur : l'ecoute d'essai envoie SA CLE
        i = pg.evaluate("() => dlgPersos().findIndex(p => p.narrateur)")
        pg.evaluate("i => document.querySelector('#dlgPrep .dlgp-carte[data-p=\"' + i + '\"] [data-ecoute-p]').click()", i); pg.wait_for_timeout(1500)
        check("narrateur : l'écoute d'essai demande « narrateur » (sa clé), plus « Narrateur »", ecoutes and ecoutes[-1].get("qui") == "narrateur", ecoutes[-1:])
        check("0 erreur JS", not errs, errs)
    import dialogues as dl
    distrib = json.load(open(os.path.join(SD, "dialogues_distribution.json"), encoding="utf-8"))
    check("cause prouvée : « Narrateur » introuvable, « narrateur » trouvé", dl.reglage_voix(distrib, "Narrateur") is None and dl.reglage_voix(distrib, "narrateur") is not None)
    r = subprocess.run([os.environ.get("MANGA_PY", r"D:\Download\02-Apps-Web\kohya-trainer\.venv\Scripts\python.exe"), "-c",
                        "import sys, json; sys.path.insert(0, r'%s'); import dialogues as dl, narrate_chapter as nc; nc.SECRET = nc._secret(); "
                        "c = dl.avec_preferees(dl.voix_francaises()); d = {'persos': [], 'narrateur': {}}; "
                        "dl.fusionner_distribution(d, [{'nom': 'Nouveau', 'genre': 'homme'}], c); print(json.dumps([c[0]['id'], c[0].get('prefere'), d['persos'][0]['voix_el']]))" % HERE],
                       capture_output=True, text=True, env=dict(os.environ, MANGA_SOURCES_DIR=T))
    out = json.loads((r.stdout or "[]").strip().splitlines()[-1] or "[]") if r.stdout.strip() else []
    check("distribution automatique : la préférée EN TÊTE et donnée au nouveau personnage homme", out[:2] == [vfr, True] and out[2] == vfr, (out, r.stderr[-200:]))
    check("réglages RÉELS des 2 applications intacts", [emp(f) for f in REELS] == avant)
finally:
    srv.kill(); time.sleep(1); shutil.rmtree(T, ignore_errors=True)
    try:
        os.remove(os.path.expanduser(r"~\Documents\ComfyUI\_studio_llm_proxy_8191.py"))
    except Exception:
        pass
print("VERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
