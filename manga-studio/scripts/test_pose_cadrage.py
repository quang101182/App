# -*- coding: utf-8 -*-
"""Le ControlNet openpose obtient-il ce que les prompts n'obtiennent pas ?

Mesure du 27/07 : ni le dataset (28 images etalees) ni les prompts (« full body »
+ negatif anti-gros-plan) n'atteignent un vrai plan en pied. Le modele de base
resiste. Reste une seule piste serieuse : imposer la POSE, donc le cadrage.

Ce banc compare, a seed identique, le meme prompt AVEC et SANS openpose, et
mesure la seule chose qui tranche : la taille du visage dans l'image.
Plus le visage est petit, plus le plan est large. Aucun jugement, un rapport.

Reference (mesuree) : sans openpose, un prompt « full body » donne 0,20-0,23.
Un VRAI plan en pied est en dessous de 0,09.

Usage: python test_pose_cadrage.py [--w8 0.6,0.8,1.0]
"""
import argparse
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
LORA = "_manga_test\\zqmg1rl_v1.safetensors"
CN = "openpose-sdxl-xinsir.safetensors"
TRIGGER = "zqmg1rl"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "pose_out")
POSES = os.path.join(HERE, "poses")
FACE = r"C:\Users\quang\Documents\ComfyUI\models\ultralytics\bbox\face_yolov8m.pt"
SEED = 222222

QUAL = "masterpiece, best quality, amazing quality, very aesthetic, absurdres, "
BW = "monochrome, greyscale, manga, screentone, halftone, lineart, ink, "
IDENT = (TRIGGER + ", 1girl, solo, short messy black hair, blunt bangs, amber eyes, "
         "black sailor uniform, red scarf")
NEG = ("bad quality, worst quality, sketch, censor, watermark, signature, text, "
       "speech bubble, extra digits, bad hands, bad anatomy, multiple girls, "
       "color, colored")
ACTION = "full body, standing in a school corridor, looking at viewer"


def post(p, d):
    r = urllib.request.Request(COMFY + p, data=json.dumps(d).encode(),
                               headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=300))


def get(p):
    return json.load(urllib.request.urlopen(COMFY + p, timeout=300))


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


def fetch(im, dest):
    url = "%s/view?filename=%s&type=%s&subfolder=%s" % (
        COMFY, urllib.parse.quote(im["filename"]), im["type"],
        urllib.parse.quote(im.get("subfolder", "")))
    with urllib.request.urlopen(url, timeout=300) as r, open(dest, "wb") as f:
        f.write(r.read())


def wf(pos, seed, pose_name=None, cn_w8=0.0):
    g = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "10": {"class_type": "LoraLoader", "inputs": {
            "lora_name": LORA, "strength_model": 0.8, "strength_clip": 0.8,
            "model": ["1", 0], "clip": ["1", 1]}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": pos, "clip": ["10", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["10", 1]}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": 832, "height": 1216, "batch_size": 1}},
        "5": {"class_type": "KSampler", "inputs": {
            "seed": seed, "steps": 30, "cfg": 5.5, "sampler_name": "euler_ancestral",
            "scheduler": "normal", "denoise": 1.0, "model": ["10", 0],
            "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0]}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage", "inputs": {"images": ["6", 0], "filename_prefix": "manga/_pose/p"}},
    }
    if pose_name:
        g["11"] = {"class_type": "ControlNetLoader", "inputs": {"control_net_name": CN}}
        g["12"] = {"class_type": "LoadImage", "inputs": {"image": pose_name}}
        g["13"] = {"class_type": "ControlNetApplyAdvanced", "inputs": {
            "positive": ["2", 0], "negative": ["3", 0], "control_net": ["11", 0],
            "image": ["12", 0], "strength": cn_w8, "start_percent": 0.0, "end_percent": 0.9}}
        g["5"]["inputs"]["positive"] = ["13", 0]
        g["5"]["inputs"]["negative"] = ["13", 1]
    return g


def run(label, nodes):
    t0 = time.time()
    pid = post("/prompt", {"prompt": nodes, "client_id": str(uuid.uuid4())})["prompt_id"]
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
    return dest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--w8", default="0.6,0.8,1.0")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    poids = [float(x) for x in a.w8.split(",")]

    from ultralytics import YOLO
    from PIL import Image
    modele = YOLO(FACE)

    def visage(p):
        im = Image.open(p).convert("RGB"); H = im.size[1]
        r = modele.predict(im, conf=0.35, verbose=False)[0]
        return max([0.0] + [(float(b.xyxy[0][3]) - float(b.xyxy[0][1])) / H for b in r.boxes])

    pose = os.path.join(POSES, "pose_fullbody.png")
    if not os.path.isfile(pose):
        print("ECHEC: lance d'abord `python make_pose.py`"); return 2
    nom = upload(pose)
    pos = QUAL + BW + IDENT + ", " + ACTION

    print("=== CADRAGE : le prompt seul contre openpose (meme seed %d) ===" % SEED)
    res = []
    p = run("sans_openpose", wf(pos, SEED))
    v0 = visage(p) if p else 0
    print("  sans openpose            visage %.3f" % v0)
    res.append(("sans openpose", 0.0, v0))
    for w in poids:
        p = run("openpose_%.1f" % w, wf(pos, SEED, nom, w))
        v = visage(p) if p else 0
        print("  openpose @ %.1f           visage %.3f  %s"
              % (w, v, "(aucun visage detecte)" if v == 0 else ""))
        res.append(("openpose %.1f" % w, w, v))

    print("\n================= VERDICT =================")
    print("reference mesuree : prompt seul = 0,20-0,23 · vrai plan en pied < 0,09")
    for nom_, w, v in res:
        etat = "plan en pied" if 0 < v < 0.09 else ("americain" if v < 0.17 else "buste/gros plan")
        print("  %-16s visage %.3f   %s" % (nom_, v, etat if v else "non detecte"))
    best = min([r for r in res[1:] if r[2] > 0], key=lambda r: r[2], default=None)
    if best and v0 > 0:
        print("\nmeilleur reglage : %s -> %.3f (contre %.3f sans) = %.0f %% plus large"
              % (best[0], best[2], v0, 100 * (1 - best[2] / v0)))
        print("=> %s" % ("openpose OBTIENT le plan en pied que le prompt seul ne donne pas."
                         if best[2] < 0.09 else
                         "openpose elargit, mais n'atteint toujours pas le vrai plan en pied."))
    print("\nimages -> %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
