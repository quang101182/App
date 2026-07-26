# -*- coding: utf-8 -*-
"""OCR + traduction FR des bulles d'une planche.

Chaine : YOLO Manga109 donne les BOITES DE BULLES (classe `text`, deja mesuree)
-> chaque bulle est decoupee -> Pixtral lit le japonais et traduit.

Pourquoi bulle par bulle plutot qu'une seule passe sur la page : sur une page
entiere, un VLM melange l'ordre et attribue mal les repliques. En donnant une
bulle isolee, il ne peut pas se tromper de bulle -- l'attribution vient de la
detection, pas du modele de langue.

Une 2e passe donne la page complete en CONTEXTE pour rendre la traduction
coherente (registre, qui parle a qui), car une bulle isolee manque de contexte.

Usage: python manga_translate.py <image> [--yolo-json x_yolo.json]
"""
import base64, io, json, os, sys, urllib.request

GATEWAY = "https://api-gateway.quang101182.workers.dev"
SECRET = "333a33b16f8cab5aec61eb5806eeaee332a50e1172ad1b3e3d710b3d84b9cc7b"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "ingest_out")

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
    "whole page reads naturally and consistently (same speaker keeps the same register, pronouns "
    "match the visible characters, jokes and honorifics adapted rather than translated literally). "
    "Return STRICT JSON only:\n"
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
                                          "User-Agent": "manga-studio/0.1"})
    with urllib.request.urlopen(req, timeout=120) as r:
        raw = json.load(r)["choices"][0]["message"]["content"].strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw[:4].lower() == "json":
            raw = raw[4:]
    a, b = raw.find("{"), raw.rfind("}")
    return json.loads(raw[a:b + 1])


def translate(page_path, yolo_json=None):
    from PIL import Image
    base = os.path.splitext(os.path.basename(page_path))[0]
    yolo_json = yolo_json or os.path.join(OUT, base + "_yolo.json")
    im = Image.open(page_path).convert("RGB")
    W, H = im.size
    texts = json.load(open(yolo_json, encoding="utf-8"))["texts"]
    # ordre de lecture japonais : par bande horizontale, puis droite -> gauche
    texts.sort(key=lambda t: (round(t["y"] * 8), -t["x"]))
    print("%s : %d bulles detectees" % (base, len(texts)), flush=True)

    lines = []
    for i, t in enumerate(texts, 1):
        pad = 6
        x1 = max(0, int(t["x"] * W) - pad); y1 = max(0, int(t["y"] * H) - pad)
        x2 = min(W, int((t["x"] + t["w"]) * W) + pad); y2 = min(H, int((t["y"] + t["h"]) * H) + pad)
        crop = im.crop((x1, y1, x2, y2))
        if crop.width < 12 or crop.height < 12:
            continue
        # un crop minuscule est illisible pour le VLM : on l'agrandit
        if max(crop.size) < 220:
            r = 220 / max(crop.size)
            crop = crop.resize((int(crop.width * r), int(crop.height * r)), Image.LANCZOS)
        buf = io.BytesIO(); crop.save(buf, "PNG")
        try:
            res = ask(SYS_BULLE, buf.getvalue(), "Read and translate this bubble.")
        except Exception as e:
            print("  bulle %-2d ERREUR %s" % (i, type(e).__name__), flush=True); continue
        if not (res.get("text") or "").strip():
            print("  bulle %-2d (vide)" % i, flush=True); continue
        res["id"] = i
        res["box"] = [x1, y1, x2, y2]
        lines.append(res)
        print("  bulle %-2d [%s/%s] %s\n            -> %s"
              % (i, res.get("lang"), res.get("tone"), res.get("text", "")[:46], res.get("fr", "")[:70]),
              flush=True)

    if lines:
        buf = io.BytesIO(); im.save(buf, "PNG")
        listing = "\n".join("%d. [%s] %s | actuel: %s" % (l["id"], l.get("lang"), l.get("text", ""), l.get("fr", ""))
                            for l in lines)
        try:
            fix = ask(SYS_PAGE, buf.getvalue(), "Bubbles in reading order:\n" + listing)
            by = {int(x["id"]): x["fr"] for x in fix.get("lines", []) if "id" in x}
            n = 0
            for l in lines:
                if l["id"] in by and by[l["id"]].strip() and by[l["id"]] != l["fr"]:
                    l["fr_page"] = by[l["id"]]; n += 1
            print("\n2e passe (contexte page) : %d/%d traductions ajustees" % (n, len(lines)), flush=True)
        except Exception as e:
            print("\n2e passe indisponible (%s)" % type(e).__name__, flush=True)

    json.dump({"lines": lines}, open(os.path.join(OUT, base + "_translate.json"), "w",
                                     encoding="utf-8"), ensure_ascii=False, indent=1)
    return lines


if __name__ == "__main__":
    translate(sys.argv[1])
