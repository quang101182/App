# -*- coding: utf-8 -*-
"""Une case doit contenir UNE image, pas une planche. (28/07/2026)

Signale par Quang, capture a l'appui : sa case 5 est sortie avec « plusieurs
petites fenetres dans l'image » -- une planche entiere dessinee A L'INTERIEUR
d'une case. Il le dit lui-meme : « je pense que c'est un probleme de manque de
controle sur le nombre de fenetres dans une image ».

Ce n'est PAS aleatoire. Le prompt reellement enregistre (base, case idx 4) porte :
    ... manga panel, GRID LINES, shibari ...
`grid lines` n'est pas de lui : c'est l'AMELIORATION qui l'a ajoute. Le tag
decrit litteralement des lignes de grille -- et combine a `manga panel`, il
demande une planche. Le meme tag figurait deja dans une autre de ses cases.

Le juge est le detecteur de cases de la PHASE 3 (l'ingestion) : c'est
exactement son metier, compter les cases d'une page. Il se calibre d'abord sur
les DEUX images reelles de Quang -- s'il ne voit pas ce que l'oeil voit, il ne
sert a rien.

Variantes mesurees (memes seeds, meme scene) :
    A  tel quel                          (ce qui est parti)
    B  sans « grid lines »
    C  sans « grid lines » ni « manga panel »
    D  C + negatif anti-planche (comic, 4koma, multiple views, borders...)

Usage:
    python test_une_seule_case.py --calibrer
    python test_une_seule_case.py [--n 4]
"""
import argparse
import io
import json
import os
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ICI = os.path.dirname(os.path.abspath(__file__))
SECRET_FILE = r"C:\Users\quang\Documents\ComfyUI\.studio_secret"
APP_URL = "http://127.0.0.1:8190/manga"
SORTIE = os.path.join(ICI, "essai_out", "une_case")
PY_COMFY = r"C:\Users\quang\Documents\ComfyUI\.venv\Scripts\python.exe"
DETECTEUR = os.path.join(ICI, "models", "manga_panel_detector_fp32.pt")

STYLE = ("masterpiece, best quality, very aesthetic, absurdres, monochrome, greyscale, "
         "manga, screentone, halftone, lineart")
# La scene REELLE de sa case 5, telle qu'enregistree (tags produits par l'app).
SCENE = ("1girl 1boy, bondage, bound, tied to bed, footjob, toes on glans, rubbing, "
         "from side, close-up, detailed, high contrast, black and white, monochrome")
NEG = ("bad quality, worst quality, sketch, censor, watermark, signature, text, "
       "speech bubble, extra digits, bad hands, bad anatomy, color, colored")
# Le vocabulaire danbooru de la PLANCHE : ce sont ces mots qu'il faut interdire.
NEG_PLANCHE = ("comic, 4koma, multiple views, panels, borders, grid, split screen, "
               "sequential art, storyboard, page, montage")

# E = ce que l'app produit REELLEMENT depuis la v1.63.0 : les tags de planche
# retires du positif par le code, et le vocabulaire de la planche au negatif.
# C'est la seule variante qui compte vraiment -- les autres expliquent pourquoi.
VARIANTES = [
    ("E-app-v163", "manga panel, " + SCENE, NEG + ", " + NEG_PLANCHE),
    ("A-tel-quel", "manga panel, grid lines, " + SCENE, NEG),
    ("B-sans-grid", "manga panel, " + SCENE, NEG),
    ("C-sans-panel", SCENE, NEG),
    ("D-neg-planche", SCENE, NEG + ", " + NEG_PLANCHE),
]

# `--duel` : E contre D sur davantage de seeds. Elles ne different que par
# « manga panel », et 4 seeds ne suffisaient pas a les separer (3/4 vs 4/4).
DUEL = [
    ("E-app-v163", "manga panel, " + SCENE, NEG + ", " + NEG_PLANCHE),
    ("D-neg-planche", SCENE, NEG + ", " + NEG_PLANCHE),
]

CODE = """
import sys, json
from ultralytics import YOLO
y = YOLO(sys.argv[1])
seuil = float(sys.argv[2])
out = {}
for f in sys.argv[3:]:
    n = 0
    for r in y(f, verbose=False, conf=seuil):
        n += len(r.boxes or [])
    out[f] = n
print("JSON:" + json.dumps(out))
"""


