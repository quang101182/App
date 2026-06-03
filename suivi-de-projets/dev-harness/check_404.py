import http.server, socketserver, threading, time, json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PORT = 8766
NOT_FOUND = []
REQUESTED = []

class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *a): pass
    def send_error(self, code, *a, **kw):
        if code == 404:
            NOT_FOUND.append(self.path)
        super().send_error(code, *a, **kw)
    def do_GET(self):
        REQUESTED.append(self.path)
        super().do_GET()

handler = lambda *a, **kw: H(*a, directory=str(ROOT), **kw)
httpd = socketserver.TCPServer(("127.0.0.1", PORT), handler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
time.sleep(0.3)

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    page = b.new_context().new_page()
    page.goto(f"http://127.0.0.1:{PORT}/index.html", wait_until="networkidle", timeout=15000)
    time.sleep(1.5)
    b.close()

httpd.shutdown(); httpd.server_close()
print(json.dumps({"404": NOT_FOUND, "requested": REQUESTED}, indent=2))
