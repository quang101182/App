# -*- coding: utf-8 -*-
"""Essai 6 (phase 2) : CONTINUITE DE SCENE via un fond MAITRE.

Le piege pointe par les 3 voix du vote : ce n'est pas le visage qui casse une
planche, c'est le DECOR. Aucun modele n'a de memoire de scene -> 6 cases
"dans la meme piece" donnent 6 pieces differentes, et le lecteur ne suit plus.

Methode testee ici :
 1. generer UNE fois un fond maitre (le decor seul, sans personnage) ;
 2. en extraire une carte de profondeur (DepthAnythingV2) ;
 3. generer chaque case avec ControlNet depth sur cette carte + le LoRA du perso.
La geometrie du decor est alors imposee, identique d'une case a l'autre, tandis
que le prompt fait varier le personnage et son action.

Le poids du ControlNet est le curseur critique :
 - trop fort  -> le personnage ne peut plus s'inserer (le decor occupe tout) ;
 - trop faible-> le decor derive a nouveau.
On teste donc PLUSIEURS poids sur la meme case pour trouver le reglage utile.

Usage: python manga_scene.py [poids1,poids2,...]
"""
import json, os, sys, time, urllib.parse, urllib.request, uuid

COMFY = "http://127.0.0.1:8188"
CKPT = "waiIllustriousSDXL_v170.safetensors"
LORA = "_manga_test\\zqmg1rl_v1.safetensors"
CN = "depth-sdxl.safetensors"
TRIGGER = "zqmg1rl"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scene_out")
os.makedirs(OUT, exist_ok=True)

QUAL = "masterpiece, best quality, amazing quality, very aesthetic, absurdres, "
BW = "monochrome, greyscale, manga, screentone, halftone, lineart, ink, "
IDENT = (TRIGGER + ", 1girl, solo, short messy black hair, blunt bangs, amber eyes, "
         "black sailor uniform, red scarf")
# Le decor, decrit une seule fois et repete VERBATIM dans chaque case :
# repeter le prompt de scene est la parade minimale recommandee par le vote.
SCENE = ("empty school classroom, wooden desks in rows, large windows on the left, "
         "blackboard at the back, afternoon light from the left, chalk dust")
NEG = ("bad quality, worst quality, sketch, censor, watermark, signature, text, "
       "speech bubble, extra digits, bad hands, bad anatomy, multiple girls, color, colored")

# 4 cases : le personnage bouge, le decor ne doit PAS bouger.
CASES = [
    ("c1_entre", "standing near the door, looking around, full body"),
    ("c2_assise", "sitting at a desk, resting chin on hand, bored, upper body"),
    ("c3_fenetre", "standing by the window, looking outside, three-quarter view"),
    ("c4_tableau", "writing on the blackboard, back turned, looking over shoulder"),
    ("c5_couloir_fond", "walking between the desk rows, carrying books, full body"),
    ("c6_accoudee", "leaning on the teacher desk, arms crossed, facing the room"),
]


def post(p, d):
    r = urllib.request.Request(COMFY + p, data=json.dumps(d).encode(),
                               headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=180))


def get(p):
    return json.load(urllib.request.urlopen(COMFY + p, timeout=180))


def fetch(im, dest):
    url = "%s/view?filename=%s&type=%s&subfolder=%s" % (
        COMFY, urllib.parse.quote(im["filename"]), im["type"], im.get("subfolder", ""))
    with urllib.request.urlopen(url, timeout=180) as r, open(dest, "wb") as f:
        f.write(r.read())


def execute(label, nodes):
    t0 = time.time()
    pid = post("/prompt", {"prompt": nodes, "client_id": str(uuid.uuid4())})["prompt_id"]
    while True:
        h = get("/history/" + pid)
        if pid in h:
            break
        if time.time() - t0 > 400:
            print("[%s] TIMEOUT" % label, flush=True); return None
        time.sleep(2)
    st = h[pid].get("status", {})
    if st.get("status_str") == "error":
        print("[%s] ERREUR: %s" % (label, json.dumps(st)[:500]), flush=True); return None
    imgs = [i for n in h[pid]["outputs"].values() for i in n.get("images", [])]
    if not imgs:
        print("[%s] AUCUNE IMAGE" % label, flush=True); return None
    dest = os.path.join(OUT, label + ".png")
    fetch(imgs[0], dest)
    print("[%s] OK %.0fs" % (label, time.time() - t0), flush=True)
    return dest


