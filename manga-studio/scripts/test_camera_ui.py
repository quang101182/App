# -*- coding: utf-8 -*-
"""Banc v2.5.0 : camera « case par case » sur l'APP REELLE (lecteur + profil + reglages video) et MIROIR JS <-> Python.

Series de TEST (copies, jamais la bibliotheque de Quang) : zz-essai-cases (One Punch-Man ch.300, manga, narration
k3-serie-ref) et zz-essai-webtoon (Solo Leveling Ragnarok ch.1, webtoon, gemini-charon).
1. le lecteur demande les cases, la detection se lance, la camera prend la page des qu'elles arrivent ;
2. la camera BOUGE (transform qui change), le voile eclaire une case ;
3. camPlan/camPose (JS) == cases_video.plan/pose (Python) sur TOUTES les pages des 2 formats, a 0,01 px pres ;
4. la case 🎥 : page entiere <-> cases, memorise dans le profil de la serie (suivi.json), vu par /manga/videos ;
5. le profil de serie montre le choix ; aucune erreur JS ; PC 1280 px + telephone 360 px.
Remet le profil comme avant. Usage : python test_camera_ui.py [port]
"""
import json, os, sys, time, urllib.request
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cases_video as cv

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
SRC = cv.SRC
OK, KO = [], []
M, WT = "zz-essai-cases/ch_300", "zz-essai-webtoon/ch_1"


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


def api(path, body=None):
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (PORT, path), data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def attendre_cases(d, s=120):
    t0 = time.time()
    while time.time() - t0 < s:
        j = api("/manga/cases?d=" + d)
        if not j["manquantes"]:
            return j
        time.sleep(3)
    return api("/manga/cases?d=" + d)


