# -*- coding: utf-8 -*-
"""Banc v2.65.0 : ARRETER une capture (maquette_arret_v1, validee 25/09 22h48). APP REELLE (8190) + vraie capture (WEBTOON ep. 1-3).
A « ⏹ Apres ce chapitre » pendant le ch. 1 -> arret apres le 1, bilan « a ta demande », reprise au 2 (adresse de l'ep. 2), ch_1 complet.
B « ✖ Maintenant » pendant le ch. 2 -> processus arrete, ch. 2 a moitie A LA CORBEILLE, reprise au 2.
C « Apres » puis « annuler » -> la serie va jusqu'au bout (2, 3), « jusqu'au ch. 3 : fait ».
+ ecran : boutons dans le detail de l'activite, puce « s'arretera », bandeau BLEU avec « ▶ Reprendre au ch. 2 ».
Nettoyage : la serie du banc, ses entrees de corbeille, le bilan de Quang (_capture_derniere.json) remis a l'identique.
"""
import json, os, shutil, sys, time, urllib.request
from urllib.parse import quote
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
API, CDP, TITRE = "http://127.0.0.1:8190", "http://127.0.0.1:9223", "banc arret"
SRC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sources"))
BILAN = os.path.join(SRC, "_capture_derniere.json")
EP = "https://www.webtoons.com/en/fantasy/tower-of-god/season-1-ep-0/viewer?title_no=95&episode_no=%d"
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


def api(chemin, corps=None):
    rq = urllib.request.Request(API + chemin, data=json.dumps(corps).encode() if corps is not None else None,
                                headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"},
                                method="POST" if corps is not None else "GET")
    return json.load(urllib.request.urlopen(rq, timeout=30))


def onglet(url):
    t = json.load(urllib.request.urlopen(urllib.request.Request(CDP + "/json/new?" + quote(url, safe=""), method="PUT")))
    time.sleep(8)
    for x in api("/manga/fetch_tabs")["tabs"]:
        if "episode_no=" in x["url"] and x["url"].split("episode_no=")[1].split("&")[0] == url.split("episode_no=")[1]:
            return t["id"], x["url"]
    return t["id"], None


def attendre(cond, max_s=300):
    t0 = time.time()
    while time.time() - t0 < max_s:
        s = api("/manga/fetch_status")
        if cond(s): return s
        time.sleep(1)
    return api("/manga/fetch_status")


def bilan():
    time.sleep(2)
    return json.load(open(BILAN, encoding="utf-8"))


