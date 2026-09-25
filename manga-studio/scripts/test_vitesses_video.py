# -*- coding: utf-8 -*-
"""Banc v2.41.0 : vitesses SEPAREES en ligne / sur le PC pour les VIDEOS (Quang 25/09 09h20). APP REELLE, PC 1280 px.

AUCUNE video n'est fabriquee : POST /manga/video est INTERCEPTE (reponse simulee) ; aucun reglage n'est enregistre
(POST /manga/suivi fait echouer le banc). Les memoires de vitesse du lecteur sont sauvees puis restaurees.
1. demande groupee : un chapitre a voix EN LIGNE part a la vitesse ☁, un chapitre a voix LOCALE (« …-local ») a la 🖥 ;
2. « video perimee ? » compare a la vitesse de SA voix ; 3. le panneau affiche les deux vitesses ;
4. le profil montre « vitesse ☁ » ET « 🖥 », et sa ligne Video les resume.
Usage : python test_vitesses_video.py [port] [serie]
"""
import json, os, sys
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = sys.argv[1] if len(sys.argv) > 1 else "8190"
SERIE = sys.argv[2] if len(sys.argv) > 2 else "claymore"
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    pg = b.new_page(viewport={"width": 1280, "height": 900}); errs, video, ecrit = [], [], []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("request", lambda r: ecrit.append(r.url) if r.method == "POST" and "/manga/suivi" in r.url else None)
    def route(rt):
        corps = json.loads(rt.request.post_data or "{}"); video.append(corps)
        rt.fulfill(status=200, content_type="application/json",
                   body=json.dumps({"ok": True, "ajoutees": [{"d": e["d"], "tag": e["tag"], "id": "banc"} for e in corps.get("entrees", [])], "refusees": []}))
    pg.route("**/manga/video", route)
    pg.goto("http://127.0.0.1:%s/manga#k=%s" % (PORT, KEY)); pg.wait_for_timeout(2500)
    av = pg.evaluate("() => ['manga_onglet','manga_serie','manga_vit_cloud','manga_vit_local'].map(k => localStorage.getItem(k))")
    pg.evaluate("s => { localStorage.setItem('manga_onglet','tChap'); localStorage.setItem('manga_serie', s);"
                " localStorage.setItem('manga_vit_cloud','1.15'); localStorage.setItem('manga_vit_local','1'); }", SERIE)
    pg.reload(); pg.wait_for_timeout(4000)
    check("version = VERSION du code", pg.inner_text("#verBadge").strip() == "v" + pg.evaluate("() => VERSION"))
    # 1. demande groupee (chapitres fictifs : aucun fichier touche, la route est simulee)
    pg.evaluate("""async () => { const sv = VIDS; VIDS = { serie: 'banc', chapitres: [] };
        try { await vidDemander([{ d: 'banc/ch_1', narrations: [{ tag: 'gemini-leda' }], videos: [] },
                                 { d: 'banc/ch_2', narrations: [{ tag: 'gemini-leda-ton10-local' }], videos: [] }], false); }
        catch (e) {} VIDS = sv; }""")
    pg.wait_for_timeout(500)
    par = {e["tag"]: c["reglages"]["vitesse"] for c in video for e in c["entrees"]}
    check("2 demandes, une par type de voix", len(video) == 2, [[e["tag"] for e in c["entrees"]] for c in video])
    check("voix EN LIGNE → vitesse ☁ (1,15)", par.get("gemini-leda") == 1.15, par)
    check("voix LOCALE → vitesse 🖥 (1)", par.get("gemini-leda-ton10-local") == 1, par)
    check("la vidéo ne reçoit pas de champ en trop", all("vitesse_local" not in c["reglages"] for c in video))
    # 2. perimee ? -- comparee a la vitesse de SA voix
    d1 = pg.evaluate("() => vidReglagesDiff({ tag: 'x-local', reglages: Object.assign(reglagesLecteur(), { vitesse: 1 }) })")
    d2 = pg.evaluate("() => vidReglagesDiff({ tag: 'x-local', reglages: Object.assign(reglagesLecteur(), { vitesse: 1.15 }) })")
    check("vidéo locale à 1× : pas « périmée » pour la vitesse", not any("vitesse" in x for x in d1), d1)
    check("vidéo locale à 1,15× : « périmée » (vitesse)", any("vitesse" in x for x in d2), d2)
    # 3. panneau
    pg.click("#btnVideos"); pg.wait_for_timeout(2500)
    reg = pg.inner_text("#vidReg")
    check("panneau Vidéos : les deux vitesses affichées", "☁ 1,15×" in reg and "🖥 1×" in reg, reg)
    pg.click("#vidFermer")
    # 4. profil
    pg.click("#btnSuivi"); pg.wait_for_timeout(2500)
    pg.evaluate("() => { document.querySelector('#suiviBox details.bloc-vid').open = true; }")
    check("profil : « vitesse ☁ » et « 🖥 » présents", pg.is_visible("#profVit") and pg.is_visible("#profVitLoc"))
    lv = pg.inner_text('#suiviBox [data-v="vid"]')
    check("profil : la ligne Vidéo résume ☁ et 🖥", ("☁" in lv and "🖥" in lv) or lv == "pas de vidéo", lv)
    # 5. v2.42.0 : les deux vitesses dans le bloc Narration d'un chapitre, a 1280 puis 360 px
    pg.click("#suiviFermer")
    for w in (1280, 360):
        pg.set_viewport_size({"width": w, "height": 900 if w > 400 else 780})
        pg.click("#chapList [data-chap] >> nth=0"); pg.wait_for_selector("#chapDetail:not([hidden])"); pg.wait_for_timeout(2500)
        vis = pg.evaluate("() => ['narrVitCloud','narrVitLocal'].map(i => $(i).checkVisibility() && $(i).getBoundingClientRect().width > 0)")
        check("%d px : ☁ et 🖥 visibles dans le bloc Narration" % w, all(vis), vis)
        vals = pg.evaluate("() => [$('narrVitCloud').value, $('narrVitLocal').value]")
        check("%d px : valeurs = mémoires du lecteur (1.15 / 1)" % w, vals == ["1.15", "1"], vals)
        act = pg.evaluate("() => [MODE, $('narrVitCloudL').classList.contains('actif'), $('narrVitLocalL').classList.contains('actif')]")
        check("%d px : la vitesse du mode actuel est mise en évidence" % w, act[1] == (act[0] != "pc") and act[2] == (act[0] == "pc"), act)
        r = pg.eval_on_selector("#narrVitLocal", "e => e.closest('.narr-vit-z').getBoundingClientRect().right")
        check("%d px : le champ tient dans l'écran" % w, r <= w, r)
        pg.click("#btnChapClose"); pg.wait_for_timeout(300)
    pg.set_viewport_size({"width": 1280, "height": 900})
    pg.click("#chapList [data-chap] >> nth=0"); pg.wait_for_timeout(2500)
    pg.select_option("#narrVitLocal", "1.1"); pg.wait_for_timeout(300)
    check("changer 🖥 ici = mémoire du lecteur et des vidéos", pg.evaluate("() => localStorage.getItem('manga_vit_local')") == "1.1"
          and pg.evaluate("() => vitDe('local')") == 1.1)
    dbd = pg.evaluate("() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
    check("aucun débordement horizontal", dbd <= 0, dbd)
    check("aucun réglage enregistré", not ecrit, ecrit[:2])
    check("aucune erreur JS", not errs, errs[:2])
    pg.evaluate("a => { ['manga_onglet','manga_serie','manga_vit_cloud','manga_vit_local'].forEach((k, i) =>"
                " a[i] == null ? localStorage.removeItem(k) : localStorage.setItem(k, a[i])); }", av)
    b.close()
print("\nVERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