def compte_cases(fichiers, seuil=0.35):
    """Rend {chemin: nb_cases_detectees}. Vide = l'outil n'a pas pu conclure."""
    for c, quoi in ((PY_COMFY, "le python de ComfyUI"), (DETECTEUR, "le detecteur de cases")):
        if not os.path.isfile(c):
            print("ARRET : %s introuvable (%s)" % (quoi, c))
            print("        -> python scripts/fetch_models.py")
            return {}
    try:
        r = subprocess.run([PY_COMFY, "-c", CODE, DETECTEUR, str(seuil)] + list(fichiers),
                           capture_output=True, timeout=1200)
        s = r.stdout.decode("utf-8", "replace")
        l = [x for x in s.splitlines() if x.startswith("JSON:")]
        if not l:
            print("ARRET : sortie inattendue :")
            print((s or r.stderr.decode("utf-8", "replace"))[-400:])
            return {}
        return json.loads(l[-1][5:])
    except Exception as e:
        print("ARRET : detection impossible (%s)" % e)
        return {}


def calibrer():
    """L'outil voit-il ce que l'oeil voit sur les images REELLES de Quang ?"""
    sortie_projet = os.path.join(ICI, "..", "output", "xxx")
    cas = [
        # Ses deux generations de 12h54-12h55 : PLUSIEURS fenetres (constate par lui).
        (os.path.join(sortie_projet, "mc19fa8c98660215_vms4nr0m8.png"), 2),
        (os.path.join(sortie_projet, "mc19fa8c98660215_vms4nruah.png"), 2),
    ]
    presents = [(f, n) for f, n in cas if os.path.isfile(f)]
    if not presents:
        print("ARRET : les images de Quang sont introuvables — calibration impossible.")
        return 2
    vus = compte_cases([f for f, _ in presents])
    if not vus:
        return 2
    print("CALIBRATION — l'outil voit-il les « fenetres » que Quang a vues ?")
    ok = True
    for f, mini in presents:
        n = vus.get(f, -1)
        bon = n >= mini
        ok = ok and bon
        print("  %-42s au moins %d attendu · vu %d   %s"
              % (os.path.basename(f), mini, n, "OK" if bon else "ECART"))
    print("\n  => %s" % ("UTILISABLE" if ok else
                         "INUTILISABLE : ne pas conclure avec cet outil"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=4)
    ap.add_argument("--seed", type=int, default=972923959)   # LA seed de sa case 5
    ap.add_argument("--calibrer", action="store_true")
    ap.add_argument("--duel", action="store_true")
    args = ap.parse_args()
    if args.calibrer:
        return calibrer()
    from playwright.sync_api import sync_playwright
    os.makedirs(SORTIE, exist_ok=True)

    secret = open(SECRET_FILE, encoding="utf-8").read().strip()
    fich = {}
    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=True, channel="msedge")
        pg = br.new_page()
        pg.set_default_timeout(300000)
        pg.goto(APP_URL + "#k=" + secret, wait_until="domcontentloaded")
        pg.wait_for_function("typeof wfPanel === 'function'")
        jeu = DUEL if args.duel else VARIANTES
        for nom, positif, neg in jeu:
            for k in range(args.n):
                seed = args.seed + k
                imgs = pg.evaluate("""async (c) => {
                    const r = Object.assign({}, recipe(), {
                      neg: c.neg, w: 832, h: 1216, steps: 30, cfg: 5.5,
                      sampler: 'euler_ancestral', lora: '' });
                    return await runGraph(
                      wfPanel(r, c.style + ', ' + c.positif, c.seed,
                              'manga/_banc_case/' + c.nom + '_' + c.seed,
                              '', null, null, []), 'case ' + c.nom);
                }""", {"positif": positif, "neg": neg, "style": STYLE,
                       "seed": seed, "nom": nom})
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
                fich.setdefault(nom, []).append(dst)
                print("  %-14s seed %d -> %s" % (nom, seed, os.path.basename(dst)))
        br.close()

    vus = compte_cases([f for v in fich.values() for f in v])
    if not vus:
        print("\nAUCUN VERDICT. Images : " + SORTIE)
        return 2
    print("\n" + "=" * 70)
    print("VERDICT — fenetres detectees dans UNE case (il en faut UNE)")
    print("=" * 70)
    for nom, _, _ in jeu:
        n = [vus.get(f, -1) for f in fich[nom]]
        propres = sum(1 for x in n if x <= 1)
        print("  %-14s une seule image : %d/%d   detail %s" % (nom, propres, len(n), n))
    print("  images : " + SORTIE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
