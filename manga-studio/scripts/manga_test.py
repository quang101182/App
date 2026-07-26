# -*- coding: utf-8 -*-
"""Essais isoles manga sur ComfyUI 8188 (checkpoint WAI-illustrious v17).

Essai 1 : une case manga N&B (tags Danbooru monochrome/screentone), base seule.
Essai 2 : MEME personnage sur 3 cases (seed fixe + bloc identite verrouille,
          cadrages/actions differents) -> c'est le test qui decide de tout.

Usage: python manga_test.py [essai1|essai2|all]
"""
import json, os, sys, time, urllib.parse, urllib.request, uuid

COMFY = "http://127.0.0.1:8188"
CKPT = "waiIllustriousSDXL_v170.safetensors"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "manga_out")
os.makedirs(OUT, exist_ok=True)

QUAL = "masterpiece, best quality, amazing quality, very aesthetic, absurdres, "
NEG = ("bad quality, worst quality, worst detail, sketch, censor, jpeg artifacts, "
       "watermark, signature, text, english text, speech bubble, extra digits, "
       "bad hands, bad anatomy, color, colored, vibrant colors")
# tags manga N&B imprime (issus des recos Illustrious/Danbooru)
BW = "monochrome, greyscale, manga, screentone, halftone, lineart, ink, high contrast, "


def post(path, payload):
    req = urllib.request.Request(COMFY + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=120))


def get(path):
    return json.load(urllib.request.urlopen(COMFY + path, timeout=120))


def workflow(pos, neg, seed, w=832, h=1216, steps=30, cfg=5.5):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": pos, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": neg, "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "5": {"class_type": "KSampler", "inputs": {
            "seed": seed, "steps": steps, "cfg": cfg, "sampler_name": "euler_ancestral",
            "scheduler": "normal", "denoise": 1.0,
            "model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0]}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage", "inputs": {"images": ["6", 0], "filename_prefix": "mangatest"}},
    }


def run(label, pos, neg, seed, **kw):
    cid = str(uuid.uuid4())
    t0 = time.time()
    r = post("/prompt", {"prompt": workflow(pos, neg, seed, **kw), "client_id": cid})
    pid = r["prompt_id"]
    while True:
        h = get("/history/" + pid)
        if pid in h:
            break
        if time.time() - t0 > 300:
            print("[%s] TIMEOUT 300s" % label, flush=True)
            return None
        time.sleep(2)
    outs = h[pid]["outputs"]
    imgs = [i for n in outs.values() for i in n.get("images", [])]
    if not imgs:
        print("[%s] AUCUNE IMAGE" % label, flush=True)
        return None
    im = imgs[0]
    url = "%s/view?filename=%s&type=%s&subfolder=%s" % (
        COMFY, urllib.parse.quote(im["filename"]), im["type"], im.get("subfolder", ""))
    dest = os.path.join(OUT, label + ".png")
    with urllib.request.urlopen(url, timeout=120) as r2, open(dest, "wb") as f:
        f.write(r2.read())
    print("[%s] OK %.0fs seed=%s -> %s (%d Ko)" % (
        label, time.time() - t0, seed, dest, os.path.getsize(dest) // 1024), flush=True)
    return dest


# ---- ESSAI 1 : rendu manga N&B, 2 variantes de reglage ----
def essai1():
    print("=== ESSAI 1 : rendu manga N&B (base WAI seule) ===", flush=True)
    scene = ("1girl, solo, short black hair, school uniform, standing on a rooftop, "
             "wind blowing, determined expression, dramatic low angle, cityscape background")
    run("e1a_bw_tags", QUAL + BW + scene, NEG, 111111)
    # variante sans les tags N&B, pour mesurer ce que les tags apportent reellement
    run("e1b_sans_tags_bw", QUAL + scene, NEG, 111111)


# ---- ESSAI 2 : meme perso sur 3 cases ----
IDENT = ("1girl, solo, 18 years old, short messy black hair, blunt bangs, "
         "sharp amber eyes, small mole under left eye, black sailor uniform with red scarf, "
         "slender build")


def essai2():
    print("=== ESSAI 2 : coherence du meme perso sur 3 cases (seed fixe) ===", flush=True)
    cases = [
        ("e2_case1_closeup", "close-up portrait, looking at viewer, neutral expression, plain background"),
        ("e2_case2_action", "full body, running through a school corridor, motion lines, dynamic angle, side view"),
        ("e2_case3_emotion", "upper body, three-quarter view, shouting, tears in eyes, dramatic shadow, speed lines background"),
    ]
    for label, act in cases:
        run(label, QUAL + BW + IDENT + ", " + act, NEG, 222222)


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("essai1", "all"):
        essai1()
    if what in ("essai2", "all"):
        essai2()
    print("=== fini -> %s ===" % OUT, flush=True)
