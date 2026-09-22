"""DEMO case par case (hors app) : meme audio et meme minutage que video_chapitre (voix + 0,45 s par page)."""
import json, math, subprocess, sys
from PIL import Image, ImageDraw, ImageFont
from cases import cases
CH = r"D:/Download/02-Apps-Web/Repo-github/App/manga-studio/sources/_demo-cases/ch_300"
TAG, P0, P1 = "k3-serie-ref", 3, 7
W, H, FPS, HT, HS = 1080, 1920, 30, 96, 360
SW, SH = W, H - HT - HS; A = SW / SH
FOND = (14, 14, 18)
F_SUB = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 46); F_TIT = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 30)
n = json.load(open(CH + "/narration/" + TAG + "/narration.json", encoding="utf-8"))
pages = [p for p in n["pages"] if P0 <= p["page"] <= P1]

def cadre(b, Wp, Hp, pad=0.035):
    x0, y0, x1, y1 = b; w, h = x1 - x0, y1 - y0
    x0 -= w * pad; x1 += w * pad; y0 -= h * pad; y1 += h * pad; w, h = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if w / h < A: w = h * A
    else: h = w / A
    return [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]
def ease(t): return t * t * (3 - 2 * t)
def lerp(a, b, t): return [x + (y - x) * t for x, y in zip(a, b)]
def zoom(r, k):
    cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2; w, h = (r[2] - r[0]) / k, (r[3] - r[1]) / k
    return [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]

def plan(p, img):
    Wp, Hp = img.size; T = p["dur"] + 0.45
    page = cadre([0, 0, Wp, Hp], Wp, Hp, 0.0)
    if Wp > Hp:                                   # double page : droite puis gauche (sens manga)
        bs = [[Wp // 2, 0, Wp, Hp], [0, 0, Wp // 2, Hp]]
    else:
        bs, _ = cases(CH + "/" + p["file"])
    if len(bs) == 1:
        return [(0, T, page, page, 1.0, 1.06, None)]
    seg = [(0, min(1.0, 0.1 * T), None, page, 1.0, 1.0, None)]  # apercu de la page
    reste = T - seg[0][1]; aires = [math.sqrt((b[2]-b[0]) * (b[3]-b[1])) for b in bs]
    t = seg[0][1]; prec = page
    for b, a in zip(bs, aires):
        d = reste * a / sum(aires); r = cadre(b, Wp, Hp)
        seg.append((t, t + d, prec, r, 1.0, 1.035, b)); prec = r; t += d
    return seg

def camera(seg, t):
    for (a, b, de, vers, z0, z1, case) in seg:
        if t < b or (a, b) == seg[-1][:2]:
            u = min(1, max(0, (t - a) / max(0.01, b - a)))
            r = zoom(vers, z0 + (z1 - z0) * u)
            fondu = 1.0
            if de is not None and t - a < 0.5:
                e = ease((t - a) / 0.5); r = lerp(zoom(de, 1.0), r, e); fondu = e
            return r, case, fondu

def sous_titre(p, t):
    mots = p["narration"].split(); tm = p.get("mots") or []
    k = sum(1 for m in tm if m[0] <= t)          # mots deja commences
    return mots, k - 1
def dessiner_sous(d, mots, cur):
    lignes, l = [], []
    for i, m in enumerate(mots):
        essai = " ".join(mots[j] for j in l + [i])
        if l and d.textlength(essai, font=F_SUB) > W - 90: lignes.append(l); l = []
        l.append(i)
    if l: lignes.append(l)
    if len(lignes) > 4:
        i = next((k for k, l in enumerate(lignes) if cur in l), 0 if cur < 0 else len(lignes) - 1)
        d0 = min(max(0, i - 1), len(lignes) - 4); lignes = lignes[d0:d0 + 4]
    y = H - HS + (HS - len(lignes) * 58) // 2
    for l in lignes:
        x = (W - d.textlength(" ".join(mots[j] for j in l), font=F_SUB)) / 2
        for j in l:
            c = (255, 215, 0) if j == cur else ((235, 235, 235) if j < cur else (120, 120, 128))
            d.text((x, y), mots[j], font=F_SUB, fill=c); x += d.textlength(mots[j] + " ", font=F_SUB)
        y += 58

out = sys.argv[1]
ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H), "-r", str(FPS),
                       "-i", "-", "-i", sys.argv[2], "-map", "0:v", "-map", "1:a", "-c:v", "h264_nvenc", "-preset", "p5", "-cq", "30", "-maxrate", "3M", "-bufsize", "6M",
                       "-c:a", "copy", "-shortest", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
for i, p in enumerate(pages):
    img = Image.open(CH + "/" + p["file"]).convert("RGB"); seg = plan(p, img); T = p["dur"] + 0.45
    print("page", p["page"], "cases:", len(seg) - (0 if len(seg) == 1 else 1), "duree %.1f s" % T, flush=True)
    for f in range(round(T * FPS)):
        t = f / FPS
        fr = Image.new("RGB", (W, H), FOND)
        cam, case, fondu = camera(seg, t)
        scene = img.transform((SW, SH), Image.EXTENT, tuple(cam), Image.BICUBIC, fillcolor=FOND)
        if case is not None:
            sx, sy = SW / (cam[2] - cam[0]), SH / (cam[3] - cam[1])
            bx = [round((case[0] - cam[0]) * sx), round((case[1] - cam[1]) * sy), round((case[2] - cam[0]) * sx), round((case[3] - cam[1]) * sy)]
            voile = Image.new("L", (SW, SH), round(170 * fondu)); ImageDraw.Draw(voile).rectangle(bx, fill=0)
            scene = Image.composite(Image.new("RGB", (SW, SH), FOND), scene, voile)
        fr.paste(scene, (0, HT)); d = ImageDraw.Draw(fr)
        tit = "%s ch. %s · page %s (%d/%d)" % (n.get("title") or "", n.get("chapter") or "", p["page"], i + 1, len(pages))
        d.text(((W - d.textlength(tit, font=F_TIT)) / 2, 30), tit, font=F_TIT, fill=(196, 196, 204))
        mots, cur = sous_titre(p, t); dessiner_sous(d, mots, cur)
        ff.stdin.write(fr.tobytes())
ff.stdin.close(); ff.wait(); print("OK", out)
