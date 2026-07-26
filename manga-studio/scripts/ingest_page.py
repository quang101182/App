# -*- coding: utf-8 -*-
"""Ingestion d'UNE page existante : detection, decoupe, et traduction optionnelle.

C'est le dos de l'app : elle appelle ce script via `POST /manga/ingest` et recoit
du JSON pret a devenir une planche (une case par cadre detecte, une bulle vide a
chaque zone de texte).

Chaine, chaque maillon choisi parce qu'il a ete MESURE :
  - cadres + bulles  -> YOLO26n fine-tune Manga109-s (IoU 0,895 ; Pixtral coupait
    en plein milieu des dessins sur les vraies planches, cf. ROADMAP phase 3) ;
  - OCR + traduction -> Pixtral, bulle par bulle PUIS page entiere en contexte
    (6/6 bulles japonaises verticales lues et traduites le 26/07).

Sortie : un seul objet JSON sur stdout. Tout le bruit part sur stderr, sinon le
proxy recoit un melange de logs et de donnees et n'en fait rien.

Usage:
    python ingest_page.py <image|pdf> --out <dossier> [--translate] [--conf 0.25]
"""
import argparse
import base64
import io
import json
import os
import sys
import urllib.request

# Tout ce qui n'est pas le resultat va sur stderr : stdout ne porte QUE le JSON.
def log(*a):
    print(*a, file=sys.stderr, flush=True)


HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.join(HERE, "models", "manga_panel_detector_fp32.pt")
GATEWAY = "https://api-gateway.quang101182.workers.dev"
SECRET = "333a33b16f8cab5aec61eb5806eeaee332a50e1172ad1b3e3d710b3d84b9cc7b"

SYS_BULLE = (
    "You are a manga translator. You receive ONE cropped speech bubble from a manga page. "
    "Read the text exactly as printed (Japanese is often VERTICAL, right-to-left). "
    "Then translate it into natural FRENCH, keeping the register (casual, formal, shouted, whispered). "
    "If the crop contains no readable text, set text to \"\" and fr to \"\". "
    "Return STRICT JSON only:\n"
    '{"lang":"ja|en|fr|other","text":"exact transcription","fr":"traduction francaise",'
    '"tone":"neutre|crie|chuchote|pense|narration"}'
)
SYS_PAGE = (
    "You are a manga translator working on a full page. You receive the page image and a numbered "
    "list of already-transcribed bubbles in reading order. Improve the FRENCH translations so the "
    "whole page reads naturally and consistently. Return STRICT JSON only:\n"
    '{"lines":[{"id":1,"fr":"traduction amelioree"}]}'
)


