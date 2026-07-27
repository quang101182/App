# -*- coding: utf-8 -*-
"""Mesure du CADRAGE par ce qui est dans le champ, pas par un proxy.

Pourquoi cet outil existe : le 27/07 j'ai classe des cadrages avec « hauteur du
visage / hauteur d'image », un seuil que je n'avais jamais etabli. Calibre apres
coup, il donnait 0,448 pour un buste et 0,207 pour un plan en pied : il ne separe
rien. Des conclusions confiantes en avaient ete tirees, il a fallu les retirer.

Ici on ne prend pas un indice indirect, on prend la DEFINITION : un cadrage, c'est
ce qui entre dans le cadre. Les keypoints OpenPose disent exactement ca.

    chevilles visibles           -> plan en pied
    genoux visibles, pas chevilles-> plan americain
    hanches visibles, pas genoux -> plan taille / buste large
    epaules seules               -> buste
    tete seule                   -> gros plan

⚠ Un point peut manquer parce qu'il est CACHE, pas parce qu'il est hors champ.
D'ou la regle : ce script ne sert que s'il reproduit, sur les images d'etalon,
le classement que j'ai etabli a l'oeil. `--calibrer` fait exactement ce controle,
et il doit passer AVANT toute utilisation pour conclure.

Usage:
    python mesure_cadrage.py --calibrer          # valide l'outil sur l'etalon
    python mesure_cadrage.py <image...>          # classe des images
"""
import argparse
import glob
import io
import json
import os
import sys
import time
import urllib.request
import uuid

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

COMFY = "http://127.0.0.1:8188"
HERE = os.path.dirname(os.path.abspath(__file__))
COMFY_OUT = r"C:\Users\quang\Documents\ComfyUI\output"

# COCO-18. On ne regarde que les articulations qui DEFINISSENT une distance de plan.
JAMBES = {"chevilles": (10, 13), "genoux": (9, 12), "hanches": (8, 11)}
BUSTE = {"epaules": (2, 5)}
TETE = {"tete": (0, 0)}
SEUIL = 0.10          # confiance minimale pour dire « ce point est la ».
                      # 0,30 ratait des chevilles pourtant visibles : OpenPose est
                      # entraine sur des photos, il est peu sur sur du trait manga.
FACE = r"C:\Users\quang\Documents\ComfyUI\models\ultralytics\bbox\face_yolov8m.pt"

# Etalon : des images dont j'ai VERIFIE le cadrage a l'oeil, une par une.
# C'est la reference de l'outil ; sans elle il n'a aucune autorite.
ETALON = [
    ("gros plan",    "compare_out/v1_case1_closeup.png"),
    ("gros plan",    "../dataset_v2/ds2_00.png"),
    ("buste",        "../dataset_v2/ds2_07.png"),
    ("americain",    "../dataset_v2/ds2_14.png"),
    ("plan en pied", "../dataset_v2/ds2_21.png"),
    ("plan en pied", "pose_out/sans_openpose.png"),
    ("plan en pied", "pose_out/openpose_0.6.png"),
    ("plan en pied", "pose_out/openpose_0.8.png"),
    ("plan en pied", "pose_out/openpose_1.0.png"),
]


def post(p, d):
    r = urllib.request.Request(COMFY + p, data=json.dumps(d).encode(),
                               headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=300))


def get(p):
    return json.load(urllib.request.urlopen(COMFY + p, timeout=300))


def upload(path):
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


def keypoints(path):
    """Renvoie la liste des keypoints COCO-18 du personnage principal."""
    nom = upload(path)
    # Le JSON part dans un SOUS-DOSSIER manga/ : les sorties de ce chantier ne se
    # melangent jamais a celles de Generate Studio (regle du 26/07).
    g = {
        "1": {"class_type": "LoadImage", "inputs": {"image": nom}},
        "2": {"class_type": "OpenposePreprocessor", "inputs": {
            "image": ["1", 0], "detect_hand": "disable", "detect_body": "enable",
            "detect_face": "disable", "resolution": 1024}},
        "3": {"class_type": "SavePoseKpsAsJsonFile", "inputs": {
            "pose_kps": ["2", 1], "filename_prefix": "manga/_kps/kps"}},
    }
    t0 = time.time()
    pid = post("/prompt", {"prompt": g, "client_id": str(uuid.uuid4())})["prompt_id"]
    while True:
        h = get("/history/" + pid)
        if pid in h:
            break
        if time.time() - t0 > 200:
            return None
        time.sleep(1)
    st = h[pid].get("status", {})
    if st.get("status_str") == "error":
        return None
    # le fichier le plus recent sous output/manga/_kps
    d = os.path.join(COMFY_OUT, "manga", "_kps")
    fs = sorted(glob.glob(os.path.join(d, "*.json")), key=os.path.getmtime)
    if not fs:
        return None
    data = json.load(open(fs[-1], encoding="utf-8"))
    if isinstance(data, list):
        data = data[0] if data else {}
    gens = data.get("people") or []
    if not gens:
        return None
    kp = gens[0].get("pose_keypoints_2d") or []
    return [(kp[i], kp[i + 1], kp[i + 2]) for i in range(0, min(len(kp), 54), 3)]


_face_modele = [None]


