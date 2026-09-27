# -*- coding: utf-8 -*-
"""Banc R17 (v2.87.0) : la vitesse d'ECOUTE d'un personnage est GRATUITE. ISOLE : instance 8191 (proxy patche 9) sur une COPIE
d'OPM ch.5 (voix faites). On regle « 🎧 Vitesse d'ecoute » de Genos a 1,3 dans l'ecran ✏ (vrai curseur) puis : distribution
enregistree ; AUCUNE voix « a refaire » (0 credit) ; lecteur des Dialogues : playbackRate = vitesse generale x 1,3 sur une
replique de Genos, x 1 sur les autres ; video : « a refaire » (gratuit), refaite par l'app -> plus courte. 0 credit.
Usage : python test_dialogues_ecoute_ui.py <html> <proxy>        (html v2.86.0 -> ROUGE)"""
import json, os, shutil, subprocess, sys, tempfile, time, urllib.request
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
HTML, PROXY = (os.path.abspath(x) for x in sys.argv[1:3])
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
SRC = r"C:\Users\quang\Documents\MangaStudio-donnees\sources"
PAGE = open(HTML, encoding="utf-8").read()
OK, KO = [], []


def check(n, c, d=""):
    (OK if c else KO).append(n); print(("  [OK] " if c else "  [KO] ") + n + (" -- " + str(d)[:180] if d else ""), flush=True)


