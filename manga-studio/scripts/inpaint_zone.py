# -*- coding: utf-8 -*-
"""Reconstruction de la zone masquee par inpainting SDXL (WAI-Illustrious).

Le masque vient du segmenteur dedie (BiSeNet de DeepMosaics). Ici on ne fait
que redessiner : Illustrious connait le style manga et l'anatomie, contrairement
au GAN de DeepMosaics entraine sur de la video photorealiste.

Rappel honnete : la zone censuree n'existe nulle part dans le fichier. On ne
"retrouve" rien, on invente une reconstruction plausible.

Usage: python inpaint_zone.py <image> <mask> [denoise] [seed]
"""
import json, os, sys, time, urllib.parse, urllib.request, uuid

COMFY = "http://127.0.0.1:8188"
CKPT = "waiIllustriousSDXL_v170.safetensors"
HERE = os.path.dirname(os.path.abspath(__file__))

# Le prompt DOIT decrire le sujet. Sans description, Illustrious improvise et
# retombe sur son attracteur par defaut (feminin) -- constate a l'essai precedent,
# meme mecanisme que le bug "chat -> femme" de Generate Studio v5.56.
POS = os.environ.get("INPAINT_POS") or (
    "masterpiece, best quality, uncensored, 1boy, male, erect penis, testicles, "
    "male genitalia, slim male body, flat chest, smooth anime shading, "
    "consistent skin tone, same art style as surrounding, clean lineart")
NEG = os.environ.get("INPAINT_NEG") or (
    "censored, mosaic censoring, bar censor, pixelated, 1girl, female, breasts, "
    "feminine body, bad anatomy, extra limbs, deformed, watermark, text, worst quality")


def post(p, d):
    r = urllib.request.Request(COMFY + p, data=json.dumps(d).encode(),
                               headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=180))


def get(p):
    return json.load(urllib.request.urlopen(COMFY + p, timeout=180))


def upload(path):
    b = os.path.basename(path)
    bd = "----c" + uuid.uuid4().hex
    body = b"".join([
        ("--%s\r\nContent-Disposition: form-data; name=\"image\"; filename=\"%s\"\r\n"
         "Content-Type: image/png\r\n\r\n" % (bd, b)).encode(),
        open(path, "rb").read(),
        ("\r\n--%s\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n--%s--\r\n"
         % (bd, bd)).encode()])
    r = urllib.request.Request(COMFY + "/upload/image", data=body,
                               headers={"Content-Type": "multipart/form-data; boundary=" + bd})
    return json.load(urllib.request.urlopen(r, timeout=120))["name"]


def wf(img, msk, denoise, seed):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": POS, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["1", 1]}},
        "8": {"class_type": "LoadImage", "inputs": {"image": img}},
        "9": {"class_type": "LoadImage", "inputs": {"image": msk}},
        "10": {"class_type": "ImageToMask", "inputs": {"image": ["9", 0], "channel": "red"}},
        "11": {"class_type": "VAEEncodeForInpaint", "inputs": {
            "pixels": ["8", 0], "vae": ["1", 2], "mask": ["10", 0], "grow_mask_by": 12}},
        "5": {"class_type": "KSampler", "inputs": {
            "seed": seed, "steps": 32, "cfg": 6.0, "sampler_name": "euler_ancestral",
            "scheduler": "normal", "denoise": denoise, "model": ["1", 0],
            "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["11", 0]}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage", "inputs": {"images": ["6", 0], "filename_prefix": "inpaint"}},
    }


if __name__ == "__main__":
    img_p, msk_p = sys.argv[1], sys.argv[2]
    dn = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
    seed = int(sys.argv[4]) if len(sys.argv) > 4 else 60001
    ni, nm = upload(img_p), upload(msk_p)
    t0 = time.time()
    pid = post("/prompt", {"prompt": wf(ni, nm, dn, seed), "client_id": str(uuid.uuid4())})["prompt_id"]
    while True:
        h = get("/history/" + pid)
        if pid in h:
            break
        if time.time() - t0 > 400:
            print("TIMEOUT"); sys.exit(1)
        time.sleep(2)
    st = h[pid].get("status", {})
    if st.get("status_str") == "error":
        print("ERREUR: " + json.dumps(st)[:600]); sys.exit(1)
    imgs = [i for n in h[pid]["outputs"].values() for i in n.get("images", [])]
    im = imgs[0]
    url = "%s/view?filename=%s&type=%s&subfolder=%s" % (
        COMFY, urllib.parse.quote(im["filename"]), im["type"], im.get("subfolder", ""))
    dest = os.path.join(HERE, "inpaint_dn%s.png" % str(dn).replace(".", ""))
    with urllib.request.urlopen(url, timeout=180) as r, open(dest, "wb") as f:
        f.write(r.read())
    print("OK %.0fs denoise=%.2f -> %s" % (time.time() - t0, dn, os.path.basename(dest)))
