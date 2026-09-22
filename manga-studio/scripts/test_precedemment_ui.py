# -*- coding: utf-8 -*-
"""Banc UI v1.94.0 : « Precedemment... » + rattrapage (One Punch-Man ch.301, resume du ch.300 ; Claymore ch.1 = rien avant).
Panneau (etats, cache sans chapitre precedent), lecteur : ouverture en tete (image du ch. d'avant, son qui JOUE,
sous-titre, karaoke), puis la vraie page 1 ; case 📜 decochee et memorisee ; « Rattrapage puis ce chapitre » ;
ecoute a l'aveugle sans resume ; « a refaire » quand une source change (proxy) ; 0 debordement a 360 px.
Remet tout comme avant. Usage : python test_precedemment_ui.py [port]
"""
import json, os, shutil, sys
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
SRC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sources"))
OUV = os.path.join(SRC, "one-punch-man", "ch_301", "precedemment", "ouverture.json")
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


ETAT = """() => { const p = LEC.n && LEC.n.pages[LEC.i], a = document.getElementById('lecAudio');
  return { prec: p ? (p.prec || null) : null, page: p ? p.page : null, info: document.getElementById('lecInfo').textContent,
           img: document.getElementById('lecImg').src, aud: a.src || '', t: a.currentTime, paused: a.paused,
           sous: document.getElementById('lecSous').textContent, km: document.querySelectorAll('#lecSous .km').length,
           n: LEC.n.pages.length }; }"""

