"""Effacement LOCAL du texte pose sur le DESSIN (feuille de route 4-nonies, etape 2 -- 24/09/2026).

Mesure de l'exploration (§ 4-octies) : un rectangle blanc mange la case ; les boites de texte (Gemini / YOLO) tombent A COTE
des lettres. D'ou deux briques locales, sur la carte graphique :
  1. comic-text-detector (ONNX, via OpenCV DNN : rien a installer) -> probabilite « lettre » au pixel ;
     on garde les MORCEAUX du masque qui touchent la boite elargie (dans le sens de la colonne), chacun EN ENTIER ;
  2. LaMa manga (lama_large_512px, architecture de manga-image-translator GPL-3.0, lama_manga_arch.py) reconstitue le
     dessin sous les lettres, zone par zone (recadree avec du contexte, a sa resolution).
Les vraies bulles blanches ne passent PAS par ici : leur effacement deterministe reste le meilleur.

API :
  proba_lettres(im)                          -> uint8 HxW (255 = lettre)
  zone_lettres(proba, box, W, H)             -> (masque HxW, boite reelle en fractions) ou (None, None)
  reconstituer(img_rgb, masque)              -> RGB uint8
  poser_avec_halo(rendu, boite, texte, taille_max) (utilise traduire_chapitre.poser_texte) -> (image, infos)
Modeles : C:/Users/quang/Documents/MangaStudio-donnees/modeles (sur C:, regle Quang).
"""
import os
import numpy as np
import cv2

VERSION = "1.2.0"
MODELES = os.path.join(os.path.expanduser("~"), "Documents", "MangaStudio-donnees", "modeles")
CTD = os.path.join(MODELES, "comictextdetector.pt.onnx")
LAMA = os.path.join(MODELES, "lama_large_512px.ckpt")
SEUIL = 0.15                   # essai v3 : 0,3 laissait des morceaux de caracteres
HALO = 11                      # contour blanc autour du francais pose sur un dessin (essai v3)
_M = {}


def disponible():
    return os.path.isfile(CTD) and os.path.isfile(LAMA)


