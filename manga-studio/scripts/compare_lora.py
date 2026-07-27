# -*- coding: utf-8 -*-
"""Comparatif LoRA v1 vs v2 sur les 3 cases de la phase 1, a seed identique.

La phase 1 avait ete jugee a l'oeil sur 18 observations. Deux de ses conclusions
sont ici remises a l'epreuve avec des mesures reproductibles :

  - « le grain de beaute ne s'apprend pas » (1/3) -> juge par Pixtral, image par
    image, avec une question fermee. On saura si le v2 le tient.
  - « le LoRA tire vers le plan rapproche » -> mesure par la TAILLE DU VISAGE
    detecte sur la case « full body ». Un plan plus large = un visage plus petit.
    Aucune interpretation : c'est un rapport de pixels.

Le seed est identique entre les deux LoRA : la seule variable est le LoRA.

Usage:
    python compare_lora.py                      (v1 vs v2, poids 0.8)
    python compare_lora.py --a v1 --b v2 --w8 0.8
"""
import argparse
import base64
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import uuid

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

COMFY = "http://127.0.0.1:8188"
CKPT = "waiIllustriousSDXL_v170.safetensors"
TRIGGER = "zqmg1rl"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "compare_out")
FACE = r"C:\Users\quang\Documents\ComfyUI\models\ultralytics\bbox\face_yolov8m.pt"
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
SEED = 222222

QUAL = "masterpiece, best quality, amazing quality, very aesthetic, absurdres, "
BW = "monochrome, greyscale, manga, screentone, halftone, lineart, ink, high contrast, "
# Le grain de beaute est RETIRE du design (decision Quang, 27/07 : « les petits
# details, on s'en fiche totalement ; ce qui compte, c'est la qualite de
# l'ensemble et les details les plus importants »). On ne mesure donc plus un
# attribut qui n'appartient plus au personnage.
IDENT = (TRIGGER + ", 1girl, solo, 18 years old, short messy black hair, blunt bangs, "
         "sharp amber eyes, black sailor uniform with red scarf, slender build")
NEG = ("bad quality, worst quality, worst detail, sketch, censor, jpeg artifacts, "
       "watermark, signature, text, english text, speech bubble, extra digits, "
       "bad hands, bad anatomy, color, colored, vibrant colors")
CASES = [
    ("case1_closeup", "close-up portrait, looking at viewer, neutral expression, plain background"),
    ("case2_fullbody", "full body, running through a school corridor, motion lines, dynamic angle, side view"),
    ("case3_emotion", "upper body, three-quarter view, shouting, tears in eyes, dramatic shadow, speed lines background"),
]

JUGE = (
    "You are grading a black-and-white manga illustration of a character. "
    "Answer ONLY about what you can actually SEE. Return STRICT JSON:\n"
    '{"mole":true|false,   // a small dark beauty mark on the cheek just under one eye\n'
    ' "eyes":"amber|red|brown|black|other|not visible",\n'
    ' "framing":"closeup|bust|cowboy|full body",\n'
    ' "face_readable":true|false}  // is the face drawn with clear, resolved features'
)


def post(p, d):
    r = urllib.request.Request(COMFY + p, data=json.dumps(d).encode(),
                               headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=300))


def get(p):
    return json.load(urllib.request.urlopen(COMFY + p, timeout=300))


def fetch(im, dest):
    url = "%s/view?filename=%s&type=%s&subfolder=%s" % (
        COMFY, urllib.parse.quote(im["filename"]), im["type"],
        urllib.parse.quote(im.get("subfolder", "")))
    with urllib.request.urlopen(url, timeout=300) as r, open(dest, "wb") as f:
        f.write(r.read())


def wf(pos, seed, lora, w8):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "10": {"class_type": "LoraLoader", "inputs": {
            "lora_name": lora, "strength_model": w8, "strength_clip": w8,
            "model": ["1", 0], "clip": ["1", 1]}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": pos, "clip": ["10", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["10", 1]}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": 832, "height": 1216, "batch_size": 1}},
        "5": {"class_type": "KSampler", "inputs": {
            "seed": seed, "steps": 30, "cfg": 5.5, "sampler_name": "euler_ancestral",
            "scheduler": "normal", "denoise": 1.0, "model": ["10", 0],
            "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0]}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage", "inputs": {"images": ["6", 0], "filename_prefix": "manga/_cmp/cmp"}},
    }