assert os.path.isfile(OUV), "il faut d'abord fabriquer l'ouverture de one-punch-man/ch_301"
sauve = OUV + ".banc"
shutil.copy(OUV, sauve)
try:
    # --- « a refaire » : une source qui change (cote proxy)
    import urllib.request

    def get(path):
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (PORT, path), headers={"Authorization": "Bearer " + KEY})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    j = get("/manga/precedemment?d=one-punch-man/ch_301")
    check("proxy : ouverture et rattrapage finis, a jour", all(j["modes"][m]["etat"] == "fini" and not j["modes"][m]["perime"]
                                                             for m in ("ouverture", "rattrapage")), j["modes"]["ouverture"].get("raisons"))
    d = json.load(open(OUV, encoding="utf-8")); d["sources"][0]["tag"] = "une-autre"
    json.dump(d, open(OUV, "w", encoding="utf-8"), ensure_ascii=False)
    j = get("/manga/precedemment?d=one-punch-man/ch_301")["modes"]["ouverture"]
    check("proxy : narration source refaite -> 🟠 + raison", j["perime"] and "refaite" in " ".join(j["raisons"]), j.get("raisons"))
    shutil.copy(sauve, OUV)
    check("proxy : Claymore ch.1 -> impossible", get("/manga/precedemment?d=claymore/ch_1")["possible"] is False)

    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True, args=["--autoplay-policy=no-user-gesture-required"])
        for w, h in ((1280, 1000), (360, 780)):
            print("=== %d px" % w)
            c = b.new_context(viewport={"width": w, "height": h}, is_mobile=w < 500, has_touch=w < 500)
            pg = c.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.on("dialog", lambda dl: dl.accept())
            pg.goto("http://127.0.0.1:%d/manga#k=" % PORT + KEY); pg.wait_for_timeout(2500)
            pg.evaluate("() => { try { localStorage.removeItem('manga_prec'); localStorage.setItem('manga_mus_on', '0'); } catch {} }")
            pg.reload(); pg.wait_for_timeout(2500)
            pg.click('nav button[data-tab="tChap"]'); pg.wait_for_timeout(1500)
            check("version >= 1.94.0", tuple(map(int, pg.inner_text("#verBadge")[1:].split("."))) >= (1, 94, 0), pg.inner_text("#verBadge"))
            i = pg.evaluate("() => CHAPS.findIndex(c => c.dir === 'claymore/ch_1')")
            pg.evaluate("(i) => openChap(i)", i); pg.wait_for_timeout(2500)
            check("Claymore ch.1 : pas de ligne Précédemment", not pg.is_visible("#precBox"))
            i = pg.evaluate("() => CHAPS.findIndex(c => c.dir === 'one-punch-man/ch_301')")
            pg.evaluate("(i) => openChap(i)", i); pg.wait_for_timeout(3000)
            check("OPM ch.301 : ligne visible, ✅ des deux", pg.is_visible("#precBox") and pg.inner_text("#precOuvEtat").startswith("✅")
                  and pg.inner_text("#precRatEtat").startswith("✅"), pg.inner_text("#precBox").replace("\n", " | "))
            dep = pg.evaluate("() => document.documentElement.scrollWidth - innerWidth")
            check("aucun débordement horizontal", dep <= 0, dep)
            tag = pg.evaluate("() => NARRS.filter(x => x.etat === 'fini' && x.audio)[0].tag")
            # --- ouverture en tete
            pg.evaluate("(t) => ouvrirLecteur([t])", tag); pg.wait_for_timeout(3000)
            e = pg.evaluate(ETAT)
            check("lecteur : 1re page = « Précédemment… »", e["prec"] == "ouverture" and e["info"].startswith("Précédemment"), e["info"])
            check("image = dernière page du ch.300", "ch_300" in e["img"] and "page_014" in e["img"], e["img"][-60:])
            check("le son du résumé JOUE", "precedemment" in e["aud"] and e["t"] > 0.5 and not e["paused"], (e["t"], e["paused"]))
            check("sous-titre karaoké du résumé", e["km"] > 20 and "Précédemment" in e["sous"], e["km"])
            check("case 📜 visible et cochée", pg.is_visible("#lecPrecOn") and pg.is_checked("#lecPrecOn"))
            pg.click("#lecNext"); pg.wait_for_timeout(2000)
            e = pg.evaluate(ETAT)
            check("suivant -> vraie page du chapitre", e["prec"] is None and "page" in e["info"] and "ch_301" in e["img"], e["info"])
            pg.click("#lecFermer"); pg.wait_for_timeout(400)
            # --- case decochee, memorisee
            pg.evaluate("(t) => ouvrirLecteur([t])", tag); pg.wait_for_timeout(1200)
            pg.click("#lecPrecOn"); pg.click("#lecFermer"); pg.wait_for_timeout(300)
            check("choix mémorisé (manga_prec=0)", pg.evaluate("() => localStorage.getItem('manga_prec')") == "0")
            pg.evaluate("(t) => ouvrirLecteur([t])", tag); pg.wait_for_timeout(1500)
            e = pg.evaluate(ETAT)
            check("décoché -> la page 1 d'abord", e["prec"] is None, e["info"])
            pg.click("#lecFermer"); pg.wait_for_timeout(300)
            # --- rattrapage puis le chapitre (meme case decochee : c'est un choix explicite)
            pg.click("#precRatJouer"); pg.wait_for_timeout(3000)
            e = pg.evaluate(ETAT)
            check("rattrapage : « Rattrapage · ch. 300 » en tête, image p.3 du ch.300", e["prec"] == "rattrapage"
                  and "ch. 300" in e["info"] and "ch_300" in e["img"] and "page_003" in e["img"], e["info"])
            check("rattrapage : le son joue", "rattrapage_01" in e["aud"] and e["t"] > 0.5, e["t"])
            pg.click("#lecNext"); pg.wait_for_timeout(1500)
            check("rattrapage -> enchaîne sur le chapitre", pg.evaluate(ETAT)["prec"] is None)
            pg.click("#lecFermer"); pg.wait_for_timeout(300)
            # --- ecoute a l'aveugle : jamais de resume
            pg.evaluate("() => localStorage.setItem('manga_prec', '1')"); pg.evaluate("() => { PREC_ON = true; }")
            pg.evaluate("(t) => ouvrirLecteur([t], true)", tag); pg.wait_for_timeout(1500)
            check("écoute à l'aveugle : pas de résumé, case cachée", pg.evaluate(ETAT)["prec"] is None and not pg.is_visible("#lecPrecOn"))
            pg.click("#lecFermer"); pg.wait_for_timeout(300)
            check("0 erreur JS", not errs, errs[:3])
            pg.evaluate("() => { try { localStorage.removeItem('manga_prec'); localStorage.removeItem('manga_mus_on'); } catch {} }")
            c.close()
        b.close()
finally:
    shutil.copy(sauve, OUV); os.remove(sauve)

print("\n%d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