def wf_fond(seed=70001):
    """Le decor seul, sans personnage : c'est lui qui fera autorite ensuite."""
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": QUAL + BW + SCENE + ", no humans, empty room", "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG + ", 1girl, person, human", "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": 832, "height": 1216, "batch_size": 1}},
        "5": {"class_type": "KSampler", "inputs": {
            "seed": seed, "steps": 32, "cfg": 5.5, "sampler_name": "euler_ancestral",
            "scheduler": "normal", "denoise": 1.0, "model": ["1", 0],
            "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0]}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage", "inputs": {"images": ["6", 0], "filename_prefix": "fond"}},
    }


def wf_depth(fond_name):
    return {
        "8": {"class_type": "LoadImage", "inputs": {"image": fond_name}},
        "9": {"class_type": "DepthAnythingV2Preprocessor", "inputs": {
            "image": ["8", 0], "ckpt_name": "depth_anything_v2_vitl.pth", "resolution": 1024}},
        "7": {"class_type": "SaveImage", "inputs": {"images": ["9", 0], "filename_prefix": "depth"}},
    }


def wf_case(pos, seed, depth_name, cn_w8, lora_w8=0.8):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "10": {"class_type": "LoraLoader", "inputs": {
            "lora_name": LORA, "strength_model": lora_w8, "strength_clip": lora_w8,
            "model": ["1", 0], "clip": ["1", 1]}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": pos, "clip": ["10", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["10", 1]}},
        "11": {"class_type": "ControlNetLoader", "inputs": {"control_net_name": CN}},
        "12": {"class_type": "LoadImage", "inputs": {"image": depth_name}},
        "13": {"class_type": "ControlNetApplyAdvanced", "inputs": {
            "positive": ["2", 0], "negative": ["3", 0], "control_net": ["11", 0],
            "image": ["12", 0], "strength": cn_w8, "start_percent": 0.0, "end_percent": 0.8}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": 832, "height": 1216, "batch_size": 1}},
        "5": {"class_type": "KSampler", "inputs": {
            "seed": seed, "steps": 30, "cfg": 5.5, "sampler_name": "euler_ancestral",
            "scheduler": "normal", "denoise": 1.0, "model": ["10", 0],
            "positive": ["13", 0], "negative": ["13", 1], "latent_image": ["4", 0]}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage", "inputs": {"images": ["6", 0], "filename_prefix": "case"}},
    }


def upload(path):
    b = os.path.basename(path)
    bound = "----claude" + uuid.uuid4().hex
    body = b"".join([
        ("--%s\r\nContent-Disposition: form-data; name=\"image\"; filename=\"%s\"\r\n"
         "Content-Type: image/png\r\n\r\n" % (bound, b)).encode(),
        open(path, "rb").read(),
        ("\r\n--%s\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n"
         "--%s--\r\n" % (bound, bound)).encode()])
    r = urllib.request.Request(COMFY + "/upload/image", data=body,
                               headers={"Content-Type": "multipart/form-data; boundary=" + bound})
    return json.load(urllib.request.urlopen(r, timeout=120))["name"]


if __name__ == "__main__":
    poids = [float(x) for x in (sys.argv[1].split(",") if len(sys.argv) > 1 else ["0.55"])]
    print("=== ESSAI 6 : continuite de scene (fond maitre + ControlNet depth) ===", flush=True)

    fond = execute("fond_maitre", wf_fond())
    if not fond:
        sys.exit(1)
    fn = upload(fond)
    depth = execute("depth_map", wf_depth(fn))
    if not depth:
        sys.exit(1)
    dn = upload(depth)
    print("[setup] fond='%s' depth='%s'" % (fn, dn), flush=True)

    # Temoin : les memes 4 cases SANS ControlNet, pour mesurer ce que le fond maitre apporte.
    for i, (lbl, act) in enumerate(CASES):
        execute("temoin_" + lbl, wf_case(QUAL + BW + IDENT + ", " + act + ", " + SCENE,
                                         80000 + i, dn, 0.0))
    for w in poids:
        tag = str(w).replace(".", "")
        for i, (lbl, act) in enumerate(CASES):
            execute("cn%s_%s" % (tag, lbl),
                    wf_case(QUAL + BW + IDENT + ", " + act + ", " + SCENE, 80000 + i, dn, w))
    print("=== fini -> %s ===" % OUT, flush=True)