SUIVI = os.path.join(SRC, "zz-essai-cases", "suivi.json")
avant = open(SUIVI, encoding="utf-8").read() if os.path.isfile(SUIVI) else None
try:
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True, args=["--autoplay-policy=no-user-gesture-required"])
        for w, h in ((1280, 900), (360, 780)):
            print("=== %d px" % w)
            c = b.new_context(viewport={"width": w, "height": h}, has_touch=(w < 400), is_mobile=(w < 400))
            pg = c.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto("http://127.0.0.1:%d/manga#k=%s" % (PORT, KEY)); pg.wait_for_timeout(2500)
            check("version 2.5.0 affichee", pg.inner_text("#verBadge") == "v2.5.0", pg.inner_text("#verBadge"))
            # --- 1. lecteur (le lecteur ordinaire, ouvert comme une narration gardee : hlLire)
            pg.evaluate("() => hlLire({d: '%s', tag: 'k3-serie-ref'})" % M); pg.wait_for_timeout(2000)
            if w == 1280:
                check("detection lancee a l'ouverture (calcul) ou deja faite", pg.evaluate("() => !!CAM.data && (CAM.data.calcul || !CAM.data.manquantes)"),
                      pg.evaluate("() => CAM.data && {calcul: CAM.data.calcul, manq: CAM.data.manquantes}"))
            attendre_cases(M)
            pg.wait_for_function("() => CAM.data && !CAM.data.manquantes", timeout=90000)
            # page 3 (index 1) : 4 cases -> camera
            pg.evaluate("() => { LEC.i = LEC.n.pages.findIndex(p => p.file === 'page_003.png'); montrerPage(); }"); pg.wait_for_timeout(1500)
            cam = pg.evaluate("() => $('lecImg').classList.contains('cam')")
            check("la camera prend la page des que ses cases sont la (classe cam, pas de kb)", cam and not pg.evaluate("() => $('lecImg').classList.contains('kb')"))
            t1 = pg.evaluate("() => $('lecImg').style.transform"); pg.wait_for_timeout(2500)
            t2 = pg.evaluate("() => $('lecImg').style.transform")
            check("la camera BOUGE (transform change en 2,5 s)", t1 and t2 and t1 != t2, (t1[:50], t2[:50]))
            vo = pg.evaluate("() => { const v = $('lecVoile'), r = v.getBoundingClientRect(); return {cache: v.hidden, w: r.width, h: r.height, "
                             "ombre: v.style.boxShadow}; }")
            check("le voile eclaire une case (visible, taille non nulle, ombre sombre)", not vo["cache"] and vo["w"] > 50 and vo["h"] > 50 and "rgba(5, 6, 8" in vo["ombre"], vo)
            sc = pg.evaluate("() => { const r = $('lecImg').parentElement.getBoundingClientRect(); return [r.width, r.height]; }")
            check("la scene reste dans l'ecran (pas de debordement horizontal)", pg.evaluate("() => document.documentElement.scrollWidth <= innerWidth + 1"), sc)
            # --- 3. MIROIR JS == Python, toutes les pages, manga ET webtoon
            if w == 1280:
                attendre_cases(WT)
                for d in (M, WT):
                    data = api("/manga/cases?d=" + d)
                    ecarts, n = [], 0
                    for fic, e in data["pages"].items():
                        for A in (1080 / 1464.0, sc[0] / sc[1], 1.6):
                            for T in (2.5, 11.3):
                                ts = [T * k / 23.0 for k in range(24)]
                                js = pg.evaluate("([e, f, A, T, ts]) => ts.map(t => camPose(camPlan(e, f, A, T), t))", [e, data["format"], A, T, ts])
                                pl = cv.plan(e, data["format"], A, T)
                                for t, j in zip(ts, js):
                                    r, case, a = cv.pose(pl, t)
                                    n += 1
                                    dif = max([abs(x - y) for x, y in zip(r, j[0])] + [abs(a - j[2])]
                                              + ([abs(x - y) for x, y in zip(case, j[1])] if case and j[1] else [0 if case == j[1] else 1e9]))
                                    if dif > 0.01:
                                        ecarts.append((fic, A, T, round(t, 2), dif))
                    check("miroir JS == Python : %s (%d poses)" % (data["format"], n), not ecarts, ecarts[:3])
            # --- 4. la case 🎥 -> page entiere, memorisee pour la serie
            pg.evaluate("() => { const c = $('lecCamOn'); c.checked = false; c.dispatchEvent(new Event('change')); }"); pg.wait_for_timeout(1500)
            st = pg.evaluate("() => ({cam: $('lecImg').classList.contains('cam'), kb: /kb/.test($('lecImg').className), voile: $('lecVoile').hidden, "
                             "tr: $('lecImg').style.transform, reg: reglagesLecteur().camera})")
            check("🎥 decoche -> page entiere (zoom lent kb, pas de voile, plus de transform camera)", not st["cam"] and st["kb"] and st["voile"] and not st["tr"], st)
            prof = json.load(open(SUIVI, encoding="utf-8"))
            check("... memorise dans le profil de la serie (suivi.json camera=page)", prof["reglages_video"].get("camera") == "page", prof["reglages_video"])
            check("... vu par /manga/videos et par les reglages envoyes aux videos", api("/manga/videos?serie=zz-essai-cases")["camera"] == "page"
                  and st["reg"] == "page")
            pg.evaluate("() => { LEC.i++; montrerPage(); }"); pg.wait_for_timeout(800)
            check("... la page suivante reste en page entiere", not pg.evaluate("() => $('lecImg').classList.contains('cam')"))
            pg.evaluate("() => { const c = $('lecCamOn'); c.checked = true; c.dispatchEvent(new Event('change')); }"); pg.wait_for_timeout(1500)
            check("🎥 recoche -> camera de nouveau, suivi.json camera=cases",
                  pg.evaluate("() => $('lecImg').classList.contains('cam') || !camEntree(LEC.n.pages[LEC.i])")
                  and json.load(open(SUIVI, encoding="utf-8"))["reglages_video"]["camera"] == "cases")
            # --- webtoon dans le lecteur
            pg.evaluate("() => $('lecFermer').click()"); pg.wait_for_timeout(300)
            pg.evaluate("() => hlLire({d: '%s', tag: 'gemini-charon'})" % WT); pg.wait_for_timeout(2500)
            pg.evaluate("() => { LEC.i = 25; montrerPage(); }"); pg.wait_for_timeout(1200)
            wt = pg.evaluate("() => ({cam: $('lecImg').classList.contains('cam'), fondu: $('lecImg').classList.contains('fondu'), f: CAM.data.format})")
            check("webtoon : camera + fondu entre pages", wt["cam"] and wt["fondu"] and wt["f"] == "webtoon", wt)
            pg.evaluate("() => $('lecFermer').click()")
            # --- 5. profil de la serie
            pg.evaluate("() => { LIB_SERIE = 'zz-essai-cases'; }")
            pg.evaluate("() => suiviCharger()"); pg.wait_for_timeout(2500)
            check("profil de la serie : selecteur camera = case par case", pg.evaluate("() => $('profCam').value") == "cases")
            check("aucune erreur JS", not errs, errs[:3])
            c.close()
        b.close()
finally:
    if avant is None:
        if os.path.isfile(SUIVI):
            os.remove(SUIVI)
    else:
        open(SUIVI, "w", encoding="utf-8").write(avant)
print("\n%d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
