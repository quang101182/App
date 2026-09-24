"""ESSAI (24/09) : masque des LETTRES au pixel avec comic-text-detector (ONNX, via OpenCV DNN : rien a installer).

Sortie `seg` (1x1x1024x1024) = probabilite « texte » par pixel. Ne modifie rien dans l'app.
  masque_texte(im) -> uint8 HxW (255 = lettre), a la taille de la page
Usage (planche de controle, masque en rouge) :
  python essai_masque_texte.py one-punch-man ch_4:17 ch_3:7 --out DIR
"""
import argparse, json, os, sys, time
import numpy as np
import cv2
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SRC = os.path.normpath(os.path.join(HERE, "..", "sources"))
# modeles locaux lourds sur C: (Quang 24/09 : D: est petit) -- a cote des donnees de l'app, hors depot
MODELES = os.path.join(os.path.expanduser("~"), "Documents", "MangaStudio-donnees", "modeles")
MODELE = os.path.join(MODELES, "comictextdetector.pt.onnx")
TAILLE = 1024
_NET = {}


def _passe(rgb):
    """Une passe 1024x1024 (letterbox en haut a gauche, bourrage noir) -> proba HxW de l'entree."""
    if "n" not in _NET:
        _NET["n"] = cv2.dnn.readNetFromONNX(MODELE)
    h, w = rgb.shape[:2]
    k = TAILLE / max(h, w)
    nh, nw = int(round(h * k)), int(round(w * k))
    x = np.zeros((TAILLE, TAILLE, 3), np.float32)
    x[:nh, :nw] = cv2.resize(rgb, (nw, nh), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    _NET["n"].setInput(x.transpose(2, 0, 1)[None])
    seg = _NET["n"].forward("seg")[0, 0][:nh, :nw]
    return cv2.resize(seg, (w, h), interpolation=cv2.INTER_LINEAR)


def masque_texte(im, seuil=0.3, tuiles=True):
    """Proba de texte a la taille de la page. Page haute : fenetres CARREES qui se chevauchent (sinon la page reduite a
    1024 px de haut rend les lettres trop petites)."""
    rgb = np.array(im.convert("RGB"))
    H, W = rgb.shape[:2]
    if not tuiles or H <= W * 1.2:
        p = _passe(rgb)
    else:
        p = np.zeros((H, W), np.float32)
        pas = int(W * 0.75)
        y = 0
        while True:
            y0 = min(y, H - W)
            p[y0:y0 + W] = np.maximum(p[y0:y0 + W], _passe(rgb[y0:y0 + W]))
            if y0 + W >= H:
                break
            y += pas
    return ((p > seuil) * 255).astype(np.uint8)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("serie"); ap.add_argument("pages", nargs="+"); ap.add_argument("--out", required=True)
    ap.add_argument("--sans-tuiles", action="store_true")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    for x in a.pages:
        ch, n = x.split(":")
        t = json.load(open(os.path.join(SRC, a.serie, ch, "traduction", "fr", "traduction.json"), encoding="utf-8"))
        p = [q for q in t["pages"] if q["page"] == int(n)][0]
        im = Image.open(os.path.join(SRC, a.serie, ch, p["source"])).convert("RGB")
        t0 = time.time(); m = masque_texte(im, tuiles=not a.sans_tuiles); dt = time.time() - t0
        v = np.array(im); v[m > 0] = (0.4 * v[m > 0] + 0.6 * np.array([255, 0, 0])).astype(np.uint8)
        out = Image.fromarray(v); out.thumbnail((1400, 1400))
        out.save(os.path.join(a.out, "masque_%s_%s_p%03d.png" % (a.serie, ch, int(n))))
        print("%s p.%s : %.1f %% de la page = texte, %.1f s" % (ch, n, 100 * (m > 0).mean(), dt))
