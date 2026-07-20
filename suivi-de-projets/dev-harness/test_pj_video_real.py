"""
Test de LECTURE VIDÉO RÉELLE in-app (point D) avec de vraies vidéos téléchargées.
mp4 (H.264) -> doit jouer dans <video> (readyState >= 1, pas de fallback).
mov (QuickTime) -> joue si codec supporté, sinon fallback propre. On rapporte le résultat factuel.
"""
import base64, http.server, socketserver, threading, time, json, sys
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
VIDEOS = Path(r"C:/Users/quang/AppData/Local/Temp/claude/D--Download-02-Apps-Web-Repo-github/dc525702-f474-48df-a5ed-c3cbab8e5499/scratchpad/pj_videos")
PORT = 8772
URL = f"http://127.0.0.1:{PORT}/index.html"


class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *a): pass


def b64(name):
    return base64.b64encode((VIDEOS / name).read_bytes()).decode()


def main():
    handler = lambda *a, **kw: H(*a, directory=str(ROOT), **kw)
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(0.3)
    mp4_b64, mov_b64 = b64("sample.mp4"), b64("sample.mov")
    R, perrs = {}, []
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(channel="msedge", headless=True)
            page = b.new_context(viewport={"width": 1440, "height": 900}).new_page()
            page.on("pageerror", lambda e: perrs.append(str(e)))
            page.goto(URL, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_selector("h1", timeout=8000)
            time.sleep(0.6)

            page.evaluate(
                """([mp4, mov]) => {
                    const toFile = (b64, name, type) => {
                        const bin = atob(b64); const arr = new Uint8Array(bin.length);
                        for (let i=0;i<bin.length;i++) arr[i]=bin.charCodeAt(i);
                        return new File([arr], name, type ? {type} : {});
                    };
                    window.__ff = {
                        'clip.mp4':   toFile(mp4, 'clip.mp4', 'video/mp4'),
                        'iphone.mov': toFile(mov, 'iphone.mov', ''),  // type vide -> détection par extension
                    };
                    getActivePjFolderHandle = () => ({ getFileHandle: async (n) => ({ getFile: async () => window.__ff[n] }) });
                    attachments[8888] = [{name:'clip.mp4'},{name:'iphone.mov'}];
                }""",
                [mp4_b64, mov_b64],
            )

            def probe(idx, label):
                page.evaluate(f"apercuPJ(8888, {idx})")
                time.sleep(2.2)  # laisse charger/décoder
                info = page.evaluate("""() => {
                    const v = document.querySelector('#preview-container video');
                    const fb = !!document.querySelector('.pj-video-fallback');
                    return {
                        video_present: !!v,
                        readyState: v ? v.readyState : null,
                        videoWidth: v ? v.videoWidth : null,
                        duration: v ? (isFinite(v.duration) ? Math.round(v.duration*10)/10 : null) : null,
                        fallback: fb
                    };
                }""")
                R[label] = info

            R["type_mp4"] = page.evaluate("detecterTypePJ(window.__ff['clip.mp4'], 'clip.mp4')")
            R["type_mov"] = page.evaluate("detecterTypePJ(window.__ff['iphone.mov'], 'iphone.mov')")
            probe(0, "mp4")
            probe(1, "mov")
            b.close()

        R["page_errors"] = perrs
        # MP4 H.264 DOIT jouer in-app : <video> présent, métadonnées chargées, pas de fallback.
        mp4_ok = (R["type_mp4"] == "video" and R["mp4"]["video_present"]
                  and (R["mp4"]["readyState"] or 0) >= 1 and not R["mp4"]["fallback"]
                  and (R["mp4"]["videoWidth"] or 0) > 0)
        # MOV : soit il joue (readyState>=1), soit fallback propre — les deux sont des succès.
        mov_ok = (R["type_mov"] == "video" and (
                  ((R["mov"]["readyState"] or 0) >= 1 and R["mov"]["video_present"])
                  or R["mov"]["fallback"]))
        ok = mp4_ok and mov_ok and not perrs
        R["mp4_joue_in_app"] = mp4_ok
        R["mov_resultat"] = "lecture in-app" if ((R["mov"]["readyState"] or 0) >= 1 and not R["mov"]["fallback"]) else ("fallback" if R["mov"]["fallback"] else "indéterminé")
        R["VERDICT"] = "PASS" if ok else "FAIL"
        print(json.dumps(R, indent=2, ensure_ascii=False))
        return 0 if ok else 1
    finally:
        httpd.shutdown(); httpd.server_close()


if __name__ == "__main__":
    sys.exit(main())
