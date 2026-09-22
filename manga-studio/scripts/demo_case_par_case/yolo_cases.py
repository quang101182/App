import json, sys
from ultralytics import YOLO
M = YOLO(r"D:/Download/02-Apps-Web/Repo-github/App/manga-studio/scripts/models/manga_panel_detector_fp32.pt")
def cases(paths, conf=0.25):
    out = {}
    for p in paths:
        r = M.predict(p, conf=conf, verbose=False)[0]; W, H = r.orig_shape[1], r.orig_shape[0]
        ps = [[float(v) for v in b.xyxy[0]] for b in r.boxes if "panel" in M.names[int(b.cls[0])].lower() or "frame" in M.names[int(b.cls[0])].lower()]
        out[p] = {"W": W, "H": H, "panels": ps}
    return out
if __name__ == "__main__":
    print(json.dumps(cases(sys.argv[1:])))
