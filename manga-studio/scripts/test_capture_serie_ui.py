# -*- coding: utf-8 -*-
"""Banc v2.3.2 (etape 18) -- repare v2.67.0 (puces de l'etape 4 au lieu du selecteur cache ; + puce « dernier paru ») : CAPTURER PLUSIEURS CHAPITRES depuis l'app, comme Quang.

360 px : la ligne « Chapitres : [selecteur] » tient sans debordement ; le selecteur vaut « jusqu'au ch. » par defaut
et n'affiche que le champ utile ; « jusqu'au » avant le depart -> alerte et RIEN n'est envoye.
1280 px : vraie capture OPM (MangaDex, vi) du ch.296 jusqu'au 298, « ignorer les chapitres intermediaires » coche
-> 296, 297, 298 (le 296.5 qui existe est saute), l'etat suit le chapitre en cours, les 3 chapitres arrivent dans la
bibliotheque. Titre « banc serie ui » -> sources/banc-serie-ui/, efface a la fin, comme l'onglet jetable.
Usage : python test_capture_serie_ui.py [port]
"""
import json, os, shutil, sys, time, urllib.request
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
CDP = "http://127.0.0.1:9223"
SRC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sources"))
BANC = os.path.join(SRC, "banc-serie-ui")
OPM_301 = "30f3755a-7dcf-4594-964d-58e2c9e93716"
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""), flush=True)