def run(label, pos, seed, lora, w8):
    t0 = time.time()
    pid = post("/prompt", {"prompt": wf(pos, seed, lora, w8), "client_id": str(uuid.uuid4())})["prompt_id"]
    while True:
        h = get("/history/" + pid)
        if pid in h:
            break
        if time.time() - t0 > 400:
            print("[%s] TIMEOUT" % label); return None
        time.sleep(2)
    st = h[pid].get("status", {})
    if st.get("status_str") == "error":
        print("[%s] ERREUR %s" % (label, json.dumps(st)[:300])); return None
    imgs = [i for n in h[pid]["outputs"].values() for i in n.get("images", [])]
    if not imgs:
        return None
    dest = os.path.join(OUT, label + ".png")
    fetch(imgs[0], dest)
    print("  [%s] %.0fs" % (label, time.time() - t0), flush=True)
    return dest


def taille_visage(path, modele):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    H = im.size[1]
    r = modele.predict(im, conf=0.35, verbose=False)[0]
    best = 0.0
    for b in r.boxes:
        y1, y2 = float(b.xyxy[0][1]), float(b.xyxy[0][3])
        best = max(best, (y2 - y1) / H)
    return best


def juge(path):
    """Verdict d'un juge EXTERIEUR, avec une question fermee. La phase 1 avait ete
    notee a l'oeil ; ici la meme question est posee de la meme facon a chaque image."""
    b64 = base64.b64encode(open(path, "rb").read()).decode()
    body = {"model": "pixtral-12b-latest", "messages": [
        {"role": "system", "content": JUGE},
        {"role": "user", "content": [
            {"type": "text", "text": "Grade this image."},
            {"type": "image_url", "image_url": "data:image/png;base64," + b64}]}],
        "max_tokens": 300, "temperature": 0.0}
    req = urllib.request.Request(GATEWAY + "/api/mistral", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + SECRET,
                                          "User-Agent": "manga-studio/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = json.load(r)["choices"][0]["message"]["content"].strip()
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw[:4].lower() == "json":
                raw = raw[4:]
        a, b = raw.find("{"), raw.rfind("}")
        return json.loads(raw[a:b + 1])
    except Exception as e:
        return {"erreur": type(e).__name__}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", default="_manga_test\\zqmg1rl_v1.safetensors")
    ap.add_argument("--b", default="_manga_test\\zqmg1rl_v2.safetensors")
    ap.add_argument("--w8", type=float, default=0.8)
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    from ultralytics import YOLO
    modele = YOLO(FACE)

    print("=== COMPARATIF LoRA — meme seed (%d), meme checkpoint, poids %.2f ===" % (SEED, args.w8))
    resultats = {}
    for nom, lora in (("v1", args.a), ("v2", args.b)):
        print("\n-- %s (%s)" % (nom, lora))
        resultats[nom] = []
        for i, (label, act) in enumerate(CASES):
            pos = QUAL + BW + IDENT + ", " + act
            p = run("%s_%s" % (nom, label), pos, SEED, lora, args.w8)
            if not p:
                resultats[nom].append(None); continue
            resultats[nom].append({"label": label, "path": p,
                                   "visage": round(taille_visage(p, modele), 4),
                                   "juge": juge(p)})

    print("\n================= COMPARATIF =================")
    print("%-16s | %-28s | %-28s" % ("case", "v1", "v2"))
    print("-" * 80)
    for i, (label, _) in enumerate(CASES):
        a = resultats["v1"][i]; b = resultats["v2"][i]
        def desc(x):
            if not x: return "(echec)"
            j = x["juge"]
            return "visage %.3f · %s · yeux %s · %s" % (
                x["visage"], "grain OUI" if j.get("mole") else "grain non",
                str(j.get("eyes"))[:9], str(j.get("framing"))[:9])
        print("%-16s | %s" % (label, desc(a)))
        print("%-16s | %s" % ("", desc(b)))
        print("-" * 80)

    def compte(n, cle):
        return sum(1 for x in resultats[n] if x and x["juge"].get(cle))
    print("\ngrain de beaute vu   : v1 %d/3   v2 %d/3" % (compte("v1", "mole"), compte("v2", "mole")))
    print("visage lisible       : v1 %d/3   v2 %d/3"
          % (compte("v1", "face_readable"), compte("v2", "face_readable")))
    fb = 1   # case2 = full body
    if resultats["v1"][fb] and resultats["v2"][fb]:
        v1f, v2f = resultats["v1"][fb]["visage"], resultats["v2"][fb]["visage"]
        print("\n--- BIAIS DE CADRAGE (case 'full body') ---")
        print("taille du visage : v1 %.3f  ->  v2 %.3f" % (v1f, v2f))
        if v2f < v1f * 0.9:
            print("=> le v2 cadre PLUS LARGE : la reserve n°2 recule.")
        elif v2f > v1f * 1.1:
            print("=> le v2 cadre PLUS SERRE : la reserve n°2 EMPIRE.")
        else:
            print("=> pas d'ecart significatif (<10 %) : la reserve n°2 reste ouverte.")
    print("\nimages -> %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
