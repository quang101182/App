"""Detection de cases (demo, lecture seule) : blocs d'encre separes par des gouttieres claires. Ordre manga (droite->gauche)."""
import numpy as np
from PIL import Image
from scipy import ndimage
def cases(path):
    im = Image.open(path).convert("L"); W, H = im.size
    a = np.asarray(im)
    encre = a < 200
    encre = ndimage.binary_dilation(encre, iterations=3)
    lab, n = ndimage.label(encre)
    boites = []
    for sl in ndimage.find_objects(lab):
        y0, y1, x0, x1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
        if (x1 - x0) * (y1 - y0) >= 0.02 * W * H and (x1 - x0) > 0.1 * W and (y1 - y0) > 0.05 * H:
            boites.append([x0, y0, x1, y1])
    # retire les boites contenues dans une autre
    boites = [b for b in boites if not any(o is not b and o[0] <= b[0] and o[1] <= b[1] and o[2] >= b[2] and o[3] >= b[3] for o in boites)]
    if not boites or (len(boites) == 1 and (boites[0][2]-boites[0][0])*(boites[0][3]-boites[0][1]) > 0.85*W*H):
        return [[0, 0, W, H]], (W, H)
    # ordre de lecture : rangees (recouvrement vertical), puis droite -> gauche
    boites.sort(key=lambda b: b[1]); rangees = []
    for b in boites:
        for r in rangees:
            if b[1] < max(x[3] for x in r) - 0.3 * (b[3] - b[1]): r.append(b); break
        else: rangees.append([b])
    ordre = [b for r in rangees for b in sorted(r, key=lambda b: -b[2])]
    return ordre, (W, H)
