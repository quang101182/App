# -*- coding: utf-8 -*-
"""Banc R10 (v2.85.0) : le « ✓ fini » est COMMUN a tous les appareils. ISOLE : instance 8191 (copie du proxy patchee par
patch_activite_finis.py) sur une COPIE d'OPM ch.5. Une tache Dialogues FACTICE (progress.json + un PID qui dort) tourne,
vue par le « telephone » ; elle finit PENDANT que le « PC » est ferme ; le PC ouvre l'app -> il doit afficher la fin.
Puis un ARRET (⏹), puis un redemarrage du serveur (le journal survit). 0 credit, 0 appel paye.
Usage : python test_activite_finis_ui.py <html> <proxy_patche>     (html v2.84.0 ou proxy non patche -> ROUGE)"""
import json, os, shutil, subprocess, sys, tempfile, time, urllib.request
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
HTML, PROXY = (os.path.abspath(x) for x in sys.argv[1:3])
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
SRC = r"C:\Users\quang\Documents\MangaStudio-donnees\sources"
PAGE = open(HTML, encoding="utf-8").read()
OK, KO = [], []


def check(n, c, d=""):
    (OK if c else KO).append(n); print(("  [OK] " if c else "  [KO] ") + n + (" -- " + str(d)[:200] if d else ""), flush=True)


T = tempfile.mkdtemp(prefix="act_finis_")
SD = os.path.join(T, "one-punch-man")
os.makedirs(SD)
shutil.copytree(os.path.join(SRC, "one-punch-man", "ch_5"), os.path.join(SD, "ch_5"), ignore=shutil.ignore_patterns("narration", "video", "*.mp4"))
for f in ("serie.json", "suivi.json", "dialogues_distribution.json"):
    shutil.copy(os.path.join(SRC, "one-punch-man", f), os.path.join(SD, f))
PROG = os.path.join(SD, "ch_5", "dialogues", "progress.json")
os.makedirs(os.path.dirname(PROG), exist_ok=True)


def tache(etape):                           # une tache qui TOURNE : un PID vivant + un progress frais
    dort = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(900)"])
    json.dump({"pid": dort.pid, "t": time.time(), "etape": etape, "fait": 3, "total": 9}, open(PROG, "w", encoding="utf-8"))
    return dort


def finir(dort, etape_fin):
    dort.kill(); dort.wait()
    d = {"t": time.time(), "etape": etape_fin, "fait": 9, "total": 9, "fini": True}   # comme dialogues.py / manga_dialogues_arreter
    json.dump(d, open(PROG, "w", encoding="utf-8"))


def serveur():
    p = subprocess.Popen([sys.executable, os.path.join(HERE, "proxy_8191.py"), PROXY], env=dict(os.environ, MANGA_SOURCES_DIR=T),
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        try:
            urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8191/manga/activite", headers={"Authorization": "Bearer " + KEY}), timeout=5)
            return p
        except Exception:
            time.sleep(1)
    return p


def ouvrir(b, larg):
    ctx = b.new_context(viewport={"width": larg, "height": 800}, is_mobile=larg < 700, has_touch=larg < 700)
    pg = ctx.new_page(); pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)))
    pg.route("**/*", lambda rt: rt.fulfill(status=200, content_type="text/html; charset=utf-8", body=PAGE)
             if rt.request.method == "GET" and rt.request.url.split("#")[0].split("?")[0].rstrip("/").endswith("/manga") else rt.continue_())
    pg.goto("http://127.0.0.1:8191/manga#k=" + KEY); pg.wait_for_timeout(1500)
    pg.evaluate("() => localStorage.setItem('manga_serie','one-punch-man')"); pg.reload()
    pg.wait_for_function("() => typeof ACT !== 'undefined' && ACT.maj", timeout=30000); pg.wait_for_timeout(800)
    return ctx, pg


def pastille(pg):
    return pg.evaluate("() => $('actTxt').textContent")


def attendre(pg, texte, s=25):
    for _ in range(s * 2):
        if texte in pastille(pg):
            return True
        pg.wait_for_timeout(500)
    return False


def liste(pg):                               # « Terminé récemment » (le panneau ouvert)
    pg.evaluate("() => { $('actPanel').hidden = false; actRendre(); }")
    t = pg.evaluate("() => $('actFinis').innerText")
    pg.evaluate("() => { $('actPanel').hidden = true; }")
    return t


srv = serveur()
dorts = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True, args=["--mute-audio"])
        # 1. le TELEPHONE voit la tache tourner
        dorts.append(tache("voix"))
        ctel, tel = ouvrir(b, 360)
        check("téléphone : la tâche en cours est affichée", attendre(tel, "Dialogues"), pastille(tel))
        # 2. elle finit, le PC est FERME
        finir(dorts[-1], "fini")
        check("téléphone : « ✓ 🔊 Voix des dialogues finies » (R10-bis)", attendre(tel, "✓ 🔊 Voix des dialogues finies"), pastille(tel))
        # 3. le PC ouvre l'app APRES coup
        cpc, pc = ouvrir(b, 1280)
        pc.wait_for_timeout(1500)
        check("PC ouvert après coup : même « ✓ 🔊 Voix des dialogues finies »", "✓ 🔊 Voix des dialogues finies" in pastille(pc), pastille(pc))
        lp = liste(pc)
        check("PC : « Terminé récemment » la contient (avec le chapitre)", "Terminé récemment" in lp and "Voix des dialogues finies" in lp and "ch.5" in lp, lp)
        lt = liste(tel)
        check("téléphone : UNE seule entrée (vue locale + serveur dédoublonnées)", lt.count("Voix des dialogues finies") == 1, lt)
        # 4. un ARRET : jamais « fini »
        dorts.append(tache("preparation"))
        check("PC : la préparation en cours est affichée", attendre(pc, "Dialogues"), pastille(pc))
        cpc.close()
        finir(dorts[-1], "arrete")
        check("téléphone : « ⏹ 🎭 Préparation des dialogues arrêtée »", attendre(tel, "⏹ 🎭 Préparation des dialogues arrêtée"), pastille(tel))
        cpc, pc = ouvrir(b, 1280); pc.wait_for_timeout(1500)
        check("PC rouvert : « ⏹ … arrêtée », pas « fini »", "⏹ 🎭 Préparation des dialogues arrêtée" in pastille(pc), pastille(pc))
        # 5. le serveur redemarre : le journal survit (fichier dans les DONNEES de l'instance)
        srv.kill(); srv.wait(); srv = serveur()
        c3, p3 = ouvrir(b, 476); p3.wait_for_timeout(1500)
        l3 = liste(p3)
        check("serveur redémarré : les 2 fins toujours listées", "Voix des dialogues finies" in l3 and "Préparation des dialogues arrêtée" in l3, l3)
        jf = os.path.join(T, "_activite_finis.json")
        check("journal rangé dans les données de l'instance (pas une série)", os.path.isfile(jf)
              and "_activite_finis" not in p3.evaluate("() => JSON.stringify(CHAPS.map(c => c.dir))"))
        check("0 erreur JS (3 appareils)", not (tel.errs or pc.errs or p3.errs), tel.errs + pc.errs + p3.errs)
finally:
    for d in dorts:
        try:
            d.kill()
        except Exception:
            pass
    srv.kill()
    time.sleep(1)
    shutil.rmtree(T, ignore_errors=True)
    try:
        os.remove(os.path.expanduser(r"~\Documents\ComfyUI\_studio_llm_proxy_8191.py"))
    except Exception:
        pass
print("VERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