def ask(sys_prompt, img_bytes, user_text, max_tokens=1400):
    b64 = base64.b64encode(img_bytes).decode()
    body = {"model": "pixtral-12b-latest", "messages": [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": [
            {"type": "text", "text": user_text},
            {"type": "image_url", "image_url": "data:image/png;base64," + b64}]}],
        "max_tokens": max_tokens, "temperature": 0.2}
    req = urllib.request.Request(GATEWAY + "/api/mistral", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + SECRET,
                                          "User-Agent": "manga-studio/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        raw = json.load(r)["choices"][0]["message"]["content"].strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw[:4].lower() == "json":
            raw = raw[4:]
    a, b = raw.find("{"), raw.rfind("}")
    return json.loads(raw[a:b + 1])


def load_page(path):
    """Image, ou 1re page d'un PDF. Un PDF de scan est le cas normal, pas l'exception."""
    from PIL import Image
    if path.lower().endswith(".pdf"):
        import fitz  # PyMuPDF
        d = fitz.open(path)
        pix = d[0].get_pixmap(dpi=200)
        return Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
    return Image.open(path).convert("RGB")


def detect(im, conf):
    from ultralytics import YOLO
    if not os.path.isfile(MODEL):
        raise SystemExit("modele absent : lance d'abord `python fetch_models.py`")
    m = YOLO(MODEL)
    names = m.names
    W, H = im.size
    r = m.predict(im, conf=conf, verbose=False)[0]
    panels, texts = [], []
    for b in r.boxes:
        x1, y1, x2, y2 = [float(v) for v in b.xyxy[0]]
        cls = names[int(b.cls[0])].lower()
        item = {"x": x1 / W, "y": y1 / H, "w": (x2 - x1) / W, "h": (y2 - y1) / H,
                "conf": round(float(b.conf[0]), 3)}
        (panels if ("panel" in cls or "frame" in cls) else texts).append(item)
    # Ordre de lecture japonais : par bande horizontale, puis DROITE -> GAUCHE.
    panels.sort(key=lambda q: (round(q["y"] * 12), -q["x"]))
    texts.sort(key=lambda q: (round(q["y"] * 8), -q["x"]))
    for i, q in enumerate(panels, 1):
        q["id"] = i
    for i, q in enumerate(texts, 1):
        q["id"] = i
    return panels, texts


def crop_panels(im, panels, outdir, base):
    """Decoupe chaque case dans le dossier du projet. Les chemins renvoyes sont
    RELATIFS a output/ : c'est ce que l'app sait servir via /manga/file."""
    os.makedirs(outdir, exist_ok=True)
    W, H = im.size
    for q in panels:
        x1, y1 = max(0, int(q["x"] * W)), max(0, int(q["y"] * H))
        x2, y2 = min(W, int((q["x"] + q["w"]) * W)), min(H, int((q["y"] + q["h"]) * H))
        if x2 - x1 < 8 or y2 - y1 < 8:
            q["file"] = ""
            continue
        name = "%s_case%02d.png" % (base, q["id"])
        im.crop((x1, y1, x2, y2)).save(os.path.join(outdir, name))
        q["file"] = name


def attach_bubbles(panels, texts):
    """Rattache chaque bulle a la case qui la contient, et convertit ses coordonnees
    de la PAGE vers la CASE — l'app ne connait que des fractions de case."""
    for t in texts:
        tcx, tcy = t["x"] + t["w"] / 2, t["y"] + t["h"] / 2
        best, bestArea = None, 1e9
        for p in panels:
            if (p["x"] <= tcx <= p["x"] + p["w"]) and (p["y"] <= tcy <= p["y"] + p["h"]):
                a = p["w"] * p["h"]
                if a < bestArea:            # la case la PLUS PETITE qui la contient
                    best, bestArea = p, a
        t["panel"] = best["id"] if best else None
        if best:
            t["bx"] = (tcx - best["x"]) / best["w"]
            t["by"] = (tcy - best["y"]) / best["h"]
            t["bw"] = min(0.94, t["w"] / best["w"] * 1.15)
            t["bh"] = min(0.60, t["h"] / best["h"] * 1.15)


def translate_bubbles(im, texts):
    from PIL import Image
    W, H = im.size
    done = 0
    for t in texts:
        pad = 6
        x1 = max(0, int(t["x"] * W) - pad); y1 = max(0, int(t["y"] * H) - pad)
        x2 = min(W, int((t["x"] + t["w"]) * W) + pad); y2 = min(H, int((t["y"] + t["h"]) * H) + pad)
        crop = im.crop((x1, y1, x2, y2))
        if crop.width < 12 or crop.height < 12:
            continue
        if max(crop.size) < 220:            # un crop minuscule est illisible pour le VLM
            r = 220 / max(crop.size)
            crop = crop.resize((int(crop.width * r), int(crop.height * r)), Image.LANCZOS)
        buf = io.BytesIO(); crop.save(buf, "PNG")
        try:
            res = ask(SYS_BULLE, buf.getvalue(), "Read and translate this bubble.")
        except Exception as e:
            log("  bulle %-2d ERREUR %s" % (t["id"], type(e).__name__)); continue
        t["src"] = (res.get("text") or "").strip()
        t["fr"] = (res.get("fr") or "").strip()
        t["lang"] = res.get("lang", "")
        # Pixtral renvoie parfois deux valeurs collees ("chuchote|pense") : on garde
        # la premiere plutot que de stocker une valeur qui n'existe pas.
        t["tone"] = str(res.get("tone", "")).split("|")[0].strip()
        if t["fr"]:
            done += 1
        log("  bulle %-2d [%s] %s -> %s" % (t["id"], t.get("lang"), t["src"][:34], t["fr"][:46]))

    # 2e passe : la page entiere en contexte. Mesuree le 26/07 : 6/6 traductions
    # ameliorees (le registre d'une bulle isolee est souvent faux).
    lines = [t for t in texts if t.get("fr")]
    if lines:
        buf = io.BytesIO(); im.save(buf, "PNG")
        listing = "\n".join("%d. [%s] %s | actuel: %s"
                            % (l["id"], l.get("lang"), l.get("src", ""), l["fr"]) for l in lines)
        try:
            fix = ask(SYS_PAGE, buf.getvalue(), "Bubbles in reading order:\n" + listing)
            by = {int(x["id"]): x["fr"] for x in fix.get("lines", []) if "id" in x}
            n = 0
            for l in lines:
                if l["id"] in by and by[l["id"]].strip() and by[l["id"]] != l["fr"]:
                    l["fr"] = by[l["id"]]; n += 1
            log("2e passe (contexte page) : %d/%d ajustees" % (n, len(lines)))
        except Exception as e:
            log("2e passe indisponible (%s)" % type(e).__name__)
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--out", required=True, help="dossier de sortie (output/<slug>)")
    ap.add_argument("--base", default="", help="prefixe des fichiers decoupes")
    ap.add_argument("--translate", action="store_true")
    ap.add_argument("--conf", type=float, default=0.25)
    a = ap.parse_args()

    im = load_page(a.image)
    W, H = im.size
    base = a.base or os.path.splitext(os.path.basename(a.image))[0]
    base = "".join(c if c.isalnum() or c in "-_" else "_" for c in base)[:40]
    log("page %dx%d" % (W, H))

    panels, texts = detect(im, a.conf)
    log("detection : %d case(s), %d bulle(s)" % (len(panels), len(texts)))
    crop_panels(im, panels, a.out, base)
    attach_bubbles(panels, texts)

    traduites = 0
    if a.translate and texts:
        traduites = translate_bubbles(im, texts)

    json.dump({"ok": True, "w": W, "h": H, "base": base,
               "panels": panels, "texts": texts, "traduites": traduites},
              sys.stdout, ensure_ascii=False)
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