T = tempfile.mkdtemp(prefix="dlg_ecoute_")
SD = os.path.join(T, "one-punch-man")
os.makedirs(SD)
shutil.copytree(os.path.join(SRC, "one-punch-man", "ch_5"), os.path.join(SD, "ch_5"), ignore=shutil.ignore_patterns("narration"))
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
        b = p.chromium.launch(channel="msedge", headless=True, args=["--mute-audio", "--autoplay-policy=no-user-gesture-required"])
        pg = b.new_context(viewport={"width": 1280, "height": 900}).new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("dialog", lambda d: d.accept())
        pg.route("**/*", lambda rt: rt.fulfill(status=200, content_type="text/html; charset=utf-8", body=PAGE)
                 if rt.request.method == "GET" and rt.request.url.split("#")[0].split("?")[0].rstrip("/").endswith("/manga") else rt.continue_())
        pg.goto("http://127.0.0.1:8191/manga#k=" + KEY); pg.wait_for_timeout(2000)
        pg.evaluate("() => localStorage.setItem('manga_serie','one-punch-man')"); pg.reload()
        pg.wait_for_function("() => typeof RESUME !== 'undefined' && RESUME && RESUME.chapitres", timeout=30000); pg.wait_for_timeout(800)
        pg.evaluate("() => openChap(CHAPS.findIndex(c => c.dir === 'one-punch-man/ch_5'))")
        pg.wait_for_function("() => DLG.e && DLG.e.doc && DLG.plan", timeout=20000); pg.wait_for_timeout(1000)
        af0, dur0 = pg.evaluate("() => DLG.plan.a_faire"), None
        vid0 = pg.evaluate("() => JSON.stringify(DLG.plan.videos || DLG.plan.video)")
        pg.evaluate("() => dlgPrepOuvrir()"); pg.wait_for_timeout(1500)
        i = pg.evaluate("() => dlgPersos().findIndex(p => p.nom === 'Genos')")
        cur = pg.locator('#dlgPrep .dlgp-carte[data-p="%d"] input[data-k="ecoute"]' % i)
        check("écran ✏ : curseur « 🎧 Vitesse d'écoute » pour Genos", cur.count() == 1)
        cur.fill("1.3"); cur.dispatch_event("input"); cur.dispatch_event("change"); pg.wait_for_timeout(2500)
        dist = json.load(open(os.path.join(SD, "dialogues_distribution.json"), encoding="utf-8"))
        g = next(x for x in dist["persos"] if x["nom"] == "Genos")
        check("distribution enregistrée : Genos ecoute = 1.3, vitesse de diction inchangée", g.get("ecoute") == 1.3, (g.get("ecoute"), g.get("vitesse")))
        af1 = pg.evaluate("() => DLG.plan.a_faire")
        check("AUCUNE voix à refaire (0 crédit) : %s -> %s" % (af0, af1), af1 == af0 == 0, (af0, af1))
        vid1 = pg.evaluate("() => JSON.stringify(DLG.plan.videos || DLG.plan.video)")
        check("la vidéo, elle, passe « à refaire » (gratuit)", "perimee" in vid1 and vid1 != vid0, (vid0, vid1))
        pg.evaluate("() => $('dlgpRet').click()"); pg.wait_for_timeout(500)
        # lecteur : x 1,3 sur Genos, x 1 ailleurs
        pg.evaluate("() => $('dlgLire').click()"); pg.wait_for_timeout(2500)
        mes = pg.evaluate("""async () => { const out = {}; const vg = +$('dllVit').value;
            for (let k = 0; k < DLL.liste.length && Object.keys(out).length < 2; k++){
              const x = DLL.liste[k]; if (x.vide || dllEtat(x) !== 'faite') continue;
              const cle = x.qui === 'Genos' ? 'genos' : 'autre'; if (out[cle]) continue;
              DLL.i = k; dllMontrer(); await new Promise(r => setTimeout(r, 700)); out[cle] = [DLL.audio.playbackRate, vg]; }
            return out; }""")
        check("lecteur : réplique de Genos à vitesse générale x 1,3", mes.get("genos") and abs(mes["genos"][0] - mes["genos"][1] * 1.3) < 0.01, mes)
        check("lecteur : un autre personnage à vitesse générale x 1", mes.get("autre") and abs(mes["autre"][0] - mes["autre"][1]) < 0.01, mes)
        pg.evaluate("() => $('dllFermer').click()"); pg.wait_for_timeout(300)
        # video refaite par l'app (montage local, 0 credit) : plus courte que l'ancienne
        v_av = json.load(open(os.path.join(SD, "ch_5", "dialogues", "dialogues.json"), encoding="utf-8"))
        d_av = (v_av.get("video") or {}).get("duree") or next(iter((v_av.get("videos") or {}).values()), {}).get("duree")
        t_clic = time.time()
        print("   bouton 🎬 :", pg.evaluate("() => [$('dlgVid').disabled, $('dlgVid').textContent, DLG.portee]"))
        print("   lancement :", pg.evaluate("() => api('/manga/dialogues_lancer', {d: 'one-punch-man/ch_5', action: 'video'})"))
        pr = {}
        for _ in range(120):                   # attendre CE montage (le progress copie avec le chapitre dit deja « fini »)
            time.sleep(2)
            pr = json.load(open(os.path.join(SD, "ch_5", "dialogues", "progress.json"), encoding="utf-8"))
            if pr.get("fini") and (pr.get("t") or 0) > t_clic:
                break
        rl = os.path.join(SD, "ch_5", "dialogues", "run.log")
        print("   run.log :", open(rl, encoding="utf-8", errors="replace").read()[-600:] if os.path.isfile(rl) else "ABSENT")
        print("   toasts :", pg.evaluate("() => [...document.querySelectorAll('.toast, #toast')].map(x => x.textContent).join(' | ')"))
        v_ap = json.load(open(os.path.join(SD, "ch_5", "dialogues", "dialogues.json"), encoding="utf-8"))
        d_ap = (v_ap.get("video") or {}).get("duree") or next(iter((v_ap.get("videos") or {}).values()), {}).get("duree")
        check("vidéo refaite par l'app, plus courte (%s s -> %s s)" % (d_av, d_ap), pr.get("etape") == "fini" and d_av and d_ap and d_ap < d_av - 0.5, pr)
        pg.evaluate("() => dlgCharger()"); pg.wait_for_timeout(2000)
        check("après montage : vidéo « à jour », toujours 0 voix à refaire",
              "perimee" not in pg.evaluate("() => JSON.stringify(DLG.plan.videos || DLG.plan.video)") and pg.evaluate("() => DLG.plan.a_faire") == 0)
        check("0 erreur JS", not errs, errs)
finally:
    srv.kill()
    time.sleep(1)
    shutil.rmtree(T, ignore_errors=True)
    try:
        os.remove(os.path.expanduser(r"~\Documents\ComfyUI\_studio_llm_proxy_8191.py"))
    except Exception:
        pass
print("VERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
