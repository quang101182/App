"""Test S3 — vérifie que la dropzone PJ s'affiche bien quand on ouvre le form add action."""
import http.server, socketserver, threading, time
from datetime import datetime
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
CAPTURES = Path(__file__).resolve().parent / "captures"
PORT = 8767


def safe_resize(path, max_side=1800):
    img = Image.open(path)
    w, h = img.size
    if max(w, h) > max_side:
        ratio = max_side / max(w, h)
        img.thumbnail((int(w*ratio), int(h*ratio)), Image.LANCZOS)
        img.save(path, optimize=True)
    return Image.open(path).size


class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *a): pass


handler = lambda *a, **kw: H(*a, directory=str(ROOT), **kw)
httpd = socketserver.TCPServer(("127.0.0.1", PORT), handler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
time.sleep(0.3)

stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        page = b.new_context(viewport={"width": 1440, "height": 900}).new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))

        page.goto(f"http://127.0.0.1:{PORT}/index.html", wait_until="domcontentloaded", timeout=15000)
        page.wait_for_selector("h1", timeout=8000)
        time.sleep(1)

        # Onglet Actions
        page.evaluate("ouvrirOnglet({currentTarget:document.querySelectorAll('.tablink')[2]}, 'tab3')")
        time.sleep(0.4)

        # Forcer l'affichage du form ajout (contournement read-only)
        page.evaluate("""
            document.getElementById('add-action-form').style.display = 'block';
            // Si refreshPJCount existe, l'appeler
            try { refreshPJCount('add'); } catch(e) {}
        """)
        time.sleep(0.4)

        # Capture
        cap = CAPTURES / f"pj_dropzone_add_{stamp}.png"
        page.screenshot(path=str(cap), full_page=False)
        size = safe_resize(cap)

        # Inspecter la dropzone : présence, attributs, compteur
        dz_exists = page.evaluate("!!document.getElementById('add-pj-dropzone')")
        input_multi = page.evaluate("document.getElementById('add-attachment-input')?.hasAttribute('multiple')")
        count_text = page.evaluate("document.getElementById('add-pj-count')?.textContent")
        max_const = page.evaluate("typeof MAX_ATTACHMENTS !== 'undefined' ? MAX_ATTACHMENTS : null")
        is_action_late_fn = page.evaluate("typeof isActionLate === 'function'")
        status_const = page.evaluate("typeof STATUS !== 'undefined' ? STATUS.DONE : null")

        b.close()

    print(f"capture: {cap} size={size}")
    print(f"dropzone present: {dz_exists}")
    print(f"input multiple attribute: {input_multi}")
    print(f"count badge text: {count_text}")
    print(f"MAX_ATTACHMENTS: {max_const}")
    print(f"isActionLate function: {is_action_late_fn}")
    print(f"STATUS.DONE: {status_const}")
    print(f"page errors: {errors}")
finally:
    httpd.shutdown()
    httpd.server_close()
