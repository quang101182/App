# -*- coding: utf-8 -*-
"""Essai 5 : rejouer EXACTEMENT l'essai 2, mais avec le LoRA de personnage.

Comparatif strict : memes 3 cadrages, meme seed (222222), meme checkpoint.
Seule difference = LoraLoader + trigger word. C'est le test qui decide si la
phase 1 de la roadmap est franchie (critere de sortie : identite >= 90 % sur
les attributs FINS -- yeux, grain de beaute, morphologie -- pas le costume,
qui tenait deja a 100 % sans LoRA).

Usage: python manga_test_lora.py <nom_du_lora.safetensors> [poids]
"""
import json, os, sys, time, urllib.parse, urllib.request, uuid

COMFY = "http://127.0.0.1:8188"
CKPT = "waiIllustriousSDXL_v170.safetensors"
TRIGGER = "zqmg1rl"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "manga_out")
os.makedirs(OUT, exist_ok=True)

QUAL = "masterpiece, best quality, amazing quality, very aesthetic, absurdres, "
BW = "monochrome, greyscale, manga, screentone, halftone, lineart, ink, high contrast, "
# Identique a l'essai 2, avec le trigger en tete.
IDENT = (TRIGGER + ", 1girl, solo, 18 years old, short messy black hair, blunt bangs, "
         "sharp amber eyes, small mole under left eye, black sailor uniform with red scarf, "
         "slender build")
NEG = ("bad quality, worst quality, worst detail, sketch, censor, jpeg artifacts, "
       "watermark, signature, text, english text, speech bubble, extra digits, "
       "bad hands, bad anatomy, color, colored, vibrant colors")
CASES = [
    ("l2_case1_closeup", "close-up portrait, looking at viewer, neutral expression, plain background"),
    ("l2_case2_action", "full body, running through a school corridor, motion lines, dynamic angle, side view"),
    ("l2_case3_emotion", "upper body, three-quarter view, shouting, tears in eyes, dramatic shadow, speed lines background"),
]


def post(p, d):
    r = urllib.request.Request(COMFY + p, data=json.dumps(d).encode(),
                               headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=180))


def get(p):
    return json.load(urllib.request.urlopen(COMFY + p, timeout=180))


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
        "7": {"class_type": "SaveImage", "inputs": {"images": ["6", 0], "filename_prefix": "loratest"}},
    }


def run(label, pos, seed, lora, w8):
    t0 = time.time()
    pid = post("/prompt", {"prompt": wf(pos, seed, lora, w8), "client_id": str(uuid.uuid4())})["prompt_id"]
    while True:
        h = get("/history/" + pid)
        if pid in h:
            break
        if time.time() - t0 > 400:
            print("[%s] TIMEOUT" % label, flush=True); return
        time.sleep(2)
    st = h[pid].get("status", {})
    if st.get("status_str") == "error":
        print("[%s] ERREUR: %s" % (label, json.dumps(st)[:300]), flush=True); return
    imgs = [i for n in h[pid]["outputs"].values() for i in n.get("images", [])]
    if not imgs:
        print("[%s] AUCUNE IMAGE" % label, flush=True); return
    im = imgs[0]
    url = "%s/view?filename=%s&type=%s&subfolder=%s" % (
        COMFY, urllib.parse.quote(im["filename"]), im["type"], im.get("subfolder", ""))
    dest = os.path.join(OUT, label + ".png")
    with urllib.request.urlopen(url, timeout=180) as r, open(dest, "wb") as f:
        f.write(r.read())
    print("[%s] OK %.0fs -> %s" % (label, time.time() - t0, os.path.basename(dest)), flush=True)


if __name__ == "__main__":
    lora = sys.argv[1]
    w8 = float(sys.argv[2]) if len(sys.argv) > 2 else 0.8
    print("=== ESSAI 5 : essai 2 rejoue AVEC le LoRA (%s @ %.2f) ===" % (lora, w8), flush=True)
    for label, act in CASES:
        run(label, QUAL + BW + IDENT + ", " + act, 222222, lora, w8)
    print("=== fini ===", flush=True)
