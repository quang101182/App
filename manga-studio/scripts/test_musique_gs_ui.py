# -*- coding: utf-8 -*-
"""Banc UI v1.87.0 sur l'APP REELLE : « Prendre dans Generate Studio » (serie claymore).
Liste (8 plus recentes / tout + recherche), badges voix mesures, ecoute, prise d'un morceau INSTRUMENTAL
(copie en MP3 dans la serie), avertissement sur un morceau AVEC voix. Remet la serie comme avant :
le morceau pris par le banc part a la corbeille, puis il est retire de la corbeille, et le choix d'avant est restaure.
Usage : python test_musique_gs_ui.py [port]
"""
import json, os, shutil, sys, urllib.request
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
SRC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sources"))
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


def api(path, body=None):
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (PORT, path), data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


avant = api("/manga/musiques?serie=claymore")
noms_avant = {x["nom"] for x in avant["items"]}
corb = os.path.join(SRC, "_corbeille")
corb_avant = set(os.listdir(corb)) if os.path.isdir(corb) else set()
pris = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True, args=["--autoplay-policy=no-user-gesture-required"])
        for w, h in ((1280, 900), (360, 780)):
            print("=== %d px" % w)
            c = b.new_context(viewport={"width": w, "height": h}, has_touch=(w < 400), is_mobile=(w < 400))
            pg = c.new_page()
            errs, dialogues = [], []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.on("dialog", lambda d: (dialogues.append(d.message), d.dismiss()))
            pg.goto("http://127.0.0.1:%d/manga#k=" % PORT + KEY); pg.wait_for_timeout(3000)
            check("version >= 1.87.0", pg.inner_text("#verBadge") >= "v1.87.0", pg.inner_text("#verBadge"))
            pg.click('nav button[data-tab="tChap"]'); pg.wait_for_timeout(1500)
            i = pg.evaluate("() => CHAPS.findIndex(c => c.dir === 'claymore/ch_1')")
            pg.evaluate("(i) => openChap(i)", i); pg.wait_for_timeout(3000)
            pg.click("#musGs"); pg.wait_for_timeout(4000)
            n8 = pg.locator("#gsListe .gs-it").count()
            tot = pg.evaluate("() => GS.tous.length")
            check("par defaut : les 8 plus recentes", n8 == 8 and tot > 8, (n8, tot))
            dates = pg.evaluate("() => GS.tous.slice(0, 8).map(x => x.date)")
            check("triees de la plus recente a la plus ancienne", dates == sorted(dates, reverse=True))
            check("badges voix / instrumental affiches", pg.locator("#gsListe .gs-badge").count() >= 1)
            pg.click("#gsTout"); pg.wait_for_timeout(5000)
            check("« Tout voir » : toute la playlist", pg.locator("#gsListe .gs-it").count() == tot, tot)
            check("champ de recherche visible en mode tout", pg.is_visible("#gsRech"))
            pg.fill("#gsRech", "zombie"); pg.wait_for_timeout(800)
            txt = pg.inner_text("#gsListe").lower()
            nz = pg.locator("#gsListe .gs-it").count()
            check("recherche « zombie » : ne garde que ces morceaux", 1 <= nz < tot and "zombie" in txt, nz)
            pg.fill("#gsRech", ""); pg.wait_for_timeout(500)
            pg.click("#gsTout"); pg.wait_for_timeout(800)
            check("retour aux 8 plus recentes", pg.locator("#gsListe .gs-it").count() == 8)
            # ecoute
            pg.click("#gsListe [data-gs-ecoute] >> nth=0"); pg.wait_for_timeout(4000)
            check("▶ ecoute le morceau (MP3 servi)", pg.evaluate("() => !MUS_APERCU.paused && MUS_APERCU.currentTime > 0.3"),
                  pg.evaluate("() => [MUS_APERCU.paused, MUS_APERCU.currentTime, MUS_APERCU.error && MUS_APERCU.error.code]"))
            pg.evaluate("() => MUS_APERCU.pause()")
            # morceau AVEC voix -> avertissement, refuse -> rien n'est copie
            cv = pg.evaluate("() => { const it = GS.tous.slice(0, 8).find(x => ((GS.meta[x.chemin] || {}).analyse || {}).voix === true); return it ? it.chemin : null; }")
            if cv:
                n0 = pg.evaluate("() => MUS.items.length")
                pg.click('#gsListe [data-gs-prendre="%s"]' % cv); pg.wait_for_timeout(1500)
                check("morceau AVEC voix -> avertissement, refuse -> rien copie",
                      dialogues and "VOIX" in dialogues[-1] and pg.evaluate("() => MUS.items.length") == n0, dialogues[-1:] )
            else:
                print("  (aucun morceau avec voix parmi les 8 : avertissement non teste)")
            # prise d'un instrumental (une seule fois)
            if w > 400:
                ci = pg.evaluate("() => { const it = GS.tous.slice(0, 8).find(x => ((GS.meta[x.chemin] || {}).analyse || {}).voix === false); return it ? it.chemin : null; }")
                check("un instrumental mesure parmi les 8", bool(ci), ci)
                if ci:
                    pg.click('#gsListe [data-gs-prendre="%s"]' % ci); pg.wait_for_timeout(8000)
                    apres = api("/manga/musiques?serie=claymore")
                    neufs = [x for x in apres["items"] if x["nom"] not in noms_avant]
                    pris.extend(x["nom"] for x in neufs)
                    check("« Prendre » : le morceau arrive dans la serie, en MP3", len(neufs) == 1 and neufs[0]["fichier"].endswith(".mp3"),
                          [(x["nom"], x["taille"]) for x in neufs])
                    check("il apparait dans le menu de la serie", pg.evaluate("(n) => [...$('musChoix').options].some(o => o.value === n)", neufs[0]["nom"] if neufs else ""))
                    check("bouton passe a « ✓ prise »", "prise" in pg.inner_text('#gsListe [data-gs-prendre="%s"]' % ci))
            dep = pg.evaluate("() => document.documentElement.scrollWidth - innerWidth")
            check("pas de debordement horizontal", dep <= 0, dep)
            pg.screenshot(path=os.path.join(os.environ.get("TEMP", "."), "gs_ui_%d.png" % w))
            check("aucune erreur JS", not errs, errs[:2])
            c.close()
        b.close()
finally:
    for nom in pris:                                  # remettre la serie comme avant
        api("/manga/musique_suppr", {"serie": "claymore", "nom": nom})
    if avant.get("choix"):
        api("/manga/musique_choix", {"serie": "claymore", "nom": avant["choix"]})
    for x in (set(os.listdir(corb)) - corb_avant) if os.path.isdir(corb) else ():
        if "claymore__musique__" in x:
            os.remove(os.path.join(corb, x))
    fin = api("/manga/musiques?serie=claymore")
    check("serie remise comme avant", {x["nom"] for x in fin["items"]} == noms_avant and fin["choix"] == avant["choix"], fin["choix"])
print("\n=== VERDICT : %d/%d" % (len(OK), len(OK) + len(KO)) + ("" if not KO else "  ECHECS : " + ", ".join(KO)))
sys.exit(1 if KO else 0)
