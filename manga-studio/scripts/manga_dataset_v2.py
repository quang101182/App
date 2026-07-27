# -*- coding: utf-8 -*-
"""Dataset v2 : corriger les DEUX reserves du LoRA v1, dont on connait la cause.

La planche contact du dataset v1 les explique toutes les deux :

 1. **Le grain de beaute est absent de presque toutes les images.** Il etait bien
    dans le prompt, mais le remplacement de visage par ReActor l'effacait. Le 1/3
    du LoRA v1 n'etait donc PAS une limite du modele (« les micro-details ne
    s'apprennent pas ») : c'etait un dataset muet sur ce point. On ne peut pas
    apprendre ce qu'on ne montre pas.

 2. **Le cadrage est uniforme a ~92 %** (que des bustes). Et ce n'etait pas un
    accident : le script v1 le dit lui-meme, « cadrages volontairement limites au
    plan rapproche ». Le verrou etait ReActor, qui echoue sur un visage trop petit.

Ce verrou a saute : on a maintenant le LoRA v1, qui tient l'identite a 89 % SANS
ReActor. On genere donc directement avec lui, et un **FaceDetailer** (Impact Pack,
face_yolov8m) re-rend le visage a haute resolution sur les plans larges — ce qui
etait precisement impossible avant.

Usage: python manga_dataset_v2.py [N]
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import uuid

COMFY = "http://127.0.0.1:8188"
CKPT = "waiIllustriousSDXL_v170.safetensors"
LORA = "_manga_test\\zqmg1rl_v1.safetensors"
TRIGGER = "zqmg1rl"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "dataset_v2")
os.makedirs(OUT, exist_ok=True)

QUAL = "masterpiece, best quality, amazing quality, very aesthetic, absurdres, "
BW = "monochrome, greyscale, manga, screentone, halftone, lineart, ink, "
# Grain de beaute RETIRE du design (decision Quang, 27/07). L'accentuation a 1.4
# n'avait de toute facon donne que 3/12 images le montrant : le detail ne valait
# pas la peine qu'on le poursuive.
IDENT = (TRIGGER + ", 1girl, solo, short messy black hair, blunt bangs, amber eyes, "
         "black sailor uniform, red scarf")
NEG = ("bad quality, worst quality, sketch, censor, jpeg artifacts, watermark, "
       "signature, text, speech bubble, extra digits, bad hands, bad anatomy, "
       "multiple girls, 2girls, blurry, out of focus, color, colored")

# 28 variations, ETALEES sur 4 distances de cadrage (7 chacune) au lieu de 92 %
# de bustes. Le negatif de cadrage pousse activement hors du plan rapproche :
# sans lui, Illustrious retombe sur le buste quoi qu'on demande.
CADRAGES = [
    ("closeup",     "portrait, closeup, face focus",            "full body, cowboy shot, wide shot"),
    ("upperbody",   "upper body",                               "full body, closeup, face focus"),
    ("cowboy",      "cowboy shot, from mid-thigh up",           "closeup, portrait, face focus, full body"),
    ("fullbody",    "full body, standing, head to toe visible", "closeup, portrait, upper body, cowboy shot"),
]
ACTIONS = [
    ("looking at viewer, neutral expression", "plain background"),
    ("three-quarter view, slight smile",      "screentone background"),
    ("looking away, thoughtful",              "classroom background"),
    ("arms crossed, confident smirk",         "school corridor background"),
    ("surprised, wide eyes",                  "speed lines background"),
    ("angry, furrowed brows",                 "dark screentone background"),
    ("walking, side view",                    "street background"),
]


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


def wf(pos, neg, seed):
    """Generation + passe FaceDetailer. C'est elle qui rend les plans larges
    entrainables : sans elle, le visage n'a pas assez de pixels et le LoRA
    apprendrait un visage flou."""
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "10": {"class_type": "LoraLoader", "inputs": {
            "lora_name": LORA, "strength_model": 0.8, "strength_clip": 0.8,
            "model": ["1", 0], "clip": ["1", 1]}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": pos, "clip": ["10", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": neg, "clip": ["10", 1]}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": 832, "height": 1216, "batch_size": 1}},
        "5": {"class_type": "KSampler", "inputs": {
            "seed": seed, "steps": 30, "cfg": 5.5, "sampler_name": "euler_ancestral",
            "scheduler": "normal", "denoise": 1.0, "model": ["10", 0],
            "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0]}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "20": {"class_type": "UltralyticsDetectorProvider",
               "inputs": {"model_name": "bbox/face_yolov8m.pt"}},
        "21": {"class_type": "FaceDetailer", "inputs": {
            "image": ["6", 0], "model": ["10", 0], "clip": ["10", 1], "vae": ["1", 2],
            "positive": ["2", 0], "negative": ["3", 0], "bbox_detector": ["20", 0],
            "guide_size": 512, "guide_size_for": True, "max_size": 1024,
            "seed": seed + 1, "steps": 24, "cfg": 5.5,
            "sampler_name": "euler_ancestral", "scheduler": "normal",
            "denoise": 0.45, "feather": 5, "noise_mask": True, "force_inpaint": True,
            "bbox_threshold": 0.45, "bbox_dilation": 10, "bbox_crop_factor": 3.0,
            "sam_detection_hint": "center-1", "sam_dilation": 0, "sam_threshold": 0.93,
            "sam_bbox_expansion": 0, "sam_mask_hint_threshold": 0.7,
            "sam_mask_hint_use_negative": "False", "drop_size": 10,
            "wildcard": "", "cycle": 1}},
        "7": {"class_type": "SaveImage", "inputs": {
            "images": ["21", 0], "filename_prefix": "manga/_dsv2/ds2"}},
    }


def execute(label, nodes):
    t0 = time.time()
    pid = post("/prompt", {"prompt": nodes, "client_id": str(uuid.uuid4())})["prompt_id"]
    while True:
        h = get("/history/" + pid)
        if pid in h:
            break
        if time.time() - t0 > 600:
            print("[%s] TIMEOUT" % label, flush=True); return None
        time.sleep(2)
    st = h[pid].get("status", {})
    if st.get("status_str") == "error":
        print("[%s] ERREUR %s" % (label, json.dumps(st)[:400]), flush=True); return None
    imgs = [i for n in h[pid]["outputs"].values() for i in n.get("images", [])]
    if not imgs:
        print("[%s] AUCUNE IMAGE" % label, flush=True); return None
    return imgs[0], time.time() - t0


def main():
    n_par_cadrage = int(sys.argv[1]) if len(sys.argv) > 1 else len(ACTIONS)
    print("=== DATASET v2 : %d cadrages x %d actions = %d images ==="
          % (len(CADRAGES), n_par_cadrage, len(CADRAGES) * n_par_cadrage), flush=True)
    print("LoRA v1 comme ancre d'identite (plus de ReActor) + FaceDetailer", flush=True)

    i, ok = 0, 0
    for nom, cad, cad_neg in CADRAGES:
        for j in range(n_par_cadrage):
            action, fond = ACTIONS[j % len(ACTIONS)]
            pos = QUAL + BW + IDENT + ", " + cad + ", " + action + ", " + fond
            neg = NEG + ", " + cad_neg
            r = execute("%s_%d" % (nom, j), wf(pos, neg, 500000 + i * 37))
            if r:
                img, dt = r
                base = "ds2_%02d" % i
                fetch(img, os.path.join(OUT, base + ".png"))
                # Caption : trigger + style + CE QUI VARIE (cadrage, action, fond).
                # Jamais un attribut constant : le trigger doit l'absorber.
                cap = "%s, 1girl, solo, monochrome, greyscale, manga, %s, %s, %s" % (
                    TRIGGER, cad, action, fond)
                with open(os.path.join(OUT, base + ".txt"), "w", encoding="utf-8") as f:
                    f.write(cap)
                ok += 1
                print("  [%02d] %-10s %-34s %.0fs" % (i, nom, action[:34], dt), flush=True)
            i += 1
    print("=== %d/%d images -> %s ===" % (ok, i, OUT), flush=True)
    return 0 if ok == i else 1


if __name__ == "__main__":
    sys.exit(main())
