# -*- coding: utf-8 -*-
"""Banc v2.75.0 : pochette + fiche d'une serie fraichement capturee posees SANS l'ouvrir (regression v2.67.1).
APP REELLE, RIEN n'est ecrit : la liste /manga/sources est modifiee A LA VOLEE dans le navigateur du banc (une serie rendue
« capturee a l'instant, sans pochette, fiche ancienne ») et les appels /manga/pochette + /manga/serie_infos sont INTERCEPTES
(comptes, jamais transmis). Cas : fin de capture (chapitre / serie) -> 1 pochette + 1 fiche pour CETTE serie, rien ne s'ouvre, aucune autre serie
touchee ; capture en cours -> rien ; pas de doublon ; navigateur pilote sans BANC_AUTO -> rien.
Usage : python test_serie_auto_ui.py [port] [serie] [--mutation]   (--mutation : app v2.74.0 servie -> doit sortir ROUGE)
"""
import json, os, sys, time
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
MUT = "--mutation" in sys.argv; sys.argv = [a for a in sys.argv if a != "--mutation"]
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
SERIE = sys.argv[2] if len(sys.argv) > 2 else "one-punch-man"
URL = "http://127.0.0.1:%d/manga#k=%s" % (PORT, KEY)
ICI = os.path.dirname(os.path.abspath(__file__))
OK, KO = [], []
def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail)[:200] if detail else ""), flush=True)

def scenario(b, cas, banc_auto=True, fin=None):
    """cas : etat de la serie dans /manga/sources ('recente' | 'en_cours'). fin : None (pas de capture) | 'chapitre' | 'serie'
    = /manga/fetch_status simule « capture terminee » puis suivreCapture() appele (le vrai chemin de fin de capture)."""
    c = b.new_context(viewport={"width": 1280, "height": 900}); pg = c.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    if banc_auto: pg.add_init_script("window.BANC_AUTO = true;")
    appels = {"pochette": [], "fiche": []}; dirs = []
    def sources(route):
        r = route.fetch(); d = r.json()
        maintenant = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
        for it in d.get("items", []):
            if it.get("slug") != SERIE: continue
            dirs.append(it["dir"])
            it["pochette"] = None
            it["serie_info"] = {"maj": "2020-01-01 00:00:00"}                     # fiche plus vieille que le dernier chapitre
            it["captured_at"] = maintenant
            if cas == "en_cours": it["manifest"] = None                            # un chapitre encore en capture
        route.fulfill(response=r, body=json.dumps(d))
    def statut(route):
        d = dirs[0] if dirs else SERIE + "/ch_1"
        if fin == "chapitre": st = {"etat": "fini", "dossier": d, "titre": "banc", "chapitre": "1", "duree_s": 1, "sortie": []}
        elif fin == "serie": st = {"etat": "fini", "suite": 2, "serie": "SÉRIE : 1 chapitre(s) : 1", "dossiers": [d], "titre": "banc",
                                   "chapitre": "1", "duree_s": 1, "sortie": []}
        else: st = {"etat": "aucune"}
        route.fulfill(status=200, content_type="application/json", body=json.dumps(st))
    def intercepte(cle):
        def f(route):
            appels[cle].append(json.loads(route.request.post_data or "{}").get("slug"))
            route.fulfill(status=200, content_type="application/json", body='{"error": "banc : non transmis"}')
        return f
    pg.route("**/manga/sources*", sources)
    pg.route("**/manga/fetch_status*", statut)
    pg.route("**/manga/pochette*", intercepte("pochette"))
    pg.route("**/manga/serie_infos*", intercepte("fiche"))
    if MUT:
        pg.route("**/manga", lambda route: route.fulfill(status=200, content_type="text/html; charset=utf-8",
                 body=open(os.path.join(ICI, "..", "manga_studio.html.bak-20260926-v2750"), encoding="utf-8").read()))
    pg.goto(URL); pg.wait_for_timeout(4500)
    avant = {k: list(v) for k, v in appels.items()}
    if fin: pg.evaluate("() => suivreCapture()"); pg.wait_for_timeout(3000)
    etat = pg.evaluate("() => [LIB_SERIE, CHAP_OPEN]")
    n1 = (len(appels["pochette"]), len(appels["fiche"]))
    if fin: pg.evaluate("() => suivreCapture()"); pg.wait_for_timeout(2500)          # une 2e fin : pas de doublon
    c.close()
    return avant, appels, n1, etat, errs

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for fin in ("chapitre", "serie"):
        print("== fin de capture (%s) d'une série sans pochette, jamais ouverte" % fin)
        avant, a, n1, etat, errs = scenario(b, "recente", fin=fin)
        check("au chargement, AVANT la fin : rien n'est demandé (aucune autre série touchée)", avant == {"pochette": [], "fiche": []}, avant)
        check("fin de capture : pochette demandée pour CETTE série seulement", a["pochette"] == [SERIE], a["pochette"])
        check("fin de capture : fiche (tomes, dates) demandée pour CETTE série", a["fiche"] == [SERIE], a["fiche"])
        check("rien ne s'ouvre : ni la série ni un chapitre", etat[0] != SERIE and not etat[1], etat)
        check("2e fin de capture : aucune demande en double", n1 == (len(a["pochette"]), len(a["fiche"])), n1)
        check("aucune erreur JS", not errs, errs[:3])
    if not MUT:
        print("== capture EN COURS (un chapitre sans manifeste)")
        avant, a, _, _, errs = scenario(b, "en_cours", fin="chapitre")
        check("chapitre encore sans manifeste : rien n'est demandé", a == {"pochette": [], "fiche": []}, a)
        print("== navigateur piloté SANS autorisation du banc")
        avant, a, _, _, errs = scenario(b, "recente", banc_auto=False, fin="chapitre")
        check("banc sans BANC_AUTO : rien n'est écrit", a == {"pochette": [], "fiche": []}, a)
    b.close()
print("\nVERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
