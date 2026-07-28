# -*- coding: utf-8 -*-
"""Quel TAG fait reellement apparaitre DEUX personnages ? (28/07/2026)

Point dur mesure la veille et reconfirme par le banc d'ordre : « deux
personnages face a face » n'est respecte que **1 a 2 fois sur 4**, quel que soit
l'ordre du prompt. Ce n'est donc pas une question de position -- c'est le TAG.

Hypothese a verifier avant tout chantier : l'app injecte `2people` / `3people`
(`promptFinal`, ligne « n + "people" »). Or **`2people` n'est pas un tag
danbooru**. Le vocabulaire reel est `2boys`, `2girls`, `1boy 1girl`,
`multiple boys`, `multiple girls`. Un tag jamais vu a l'entrainement ne vaut pas
zero : il consomme des tokens et dilue le reste. Si c'est le cas, le correctif
tient en une ligne -- et il faut le PROUVER, pas le supposer.

Cinq formulations, memes seeds, meme scene :
  V1  2people, two characters facing each other      (ce que l'app envoie)
  V2  1boy 1girl                                     (le tag booru canonique)
  V3  2boys                                          (canonique, meme genre)
  V4  multiple people                                (formulation intermediaire)
  V5  aucun tag de comptage                          (temoin : que fait le modele seul ?)

Le juge compte les VISAGES (`face_yolov8m`, celui de tout le projet). Le temoin
V5 est indispensable : sans lui, on ne saurait pas si un bon score vient du tag
ou de la scene elle-meme.

Usage:
    python test_duo_comptage.py [--n 5]
"""
import argparse
import io
import json
import os
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
APP_URL = "http://127.0.0.1:8190/manga"
SORTIE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "essai_out", "duo")
PY_COMFY = r"C:\Users\quang\Documents\ComfyUI\.venv\Scripts\python.exe"
MODELE_FACE = (r"C:\Users\quang\Documents\ComfyUI\models"
               r"\ultralytics\bbox\face_yolov8m.pt")

STYLE = ("masterpiece, best quality, very aesthetic, absurdres, monochrome, greyscale, "
         "manga, screentone, halftone, lineart")
SCENE = "two characters facing each other, center of a dojo, wide shot, tension"
NEG = ("bad quality, worst quality, sketch, censor, watermark, signature, text, "
       "speech bubble, extra digits, bad hands, bad anatomy, color, colored")

VARIANTES = [
    ("V1-2people", "2people"),
    ("V2-1boy1girl", "1boy 1girl"),
    ("V3-2boys", "2boys"),
    ("V4-multiple", "multiple people"),
    ("V5-temoin", ""),
]


def juge(fichiers):
    code = ("import sys, json\n"
            "from ultralytics import YOLO\n"
            "y = YOLO(sys.argv[1])\n"
            "out = {}\n"
            "for f in sys.argv[2:]:\n"
            "    n = 0\n"
            "    for r in y(f, verbose=False):\n"
            "        n += len(r.boxes or [])\n"
            "    out[f] = n\n"
            "print(json.dumps(out))\n")
    for c, quoi in ((PY_COMFY, "le python de ComfyUI"), (MODELE_FACE, "le modele")):
        if not os.path.isfile(c):
            print("ARRET : %s introuvable (%s)" % (quoi, c))
            return {}
    try:
        r = subprocess.run([PY_COMFY, "-c", code, MODELE_FACE] + list(fichiers),
                           capture_output=True, timeout=900)
        return json.loads(r.stdout.decode("utf-8", "replace").strip().splitlines()[-1])
    except Exception as e:
        print("ARRET : detection impossible (%s)" % e)
        return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--seed", type=int, default=880000)
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright
    os.makedirs(SORTIE, exist_ok=True)

    secret = open(SECRET_FILE, encoding="utf-8").read().strip()
    fichiers = {}
    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=True, channel="msedge")
        pg = br.new_page()
        pg.set_default_timeout(300000)
        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_function("typeof wfPanel === 'function'")

        for nom, tag in VARIANTES:
            positif = ", ".join([x for x in [STYLE, tag, SCENE] if x])
            for k in range(args.n):
                seed = args.seed + k
                imgs = pg.evaluate("""async (c) => {
                    const r = Object.assign({}, recipe(), {
                      neg: c.neg, w: 832, h: 1216, steps: 30, cfg: 5.5,
                      sampler: 'euler_ancestral', lora: '' });
                    return await runGraph(
                      wfPanel(r, c.positif, c.seed,
                              'manga/_banc_duo/' + c.nom + '_' + c.seed,
                              '', null, null, []), 'duo ' + c.nom);
                }""", {"positif": positif, "neg": NEG, "seed": seed, "nom": nom})
                data = pg.evaluate("""async (f) => {
                    const r = await fetch(CFG.base + '/comfy/view?filename='
                              + encodeURIComponent(f.filename)
                              + '&subfolder=' + encodeURIComponent(f.subfolder || '')
                              + '&type=' + (f.type || 'output'),
                              { headers: { 'Authorization': 'Bearer ' + CFG.key } });
                    return Array.from(new Uint8Array(await r.arrayBuffer()));
                }""", imgs[0])
                dst = os.path.join(SORTIE, "%s_%d.png" % (nom, seed))
                io.open(dst, "wb").write(bytes(data))
                fichiers.setdefault(nom, []).append(dst)
                print("  %-14s seed %d -> %s" % (nom, seed, os.path.basename(dst)))
        br.close()

    vus = juge([f for v in fichiers.values() for f in v])
    if not vus:
        print("\nAUCUN VERDICT. Images : " + SORTIE)
        return 2

    print("\n" + "=" * 72)
    print("VERDICT — visages detectes (la scene en demande DEUX)")
    print("=" * 72)
    scores = {}
    for nom, tag in VARIANTES:
        n = [vus.get(f, -1) for f in fichiers[nom]]
        deux = sum(1 for x in n if x >= 2)
        scores[nom] = deux
        print("  %-14s %-16s deux personnages %d/%d   detail %s"
              % (nom, "« " + (tag or "aucun") + " »", deux, len(n), n))

    ref = scores["V1-2people"]
    tem = scores["V5-temoin"]
    print("\n  L'app envoie aujourd'hui V1 (« 2people ») : %d/%d" % (ref, args.n))
    print("  Sans aucun tag de comptage (temoin)       : %d/%d" % (tem, args.n))
    if ref <= tem:
        print("  => « 2people » ne fait PAS mieux que rien : le tag est inerte.")
    meilleur = max(scores, key=lambda k: scores[k])
    if scores[meilleur] > ref:
        print("  => MEILLEUR : %s (%d/%d, soit %+d vs l'app)"
              % (meilleur, scores[meilleur], args.n, scores[meilleur] - ref))
    else:
        print("  => Aucune formulation ne fait mieux que l'actuelle sur cet echantillon.")
    print("  images : " + SORTIE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
