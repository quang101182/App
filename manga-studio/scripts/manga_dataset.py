# -*- coding: utf-8 -*-
"""Essai 4 : construire le DATASET d'un LoRA de personnage (bootstrap ReActor).

Probleme mesure aux essais 2 et 3 :
 - essai 2 (seed fixe + prompt verrouille) : identite tenue a ~50 % seulement ;
 - essai 3 (character sheet) : costume coherent mais VISAGES NON RESOLUS (trop petits).
=> Aucun des deux ne fournit un dataset entrainable.

Bootstrap retenu :
 1. un PORTRAIT DE REFERENCE en gros plan (visage net, resolu) ;
 2. N images variees (cadrage/pose/expression) -- incoherentes entre elles, c'est attendu ;
 3. ReActor impose le visage de reference sur chacune -> dataset coherent ;
 4. (suite) kohya entraine le LoRA la-dessus, ReActor ne sert plus ensuite.

Cadrages volontairement limites au plan rapproche/americain : en pied, le visage
n'a pas assez de pixels et ReActor echoue (meme cause qu'a l'essai 3).
"""
import json, os, sys, time, urllib.parse, urllib.request, uuid

COMFY = "http://127.0.0.1:8188"
CKPT = "waiIllustriousSDXL_v170.safetensors"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "dataset")
os.makedirs(OUT, exist_ok=True)

QUAL = "masterpiece, best quality, amazing quality, very aesthetic, absurdres, "
BW = "monochrome, greyscale, manga, screentone, halftone, lineart, ink, "
IDENT = ("1girl, solo, 18 years old, short messy black hair, blunt bangs, "
         "amber eyes, mole under left eye, black sailor uniform, red scarf")
NEG = ("bad quality, worst quality, sketch, censor, jpeg artifacts, watermark, "
       "signature, text, speech bubble, extra digits, bad hands, bad anatomy, "
       "multiple girls, 2girls, blurry, out of focus")

# 24 variations : cadrage + pose/expression + fond. Jamais de plein pied.
VARI = [
    ("closeup, looking at viewer, neutral expression", "plain background"),
    ("closeup, three-quarter view, slight smile", "screentone background"),
    ("closeup, profile view, serious", "white background"),
    ("upper body, looking away, thoughtful", "classroom background"),
    ("upper body, arms crossed, confident smirk", "school corridor"),
    ("upper body, hand on chin, curious", "plain background"),
    ("bust shot, surprised, wide eyes", "speed lines background"),
    ("bust shot, angry, furrowed brows", "dark screentone background"),
    ("bust shot, sad, downcast eyes", "rain background"),
    ("upper body, laughing, eyes closed", "sparkle background"),
    ("closeup, blushing, embarrassed", "screentone background"),
    ("upper body, shouting, open mouth", "impact lines background"),
    ("cowboy shot, standing, hands in pockets", "rooftop background"),
    ("cowboy shot, turning around, looking back", "street background"),
    ("upper body, from below, dramatic angle", "sky background"),
    ("upper body, from above, looking up", "plain background"),
    ("closeup, side glance, smug", "plain background"),
    ("upper body, holding a book, reading", "library background"),
    ("bust shot, wind blowing hair, calm", "outdoor background"),
    ("upper body, leaning on a wall, bored", "wall background"),
    ("closeup, crying, tears", "dark background"),
    ("upper body, pointing forward, determined", "plain background"),
    ("bust shot, whispering, hand near mouth", "plain background"),
    ("upper body, stretching, tired, yawning", "morning background"),
]

REF_PROMPT = (QUAL + BW + IDENT +
              ", extreme close-up portrait, face focus, looking at viewer, "
              "neutral expression, detailed face, detailed eyes, white background")


def post(p, d):
    r = urllib.request.Request(COMFY + p, data=json.dumps(d).encode(),
                               headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=180))


def get(p):
    return json.load(urllib.request.urlopen(COMFY + p, timeout=180))


def base_nodes(pos, seed, w, h, steps=32):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": pos, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "5": {"class_type": "KSampler", "inputs": {
            "seed": seed, "steps": steps, "cfg": 5.5, "sampler_name": "euler_ancestral",
            "scheduler": "normal", "denoise": 1.0, "model": ["1", 0],
            "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0]}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
    }


def swap_nodes(ref_name):
    """Ajoute LoadImage(ref) + ReActorFaceSwap sur la sortie du VAEDecode (noeud 6)."""
    return {
        "8": {"class_type": "LoadImage", "inputs": {"image": ref_name}},
        "9": {"class_type": "ReActorFaceSwap", "inputs": {
            "enabled": True, "input_image": ["6", 0], "source_image": ["8", 0],
            "swap_model": "inswapper_128.onnx", "facedetection": "retinaface_resnet50",
            "face_restore_model": "codeformer-v0.1.0.pth", "face_restore_visibility": 1.0,
            "codeformer_weight": 0.6, "detect_gender_input": "no", "detect_gender_source": "no",
            "input_faces_index": "0", "source_faces_index": "0", "console_log_level": 1}},
    }


def execute(label, nodes, save_from, prefix):
    nodes["99"] = {"class_type": "SaveImage",
                   "inputs": {"images": [save_from, 0], "filename_prefix": prefix}}
    t0 = time.time()
    pid = post("/prompt", {"prompt": nodes, "client_id": str(uuid.uuid4())})["prompt_id"]
    while True:
        h = get("/history/" + pid)
        if pid in h:
            break
        if time.time() - t0 > 400:
            print("[%s] TIMEOUT" % label, flush=True)
            return None
        time.sleep(2)
    st = h[pid].get("status", {})
    if st.get("status_str") == "error":
        print("[%s] ERREUR ComfyUI: %s" % (label, json.dumps(st)[:400]), flush=True)
        return None
    imgs = [i for n in h[pid]["outputs"].values() for i in n.get("images", [])]
    if not imgs:
        print("[%s] AUCUNE IMAGE" % label, flush=True)
        return None
    im = imgs[-1]
    url = "%s/view?filename=%s&type=%s&subfolder=%s" % (
        COMFY, urllib.parse.quote(im["filename"]), im["type"], im.get("subfolder", ""))
    dest = os.path.join(OUT, label + ".png")
    with urllib.request.urlopen(url, timeout=180) as r, open(dest, "wb") as f:
        f.write(r.read())
    print("[%s] OK %.0fs -> %s" % (label, time.time() - t0, os.path.basename(dest)), flush=True)
    return dest


def upload(path):
    """Envoie l'image de reference dans le dossier input de ComfyUI (pour LoadImage)."""
    import mimetypes
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
    n = int(sys.argv[1]) if len(sys.argv) > 1 else len(VARI)
    print("=== ESSAI 4 : dataset LoRA (bootstrap ReActor), %d images ===" % n, flush=True)

    ref = execute("ref_portrait", base_nodes(REF_PROMPT, 40001, 1024, 1024, 36), "6", "ref")
    if not ref:
        print("!! pas de portrait de reference -> arret", flush=True)
        sys.exit(1)
    ref_name = upload(ref)
    print("[ref] uploade dans ComfyUI/input sous '%s'" % ref_name, flush=True)

    ok = 0
    for i, (pose, bg) in enumerate(VARI[:n]):
        pos = QUAL + BW + IDENT + ", " + pose + ", " + bg
        nodes = base_nodes(pos, 50000 + i, 832, 1216)
        nodes.update(swap_nodes(ref_name))
        if execute("ds_%02d" % i, nodes, "9", "ds"):
            ok += 1
    print("=== dataset : %d/%d images -> %s ===" % (ok, n, OUT), flush=True)
