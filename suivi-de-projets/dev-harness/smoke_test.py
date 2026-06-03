"""
Smoke test harness pour App/suivi-de-projets/index.html

Usage:
    python smoke_test.py [--headed] [--no-server]

Lance un http.server local sur 127.0.0.1:8765, ouvre l'app dans Playwright Edge,
capture l'etat initial (4 onglets) avec resize PIL <= 1800px, et reporte les
erreurs JS / network.

Sortie: captures/{tab}_{timestamp}.png + console JSON status.
"""
import argparse
import http.server
import json
import socketserver
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HARNESS = Path(__file__).resolve().parent
CAPTURES = HARNESS / "captures"
PORT = 8765
URL = f"http://127.0.0.1:{PORT}/index.html"

MAX_SIDE = 1800


def safe_resize(path: Path, max_side: int = MAX_SIDE) -> tuple[int, int]:
    img = Image.open(path)
    w, h = img.size
    if max(w, h) > max_side:
        ratio = max_side / max(w, h)
        new_size = (int(w * ratio), int(h * ratio))
        img.thumbnail(new_size, Image.LANCZOS)
        img.save(path, optimize=True)
    return Image.open(path).size


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass


def start_server() -> socketserver.TCPServer:
    handler = lambda *a, **kw: QuietHandler(*a, directory=str(ROOT), **kw)
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def run(headed: bool = False, skip_server: bool = False):
    httpd = None
    if not skip_server:
        httpd = start_server()
        time.sleep(0.5)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    page_errors: list[str] = []
    console_errors: list[str] = []
    failed_requests: list[str] = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge", headless=not headed)
            ctx = browser.new_context(viewport={"width": 1440, "height": 900})
            page = ctx.new_page()
            page.on("pageerror", lambda e: page_errors.append(str(e)))
            page.on("console", lambda m: console_errors.append(f"{m.type}: {m.text}") if m.type == "error" else None)
            page.on("requestfailed", lambda r: failed_requests.append(f"{r.url} ({r.failure})"))

            page.goto(URL, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_selector("h1", timeout=8000)
            time.sleep(0.8)

            # Tab 1 - Tableau de bord
            cap_tb = CAPTURES / f"tb_{stamp}.png"
            page.screenshot(path=str(cap_tb), full_page=False)
            size_tb = safe_resize(cap_tb)

            # Tab 2 - Projets
            page.evaluate("ouvrirOnglet({currentTarget:document.querySelectorAll('.tablink')[1]}, 'tab2')")
            time.sleep(0.4)
            cap_p = CAPTURES / f"projets_{stamp}.png"
            page.screenshot(path=str(cap_p), full_page=False)
            size_p = safe_resize(cap_p)

            # Tab 3 - Actions
            page.evaluate("ouvrirOnglet({currentTarget:document.querySelectorAll('.tablink')[2]}, 'tab3')")
            time.sleep(0.4)
            cap_a = CAPTURES / f"actions_{stamp}.png"
            page.screenshot(path=str(cap_a), full_page=False)
            size_a = safe_resize(cap_a)

            # Tab 4 - Configuration
            page.evaluate("ouvrirOnglet({currentTarget:document.querySelectorAll('.tablink')[3]}, 'tab4')")
            time.sleep(0.4)
            cap_c = CAPTURES / f"config_{stamp}.png"
            page.screenshot(path=str(cap_c), full_page=False)
            size_c = safe_resize(cap_c)

            title = page.title()
            h1 = page.locator("h1").first.inner_text()
            ctx.close()
            browser.close()

        report = {
            "ok": not page_errors and not console_errors,
            "title": title,
            "h1": h1,
            "page_errors": page_errors,
            "console_errors": console_errors,
            "failed_requests": failed_requests,
            "captures": {
                "tableau_bord": {"path": str(cap_tb), "size": size_tb},
                "projets":       {"path": str(cap_p),  "size": size_p},
                "actions":       {"path": str(cap_a),  "size": size_a},
                "configuration": {"path": str(cap_c),  "size": size_c},
            },
        }
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if report["ok"] else 1

    finally:
        if httpd is not None:
            httpd.shutdown()
            httpd.server_close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true", help="run with visible browser")
    ap.add_argument("--no-server", action="store_true", help="assume server already running")
    args = ap.parse_args()
    sys.exit(run(headed=args.headed, skip_server=args.no_server))
