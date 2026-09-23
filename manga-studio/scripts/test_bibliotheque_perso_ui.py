# -*- coding: utf-8 -*-
"""Banc UI v2.6.0 (B4-B6) : bibliotheque personnelle -- masquer, trier, filtrer -- sur l'APP REELLE.
Le banc calcule LUI-MEME, a partir de /manga/sources et /manga/bibliotheque, ce que chaque tri / filtre doit montrer,
et le compare a ce que l'app affiche. PC 1280 px + telephone 360 px (deux contextes = deux appareils : le masquage est
commun). Remet _bibliotheque.json exactement comme avant. Usage : python test_bibliotheque_perso_ui.py [port]
"""
import json, os, sys, time, urllib.request
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banc_outils as bo

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
S = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sources"))
BIBF = os.path.join(S, "_bibliotheque.json")
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


def api(path, body=None):
    r = urllib.request.Request("http://127.0.0.1:%d%s" % (PORT, path), data=json.dumps(body).encode() if body is not None else None,
                               headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=60) as x:
        return json.load(x)


def series():
    out = {}
    for c in api("/manga/sources")["items"]:
        s = out.setdefault(c["slug"], {"slug": c["slug"], "title": c["title"], "info": c.get("serie_info") or {}, "dates": []})
        s["dates"].append(c.get("captured_at") or "")
    return out


def etiq(s):
    i = s["info"]
    return set(["g:" + g for g in i.get("genres") or []] + ["t:" + t for t in i.get("themes") or []]
               + (["p:" + i["public"]] if i.get("public") else []) + (["s:" + i["statut"]] if i.get("statut") else []))


