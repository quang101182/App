# -*- coding: utf-8 -*-
"""R15 (27/09, Quang 12h58 « oui, a la suite » : effacement cible sur les lettres) -- traduire_chapitre.py 2.3.0.

Un texte « hors zones » dont la zone depasse 5 % de la page etait ECARTE (anglais laisse sur l'image) : la boite du modele
deborde du texte, l'effacer en entier blanchit le dessin (essai du 27/09, fond clair >= 70 % : morceaux de cases blanchis
p.43/p.47 -> abandonne). Ici on RESSERRE la zone sur les LETTRES avant d'effacer : composantes sombres de la taille d'un
caractere, qui ne touchent pas le bord, ENTOUREES de fond clair (un trait du dessin est entoure de demi-teintes) ; puis la
boite resserree doit etre du texte net sur fond clair (>= 55 % clair, <= 12 % de demi-teintes). Sinon : ecarte comme avant.
Mesure 27/09 (chapitre webtoon de la secondaire) : 4 textes sur 4 resserres (demi-teintes 2-3 %), 6 zones de dessin sur 6
refusees (la plus proche : 16 %). Suppose scripts_patch_r12_r13.py. Rejouable : python scripts_patch_r15.py <dossier scripts>"""
import os, sys

D = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
p = os.path.join(D, "traduire_chapitre.py")
s = open(p, encoding="utf-8", newline="").read()
if "def boite_lettres(" in s:
    print("deja applique"); sys.exit(0)
if 'VERSION = "2.2.0"' not in s:
    print("ERREUR : appliquer d'abord scripts_patch_r12_r13.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


rep('VERSION = "2.2.0"', 'VERSION = "2.3.0"   # 2.3.0 (R15, 27/09) : grande zone hors bulles RESSERREE sur les lettres au lieu d\'etre ecartee ;')
rep('''def blanchiment(im, rendu, texts):''', '''def boite_lettres(im, t, sombre=110, clair=200):
    """2.3.0 (R15) : la zone t resserree sur ses LETTRES {x, y, w, h}, ou None si ce n'est pas du texte net sur fond clair.
    Lettre = composante sombre de la taille d'un caractere, qui ne touche pas le bord de la zone (cadre, trait de case) et
    ENTOUREE de fond clair ou d'encre (un trait du dessin est entoure de demi-teintes). Mesure 27/09 : texte 2-3 % de
    demi-teintes dans la boite resserree, dessin >= 16 %."""
    import numpy as np
    from scipy import ndimage
    W, H = im.size
    x1, y1 = int(t["x"] * W), int(t["y"] * H)
    x2, y2 = max(int((t["x"] + t["w"]) * W), x1 + 2), max(int((t["y"] + t["h"]) * H), y1 + 2)
    A = np.asarray(im.convert("L").crop((x1, y1, x2, y2)), dtype=np.int16)
    h, w = A.shape
    lab, _ = ndimage.label(A < sombre)
    lettres = []
    for i, sl in enumerate(ndimage.find_objects(lab)):
        if sl is None:
            continue
        gh, gw = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if not (0.006 * H <= gh <= 0.06 * H and gw <= 0.08 * W):
            continue
        if sl[0].start == 0 or sl[1].start == 0 or sl[0].stop == h or sl[1].stop == w:
            continue
        r0, r1, c0, c1 = max(0, sl[0].start - 4), min(h, sl[0].stop + 4), max(0, sl[1].start - 4), min(w, sl[1].stop + 4)
        voisin = A[r0:r1, c0:c1][lab[r0:r1, c0:c1] != i + 1]
        if voisin.size and float(((voisin >= clair) | (voisin < sombre)).mean()) < 0.85:
            continue
        lettres.append(sl)
    if len(lettres) < 4:
        return None
    pad = max(4, int(0.004 * W))
    ya, yb = max(0, min(q[0].start for q in lettres) - pad), min(h, max(q[0].stop for q in lettres) + pad)
    xa, xb = max(0, min(q[1].start for q in lettres) - pad), min(w, max(q[1].stop for q in lettres) + pad)
    B = A[ya:yb, xa:xb]
    if float((B >= clair).mean()) < 0.55 or float(((B >= sombre) & (B < clair)).mean()) > 0.12:
        return None
    return {"x": (x1 + xa) / W, "y": (y1 + ya) / H, "w": (xb - xa) / W, "h": (yb - ya) / H}


def blanchiment(im, rendu, texts):''')
rep('''                    if etat != "bulle" and t["w"] * t["h"] > COMPLEMENT_BOITE_MAX and a.effacement != "local":
                        douteux.append((t, lig, "zone trop grande pour une boite entiere")); continue''',
    '''                    if etat != "bulle" and t["w"] * t["h"] > COMPLEMENT_BOITE_MAX and a.effacement != "local":
                        serre = boite_lettres(im, t)                  # 2.3.0 (R15) : resserrer sur les lettres, sinon ecarter
                        if not serre:
                            douteux.append((t, lig, "zone trop grande pour une boite entiere")); continue
                        t.update(serre)
                        lig["box"] = {k: round(serre[k], 4) for k in ("x", "y", "w", "h")}
                        lig["resserre"] = True
                        stats["resserres"] = stats.get("resserres", 0) + 1''')
open(p, "w", encoding="utf-8", newline="").write(s)
print("ok")
