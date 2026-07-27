# -*- coding: utf-8 -*-
"""IPAdapter tient-il un personnage SANS entrainement ? — trois bras, meme seed.

C'est la question n°1 de la phase 7 : tout l'acquis des phases 1 et 2 repose sur
un LoRA entraine pour UN personnage (35 min de GPU). Ca ne passe pas a l'echelle
d'un outil « n'importe quel sujet ». IPAdapter est le candidat, il vient d'etre
installe — reste a savoir ce qu'il vaut, chiffre, contre les deux references
DEJA mesurees : le prompt seul (~50 %) et le LoRA (100 %).

L'INSTRUMENT, et pourquoi ce n'est plus un juge LLM
---------------------------------------------------
Le 27/07 a coute une lecon : un juge Pixtral non calibre disait « buste » sur des
plans en pied, et ma propre mesure disait pareil — ils se trompaient ENSEMBLE, et
leur accord m'a rendu confiant. On ne recommence pas.

⛔ INSIGHTFACE A ETE ESSAYE ET ECARTE, chiffres a l'appui (27/07). C'est la mesure
standard de la litterature IPAdapter/InstantID... sur des VISAGES PHOTOREALISTES.
Sur du manga N&B il ne voit presque rien :

    seuil 0.5 -> 2/12    seuil 0.3 -> 4/12    seuil 0.2 -> 6/12    seuil 0.1 -> 7/12
    et meme sur un visage DEJA recadre par YOLO (qui, lui, en trouve 11/12) : 5/12

Baisser le seuil ne repare rien : ca degrade l'alignement, donc l'embedding. Deux
echecs de meme nature -> on change d'outil au lieu de s'acharner.

L'instrument retenu est a deux etages, chacun employe la ou il est bon :
  1. YOLO face (face_yolov8m, deja utilise par compare_lora.py) DETECTE le visage
     -- il fonctionne sur du dessin, c'est mesure : 11/12 ;
  2. CLIP-ViT-H (l'encodeur installe ce jour avec IPAdapter) EMBEDDE le visage
     recadre -> cosinus.
Le recadrage n'est pas un detail : sans lui, CLIP comparerait surtout le fond, le
cadrage et le style -- toutes choses identiques ici par construction, donc toutes
les images se ressembleraient.

Et surtout, cette mesure est CALIBRABLE, ce que le juge ne pouvait pas etre :
  - etalon POSITIF : deux images du dataset = le MEME personnage -> doit sortir haut
  - etalon NEGATIF : ce personnage contre un autre design -> doit sortir bas
Si les deux nuages se chevauchent, l'instrument ne separe rien et LE BANC REFUSE
DE CONCLURE, au lieu de produire des chiffres qui ne veulent rien dire.

Usage:
    python test_ipadapter.py                      (calibration + les 3 bras)
    python test_ipadapter.py --calibrer           (calibration SEULE)
    python test_ipadapter.py --poids 0.8 1.0      (balayage du poids IPAdapter)

A lancer avec le python de ComfyUI (le seul qui a insightface) :
    C:/Users/quang/Documents/ComfyUI/.venv/Scripts/python.exe test_ipadapter.py
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
LORA = r"_manga_test\zqmg1rl_v1.safetensors"
TRIGGER = "zqmg1rl"
HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(os.path.dirname(HERE), "dataset")
OUT = os.path.join(HERE, "ipa_out")
FACE = r"C:\Users\quang\Documents\ComfyUI\models\ultralytics\bbox\face_yolov8m.pt"
CLIP_POIDS = "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"
CLIP_HF = r"C:\Users\quang\Documents\ComfyUI\models\clip_vision\vit_h_hf"
SEED = 222222

QUAL = "masterpiece, best quality, amazing quality, very aesthetic, absurdres, "
BW = "monochrome, greyscale, manga, screentone, halftone, lineart, ink, high contrast, "
# Exactement l'identite de compare_lora.py, pour rester comparable case pour case.
# Le trigger n'est ajoute QUE sur le bras LoRA : sans le LoRA il ne veut rien dire.
IDENT = ("1girl, solo, 18 years old, short messy black hair, blunt bangs, "
         "sharp amber eyes, black sailor uniform with red scarf, slender build")
# Un design volontairement ELOIGNE : etalon negatif FACILE.
AUTRE = ("1girl, solo, 30 years old, very long blonde wavy hair, blue eyes, "
         "round face, white lab coat, tall")
# Etalon negatif DIFFICILE : le meme personnage a deux attributs pres (les yeux
# et la forme du visage). C'est exactement ce que la phase 1 mesurait, et ce
# qu'un instrument doit savoir separer pour avoir le droit de conclure sur
# l'identite. Sans lui, on ne teste que « brune a frange vs blonde en blouse »,
# ce qui est trop facile pour vouloir dire quoi que ce soit.
PROCHE = ("1girl, solo, 18 years old, short messy black hair, blunt bangs, "
          "bright blue eyes, round soft face, black sailor uniform with red scarf, "
          "slender build")
NEG = ("bad quality, worst quality, worst detail, sketch, censor, jpeg artifacts, "
       "watermark, signature, text, english text, speech bubble, extra digits, "
       "bad hands, bad anatomy, color, colored, vibrant colors")
CASES = [
    ("case1_closeup", "close-up portrait, looking at viewer, neutral expression, plain background"),
    ("case2_fullbody", "full body, running through a school corridor, motion lines, dynamic angle, side view"),
    ("case3_emotion", "upper body, three-quarter view, shouting, tears in eyes, dramatic shadow, speed lines background"),
]


# ----------------------------------------------------------------- ComfyUI ---
def post(p, d):
    r = urllib.request.Request(COMFY + p, data=json.dumps(d).encode(),
                               headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=300))


def get(p):
    return json.load(urllib.request.urlopen(COMFY + p, timeout=300))


def upload(path, en_nb=False):
    """Depose l'image de reference dans ComfyUI/input pour que LoadImage la voie.

    `en_nb` : la convertit d'abord en niveaux de gris. Ce n'est pas un detail de
    confort — c'est la parade au transfert de palette mesure le 27/07.
    """
    if en_nb:
        from PIL import Image
        gris = os.path.join(OUT, "_ref_nb.png")
        Image.open(path).convert("L").convert("RGB").save(gris)
        path = gris
    nom = "manga_ref_" + os.path.basename(path)
    front = ("--b\r\nContent-Disposition: form-data; name=\"image\"; filename=\"%s\"\r\n"
             "Content-Type: image/png\r\n\r\n" % nom).encode()
    milieu = open(path, "rb").read()
    fin = ("\r\n--b\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\n"
           "true\r\n--b--\r\n").encode()
    r = urllib.request.Request(COMFY + "/upload/image", data=front + milieu + fin,
                               headers={"Content-Type": "multipart/form-data; boundary=b"})
    rep = json.load(urllib.request.urlopen(r, timeout=120))
    return rep["name"]


def fetch(im, dest):
    url = "%s/view?filename=%s&type=%s&subfolder=%s" % (
        COMFY, urllib.parse.quote(im["filename"]), im["type"],
        urllib.parse.quote(im.get("subfolder", "")))
    with urllib.request.urlopen(url, timeout=300) as r, open(dest, "wb") as f:
        f.write(r.read())


def wf(pos, seed, bras, ref_nom=None, poids=0.8, preset="PLUS FACE (portraits)",
       end_at=1.0):
    """Un seul squelette pour les trois bras : SEULE l'ancre d'identite change.

    Un workflow par bras aurait introduit des differences invisibles (un sampler,
    un nombre de steps) et le comparatif n'aurait plus rien compare.
    """
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
              "inputs": {"images": ["6", 0], "filename_prefix": "manga/_ipa/ipa"}},
    }
    if bras == "lora":
        g["10"] = {"class_type": "LoraLoader", "inputs": {
            "lora_name": LORA, "strength_model": 0.8, "strength_clip": 0.8,
            "model": ["1", 0], "clip": ["1", 1]}}
        g["2"]["inputs"]["clip"] = ["10", 1]
        g["3"]["inputs"]["clip"] = ["10", 1]
        g["5"]["inputs"]["model"] = ["10", 0]
    elif bras == "ipa":
        g["20"] = {"class_type": "LoadImage", "inputs": {"image": ref_nom}}
        g["21"] = {"class_type": "IPAdapterUnifiedLoader", "inputs": {
            "model": ["1", 0], "preset": preset}}
        g["22"] = {"class_type": "IPAdapterAdvanced", "inputs": {
            "model": ["21", 0], "ipadapter": ["21", 1], "image": ["20", 0],
            "weight": poids, "weight_type": "linear", "combine_embeds": "concat",
            "start_at": 0.0, "end_at": end_at, "embeds_scaling": "V only"}}
        g["5"]["inputs"]["model"] = ["22", 0]
    return g


def run(label, pos, seed, bras, ref_nom=None, poids=0.8,
        preset="PLUS FACE (portraits)", end_at=1.0):
    t0 = time.time()
    try:
        pid = post("/prompt", {"prompt": wf(pos, seed, bras, ref_nom, poids,
                                            preset, end_at),
                               "client_id": str(uuid.uuid4())})["prompt_id"]
    except urllib.error.HTTPError as e:
        print("  [%s] REFUS ComfyUI : %s" % (label, e.read().decode()[:400]), flush=True)
        return None
    while True:
        h = get("/history/" + pid)
        if pid in h:
            break
        if time.time() - t0 > 400:
            print("  [%s] TIMEOUT" % label, flush=True)
            return None
        time.sleep(2)
    st = h[pid].get("status", {})
    if st.get("status_str") == "error":
        print("  [%s] ERREUR %s" % (label, json.dumps(st)[:400]), flush=True)
        return None
    imgs = [i for n in h[pid]["outputs"].values() for i in n.get("images", [])]
    if not imgs:
        print("  [%s] AUCUNE IMAGE" % label, flush=True)
        return None
    dest = os.path.join(OUT, label + ".png")
    fetch(imgs[0], dest)
    print("  [%s] %.0fs" % (label, time.time() - t0), flush=True)
    return dest


# ------------------------------------------------------------- instrument ---
def prepare_clip():
    """Rend l'encodeur lisible par transformers, sans retelecharger 2,5 Go.

    Le poids installe pour IPAdapter EST le vision encoder de CLIP-ViT-H, mais il
    vit seul, sans les deux petits fichiers de config que transformers reclame.
    On fabrique donc un dossier a cote, avec un LIEN DUR vers le meme poids (zero
    octet de plus sur le disque) — plutot que d'exiger un second telechargement
    qu'une session future oublierait de refaire.
    """
    if os.path.isfile(os.path.join(CLIP_HF, "model.safetensors")):
        return CLIP_HF
    src = os.path.join(os.path.dirname(CLIP_HF), CLIP_POIDS)
    if not os.path.isfile(src):
        print("ARRET : encodeur absent (%s). Lancer d'abord :" % src)
        print("  python fetch_models.py")
        sys.exit(2)
    os.makedirs(CLIP_HF, exist_ok=True)
    url = "https://huggingface.co/h94/IP-Adapter/resolve/main/models/image_encoder/config.json"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        cfg = r.read()
    if len(cfg) < 200:
        print("ARRET : config.json suspect (%d octets)" % len(cfg))
        sys.exit(2)
    open(os.path.join(CLIP_HF, "config.json"), "wb").write(cfg)
    # Le preprocesseur n'est pas publie a cote du poids : ce sont les constantes
    # canoniques de CLIP, on les ecrit plutot que d'esperer un fichier absent.
    open(os.path.join(CLIP_HF, "preprocessor_config.json"), "w").write(json.dumps({
        "crop_size": 224, "do_center_crop": True, "do_normalize": True,
        "do_resize": True, "feature_extractor_type": "CLIPFeatureExtractor",
        "image_mean": [0.48145466, 0.4578275, 0.40821073],
        "image_std": [0.26862954, 0.26130258, 0.27577711],
        "resample": 3, "size": 224}, indent=2))
    dst = os.path.join(CLIP_HF, "model.safetensors")
    try:
        os.link(src, dst)
    except OSError:
        import shutil
        shutil.copy2(src, dst)
    return CLIP_HF


class Visages:
    """YOLO detecte le visage, CLIP-ViT-H l'embedde. Il CRIE s'il ne peut pas.

    Piege deja paye sur ce projet : un detecteur de repli enferme dans un
    try/except muet repondait « pas de visage » alors qu'il lui manquait sa
    dependance — et la calibration accusait l'outil au lieu de l'environnement.
    Ici, une dependance absente ARRETE le banc avec la commande a taper.
    """

    def __init__(self):
        try:
            import numpy as np
            import torch
            from transformers import CLIPImageProcessor, CLIPVisionModelWithProjection
            from ultralytics import YOLO
        except ImportError as e:
            print("ARRET : %s. Lancer ce banc avec le python de ComfyUI :" % e)
            print("  C:/Users/quang/Documents/ComfyUI/.venv/Scripts/python.exe %s"
                  % os.path.basename(__file__))
            sys.exit(2)
        if not os.path.isfile(FACE):
            print("ARRET : detecteur de visage absent : %s" % FACE)
            sys.exit(2)
        self.np, self.torch = np, torch
        d = prepare_clip()
        self.dev = "cuda" if torch.cuda.is_available() else "cpu"
        self.proc = CLIPImageProcessor.from_pretrained(d)
        self.clip = CLIPVisionModelWithProjection.from_pretrained(
            d, torch_dtype=torch.float16 if self.dev == "cuda" else torch.float32)
        self.clip = self.clip.to(self.dev).eval()
        self.yolo = YOLO(FACE)
        self.cache = {}
        self.rates = [0, 0]   # [images vues, visages trouves]

    def emb(self, path):
        if path in self.cache:
            return self.cache[path]
        import cv2
        im = cv2.imread(path)
        if im is None:
            raise RuntimeError("image illisible : " + path)
        H, W = im.shape[:2]
        self.rates[0] += 1
        r = self.yolo.predict(path, conf=0.35, verbose=False)[0]
        v = None
        if len(r.boxes):
            b = max(r.boxes, key=lambda b: (b.xyxy[0][2] - b.xyxy[0][0])
                    * (b.xyxy[0][3] - b.xyxy[0][1]))
            x1, y1, x2, y2 = [float(t) for t in b.xyxy[0]]
            mx, my = (x2 - x1) * 0.35, (y2 - y1) * 0.35   # un peu de coiffure
            crop = im[max(0, int(y1 - my)):min(H, int(y2 + my)),
                      max(0, int(x1 - mx)):min(W, int(x2 + mx))]
            if crop.size:
                crop = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
                px = self.proc(images=crop, return_tensors="pt")["pixel_values"]
                px = px.to(self.dev, dtype=self.clip.dtype)
                with self.torch.no_grad():
                    e = self.clip(px).image_embeds[0].float().cpu().numpy()
                v = e / (self.np.linalg.norm(e) + 1e-8)
                self.rates[1] += 1
        self.cache[path] = v
        return v

    def sim(self, a, b):
        ea, eb = self.emb(a), self.emb(b)
        if ea is None or eb is None:
            return None
        return float(self.np.dot(ea, eb))

    def taille_visage(self, path):
        """Part de l'image occupee par le visage — sert a CHOISIR la reference.

        IPAdapter travaille sur ce qu'on lui montre : une reference ou le visage
        fait 3 % de l'image ne porte presque aucune information de visage.
        """
        from PIL import Image
        r = self.yolo.predict(path, conf=0.35, verbose=False)[0]
        if not len(r.boxes):
            return 0.0
        w, h = Image.open(path).size
        return max(float((b.xyxy[0][2] - b.xyxy[0][0]) * (b.xyxy[0][3] - b.xyxy[0][1]))
                   / (w * h) for b in r.boxes)


def noirceur(path):
    """Fraction de pixels vraiment NOIRS. Mesure le delavage, vu a l'oeil le 27/07.

    Un manga N&B vit de ses aplats noirs. IPAdapter, monte en poids, rend une
    esquisse pale : l'identite pouvait rester correcte que le resultat etait
    deja inutilisable. Aucun chiffre du banc ne regardait ca — c'est le defaut
    que la roadmap a deja paye deux fois (« un banc qui ne regarde jamais l'ecran »).
    """
    from PIL import Image
    import numpy as np
    a = np.asarray(Image.open(path).convert("L"))
    return float((a < 40).mean())


def saturation(path):
    """Saturation moyenne. La mesure qui MANQUAIT, et qui a coute une hypothese.

    J'ai d'abord mesure la « noirceur » en croyant qu'IPAdapter delavait la
    planche. La planche contact a montre autre chose : il y INJECTE DE LA COULEUR
    (bleu, cyan) — et du bleu sombre est sombre en luminance, donc la noirceur
    n'y voyait rien. C'est la meme faute que « mesurer au mauvais endroit » deja
    payee sur l'effacement des bulles : l'instrument etait aveugle au defaut.

    Cause, une fois vue : l'image de reference est EN COULEUR, et IPAdapter
    transfere sa palette. Le negatif textuel « color » ne pese rien face a un
    conditionnement par image.
    """
    from PIL import Image
    import numpy as np
    a = np.asarray(Image.open(path).convert("HSV"))
    return float(a[:, :, 1].mean() / 255.0)


def calibrer(vis, refs, loin, proche):
    """Verifie que l'instrument SEPARE des classes connues d'avance — DEUX fois.

    Sans ce passage, un cosinus n'est qu'un nombre : on ne sait pas si 0,80 est
    « le meme personnage » ou « deux inconnus ». Ce sont les nuages qui donnent
    son sens a l'echelle, pas un seuil sorti de nulle part.

    Et il y a DEUX epreuves, parce que la premiere version de ce banc n'avait que
    la facile et se croyait calibree : separer « brune a frange » de « blonde en
    blouse » ne prouve rien sur l'identite FINE, qui est justement ce que la
    phase 1 mesurait. La seconde epreuve change deux attributs, pas la personne.
    """
    def nuage(paires):
        v = [s for s in paires if s is not None]
        return v

    print("\n=== CALIBRATION DE L'INSTRUMENT ===")
    pos = nuage([vis.sim(refs[i], refs[j])
                 for i in range(len(refs)) for j in range(i + 1, len(refs))])
    n_loin = nuage([vis.sim(r, a) for r in refs for a in loin])
    n_proche = nuage([vis.sim(r, a) for r in refs for a in proche])
    print("visages detectes sur les references : %d/%d"
          % (sum(1 for r in refs if vis.emb(r) is not None), len(refs)))
    print("taux de detection global de l'instrument : %d/%d" % (vis.rates[1], vis.rates[0]))
    if len(pos) < 3 or len(n_loin) < 3:
        print("VERDICT : instrument INUTILISABLE (trop peu de visages detectes).")
        return None
    for nom, v in (("meme personnage ", pos), ("design ELOIGNE ", n_loin),
                   ("design PROCHE  ", n_proche)):
        if v:
            print("%s (n=%2d) : min %.3f  moy %.3f  max %.3f"
                  % (nom, len(v), min(v), sum(v) / len(v), max(v)))
    if min(pos) <= max(n_loin):
        print("VERDICT : echec des l'epreuve FACILE (%.3f <= %.3f) -> l'instrument"
              " ne separe rien. Aucune conclusion d'identite." % (min(pos), max(n_loin)))
        return None
    if not n_proche:
        print("VERDICT : epreuve facile passee, epreuve DIFFICILE non evaluable"
              " (aucun visage detecte sur l'etalon proche).")
        return None
    if min(pos) > max(n_proche):
        seuil = (min(pos) + max(n_proche)) / 2
        print("VERDICT : les deux epreuves sont passees (marge difficile %.3f)"
              " -> l'instrument mesure bien l'identite FINE, frontiere a %.3f."
              % (min(pos) - max(n_proche), seuil))
        return seuil
    print("VERDICT : epreuve FACILE passee, epreuve DIFFICILE ECHOUEE"
          " (%.3f <= %.3f)." % (min(pos), max(n_proche)))
    print("  => l'instrument distingue deux personnages TRES differents, mais PAS")
    print("     un changement d'yeux ou de morphologie. Il ne peut donc pas etre")
    print("     lu comme une note d'identite : ses chiffres se comparent entre")
    print("     bras, ils ne prouvent pas « c'est le meme personnage ».")
    return None


def matrice(vis, ref_nom, seuil, refs=None):
    """Cherche un reglage d'IPAdapter qui n'abime PAS le rendu N&B.

    Constat du 27/07, vu a l'oeil puis chiffre : IPAdapter delave la planche, de
    plus en plus fort avec le poids. La parade standard est de ne l'appliquer
    qu'au DEBUT du debruitage (`end_at`) : l'ancre d'identite se pose sur la
    composition, puis le checkpoint reprend la main sur le rendu. On l'essaie
    plutot que de la supposer.
    """
    tem = os.path.join(OUT, "rien_case1_closeup.png")
    ref_noir = noirceur(tem) if os.path.isfile(tem) else None
    print("\n=== MATRICE : preset x end_at, poids 0.8, case1 ===")
    if ref_noir is not None:
        print("temoin sans IPAdapter : noir = %.3f" % ref_noir)
    print("%-26s | %-8s | %-8s" % ("reglage", "noir", "identite"))
    print("-" * 50)
    lignes = []
    for preset in ("PLUS FACE (portraits)", "PLUS (high strength)"):
        for end_at in (0.3, 0.5, 0.8):
            lab = "m_%s_%02d" % ("face" if "FACE" in preset else "plus", end_at * 10)
            p = run(lab, QUAL + BW + IDENT + ", " + CASES[0][1], SEED, "ipa",
                    ref_nom, 0.8, preset, end_at)
            if not p:
                continue
            n = noirceur(p)
            s = None
            if refs:
                v = [vis.sim(p, r) for r in refs]
                v = [x for x in v if x is not None]
                s = sum(v) / len(v) if v else None
            lignes.append((preset, end_at, n, s))
            print("%-26s | %-8.3f | %-8s"
                  % ("%s end_at %.1f" % ("PLUS FACE" if "FACE" in preset else "PLUS", end_at),
                     n, "visage absent" if s is None else "%.3f" % s))
    if ref_noir is not None and lignes:
        bons = [l for l in lignes if l[2] >= ref_noir * 0.75]
        print("\nreglages qui gardent au moins 75 %% du noir du temoin : %d/%d"
              % (len(bons), len(lignes)))
        if not bons:
            print("=> AUCUN : sur ce checkpoint, IPAdapter delave la planche quoi qu'on fasse.")
    return 0


# ------------------------------------------------------------------- main ---
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calibrer", action="store_true", help="calibration seule")
    ap.add_argument("--matrice", action="store_true",
                    help="balayage preset x end_at (cherche un reglage non delavant)")
    ap.add_argument("--poids", nargs="*", type=float, default=[0.8],
                    help="poids IPAdapter a essayer")
    ap.add_argument("--preset", default="PLUS (high strength)",
                    help="preset IPAdapter (defaut PLUS : PLUS FACE delave, mesure 27/07)")
    ap.add_argument("--end-at", type=float, default=0.8, dest="end_at",
                    help="jusqu'ou IPAdapter agit dans le debruitage")
    ap.add_argument("--ref-nb", action="store_true", dest="ref_nb",
                    help="convertir la reference en N&B avant de la donner a IPAdapter")
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    refs = [os.path.join(DATASET, f) for f in sorted(os.listdir(DATASET))
            if f.endswith(".png")]
    if len(refs) < 4:
        print("ARRET : dataset de reference introuvable ou vide (%s)" % DATASET)
        return 2
    print("=== IPAdapter vs LoRA vs prompt seul — seed %d, checkpoint %s ==="
          % (SEED, CKPT))
    print("references : %d images de %s" % (len(refs), DATASET))

    vis = Visages()

    # Etalon negatif : un autre design, genere ici meme (meme checkpoint, meme
    # rendu) — comparer a des photos reelles aurait mesure l'ecart de STYLE.
    print("\n-- etalons negatifs (3 images ELOIGNEES + 3 images PROCHES)")
    loin, proche = [], []
    for i in range(3):
        p = run("etalon_loin_%d" % i, QUAL + BW + AUTRE + ", " + CASES[0][1],
                SEED + 1000 + i, "rien")
        if p:
            loin.append(p)
        p = run("etalon_proche_%d" % i, QUAL + BW + PROCHE + ", " + CASES[0][1],
                SEED + 2000 + i, "rien")
        if p:
            proche.append(p)

    seuil = calibrer(vis, refs[:8], loin, proche)
    if args.calibrer:
        return 0 if seuil else 1

    # Reference IPAdapter : le portrait du dataset ou le visage est REELLEMENT le
    # plus grand — et on l'annonce, parce qu'un banc dont la reference change en
    # silence d'une session a l'autre ne compare plus rien.
    tailles = [(vis.taille_visage(r), r) for r in refs]
    tailles = sorted([t for t in tailles if t[0] > 0], reverse=True)
    if not tailles:
        print("ARRET : aucun visage detecte dans le dataset — rien a donner a IPAdapter.")
        return 2
    part, ref_img = tailles[0]
    ref_nom = upload(ref_img, en_nb=args.ref_nb)
    print("\nreference donnee a IPAdapter : %s (visage = %.1f %% de l'image) -> %s"
          % (os.path.basename(ref_img), 100 * part, ref_nom))

    if args.matrice:
        return matrice(vis, ref_nom, seuil, refs[:8])

    bras = [("rien", IDENT, None, 0.0), ("lora", TRIGGER + ", " + IDENT, None, 0.0)]
    for p in args.poids:
        bras.append(("ipa@%.2f" % p, IDENT, ref_nom, p))

    res = {}
    for nom, ident, rn, poids in bras:
        print("\n-- bras %s" % nom)
        res[nom] = []
        for label, act in CASES:
            b = "ipa" if nom.startswith("ipa") else nom
            p = run("%s_%s" % (nom.replace("@", "").replace(".", ""), label),
                    QUAL + BW + ident + ", " + act, SEED, b, rn, poids,
                    args.preset, args.end_at)
            if not p:
                res[nom].append(None)
                continue
            sims = [vis.sim(p, r) for r in refs[:8]]
            sims = [s for s in sims if s is not None]
            res[nom].append({"path": p, "noir": noirceur(p), "sat": saturation(p),
                             "sim": (sum(sims) / len(sims)) if sims else None})

    print("\n================= IDENTITE (cosinus moyen vs 8 references) =================")
    entete = "%-16s" % "case"
    for nom, _, _, _ in bras:
        entete += " | %-12s" % nom
    print(entete)
    print("-" * len(entete))
    for i, (label, _) in enumerate(CASES):
        ligne = "%-16s" % label
        for nom, _, _, _ in bras:
            x = res[nom][i]
            ligne += " | %-12s" % ("(echec)" if not x else
                                   ("visage absent" if x["sim"] is None
                                    else "%.3f" % x["sim"]))
        print(ligne)
    print("-" * len(entete))
    ligne = "%-16s" % "MOYENNE"
    for nom, _, _, _ in bras:
        v = [x["sim"] for x in res[nom] if x and x["sim"] is not None]
        ligne += " | %-12s" % ("%.3f (%d/3)" % (sum(v) / len(v), len(v)) if v else "-")
    print(ligne)

    print("\n============ RENDU N&B (fraction de pixels noirs) ============")
    print("Une identite tenue sur une planche delavee ne sert a rien : les deux")
    print("se mesurent, jamais l'une sans l'autre.")
    print(entete)
    for cle, titre in (("noir", "noir moyen"), ("sat", "SATURATION")):
        ligne = "%-16s" % titre
        for nom, _, _, _ in bras:
            v = [x[cle] for x in res[nom] if x]
            ligne += " | %-12s" % ("%.3f" % (sum(v) / len(v)) if v else "-")
        print(ligne)
    print("(saturation : un vrai N&B est proche de 0 ; toute valeur haute = couleur injectee)")

    if seuil:
        print("\nfrontiere calibree : %.3f  (au-dessus = meme personnage)" % seuil)
        for nom, _, _, _ in bras:
            v = [x["sim"] for x in res[nom] if x and x["sim"] is not None]
            print("  %-12s : %d/3 cases au-dessus de la frontiere"
                  % (nom, sum(1 for s in v if s > seuil)))
    else:
        print("\nPas de frontiere calibree -> les chiffres ci-dessus se COMPARENT")
        print("entre eux, mais aucun ne prouve a lui seul « c'est le meme personnage ».")
    print("\nimages -> %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