avant = open(BIBF, encoding="utf-8").read() if os.path.isfile(BIBF) else None
CIBLE = "pepper-carrot"
try:
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        for w, h in ((1280, 900), (360, 780)):
            print("=== %d px" % w)
            c = b.new_context(viewport={"width": w, "height": h}, is_mobile=w < 400, has_touch=w < 400); pg = c.new_page(); errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto("http://127.0.0.1:%d/manga#k=%s" % (PORT, KEY)); pg.wait_for_timeout(1500)
            pg.evaluate("() => { localStorage.removeItem('manga_lib_filtres'); localStorage.removeItem('manga_lib_tri'); localStorage.removeItem('manga_serie'); }")
            pg.reload(); pg.wait_for_timeout(2500)
            pg.click('nav button[data-tab="tChap"]'); pg.wait_for_timeout(1500)
            if pg.is_visible("#btnLibBack"):
                pg.click("#btnLibBack"); pg.wait_for_timeout(500)
            check("version affichee = celle du fichier", pg.inner_text("#verBadge") == "v" + bo.version_app())
            affiche = lambda: pg.evaluate("() => [...document.querySelectorAll('#chapList > .serie-item')].map(b => b.dataset.serie)")
            masquees_aff = lambda: pg.evaluate("() => [...document.querySelectorAll('#libMasquees [data-serie]')].map(b => b.dataset.serie)")
            SER = series(); masq = set(api("/manga/bibliotheque")["masquees"])
            vis = [s for s in SER.values() if s["slug"] not in masq]
            # --- tri par defaut : recemment ajoutee
            att = [s["slug"] for s in sorted(vis, key=lambda s: (-max(time.mktime(time.strptime(d[:19], "%Y-%m-%dT%H:%M:%S")) if d else 0 for d in s["dates"]), s["title"].lower()))]
            check("tri par défaut « récemment ajoutée » = ordre calculé", affiche() == att, (affiche()[:4], att[:4]))
            pg.select_option("#libTri", "az"); pg.wait_for_timeout(400)
            import locale
            check("tri A → Z", [x.lower() for x in [SER[s]["title"] for s in affiche()]] == sorted(SER[s]["title"].lower() for s in affiche()),
                  [SER[s]["title"] for s in affiche()][:5])
            # --- masquer (depuis la barre de la serie)
            if CIBLE not in masq:
                pg.evaluate("(s) => ouvrirSerie(s)", CIBLE); pg.wait_for_timeout(1200)
                check("barre de la série : bouton « 🙈 Masquer »", "Masquer" in pg.inner_text("#btnMasquer"))
                pg.click("#btnMasquer"); pg.wait_for_timeout(1500)
                check("masquée -> retour à la liste, elle n'y est plus", not pg.is_visible("#btnLibBack") and CIBLE not in affiche(), affiche()[:3])
                check("... elle est dans « Séries masquées » (replié)", CIBLE in masquees_aff() and not pg.evaluate("() => $('libMasquees').open"))
                check("... la ligne d'état compte les masquées", "masquée" in pg.inner_text("#chapState"), pg.inner_text("#chapState"))
                check("... enregistré côté PC (commun aux appareils)", CIBLE in api("/manga/bibliotheque")["masquees"])
                pg.fill("#libRech", "pepper carrot"); pg.wait_for_timeout(700)
                txt = pg.inner_text("#chapList")
                check("recherche : les masquées ne sont pas mêlées, mais signalées", CIBLE not in affiche() and "masquées" in txt, txt[:120].replace("\n", " | "))
                pg.fill("#libRech", ""); pg.wait_for_timeout(500)
                pg.evaluate("() => { $('libMasquees').open = true; }"); pg.wait_for_timeout(200)
                pg.click('#libMasquees [data-afficher="%s"]' % CIBLE); pg.wait_for_timeout(1500)
                check("« Ré-afficher » -> de retour dans la liste", CIBLE in affiche() and CIBLE not in api("/manga/bibliotheque")["masquees"])
            # --- récemment ouverte
            dernier = [s for s in affiche()][-1]
            pg.evaluate("(s) => ouvrirSerie(s)", dernier); pg.wait_for_timeout(800); pg.click("#btnLibBack"); pg.wait_for_timeout(600)
            pg.select_option("#libTri", "ouverte"); pg.wait_for_timeout(500)
            check("tri « récemment ouverte » : la série qu'on vient d'ouvrir passe en tête", affiche()[0] == dernier, (dernier, affiche()[:3]))
            # --- filtres
            pg.click("#libFiltresBtn"); pg.wait_for_timeout(300)
            check("panneau de filtres ouvert", pg.is_visible("#libFiltres"))
            SER = series(); masq = set(api("/manga/bibliotheque")["masquees"]); vis = [s for s in SER.values() if s["slug"] not in masq]
            chips = pg.evaluate("() => [...document.querySelectorAll('#libFiltres [data-filtre]')].map(b => [b.dataset.filtre, b.textContent])")
            check("pastilles proposées = étiquettes présentes dans la bibliothèque", {k for k, _ in chips} == set().union(*[etiq(s) for s in vis]),
                  len(chips))
            bad = []
            for k, lab in chips:
                if k.startswith("t:"):                       # les themes sont replies sous « + Themes » : on deplie comme un humain
                    pg.evaluate("() => { const d = document.querySelector('#libFiltres details'); if (d) d.open = true; }")
                pg.click('#libFiltres [data-filtre="%s"]' % k); pg.wait_for_timeout(250)
                att = {s["slug"] for s in vis if k in etiq(s)}
                n_lab = int("".join(ch for ch in lab if ch.isdigit()) or -1)
                if set(affiche()) != att or n_lab != len(att):
                    bad.append((k, sorted(affiche()), sorted(att), n_lab))
                pg.click('#libActifs [data-filtre="%s"]' % k); pg.wait_for_timeout(250)
            check("chaque pastille : séries affichées == calcul du banc, et son nombre est juste (%d pastilles)" % len(chips), not bad, bad[:2])
            g = [k for k, _ in chips if k.startswith("g:")]
            if len(g) >= 2:
                a_, b_ = "g:Action", "g:Adventure"
                pg.click('#libFiltres [data-filtre="%s"]' % a_); pg.wait_for_timeout(250); pg.click('#libFiltres [data-filtre="%s"]' % b_); pg.wait_for_timeout(250)
                att = {s["slug"] for s in vis if {a_, b_} <= etiq(s)}
                check("deux pastilles = les deux à la fois (Action ET Aventure)", set(affiche()) == att, (sorted(affiche()), sorted(att)))
                check("filtres actifs rappelés sous la barre + compteur du bouton", pg.is_visible("#libActifs") and "(2)" in pg.inner_text("#libFiltresBtn"))
                pg.reload(); pg.wait_for_timeout(2500); pg.click('nav button[data-tab="tChap"]'); pg.wait_for_timeout(1200)
                check("tri et filtres gardés après rechargement (cet appareil)", pg.eval_on_selector("#libTri", "e => e.value") == "ouverte"
                      and set(affiche()) == att, pg.eval_on_selector("#libTri", "e => e.value"))
                pg.click("#libActifs [data-filtres-vider]"); pg.wait_for_timeout(400)
                check("« Tout effacer » -> toutes les séries visibles", set(affiche()) == {s["slug"] for s in vis})
            check("aucun débordement horizontal", pg.evaluate("() => document.documentElement.scrollWidth <= innerWidth + 1"))
            pg.click("#libFiltresBtn"); pg.wait_for_timeout(300)
            if pg.is_visible("#libFiltres") is False:
                pg.click("#libFiltresBtn"); pg.wait_for_timeout(300)
            pg.screenshot(path=os.path.join(os.environ.get("TEMP", "."), "biblio_%d.png" % w), full_page=False)
            check("aucune erreur JS", not errs, errs[:2])
            c.close()
        b.close()
finally:
    if avant is None:
        if os.path.isfile(BIBF):
            os.remove(BIBF)
    else:
        open(BIBF, "w", encoding="utf-8").write(avant)
print("\n%d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
