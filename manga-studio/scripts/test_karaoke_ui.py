# -*- coding: utf-8 -*-
"""Banc UI v1.86.0 sur l'APP REELLE : karaoke du lecteur (Claymore ch.1).
- banc-k3-charon : mots cales (karaoke_mots.py) -> le mot allume = celui que donnent pages[].mots a l'instant lu ;
- banc-k3-kore   : pas calee -> repli au prorata, le mot allume avance quand meme ;
- bouton « 🎤 Karaoke » : lance le calage de banc-k3-fenrir (si pas deja fait) et attend « karaoke cale ».
PC 1280 px puis 360 px. Usage : python test_karaoke_ui.py [port] [--caler]
"""
import os, sys
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = int(([a for a in sys.argv[1:] if a.isdigit()] or ["8190"])[0])
CALER = "--caler" in sys.argv
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


ETAT = """() => { const s = [...$('lecSous').querySelectorAll('.km')], p = LEC.n.pages[LEC.i], t = $('lecAudio').currentTime;
  const on = s.findIndex(x => x.classList.contains('on'));
  let att = -1; if (p.mots) while (att + 1 < p.mots.length && p.mots[att + 1][0] <= t + 0.05) att++;
  return {n: s.length, toks: (p.narration || '').split(/\\s+/).filter(Boolean).length, on, att, t: +t.toFixed(2),
          cale: !!p.mots, dits: s.filter(x => x.classList.contains('dit')).length, txt: $('lecSous').textContent.length}; }"""


def ouvrir(pg, tag):
    pg.evaluate("(t) => ouvrirLecteur([t])", tag)


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True, args=["--autoplay-policy=no-user-gesture-required"])
    for w, h in ((1280, 900), (360, 780)):
        print("=== %d px" % w)
        c = b.new_context(viewport={"width": w, "height": h}, has_touch=(w < 400), is_mobile=(w < 400))
        pg = c.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("dialog", lambda d: d.accept())
        pg.goto("http://127.0.0.1:%d/manga#k=" % PORT + KEY); pg.wait_for_timeout(3000)
        pg.evaluate("() => { try { localStorage.removeItem('manga_kar'); localStorage.setItem('manga_mus_on', '0'); } catch {} }")
        pg.reload(); pg.wait_for_timeout(3000)
        check("version 1.86.0", "1.86.0" in pg.inner_text("#verBadge"))
        pg.click('nav button[data-tab="tChap"]'); pg.wait_for_timeout(1500)
        i = pg.evaluate("() => CHAPS.findIndex(c => c.dir === 'claymore/ch_1')")
        pg.evaluate("(i) => openChap(i)", i); pg.wait_for_timeout(3000)
        runs = pg.inner_text("#narrRuns")
        check("narration calee affichee « karaoke cale »", "karaoké calé" in runs)
        # --- narration calee
        ouvrir(pg, "banc-k3-charon"); pg.wait_for_timeout(3500)
        e = pg.evaluate(ETAT)
        check("un <span> par mot", e["n"] == e["toks"] and e["n"] > 5, e)
        check("le mot allume = celui des temps Whisper", e["cale"] and e["on"] == e["att"] and e["on"] >= 2, e)
        pg.wait_for_timeout(1500)
        e2 = pg.evaluate(ETAT)
        check("il avance avec la voix", e2["on"] > e["on"] and e2["on"] == e2["att"], (e["on"], e2["on"], e2["att"]))
        check("les mots deja dits restent allumes", e2["dits"] == max(0, e2["on"]), e2)
        pg.click("#lecNext"); pg.wait_for_timeout(2500)
        e = pg.evaluate(ETAT)
        check("page suivante : son audio repart de 0, le mot allume suit SES temps", e["on"] == e["att"] and e["t"] < 3.5 and e["n"] == e["toks"], e)
        pg.click("#lecPlay"); pg.wait_for_timeout(800)
        k0 = pg.evaluate(ETAT)["on"]; pg.wait_for_timeout(1000)
        check("pause : le mot allume ne bouge plus", pg.evaluate(ETAT)["on"] == k0, k0)
        pg.click("#lecPlay")
        pg.click("#lecKarOn"); pg.wait_for_timeout(400)
        e = pg.evaluate(ETAT)
        check("karaoke decoche -> texte simple, toujours affiche", e["n"] == 0 and e["txt"] > 10, e)
        check("choix memorise", pg.evaluate("() => localStorage.getItem('manga_kar')") == "0")
        pg.click("#lecKarOn"); pg.wait_for_timeout(400)
        check("recoche -> mots", pg.evaluate(ETAT)["n"] > 0)
        pg.click("#lecSousOn"); pg.wait_for_timeout(300)
        check("sous-titres decoches -> rien", pg.evaluate(ETAT)["txt"] == 0)
        pg.click("#lecSousOn"); pg.wait_for_timeout(300)
        dep = pg.evaluate("() => document.documentElement.scrollWidth - innerWidth")
        bb = pg.locator("#lecKarOn").bounding_box()
        check("case karaoke dans l'ecran", bb and 0 <= bb["x"] <= w - bb["width"] and dep <= 0, (bb, dep))
        pg.screenshot(path=os.path.join(os.environ.get("TEMP", "."), "kar_ui_%d.png" % w))
        pg.click("#lecFermer"); pg.wait_for_timeout(500)
        # --- narration non calee : repli au prorata
        ouvrir(pg, "banc-k3-kore"); pg.wait_for_timeout(3500)
        e = pg.evaluate(ETAT)
        if e["cale"]:
            print("  (banc-k3-kore est calee : repli non teste)")
        else:
            pg.wait_for_timeout(1500)
            e2 = pg.evaluate(ETAT)
            check("non calee : repli, le mot allume avance quand meme", e["n"] == e["toks"] and e2["on"] > e["on"] >= 0, (e["on"], e2["on"]))
        pg.click("#lecFermer"); pg.wait_for_timeout(300)
        # --- bouton de calage (une seule fois, au premier passage)
        if CALER and w > 400:
            k = pg.evaluate("() => NARRS.findIndex(n => n.tag === 'banc-k3-fenrir')")
            if pg.is_visible('#narrRuns [data-kar="%d"]' % k):
                pg.click('#narrRuns [data-kar="%d"]' % k); pg.wait_for_timeout(2500)
                check("clic -> « karaoke en calage »", "karaoké en calage" in pg.inner_text("#narrRuns"))
                for _ in range(45):
                    pg.wait_for_timeout(4000)
                    if "en calage" not in pg.inner_text("#narrRuns"):
                        break
                st = pg.evaluate("() => (NARRS.find(n => n.tag === 'banc-k3-fenrir').stats || {}).karaoke")
                check("calage fini -> stats.karaoke + bouton disparu", bool(st) and not pg.is_visible('#narrRuns [data-kar="%d"]' % k), st)
            else:
                print("  (banc-k3-fenrir deja calee : bouton non teste)")
        pg.evaluate("() => { try { localStorage.removeItem('manga_kar'); localStorage.removeItem('manga_mus_on'); } catch {} }")
        check("aucune erreur JS", not errs, errs[:2])
        c.close()
    b.close()
print("\n=== VERDICT : %d/%d" % (len(OK), len(OK) + len(KO)) + ("" if not KO else "  ECHECS : " + ", ".join(KO)))
sys.exit(1 if KO else 0)
