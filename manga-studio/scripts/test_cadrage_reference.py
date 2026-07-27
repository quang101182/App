# -*- coding: utf-8 -*-
"""QUEL CADRAGE pour une image de reference ? (question de Quang, 27/07)

« J'avais demande s'il fallait juste un visage, s'il fallait le corps, s'il
fallait des vetements. Je n'ai pas compris ce qu'il faut. »

Il n'avait pas compris parce que **ca n'avait jamais ete mesure**. Le banc
`test_ipadapter.py` a prouve qu'IPAdapter fonctionne (identite 0,839), mais avec
une reference prise au hasard dans le dataset -- le cadrage n'etait pas une
variable etudiee, et c'est un des quatre pieges reconnus ce jour-la.

Ce banc compare QUATRE cadrages de la MEME image source, a seed identique, avec
le reglage retenu (PLUS / 0,4 / end 0,5 / N&B) :

    visage   -- tete seule, serree
    buste    -- visage + epaules + haut du costume     (mon hypothese)
    entier   -- l'image complete, en pied
    sheet    -- mosaique 2x2 facon « character sheet » (plusieurs vues)

Ce qui est atteignable ici, et ce qui ne l'est pas
--------------------------------------------------
⛔ Ce banc ne dit PAS « c'est bien lui ». L'instrument YOLO+CLIP du 27/07 a
   ECHOUE a son epreuve difficile : il ne distingue pas un changement d'yeux et
   de morphologie. On ne le rejoue donc pas pour trancher une identite.
✅ Ce qu'il produit : les 4 rendus cote a cote, au meme seed, plus deux mesures
   OBJECTIVES qui, elles, ont deja discrimine par le passe -- la saturation (une
   reference qui deteint fait virer la planche) et la fraction de noir (le rendu
   manga s'effondre quand IPAdapter pese trop).
Le choix final est visuel, et il revient a Quang. C'est assume, pas une lacune.

Usage:
    python test_cadrage_reference.py [--seed 12345]
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
CKPT = "waiIllustriousSDXL_v170.safetensors"
ICI = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(os.path.dirname(ICI), "dataset")
OUT = os.path.join(ICI, "cadrage_out")

QUAL = ("masterpiece, best quality, very aesthetic, absurdres, monochrome, greyscale, "
        "manga, screentone, halftone, lineart, ink, high contrast")
# Une scene VOLONTAIREMENT differente des images du dataset : si on redemandait
# la meme pose, on ne mesurerait pas le transfert d'identite, on mesurerait la
# capacite d'IPAdapter a recopier son entree.
SCENE = "1girl, walking in a school corridor, full body, looking back over shoulder"
NEG = ("bad quality, worst quality, censor, watermark, signature, text, extra digits, "
       "bad hands, bad anatomy, color, colored")
IPA = {"preset": "PLUS (high strength)", "poids": 0.4, "end": 0.5}

# Les quatre cadrages, en fractions de l'image source (x, y, largeur, hauteur).
CADRAGES = {
    "visage": (0.24, 0.02, 0.52, 0.26),
    "buste":  (0.06, 0.00, 0.88, 0.52),
    "entier": (0.00, 0.00, 1.00, 1.00),
}


def post(route, data):
    r = urllib.request.Request(COMFY + route, data=json.dumps(data).encode(),
                               headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=60))


def upload(chemin):
    """Depose une image dans le dossier input de ComfyUI (multipart a la main)."""
    nom = os.path.basename(chemin)
    b = open(chemin, "rb").read()
    lim = "----cadrage" + uuid.uuid4().hex
    tete = ("--%s\r\nContent-Disposition: form-data; name=\"image\"; filename=\"%s\"\r\n"
            "Content-Type: image/png\r\n\r\n" % (lim, nom)).encode()
    milieu = ("\r\n--%s\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n"
              "--%s--\r\n" % (lim, lim)).encode()
    req = urllib.request.Request(COMFY + "/upload/image", data=tete + b + milieu,
        headers={"Content-Type": "multipart/form-data; boundary=" + lim})
    return json.load(urllib.request.urlopen(req, timeout=120))["name"]


def graphe(ref, seed):
    g = {
      "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
      "2": {"class_type": "CLIPTextEncode", "inputs": {"text": QUAL + ", " + SCENE, "clip": ["1",1]}},
      "3": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["1",1]}},
      "4": {"class_type": "EmptyLatentImage", "inputs": {"width": 832, "height": 1216, "batch_size": 1}},
      "5": {"class_type": "KSampler", "inputs": {"seed": seed, "steps": 30, "cfg": 5.5,
            "sampler_name": "euler_ancestral", "scheduler": "normal", "denoise": 1.0,
            "model": ["1",0], "positive": ["2",0], "negative": ["3",0], "latent_image": ["4",0]}},
      "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5",0], "vae": ["1",2]}},
      "7": {"class_type": "SaveImage", "inputs": {"images": ["6",0], "filename_prefix": "manga/_cadrage/c"}},
    }
    if ref:
        g["20"] = {"class_type": "LoadImage", "inputs": {"image": ref}}
        g["21"] = {"class_type": "IPAdapterUnifiedLoader", "inputs": {"model": ["1",0], "preset": IPA["preset"]}}
        g["22"] = {"class_type": "IPAdapterAdvanced", "inputs": {
            "model": ["21",0], "ipadapter": ["21",1], "image": ["20",0],
            "weight": IPA["poids"], "weight_type": "linear", "combine_embeds": "concat",
            "start_at": 0.0, "end_at": IPA["end"], "embeds_scaling": "V only"}}
        g["5"]["inputs"]["model"] = ["22",0]
    return g


def genere(label, ref, seed):
    from PIL import Image
    t0 = time.time()
    pid = post("/prompt", {"prompt": graphe(ref, seed), "client_id": str(uuid.uuid4())})["prompt_id"]
    while True:
        h = json.load(urllib.request.urlopen(COMFY + "/history/" + pid, timeout=30))
        if pid in h:
            break
        if time.time() - t0 > 300:
            print("  [%s] TIMEOUT" % label)
            return None
        time.sleep(2)
    sorties = h[pid].get("outputs", {}).get("7", {}).get("images", [])
    if not sorties:
        print("  [%s] aucune image" % label)
        return None
    im = sorties[0]
    url = (COMFY + "/view?filename=" + urllib.parse.quote(im["filename"])
           + "&subfolder=" + urllib.parse.quote(im.get("subfolder", "")) + "&type=output")
    d = urllib.request.urlopen(url, timeout=60).read()
    p = os.path.join(OUT, label + ".png")
    open(p, "wb").write(d)
    print("  [%s] %.0f s -> %s" % (label, time.time() - t0, os.path.basename(p)))
    return p


def mesures(chemin):
    from PIL import Image
    im = Image.open(chemin).convert("RGB")
    px = list(im.getdata())[::503]
    sat = sum(max(p) - min(p) for p in px) / len(px)
    noir = sum(1 for p in px if sum(p) / 3 < 60) / len(px)
    return sat, noir


def main():
    import urllib.parse
    global urllib
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=771903)
    args = ap.parse_args()
    from PIL import Image
    os.makedirs(OUT, exist_ok=True)

    src = Image.open(os.path.join(DATASET, "ds_00.png")).convert("L")
    print("source : ds_00.png %sx%s (deja en N&B pour la mesure)" % src.size)

    refs = {}
    for nom, (x, y, w, h) in CADRAGES.items():
        W, H = src.size
        c = src.crop((int(x*W), int(y*H), int((x+w)*W), int((y+h)*H)))
        c = c.resize((min(1024, c.width), int(c.height * min(1024, c.width) / c.width)))
        p = os.path.join(OUT, "ref_" + nom + ".png")
        c.save(p)
        refs[nom] = p
        print("  reference %-7s : %sx%s" % (nom, c.width, c.height))

    # « character sheet » : plusieurs vues dans UNE image, comme le proposerait
    # `manga_sheet.py`. C'est le cas ou le visage occupe le moins de pixels.
    vues = [f for f in sorted(os.listdir(DATASET)) if f.endswith(".png")][:4]
    if len(vues) >= 4:
        m = Image.new("L", (1024, 1024), 255)
        for i, f in enumerate(vues):
            v = Image.open(os.path.join(DATASET, f)).convert("L").resize((512, 512))
            m.paste(v, (512 * (i % 2), 512 * (i // 2)))
        p = os.path.join(OUT, "ref_sheet.png")
        m.save(p)
        refs["sheet"] = p
        print("  reference sheet   : mosaique 2x2 de %d vues" % len(vues))

    print("\n--- generations (meme seed %d, meme scene) ---" % args.seed)
    rendus = {"temoin (sans reference)": genere("temoin", None, args.seed)}
    for nom, p in refs.items():
        rendus[nom] = genere(nom, upload(p), args.seed)

    print("\n%-26s %10s %10s" % ("cadrage", "saturation", "noir"))
    print("-" * 48)
    for nom, p in rendus.items():
        if not p:
            continue
        s, n = mesures(p)
        print("%-26s %10.2f %10.3f" % (nom, s, n))
    print("\n(saturation : 0 = monochrome parfait ; une reference qui deteint la fait monter)")
    print("(noir : le temoin donne la reference du rendu manga attendu)")

    ok = [(n, p) for n, p in rendus.items() if p]
    if ok:
        ims = [Image.open(p).convert("RGB") for _, p in ok]
        L = Image.new("RGB", (sum(i.width for i in ims), ims[0].height), "white")
        x = 0
        for i in ims:
            L.paste(i, (x, 0)); x += i.width
        r = 1600 / max(L.size)
        L = L.resize((int(L.width * r), int(L.height * r)), Image.LANCZOS)
        pl = os.path.join(OUT, "planche_cadrages.png")
        L.save(pl)
        print("\nplanche comparative : %s" % pl)
        print("ordre : " + " | ".join(n for n, _ in ok))
    print("\n⚠ Le choix est VISUEL : ces chiffres comparent des rendus, ils ne prouvent")
    print("  pas une identite. L'instrument du 27/07 a echoue a son epreuve difficile.")
    return 0


if __name__ == "__main__":
    import urllib.parse
    sys.exit(main())
