# -*- coding: utf-8 -*-
"""Banc UI « voix » (v1.82.0) sur l'APP REELLE : « Autre voix » (meme texte, nouvelle voix, SANS relire les
pages) + voix memorisee par serie. Cout reel : la voix seule (mesure 0,011 $/page). Verdict chiffre en sortie.

Usage : python test_voix_ui.py [tag_source]     (defaut : k3-sans-serie, OPM 301 -> cree kimi-fenrir)
        python test_voix_ui.py --memoire         (ne regenere RIEN : teste seulement la memoire des voix)
"""
import json, os, sys, time
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
SRC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sources"))
MEMOIRE_SEULE = "--memoire" in sys.argv
TAG = next((a for a in sys.argv[1:] if not a.startswith("--")), "k3-sans-serie")
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


def ouvrir_chapitre(pg, serie, rang):
    pg.click('nav button[data-tab="tChap"]'); pg.wait_for_timeout(1500)
    if pg.is_visible("#btnLibBack"):
        pg.click("#btnLibBack"); pg.wait_for_timeout(400)
    pg.click('#chapList [data-serie="%s"]' % serie); pg.wait_for_timeout(800)
    pg.click("#chapList [data-chap] >> nth=%d" % rang)
    pg.wait_for_selector("#chapDetail:not([hidden])", timeout=15000); pg.wait_for_timeout(2500)


def autre_voix(pg):
    i = pg.evaluate("(t) => NARRS.findIndex(n => n.tag === t)", TAG)
    check("narration source presente (%s)" % TAG, i >= 0)
    pg.once("dialog", lambda d: d.accept())
    if pg.query_selector("#narrRuns details.narr-essais"):
        pg.click("#narrRuns details.narr-essais summary")
    t0 = time.time()
    pg.click('#narrRuns [data-revoix="%d"]' % i); pg.wait_for_timeout(2000)
    fin = None
    while time.time() - t0 < 600:                                # la voix seule : ~1 min mesuree
        n = pg.evaluate("() => NARRS.find(n => n.tag === 'kimi-fenrir')")
        if n and n.get("etat") in ("fini", "echec"):
            fin = n
            break
        pg.wait_for_timeout(5000)
    check("nouvelle narration kimi-fenrir terminee", fin is not None and fin["etat"] == "fini", (fin or {}).get("etat"))
    nj = json.load(open(os.path.join(SRC, "one-punch-man", "ch_301", "narration", "kimi-fenrir", "narration.json"),
                        encoding="utf-8"))
    st = nj.get("stats") or {}
    check("texte REPRIS (reuse = %s), pas de nouvelle lecture" % nj.get("reuse_vision"), nj.get("reuse_vision") == TAG)
    check("voix Fenrir, pages audio > 0", nj.get("voice") == "Fenrir" and (fin or {}).get("audio", 0) > 0, (fin or {}).get("audio"))
    print("  cout de ce run : voix %.3f $ + recit %.3f $ en %.0f s" % (st.get("cout_tts", 0), st.get("cout_recit", 0), time.time() - t0))


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    pg = b.new_context(viewport={"width": 1280, "height": 900}).new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("http://127.0.0.1:8190/manga#k=" + KEY); pg.wait_for_timeout(3000)
    pg.evaluate("() => { for (const k of Object.keys(localStorage)) if (k.startsWith('manga_voix_')) localStorage.removeItem(k); }")
    ouvrir_chapitre(pg, "one-punch-man", 1)                      # ch 301
    pg.select_option("#narrVoice", "Fenrir"); pg.wait_for_timeout(300)   # choisir = memoriser pour la serie
    if not MEMOIRE_SEULE:
        autre_voix(pg)
    ouvrir_chapitre(pg, "one-punch-man", 0)                      # ch 300 : meme serie
    check("ch.300 (meme serie) : Fenrir repris", pg.eval_on_selector("#narrVoice", "s => s.value") == "Fenrir")
    ouvrir_chapitre(pg, "claymore", 0)
    v = pg.eval_on_selector("#narrVoice", "s => s.value")
    check("Claymore (autre serie, rien de memorise) : voix par defaut Charon", v == "Charon", v)
    check("aucune erreur JS", not errs, errs[:2])
    b.close()
print("\n=== VERDICT : %d/%d" % (len(OK), len(OK) + len(KO)) + ("" if not KO else "  ECHECS : " + ", ".join(KO)))
sys.exit(1 if KO else 0)
