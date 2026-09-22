"""Blocs d'un webtoon : zones entre des rangees UNIES (gouttieres), de haut en bas."""
import numpy as np
from PIL import Image
def bandes(path, tol=24, gmin=14, hmin=90):
    a = np.asarray(Image.open(path).convert("L"), dtype=np.int16); H, W = a.shape
    unie = (a.max(axis=1) - a.min(axis=1)) <= tol
    out, y = [], 0
    while y < H:
        if unie[y]: y += 1; continue
        y0 = y
        while y < H:
            if unie[y]:
                k = y
                while k < H and unie[k]: k += 1
                if k - y >= gmin or k == H: break
                y = k
            else: y += 1
        if y - y0 >= hmin: out.append([0, y0, W, y])
    return out, (W, H)
