# -*- coding: utf-8 -*-
"""Banc R3-bis (v2.82.1, Quang 27/09 03h08 : « plusieurs videos sur un meme chapitre, pages 5 a 10 et 35 a 42 ? ») : UNE video par
portee. ISOLE : instance 8191 (proxy patche 7) sur une COPIE d'OPM ch.5 (12 voix, video « chapitre entier » deja la) ; page = le
HTML donne. Les videos sont VRAIMENT fabriquees (ffmpeg, 0 credit).
Usage : python test_dialogues_video_portee_ui.py <html> <proxy>        (html = page v2.82.0 -> doit sortir ROUGE)"""
import json, os, shutil, subprocess, sys, tempfile, time, urllib.request
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
HTML, PROXY = (os.path.abspath(x) for x in sys.argv[1:3])
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
SRC = r"C:\Users\quang\Documents\MangaStudio-donnees\sources"
PAGE = open(HTML, encoding="utf-8").read()
OK, KO = [], []


def check(n, c, d=""):
    (OK if c else KO).append(n); print(("  [OK] " if c else "  [KO] ") + n + (" -- " + str(d)[:170] if d else ""), flush=True)


T = tempfile.mkdtemp(prefix="dlg_vid_portee_")
os.makedirs(os.path.join(T, "one-punch-man"))
shutil.copytree(os.path.join(SRC, "one-punch-man", "ch_5"), os.path.join(T, "one-punch-man", "ch_5"), ignore=shutil.ignore_patterns("narration"))
for f in ("serie.json", "dialogues_distribution.json", "suivi.json"):
    shutil.copy(os.path.join(SRC, "one-punch-man", f), os.path.join(T, "one-punch-man", f))
