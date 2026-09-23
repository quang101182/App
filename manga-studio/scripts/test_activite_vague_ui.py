# -*- coding: utf-8 -*-
"""Banc UI v2.8.0 (A1) : compteur « 3/15 » et « reste ~X sur ~Y » de l'Activite, sur une VAGUE simulee (les reponses de
/manga/activite sont interceptees : deroulement deterministe). PC 1280 px + telephone 360 px. Ne lance RIEN.
Usage : python test_activite_vague_ui.py"""
import json, os, sys
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banc_outils as bo
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
OK, KO = [], []
def check(n, c, d=""):
    (OK if c else KO).append(n); print(("  [OK] " if c else "  [KO] ") + n + (" -- " + str(d) if d else ""), flush=True)
A = {"type": "narration", "d": "x/ch_1", "titre": "Essai", "chapitre": "1", "tag": "t", "etape": "voix", "fait": 3, "total": 20, "reste_s": 600}
B = {"type": "video", "d": "x/ch_2", "titre": "Essai", "chapitre": "2", "tag": "t", "etape": "attente"}
B2 = dict(B, etape="images", fait=5, total=20, reste_s=300)
C = {"type": "video", "d": "x/ch_3", "titre": "Essai", "chapitre": "3", "tag": "t", "etape": "attente"}
ETAT = {"items": []}
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w, h in ((1280, 900), (360, 780)):
        print("=== %d px" % w)
        c = b.new_context(viewport={"width": w, "height": h}, is_mobile=w < 400, has_touch=w < 400); pg = c.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.route("**/manga/activite*", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(ETAT)))
        pg.route("**/manga/suivi?serie=*", lambda r: r.fulfill(status=200, content_type="application/json",
                                                              body=json.dumps({"config": {"video": ETAT.get("video", False)}})))
        pg.goto("http://127.0.0.1:8190/manga#k=" + KEY); pg.wait_for_timeout(2500)
        check("version = fichier", pg.inner_text("#verBadge") == "v" + bo.version_app())
        def etape(items, attente=0):
            ETAT["items"] = items
            if attente: pg.wait_for_timeout(attente)
            pg.evaluate("() => actRafraichir()"); pg.wait_for_timeout(300)
            return pg.evaluate("() => [document.getElementById('actN').hidden ? '' : document.getElementById('actN').textContent,"
                               " document.getElementById('actVague').hidden ? '' : document.getElementById('actVague').textContent,"
                               " document.getElementById('hdrAct').title]")
        pg.click("#hdrAct"); pg.wait_for_timeout(300)                           # panneau ouvert : le bilan s'y affiche
        n, v, t = etape([A, B])
        check("1 : 2 taches (1 en cours, 1 en attente) -> « 0/2 »", n == "0/2", n)
        check("1 : « reste au moins ~10 min » (la video en attente n'a pas encore de duree mesuree)", "au moins ~10 min" in v, v)
        n, v, t = etape([B2], attente=2000)
        check("2 : la narration finie -> « 1/2 »", n == "1/2", n)
        check("2 : reste ~5 min (estimation de la video en cours)", "reste ~5 min" in v and "au moins" not in v, v)
        n, v, t = etape([B2, C])
        check("3 : une video de plus en file -> « 1/3 », « au moins » (aucune video encore mesuree)", n == "1/3" and "au moins" in v, (n, v))
        n, v, t = etape([dict(C, etape="images", fait=1, total=20, reste_s=120)], attente=1500)
        check("4 : 2e video finie -> « 2/3 », duree des videos maintenant MESUREE", n == "2/3" and "au moins" not in v, (n, v))
        check("4 : le total « sur ~… » est donne", " sur " in v, v)
        check("la pastille le dit aussi (survol)", "2 / 3 terminées" in t, t)
        n, v, t = etape([])
        check("5 : tout est fini -> compteur et bilan effaces (remise a zero)", n == "" and v == "", (n, v))
        n, v, t = etape([A])
        check("6 : nouvelle vague -> repart de 0 (« 0 / 1 », pas de « x/y » dans la pastille pour 1 seule tache)", n == "" and v.startswith("0 / 1"), (n, v))
        etape([])
        # v2.8.1 : un BATCH « Tout traiter » de 27 chapitres = 27 taches (pas 1), sans compter en double l'etape en cours
        LOT = {"type": "lot", "d": "x/ch_1", "titre": "x", "chapitre": "1", "etape": "narration", "fait": 0, "total": 27}
        N1 = {"type": "narration", "d": "x/ch_1", "titre": "Essai", "chapitre": "1", "tag": "t", "etape": "voix", "reste_s": 300}
        n, v, t = etape([LOT, N1])
        check("L1 : batch de 27 chapitres -> « 0/27 » (la narration du chapitre en cours n'est pas une tache de plus)", n == "0/27", n)
        check("L1 : « au moins » tant qu'aucun chapitre du batch n'est mesure", "au moins" in v, v)
        LOT2 = dict(LOT, d="x/ch_2", chapitre="2", fait=1)
        N2 = dict(N1, d="x/ch_2", chapitre="2")
        V1 = {"type": "video", "d": "x/ch_1", "titre": "Essai", "chapitre": "1", "tag": "t", "etape": "attente"}
        n, v, t = etape([LOT2, N2, V1], attente=1500)
        check("L2 : 1er chapitre fait + sa video en file -> « 1/28 »", n == "1/28", n)
        check("L2 : duree d'un chapitre mesuree -> plus de « au moins » pour le batch (la video, elle, pas encore mesuree)", "reste" in v, v)
        etape([])
        # v2.8.2 : batch AVEC videos : 27 chapitres + 27 videos a venir -> total 54, qui ne bouge plus
        ETAT["video"] = True
        etape([LOT, N1]); n, v, t = etape([LOT, N1])                    # 2e tour : l'option video du profil est lue
        check("V1 : batch de 27 chapitres AVEC videos -> « 0/54 » des le depart", n == "0/54", n)
        n, v, t = etape([LOT2, N2, V1], attente=1200)
        check("V2 : 1er chapitre fini, sa video en file -> « 1/54 » (le total NE BOUGE PAS)", n == "1/54", n)
        n, v, t = etape([dict(LOT2, d="x/ch_3", chapitre="3", fait=2), dict(N2, d="x/ch_3"), dict(V1, etape="images", fait=2, total=20, reste_s=60),
                         dict(V1, d="x/ch_2", chapitre="2")], attente=1200)
        check("V3 : 2e chapitre fini, 2e video en file -> « 2/54 »", n == "2/54", n)
        ETAT["video"] = False
        etape([])
        # v2.8.4 : on ROUVRE l'app pendant la vague ; la narration s'est finie pendant que l'app etait fermee
        etape([A, B]); ETAT["items"] = [B]
        pg.reload(); pg.wait_for_timeout(3500)
        rr = pg.evaluate("() => [document.getElementById('actN').hidden ? '' : document.getElementById('actN').textContent, ACT.finis.length]")
        check("R : app rouverte, une tache finie entre-temps -> « 1/2 » (et non « 0/1 »)", rr[0] == "1/2", rr)
        pg.click("#hdrAct"); pg.wait_for_timeout(300)                           # le rechargement a ferme le panneau
        etape([])
        n0, v0, t0 = etape([dict(B, etape="images"), C])                                 # v2.8.3 : rien de mesure
        check("0 : rien de mesure (videos sans estimation) -> « estimation en cours… »", "estimation en cours" in v0, v0)
        etape([])
        check("pas de défilement horizontal", pg.evaluate("() => document.documentElement.scrollWidth <= innerWidth + 1"))
        etape([A, B])
        pg.locator("#actPanel").screenshot(path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "act_vague_%d.png" % w))
        check("aucune erreur JS", not errs, errs[:2]); c.close()
    b.close()
print("\n%d/%d" % (len(OK), len(OK) + len(KO))); sys.exit(1 if KO else 0)
