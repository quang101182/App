# -*- coding: utf-8 -*-
"""Banc v2.79.3 : bandeau de fin de capture perime (Fold de Quang, 26/09 19h02 : « arretee a ta demande… Reprendre » alors que le
bilan serveur est « jusqu'au ch. 15 : fait »). APP REELLE, rien n'est ecrit (POST bloques). Verifie :
1. au RETOUR dans l'app (visibilitychange), un bandeau perime s'efface TOUT DE SUITE (pas au tour de 60 s) + ligne au journal ;
2. bilan illisible (reseau coupe) : l'erreur est ECRITE au journal, UNE fois (pas a chaque verification) ; le bandeau reste ;
3. le reseau revient : le bandeau s'efface.
Usage : python test_bandeau_capture_ui.py [port] [--mutation]   (--mutation : app v2.79.2 servie -> doit sortir ROUGE)
"""
import os, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
MUT = "--mutation" in sys.argv; sys.argv = [a for a in sys.argv if a != "--mutation"]
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8190
ICI = os.path.dirname(os.path.abspath(__file__))
OK, KO = [], []
def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail)[:200] if detail else ""), flush=True)
PERIME = """() => { CAP_ALERTE = { fin: 1, titre: 'banc', tenu: false, demande: true, arret: 'arrêtée à ta demande pendant le ch. 2',
    faits: [], jusqua: '15', reprise: { chapitre: '2', url: 'https://x/vol-2/' } }; capAlerteRendre(); }"""
RETOUR = "() => document.dispatchEvent(new Event('visibilitychange'))"
VISIBLE = "() => !$('capAlerte').hidden"

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    c = b.new_context(viewport={"width": 476, "height": 900}, is_mobile=True, has_touch=True); pg = c.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.route("**/*", lambda r: r.abort() if r.request.method == "POST" else r.continue_())
    if MUT:
        corps = open(os.path.join(ICI, "..", "manga_studio.html.bak-20260926-v2793"), encoding="utf-8").read()   # = v2.79.2
        pg.route("**/manga", lambda r, q=None: r.fulfill(status=200, content_type="text/html; charset=utf-8", body=corps))
    pg.goto("http://127.0.0.1:%d/manga#k=%s" % (PORT, KEY)); pg.wait_for_timeout(5000)
    pg.evaluate("() => { window._j = []; const l = log; log = (m, ...x) => { _j.push(String(m)); return l(m, ...x); }; }")
    # 1) retour dans l'app
    pg.evaluate(PERIME); pg.wait_for_timeout(300)
    check("bandeau périmé affiché (état du Fold reproduit)", pg.evaluate(VISIBLE))
    pg.evaluate(RETOUR); pg.wait_for_timeout(2500)
    check("retour dans l'app → effacé TOUT DE SUITE (< 3 s, sans attendre 60 s)", not pg.evaluate(VISIBLE))
    check("… et le journal le dit", any("bandeau de capture effacé" in x for x in pg.evaluate("() => _j")), pg.evaluate("() => _j.slice(-3)"))
    # 2) bilan illisible : ecrit une fois
    pg.route("**/manga/capture_derniere*", lambda r: r.abort())
    pg.evaluate(PERIME); pg.evaluate("() => { _j.length = 0; }")
    for _ in range(3):
        pg.evaluate("() => capAlerteVerifier()"); pg.wait_for_timeout(600)
    j = pg.evaluate("() => _j.filter(x => /bilan de capture illisible/.test(x))")
    check("réseau coupé : l'échec est ÉCRIT au journal, une seule fois pour 3 vérifications", len(j) == 1, j)
    check("réseau coupé : le bandeau reste (rien de sûr à afficher)", pg.evaluate(VISIBLE))
    # 3) le reseau revient
    pg.unroute("**/manga/capture_derniere*")
    pg.evaluate("() => capAlerteVerifier()"); pg.wait_for_timeout(2000)
    check("réseau revenu : le bandeau s'efface", not pg.evaluate(VISIBLE))
    check("aucune erreur JS", not errs, errs[:3])
    b.close()
print("\nVERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
