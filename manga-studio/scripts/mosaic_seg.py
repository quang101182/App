# -*- coding: utf-8 -*-
"""Detection des zones de mosaique par le modele DEDIE de DeepMosaics (BiSeNet).

Pourquoi pas mon detecteur maison : sur une illustration numerique, les aplats
sont parfaitement uniformes -> le critere "plateaux + grille" matche partout
(il sortait une zone couvrant 26 % de la page). Meme lecon que pour le
decoupage des cases : sur du vrai materiel, un modele entraine bat une
heuristique ecrite a la main.

On n'utilise QUE le segmenteur (`mosaic_position.pth`, 49 Mo, deja present chez
Quang), pas le pipeline video casse : on veut un MASQUE, l'inpainting sera fait
par Illustrious qui, lui, sait dessiner du manga.

Usage: python mosaic_seg.py <image> [--all]
"""
import os, sys
import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFilter

DM = r"D:/Download/02-Apps-Web/Repo-github/App/demosaic-pipeline/DeepMosaics"
MODEL = r"D:/Download/02-Apps-Web/Repo-github/App/demosaic-pipeline/models/mosaic_position.pth"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DM)

from models.BiSeNet_model import BiSeNet          # noqa: E402
from util import image_processing as impro        # noqa: E402


def segment(path, all_areas=True, threshold=64):
    net = BiSeNet(num_classes=1, context_path='resnet18', train_flag=False)
    net.load_state_dict(torch.load(MODEL, map_location="cpu", weights_only=False))
    net = net.cuda().eval()

    im = Image.open(path).convert("RGB")
    W, H = im.size
    img = np.asarray(im)[:, :, ::-1].copy()        # BGR, comme DeepMosaics

    size = 360
    small = impro.resize(img, size)
    h, w = small.shape[:2]
    small = small[(h - size) // 2:(h - size) // 2 + size, (w - size) // 2:(w - size) // 2 + size]
    x = small.astype(np.float32) / 255.0
    x = torch.from_numpy(x.transpose(2, 0, 1))[None].cuda()
    with torch.no_grad():
        out = net(x)
    m = (out[0][0].cpu().numpy() * 255).clip(0, 255).astype(np.uint8)

    mask = Image.fromarray(m).resize((W, H), Image.BILINEAR)
    mask = mask.point(lambda v: 255 if v > threshold else 0)
    mask = mask.filter(ImageFilter.MaxFilter(9))   # marge autour de la zone

    a = np.asarray(mask) > 127
    cov = 100.0 * a.mean()
    ys, xs = np.nonzero(a)
    base = os.path.splitext(os.path.basename(path))[0]
    if len(xs) == 0:
        print("%s : AUCUNE mosaique detectee" % base, flush=True)
        return None
    x1, x2, y1, y2 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
    print("%s  %dx%d  couverture du masque %.2f%%  enveloppe %d,%d -> %d,%d"
          % (base, W, H, cov, x1, y1, x2, y2), flush=True)

    mask.save(os.path.join(HERE, "seg_%s_mask.png" % base))
    vis = im.copy()
    red = Image.new("RGB", (W, H), (255, 0, 255))
    vis = Image.composite(Image.blend(vis, red, 0.45), vis, mask)
    ImageDraw.Draw(vis).rectangle([x1, y1, x2, y2], outline=(0, 255, 0), width=4)
    vis.save(os.path.join(HERE, "seg_%s_vis.jpg" % base), quality=90)
    return {"cov": cov, "box": (x1, y1, x2, y2)}


if __name__ == "__main__":
    segment(sys.argv[1], all_areas="--all" in sys.argv)
