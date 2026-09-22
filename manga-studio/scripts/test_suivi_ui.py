# -*- coding: utf-8 -*-
"""Banc v1.98.0 : SUIVI DE SERIES, en vrai (Demo Frieren ch.143, 19 p. sans narration -> ~0,76 $, ~20 min).
Temps 1 (`lancer`) : panneau 🌙 (file + estimation), le reglage s'ecrit dans suivi.json, « Lancer maintenant » part
depuis l'app (confirmation), le passage est VIVANT, la cellule d'activite montre la narration, un 2e lancement est refuse.
Temps 2 (`verifier`) : passage fini, narration AVEC voix, karaoke cale, journal complet, file vide ensuite.
Usage : python test_suivi_ui.py lancer|verifier [port]
"""
import json, os, sys, time, urllib.request
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
TEMPS = sys.argv[1] if len(sys.argv) > 1 else "lancer"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8190
SRC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sources"))
SERIE, D = "demo-frieren", "demo-frieren/ch_143"
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


def api(path, body=None):
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (PORT, path), data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


if TEMPS == "lancer":
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        c = b.new_context(viewport={"width": 360, "height": 780}, is_mobile=True, has_touch=True)
        pg = c.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        dialogues = []
        pg.on("dialog", lambda dl: (dialogues.append(dl.message), dl.accept()))
        pg.goto("http://127.0.0.1:%d/manga/#k=" % PORT + KEY); pg.wait_for_timeout(2500)
        pg.click('nav button[data-tab="tChap"]'); pg.wait_for_timeout(1200)
        pg.evaluate("() => { const b = document.querySelector('#chapList [data-serie=\"%s\"]'); if (b) b.click(); }" % SERIE); pg.wait_for_timeout(2000)
        pg.click("#btnSuivi"); pg.wait_for_timeout(2000)
        txt = pg.inner_text("#suiviFile")
        check("file : ch. 143 à narrer + estimation", "ch. 143" in txt and "$" in txt, txt)
        check("jamais lancé, bouton actif", pg.is_enabled("#suiviLancer"), pg.inner_text("#suiviPassage"))
        pg.select_option("#suiviVoix", "Charon"); pg.wait_for_timeout(800)
        pg.check("#suiviActif"); pg.wait_for_timeout(1200)
        cfg = json.load(open(os.path.join(SRC, SERIE, "suivi.json"), encoding="utf-8"))
        check("suivi.json : actif, Charon, karaoké, précédemment", cfg.get("actif") and cfg.get("voix") == "Charon" and cfg.get("karaoke") and cfg.get("precedemment"), cfg)
        dep = pg.evaluate("() => document.documentElement.scrollWidth - innerWidth")
        check("360 px : aucun débordement", dep <= 0, dep)
        pg.click("#suiviLancer"); pg.wait_for_timeout(6000)
        check("confirmation avec coût et voix", dialogues and "Charon" in dialogues[-1] and "$" in dialogues[-1], dialogues[-1:] )
        j = api("/manga/suivi?serie=" + SERIE)
        check("passage VIVANT", j["passage"].get("vivant"), j["passage"].get("etat"))
        time.sleep(20)
        act = api("/manga/activite")["items"]
        check("cellule d'activité : la narration du ch.143", any(x.get("d") == D and x.get("type") == "narration" for x in act), [x.get("d") for x in act])
        check("2e lancement refusé", "error" in api("/manga/suivi_lancer", {"serie": SERIE}))
        check("0 erreur JS", not errs, errs[:3])
        b.close()
else:
    j = api("/manga/suivi?serie=" + SERIE)
    ps = j["passage"]
    check("passage fini", ps.get("etat") == "fini" and not ps.get("vivant"), ps.get("etat"))
    check("1 chapitre narré, 0 erreur", len(ps.get("fait") or []) == 1 and not ps.get("erreurs"), (ps.get("fait"), ps.get("erreurs")))
    n = json.load(open(os.path.join(SRC, D, "narration", "kimi-charon", "narration.json"), encoding="utf-8"))
    avec = [x for x in n["pages"] if x.get("audio")]
    check("narration AVEC voix", len(avec) >= 10, len(avec))
    check("karaoké calé", bool((n.get("stats") or {}).get("karaoke")), (n.get("stats") or {}).get("karaoke"))
    evs = [x["ev"] for x in j["journal"]]
    check("journal : début, narration, karaoké, fin", all(e in evs for e in ("debut", "narration", "karaoke", "fin")), evs)
    check("file vide ensuite", not j["file"], j["file"])
    print("  cout de la narration : %.3f $ en %.0f s" % ((n.get("stats") or {}).get("cout_total", 0), (n.get("stats") or {}).get("total_s", 0)))
print("\n%d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