def a_un_visage(path):
    """Secours pour les cadrages SERRES. OpenPose ne trouve aucun corps sur un gros
    plan — et pour cause, il n'y en a pas dans le cadre. Un visage bien present
    SANS aucune articulation de corps, c'est justement la definition d'un plan
    serre. Chaque instrument couvre la ou l'autre est aveugle."""
    try:
        if _face_modele[0] is None:
            from ultralytics import YOLO
            _face_modele[0] = YOLO(FACE)
        from PIL import Image
        im = Image.open(path).convert("RGB")
        r = _face_modele[0].predict(im, conf=0.35, verbose=False)[0]
        return len(r.boxes) > 0
    except Exception as ex:
        # JAMAIS en silence : un secours qui echoue sans le dire fait croire que
        # l'image n'a pas de visage. C'est ce qui est arrive au 1er essai — lance
        # avec le python systeme, sans ultralytics, l'exception etait avalee et la
        # calibration accusait l'outil au lieu de l'environnement.
        print("  ⚠ detecteur de visage indisponible (%s: %s) — lance ce script avec\n"
              "    D:/Download/02-Apps-Web/kohya-trainer/.venv/Scripts/python.exe"
              % (type(ex).__name__, str(ex)[:80]), file=sys.stderr)
        raise SystemExit(2)


def classe(kp, path=None):
    if not kp:
        if path and a_un_visage(path):
            return "serre", {"visage": True}
        return "indetermine", {}
    def vu(paire):
        return any(kp[i][2] >= SEUIL for i in paire if i < len(kp))
    presents = {}
    for nom, paire in list(JAMBES.items()) + list(BUSTE.items()) + list(TETE.items()):
        presents[nom] = vu(paire)
    if presents.get("chevilles"):
        c = "plan en pied"
    elif presents.get("genoux"):
        c = "americain"
    elif presents.get("hanches"):
        c = "buste large"
    elif presents.get("epaules") or presents.get("tete"):
        c = "serre"
    else:
        c = "serre" if (path and a_un_visage(path)) else "indetermine"
    return c, presents


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="*")
    ap.add_argument("--calibrer", action="store_true")
    a = ap.parse_args()

    if a.calibrer:
        print("=== CALIBRATION : l'outil retrouve-t-il ce que j'ai vu ? ===")
        print("(regle : sans ce controle, l'outil n'a aucune autorite pour conclure)\n")
        bons, total, ecarts = 0, 0, []
        # « buste » et « buste large » sont la meme famille : on ne se donne pas
        # une precision qu'on ne cherche pas.
        fam = {"gros plan": "serre", "buste": "serre", "serre": "serre",
               "buste large": "moyen", "americain": "moyen",
               "plan en pied": "large", "indetermine": "?"}
        for attendu, rel in ETALON:
            p = os.path.join(HERE, rel)
            if not os.path.isfile(p):
                print("  (absente) %s" % rel); continue
            c, pr = classe(keypoints(p), p)
            total += 1
            ok = fam.get(c) == fam.get(attendu)
            bons += 1 if ok else 0
            if not ok:
                ecarts.append((attendu, c))
            vus = ",".join(k for k, v in pr.items() if v) or "rien"
            print("  %-14s -> %-14s %s   [%s]"
                  % (attendu, c, "OK " if ok else "FAUX", vus))
        print("\n%d/%d classes dans la bonne famille (serre / moyen / large)" % (bons, total))
        # Un instrument imparfait reste utilisable SI son erreur va toujours dans le
        # meme sens et qu'on le sait. Ici : il rate des plans larges, il n'en invente
        # jamais. Donc « c'est large » est fiable ; « ce n'est pas large » ne l'est pas.
        rang = {"serre": 0, "moyen": 1, "large": 2, "?": -1}
        sur, sous = 0, 0
        for attendu, obtenu in ecarts:
            ra, ro = rang.get(fam.get(attendu), -1), rang.get(fam.get(obtenu), -1)
            if ro > ra: sur += 1
            elif ro < ra or ro < 0: sous += 1
        print("erreurs : %d sous-estimation(s) de largeur, %d surestimation(s)" % (sous, sur))
        if total and bons == total:
            print("=> l'outil reproduit mon classement : utilisable sans reserve.")
            return 0
        if sur == 0 and bons >= total * 0.7:
            print("=> BIAIS UNIDIRECTIONNEL CONNU : l'outil rate des plans larges,")
            print("   il n'en invente jamais. Donc :")
            print("   - « c'est un plan large » est FIABLE ;")
            print("   - « ce n'est pas un plan large » ne l'est PAS ;")
            print("   - il ne peut donc PAS servir a etablir une repartition de cadrages,")
            print("     seulement un MINIMUM de plans larges.")
            return 0
        print("=> l'outil se trompe dans les DEUX sens : ne rien conclure avec.")
        return 1

    if not a.images:
        print("rien a mesurer (voir --calibrer)"); return 2
    for motif in a.images:
        for p in sorted(glob.glob(motif)):
            c, pr = classe(keypoints(p), p)
            vus = ",".join(k for k, v in pr.items() if v) or "rien"
            print("  %-40s %-14s [%s]" % (os.path.basename(p), c, vus))
    return 0


if __name__ == "__main__":
    sys.exit(main())