def mdx(path):
    req = urllib.request.Request("https://api.mangadex.org" + path, headers={"User-Agent": "manga-studio-banc/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def uuid_chapitre(num):
    info = mdx("/chapter/" + OPM_301)["data"]
    manga = next(r["id"] for r in info["relationships"] if r["type"] == "manga")
    agg = mdx("/manga/%s/aggregate?translatedLanguage[]=%s" % (manga, info["attributes"]["translatedLanguage"]))
    for vol in agg["volumes"].values():
        if str(num) in vol["chapters"]:
            return vol["chapters"][str(num)]["id"]
    raise SystemExit("chapitre %s introuvable" % num)


def prepare(pg):
    pg.goto("http://127.0.0.1:%d/manga/#k=" % PORT + KEY); pg.wait_for_timeout(2500)
    pg.click('nav button[data-tab="tChap"]'); pg.wait_for_timeout(1500)
    pg.evaluate("() => { const d = document.getElementById('capBox'); d.open = true; }")
    pg.evaluate("() => refreshCapTabs()"); pg.wait_for_timeout(1500)


shutil.rmtree(BANC, ignore_errors=True)
url296 = "https://mangadex.org/chapter/" + uuid_chapitre(296)   # v2.3.2 : 296 -> 298, un 296.5 existe (vi)
with urllib.request.urlopen(urllib.request.Request(CDP + "/json/new?" + url296, method="PUT"), timeout=10) as r:
    onglet = json.load(r)["id"]
time.sleep(8)
try:
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        # --- 360 px : mise en page + refus
        pg = b.new_page(viewport={"width": 360, "height": 780}); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        dialogues, envois = [], []
        pg.on("dialog", lambda dl: (dialogues.append(dl.message), dl.dismiss()))
        pg.on("request", lambda rq: envois.append(rq.url) if "/manga/fetch_capture" in rq.url else None)
        prepare(pg)
        m = pg.evaluate("""() => { const r = document.querySelector('.cap-serie'); const s = r.getBoundingClientRect();
            return {page: document.documentElement.scrollWidth - document.documentElement.clientWidth,
                    droite: Math.round(s.right), vw: innerWidth, suite: !!document.getElementById('capSuite'),
                    jusqua: !!document.getElementById('capJusqua'),
                    interne: Array.from(r.querySelectorAll('*')).filter(e => e.getBoundingClientRect().right > innerWidth + 1).length}; }""")
        check("360 px : la page ne déborde pas", m["page"] <= 0, m)
        check("360 px : la ligne « suivants / jusqu'au » tient dans l'écran", m["droite"] <= m["vw"] and m["interne"] == 0, m)
        k = pg.evaluate("(u) => CAP_TABS.findIndex(t => t.url === u)", url296)
        pg.select_option("#capTab", str(k))
        sel = pg.evaluate("() => [document.getElementById('capSerieMode').value, !document.getElementById('capJusqua').hidden, document.getElementById('capSuite').hidden, document.getElementById('capEntiers').checked]")
        check("sélecteur : « jusqu'au ch. » par défaut, seul son champ visible, x.5 ignorés cochés", sel == ["jusqua", True, True, True], sel)
        pg.click("#capChips [data-serie=suite]")          # v2.67.0 : les PUCES de l'etape 4 (le selecteur est cache depuis v2.28)
        sel = pg.evaluate("() => [document.getElementById('capJusqua').hidden, !document.getElementById('capSuite').hidden]")
        check("sélecteur « + suivants » : l'autre champ", sel == [True, True], sel)
        pg.click("#capChips [data-serie=seul]")
        check("sélecteur « ce chapitre seul » : aucun champ", pg.evaluate("() => document.getElementById('capJusqua').hidden && document.getElementById('capSuite').hidden && document.getElementById('capEntiersL').hidden"))
        pg.click("#capChips [data-serie=dernier]")
        sel = pg.evaluate("() => [document.getElementById('capSerieMode').value, document.getElementById('capJusqua').hidden, document.getElementById('capSuite').hidden, !document.getElementById('capEntiersL').hidden]")
        check("puce « Jusqu'au dernier paru » (v2.67.0) : aucun champ à remplir, x.5 proposés", sel == ["dernier", True, True, True], sel)
        pg.click("#capChips [data-serie=jusqua]")
        pg.evaluate("() => { $('capTitre').value = 'banc serie ui'; }");   # v2.63.0 : bouton en lecture seule sur telephone
        pg.fill("#capChap", "296"); pg.fill("#capJusqua", "295")
        pg.click("#btnCapturer"); pg.wait_for_timeout(1000)
        check("« jusqu'au 295 » depuis 296 : alerte", any("plus grand que 296" in d for d in dialogues), dialogues)
        check("… et RIEN n'est envoyé", not envois, envois)
        check("360 px : aucune erreur JS", not errs, errs)
        pg.close()

        # --- 1280 px : vraie capture en série depuis l'interface
        pg = b.new_page(viewport={"width": 1280, "height": 1000}); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        dialogues, envois = [], []
        pg.on("dialog", lambda dl: (dialogues.append(dl.message), dl.accept()))
        pg.on("request", lambda rq: envois.append(rq.post_data) if "/manga/fetch_capture" in rq.url else None)
        prepare(pg)
        k = pg.evaluate("(u) => CAP_TABS.findIndex(t => t.url === u)", url296)
        check("l'onglet jetable est dans la liste", k >= 0, k)
        pg.select_option("#capTab", str(k))
        pg.evaluate("() => { $('capTitre').value = 'banc serie ui'; }");   # v2.63.0 : bouton en lecture seule sur telephone
        pg.fill("#capChap", "296"); pg.fill("#capJusqua", "298")
        pg.click("#btnCapturer"); pg.wait_for_timeout(1500)
        check("la confirmation annonce la série sans x.5", any("jusqu'au chapitre 298 (sans les chapitres intermédiaires)" in d for d in dialogues), dialogues)
        corps = json.loads(envois[0]) if envois else {}
        check("envoi : jusqu'au 298, entiers", corps.get("jusqua") == "298" and corps.get("entiers") is True and corps.get("chapter") == "296", corps)
        etats, t0 = [], time.time()
        while time.time() - t0 < 600:
            e = pg.evaluate("() => document.getElementById('capEtat').textContent")
            if not etats or etats[-1] != e:
                etats.append(e)
            if e.startswith(("✅", "🟠", "❌", "ℹ️")):
                break
            pg.wait_for_timeout(2000)
        fin = etats[-1] if etats else ""
        check("pendant : « ch. 297 (jusqu'au ch. 298) … 1 chapitre(s) déjà faits »",
              any("ch. 297 (jusqu'au ch. 298)" in e and "1 chapitre(s) déjà faits" in e for e in etats),
              [e for e in etats if "297" in e][:1])
        check("bilan : ✅ 3 chapitres, ch. 296, 297, 298 (pas de 296.5)", fin.startswith("✅ 3 chapitre(s)") and "ch. 296, 297, 298 " in fin, fin)
        pg.wait_for_timeout(2000)
        dirs = pg.evaluate("() => CHAPS.map(c => c.dir).filter(d => d.startsWith('banc-serie-ui/'))")
        check("bibliothèque : les 3 chapitres", sorted(dirs) == ["banc-serie-ui/ch_296", "banc-serie-ui/ch_297", "banc-serie-ui/ch_298"], dirs)
        check("le 1er chapitre de la série est ouvert", pg.evaluate("() => CHAP_OPEN") == "banc-serie-ui/ch_296",
              pg.evaluate("() => CHAP_OPEN"))
        check("1280 px : aucune erreur JS", not errs, errs)
        pg.close()
        b.close()
finally:
    try:
        urllib.request.urlopen(CDP + "/json/close/" + onglet, timeout=5).read()
    except Exception:
        pass
    shutil.rmtree(BANC, ignore_errors=True)
print("\nVERDICT : %d/%d" % (len(OK), len(OK) + len(KO)) + ("" if not KO else "  -- KO : " + " ; ".join(KO)))
sys.exit(0 if not KO else 1)
