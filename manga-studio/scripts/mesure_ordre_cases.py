# -*- coding: utf-8 -*-
"""Mesure (LECTURE SEULE, 27/09) : l'ordre de lecture actuel des bulles (numero de detection) contre un ordre CASE PAR CASE
(manga : rangees de cases de haut en bas, dans une rangee de DROITE a GAUCHE ; dans une case, de haut en bas puis de droite
a gauche). Quang 27/09 17h05 : « une bulle en bas a droite lue avant celle en bas a gauche, puis on revient ».
Ne modifie rien. Sort : pages comparees, pages dont l'ordre changerait, exemples, et une image annotee par exemple.
Usage : python mesure_ordre_cases.py [--sources DIR] [--exemples N] [--images DOSSIER]"""
import argparse, json, os

ap = argparse.ArgumentParser()
ap.add_argument("--sources", default=os.path.expanduser(r"~\Documents\MangaStudio-donnees\sources"))
ap.add_argument("--exemples", type=int, default=6)
ap.add_argument("--images", default="")
a = ap.parse_args()


def lire(f):
    try:
        return json.load(open(f, encoding="utf-8"))
    except Exception:
        return None


def rangees(cases):
    """cases [x1,y1,x2,y2] -> liste ordonnee (manga) ; une case rejoint une rangee si elle chevauche sa hauteur a 50 %."""
    rs = []
    for c in sorted(cases, key=lambda c: c[1]):
        h = c[3] - c[1]
        for r in rs:
            ov = min(r["y2"], c[3]) - max(r["y1"], c[1])
            if ov > 0.5 * min(h, r["y2"] - r["y1"]):
                r["cs"].append(c); r["y1"] = min(r["y1"], c[1]); r["y2"] = max(r["y2"], c[3]); break
        else:
            rs.append({"y1": c[1], "y2": c[3], "cs": [c]})
    out = []
    for r in sorted(rs, key=lambda r: r["y1"]):
        out += sorted(r["cs"], key=lambda c: -c[2])
    return out


def ordre_cases(bulles, cases, W, H):
    oc = rangees(cases)
    def case_de(b):
        cx, cy = (b["box"]["x"] + b["box"]["w"] / 2) * W, (b["box"]["y"] + b["box"]["h"] / 2) * H
        best, dm = None, 1e18
        for i, c in enumerate(oc):
            d = max(c[0] - cx, 0, cx - c[2]) ** 2 + max(c[1] - cy, 0, cy - c[3]) ** 2
            if d < dm:
                dm, best = d, i
        return best if best is not None else 999
    def cle(b):
        return (case_de(b), round(b["box"]["y"] / 0.06), -(b["box"]["x"] + b["box"]["w"]))
    return [b["id"] for b in sorted(bulles, key=cle)]


tot_p = diff_p = 0
exemples = []
for serie in sorted(os.listdir(a.sources)):
    sd = os.path.join(a.sources, serie)
    if not os.path.isdir(sd):
        continue
    for ch in sorted(os.listdir(sd)):
        cd = os.path.join(sd, ch)
        tr = lire(os.path.join(cd, "traduction", "fr", "traduction.json"))
        cs = lire(os.path.join(cd, "cases.json"))
        man = lire(os.path.join(cd, "manifest.json"))
        if not (tr and cs and man) or cs.get("format") != "manga":
            continue
        fich = [q.get("file") for q in man.get("pages") or []]
        for p in tr.get("pages") or []:
            n = p.get("page") or 0
            pg = (cs.get("pages") or {}).get(fich[n - 1] if 0 < n <= len(fich) else "")
            bl = [b for b in p.get("bulles") or [] if b.get("type") in ("dialogue", "narration") and b.get("box")]
            if not pg or not pg.get("cases") or len(bl) < 2:
                continue
            tot_p += 1
            act = [b["id"] for b in sorted(bl, key=lambda b: b["id"])]
            nouv = ordre_cases(bl, pg["cases"], pg["W"], pg["H"])
            if act != nouv:
                diff_p += 1
                exemples.append((serie + "/" + ch, n, act, nouv, os.path.join(cd, fich[n - 1]), bl))
print("pages manga traduites comparees (>= 2 bulles, cases connues) : %d" % tot_p)
print("pages dont l'ordre CHANGERAIT avec le tri case par case : %d (%.0f %%)" % (diff_p, 100.0 * diff_p / max(1, tot_p)))
for (c, n, act, nouv, img, bl) in exemples[:a.exemples]:
    print("  %s p.%d  actuel %s  ->  cases %s" % (c, n, act, nouv))
if a.images and exemples:
    from PIL import Image, ImageDraw, ImageFont
    os.makedirs(a.images, exist_ok=True)
    for k, (c, n, act, nouv, img, bl) in enumerate(exemples[:a.exemples]):
        im = Image.open(img).convert("RGB"); W, H = im.size; d = ImageDraw.Draw(im)
        r = max(14, W // 45)
        try: fnt = ImageFont.truetype("arialbd.ttf", int(r * 1.4))
        except Exception: fnt = None
        for b in bl:
            cx, cy = (b["box"]["x"] + b["box"]["w"] / 2) * W, (b["box"]["y"] + b["box"]["h"] / 2) * H
            for rang, (ordre, coul, dx) in enumerate(((act, (232, 74, 95), -r * 1.2), (nouv, (63, 199, 168), r * 1.2))):
                i = ordre.index(b["id"]) + 1
                d.ellipse([cx + dx - r, cy - r, cx + dx + r, cy + r], fill=coul, outline=(0, 0, 0), width=3)
                d.text((cx + dx, cy), str(i), fill=(255, 255, 255), font=fnt, anchor="mm")
        im.thumbnail((1400, 1400)); im.save(os.path.join(a.images, "ordre_%d.png" % k))
    print("images : rouge = ordre actuel, vert = case par case ->", a.images)
