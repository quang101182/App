# -*- coding: utf-8 -*-
"""« Gros plan sans visage » : quelle parade marche VRAIMENT ? (28/07/2026)

Constat du banc live : l'app retire bien l'identite (plus d'uniforme, plus de
cheveux nommes) et met `face` au negatif -- et le modele dessine quand meme un
visage plein cadre. Retirer l'identite ne suffit donc pas.

Trois hypotheses, mesurees au lieu d'etre choisies :
  A (actuel)  `1girl, close-up on clenched hands`      / NEG: face
  B  sans le comptage `1girl`                          / NEG: face, head, portrait, looking at viewer
  C  B + des tags POSITIFS de recadrage (out of frame, focus on hands, cropped)

Meme seed pour les trois : seule la formulation change. Le juge est un detecteur
de visage (le meme que `mesure_cadrage.py`), pas mon oeil -- et il DIT quand il
ne peut pas fonctionner, plutot que de repondre « pas de visage » en silence.

Usage:
    python test_sans_visage.py [--seed N] [--n 3]
"""
import argparse
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
APP_URL = "http://127.0.0.1:8190/manga"
SORTIE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "essai_out", "sans_visage")

STYLE = ("masterpiece, best quality, very aesthetic, absurdres, monochrome, greyscale, "
         "manga, screentone, halftone, lineart")
NEG_BASE = ("bad quality, worst quality, sketch, censor, watermark, signature, text, "
            "speech bubble, extra digits, bad hands, bad anatomy, color, colored")

VARIANTES = [
    ("A-actuel", "1girl, close-up on clenched hands", "face"),
    ("B-sans-comptage", "close-up on clenched hands",
     "face, head, portrait, looking at viewer, 1girl, solo"),
    ("C-recadrage",
     "extreme close-up, focus on hands, clenched hands, head out of frame, cropped",
     "face, head, portrait, looking at viewer, 1girl, solo, full body"),
]


# `ultralytics` vit dans le venv de ComfyUI, pas dans le Python qui pilote le
# navigateur. On ne l'installe pas deux fois : on appelle CE python-la, et on
# utilise le MEME modele que crop_ref.py / compare_lora.py -- deux juges
# differents ne se comparent pas.
PY_COMFY = r"C:\Users\quang\Documents\ComfyUI\.venv\Scripts\python.exe"
MODELE_FACE = (r"C:\Users\quang\Documents\ComfyUI\models"
               r"\ultralytics\bbox\face_yolov8m.pt")

CODE_JUGE = (
    "import sys, json\n"
    "from ultralytics import YOLO\n"
    "from PIL import Image\n"
    "y = YOLO(sys.argv[1])\n"
    "out = {}\n"
    "for f in sys.argv[2:]:\n"
    "    im = Image.open(f); W, H = im.size; best = 0.0\n"
    "    for r in y(f, verbose=False):\n"
    "        for b in (r.boxes or []):\n"
    "            x1, y1, x2, y2 = [float(v) for v in b.xyxy[0]]\n"
    "            best = max(best, ((x2-x1)*(y2-y1))/(W*H))\n"
    "    out[f] = best\n"
    "print(json.dumps(out))\n")


def juge_visages(fichiers):
    """Rend {chemin: part_du_visage}. Vide = l'outil n'a PAS pu conclure.

    Un secours muet a deja fait accuser l'OUTIL au lieu de l'ENVIRONNEMENT
    (piege connu du projet) : ici l'echec est explicite et remonte tel quel.
    """
    import subprocess
    for chemin, quoi in ((PY_COMFY, "le python de ComfyUI"),
                         (MODELE_FACE, "le modele de visage")):
        if not os.path.isfile(chemin):
            print("  ARRET : %s est introuvable (%s)" % (quoi, chemin))
            return {}
    try:
        r = subprocess.run([PY_COMFY, "-c", CODE_JUGE, MODELE_FACE] + list(fichiers),
                           capture_output=True, timeout=600)
        return json.loads(r.stdout.decode("utf-8", "replace").strip().splitlines()[-1])
    except Exception as e:
        print("  ARRET : la detection a echoue (%s)" % e)
        return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=424242)
    ap.add_argument("--n", type=int, default=3, help="essais par variante")
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright
    os.makedirs(SORTIE, exist_ok=True)

    secret = open(SECRET_FILE, encoding="utf-8").read().strip()
    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=True, channel="msedge")
        pg = br.new_page()
        pg.set_default_timeout(300000)
        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_function("typeof wfPanel === 'function'")

        resultats = {}
        for nom, positif, negPlus in VARIANTES:
            resultats[nom] = []
            for k in range(args.n):
                seed = args.seed + k
                # On appelle le GRAPHE DE L'APP, pas une copie : si wfPanel change,
                # ce banc suit. Une copie du graphe mesurerait un moteur imaginaire.
                fichiers = pg.evaluate("""async (c) => {
                    const r = Object.assign({}, recipe(), {
                      neg: c.neg, w: 832, h: 1216, steps: 30, cfg: 5.5,
                      sampler: 'euler_ancestral', lora: '' });
                    const imgs = await runGraph(
                      wfPanel(r, c.style + ', ' + c.positif, c.seed,
                              'manga/_banc_visage/' + c.nom + '_' + c.seed,
                              '', null, null, []), 'banc ' + c.nom);
                    return imgs;
                }""", {"positif": positif, "neg": NEG_BASE + ", " + negPlus,
                       "style": STYLE, "seed": seed, "nom": nom})
                src = fichiers[0]
                dst = os.path.join(SORTIE, "%s_%d.png" % (nom, seed))
                # On rapatrie par le proxy : les sorties manga ne restent JAMAIS
                # dans le dossier de Generate Studio (regle Quang du 26/07).
                data = pg.evaluate("""async (f) => {
                    const r = await fetch(CFG.base + '/comfy/view?filename='
                              + encodeURIComponent(f.filename)
                              + '&subfolder=' + encodeURIComponent(f.subfolder || '')
                              + '&type=' + (f.type || 'output'),
                              { headers: { 'Authorization': 'Bearer ' + CFG.key } });
                    const b = new Uint8Array(await r.arrayBuffer());
                    return Array.from(b);
                }""", src)
                io.open(dst, "wb").write(bytes(data))
                resultats[nom].append(dst)
                print("  %-16s seed %d -> %s" % (nom, seed, os.path.basename(dst)))
        br.close()

    tous = [f for v in resultats.values() for f in v]
    parts = juge_visages(tous)
    if not parts:
        print("\nAUCUN VERDICT : le juge n a pas pu conclure. Les images sont dans "
              + SORTIE + " — a regarder a l oeil, mais NE PAS conclure au chiffre.")
        return 2

    print("\n=== VERDICT (part de l'image occupee par un visage, plus bas = mieux) ===")
    for nom, fichiers in resultats.items():
        mesures = [parts.get(f, -1) for f in fichiers]
        mesures = [m for m in mesures if m >= 0]
        if not mesures:
            print("  %-16s : NON MESURE" % nom)
            continue
        moy = sum(mesures) / len(mesures)
        sans = sum(1 for m in mesures if m < 0.02)
        petit = sum(1 for m in mesures if m < 0.10)
        print("  %-16s : moyenne %.3f · aucun visage %d/%d · visage < 10%% %d/%d"
              % (nom, moy, sans, len(mesures), petit, len(mesures)))
    print("images : " + SORTIE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
