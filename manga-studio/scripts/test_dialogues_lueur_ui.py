# -*- coding: utf-8 -*-
"""Banc R8 (v2.83.0) : la lueur de l'etape suivante des Dialogues -- UNE etape, le BON bouton. ISOLE : instance 8191 sur une
COPIE d'OPM ch.5 (prepare, voix faites). Les etats sont poses dans DLG puis l'app redessine (clMaj toutes les 800 ms) : on lit
ce qui brille VRAIMENT. 0 credit (aucun lancement).
Usage : python test_dialogues_lueur_ui.py <html> <proxy> [largeur]      (html = page v2.82.4 -> doit sortir ROUGE)"""
import json, os, shutil, subprocess, sys, tempfile, time, urllib.request
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
HTML, PROXY = (os.path.abspath(x) for x in sys.argv[1:3])
LARG = int(sys.argv[3]) if len(sys.argv) > 3 else 360
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
SRC = r"C:\Users\quang\Documents\MangaStudio-donnees\sources"
PAGE = open(HTML, encoding="utf-8").read()
OK, KO = [], []


def check(n, c, d=""):
    (OK if c else KO).append(n); print(("  [OK] " if c else "  [KO] ") + n + (" -- " + str(d)[:170] if d else ""), flush=True)


T = tempfile.mkdtemp(prefix="dlg_lueur_")
SD = os.path.join(T, "one-punch-man")
os.makedirs(SD)
shutil.copytree(os.path.join(SRC, "one-punch-man", "ch_5"), os.path.join(SD, "ch_5"), ignore=shutil.ignore_patterns("narration", "*.mp4"))
for f in ("serie.json", "suivi.json", "dialogues_distribution.json"):
    shutil.copy(os.path.join(SRC, "one-punch-man", f), os.path.join(SD, f))