serie = os.path.join(SRC, "banc-arret")
assert not os.path.exists(serie), "la serie du banc existe deja : a nettoyer d'abord"
sauve = open(BILAN, "rb").read() if os.path.exists(BILAN) else None
cb0 = set(os.listdir(os.path.join(SRC, "_corbeille"))) if os.path.isdir(os.path.join(SRC, "_corbeille")) else set()
tabs = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        pg = b.new_page(viewport={"width": 476, "height": 860}, is_mobile=True, has_touch=True)
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(API + "/manga#k=" + KEY); pg.wait_for_timeout(4000)
        # ---- A : apres ce chapitre
        tid, url = onglet(EP % 1); tabs.append(tid)
        r = api("/manga/fetch_capture", {"tab": url, "title": TITRE, "chapter": "1", "page1": True, "jusqua": "3"})
        check("A : capture ep.1 -> 3 lancée", r.get("ok"), r)
        attendre(lambda s: s.get("etat") == "en cours" and (s.get("pages") or 0) >= 1, 120)
        pg.evaluate("() => { actRafraichir(); $('actPanel').hidden = false; }"); pg.wait_for_timeout(1500); pg.evaluate("() => actRendre()")
        btn = pg.evaluate("() => [...document.querySelectorAll('#actListe [data-arret]')].map(b => b.dataset.arret + ':' + b.textContent.trim())")
        check("écran : « ⏹ Après ce chapitre » et « ✖ Maintenant » sous la capture", btn == ["apres:⏹ Après ce chapitre", "maintenant:✖ Maintenant"], btn)
        r = api("/manga/fetch_arret", {"quand": "apres"})
        act = [x for x in api("/manga/activite")["items"] if x["type"] == "capture"]
        check("A : arrêt « après » posé, visible dans l'activité", r.get("arret") == "apres" and act and act[0].get("arret") == "apres", act)
        pg.evaluate("() => actRafraichir()"); pg.wait_for_timeout(1500); pg.evaluate("() => actRendre()")
        puce = pg.evaluate("() => (document.querySelector('#actListe .act-arret .puce') || {}).textContent || ''")
        check("écran : puce « s'arrêtera à la fin du ch. 1 · annuler »", "s'arrêtera à la fin du ch. 1" in puce and "annuler" in puce, puce)
        s = attendre(lambda s: s.get("etat") != "en cours", 300)
        bi = bilan()
        check("A : bilan « à ta demande après le ch. 1 », reprise au 2 (adresse de l'ep. 2)",
              bi.get("demande") and "après le ch. 1" in bi.get("arret", "") and bi.get("faits") == ["1"]
              and (bi.get("reprise") or {}).get("chapitre") == "2" and "episode_no=2" in (bi.get("reprise") or {}).get("url", ""), bi)
        check("A : ch_1 complet (manifeste), aucun ch_2", os.path.isfile(os.path.join(serie, "ch_1", "manifest.json"))
              and not os.path.exists(os.path.join(serie, "ch_2")), os.listdir(serie) if os.path.isdir(serie) else "absent")
        pg.evaluate("() => { try { localStorage.removeItem('manga_cap_vu'); } catch {} }"); pg.reload(); pg.wait_for_timeout(5000)
        pg.evaluate("() => capAlerteVerifier()"); pg.wait_for_timeout(1500)
        ban = pg.evaluate("() => [!$('capAlerte').hidden, $('capAlerte').classList.contains('info'), $('capAlerteTxt').textContent, $('capAlerteReprendre').hidden ? '' : $('capAlerteReprendre').textContent, $('actErr').hidden]")
        check("écran : bandeau BLEU « arrêtée à ta demande après le ch. 1 », « ▶ Reprendre au ch. 2 », pas de ❌",
              ban[0] and ban[1] and "à ta demande après le ch. 1" in ban[2] and ban[3] == "▶ Reprendre au ch. 2" and ban[4], ban)
        # ---- B : maintenant, pendant le ch. 2 (l'onglet est deja sur l'ep. 2)
        url2 = next((x["url"] for x in api("/manga/fetch_tabs")["tabs"] if "episode_no=2" in x["url"]), None)
        r = api("/manga/fetch_capture", {"tab": url2, "title": TITRE, "chapter": "2", "page1": True, "jusqua": "3"})
        check("B : capture ep.2 -> 3 lancée", r.get("ok"), r)
        attendre(lambda s: s.get("etat") == "en cours" and (s.get("pages") or 0) >= 2, 120)
        r = api("/manga/fetch_arret", {"quand": "maintenant"})
        s = api("/manga/fetch_status")
        check("B : processus arrêté (statut « arrêtée à ta demande » ch. 2)", r.get("arret") == "maintenant" and s.get("etat") != "en cours"
              and s.get("arret_demande") == "2", [r, s.get("etat"), s.get("arret_demande")])
        bi = bilan()
        cb = set(os.listdir(os.path.join(SRC, "_corbeille"))) - cb0
        check("B : bilan « pendant le ch. 2 », reprise au 2 (adresse de l'ep. 2), 0 chapitre fait",
              bi.get("demande") and "pendant le ch. 2" in bi.get("arret", "") and bi.get("faits") == []
              and (bi.get("reprise") or {}).get("chapitre") == "2" and "episode_no=2" in (bi.get("reprise") or {}).get("url", ""), bi)
        check("B : le ch. 2 à moitié est à la CORBEILLE (plus dans la série)", not os.path.exists(os.path.join(serie, "ch_2"))
              and any("banc-arret__ch_2__arret" in x for x in cb), sorted(cb))
        # ---- C : apres puis annuler
        r = api("/manga/fetch_capture", {"tab": url2, "title": TITRE, "chapter": "2", "page1": True, "jusqua": "3"})
        attendre(lambda s: s.get("etat") == "en cours" and (s.get("pages") or 0) >= 1, 120)
        api("/manga/fetch_arret", {"quand": "apres"}); time.sleep(1); r = api("/manga/fetch_arret", {"quand": "annuler"})
        act = [x for x in api("/manga/activite")["items"] if x["type"] == "capture"]
        check("C : « annuler » retire l'arrêt", r.get("ok") and act and not act[0].get("arret"), act)
        attendre(lambda s: s.get("etat") != "en cours", 400)
        bi = bilan()
        check("C : la série va jusqu'au bout (2, 3), « jusqu'au ch. 3 : fait », objectif tenu",
              bi.get("faits") == ["2", "3"] and bi.get("arret") == "jusqu'au ch. 3 : fait" and bi.get("tenu") and not bi.get("demande"), bi)
        check("aucune erreur JS", not errs, errs[:3])
        b.close()
finally:
    for t in tabs:
        try: urllib.request.urlopen(CDP + "/json/close/" + t)
        except Exception: pass
    shutil.rmtree(serie, ignore_errors=True)
    cbd = os.path.join(SRC, "_corbeille")
    for x in (set(os.listdir(cbd)) - cb0 if os.path.isdir(cbd) else []):
        if "banc-arret" in x: shutil.rmtree(os.path.join(cbd, x), ignore_errors=True)
    if sauve is not None: open(BILAN, "wb").write(sauve)
    elif os.path.exists(BILAN): os.remove(BILAN)
    print("nettoyage : série du banc supprimée, corbeille du banc vidée, bilan de Quang " + ("restauré" if sauve is not None else "absent au départ"))

print("\nVERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
