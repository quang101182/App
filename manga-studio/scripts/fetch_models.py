# -*- coding: utf-8 -*-
"""Recupere les modeles NON versionnes dont le chantier depend.

Pourquoi ce script existe : le detecteur de cases YOLO avait ete telecharge dans
le scratchpad d'une session, jamais range ni documente. A la session suivante, il
avait DISPARU — et avec lui la reproductibilite de toute la phase 3, alors que ses
chiffres (IoU 0,895) etaient soigneusement consignes dans la roadmap.

Un poids binaire n'a pas sa place dans le depot. Mais la COMMANDE qui le rapporte,
si. Sans elle, un chiffre mesure n'est pas un resultat : c'est un souvenir.

Usage:
    python fetch_models.py            (ne retelecharge pas ce qui est deja la)
    python fetch_models.py --force
"""
import argparse
import hashlib
import io
import os
import sys
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(HERE, "models")
COMFY = os.environ.get("COMFYUI_HOME", r"C:\Users\quang\Documents\ComfyUI")

# `dest` : dossier de destination. Absent -> scripts/models/ (outils du chantier).
# Les poids d'IPAdapter vont dans ComfyUI, c'est lui qui les charge.
IPADAPTER = os.path.join(COMFY, "models", "ipadapter")
CLIP_VISION = os.path.join(COMFY, "models", "clip_vision")
LORAS = os.path.join(COMFY, "models", "loras")

# Detecteur de cases ET de bulles, YOLO26-nano fine-tune sur Manga109-s.
# Licence Apache 2.0 -> utilisable, contrairement a Magi (recherche academique).
ASSETS = [
    {
        "nom": "manga_panel_detector_fp32.pt",
        "url": "https://huggingface.co/leoxs22/manga-panel-detector-yolo26n/resolve/main/manga_panel_detector_fp32.pt",
        "min_octets": 5_000_000,
        "a_quoi": "detection des cases (classe frame) et des bulles (classe text)",
    },
    # --- IPAdapter (cohérence d'un personnage SANS entrainement) -------------
    # Le nom du fichier de l'encodeur d'image n'est pas cosmetique : le noeud
    # IPAdapterUnifiedLoader cherche par MOTIF dans models/clip_vision. Depose
    # sous le nom d'origine (model.safetensors), il n'est jamais trouve.
    {
        "nom": "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors",
        "dest": CLIP_VISION,
        "url": "https://huggingface.co/h94/IP-Adapter/resolve/main/models/image_encoder/model.safetensors",
        "min_octets": 2_000_000_000,
        "a_quoi": "encodeur d'image ViT-H, requis par TOUS les IPAdapter _vit-h",
    },
    {
        "nom": "ip-adapter-plus_sdxl_vit-h.safetensors",
        "dest": IPADAPTER,
        "url": "https://huggingface.co/h94/IP-Adapter/resolve/main/sdxl_models/ip-adapter-plus_sdxl_vit-h.safetensors",
        "min_octets": 700_000_000,
        "a_quoi": "PLUS SDXL : transfert de style/sujet depuis une image de reference",
    },
    {
        "nom": "ip-adapter-plus-face_sdxl_vit-h.safetensors",
        "dest": IPADAPTER,
        "url": "https://huggingface.co/h94/IP-Adapter/resolve/main/sdxl_models/ip-adapter-plus-face_sdxl_vit-h.safetensors",
        "min_octets": 700_000_000,
        "a_quoi": "PLUS FACE SDXL : verrou facial, sans insightface",
    },
    # FaceID v2 : le plus fort sur le visage, mais il exige insightface (present,
    # installe par ReActor) ET son LoRA compagnon -- les deux, sinon le rendu part.
    {
        "nom": "ip-adapter-faceid-plusv2_sdxl.bin",
        "dest": IPADAPTER,
        "url": "https://huggingface.co/h94/IP-Adapter-FaceID/resolve/main/ip-adapter-faceid-plusv2_sdxl.bin",
        "min_octets": 700_000_000,
        "a_quoi": "FACEID PLUS V2 SDXL (usage NON commercial -- projet perso)",
    },
    {
        "nom": "ip-adapter-faceid-plusv2_sdxl_lora.safetensors",
        "dest": LORAS,
        "url": "https://huggingface.co/h94/IP-Adapter-FaceID/resolve/main/ip-adapter-faceid-plusv2_sdxl_lora.safetensors",
        "min_octets": 300_000_000,
        "a_quoi": "LoRA compagnon OBLIGATOIRE de FaceID plus v2",
    },
]

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def fetch(a, force=False):
    dossier = a.get("dest", MODELS)
    dest = os.path.join(dossier, a["nom"])
    if os.path.isfile(dest) and not force:
        n = os.path.getsize(dest)
        if n >= a["min_octets"]:
            print("  %-34s deja present (%.1f Mo)" % (a["nom"], n / 1e6))
            return True
        print("  %-34s present mais TRONQUE (%d octets) -> retelechargement"
              % (a["nom"], n))
    os.makedirs(dossier, exist_ok=True)
    print("  %-34s telechargement..." % a["nom"], flush=True)
    req = urllib.request.Request(a["url"], headers={"User-Agent": UA})
    tmp = dest + ".part"
    try:
        with urllib.request.urlopen(req, timeout=300) as r, open(tmp, "wb") as f:
            while True:
                chunk = r.read(1 << 16)
                if not chunk:
                    break
                f.write(chunk)
    except Exception as ex:
        print("      ECHEC : %s" % ex)
        if os.path.exists(tmp):
            os.remove(tmp)
        return False
    n = os.path.getsize(tmp)
    # Un HTML d'erreur fait quelques Ko et se laisserait ecrire sans broncher :
    # on refuse tout fichier trop petit plutot que de "reussir" avec un leurre.
    if n < a["min_octets"]:
        print("      ECHEC : %d octets seulement (page d'erreur ?)" % n)
        os.remove(tmp)
        return False
    os.replace(tmp, dest)
    # Par blocs : l'encodeur d'image fait 2,5 Go, le lire d'un coup en RAM
    # marcherait ici et exploserait ailleurs.
    hsh = hashlib.sha256()
    with open(dest, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            hsh.update(bloc)
    print("      OK %.1f Mo  sha256:%s" % (n / 1e6, hsh.hexdigest()[:16]))
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    print("=== MODELES DE MANGA STUDIO ===")
    print("outils du chantier : %s" % MODELS)
    print("poids ComfyUI      : %s\n" % COMFY)
    ok = True
    for a in ASSETS:
        print("  (%s)" % a["a_quoi"])
        print("   -> %s" % a.get("dest", MODELS))
        ok = fetch(a, args.force) and ok
    print("\n%s" % ("tout est en place." if ok else "AU MOINS UN MODELE MANQUE."))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
