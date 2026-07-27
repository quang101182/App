# -*- coding: utf-8 -*-
"""Un semblant de MOUVEMENT par une suite d'images. Idee de Quang, 27/07.

« Est-ce possible de creer plusieurs images qui creent un semblant de mouvement,
comme les dessinateurs qui enchainent plusieurs pages ? »

Ce qu'on N'utilise PAS, et pourquoi : aucun modele video n'est installe
(animatediff_models et CogVideo sont vides), et ceux-ci produisent de toute
facon du photorealiste ou de l'anime COULEUR -- pas du manga N&B trame. Les
telecharger serait plusieurs Go pour un rendu hors sujet.

Ce qu'on fait a la place, et c'est exactement la methode des dessinateurs : des
POSES CLES. Le personnage ne change pas (meme seed, meme prompt, meme
checkpoint) ; SEULE la pose bouge, imposee par des squelettes openpose
interpoles. Deterministe, gratuit, et le mouvement est CHOISI et non subi.

Le banc mesure les deux choses qui font ou defont une animation :
  - COHERENCE : deux images voisines doivent se ressembler (meme personnage) ;
  - MOUVEMENT : elles ne doivent PAS etre identiques, sinon rien ne bouge.
Une suite d'images tres coherentes mais immobiles est un echec aussi net qu'une
suite qui bouge en changeant de personnage a chaque vignette.

Usage:
    C:/Users/quang/Documents/ComfyUI/.venv/Scripts/python.exe test_mouvement.py
    ... --images 6 --geste marche|coup
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

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
# make_pose enveloppe deja sys.stdout ; en rajouter un ferme le premier et toute
# la sortie plante sur « I/O operation on closed file » (piege deja paye le 27/07).
import make_pose as MP   # noqa: E402  (squelettes synthetiques deja outilles)

COMFY = "http://127.0.0.1:8188"
CKPT = "waiIllustriousSDXL_v170.safetensors"
OUT = os.path.join(HERE, "mouvement_out")
CLIP_HF = r"C:\Users\quang\Documents\ComfyUI\models\clip_vision\vit_h_hf"
SEED = 777777

QUAL = "masterpiece, best quality, very aesthetic, absurdres, "
BW = "monochrome, greyscale, manga, screentone, halftone, lineart, ink, high contrast, "
# « facing viewer » n'est pas decoratif : un squelette openpose est en 2D et ne
# dit PAS si le corps est vu de face ou de dos -- les memes points se lisent dans
# les deux sens. Sans cette contrainte, le personnage se retournait au milieu de
# la sequence (mesure du 27/07 : images 1-2 de dos, 3-6 de face), ce qu'aucun
# cosinus global ne signale.
SUJET = ("1boy, solo, martial artist, black gi, short dark hair, plain background, "
         "front view, facing viewer, full body, standing")
NEG = ("bad quality, worst quality, sketch, censor, watermark, signature, text, "
       "extra digits, bad hands, bad anatomy, extra limbs, color, colored, "
       "multiple views, multiple panels, from behind, back view, turned around")

# Deux postures extremes ; on interpole entre les deux. Les cles sont celles de
# CORPS (COCO-18) : on ne bouge que ce qui doit bouger.
GESTES = {
    # Un coup de poing : le bras droit part plie, finit tendu vers l'avant.
    "coup": {
        3:  ((-0.150, 0.300), (-0.020, 0.250)),   # coude droit
        4:  ((-0.170, 0.400), (0.230, 0.235)),    # main droite
        6:  ((0.115, 0.290), (0.140, 0.330)),     # coude gauche (contre-balance)
        7:  ((0.130, 0.410), (0.180, 0.430)),
    },
    # Une marche : les jambes alternent, les bras suivent.
    "marche": {
        9:  ((-0.055, 0.730), (-0.130, 0.700)),   # genou droit
        10: ((-0.058, 0.960), (-0.190, 0.930)),   # pied droit
        12: ((0.055, 0.730), (0.120, 0.740)),     # genou gauche
        13: ((0.058, 0.960), (0.150, 0.960)),     # pied gauche
        3:  ((-0.115, 0.290), (-0.150, 0.270)),
        6:  ((0.115, 0.290), (0.075, 0.320)),
    },
}


def post(p, d):
    r = urllib.request.Request(COMFY + p, data=json.dumps(d).encode(),
                               headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=300))


def get(p):
    return json.load(urllib.request.urlopen(COMFY + p, timeout=300))


def upload(path):
    nom = "manga_mv_" + os.path.basename(path)
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


def squelette_interpole(geste, t):
    """Corps de reference, avec les articulations du geste deplacees a l'instant t."""
    corps = dict(MP.CORPS)
    for cle, (depart, arrivee) in GESTES[geste].items():
        corps[cle] = (depart[0] + (arrivee[0] - depart[0]) * t,
                      depart[1] + (arrivee[1] - depart[1]) * t)
    return corps


