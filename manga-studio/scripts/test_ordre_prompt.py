# -*- coding: utf-8 -*-
"""L'ORDRE du prompt change-t-il le respect de la demande ? (28/07/2026)

Hypothese posee -- et NON verifiee -- le 28/07 : sur le projet « Magic woman »,
le style declare 31 tags et la demande de Quang arrive en ~45e position, au-dela
des 77 tokens que CLIP encode dans un chunk. Elle pesait donc presque rien.

⚠ Une hypothese plausible n'est pas un fait. Le 28/07 au matin, TROIS
explications plausibles du meme defaut ont ete infirmees par la mesure, et
chacune aurait coute un chantier. Celle-ci passe donc au banc avant d'etre
appliquee -- ou abandonnee.

Deux ordres, meme contenu, memes seeds :
  A (actuel)  style long, puis identite, puis LA DEMANDE
  B (teste)   identite, puis LA DEMANDE, puis le style long

Le juge est OBJECTIF : un detecteur de visage (`face_yolov8m`, le meme que
`crop_ref.py`). On n'utilise donc que des demandes dont le respect se compte :
  D1  « aucun personnage »          -> 0 visage attendu
  D2  « gros plan mains, sans tete » -> 0 visage attendu
  D3  « deux personnages face a face » -> 2 visages attendus
Un juge qui rendrait un avis (« est-ce fidele ? ») ne trancherait rien : deux
instruments non calibres qui s'accordent se trompent ensemble (lecon du 27/07).

Usage:
    python test_ordre_prompt.py [--n 4]
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
SORTIE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "essai_out", "ordre")
PY_COMFY = r"C:\Users\quang\Documents\ComfyUI\.venv\Scripts\python.exe"
MODELE_FACE = (r"C:\Users\quang\Documents\ComfyUI\models"
               r"\ultralytics\bbox\face_yolov8m.pt")

# Le style REEL du projet « Magic woman » : c'est lui qui noie la demande.
STYLE = ("masterpiece, best quality, very aesthetic, absurdres, monochrome, greyscale, "
         "manga, screentone, halftone, lineart, ink, high contrast, black and white, "
         "manga style, heavy inking, crosshatching, dynamic lineart, thick outlines, "
         "dramatic shading, epic mood, fantasy atmosphere, dark fantasy, heroic fantasy, "
         "detailed linework, chiaroscuro, gritty texture, ink wash, stark lighting")
IDENT = "1girl, black hair, short hair, sharp eyes, pale skin, sailor uniform"
NEG = ("bad quality, worst quality, sketch, censor, watermark, signature, text, "
       "speech bubble, extra digits, bad hands, bad anatomy, color, colored")

# (id, demande, identite injectee ?, visages attendus)
DEMANDES = [
    ("D1-vide", "empty school hallway, morning light, no humans", False, 0),
    ("D2-mains", "extreme close-up, focus on hands, clenched hands, "
                 "head out of frame, cropped", False, 0),
    ("D3-duo", "2people, two characters facing each other, wide shot, dojo", True, 2),
]


def juge(fichiers):
    code = ("import sys, json\n"
            "from ultralytics import YOLO\n"
            "from PIL import Image\n"
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
    ap.add_argument("--n", type=int, default=4, help="seeds par combinaison")
    ap.add_argument("--seed", type=int, default=770000)
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

        for nom, demande, avecIdent, attendus in DEMANDES:
            ident = IDENT if avecIdent else ""
            ordres = {
                # A : ce que fait l'app aujourd'hui.
                "A": ", ".join([x for x in [STYLE, ident, demande] if x]),
                # B : la demande remonte devant le style.
                "B": ", ".join([x for x in [ident, demande, STYLE] if x]),
            }
            for cle, positif in ordres.items():
                for k in range(args.n):
                    seed = args.seed + k
                    imgs = pg.evaluate("""async (c) => {
                        const r = Object.assign({}, recipe(), {
                          neg: c.neg, w: 832, h: 1216, steps: 30, cfg: 5.5,
                          sampler: 'euler_ancestral', lora: '' });
                        return await runGraph(
                          wfPanel(r, c.positif, c.seed,
                                  'manga/_banc_ordre/' + c.nom + '_' + c.seed,
                                  '', null, null, []), 'ordre ' + c.nom);
                    }""", {"positif": positif, "neg": NEG, "seed": seed,
                           "nom": nom + "_" + cle})
                    data = pg.evaluate("""async (f) => {
                        const r = await fetch(CFG.base + '/comfy/view?filename='
                                  + encodeURIComponent(f.filename)
                                  + '&subfolder=' + encodeURIComponent(f.subfolder || '')
                                  + '&type=' + (f.type || 'output'),
                                  { headers: { 'Authorization': 'Bearer ' + CFG.key } });
                        return Array.from(new Uint8Array(await r.arrayBuffer()));
                    }""", imgs[0])
                    dst = os.path.join(SORTIE, "%s_%s_%d.png" % (nom, cle, seed))
                    io.open(dst, "wb").write(bytes(data))
                    fichiers.setdefault((nom, cle), []).append(dst)
                    print("  %-10s ordre %s seed %d -> %s"
                          % (nom, cle, seed, os.path.basename(dst)))
        br.close()

    tous = [f for v in fichiers.values() for f in v]
    vus = juge(tous)
    if not vus:
        print("\nAUCUN VERDICT : les images sont dans " + SORTIE)
        return 2

    print("\n" + "=" * 74)
    print("VERDICT — visages detectes vs attendus (l'ordre change-t-il le respect ?)")
    print("=" * 74)
    total = {"A": 0, "B": 0}
    for nom, demande, avecIdent, attendus in DEMANDES:
        ligne = "  %-10s attendu %d :" % (nom, attendus)
        for cle in ("A", "B"):
            n = [vus.get(f, -1) for f in fichiers[(nom, cle)]]
            bons = sum(1 for x in n if x == attendus)
            total[cle] += bons
            ligne += "   %s %d/%d %s" % (cle, bons, len(n), n)
        print(ligne)
    n_tot = len(DEMANDES) * args.n
    print("\n  TOTAL   A (actuel) %d/%d   ·   B (demande en tete) %d/%d"
          % (total["A"], n_tot, total["B"], n_tot))
    ecart = total["B"] - total["A"]
    if abs(ecart) <= max(1, n_tot // 10):
        print("  => ECART NON SIGNIFICATIF sur cet echantillon : l'ordre ne tranche pas.")
        print("     Ne pas changer l'app sur cette base -- ce serait un chantier gratuit.")
    else:
        print("  => ECART REEL (%+d) en faveur de %s." % (ecart, "B" if ecart > 0 else "A"))
    print("  images : " + SORTIE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