srv = subprocess.Popen([sys.executable, os.path.join(HERE, "proxy_8191.py"), PROXY], env=dict(os.environ, MANGA_SOURCES_DIR=T),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
# ce qui brille : [id ou « tete:<data-dlg> »]
BRILLE = """() => [...document.querySelectorAll('.btn.dlg-suiv')].map(b => b.id || ('tete:' + (b.dataset.dlg || '?')))"""
POSER = """(o) => { const p = DLG.plan; DLG.solde = {ok: true, restants: 99999};
  if (o.plan) Object.assign(p, o.plan);
  if (o.traiter !== undefined){ const ks = Object.keys(p.repliques); ks.forEach((k, i) => p.repliques[k] = i < o.traiter ? 'a_traiter' : 'ok'); }
  if (o.doc === null) DLG.e.doc = null;
  if (o.en_cours) DLG.e.en_cours = true;
  if (o.lu !== undefined){ if (o.lu === null) localStorage.removeItem(dlgLuCle(DLG.d)); else localStorage.setItem(dlgLuCle(DLG.d), String(o.lu)); }
  if (o.sansVideo){ DLG.e.doc.videos = {}; DLG.e.doc.video = null; p.videos = {}; p.video = 'absente'; }
  dlgRendre(); }"""
try:
    for _ in range(60):
        try:
            urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8191/manga/el_solde", headers={"Authorization": "Bearer " + KEY}), timeout=5); break
        except Exception:
            time.sleep(1)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True, args=["--mute-audio"])
        ctx = b.new_context(viewport={"width": LARG, "height": 800}, is_mobile=LARG < 700, has_touch=LARG < 700)
        pg = ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("dialog", lambda d: d.accept())
        pg.route("**/*", lambda rt: rt.fulfill(status=200, content_type="text/html; charset=utf-8", body=PAGE)
                 if rt.request.method == "GET" and rt.request.url.split("#")[0].split("?")[0].rstrip("/").endswith("/manga") else rt.continue_())
        pg.goto("http://127.0.0.1:8191/manga#k=" + KEY); pg.wait_for_timeout(2500)
        pg.evaluate("() => localStorage.setItem('manga_serie','one-punch-man')"); pg.reload()
        pg.wait_for_function("() => typeof RESUME !== 'undefined' && RESUME && RESUME.chapitres", timeout=30000); pg.wait_for_timeout(800)
        pg.evaluate("() => openChap(CHAPS.findIndex(c => c.dir === 'one-punch-man/ch_5'))")
        pg.wait_for_function("() => DLG.e && DLG.e.doc && DLG.plan", timeout=20000); pg.wait_for_timeout(1500)
        nrep = pg.evaluate("() => Object.keys(DLG.plan.repliques).length")
        check("chapitre de test prepare (%d repliques)" % nrep, nrep > 3)

        def etat(nom, o, attendu, doit):
            pg.evaluate(POSER, o); pg.wait_for_timeout(1100)          # > 800 ms : clMaj a repose la lueur
            br = pg.evaluate(BRILLE)
            suiv = pg.evaluate("() => typeof dlgSuivante === 'function' ? dlgSuivante() : 'absente'")
            check(nom + " -> « " + attendu + " »", suiv == attendu and set(br) == set(doit), (suiv, br))
            return br

        etat("⚠ a traiter (meme avec des voix a faire)", {"traiter": 2, "plan": {"a_faire": 3, "deja": 0}}, "ouvrir", ["dlgOuvrir", "tete:ouvrir"])
        etat("prepare, rien a traiter, 3 voix a faire", {"traiter": 0, "plan": {"a_faire": 3, "deja": 0}}, "voix", ["dlgVoix", "tete:voix"])
        etat("credits insuffisants : rien ne brille", {"traiter": 0, "plan": {"a_faire": 3, "deja": 0, "credits": 10 ** 9}}, "", [])
        etat("voix pretes, jamais ecoutees ici", {"traiter": 0, "plan": {"a_faire": 0, "deja": 5, "credits": 0}, "lu": None}, "lire", ["dlgLire", "tete:lire"])
        # le VRAI geste : ▶ Lire (le lecteur s'ouvre), puis on le ferme
        pg.evaluate("() => $('dlgLire').click()"); pg.wait_for_timeout(1500)
        lu = pg.evaluate("() => localStorage.getItem(dlgLuCle(DLG.d))")
        check("▶ Lire note l'ecoute (5 voix)", lu == "5", lu)
        pg.keyboard.press("Escape"); pg.wait_for_timeout(600)
        pg.evaluate("() => { const f = document.querySelector('#dlgLecteur .retour, #dllFermer'); if (f && f.offsetParent) f.click(); }"); pg.wait_for_timeout(600)
        etat("ecoutees, pas de video -> 🎬", {"sansVideo": True}, "video", ["dlgVid"])
        etat("3 voix de plus pretes -> a nouveau ▶ Lire", {"plan": {"deja": 8}}, "lire", ["dlgLire", "tete:lire"])
        etat("traitement en cours : rien", {"en_cours": True}, "", [])
        pg.evaluate("() => { DLG.e.en_cours = false; }")
        etat("chapitre jamais prepare : rien (pas de concurrence avec la Narration)", {"doc": None}, "", [])
        # l'ecran ✏ : recharger l'etat reel, 3 voix a faire -> « Generer les voix manquantes » brille dans le pied
        pg.evaluate("() => dlgCharger()"); pg.wait_for_function("() => DLG.e && DLG.e.doc", timeout=15000); pg.wait_for_timeout(800)
        pg.evaluate("() => dlgPrepOuvrir()"); pg.wait_for_timeout(1200)
        pg.evaluate(POSER, {"traiter": 0, "plan": {"a_faire": 3, "deja": 0, "credits": 50}}); pg.evaluate("() => dlgPrepRendre()"); pg.wait_for_timeout(1100)
        br = pg.evaluate(BRILLE)
        check("ecran ✏ : le pied « Générer les voix manquantes » brille", "dlgpGen" in br, br)
        check("une seule etape a la fois (pas de ▶ Lire en meme temps)", not [x for x in br if "ire" in x], br)
        anim = pg.evaluate("() => { const b = $('dlgpGen'); return b ? getComputedStyle(b).animationName : '' }")
        check("meme animation que la Narration (clLueur)", anim == "clLueur", anim)
        check("0 erreur JS", not errs, errs)
finally:
    srv.kill()
    shutil.rmtree(T, ignore_errors=True)
    try:
        os.remove(os.path.expanduser(r"~\Documents\ComfyUI\_studio_llm_proxy_8191.py"))
    except Exception:
        pass
print("VERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