def wf(pose_nom, seed, cn):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "CLIPTextEncode",
              "inputs": {"text": QUAL + BW + SUJET, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage",
              "inputs": {"width": 832, "height": 1216, "batch_size": 1}},
        "11": {"class_type": "ControlNetLoader",
               "inputs": {"control_net_name": "openpose-sdxl-xinsir.safetensors"}},
        "12": {"class_type": "LoadImage", "inputs": {"image": pose_nom}},
        "13": {"class_type": "ControlNetApplyAdvanced", "inputs": {
            "positive": ["2", 0], "negative": ["3", 0], "control_net": ["11", 0],
            "image": ["12", 0], "strength": cn,
            "start_percent": 0.0, "end_percent": 0.9}},
        "5": {"class_type": "KSampler", "inputs": {
            "seed": seed, "steps": 30, "cfg": 5.5, "sampler_name": "euler_ancestral",
            "scheduler": "normal", "denoise": 1.0, "model": ["1", 0],
            "positive": ["13", 0], "negative": ["13", 1], "latent_image": ["4", 0]}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage",
              "inputs": {"images": ["6", 0], "filename_prefix": "manga/_mv/mv"}},
    }


def run(label, pose_nom, seed, cn):
    t0 = time.time()
    pid = post("/prompt", {"prompt": wf(pose_nom, seed, cn),
                           "client_id": str(uuid.uuid4())})["prompt_id"]
    while True:
        h = get("/history/" + pid)
        if pid in h:
            break
        if time.time() - t0 > 300:
            print("  [%s] TIMEOUT" % label)
            return None
        time.sleep(1.5)
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


class Comparateur:
    """Cohérence entre images voisines, par embedding CLIP de l'image ENTIERE.

    Ici on veut comparer la SCENE, pas le seul visage : c'est le rendu global qui
    doit rester stable d'une vignette a l'autre.
    """

    def __init__(self):
        import numpy as np
        import torch
        from transformers import CLIPImageProcessor, CLIPVisionModelWithProjection
        self.np, self.torch = np, torch
        self.dev = "cuda" if torch.cuda.is_available() else "cpu"
        self.proc = CLIPImageProcessor.from_pretrained(CLIP_HF)
        self.m = CLIPVisionModelWithProjection.from_pretrained(
            CLIP_HF, torch_dtype=torch.float16 if self.dev == "cuda" else torch.float32
        ).to(self.dev).eval()

    def emb(self, path):
        from PIL import Image
        px = self.proc(images=Image.open(path).convert("RGB"),
                       return_tensors="pt")["pixel_values"].to(self.dev, dtype=self.m.dtype)
        with self.torch.no_grad():
            e = self.m(px).image_embeds[0].float().cpu().numpy()
        return e / (self.np.linalg.norm(e) + 1e-8)

    def sim(self, a, b):
        return float(self.np.dot(self.emb(a), self.emb(b)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", type=int, default=6)
    ap.add_argument("--geste", choices=list(GESTES), default="coup")
    ap.add_argument("--cn", type=float, default=0.9)
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    from PIL import Image

    print("=== MOUVEMENT par poses cles : %d images, geste « %s », seed FIXE %d ==="
          % (args.images, args.geste, SEED))
    fichiers = []
    for i in range(args.images):
        t = i / float(args.images - 1)
        corps = squelette_interpole(args.geste, t)
        im = MP.dessine_pts([MP.placer(corps, 0.5, 0.03, 0.985)])
        pose = os.path.join(OUT, "_pose_%02d.png" % i)
        im.save(pose)
        nom = upload(pose)
        f = run("mv_%02d" % i, nom, SEED, args.cn)
        if f:
            fichiers.append(f)

    if len(fichiers) < 3:
        print("ARRET : trop peu d'images produites.")
        return 2

    # --- planche contact + GIF ---
    ims = [Image.open(f).convert("RGB") for f in fichiers]
    h = 260
    pet = [i.resize((int(i.width * h / i.height), h)) for i in ims]
    planche = Image.new("RGB", (sum(p.width for p in pet), h), "white")
    x = 0
    for p in pet:
        planche.paste(p, (x, 0))
        x += p.width
    planche.save(os.path.join(OUT, "_planche.png"))
    gif = [i.resize((i.width // 2, i.height // 2)) for i in ims]
    gif[0].save(os.path.join(OUT, "_mouvement.gif"), save_all=True,
                append_images=gif[1:] + gif[-2:0:-1], duration=140, loop=0)

    # --- mesures ---
    c = Comparateur()
    voisins = [c.sim(fichiers[i], fichiers[i + 1]) for i in range(len(fichiers) - 1)]
    extremes = c.sim(fichiers[0], fichiers[-1])
    print("\n================= MESURES =================")
    print("cohérence entre images VOISINES : min %.3f · moy %.3f · max %.3f"
          % (min(voisins), sum(voisins) / len(voisins), max(voisins)))
    print("écart entre la PREMIERE et la DERNIERE : %.3f" % extremes)
    print("(voisines proches de 1 = meme personnage ; premiere/derniere plus bas = ca bouge)")
    stable = min(voisins) >= 0.80
    bouge = extremes <= 0.97 and min(voisins) <= 0.995
    print("\npersonnage stable d'une image a l'autre : %s" % ("OUI" if stable else "NON"))
    print("le mouvement est reellement visible      : %s" % ("OUI" if bouge else "NON"))
    print("\nVERDICT : %s" % (
        "VERT — la suite tient comme un flipbook." if (stable and bouge)
        else "ROUGE — voir les deux lignes ci-dessus."))
    print("\nplanche : %s" % os.path.join(OUT, "_planche.png"))
    print("gif     : %s" % os.path.join(OUT, "_mouvement.gif"))
    return 0 if (stable and bouge) else 1


if __name__ == "__main__":
    sys.exit(main())
