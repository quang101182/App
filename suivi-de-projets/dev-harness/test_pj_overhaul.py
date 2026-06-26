"""
Test fonctionnel de la refonte PJ (points A/B/C/D) — index.html.

Stub `getActivePjFolderHandle` avec de faux fichiers en mémoire (FSA API non dispo en headless),
puis exerce : galerie + cache (B), navigation préc/suiv (C), vidéo/fallback (D),
acceptation des homonymes dans le buffer (A). Verdict chiffré + captures resize <=1800px.
"""
import http.server, socketserver, threading, time, json, sys
from datetime import datetime
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
CAPTURES = Path(__file__).resolve().parent / "captures"
PORT = 8769
URL = f"http://127.0.0.1:{PORT}/index.html"

PNG_1x1 = ("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwC"
           "AAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
PDF_MIN = "data:application/pdf;base64,JVBERi0xLjQKJUVPRg=="          # %PDF-1.4 %EOF
VIDEO_FAKE = "data:application/octet-stream;base64,AAAAID=="          # octets bidons (décodage échouera)


def safe_resize(path, max_side=1800):
    img = Image.open(path)
    w, h = img.size
    if max(w, h) > max_side:
        ratio = max_side / max(w, h)
        img.thumbnail((int(w * ratio), int(h * ratio)), Image.LANCZOS)
        img.save(path, optimize=True)
    return Image.open(path).size


class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *a): pass


