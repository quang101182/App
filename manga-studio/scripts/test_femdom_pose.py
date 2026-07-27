# -*- coding: utf-8 -*-
"""Le rapport de force s'obtient-il par la POSE plutot que par le texte ?

Mesure du 27/07 (test_duo.py, niveau n3) : demande en texte -- « femdom, the woman
stands tall looking down at the man, the man kneels at her feet » -- le modele
produit la femme debout et OUBLIE purement et simplement l'homme a genoux. 0/3.

Diagnostic pose alors : ce qui casse une scene de domination n'est pas l'anatomie
a deux corps (n1, n2 et n4 passent), c'est la MISE EN SCENE. Or un rapport de
force est une GEOMETRIE -- qui est haut, qui est bas, qui occupe le cadre. Un
squelette le dit sans ambiguite la ou une phrase echoue.

Ce banc teste exactement cette hypothese, et il peut la REFUTER :
    bras A -- texte seul                 (l'etat actuel, 0/3 attendu)
    bras B -- texte + ControlNet openpose a deux squelettes
Meme prompt, memes seeds, meme checkpoint. Seule la contrainte de pose change.

Mesure : les DEUX personnages sont-ils presents ? Compteur de visages (calibre
9/9 sur des images a une personne dans test_duo.py) -- avec sa limite connue :
il sous-compte quand les visages se chevauchent, ce qui n'est pas le cas ici,
les deux corps etant a des hauteurs differentes.

Usage:
    C:/Users/quang/Documents/ComfyUI/.venv/Scripts/python.exe test_femdom_pose.py
    ... --cn 0.8 1.0        (forces de ControlNet a essayer)
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
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "femdom_out")
POSES = os.path.join(HERE, "poses")
FACE = r"C:\Users\quang\Documents\ComfyUI\models\ultralytics\bbox\face_yolov8m.pt"
SEED = 222222

QUAL = "masterpiece, best quality, amazing quality, very aesthetic, absurdres, "
BW = "monochrome, greyscale, manga, screentone, halftone, lineart, ink, high contrast, "
CAST = ("1girl, 1boy, mature woman 28 years old, long black hair, sharp eyes, "
        "tailored black suit, adult man 30 years old, short hair, white shirt, ")
SCENE = ("femdom, the woman stands tall looking down at the man, the man kneels at "
         "her feet looking up, dramatic shadow, power dynamic, fully clothed")
NEG = ("bad quality, worst quality, worst detail, sketch, censor, jpeg artifacts, "
       "watermark, signature, text, speech bubble, extra digits, bad hands, "
       "bad anatomy, extra limbs, fused fingers, missing limb, deformed, "
       "color, colored, vibrant colors, "
       "3girls, 3boys, multiple girls, multiple boys, crowd, group, "
       "child, loli, shota, teen, young")


def post(p, d):
    r = urllib.request.Request(COMFY + p, data=json.dumps(d).encode(),
                               headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=300))


def get(p):
    return json.load(urllib.request.urlopen(COMFY + p, timeout=300))


def upload(path):
    nom = "manga_pose_" + os.path.basename(path)
    b = uuid.uuid4().hex
    tete = ("--" + b + "\r\n"
            'Content-Disposition: form-data; name="image"; filename="' + nom + '"\r\n'
            "Content-Type: image/png\r\n\r\n").encode()
    pied = ("\r\n--" + b + "\r\n"
            'Content-Disposition: form-data; name="overwrite"\r\n\r\ntrue\r\n'
            "--" + b + "--\r\n").encode()
    r = urllib.request.Request(COMFY + "/upload/image",
                               data=tete + open(path, "rb").read() + pied,
                               headers={"Content-Type":
                                        "multipart/form-data; boundary=" + b})
    return json.load(urllib.request.urlopen(r, timeout=120))["name"]


def wf(pos, seed, pose_nom=None, cn=0.8):
    g = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": pos, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage",
              "inputs": {"width": 832, "height": 1216, "batch_size": 1}},
        "5": {"class_type": "KSampler", "inputs": {
            "seed": seed, "steps": 30, "cfg": 5.5, "sampler_name": "euler_ancestral",
            "scheduler": "normal", "denoise": 1.0, "model": ["1", 0],
            "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0]}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage",
              "inputs": {"images": ["6", 0], "filename_prefix": "manga/_femdom/f"}},
    }
    if pose_nom:
        g["11"] = {"class_type": "ControlNetLoader",
                   "inputs": {"control_net_name": "openpose-sdxl-xinsir.safetensors"}}
        g["12"] = {"class_type": "LoadImage", "inputs": {"image": pose_nom}}
        g["13"] = {"class_type": "ControlNetApplyAdvanced", "inputs": {
            "positive": ["2", 0], "negative": ["3", 0], "control_net": ["11", 0],
            "image": ["12", 0], "strength": cn,
            "start_percent": 0.0, "end_percent": 0.8}}
        g["5"]["inputs"]["positive"] = ["13", 0]
        g["5"]["inputs"]["negative"] = ["13", 1]
    return g


def run(label, seed, pose_nom=None, cn=0.8):
    t0 = time.time()
    pos = QUAL + BW + CAST + SCENE
    try:
        pid = post("/prompt", {"prompt": wf(pos, seed, pose_nom, cn),
                               "client_id": str(uuid.uuid4())})["prompt_id"]
    except urllib.error.HTTPError as e:
        print("  [%s] REFUS ComfyUI : %s" % (label, e.read().decode()[:300]), flush=True)
        return None
    while True:
        h = get("/history/" + pid)
        if pid in h:
            break
        if time.time() - t0 > 400:
            print("  [%s] TIMEOUT" % label, flush=True)
            return None
        time.sleep(2)
    if h[pid].get("status", {}).get("status_str") == "error":
        print("  [%s] ERREUR" % label, flush=True)
        return None
    imgs = [i for n in h[pid]["outputs"].values() for i in n.get("images", [])]
    if not imgs:
        return None
    dest = os.path.join(OUT, label + ".png")
    url = "%s/view?filename=%s&type=%s&subfolder=%s" % (
        COMFY, urllib.parse.quote(imgs[0]["filename"]), imgs[0]["type"],
        urllib.parse.quote(imgs[0].get("subfolder", "")))
    with urllib.request.urlopen(url, timeout=300) as r, open(dest, "wb") as f:
        f.write(r.read())
    print("  [%s] %.0fs" % (label, time.time() - t0), flush=True)
    return dest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cn", nargs="*", type=float, default=[0.8, 1.0])
    ap.add_argument("--seeds", type=int, default=3)
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    pose = os.path.join(POSES, "duo_femdom_debout_genoux.png")
    if not os.path.isfile(pose):
        print("ARRET : squelette absent -> lancer d'abord : python make_pose.py")
        return 2
    from ultralytics import YOLO
    yolo = YOLO(FACE)
    compte = lambda p: len(yolo.predict(p, conf=0.35, verbose=False)[0].boxes)

    pose_nom = upload(pose)
    print("squelette : %s -> %s" % (os.path.basename(pose), pose_nom))

    bras = [("texte_seul", None, 0.0)]
    for c in args.cn:
        bras.append(("pose_cn%02d" % (c * 10), pose_nom, c))

    res = {}
    for nom, pn, cn in bras:
        print("\n-- %s" % nom)
        res[nom] = []
        for k in range(args.seeds):
            p = run("%s_s%d" % (nom, k), SEED + k * 111, pn, cn)
            if p:
                res[nom].append(compte(p))

    print("\n============== LES DEUX PERSONNAGES SONT-ILS LA ? ==============")
    print("%-14s | %-16s | %s" % ("bras", "visages par seed", "2 personnages"))
    print("-" * 58)
    for nom, _, _ in bras:
        v = res[nom]
        if not v:
            print("%-14s | (aucune image)" % nom)
            continue
        print("%-14s | %-16s | %d/%d"
              % (nom, "/".join(str(x) for x in v),
                 sum(1 for x in v if x >= 2), len(v)))
    print("-" * 58)

    base = sum(1 for x in res.get("texte_seul", []) if x >= 2)
    mieux = [n for n, _, _ in bras[1:]
             if sum(1 for x in res.get(n, []) if x >= 2) > base]
    if mieux:
        print("\nLa POSE fait apparaitre le second personnage la ou le texte echouait.")
        print("Reglage(s) qui ameliorent : %s" % ", ".join(mieux))
    else:
        print("\nAucun reglage ne fait mieux que le texte seul : l'hypothese")
        print("« le rapport de force s'impose par la pose » est REFUTEE ici.")
    print("\nimages -> %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