VD = os.path.join(T, "one-punch-man", "ch_5", "dialogues", "video")
srv = subprocess.Popen([sys.executable, os.path.join(HERE, "proxy_8191.py"), PROXY], env=dict(os.environ, MANGA_SOURCES_DIR=T),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def attendre(pg, delai=90):
    t0 = time.time()
    pg.wait_for_timeout(1500)
    while time.time() - t0 < delai:
        if not pg.evaluate("() => !!(DLG.e && DLG.e.en_cours)"):
            break
        pg.wait_for_timeout(1500)
    pg.evaluate("() => dlgCharger()"); pg.wait_for_timeout(2500)


try:
    for _ in range(60):
        try:
            urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8191/manga/el_solde", headers={"Authorization": "Bearer " + KEY}), timeout=5); break
        except Exception:
            time.sleep(1)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True, args=["--mute-audio"])
        ctx = b.new_context(viewport={"width": 1280, "height": 900})
        pg = ctx.new_page(); errs = []; toasts = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.route("**/*", lambda rt: rt.fulfill(status=200, content_type="text/html; charset=utf-8", body=PAGE)
                 if rt.request.method == "GET" and rt.request.url.split("#")[0].split("?")[0].rstrip("/").endswith("/manga") else rt.continue_())
        pg.goto("http://127.0.0.1:8191/manga#k=" + KEY); pg.wait_for_timeout(2500)
        pg.evaluate("() => localStorage.setItem('manga_serie','one-punch-man')"); pg.reload()
        pg.wait_for_function("() => typeof RESUME !== 'undefined' && RESUME && RESUME.chapitres", timeout=30000); pg.wait_for_timeout(1000)
        pg.evaluate("() => { const t0 = window.toast; window.toast = m => { (window.__toasts = window.__toasts || []).push(m); return t0(m); }; }")
        pg.evaluate("() => openChap(CHAPS.findIndex(c => c.dir === 'one-punch-man/ch_5'))"); pg.wait_for_timeout(3000)
        if "cl-ouv" not in pg.evaluate("() => $('dlgBox').className"):
            pg.click("#dlgBox .cl-chev"); pg.wait_for_timeout(300)
        pg.click("#dlgBox .dlg-p[data-portee=pages]"); pg.fill("#dlgDe", "13"); pg.fill("#dlgA", "14"); pg.wait_for_timeout(400)
        check("bouton 🎬 nomme la portee des champs (« … p. 13-14 »)", pg.evaluate("() => $('dlgVid').textContent").endswith("p. 13-14"), pg.evaluate("() => $('dlgVid').textContent"))
        pg.click("#dlgVid"); attendre(pg)
        pg.fill("#dlgDe", "15"); pg.fill("#dlgA", "15"); pg.wait_for_timeout(400)
        pg.click("#dlgVid"); attendre(pg)
        fichiers = sorted(f for f in os.listdir(VD) if f.endswith(".mp4"))
        check("deux videos DISTINCTES fabriquees, l'ancienne gardee", fichiers == ["dialogues.mp4", "dialogues_p13-14.mp4", "dialogues_p15-15.mp4"], fichiers)
        liste = pg.evaluate("() => $('dlgVids').hidden ? '' : $('dlgVids').innerText.replace(/\\s+/g, ' ')")
        check("la ligne 🎭 liste les 3 videos (chapitre entier, p. 13-14, p. 15-15), a jour", all(t in liste for t in ("chapitre entier", "p. 13-14", "p. 15-15")) and "à refaire" not in liste, liste)
        pg.fill("#dlgDe", "13"); pg.fill("#dlgA", "14"); pg.wait_for_timeout(400)
        check("champs 13-14 : « Refaire la vidéo p. 13-14 », ▶ Voir visible", pg.evaluate("() => $('dlgVid').textContent") == "🎬 Refaire la vidéo p. 13-14" and pg.evaluate("() => !$('dlgVidVoir').hidden"))
        pg.evaluate("() => $('dlgVidVoir').click()"); pg.wait_for_timeout(1200)
        check("▶ Voir = la video de CETTE portee", pg.evaluate("() => decodeURIComponent($('vidLecVideo').src).includes('dialogues_p13-14.mp4')"), pg.evaluate("() => decodeURIComponent($('vidLecVideo').src).split('p=')[1].split('&')[0]"))   # jamais l'adresse entiere (elle porte le secret)
        pg.evaluate("() => $('vidLecFermer').click()")
        pg.evaluate("() => document.querySelector('#dlgVids [data-dlgv=voir][data-k=\"15-15\"]').click()"); pg.wait_for_timeout(1200)
        check("la liste : ▶ de p. 15-15 lit la sienne", pg.evaluate("() => decodeURIComponent($('vidLecVideo').src).includes('dialogues_p15-15.mp4')"))
        pg.evaluate("() => $('vidLecFermer').click()")
        # R7 : plusieurs videos de dialogues dans la serie -> precedente / suivante / enchainement, DANS le lecteur video de l'app
        pg.evaluate("() => document.querySelector('#dlgVids [data-dlgv=voir][data-k=\"13-14\"]').click()"); pg.wait_for_timeout(2500)
        nav = pg.evaluate("() => [$('vidLecPrev').hidden ? '' : $('vidLecPrev').textContent, $('vidLecNext').hidden ? '' : $('vidLecNext').textContent]")
        check("R7 : p.13-14 dans le lecteur de l'app, ⏮ = chapitre entier, ⏭ = p. 15-15", not pg.evaluate("() => $('vidLecteur').hidden") and nav[0].strip() == "⏮ ch. 5" and "p. 15-15" in nav[1], nav)
        pg.evaluate("() => { const e = $('vidLecVideo'); e.currentTime = Math.max(0, e.duration - 0.3); }"); pg.wait_for_timeout(2500)
        check("R7 : fin de video = « ch. 5 · p. 15-15 dans N s » (enchainement)", pg.evaluate("() => !$('vidSuite').hidden && $('vidSuiteTxt').textContent.includes('p. 15-15')"),
              pg.evaluate("() => $('vidSuiteTxt').textContent"))
        pg.evaluate("() => $('vidSuiteOui').click()"); pg.wait_for_timeout(2000)
        check("R7 : « Maintenant » ouvre la video p.15-15, derniere : pas de suivante", pg.evaluate("() => decodeURIComponent($('vidLecVideo').src).includes('dialogues_p15-15.mp4') && $('vidLecNext').hidden"))
        pg.keyboard.press("g"); pg.wait_for_timeout(600)
        sel = pg.evaluate("() => $('selFeuille').hidden ? '' : $('selFeuille').innerText.replace(/\s+/g, ' ')")
        check("R7 : touche G = selecteur des videos de DIALOGUES (pas de la narration)", "Dialogues — aller à la vidéo" in sel and "p. 13-14" in sel, sel[:120])
        pg.evaluate("() => { const b = [...document.querySelectorAll('#selFeuille [data-k]')].find(x => x.textContent.includes('13-14')); if (b) b.click(); }"); pg.wait_for_timeout(1500)
        check("R7 : choisir p.13-14 dans le selecteur l'ouvre", pg.evaluate("() => decodeURIComponent($('vidLecVideo').src).includes('dialogues_p13-14.mp4')"))
        pg.evaluate("() => $('vidLecFermer').click()"); pg.wait_for_timeout(300)
        # une voix disparait en p.14 : la video 13-14 est refusee AVANT d'etre lancee, et le dit
        doc = json.load(open(os.path.join(T, "one-punch-man", "ch_5", "dialogues", "dialogues.json"), encoding="utf-8"))
        x = next(y for y in doc["repliques"] if y["page"] == 14 and y.get("voix"))
        os.remove(os.path.join(T, "one-punch-man", "ch_5", "dialogues", "voix", x["voix"]["fichier"]))
        pg.evaluate("() => dlgCharger()"); pg.wait_for_timeout(2500)
        pg.evaluate("() => window.__toasts = []")
        pg.click("#dlgVid"); pg.wait_for_timeout(800)
        t = pg.evaluate("() => (window.__toasts || []).join(' | ')")
        check("voix manquante en p.14 : refus annonce AVANT de lancer", "sans voix à jour" in t and not pg.evaluate("() => !!(DLG.e && DLG.e.en_cours)"), t)
        pg.fill("#dlgDe", "15"); pg.fill("#dlgA", "15"); pg.wait_for_timeout(300)
        check("p.15 n'est pas touchee : sa video reste « Refaire » (a jour)", pg.evaluate("() => $('dlgVid').textContent") == "🎬 Refaire la vidéo p. 15-15")
        # le panneau de la serie compte les videos
        pg.evaluate("() => { $('chapDetail').hidden = true; }")
        pg.evaluate("() => { $('dlgsBox').hidden = false; dlgsCharger('one-punch-man'); }"); pg.wait_for_timeout(3500)
        l5 = pg.evaluate("() => { const l = document.querySelector('#dlgsListe .dlgs-l[data-dir=\"one-punch-man/ch_5\"]'); return l ? l.innerText.replace(/\\s+/g, ' ') : '' }")
        check("panneau de la serie : « 🎬 3 vidéos » + ▶ Vidéo", "3 vidéos" in l5 and "Vidéo" in l5, l5)
        check("0 erreur JS", not errs, errs)
finally:
    srv.kill()
    shutil.rmtree(T, ignore_errors=True)
    try:
        os.remove(os.path.expanduser(r"~\Documents\ComfyUI\_studio_llm_proxy_8191.py"))
    except Exception:
        pass
print("VERDICT : %d OK / %d KO" % (len(OK), len(KO)))
