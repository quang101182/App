# -*- coding: utf-8 -*-
"""Banc v2.14.1 : « ✕ Fermer la fenetre » ferme LE navigateur dedie vise, et lui seul.

On ne ferme PAS la vraie fenetre de capture de Quang (ses onglets seraient perdus) : un Edge JETABLE lance par
Playwright joue son role (un Edge neuf lance a la main n'ouvrait pas son port de pilotage : 3 essais, abandonne).
La fonction reelle cdp_mini.fenetre(..., "fermer") est appelee, branchee sur la session navigateur de ce jetable.
Verifie : le jetable se ferme ; la vraie fenetre de capture (port 9223) est intacte.
"""
import os, sys, time, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import cdp_mini as cm
from playwright.sync_api import sync_playwright

OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""), flush=True)


def vivant(port):
    try:
        urllib.request.urlopen("http://127.0.0.1:%d/json/version" % port, timeout=2).read()
        return True
    except Exception:
        return False


class Session:                                   # une session CDP Playwright avec l'interface d'Onglet (.cmd)
    def __init__(self, s): self.s = s
    def __enter__(self): return self
    def __exit__(self, *e): return False
    def cmd(self, m, **k): return self.s.send(m, k)


quang_avant = vivant(9223)
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    b.new_page().goto("about:blank")
    check("Edge jetable ouvert", b.is_connected())
    cm._navigateur = lambda: Session(b.new_browser_cdp_session())
    try:
        r = cm.fenetre("ws://jetable/devtools/page/x", "fermer")
    except Exception as e:                       # la liaison peut se couper PENDANT la fermeture : attendu
        r = {"ferme": True, "coupure": str(e)[:60]}
    check("l'action rend « fermé »", r.get("ferme") is True, r)
    time.sleep(2)
    try:                                         # vraiment ferme : il ne peut plus ouvrir de page
        b.new_page(); ferme = False
    except Exception:
        ferme = True
    check("Edge jetable FERMÉ (il ne peut plus ouvrir de page)", ferme, "connecté=%s" % b.is_connected())
check("la vraie fenêtre de capture n'a pas été touchée", vivant(9223) == quang_avant, "vivante" if quang_avant else "déjà fermée")
print("\n%d/%d" % (len(OK), len(OK) + len(KO)), flush=True)
sys.exit(1 if KO else 0)
