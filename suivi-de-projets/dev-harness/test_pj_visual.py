"""Capture de la dropzone PJ en focus."""
import http.server, socketserver, threading, time
from datetime import datetime
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
CAPTURES = Path(__file__).resolve().parent / "captures"
PORT = 8768

class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *a): pass

handler = lambda *a, **kw: H(*a, directory=str(ROOT), **kw)
httpd = socketserver.TCPServer(("127.0.0.1", PORT), handler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
time.sleep(0.3)

stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
try:
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        page = b.new_context(viewport={"width": 1440, "height": 900}).new_page()
        page.goto(f"http://127.0.0.1:{PORT}/index.html", wait_until="domcontentloaded", timeout=15000)
        page.wait_for_selector("h1", timeout=8000)
        time.sleep(0.8)
        page.evaluate("ouvrirOnglet({currentTarget:document.querySelectorAll('.tablink')[2]}, 'tab3')")
        time.sleep(0.4)
        page.evaluate("document.getElementById('add-action-form').style.display = 'block'; try { refreshPJCount('add'); } catch(e) {}")
        time.sleep(0.4)
        # Scroll to dropzone
        page.evaluate("document.getElementById('add-pj-dropzone')?.scrollIntoView({block:'center'})")
        time.sleep(0.3)
        cap = CAPTURES / f"pj_dropzone_focus_{stamp}.png"
        page.screenshot(path=str(cap), full_page=False)
        # resize si dépasse 1800 (ne devrait pas vu viewport 900)
        img = Image.open(cap)
        if max(img.size) > 1800:
            ratio = 1800 / max(img.size)
            img.thumbnail((int(img.size[0]*ratio), int(img.size[1]*ratio)), Image.LANCZOS)
            img.save(cap)
        print(f"capture: {cap}")
        b.close()
finally:
    httpd.shutdown()
    httpd.server_close()