def main():
    handler = lambda *a, **kw: H(*a, directory=str(ROOT), **kw)
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(0.3)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    perrs, cerrs = [], []
    R = {}
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(channel="msedge", headless=True)
            page = b.new_context(viewport={"width": 1440, "height": 900}).new_page()
            page.on("pageerror", lambda e: perrs.append(str(e)))
            page.on("console", lambda m: cerrs.append(f"{m.type}: {m.text}") if m.type == "error" else None)

            page.goto(URL, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_selector("h1", timeout=8000)
            time.sleep(0.8)

            # --- Setup : faux dossier PJ + faux fichiers + une action avec 5 PJ ---
            page.evaluate(
                """async ([png, pdf, vid]) => {
                    const mk = async (name, durl, type) => {
                        const blob = await (await fetch(durl)).blob();
                        return new File([blob], name, type !== null ? {type} : {});
                    };
                    window.__ff = {
                        'a.png':      await mk('a.png', png, 'image/png'),
                        'b.png':      await mk('b.png', png, 'image/png'),
                        'doc.pdf':    await mk('doc.pdf', pdf, 'application/pdf'),
                        'clip.mp4':   await mk('clip.mp4', vid, 'video/mp4'),
                        'iphone.mov': await mk('iphone.mov', vid, null),  // type vide -> détection par extension
                    };
                    getActivePjFolderHandle = () => ({
                        getFileHandle: async (name, opts) => {
                            if (opts && opts.create === false && !window.__ff[name]) { const e = new Error('nf'); e.name = 'NotFoundError'; throw e; }
                            return { getFile: async () => window.__ff[name] };
                        }
                    });
                    attachments[9999] = [{name:'a.png'},{name:'b.png'},{name:'doc.pdf'},{name:'clip.mp4'},{name:'iphone.mov'}];
                    return Object.keys(window.__ff).length;
                }""",
                [PNG_1x1, PDF_MIN, VIDEO_FAKE],
            )

            # ---------- B : galerie + cache ----------
            page.evaluate("afficherToutesPJ(9999)")
            time.sleep(1.0)  # laisse les vignettes se charger
            R["galerie_tuiles"] = page.evaluate("document.querySelectorAll('#preview-container > div').length")
            R["galerie_imgs"] = page.evaluate("document.querySelectorAll('#preview-container img').length")
            R["cache_size_apres_galerie"] = page.evaluate("pjBlobCache.size")
            cap_gal = CAPTURES / f"pj_galerie_{stamp}.png"
            page.screenshot(path=str(cap_gal))
            R["cap_galerie"] = [str(cap_gal), list(safe_resize(cap_gal))]

            # ré-ouverture : le cache ne doit PAS recréer d'URL (taille stable)
            page.evaluate("afficherToutesPJ(9999)")
            time.sleep(0.6)
            R["cache_size_reouverture"] = page.evaluate("pjBlobCache.size")

            # ---------- C : navigation préc/suiv ----------
            page.evaluate("apercuPJ(9999, 0)")
            time.sleep(0.5)
            R["apercu0_counter"] = page.evaluate("document.getElementById('pj-counter').textContent")
            R["nav_prev_visible"] = page.evaluate("getComputedStyle(document.getElementById('pj-nav-prev')).display")
            R["nav_next_visible"] = page.evaluate("getComputedStyle(document.getElementById('pj-nav-next')).display")
            R["apercu0_img"] = page.evaluate("document.querySelectorAll('#preview-container img').length")
            cap_ap = CAPTURES / f"pj_apercu_nav_{stamp}.png"
            page.screenshot(path=str(cap_ap))
            R["cap_apercu"] = [str(cap_ap), list(safe_resize(cap_ap))]

            page.evaluate("naviguerPJ(1)")
            time.sleep(0.4)
            R["apres_suivant_counter"] = page.evaluate("document.getElementById('pj-counter').textContent")

            page.evaluate("apercuPJ(9999, 0); naviguerPJ(-1)")  # boucle : depuis 0, précédent -> dernier
            time.sleep(0.4)
            R["boucle_prec_counter"] = page.evaluate("document.getElementById('pj-counter').textContent")

            # ---------- D : vidéo + fallback ----------
            R["type_mp4"] = page.evaluate("detecterTypePJ(window.__ff['clip.mp4'], 'clip.mp4')")
            R["type_mov"] = page.evaluate("detecterTypePJ(window.__ff['iphone.mov'], 'iphone.mov')")
            page.evaluate("apercuPJ(9999, 3)")  # clip.mp4
            time.sleep(0.5)
            R["apercu_mp4_video_tag"] = page.evaluate("document.querySelectorAll('#preview-container video').length")
            time.sleep(0.8)  # laisse l'onerror se déclencher sur octets bidons -> fallback
            R["apercu_mp4_fallback"] = page.evaluate("!!document.querySelector('.pj-video-fallback')")
            R["fallback_dl_strong"] = page.evaluate(
                "(() => { const a=document.getElementById('pj-fallback-dl'); return a ? (a.getAttribute('download')||'') : null; })()")

            # PDF
            page.evaluate("apercuPJ(9999, 2)")
            time.sleep(0.4)
            R["apercu_pdf_iframe"] = page.evaluate("document.querySelectorAll('#preview-container iframe').length")

            # Bouton "Retour galerie" : doit être visible en aperçu vidéo (clic vidéo = lecture, pas retour)
            page.evaluate("apercuPJ(9999, 3)")  # clip.mp4
            time.sleep(0.4)
            R["back_btn_visible_video"] = page.evaluate("getComputedStyle(document.getElementById('pj-back-gallery')).display")
            page.evaluate("retourGaleriePJ()")
            time.sleep(0.5)
            R["retour_galerie_tuiles"] = page.evaluate("document.querySelectorAll('#preview-container > div').length")
            R["back_btn_hidden_galerie"] = page.evaluate("getComputedStyle(document.getElementById('pj-back-gallery')).display")

            page.evaluate("fermerApercuPj()")
            time.sleep(0.2)
            R["apres_fermeture_nav_state"] = page.evaluate("pjPreviewState.idx")

            # ---------- A : homonymes dans le buffer ----------
            R["homonymes"] = page.evaluate(
                """() => {
                    addActionAttachments = [];
                    const f1 = new File([new Uint8Array([1,2,3])], 'photo.png');
                    const f2 = new File([new Uint8Array([1,2,3,4,5,6,7])], 'photo.png'); // homonyme, taille différente
                    ajouterFichiersAuxPJ([f1, f2], 'add');
                    const apres2 = addActionAttachments.length;
                    ajouterFichiersAuxPJ([f1], 'add'); // vrai re-clic du MÊME fichier -> doit être ignoré
                    const apresReclic = addActionAttachments.length;
                    return { apres2, apresReclic };
                }""")

            b.close()

        R["page_errors"] = perrs
        # 404 connus et cosmétiques (favicon.ico + 2 images d'aide), hors périmètre de cette modif
        cerrs_real = [e for e in cerrs if "404" not in e and "Failed to load resource" not in e]
        R["console_errors_404_connus"] = len(cerrs) - len(cerrs_real)
        R["console_errors_reels"] = cerrs_real

        # ---- Verdict ----
        ok = (
            not perrs and not cerrs_real
            and R["galerie_tuiles"] == 5
            and R["galerie_imgs"] == 2
            and R["cache_size_reouverture"] == R["cache_size_apres_galerie"]
            and R["nav_prev_visible"] == "block" and R["nav_next_visible"] == "block"
            and R["apercu0_counter"].startswith("1 / 5")
            and R["apres_suivant_counter"].startswith("2 / 5")
            and R["boucle_prec_counter"].startswith("5 / 5")
            and R["type_mp4"] == "video" and R["type_mov"] == "video"
            # vidéo non décodable (octets bidons = cas MOV/HEVC) -> fallback + bouton télécharger
            and R["apercu_mp4_fallback"] is True and R["fallback_dl_strong"] == "clip.mp4"
            and R["apercu_pdf_iframe"] == 1
            and R["back_btn_visible_video"] != "none"
            and R["retour_galerie_tuiles"] == 5
            and R["back_btn_hidden_galerie"] == "none"
            and R["apres_fermeture_nav_state"] == -1
            and R["homonymes"]["apres2"] == 2
            and R["homonymes"]["apresReclic"] == 2
        )
        R["VERDICT"] = "PASS" if ok else "FAIL"
        print(json.dumps(R, indent=2, ensure_ascii=False))
        return 0 if ok else 1
    finally:
        httpd.shutdown(); httpd.server_close()


if __name__ == "__main__":
    sys.exit(main())
