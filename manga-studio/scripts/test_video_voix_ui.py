# -*- coding: utf-8 -*-
"""Banc UI v1.95.1 : video -- choix de la VOIX (plusieurs narrations) + « Precedemment... » en tete (case 📜).
1. Claymore ch.1 (plusieurs narrations avec voix) : menu « Voix de la video », defaut = la voix de la video existante ;
   un autre choix est MEMORISE et c'est lui qui part dans la demande (requete interceptee : rien n'est fabrique).
2. One Punch-Man ch.301 (une seule voix) : pas de menu. VRAIE video demandee avec 📜 par l'API de l'app ->
   fabriquee par la file, reglage precedemment garde, a jour, plus longue que sans (le resume est en tete).
Usage : python test_video_voix_ui.py [port]
"""
import json, os, sys, time, urllib.request
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


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w in (1280, 360):
        print("=== %d px" % w)
        c = b.new_context(viewport={"width": w, "height": 900}, is_mobile=w < 500, has_touch=w < 500)
        pg = c.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        envoye = []

        def intercepte(route):
            envoye.append(json.loads(route.request.post_data or "{}"))
            route.fulfill(status=200, content_type="application/json", body='{"ajoutees": [], "refusees": []}')
        pg.goto("http://127.0.0.1:%d/manga/#k=" % PORT + KEY); pg.wait_for_timeout(2500)
        pg.evaluate("() => { try { localStorage.removeItem('manga_vid_voix'); } catch {} }")
        pg.reload(); pg.wait_for_timeout(2500)
        pg.click('nav button[data-tab="tChap"]'); pg.wait_for_timeout(1200)
        i = pg.evaluate("() => CHAPS.findIndex(c => c.dir === 'claymore/ch_1')")
        pg.evaluate("(i) => openChap(i)", i); pg.wait_for_timeout(3500)
        n = pg.evaluate("() => document.querySelectorAll('#chapVid [data-vid-voix] option').length")
        check("Claymore ch.1 : menu Voix de la vidéo (plusieurs voix)", n >= 2, n)
        defaut = pg.evaluate("() => { const s = document.querySelector('#chapVid [data-vid-voix]'); return s && s.value; }")
        vtag = pg.evaluate("() => { const c = VIDS.chapitres.find(x => x.d === 'claymore/ch_1'); return c.videos[0] && c.videos[0].tag; }")
        check("défaut = la voix de la vidéo existante", defaut == vtag, (defaut, vtag))
        autre = pg.evaluate("() => [...document.querySelectorAll('#chapVid [data-vid-voix] option')].map(o => o.value).find(v => v !== '%s')" % defaut)
        pg.select_option("#chapVid [data-vid-voix]", autre); pg.wait_for_timeout(600)
        check("choix mémorisé", json.loads(pg.evaluate("() => localStorage.getItem('manga_vid_voix')") or "{}").get("claymore/ch_1") == autre)
        check("le menu garde le choix après rafraîchissement", pg.evaluate("() => document.querySelector('#chapVid [data-vid-voix]').value") == autre)
        pg.route("**/manga/video", intercepte)
        pg.route("**/manga/video_suppr", lambda r: r.fulfill(status=200, content_type="application/json", body='{"ok": true}'))
        pg.evaluate("() => vidDemander([VIDS.chapitres.find(x => x.d === 'claymore/ch_1')], false)"); pg.wait_for_timeout(800)
        ent = (envoye[-1].get("entrees") or [{}])[0] if envoye else {}
        check("la demande envoie la voix choisie", ent.get("tag") == autre, ent)
        check("la demande porte le réglage 📜", "precedemment" in (envoye[-1].get("reglages") or {}) if envoye else False)
        pg.unroute("**/manga/video"); pg.unroute("**/manga/video_suppr")
        pg.evaluate("() => { try { localStorage.removeItem('manga_vid_voix'); } catch {} }")
        i = pg.evaluate("() => CHAPS.findIndex(c => c.dir === 'one-punch-man/ch_301')")
        pg.evaluate("(i) => openChap(i)", i); pg.wait_for_timeout(3000)
        check("OPM ch.301 (une voix) : pas de menu", pg.evaluate("() => !document.querySelector('#chapVid [data-vid-voix]')"))
        dep = pg.evaluate("() => document.documentElement.scrollWidth - innerWidth")
        check("aucun débordement", dep <= 0, dep)
        check("0 erreur JS", not errs, errs[:2])
        c.close()
    b.close()

# --- vraie video avec 📜, par la file
d = "one-punch-man/ch_301"
ch = [x for x in api("/manga/videos?serie=one-punch-man")["chapitres"] if x["d"] == d][0]
for v in ch["videos"]:
    api("/manga/video_suppr", {"d": d, "tag": v["tag"]})
reg = {"vitesse": 1.15, "sous": True, "karaoke": True, "musique": False, "volume": 25, "pages": "", "precedemment": True}
r = api("/manga/video", {"entrees": [{"d": d}], "reglages": reg})
check("demande acceptée", len(r.get("ajoutees") or []) == 1, r)
t0 = time.time(); v = None
while time.time() - t0 < 600:
    time.sleep(10)
    ch = [x for x in api("/manga/videos?serie=one-punch-man")["chapitres"] if x["d"] == d][0]
    if ch["videos"]:
        v = ch["videos"][0]; break
    if any(f.get("etat") == "echec" for f in ch["file"]):
        break
check("vidéo fabriquée par la file", v is not None, ch.get("file"))
if v:
    check("réglage 📜 gardé avec la vidéo", (v.get("reglages") or {}).get("precedemment") is True, v.get("reglages"))
    check("à jour (aucune raison)", not v["raisons"], v["raisons"])
    check("durée = résumé (~21 s) + chapitre", v["duree_s"] > 280, v["duree_s"])
    print("  fabriquee en %.0f s" % (time.time() - t0))
    from urllib.parse import unquote
    req = urllib.request.Request("http://127.0.0.1:%d/manga/video_file?p=%s&dl=1" % (PORT, urllib.request.quote(v["fichier"])),
                                 headers={"Authorization": "Bearer " + KEY, "Range": "bytes=0-9"})
    with urllib.request.urlopen(req, timeout=60) as rr:
        cd = rr.headers.get("Content-Disposition") or ""
    nom = unquote(cd.split("filename*=UTF-8''")[-1]) if "filename*=" in cd else ""
    print("  nom telecharge : " + nom)
    check("nom téléchargé : série, ch301, voix, réglages, 📜", nom.startswith("One Punch-Man - ch301 - Fenrir - VO - karaoké - sans musique - précédemment - 1,15x - ")
          and nom.endswith(".mp4"), nom)
    check("nom ASCII de secours présent", 'filename="One Punch-Man - ch301 - Fenrir' in cd, cd[:90])
print("\n%d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
