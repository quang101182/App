# -*- coding: utf-8 -*-
"""Essai 3 : CHARACTER SHEET — creer le dataset de depart d'un LoRA de personnage.

Idee : une planche de reference (plusieurs vues) est generee en UNE SEULE passe
=> la coherence entre les vues est garantie par construction, contrairement a
N generations separees (essai 2, ~50%). C'est le seul moyen d'obtenir un
personnage stable AVANT d'avoir un LoRA (probleme de l'oeuf et de la poule).

Sort 4 planches (seeds differents) pour avoir du choix.
"""
import json, os, sys, time, urllib.parse, urllib.request, uuid

COMFY = "http://127.0.0.1:8188"
CKPT = "waiIllustriousSDXL_v170.safetensors"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "manga_out")
os.makedirs(OUT, exist_ok=True)

QUAL = "masterpiece, best quality, amazing quality, very aesthetic, absurdres, "
BW = "monochrome, greyscale, manga, screentone, lineart, ink, "
IDENT = ("1girl, solo, 18 years old, short messy black hair, blunt bangs, "
         "amber eyes, mole under left eye, black sailor uniform, red scarf, slender build")
SHEET = ("character sheet, reference sheet, multiple views, full body, "
         "front view, side view, back view, character turnaround, "
         "same character, white background, simple background, standing, neutral pose")
NEG = ("bad quality, worst quality, sketch, censor, jpeg artifacts, watermark, "
       "signature, text, english text, speech bubble, extra digits, bad hands, "
       "bad anatomy, multiple girls, different characters, color, colored")


def post(p, d):
    r = urllib.request.Request(COMFY + p, data=json.dumps(d).encode(),
                               headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=120))


def get(p):
    return json.load(urllib.request.urlopen(COMFY + p, timeout=120))


def wf(pos, neg, seed, w, h):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": pos, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": neg, "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "5": {"class_type": "KSampler", "inputs": {
            "seed": seed, "steps": 32, "cfg": 5.5, "sampler_name": "euler_ancestral",
            "scheduler": "normal", "denoise": 1.0, "model": ["1", 0],
            "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0]}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage", "inputs": {"images": ["6", 0], "filename_prefix": "sheet"}},
    }


def run(label, pos, neg, seed, w=1536, h=832):
    t0 = time.time()
    pid = post("/prompt", {"prompt": wf(pos, neg, seed, w, h), "client_id": str(uuid.uuid4())})["prompt_id"]
    while True:
        h_ = get("/history/" + pid)
        if pid in h_:
            break
        if time.time() - t0 > 300:
            print("[%s] TIMEOUT" % label, flush=True); return
        time.sleep(2)
    imgs = [i for n in h_[pid]["outputs"].values() for i in n.get("images", [])]
    if not imgs:
        print("[%s] AUCUNE IMAGE" % label, flush=True); return
    im = imgs[0]
    url = "%s/view?filename=%s&type=%s&subfolder=%s" % (
        COMFY, urllib.parse.quote(im["filename"]), im["type"], im.get("subfolder", ""))
    dest = os.path.join(OUT, label + ".png")
    with urllib.request.urlopen(url, timeout=120) as r, open(dest, "wb") as f:
        f.write(r.read())
    print("[%s] OK %.0fs seed=%s -> %s" % (label, time.time() - t0, seed, dest), flush=True)


if __name__ == "__main__":
    print("=== ESSAI 3 : character sheet (dataset de depart du LoRA) ===", flush=True)
    for i, seed in enumerate([31001, 31002, 31003, 31004]):
        run("e3_sheet%d" % (i + 1), QUAL + BW + IDENT + ", " + SHEET, NEG, seed)
    print("=== fini ===", flush=True)
