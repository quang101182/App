# -*- coding: utf-8 -*-
"""Detection de cases par modele DEDIE (YOLO26-nano fine-tune sur Manga109-s).

Remplace la detection par VLM, qui echouait sur les vraies planches : Pixtral
quantifiait sur une grille et coupait au milieu des dessins. Ce modele-ci est
entraine sur 109 vrais volumes de manga -> il connait les cases sans bordure,
les fonds noirs, les inserts.

Bonus : il sort AUSSI les bulles de texte (classe `text`), ce qui servira
directement au mode traduction (une bulle = une zone a relettrer).
Licence Apache 2.0 (contrairement a Magi, reserve a la recherche).

Usage: python panel_yolo.py <image...> [--conf 0.25]
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.join(HERE, "models", "manga_panel_detector_fp32.pt")
OUT = os.path.join(HERE, "ingest_out")
os.makedirs(OUT, exist_ok=True)


def detect(paths, conf=0.25):
    from ultralytics import YOLO
    from PIL import Image, ImageDraw
    m = YOLO(MODEL)
    names = m.names
    print("classes du modele : %s" % names, flush=True)
    summary = []
    for p in paths:
        im = Image.open(p).convert("RGB")
        W, H = im.size
        r = m.predict(p, conf=conf, verbose=False)[0]
        panels, texts = [], []
        for b in r.boxes:
            x1, y1, x2, y2 = [float(v) for v in b.xyxy[0]]
            cls = names[int(b.cls[0])].lower()
            item = {"x": x1 / W, "y": y1 / H, "w": (x2 - x1) / W, "h": (y2 - y1) / H,
                    "conf": round(float(b.conf[0]), 3)}
            (panels if "panel" in cls or "frame" in cls else texts).append(item)
        # ordre de lecture japonais : haut->bas, puis droite->gauche par bande
        panels.sort(key=lambda q: (round(q["y"] * 12), -q["x"]))
        for i, q in enumerate(panels, 1):
            q["id"] = i
        base = os.path.splitext(os.path.basename(p))[0]
        json.dump({"panels": panels, "texts": texts},
                  open(os.path.join(OUT, base + "_yolo.json"), "w", encoding="utf-8"), indent=1)

        vis = im.copy()
        d = ImageDraw.Draw(vis)
        for q in panels:
            d.rectangle([q["x"] * W + 2, q["y"] * H + 2,
                         (q["x"] + q["w"]) * W - 2, (q["y"] + q["h"]) * H - 2],
                        outline=(0, 200, 0), width=5)
            d.text((q["x"] * W + 8, q["y"] * H + 6), str(q["id"]), fill=(0, 200, 0))
        for q in texts:
            d.rectangle([q["x"] * W, q["y"] * H, (q["x"] + q["w"]) * W, (q["y"] + q["h"]) * H],
                        outline=(255, 140, 0), width=2)
        vis.save(os.path.join(HERE, "yolo_" + base + ".jpg"), quality=88)
        # decoupe des cases
        for q in panels:
            x1, y1 = int(q["x"] * W), int(q["y"] * H)
            x2, y2 = int((q["x"] + q["w"]) * W), int((q["y"] + q["h"]) * H)
            im.crop((max(0, x1), max(0, y1), min(W, x2), min(H, y2))).save(
                os.path.join(OUT, "%s_yolocase%02d.png" % (base, q["id"])))
        cf = [q["conf"] for q in panels]
        print("%-8s %4dx%-4d  cases=%-3d bulles=%-3d  conf min/moy %.2f/%.2f"
              % (base, W, H, len(panels), len(texts),
                 min(cf) if cf else 0, sum(cf) / len(cf) if cf else 0), flush=True)
        summary.append((base, len(panels), len(texts)))
    return summary


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    conf = 0.25
    if "--conf" in sys.argv:
        conf = float(sys.argv[sys.argv.index("--conf") + 1])
    detect(args, conf)
