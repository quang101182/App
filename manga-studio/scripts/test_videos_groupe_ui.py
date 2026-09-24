# -*- coding: utf-8 -*-
"""Banc UI v1.97.0 : telecharger un GROUPE de videos (One Punch-Man ch.300 + ch.301 ; fabrique la video du ch.300 si absente).
Selection : TOUT coche par defaut, gardee apres un rafraichissement du panneau, « Rien », « Tout », plage ; compte + poids ;
« En une archive .zip » = UN fichier, nom lisible, archive VALIDE contenant les bonnes videos (noms lisibles) ;
« Une par une » = les fichiers MP4 avec leur nom ; 0 debordement a 360 px. Usage : python test_videos_groupe_ui.py [port]
"""
import json, os, sys, tempfile, time, urllib.request, zipfile
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


def api(path, body=None):
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (PORT, path), data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def chap(d):
    return [x for x in api("/manga/videos?serie=one-punch-man")["chapitres"] if x["d"] == d][0]


if not chap("one-punch-man/ch_300")["videos"]:
    print("fabrication de la video du ch.300 ...")
    api("/manga/video", {"entrees": [{"d": "one-punch-man/ch_300"}], "reglages": {"vitesse": 1.15, "sous": True, "karaoke": True,
                                                                                    "musique": False, "volume": 25, "pages": "", "precedemment": True}})
    t0 = time.time()
    while time.time() - t0 < 600 and not chap("one-punch-man/ch_300")["videos"]:
        time.sleep(10)