def _passe(rgb, taille=1024):
    if "ctd" not in _M:
        _M["ctd"] = cv2.dnn.readNetFromONNX(CTD)
    h, w = rgb.shape[:2]
    k = taille / max(h, w)
    nh, nw = int(round(h * k)), int(round(w * k))
    x = np.zeros((taille, taille, 3), np.float32)
    x[:nh, :nw] = cv2.resize(rgb, (nw, nh), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    _M["ctd"].setInput(x.transpose(2, 0, 1)[None])
    seg = _M["ctd"].forward("seg")[0, 0][:nh, :nw]
    return cv2.resize(seg, (w, h), interpolation=cv2.INTER_LINEAR)


def proba_lettres(im, seuil=SEUIL):
    """Page haute : fenetres CARREES qui se chevauchent (reduite a 1024 px, la lettre devient trop petite)."""
    rgb = np.array(im.convert("RGB"))
    H, W = rgb.shape[:2]
    if H <= W * 1.2:
        p = _passe(rgb)
    else:
        p = np.zeros((H, W), np.float32)
        y, pas = 0, int(W * 0.75)
        while True:
            y0 = min(y, H - W)
            p[y0:y0 + W] = np.maximum(p[y0:y0 + W], _passe(rgb[y0:y0 + W]))
            if y0 + W >= H:
                break
            y += pas
    return ((p > seuil) * 255).astype(np.uint8)


def zone_lettres(proba, b, W, H, marge=0.8, marge_long=0.8, dedans_min=0.5):
    """Les lettres d'UNE zone de texte. v1.1.0 (banc OPM ch.3 p.4 et p.9) : garder les morceaux « en entier » attrapait
    les onomatopees DESSINEES voisines et faisait partager la meme zone a deux bulles (textes superposes). Desormais :
    morceau garde seulement s'il est MAJORITAIREMENT dans la boite elargie, puis coupe a cette boite."""
    bx, by, bw, bh = b["x"] * W, b["y"] * H, b["w"] * W, b["h"] * H
    mx, my = (marge_long, marge) if bw > bh else (marge, marge_long)      # plus large dans le SENS de la colonne
    x1, y1 = int(max(0, bx - mx * bw - 10)), int(max(0, by - my * bh - 10))
    x2, y2 = int(min(W, bx + bw * (1 + mx) + 10)), int(min(H, by + bh * (1 + my) + 10))
    lettres = cv2.dilate(proba, np.ones((9, 9), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats((lettres > 0).astype(np.uint8), 8)
    dans = np.bincount(lab[y1:y2, x1:x2].ravel(), minlength=n)
    ids = [i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] >= 150 and dans[i] >= dedans_min * st[i, cv2.CC_STAT_AREA]]
    if not ids:
        return None, None
    m = np.zeros((H, W), np.uint8)
    m[y1:y2, x1:x2] = np.isin(lab[y1:y2, x1:x2], ids).astype(np.uint8) * 255
    m = cv2.dilate(m, np.ones((5, 5), np.uint8))                          # + le contour blanc des cris
    ys, xs = np.where(m > 0)
    return m, {"x": xs.min() / W, "y": ys.min() / H, "w": (xs.max() - xs.min() + 1) / W, "h": (ys.max() - ys.min() + 1) / H}


def chevauche(a, b, seuil=0.15):
    """Deux boites (fractions) se chevauchent-elles de plus de `seuil` de la plus petite ?"""
    ix = max(0.0, min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"]))
    iy = max(0.0, min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"]))
    return ix * iy > seuil * min(a["w"] * a["h"], b["w"] * b["h"])


def _lama():
    if "lama" not in _M:
        import torch
        import lama_manga_arch as la
        _M["lama"] = la.load_lama_mpe(LAMA, "cuda" if torch.cuda.is_available() else "cpu", use_mpe=False, large_arch=True)
    return _M["lama"]


def _crop(img, masque):
    import torch
    H, W = masque.shape
    k = min(1.0, 1024 / max(H, W))
    x, m = img, masque
    if k < 1:
        x = cv2.resize(img, (int(W * k), int(H * k)), interpolation=cv2.INTER_AREA)
        m = cv2.resize(masque, (int(W * k), int(H * k)), interpolation=cv2.INTER_NEAREST)
    h, w = m.shape
    ph, pw = (8 - h % 8) % 8, (8 - w % 8) % 8
    x = np.pad(x, ((0, ph), (0, pw), (0, 0)), mode="reflect")
    m = np.pad(m, ((0, ph), (0, pw)), mode="reflect")
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    xt = torch.from_numpy(x).permute(2, 0, 1)[None].float().to(dev) / 255
    mt = (torch.from_numpy(m)[None, None].float().to(dev) > 127).float()
    with torch.no_grad():
        out = _lama()(xt * (1 - mt), mt)
    out = (out[0].float().permute(1, 2, 0).clamp(0, 1).cpu().numpy() * 255).astype(np.uint8)[:h, :w]
    return cv2.resize(out, (W, H), interpolation=cv2.INTER_CUBIC) if k < 1 else out


def reconstituer(img, masque, contexte=192):
    """Une passe PAR ZONE, recadree avec du contexte : la page entiere reduite a 1024 px rendait les zones floues."""
    res = img.copy()
    H, W = masque.shape
    n, lab, st, _ = cv2.connectedComponentsWithStats((cv2.dilate(masque, np.ones((25, 25), np.uint8)) > 0).astype(np.uint8), 8)
    for i in range(1, n):
        x, y, w, h = st[i, 0], st[i, 1], st[i, 2], st[i, 3]
        x1, y1, x2, y2 = max(0, x - contexte), max(0, y - contexte), min(W, x + w + contexte), min(H, y + h + contexte)
        mc = masque[y1:y2, x1:x2] * (lab[y1:y2, x1:x2] == i)
        if not mc.any():
            continue
        out = _crop(res[y1:y2, x1:x2], mc)
        sel = mc > 127
        res[y1:y2, x1:x2][sel] = out[sel]
    return res


def poser_avec_halo(rendu, boite, texte, taille_max, poser_texte):
    """Le francais pose par la fonction de l'app, sur un calque, avec un contour blanc (lisible sur un dessin)."""
    from PIL import Image
    calque = Image.new("RGB", rendu.size, (255, 255, 255))
    r = poser_texte(calque, boite, texte, False, taille_max=taille_max)
    a = np.array(calque.convert("L")) < 128
    base = np.array(rendu.convert("RGB"))
    base[cv2.dilate(a.astype(np.uint8), np.ones((HALO, HALO), np.uint8)) > 0] = 255
    base[a] = 0
    return Image.fromarray(base), r
