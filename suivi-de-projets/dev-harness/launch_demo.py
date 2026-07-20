"""
Fenêtre Edge VISIBLE sur App/suivi-de-projets/index.html, avec de vraies PJ injectées
(2 vidéos réelles + 2 images) et la galerie PJ ouverte d'emblée pour démo des points B/C/D.
Capture une preuve (MP4 en lecture) puis reste ouverte jusqu'à fermeture par l'utilisateur
ou expiration du délai (défaut 30 min).
"""
import base64, http.server, socketserver, threading, time, sys
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
CAPTURES = Path(__file__).resolve().parent / "captures"
VIDEOS = Path(r"C:/Users/quang/AppData/Local/Temp/claude/D--Download-02-Apps-Web-Repo-github/dc525702-f474-48df-a5ed-c3cbab8e5499/scratchpad/pj_videos")
PORT = 8777
URL = f"http://127.0.0.1:{PORT}/index.html"
MAX_MINUTES = int(sys.argv[1]) if len(sys.argv) > 1 else 30
PNG_1x1 = ("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")


class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *a): pass


def b64(name):
    return base64.b64encode((VIDEOS / name).read_bytes()).decode()


def main():
    handler = lambda *a, **kw: H(*a, directory=str(ROOT), **kw)
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    mp4_b64, mov_b64 = b64("sample.mp4"), b64("sample.mov")
    print(f"[demo] serveur prêt — ouverture Edge…", flush=True)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge", headless=False, args=["--start-maximized"])
            page = browser.new_context(viewport=None).new_page()
            page.goto(URL, wait_until="domcontentloaded", timeout=20000)
            time.sleep(0.8)
            page.evaluate(
                """([mp4, mov, png]) => {
                    const toFile = (b, name, type) => {
                        const bin = atob(b); const arr = new Uint8Array(bin.length);
                        for (let i=0;i<bin.length;i++) arr[i]=bin.charCodeAt(i);
                        return new File([arr], name, type ? {type} : {});
                    };
                    window.__ff = {
                        'photo-A.png': toFile(png, 'photo-A.png', 'image/png'),
                        'photo-B.png': toFile(png, 'photo-B.png', 'image/png'),
                        'video-demo.mp4': toFile(mp4, 'video-demo.mp4', 'video/mp4'),
                        'iphone-clip.mov': toFile(mov, 'iphone-clip.mov', ''),
                    };
                    getActivePjFolderHandle = () => ({ getFileHandle: async (n) => ({ getFile: async () => window.__ff[n] }) });
                    attachments[7777] = [{name:'photo-A.png'},{name:'photo-B.png'},{name:'video-demo.mp4'},{name:'iphone-clip.mov'}];
                    afficherToutesPJ(7777);
                }"""
                , [mp4_b64, mov_b64, PNG_1x1])
            time.sleep(1.2)
            # Preuve : ouvre directement la vidéo MP4 en lecture
            page.evaluate("apercuPJ(7777, 2)")
            time.sleep(2.0)
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            cap = CAPTURES / f"pj_video_live_{stamp}.png"
            try:
                page.screenshot(path=str(cap)); print(f"[demo] capture: {cap}", flush=True)
            except Exception as e:
                print(f"[demo] capture KO: {e}", flush=True)
            # revient sur la galerie pour que l'utilisateur explore
            page.evaluate("afficherToutesPJ(7777)")
            print(f"[demo] App ouverte avec PJ démo. Fenêtre active {MAX_MINUTES} min max. "
                  f"Ferme la fenêtre Edge pour terminer.", flush=True)
            deadline = time.time() + MAX_MINUTES * 60
            while browser.is_connected() and time.time() < deadline:
                time.sleep(2)
            if browser.is_connected():
                print("[demo] délai atteint — fermeture.", flush=True); browser.close()
            else:
                print("[demo] fenêtre fermée par l'utilisateur.", flush=True)
    finally:
        httpd.shutdown(); httpd.server_close()
        print("[demo] terminé.", flush=True)


if __name__ == "__main__":
    main()
