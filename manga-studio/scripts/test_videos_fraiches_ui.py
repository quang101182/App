# -*- coding: utf-8 -*-
"""Banc v2.5.2 : l'etat des videos se rafraichit SANS le bouton ↻ (Quang 23/09 09h00).
Serie de TEST zz-essai-rafr (copie de One Punch-Man ch.300 + ch.301, chacun avec sa video).
1. une FAUSSE video (1 s) posee sur ch.300 ; supprimee AILLEURS ; on ouvre le 301 puis le 300 -> « pas de video », sans ↻ ;
   on ouvre le 301 puis on revient au 300 -> le bloc 🎬 doit dire « pas de video », sans ↻ ;
2. on reste sur le 300 : une demande faite ailleurs apparait, puis son annulation (jamais de rendu reel) ;
3. aucune erreur JS. Usage : python test_videos_fraiches_ui.py [port]
"""
import json, os, subprocess, sys, time, urllib.request
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
S = "zz-essai-rafr"
SRC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sources"))
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


def api(path, body=None):
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (PORT, path), data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    pg = b.new_page(viewport={"width": 1280, "height": 900}); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("http://127.0.0.1:%d/manga#k=%s" % (PORT, KEY)); pg.wait_for_timeout(2500)
    check("version 2.5.2", pg.inner_text("#verBadge") == "v2.5.2")
    pg.click('nav button[data-tab="tChap"]'); pg.wait_for_timeout(1000)
    pg.evaluate("() => ouvrirSerie('%s')" % S); pg.wait_for_timeout(2500)
    ouvrir = lambda ch: pg.evaluate("async () => { await openChap(CHAPS.findIndex(c => c.dir === '%s/%s')); }" % (S, ch))
    etat = lambda: pg.inner_text("#chapVid")
    tag = api("/manga/narrations?d=%s/ch_300" % S)["items"][0]["tag"]
    # une FAUSSE video posee a la main (1 s, noire) : pas de rendu, pas de temps GPU pris a la file de Quang
    vd = os.path.join(SRC, S, "ch_300", "video"); os.makedirs(vd, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=black:s=108x192:d=1", os.path.join(vd, tag + ".mp4")], check=True)
    json.dump({"tag": tag, "created_at": "2026-09-23T09:00:00", "reglages": {"vitesse": 1, "sous": True, "camera": "cases"}, "empreinte": {},
               "duree_s": 1, "taille": 1}, open(os.path.join(vd, tag + ".json"), "w", encoding="utf-8"))
    ouvrir("ch_300"); pg.wait_for_timeout(2500)
    check("ch.300 ouvert : sa video est la", "à jour" in etat() or "à refaire" in etat(), etat()[-70:])
    # 1. suppression AILLEURS (autre appareil), puis on change de chapitre et on revient
    print("  (suppression AILLEURS :", api("/manga/video_suppr", {"d": S + "/ch_300", "tag": tag}).get("ok"), ")")
    ouvrir("ch_301"); pg.wait_for_timeout(1500); ouvrir("ch_300"); pg.wait_for_timeout(2500)
    check("retour sur ch.300 SANS ↻ : « pas de vidéo »", "pas de vidéo" in etat(), etat()[-70:])
    badge = pg.evaluate("() => { const b = [...document.querySelectorAll('#chapList [data-chap]')].find(x => CHAPS[+x.dataset.chap].dir.endsWith('ch_300'));"
                        " const s = b && b.querySelector('.vid-badge'); return s ? s.textContent : ''; }")
    check("... et la carte du chapitre n'a plus le badge 🎬", "🎬" not in badge, badge)
    # 2. on RESTE sur le chapitre : une demande faite ailleurs apparait, puis son annulation, sans ↻
    r = api("/manga/video", {"entrees": [{"d": S + "/ch_300", "tag": tag}], "reglages": {"vitesse": 1, "sous": True, "camera": "cases"}})
    ide = r["ajoutees"][0]["id"]
    try:
        t0 = time.time(); vu = ""
        while time.time() - t0 < 30:
            pg.wait_for_timeout(2000); vu = etat()
            if "en attente" in vu or "fabrication" in vu:
                break
        check("demande faite ailleurs -> visible dans le chapitre ouvert, sans ↻ (%.0f s)" % (time.time() - t0),
              "en attente" in vu or "fabrication" in vu, vu[-60:])
    finally:
        api("/manga/video_annule", {"id": ide})                  # jamais de rendu reel : la file de Quang passe avant
    t0 = time.time()
    while time.time() - t0 < 40 and "pas de vidéo" not in etat():
        pg.wait_for_timeout(2000)
    check("... son annulation ailleurs aussi, sans ↻ (%.0f s)" % (time.time() - t0), "pas de vidéo" in etat(), etat()[-60:])
    check("aucune erreur JS", not errs, errs[:2])
    b.close()
print("\n%d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
