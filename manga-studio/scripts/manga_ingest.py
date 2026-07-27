# -*- coding: utf-8 -*-
"""Phase 3 : INGESTION d'une planche (scan / capture / page de PDF).

Chaine : fichier -> image(s) de page -> Pixtral -> (a) decoupage en cases,
(b) fiche d'analyse de style reutilisable comme prompt.

Reutilise le meme chemin que le proxy Generate Studio (`/api/mistral` du gateway
Cloudflare, modele pixtral-12b-latest) : la brique vision existe deja, on ne fait
que lui donner un autre travail.

Usage:
  python manga_ingest.py panels <image|pdf> [page]   -> bounding-box des cases + decoupe
  python manga_ingest.py style  <image>              -> fiche de style + prompt reutilisable
"""
import base64, io, json, os, sys, urllib.request

GATEWAY = "https://api-gateway.quang101182.workers.dev"
# ⚠ Le secret du gateway NE VIT PLUS DANS LE CODE (28/07). Ce depot est PUBLIC,
# et le secret y a ete versionne en clair du 26 au 28/07 : l'historique git en garde
# la trace, donc il doit etre CHANGE cote gateway, pas seulement retire d'ici.
def _secret():
    s = os.environ.get('WORKER_SECRET', '').strip()
    if s:
        return s
    base = os.path.join(os.path.expanduser('~'), 'Documents', 'ComfyUI')
    for nom in ('.worker_secret', '.studio_secret'):
        p = os.path.join(base, nom)
        if os.path.isfile(p):
            v = open(p, encoding='utf-8').read().strip()
            if v:
                return v
    raise SystemExit('ARRET : secret du gateway introuvable. Definir WORKER_SECRET '
                     'dans l environnement, ou le poser dans ComfyUI/.worker_secret.')


SECRET = _secret()
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "ingest_out")
os.makedirs(OUT, exist_ok=True)

SYS_PANELS = (
    "You are a manga layout analyst. You receive ONE manga page. "
    "Identify every PANEL (case). A panel is a framed drawing area; gutters are the white gaps between them. "
    "Panels may be borderless, tilted, overlapping, or bleed to the page edge - include them anyway. "
    "Do NOT list speech bubbles or sound effects as panels. "
    "Return STRICT JSON only, no prose:\n"
    '{"page_type":"grid|irregular|splash","reading_order":"rtl|ltr",'
    '"panels":[{"id":1,"x":0.0,"y":0.0,"w":0.0,"h":0.0,"desc":"3 words"}]}\n'
    "x,y,w,h are FRACTIONS of the page (0..1), x,y = top-left corner. "
    "List panels in reading order (Japanese manga = right-to-left, top-to-bottom)."
)

SYS_STYLE = (
    "You are a manga art director. You receive ONE manga image. "
    "Describe its GRAPHIC STYLE precisely enough that a text-to-image model could reproduce the LOOK "
    "(never the characters, never the story - style only). "
    "Return STRICT JSON only, no prose:\n"
    '{"line":"line weight and inking","screentone":"tone density and type","contrast":"blacks vs whites",'
    '"shading":"how shadows are done","framing":"typical camera angles","mood":"atmosphere",'
    '"era":"visual era e.g. 80s shonen, modern seinen",'
    '"danbooru_tags":["tag1","tag2"],'
    '"reusable_prompt":"a ready-to-use english prompt describing ONLY the style, comma-separated tags"}'
)


def ask(sys_prompt, img_bytes, mime="image/png", max_tokens=1200):
    b64 = base64.b64encode(img_bytes).decode()
    body = {
        "model": "pixtral-12b-latest",
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": [
                {"type": "text", "text": "Analyse this page and return the JSON."},
                {"type": "image_url", "image_url": "data:" + mime + ";base64," + b64},
            ]},
        ],
        "max_tokens": max_tokens, "temperature": 0.2,
    }
    req = urllib.request.Request(
        GATEWAY + "/api/mistral", data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + SECRET,
                 "User-Agent": "manga-studio/0.1"})
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.load(r)
    raw = d["choices"][0]["message"]["content"].strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw[:4].lower() == "json":
            raw = raw[4:]
    a, b = raw.find("{"), raw.rfind("}")
    return json.loads(raw[a:b + 1])


def load_page(path, page=1):
    """Accepte une image ou un PDF (page N). Renvoie (bytes_png, PIL.Image)."""
    from PIL import Image
    if path.lower().endswith(".pdf"):
        import fitz  # PyMuPDF
        doc = fitz.open(path)
        p = doc[page - 1]
        pix = p.get_pixmap(dpi=200)
        data = pix.tobytes("png")
        return data, Image.open(io.BytesIO(data))
    im = Image.open(path).convert("RGB")
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue(), im


def cmd_panels(path, page=1):
    data, im = load_page(path, page)
    W, H = im.size
    print("page %dx%d" % (W, H), flush=True)
    res = ask(SYS_PANELS, data)
    panels = res.get("panels", [])
    print("type=%s ordre=%s cases=%d" % (res.get("page_type"), res.get("reading_order"), len(panels)), flush=True)
    base = os.path.splitext(os.path.basename(path))[0]
    kept = 0
    for p in panels:
        # Pixtral rend parfois des boites qui debordent de la page (x+w > 1) ou
        # degenerees : on borne AUX DEUX BOUTS avant de decouper, sinon PIL leve
        # "tile cannot extend outside image".
        x1 = max(0, min(W - 1, int(p["x"] * W)))
        y1 = max(0, min(H - 1, int(p["y"] * H)))
        x2 = max(x1 + 1, min(W, x1 + int(p["w"] * W)))
        y2 = max(y1 + 1, min(H, y1 + int(p["h"] * H)))
        w, h = x2 - x1, y2 - y1
        if w < 40 or h < 40:
            print("  case %s IGNOREE (trop petite %dx%d)" % (p.get("id"), w, h), flush=True)
            continue
        x, y = x1, y1
        kept += 1
        crop = im.crop((x1, y1, x2, y2))
        dest = os.path.join(OUT, "%s_case%02d.png" % (base, p.get("id", 0)))
        crop.save(dest)
        print("  case %-2s %-22s %4d,%4d %4dx%4d" % (p.get("id"), (p.get("desc") or "")[:22], x, y, w, h), flush=True)
    print("=> %d/%d cases decoupees" % (kept, len(panels)), flush=True)
    with open(os.path.join(OUT, base + "_panels.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    return res


def cmd_style(path):
    data, _ = load_page(path)
    res = ask(SYS_STYLE, data)
    print(json.dumps(res, ensure_ascii=False, indent=1), flush=True)
    base = os.path.splitext(os.path.basename(path))[0]
    with open(os.path.join(OUT, base + "_style.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    return res


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "panels":
        cmd_panels(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 1)
    elif cmd == "style":
        cmd_style(sys.argv[2])
    else:
        print(__doc__)
