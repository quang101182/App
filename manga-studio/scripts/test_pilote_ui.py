# -*- coding: utf-8 -*-
"""Banc v2.0.0 : TELECOMMANDE de la fenetre de capture, en vrai (fenetre Edge dediee, CDP 9223).
Travaille dans un onglet A LUI (＋ nouvel onglet, ferme a la fin) : les onglets de Quang ne sont pas touches.
Panneau : onglets listes, ecran affiche ; ＋ ouvre un onglet ; adresse -> la page change (url + ecran) ; ⬇ defile
(l'ecran change) ; toucher l'ecran = un clic (sur un lien : la page change) ; ◀ revient ; basculer d'onglet ;
« ✔ Capturer cet onglet » le selectionne pour la capture ; ✕ le ferme ; 360 px sans debordement.
Usage : python test_pilote_ui.py [port]
"""
import hashlib, json, os, sys, urllib.request
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
OK, KO = [], []
URL1 = "https://en.wikipedia.org/wiki/Manga"


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


def onglets():
    req = urllib.request.Request("http://127.0.0.1:%d/manga/pilote_onglets" % PORT, headers={"Authorization": "Bearer " + KEY})
    return json.load(urllib.request.urlopen(req, timeout=10))


avant = {o["id"] for o in onglets()["onglets"]}
check("fenêtre de capture ouverte", onglets()["edge"], len(avant))
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w, h in ((1280, 1000), (360, 780)):
        print("=== %d px" % w)
        c = b.new_context(viewport={"width": w, "height": h}, is_mobile=w < 500, has_touch=w < 500)
        pg = c.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("dialog", lambda dl: dl.accept())
        pg.goto("http://127.0.0.1:%d/manga/#k=" % PORT + KEY); pg.wait_for_timeout(2500)
        pg.click('nav button[data-tab="tChap"]'); pg.wait_for_timeout(800)
        pg.evaluate("() => { document.getElementById('capBox').open = true; }")
        pg.click('#capMode [data-mode="pilote"]'); pg.wait_for_timeout(2500)      # v2.1.1 : un choix parmi trois
        n = pg.evaluate("() => document.querySelectorAll('#pilOnglets [data-pil-onglet]').length")
        check("onglets de la fenêtre listés", n == len(avant), (n, len(avant)))
        ecran = lambda: pg.evaluate("() => { const i = document.getElementById('pilEcran'); return [i.naturalWidth, i.src]; }")
        check("écran de l'onglet affiché", ecran()[0] > 300, ecran()[0])
        # --- mon onglet
        pg.click("[data-pil-nouvel]"); pg.wait_for_timeout(2500)
        mien = pg.evaluate("() => PIL.id")
        check("＋ : un nouvel onglet, sélectionné", mien and mien not in avant, mien)
        pg.fill("#pilUrl", URL1); pg.click("#pilAller"); pg.wait_for_timeout(5000)
        check("adresse → la page s'ouvre (url lue)", "wikipedia.org/wiki/Manga" in pg.input_value("#pilUrl"), pg.input_value("#pilUrl"))
        # toucher l'ecran sur un lien : on vise le 1er lien de contenu (coordonnees lues dans la page par CDP)
        lien = json.loads(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:9223/json/list"), timeout=5).read())
        ws = [t for t in lien if t["id"] == mien][0]["webSocketDebuggerUrl"]
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import cdp_mini
        with cdp_mini.Onglet(ws) as o:
            r = o.cmd("Runtime.evaluate", returnByValue=True, expression="""(() => { const a = [...document.querySelectorAll('#mw-content-text p a[href*="wikipedia.org/wiki/"]')]
                .find(x => { if (x.href.split('/wiki/')[1].includes(':')) return false; const r = x.getBoundingClientRect(); return r.top > 60 && r.bottom < innerHeight - 20 && r.width > 20; });
                if (!a) return null; const r = a.getBoundingClientRect();
                return [ (r.left + r.width / 2) / innerWidth, (r.top + r.height / 2) / innerHeight, a.href ]; })()""")
        cible = (r.get("result") or {}).get("value")
        if cible:
            box = pg.locator("#pilEcran").bounding_box()
            pg.mouse.click(box["x"] + cible[0] * box["width"], box["y"] + cible[1] * box["height"]); pg.wait_for_timeout(5000)
            check("toucher l'écran sur un lien → la page change", pg.input_value("#pilUrl").split("#")[0] == cible[2].split("#")[0], (pg.input_value("#pilUrl"), cible[2]))
            pg.click('[data-pil="retour"]'); pg.wait_for_timeout(4000)
            check("◀ : retour à la page d'avant", pg.input_value("#pilUrl").startswith(URL1), pg.input_value("#pilUrl"))
        else:
            check("un lien visible pour le test du toucher", False)
        # le defilement APRES le clic : un defilement juste avant faisait viser un lien encore en mouvement
        img = lambda: hashlib.md5(pg.evaluate("async () => { const r = await fetch(document.getElementById('pilEcran').src); return Array.from(new Uint8Array(await r.arrayBuffer())).slice(0, 4000).join(','); }").encode()).hexdigest()
        h1 = img()
        pg.click('[data-pil-mol="700"]'); pg.wait_for_timeout(2500)
        check("⬇ : la page défile (l'écran change)", img() != h1)
        # --- basculer d'onglet puis revenir
        autre = pg.evaluate("(m) => [...document.querySelectorAll('#pilOnglets [data-pil-onglet]')].map(b => b.dataset.pilOnglet).find(x => x !== m)", mien)
        if autre:
            pg.click('#pilOnglets [data-pil-onglet="%s"]' % autre); pg.wait_for_timeout(2500)
            check("basculer d'onglet", pg.evaluate("() => PIL.id") == autre and not pg.input_value("#pilUrl").startswith(URL1), pg.input_value("#pilUrl")[:50])
            pg.click('#pilOnglets [data-pil-onglet="%s"]' % mien); pg.wait_for_timeout(2500)
        pg.click("#pilChoisir"); pg.wait_for_timeout(1500)
        choisi = pg.evaluate("() => (CAP_TABS[+document.getElementById('capTab').value] || {}).url || ''")
        check("✔ Capturer cet onglet → sélectionné pour la capture", choisi.startswith(URL1), choisi)
        dep = pg.evaluate("() => document.documentElement.scrollWidth - innerWidth")
        check("aucun débordement", dep <= 0, dep)
        pg.click("[data-pil-fermer]"); pg.wait_for_timeout(2000)
        check("✕ : mon onglet fermé, ceux de Quang intacts", {o["id"] for o in onglets()["onglets"]} == avant)
        check("0 erreur JS", not errs, errs[:3])
        c.close()
    b.close()
print("\n%d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
