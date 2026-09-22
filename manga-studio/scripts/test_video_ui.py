# -*- coding: utf-8 -*-
"""Banc UI v1.93.0 : VIDEOS (Claymore ch.1 = une video faite ; One Punch-Man = 2 chapitres, sans video).
Panneau serie (etats, zones fixes, reglages affiches), ligne du chapitre, badge, ▶ lecture reelle, ⬇ telechargement
(nom + taille), Range, « a refaire » : reglages du lecteur (client) ET selection de musique (proxy), ✕ d'une erreur.
Remet tout comme avant. PC 1280 px + 360 px. Usage : python test_video_ui.py [port]
"""
import json, os, sys, time, urllib.request
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
SRC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sources"))
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


def api(path, body=None, headers=None, brut=False):
    h = {"Authorization": "Bearer " + KEY, "Content-Type": "application/json"}; h.update(headers or {})
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (PORT, path), data=json.dumps(body).encode() if body is not None else None, headers=h)
    with urllib.request.urlopen(req, timeout=120) as r:
        return (r.status, r.headers, r.read(2000)) if brut else json.load(r)


MUS_AVANT = api("/manga/musiques?serie=claymore&d=claymore/ch_1")
VID = api("/manga/videos?serie=claymore")["chapitres"][0]["videos"]
assert VID, "il faut d'abord une video de claymore/ch_1"
FICHIER = VID[0]["fichier"]
FAUX = os.path.join(SRC, "_videos_file", "20260101-000000-9999.json")
try:
    # --- flux : Range, telechargement
    st, hd, corps = api("/manga/video_file?p=" + urllib.request.quote(FICHIER), headers={"Range": "bytes=0-999"}, brut=True)
    check("flux video : Range -> 206, 1000 octets, video/mp4", st == 206 and len(corps) == 1000 and hd["Content-Type"] == "video/mp4", (st, len(corps)))
    st, hd, _ = api("/manga/video_file?p=" + urllib.request.quote(FICHIER) + "&dl=1", headers={"Range": "bytes=0-9"}, brut=True)
    check("dl=1 -> « enregistrer sous » avec un nom .mp4", "attachment" in (hd.get("Content-Disposition") or "") and ".mp4" in hd.get("Content-Disposition"), hd.get("Content-Disposition"))
    # une demande en ECHEC factice (One Punch-Man ch.300) pour le bouton ✕
    os.makedirs(os.path.dirname(FAUX), exist_ok=True)
    json.dump({"id": "20260101-000000-9999", "d": "one-punch-man/ch_300", "tag": "x", "etat": "echec", "err": "banc", "t": 1}, open(FAUX, "w", encoding="utf-8"))
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True, args=["--autoplay-policy=no-user-gesture-required"])
        for w, h in ((1280, 1000), (360, 780)):
            print("=== %d px" % w)
            c = b.new_context(viewport={"width": w, "height": h}, is_mobile=w < 500, has_touch=w < 500, accept_downloads=True)
            pg = c.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.on("dialog", lambda d: d.accept())
            pg.goto("http://127.0.0.1:%d/manga#k=" % PORT + KEY); pg.wait_for_timeout(2500)
            pg.click('nav button[data-tab="tChap"]'); pg.wait_for_timeout(1500)
            check("version >= 1.93.0", pg.inner_text("#verBadge") >= "v1.93.0", pg.inner_text("#verBadge"))
            pg.evaluate("() => { const b = document.querySelector('#chapList [data-serie=\"claymore\"]'); if (b) b.click(); }"); pg.wait_for_timeout(2500)
            check("badge 🎬 ✅ sur la carte du chapitre", "🎬 ✅" in pg.inner_text("#chapList"), pg.inner_text("#chapList")[:80].replace("\n", " "))
            pg.click("#btnVideos"); pg.wait_for_timeout(2500)
            check("panneau Vidéos + réglages du lecteur affichés", pg.is_visible("#vidBox") and "1,15×" in pg.inner_text("#vidReg"), pg.inner_text("#vidReg"))
            check("ligne ch.1 : ✅ à jour", "✅ à jour" in pg.inner_text("#vidListe"), pg.inner_text("#vidListe")[:120].replace("\n", " "))
            # « a refaire » par les reglages du lecteur (cote client)
            # reglages du lecteur (propres a CET appareil) : une NOTE ℹ️, jamais 🟠 (le chapitre n'a pas change)
            pg.evaluate("() => { $('lecVit').value = '1'; vidRendre(); }"); pg.wait_for_timeout(300)
            txt = pg.inner_text("#vidListe")
            check("vitesse du lecteur differente -> reste ✅ + note ℹ️ (vitesse)", "✅ à jour" in txt and "ℹ️" in txt and "vitesse" in txt, txt[:160].replace(chr(10), " "))
            pg.evaluate("() => { $('lecVit').value = '1.15'; vidRendre(); }"); pg.wait_for_timeout(300)
            # « a refaire » par la musique (cote proxy)
            api("/manga/musique_selection", {"serie": "claymore", "d": "claymore/ch_1", "mode": "propre", "noms": [MUS_AVANT["items"][0]["nom"]]})
            pg.evaluate("() => vidCharger('claymore')"); pg.wait_for_timeout(1500)
            check("musique du chapitre changée -> 🟠 « sélection de musique »", "sélection de musique a changé" in pg.inner_text("#vidListe"))
            ch = MUS_AVANT.get("chapitre") or {"mode": "serie", "noms": []}
            api("/manga/musique_selection", {"serie": "claymore", "d": "claymore/ch_1", "mode": ch["mode"], "noms": ch["noms"]})
            pg.evaluate("() => vidCharger('claymore')"); pg.wait_for_timeout(1500)
            check("musique remise -> de nouveau ✅", "✅ à jour" in pg.inner_text("#vidListe"))
            # lecture reelle
            pg.click("#vidListe [data-vid-voir]"); pg.wait_for_timeout(3500)
            t = pg.evaluate("() => $('vidLecVideo').currentTime")
            dims = pg.evaluate("() => [$('vidLecVideo').videoWidth, $('vidLecVideo').videoHeight]")
            check("▶ la vidéo se lit (9:16, 1080x1920)", t > 1 and dims == [1080, 1920], (t, dims))
            pg.click("#vidLecFermer"); pg.wait_for_timeout(300)
            if w > 400:
                with pg.expect_download(timeout=120000) as dl:
                    pg.click("#vidListe [data-vid-dl]")
                d = dl.value
                chemin = d.path()
                check("⬇ téléchargement complet (.mp4, même taille)", d.suggested_filename.endswith(".mp4") and os.path.getsize(chemin) == VID[0]["taille"],
                      (d.suggested_filename, os.path.getsize(chemin), VID[0]["taille"]))
            # autre serie : 2 chapitres, alignement et erreur factice
            pg.click("#btnLibBack"); pg.wait_for_timeout(800)
            pg.evaluate("() => { const b = document.querySelector('#chapList [data-serie=\"one-punch-man\"]'); if (b) b.click(); }"); pg.wait_for_timeout(2500)
            if pg.is_hidden("#vidBox"):
                pg.click("#btnVideos")
            pg.wait_for_timeout(2500)
            txt = pg.inner_text("#vidListe")
            check("One Punch-Man : ❌ (erreur factice) + ⚪ pas de vidéo", "❌" in txt and "⚪ pas de vidéo" in txt, txt.replace("\n", " | ")[:200])
            xs = pg.evaluate("() => [...document.querySelectorAll('#vidListe .vid-it')].map(r => Math.round(r.children[5].getBoundingClientRect().x))")
            check("4e case (🗑 / vide) au même x sur toutes les lignes", len(set(xs)) == 1, xs)
            pg.click("#vidListe [data-vid-annule]"); pg.wait_for_timeout(1500)
            check("✕ retire l'erreur de la file", "❌" not in pg.inner_text("#vidListe") and not os.path.isfile(FAUX))
            noms = pg.evaluate("() => [...document.querySelectorAll('#vidListe .vi-nom')].map(e => [e.textContent, e.scrollWidth <= e.clientWidth + 1])")
            check("chaque ligne montre « Chapitre N » en entier", all(x[0].startswith("Chapitre ") and x[1] for x in noms), noms)
            dep = pg.evaluate("() => document.documentElement.scrollWidth - innerWidth")
            check("pas de débordement horizontal", dep <= 0, dep)
            pg.screenshot(path=os.path.join(os.environ.get("TEMP", "."), "vid_ui_%d.png" % w))
            check("aucune erreur JS", not errs, errs[:2])
            c.close()
            if w > 400:   # l'erreur factice a ete retiree : on la remet pour le passage telephone
                json.dump({"id": "20260101-000000-9999", "d": "one-punch-man/ch_300", "tag": "x", "etat": "echec", "err": "banc", "t": 1}, open(FAUX, "w", encoding="utf-8"))
        b.close()
finally:
    if os.path.isfile(FAUX):
        os.remove(FAUX)
    ch = MUS_AVANT.get("chapitre") or {"mode": "serie", "noms": []}
    api("/manga/musique_selection", {"serie": "claymore", "d": "claymore/ch_1", "mode": ch["mode"], "noms": ch["noms"]})
print("\n=== VERDICT : %d/%d" % (len(OK), len(OK) + len(KO)) + ("" if not KO else "  ECHECS : " + ", ".join(KO)))
sys.exit(1 if KO else 0)
