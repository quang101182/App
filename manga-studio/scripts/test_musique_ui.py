# -*- coding: utf-8 -*-
"""Banc UI v1.85.0 sur l'APP REELLE : musique de fond sous la narration (Claymore ch.1, narration banc-k3-charon).
Suppose que la serie claymore a au moins un morceau (importe par l'app). Mesure les VOLUMES reels des deux
lecteurs de musique : niveau sous la voix, remontee entre les pages, pause, interrupteur, volume, boucle en
fondu enchaine, fermeture. PC 1280 px puis telephone 360 px. Remet le volume / l'interrupteur par defaut.
Usage : python test_musique_ui.py
"""
import json, os, sys, urllib.request
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
OK, KO = [], []


def api(path, body=None):
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (PORT, path), data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


# v1.90 : on joue 2 morceaux (selection PROPRE au chapitre, le temps du banc), puis on remet tout comme avant
AVANT = api("/manga/musiques?serie=claymore&d=claymore/ch_1")
DEUX = [x["nom"] for x in AVANT["items"]][:2]
api("/manga/musique_selection", {"serie": "claymore", "d": "claymore/ch_1", "mode": "propre", "noms": DEUX})


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


ETAT = "() => ({g: +MP.g.toFixed(3), cur: MP.cur, v: MP.els.map(x => +x.volume.toFixed(3)), " \
       "p: MP.els.map(x => x.paused), t: MP.els.map(x => +x.currentTime.toFixed(1)), " \
       "voix: !$('lecAudio').paused, d: +(MP.els[0].duration || 0).toFixed(1)})"

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True, args=["--autoplay-policy=no-user-gesture-required"])
    for w, h in ((1280, 900), (360, 780)):
        print("=== %d px" % w)
        c = b.new_context(viewport={"width": w, "height": h}, has_touch=(w < 400), is_mobile=(w < 400))
        pg = c.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("dialog", lambda d: d.accept())
        pg.goto("http://127.0.0.1:%d/manga#k=" % PORT + KEY); pg.wait_for_timeout(3000)
        pg.evaluate("() => { try { localStorage.removeItem('manga_mus_on'); localStorage.removeItem('manga_mus_vol'); } catch {} }")
        pg.reload(); pg.wait_for_timeout(3000)
        check("version >= 1.90.0", pg.inner_text("#verBadge") >= "v1.90.0", pg.inner_text("#verBadge"))
        pg.click('nav button[data-tab="tChap"]'); pg.wait_for_timeout(1500)
        i = pg.evaluate("() => CHAPS.findIndex(c => c.dir === 'claymore/ch_1')")
        pg.evaluate("(i) => openChap(i)", i); pg.wait_for_timeout(3000)
        n = pg.locator("#musListe .mus-it").count()
        check("liste des morceaux de la serie (colonnes fixes)", n >= 2, n)
        xs = pg.evaluate("() => [...document.querySelectorAll('#musListe .mus-it [data-mus-suppr]')].map(b => Math.round(b.getBoundingClientRect().x))")
        check("🗑 aligne sur toutes les lignes", len(set(xs)) == 1, xs)
        check("« propre au chapitre » actif, 2 coches", pg.evaluate("() => $('musMode').querySelector('.on').dataset.mode") == "propre"
              and pg.locator("#musListe input:checked").count() == 2)
        pg.click("#musListe [data-mus-ecoute] >> nth=0"); pg.wait_for_timeout(1500)
        check("▶ ecoute le morceau seul", pg.inner_text("#musListe [data-mus-ecoute] >> nth=0") == "■")
        pg.click("#musListe [data-mus-ecoute] >> nth=0"); pg.wait_for_timeout(300)
        # lecteur
        k = pg.evaluate("() => NARRS.findIndex(n => n.tag === 'banc-k3-charon')")
        pg.evaluate("(k) => ouvrirLecteur([NARRS[k].tag])", k)
        pg.wait_for_timeout(4500)
        e = pg.evaluate(ETAT)
        check("la musique joue sous la voix", not e["p"][e["cur"]] and e["voix"], e)
        check("sous la voix : gain ~0,045 (-27 dB)", 0.03 <= e["g"] <= 0.06, e["g"])
        check("case 🎵 et volume visibles, 25 % par defaut", pg.is_visible("#lecMusOn") and pg.evaluate("() => +$('lecMusVol').value") == 25)
        # la voix se tait (fin de page simulee par une pause de la voix seule) -> la musique remonte
        pg.evaluate("() => $('lecAudio').pause()"); pg.wait_for_timeout(2500)
        e = pg.evaluate(ETAT)
        check("voix muette -> la musique remonte vers 0,1", e["g"] >= 0.085, e["g"])
        pg.evaluate("() => $('lecAudio').play()"); pg.wait_for_timeout(800)
        e = pg.evaluate(ETAT)
        check("la voix reprend -> la musique rebaisse vite (< 1 s)", e["g"] <= 0.06, e["g"])
        # pause generale
        pg.click("#lecPlay"); pg.wait_for_timeout(1200)
        e = pg.evaluate(ETAT)
        check("pause -> la musique s'arrete aussi", all(e["p"]) and e["g"] <= 0.001, e)
        pg.click("#lecPlay"); pg.wait_for_timeout(1500)
        check("reprise -> la musique repart", not pg.evaluate(ETAT)["p"][pg.evaluate("() => MP.cur")])
        # interrupteur
        pg.click("#lecMusOn"); pg.wait_for_timeout(1200)
        e = pg.evaluate(ETAT)
        check("🎵 decoche -> silence", all(e["p"]), e)
        pg.click("#lecMusOn"); pg.wait_for_timeout(1500)
        check("🎵 recoche -> la musique repart", not all(pg.evaluate(ETAT)["p"]))
        # volume au maximum
        pg.evaluate("() => { $('lecMusVol').value = 100; $('lecMusVol').dispatchEvent(new Event('input')); }")
        pg.evaluate("() => $('lecAudio').pause()"); pg.wait_for_timeout(3000)
        e = pg.evaluate(ETAT)
        check("volume 100 % -> gain 0,4 hors voix", 0.37 <= e["g"] <= 0.4, e["g"])
        pg.evaluate("() => $('lecAudio').play()")
        # boucle : on saute a 4 s de la fin du morceau
        pg.evaluate("() => { const a = MP.els[MP.cur]; a.currentTime = a.duration - 4; }")
        cur0 = pg.evaluate("() => MP.cur")
        src0 = pg.evaluate("() => MP.els[MP.cur].src")
        pg.wait_for_timeout(2200)
        e = pg.evaluate(ETAT)
        check("fin du morceau -> les deux lecteurs se croisent", not e["p"][0] and not e["p"][1] and e["cur"] != cur0, e)
        pg.wait_for_timeout(3500)
        e = pg.evaluate(ETAT)
        check("apres le fondu : un AUTRE morceau joue depuis le debut, l'ancien s'est tu",
              e["p"][cur0] and not e["p"][e["cur"]] and e["t"][e["cur"]] < 8 and pg.evaluate("() => MP.els[MP.cur].src") != src0, e)
        # memorise par appareil
        check("volume memorise", pg.evaluate("() => localStorage.getItem('manga_mus_vol')") == "100")
        dep = pg.evaluate("() => document.documentElement.scrollWidth - innerWidth")
        bb = pg.locator("#lecMusVol").bounding_box()
        check("curseur de volume dans l'ecran", bb and bb["x"] >= 0 and bb["x"] + bb["width"] <= w and dep <= 0, (bb, dep))
        pg.screenshot(path=os.path.join(os.environ.get("TEMP", "."), "mus_ui_%d.png" % w))
        pg.click("#lecFermer"); pg.wait_for_timeout(600)
        e = pg.evaluate(ETAT)
        check("fermer le lecteur -> silence", all(e["p"]), e)
        pg.evaluate("() => { try { localStorage.removeItem('manga_mus_on'); localStorage.removeItem('manga_mus_vol'); } catch {} }")
        check("aucune erreur JS", not errs, errs[:2])
        c.close()
    b.close()
prop = AVANT.get("chapitre") or {"mode": "serie", "noms": []}
api("/manga/musique_selection", {"serie": "claymore", "d": "claymore/ch_1", "mode": prop["mode"], "noms": prop["noms"]})
fin = api("/manga/musiques?serie=claymore&d=claymore/ch_1")
check("Claymore remise comme avant", fin["chapitre"] == prop and fin["serie_sel"] == AVANT["serie_sel"], (fin["chapitre"], fin["serie_sel"]))
print("\n=== VERDICT : %d/%d" % (len(OK), len(OK) + len(KO)) + ("" if not KO else "  ECHECS : " + ", ".join(KO)))
sys.exit(1 if KO else 0)