check("2 vidéos prêtes dans la série", all(chap("one-punch-man/ch_%d" % n)["videos"] for n in (300, 301)))
tmp = tempfile.mkdtemp(prefix="banc_zip_")
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w, h in ((1280, 1000), (360, 780)):
        print("=== %d px" % w)
        c = b.new_context(viewport={"width": w, "height": h}, is_mobile=w < 500, has_touch=w < 500, accept_downloads=True)
        pg = c.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("dialog", lambda dl: dl.accept())
        pg.goto("http://127.0.0.1:%d/manga/#k=" % PORT + KEY); pg.wait_for_timeout(2500)
        pg.click('nav button[data-tab="tChap"]'); pg.wait_for_timeout(1200)
        pg.evaluate("() => { const b = document.querySelector('#chapList [data-serie=\"one-punch-man\"]'); if (b) b.click(); }"); pg.wait_for_timeout(2000)
        pg.click("#btnVideos"); pg.wait_for_timeout(2500)
        coches = lambda: pg.evaluate("() => [...document.querySelectorAll('#vidListe [data-vid-coche]')].map(x => x.checked)")
        check("tout coché par défaut", coches() and all(coches()), coches())
        check("compte : 2 cochés, 2 prêtes, poids", pg.inner_text("#vidCompte").startswith("2 coché(s) · 2 vidéo(s) prête(s) ·"), pg.inner_text("#vidCompte"))
        pg.evaluate("s => { const e = document.querySelector(s); if (!e) return; const d = e.closest('details'); if (d && !d.open) d.open = true; const m = e.closest('.menu-plus'); if (m && m.querySelector('.menu-pan').hidden) m.querySelector('.plus').click(); }", "#vidRien"); pg.click("#vidRien"); pg.wait_for_timeout(300)
        check("Rien : 0 coché, boutons de téléchargement inactifs", not any(coches()) and pg.is_disabled("#vidZip") and pg.is_disabled("#vidDl"))
        pg.evaluate("s => { const e = document.querySelector(s); if (!e) return; const d = e.closest('details'); if (d && !d.open) d.open = true; const m = e.closest('.menu-plus'); if (m && m.querySelector('.menu-pan').hidden) m.querySelector('.plus').click(); }", "#vidTout"); pg.click("#vidTout"); pg.wait_for_timeout(300)
        pg.evaluate("() => { const m = document.querySelector('#vidDe').closest('.menu-plus'); if (m && m.querySelector('.menu-pan').hidden) m.querySelector('.plus').click(); }"); pg.fill("#vidDe", "301"); pg.fill("#vidA", "301"); pg.evaluate("s => { const e = document.querySelector(s); if (!e) return; const d = e.closest('details'); if (d && !d.open) d.open = true; const m = e.closest('.menu-plus'); if (m && m.querySelector('.menu-pan').hidden) m.querySelector('.plus').click(); }", "#vidPlage"); pg.click("#vidPlage"); pg.wait_for_timeout(300)
        check("plage 301 → 301 : seul le ch.301", coches() == [False, True], coches())
        pg.evaluate("() => vidCharger(VIDS.serie)"); pg.wait_for_timeout(1500)
        check("la sélection survit au rafraîchissement du panneau", coches() == [False, True], coches())
        pg.evaluate("s => { const e = document.querySelector(s); if (!e) return; const d = e.closest('details'); if (d && !d.open) d.open = true; const m = e.closest('.menu-plus'); if (m && m.querySelector('.menu-pan').hidden) m.querySelector('.plus').click(); }", "#vidTout"); pg.click("#vidTout"); pg.wait_for_timeout(300)
        dep = pg.evaluate("() => document.documentElement.scrollWidth - innerWidth")
        check("aucun débordement", dep <= 0, dep)
        # --- archive
        with pg.expect_download(timeout=120000) as dl:
            pg.click("#vidZip")
        d = dl.value; nom = d.suggested_filename
        f = os.path.join(tmp, "a%d.zip" % w); d.save_as(f)
        check("archive : UN fichier, nom lisible", nom.startswith("One Punch-Man - vidéos ch300 à ch301 (2) - ") and nom.endswith(".zip"), nom)
        z = zipfile.ZipFile(f); noms = [i.filename for i in z.infolist()]
        check("archive valide, 2 vidéos aux noms lisibles", z.testzip() is None and len(noms) == 2
              and noms[0].startswith("One Punch-Man - ch300 - ") and noms[1].startswith("One Punch-Man - ch301 - "), noms)
        check("vidéos stockées sans recompression (taille exacte)", sum(i.file_size for i in z.infolist()) ==
              sum(chap("one-punch-man/ch_%d" % n)["videos"][0]["taille"] for n in (300, 301)))
        z.close()
        # --- une par une
        if w == 1280:
            noms = []
            for _ in range(2):
                pass
            pg.evaluate("() => { const m = document.querySelector('#vidDe').closest('.menu-plus'); if (m && m.querySelector('.menu-pan').hidden) m.querySelector('.plus').click(); }"); pg.fill("#vidDe", "300"); pg.fill("#vidA", "300"); pg.evaluate("s => { const e = document.querySelector(s); if (!e) return; const d = e.closest('details'); if (d && !d.open) d.open = true; const m = e.closest('.menu-plus'); if (m && m.querySelector('.menu-pan').hidden) m.querySelector('.plus').click(); }", "#vidPlage"); pg.click("#vidPlage"); pg.wait_for_timeout(300)
            with pg.expect_download(timeout=60000) as dl:
                pg.evaluate("s => { const e = document.querySelector(s); if (!e) return; const d = e.closest('details'); if (d && !d.open) d.open = true; const m = e.closest('.menu-plus'); if (m && m.querySelector('.menu-pan').hidden) m.querySelector('.plus').click(); }", "#vidDl"); pg.click("#vidDl")
            check("une par une : le MP4 avec son nom lisible", dl.value.suggested_filename.startswith("One Punch-Man - ch300 - "), dl.value.suggested_filename)
            dl.value.cancel()
        check("0 erreur JS", not errs, errs[:3])
        c.close()
    b.close()
for n in os.listdir(tmp):
    os.remove(os.path.join(tmp, n))
os.rmdir(tmp)
print("\n%d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
