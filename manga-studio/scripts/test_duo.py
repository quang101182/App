# -*- coding: utf-8 -*-
"""DEUX personnages dans une case — le trou de mesure du chantier.

Tout ce que la feuille de route affirme (identite 100 %, decor 6/6, cadrage) a ete
mesure sur UN personnage seul, dans un couloir de lycee. Le volet adulte demande
par Quang (fetichisme, femdom) suppose au minimum deux corps qui interagissent —
et c'est le point de rupture connu de SDXL. « Ca marche » sur une lyceenne seule
ne dit rien la-dessus : ce banc mesure ce qui n'a jamais ete mesure.

ECHELLE, du plus facile au plus dur — pour savoir OU ca casse, pas SI ca casse :
  n1 cote-a-cote      : deux personnes, aucune interaction
  n2 contact simple   : une main sur une epaule
  n3 rapport de force : elle debout, lui a genoux (femdom, mise en scene, non explicite)
  n4 etreinte proche  : deux corps enlaces, cadrage serre

L'INSTRUMENT
------------
Compter les personnages n'a de sens que si le compteur sait compter. Il est donc
calibre sur des images dont la reponse est CONNUE : les sorties du banc IPAdapter
contiennent exactement UNE personne. S'il n'y trouve pas 1, il ne peut rien dire
sur 2, et le banc s'arrete.

Sujets ADULTES explicites (25-30 ans, tenue de ville) et non des lyceens : le
personnage du LoRA est decrit « 18 years old » en uniforme scolaire, ce qui n'a
rien a faire dans un test de registre adulte.

Usage:
    C:/Users/quang/Documents/ComfyUI/.venv/Scripts/python.exe test_duo.py
    ... --calibrer        (calibration du compteur SEULE)
    ... --seeds 3         (n seeds par scene, defaut 3)
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
OUT = os.path.join(HERE, "duo_out")
IPA_OUT = os.path.join(HERE, "ipa_out")
PERSON = os.path.join(HERE, "models", "yolov8n.pt")
FACE = r"C:\Users\quang\Documents\ComfyUI\models\ultralytics\bbox\face_yolov8m.pt"
SEED = 222222

QUAL = "masterpiece, best quality, amazing quality, very aesthetic, absurdres, "
BW = "monochrome, greyscale, manga, screentone, halftone, lineart, ink, high contrast, "
# Deux adultes, decrits une fois, injectes partout : ce qui varie doit etre la
# SCENE, jamais le casting -- sinon on ne saurait pas ce qui a casse.
CAST = ("1girl, 1boy, mature woman 28 years old, long black hair, sharp eyes, "
        "tailored black suit, adult man 30 years old, short hair, white shirt, ")
# Casting negatif repris du principe de Muse : le modele ADORE ajouter du monde,
# et une 3e personne fausse tout le comptage.
NEG = ("bad quality, worst quality, worst detail, sketch, censor, jpeg artifacts, "
       "watermark, signature, text, speech bubble, extra digits, bad hands, "
       "bad anatomy, extra limbs, fused fingers, missing limb, deformed, "
       "color, colored, vibrant colors, "
       "3girls, 3boys, multiple girls, multiple boys, crowd, group, "
       "child, loli, shota, teen, young")

SCENES = [
    ("n1_cote_a_cote",
     "two people standing side by side in an office corridor, full body, "
     "facing viewer, neutral expressions, no contact"),
    ("n2_contact",
     "the woman puts one hand on the man's shoulder, upper body, "
     "three-quarter view, office background"),
    ("n3_rapport_force",
     "femdom, the woman stands tall looking down at the man, the man kneels at "
     "her feet looking up, low angle shot from below, dramatic shadow, "
     "power dynamic, fully clothed"),
    ("n4_etreinte",
     "the woman and the man embrace closely, face to face, close-up, "
     "arms around each other, intimate mood, fully clothed"),
]


def post(p, d):
    r = urllib.request.Request(COMFY + p, data=json.dumps(d).encode(),
                               headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=300))


def get(p):
    return json.load(urllib.request.urlopen(COMFY + p, timeout=300))


def wf(pos, seed):
    return {
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
              "inputs": {"images": ["6", 0], "filename_prefix": "manga/_duo/duo"}},
    }


def run(label, pos, seed):
    t0 = time.time()
    try:
        pid = post("/prompt", {"prompt": wf(pos, seed),
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


class Compteur:
    def __init__(self):
        try:
            from ultralytics import YOLO
        except ImportError as e:
            print("ARRET : %s -> lancer avec le python de ComfyUI." % e)
            sys.exit(2)
        for p in (PERSON, FACE):
            if not os.path.isfile(p):
                print("ARRET : modele absent %s (lancer fetch_models.py)" % p)
                sys.exit(2)
        self.p = YOLO(PERSON)
        self.f = YOLO(FACE)

    def personnes(self, path, conf=0.30):
        r = self.p.predict(path, conf=conf, classes=[0], verbose=False)[0]
        return len(r.boxes)

    def visages(self, path, conf=0.35):
        return len(self.f.predict(path, conf=conf, verbose=False)[0].boxes)


def saturation(path):
    from PIL import Image
    import numpy as np
    return float(np.asarray(Image.open(path).convert("HSV"))[:, :, 1].mean() / 255.0)


def calibrer(c):
    """Le compteur sait-il compter ? Epreuve sur des images a UNE personne.

    Les sorties du banc IPAdapter contiennent exactement un personnage : c'est une
    verite connue AVANT la mesure, donc un etalon legitime. Un compteur qui n'y
    trouve pas 1 ne peut rien affirmer sur 2 — et il vaut mieux le savoir ici que
    d'aller expliquer plus tard qu'une scene « contient trois personnes ».
    """
    temoins = [os.path.join(IPA_OUT, f) for f in sorted(os.listdir(IPA_OUT))
               if f.endswith(".png") and not f.startswith("_")] if os.path.isdir(IPA_OUT) else []
    temoins = [t for t in temoins if "etalon" not in t][:9]
    print("\n=== CALIBRATION DU COMPTEUR (images a UNE personne) ===")
    if len(temoins) < 4:
        print("ARRET : pas assez de temoins (lancer test_ipadapter.py d'abord).")
        return False
    # Deux candidats en concurrence, juges sur la meme epreuve. On garde celui
    # qui la passe, on ne suppose pas lequel devrait gagner.
    pers = [c.personnes(t) for t in temoins]
    visa = [c.visages(t) for t in temoins]
    n = len(temoins)
    ok_p = sum(1 for v in pers if v == 1)
    ok_v = sum(1 for v in visa if v == 1)
    print("temoins : %d" % n)
    print("  COCO 'person' : %s -> exactement 1 : %d/%d" % (pers, ok_p, n))
    print("  visages       : %s -> exactement 1 : %d/%d" % (visa, ok_v, n))
    if ok_v >= int(0.8 * n):
        print("VERDICT : COCO echoue sur du dessin (photorealiste), le compteur de")
        print("          VISAGES passe -> c'est lui qui compte les personnages.")
        return "visages"
    if ok_p >= int(0.8 * n):
        print("VERDICT : compteur COCO utilisable.")
        return "personnes"
    print("VERDICT : AUCUN compteur ne passe l'epreuve -> le banc ne conclura pas")
    print("          sur le nombre de personnages ; seul le regard tranchera.")
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calibrer", action="store_true")
    ap.add_argument("--seeds", type=int, default=3)
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    c = Compteur()
    fiable = calibrer(c)
    if args.calibrer:
        return 0 if fiable else 1
    compte = (lambda p: c.visages(p)) if fiable == "visages" else (lambda p: c.personnes(p))

    print("\n=== DEUX PERSONNAGES — %d scenes x %d seeds ===" % (len(SCENES), args.seeds))
    res = {}
    for nom, desc in SCENES:
        print("\n-- %s" % nom)
        res[nom] = []
        for k in range(args.seeds):
            p = run("%s_s%d" % (nom, k), QUAL + BW + CAST + desc, SEED + k * 111)
            if not p:
                continue
            res[nom].append({"path": p, "pers": compte(p),
                             "vis": c.visages(p), "sat": saturation(p)})

    print("\n===================== RESULTATS =====================")
    print("%-18s | %-14s | %-12s | %-10s" % ("scene", "duo trouve", "visages", "saturation"))
    print("-" * 66)
    for nom, _ in SCENES:
        v = res[nom]
        if not v:
            print("%-18s | (aucune image)" % nom)
            continue
        deux = sum(1 for x in v if x["pers"] == 2)
        print("%-18s | %-14s | %-12s | %-10.3f"
              % (nom, "%d/%d" % (deux, len(v)),
                 "/".join(str(x["vis"]) for x in v),
                 sum(x["sat"] for x in v) / len(v)))
    print("-" * 66)
    if not fiable:
        print("RAPPEL : le compteur a echoue sa calibration -> colonne 'personnes'")
        print("         indicative seulement.")
    print("\nimages -> %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
