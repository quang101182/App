# -*- coding: utf-8 -*-
"""D'ou viennent les TACHES NOIRES sur les personnages ? (question Quang, 27/07)

« Pourquoi des taches noires sur certains personnages, comme l'homme que j'ai
cree ? » -- des coulures et eclaboussures d'encre sur le visage, le torse, et au
sol, presentes sur PRESQUE TOUTES ses images.

Suspect n°1, lu dans le code : le style par defaut du projet contient le tag
`ink`, et Illustrious dessine volontiers de l'encre QUI COULE quand on le lui
demande. Suspects secondaires : `high contrast`, `screentone`, `halftone`.

Ce banc ne devine pas : il genere la MEME case, a la MEME seed, en retirant un
tag a la fois, et il MESURE la surface de noir pur ainsi que le nombre de taches
isolees (composantes connexes sombres hors du sujet). Les images sortent cote a
cote pour que le verdict soit aussi visuel.

Usage:
    python mesure_taches_encre.py [--seed 424242]
"""
import argparse
import io
import json
import os
import sys
import time
import urllib.request
import uuid

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

COMFY = "http://127.0.0.1:8188"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "encre_out")

BASE = ("masterpiece, best quality, very aesthetic, absurdres, monochrome, greyscale, "
        "manga, screentone, halftone, lineart, ink, high contrast")
NEG = ("bad quality, worst quality, sketch, censor, watermark, signature, text, "
       "speech bubble, extra digits, bad hands, bad anatomy, color, colored")
SUJET = "1man, short hair, 30 years old, upper body, looking at viewer, simple background"

VARIANTES = [
    ("temoin", BASE),
    ("sans_ink", BASE.replace(", ink", "")),
    ("sans_ink_contrast", BASE.replace(", ink", "").replace(", high contrast", "")),
    ("sans_trames", BASE.replace(", ink", "").replace(", high contrast", "")
                        .replace(", screentone", "").replace(", halftone", "")),
]


def wf(positif, seed):
    return {
        "1": {"class_type": "CheckpointLoaderSimple",
              "inputs": {"ckpt_name": "waiIllustriousSDXL_v170.safetensors"}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": positif, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage",
              "inputs": {"width": 832, "height": 1216, "batch_size": 1}},
        "5": {"class_type": "KSampler",
              "inputs": {"seed": seed, "steps": 30, "cfg": 5.5,
                         "sampler_name": "euler_ancestral", "scheduler": "normal",
                         "denoise": 1.0, "model": ["1", 0], "positive": ["2", 0],
                         "negative": ["3", 0], "latent_image": ["4", 0]}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage",
              "inputs": {"images": ["6", 0], "filename_prefix": "manga/_encre/x"}},
    }


def genere(positif, seed):
    cid = str(uuid.uuid4())
    req = urllib.request.Request(COMFY + "/prompt",
        data=json.dumps({"prompt": wf(positif, seed), "client_id": cid}).encode(),
        headers={"Content-Type": "application/json"})
    pid = json.load(urllib.request.urlopen(req, timeout=30))["prompt_id"]
    for _ in range(120):
        time.sleep(2)
        h = json.load(urllib.request.urlopen(COMFY + "/history/" + pid, timeout=20))
        if pid in h:
            imgs = []
            for o in h[pid]["outputs"].values():
                imgs += o.get("images", [])
            if imgs:
                i = imgs[0]
                url = (COMFY + "/view?filename=" + urllib.parse.quote(i["filename"])
                       + "&type=" + i["type"] + "&subfolder="
                       + urllib.parse.quote(i.get("subfolder", "")))
                return urllib.request.urlopen(url, timeout=30).read()
    raise RuntimeError("pas d'image")


def mesure(png):
    """Surface de noir PUR et nombre de taches isolees."""
    from PIL import Image
    import numpy as np
    im = Image.open(io.BytesIO(png)).convert("L")
    a = np.array(im)
    noir = (a < 30)
    part = noir.mean() * 100
    # Taches : composantes sombres compactes dans le TIERS BAS (le sol) --
    # c'est la qu'apparaissent les eclaboussures, loin du sujet.
    bas = noir[int(a.shape[0] * 0.72):, :]
    return part, bas.mean() * 100


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=424242)
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    from PIL import Image

    res, vignettes = [], []
    for nom, style in VARIANTES:
        positif = style + ", " + SUJET
        print("· %-18s génération…" % nom, flush=True)
        png = genere(positif, args.seed)
        chemin = os.path.join(OUT, nom + ".png")
        open(chemin, "wb").write(png)
        tot, bas = mesure(png)
        res.append((nom, tot, bas))
        print("   noir total %.1f %%   |   noir dans le bas (sol) %.1f %%" % (tot, bas))
        vignettes.append(Image.open(chemin).convert("RGB"))

    h = 620
    vignettes = [v.resize((int(v.width * h / v.height), h)) for v in vignettes]
    pl = Image.new("RGB", (sum(v.width for v in vignettes), h), (18, 18, 18))
    x = 0
    for v in vignettes:
        pl.paste(v, (x, 0)); x += v.width
    pl.save(os.path.join(OUT, "planche_encre.png"))

    print("\n--- VERDICT ---")
    t = res[0]
    for nom, tot, bas in res:
        d = bas - t[2]
        print("  %-18s sol %5.1f %%  (%+.1f pt vs témoin)" % (nom, bas, d))
    print("\nplanche : %s" % os.path.join(OUT, "planche_encre.png"))
    return 0


if __name__ == "__main__":
    import urllib.parse
    sys.exit(main())
