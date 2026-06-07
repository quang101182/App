# -*- coding: utf-8 -*-
"""QA live v1.14.0 — onglet Factory + non-régression + UX (auto-refresh retiré, persistance onglet).
Sert le dossier en local, charge dans Edge headless via Playwright, observe console + DOM factuellement.
Screenshots resize <=1800px AVANT toute lecture (feedback_screenshot_resize_harness)."""
import sys, io, os, threading, http.server
from functools import partial
from PIL import Image

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DIR = os.path.dirname(os.path.abspath(__file__))
PORT = 8777

def serve():
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=DIR)
    httpd = http.server.ThreadingHTTPServer(('127.0.0.1', PORT), handler)
    httpd.serve_forever()

def safe_shot(page, path, max_side=1700):
    page.screenshot(path=path, full_page=True)
    im = Image.open(path)
    if max(im.size) > max_side:
        r = max_side / max(im.size)
        im = im.resize((int(im.size[0]*r), int(im.size[1]*r)))
        im.save(path)
    print(f"  shot {os.path.basename(path)} -> {im.size}")

def main():
    t = threading.Thread(target=serve, daemon=True); t.start()
    from playwright.sync_api import sync_playwright
    base = f"http://127.0.0.1:{PORT}/index.html"
    errors, console_all = [], []
    with sync_playwright() as p:
        br = p.chromium.launch(channel="msedge", headless=True)
        ctx = br.new_context(viewport={"width": 430, "height": 920})  # mobile-first viewport
        # Injecter le token factory-stats (lu depuis le fichier non commité) pour valider l'intégration backend
        tok_path = os.path.join(DIR, "..", "factory-stats", "_admin_token.txt")
        fac_tok = ""
        try:
            with open(tok_path) as f: fac_tok = f.read().strip()
        except Exception: pass
        if fac_tok:
            ctx.add_init_script("try{localStorage.setItem('monitoring_factory_token','%s');}catch(e){}" % fac_tok)
            print("  [init] token factory-stats injecté")
        page = ctx.new_page()
        page.on("console", lambda m: (console_all.append(f"{m.type}:{m.text}"),
                                       errors.append(m.text) if m.type == "error" else None))
        page.on("pageerror", lambda e: errors.append("PAGEERROR:" + str(e)))
        page.route("**/favicon.ico", lambda r: r.fulfill(status=200, body=b""))  # éviter le 404 favicon (bruit local)

        # --- 1) Boot par défaut : 3 onglets présents ---
        page.goto(base, wait_until="networkidle")
        page.wait_for_timeout(800)
        tabs = page.eval_on_selector_all(".app-tab", "els => els.map(e => e.textContent.trim())")
        print("TEST 1 — onglets:", tabs)
        assert tabs == ["DictoKey", "SubWhisper Pro", "Factory"], f"onglets inattendus: {tabs}"
        # bouton Actualiser present, plus de checkbox auto-refresh
        has_refresh = page.eval_on_selector("#btnRefresh", "e => !!e") if page.query_selector("#btnRefresh") else False
        has_auto = page.query_selector("#autoRefresh") is not None
        print(f"  btnRefresh={has_refresh} autoRefreshCheckbox={has_auto}")
        assert has_refresh and not has_auto, "UX auto-refresh non retiré"

        # --- 2) Onglet Factory : rendu + vraies donnees visites ---
        page.evaluate("() => { document.getElementById('loginModal').style.display='none'; }")
        page.eval_on_selector_all(".app-tab", "els => { const f = els.find(e=>e.textContent.trim()==='Factory'); if(f) f.click(); }")
        page.wait_for_timeout(2500)  # laisser les fetch visit aboutir
        fac_visible = page.eval_on_selector("#factoryView", "e => getComputedStyle(e).display") if page.query_selector("#factoryView") else "absent"
        cards = page.eval_on_selector_all(".fac-card", "els => els.length")
        names = page.eval_on_selector_all(".fac-card .fac-name", "els => els.map(e=>e.textContent.replace(/\\s+/g,' ').trim())")
        # valeur visites du 1er compte instrumenté (aea = #1) — chercher la carte avec handle aimer
        metrics_text = page.eval_on_selector_all(".fac-card", "els => els.map(c => c.innerText.replace(/\\n+/g,' | '))")
        print(f"TEST 2 — factoryView display={fac_visible} cards={cards}")
        print("  names:", names)
        for mt in metrics_text:
            print("  CARD:", mt[:260])
        assert fac_visible == "block", "factoryView pas visible"
        assert cards == 4, f"attendu 4 cartes (TUC, AEA, #2, #3), eu {cards}"
        joined = " ".join(metrics_text)
        assert "44" in joined, "visites aea (44) absentes du rendu"
        assert "96" in joined, "visites tuc (96) absentes du rendu"
        # Intégration backend : avec token, les ventes/abonnés/revenu doivent être chiffrés (0 EUR), pas "—"
        if fac_tok:
            assert "EUR" in joined, "revenu LemonSqueezy (worker) non intégré (pas de 'EUR')"
            print("  [backend] worker factory-stats intégré : ventes/revenu/abonnés chiffrés (0 réels)")
        safe_shot(page, os.path.join(DIR, "_qa_factory_mobile.png"))

        # --- 3) Persistance onglet apres F5 ---
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(1500)
        active_after = page.evaluate("() => document.body.dataset.activeApp")
        print(f"TEST 3 — apres F5 activeApp={active_after}")
        assert active_after == "factory", "persistance onglet KO"

        # --- 4) Non-regression : retour DictoKey (login modal attendu, pas de crash) ---
        page.eval_on_selector_all(".app-tab", "els => { const d = els.find(e=>e.textContent.trim()==='DictoKey'); if(d) d.click(); }")
        page.wait_for_timeout(800)
        modal = page.eval_on_selector("#loginModal", "e => getComputedStyle(e).display")
        active_dk = page.evaluate("() => document.body.dataset.activeApp")
        print(f"TEST 4 — DictoKey activeApp={active_dk} loginModal={modal}")
        assert active_dk == "dictokey", "switch dictokey KO"

        # --- 5) Desktop viewport screenshot factory ---
        page.set_viewport_size({"width": 1280, "height": 900})
        page.eval_on_selector_all(".app-tab", "els => { const f = els.find(e=>e.textContent.trim()==='Factory'); if(f) f.click(); }")
        page.wait_for_timeout(1500)
        modal2 = page.eval_on_selector("#loginModal", "e => getComputedStyle(e).display")
        print(f"TEST 5 — retour Factory, loginModal={modal2} (doit être none)")
        assert modal2 == "none", "modale login résiduelle non fermée au retour Factory"
        safe_shot(page, os.path.join(DIR, "_qa_factory_desktop.png"))

        br.close()

    print("\n=== CONSOLE ERRORS ===")
    real = [e for e in errors if "favicon" not in e.lower()]
    for e in real: print("  ERR:", e)
    print(f"\nVERDICT: tests=5/5 passes · console_errors={len(real)} · cards=4 · visites_live=OK")
    if real:
        print("!!! ERREURS CONSOLE PRESENTES — investiguer")
        sys.exit(2)
    print("OK — zero erreur console, factory live, persistance OK, switch OK")

if __name__ == "__main__":
    main()
