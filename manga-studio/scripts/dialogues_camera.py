# -*- coding: utf-8 -*-
"""Video des Dialogues -- CAMERA « case par case » (dialogues.py 1.31.0, Manga Studio, 01/10/2026).

Demande de Quang (01/10 23h47) : « avec le mode dialogue, la video generee ne recupere pas l'animation, lire case par
case ». La video doit faire ce que fait DEJA le lecteur de l'app (manga_studio.html) -- ce fichier en est le MIROIR :
  - dllFile    : la file passe par TOUTES les cases ; avant une replique de la case k, les cases sans replique pas encore
                 vues qui la precedent (ordre des cases du cache) ; apres la derniere replique, celles qui restent ;
                 une page sans dialogue = ses cases une a une. Moins de 2 cases connues : file inchangee.
  - dllIdxCase : la case d'une replique = la plus proche du centre de sa bulle.
  - dllCaseDe  : on cadre la case ELARGIE a la bulle entiere et a la pastille du nom ; une case muette = la case seule.
  - dllCamera  : marge 3 %, zoom borne a [1, 3], vue gardee dans l'image ; glissement de 0,7 s
                 (cubic-bezier(.4, 0, .2, 1), comme le CSS #dllZoom.anim).
  - case muette : 1,2 s, page nue, bandeau « p. N · case k / nk · sans dialogue ».
Rendu d'une replique : le meme que image_replique (dialogues.py) -- page voilee hors de la bulle, halo, pastille --
mais calcule a l'echelle S (gros plan net jusqu'au zoom x3). Les deux doivent rester d'accord.

Chaque etape devient un petit MP4 (images du glissement passees a ffmpeg, puis la derniere tenue par tpad) ; les
etapes s'assemblent sans re-encodage. Nombre d'images = arrondi du temps CUMULE : aucune derive avec le son.
"""
import math, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

VW, VH, BANDE = 1080, 1920, 330
ZH = VH - BANDE
S = 2                       # echelle de calcul de la scene (le zoom va jusqu'a x3)
FPS = 30
GLISSE = 0.7                # s -- #dllZoom.anim
MUETTE = 1.2                # s -- dllSilence (1200 ms a vitesse 1)
MARGE, ZMIN, ZMAX = 0.03, 1.0, 3.0
FOND = (7, 8, 11)
CREATE = getattr(subprocess, "CREATE_NO_WINDOW", 0)


# ------------------------------------------------------------------ outils
def _police(taille, gras=False):
    from PIL import ImageFont
    for f in (("arialbd.ttf" if gras else "arial.ttf"), "DejaVuSans-Bold.ttf" if gras else "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(f, taille)
        except OSError:
            continue
    return ImageFont.load_default()


def _hex(c):
    c = (c or "#9aa6b8").lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def bezier(u, x1=.4, y1=0.0, x2=.2, y2=1.0):
    """cubic-bezier CSS : u = temps (0..1) -> avancement (0..1)."""
    u = min(1.0, max(0.0, u))
    if u in (0.0, 1.0):
        return u
    bx = lambda t: 3 * x1 * t * (1 - t) ** 2 + 3 * x2 * t * t * (1 - t) + t ** 3
    by = lambda t: 3 * y1 * t * (1 - t) ** 2 + 3 * y2 * t * t * (1 - t) + t ** 3
    lo, hi = 0.0, 1.0
    for _ in range(40):                                   # bissection : bx est croissante
        m = (lo + hi) / 2
        if bx(m) < u:
            lo = m
        else:
            hi = m
    return by((lo + hi) / 2)


# ------------------------------------------------------------------ cases (miroir dllPageCases / dllIdxCase / dllCaseDe)
def page_cases(cases, fich, n, fichier):
    """Les cases de la page n : cles = nom de l'image d'ORIGINE (comme le lecteur), sinon le nom du fichier de l'etape."""
    cp = (cases or {}).get("pages") or {}
    pg = (cp.get(fich[n - 1]) if 0 < n <= len(fich) else None) or cp.get(fichier or "")
    return pg if pg and pg.get("cases") and pg.get("W") and pg.get("H") else None


def idx_case(x, pg):
    b = x.get("box") or {"x": .5, "y": .5, "w": 0, "h": 0}
    cx, cy = (b["x"] + b["w"] / 2) * pg["W"], (b["y"] + b["h"] / 2) * pg["H"]
    bi, dm = -1, float("inf")
    for i, c in enumerate(pg["cases"]):
        d = math.hypot(max(c[0] - cx, 0, cx - c[2]), max(c[1] - cy, 0, cy - c[3]))
        if d < dm:
            dm, bi = d, i
    return bi


def file_cases(etapes, cases, fich):
    """dllFile : intercale les cases muettes. etapes = repliques + pages vides, deja dans l'ordre verifie."""
    out, groupes = [], []
    for x in etapes:
        if not groupes or groupes[-1][0] != x["page"]:
            groupes.append((x["page"], []))
        groupes[-1][1].append(x)
    for n, et in groupes:
        pg = page_cases(cases, fich, n, et[0].get("file"))
        if not pg or len(pg["cases"]) < 2:
            out.extend(et); continue
        reps = [x for x in et if not x.get("vide")]
        idx = [idx_case(x, pg) for x in reps]
        parlent, vues, N = set(idx), set(), len(pg["cases"])
        src = next((x.get("src") for x in et if x.get("src")), None)

        def jusqua(k):
            for m in range(k):
                if m not in parlent and m not in vues:
                    vues.add(m)
                    out.append({"page": n, "muette": True, "k": m, "nk": N, "case": pg["cases"][m], "pg": pg, "src": src})
        for x, k in zip(reps, idx):
            jusqua(k); vues.add(k); out.append(dict(x, _pg=pg, _k=k))
        jusqua(N)
    return out


def rect_etape(x, pastille):
    """dllCaseDe -> fractions de page (x1, y1, x2, y2), ou None (page entiere)."""
    if x.get("muette"):
        c, pg = x["case"], x["pg"]
        return (c[0] / pg["W"], c[1] / pg["H"], c[2] / pg["W"], c[3] / pg["H"])
    pg = x.get("_pg")
    if not pg or x.get("vide"):
        return None
    c = pg["cases"][x["_k"]]
    b = x["box"]
    if x.get("contour") and len(x["contour"]) > 2:
        xs, ys = [p[0] for p in x["contour"]], [p[1] for p in x["contour"]]
    else:
        xs, ys = [b["x"], b["x"] + b["w"]], [b["y"], b["y"] + b["h"]]
    q = pastille or (1, 1, 0, 0)
    return (min(c[0] / pg["W"], q[0], *xs), min(c[1] / pg["H"], q[1], *ys),
            max(c[2] / pg["W"], q[2], *xs), max(c[3] / pg["H"], q[3], *ys))


def vue(r, geo):
    """dllCamera : fractions de page -> rectangle de vue en pixels de SCENE (echelle 1)."""
    if r is None:
        return (0.0, 0.0, float(VW), float(ZH))
    ox, oy, pw, ph = geo
    # pas borne a la PAGE : la pastille du nom deborde souvent dans la marge (elle etait coupee) -- la vue reste dans l'ecran
    x1, y1, x2, y2 = r[0] - MARGE, r[1] - MARGE, r[2] + MARGE, r[3] + MARGE
    R = (ox + x1 * pw, oy + y1 * ph, ox + x2 * pw, oy + y2 * ph)
    k = min(VW / max(1.0, R[2] - R[0]), ZH / max(1.0, R[3] - R[1]))
    k = max(ZMIN, min(ZMAX, k))
    w, h = VW / k, ZH / k
    cx, cy = (R[0] + R[2]) / 2, (R[1] + R[3]) / 2
    x0, y0 = min(max(cx - w / 2, 0), VW - w), min(max(cy - h / 2, 0), ZH - h)
    return (x0, y0, x0 + w, y0 + h)


# ------------------------------------------------------------------ rendu (jumeau de image_replique, a l'echelle S)
def _place(pg):
    k = min(VW / pg.width, ZH / pg.height)
    pw, ph = round(pg.width * k), round(pg.height * k)
    return (VW - pw) // 2, (ZH - ph) // 2, pw, ph


def scene_page(page_png):
    """Page nue, centree dans la scene (case muette, page vide)."""
    from PIL import Image
    pg = Image.open(page_png).convert("RGB")
    ox, oy, pw, ph = _place(pg)
    sc = Image.new("RGB", (VW * S, ZH * S), FOND)
    sc.paste(pg.resize((pw * S, ph * S), Image.LANCZOS), (ox * S, oy * S))
    return sc, (ox, oy, pw, ph)


def scene_replique(page_png, x, couleur, nom):
    """-> (scene VW*S x ZH*S, geo (ox, oy, pw, ph) a l'echelle 1, pastille en fractions de page ou None)."""
    import numpy as np, cv2
    from PIL import Image, ImageDraw
    pg0 = Image.open(page_png).convert("RGB")
    ox, oy, pw, ph = _place(pg0)
    PW, PH = pw * S, ph * S
    pg = pg0.resize((PW, PH), Image.LANCZOS)
    masque = np.zeros((PH, PW), np.uint8)
    if x.get("contour") and len(x["contour"]) > 2:
        cv2.fillPoly(masque, [np.array([[int(p[0] * PW), int(p[1] * PH)] for p in x["contour"]], np.int32)], 255)
    else:
        b = x["box"]
        cv2.ellipse(masque, (int((b["x"] + b["w"] / 2) * PW), int((b["y"] + b["h"] / 2) * PH)),
                    (int(b["w"] * PW / 2 + PW * .012), int(b["h"] * PH / 2 + PH * .01)), 0, 0, 360, 255, -1)
    arr = np.asarray(pg).astype(np.float32)
    arr = np.where((masque == 0)[..., None], arr * 0.62, arr)
    rgb = np.array(_hex(couleur), np.float32)
    trait = cv2.dilate(masque, np.ones((5 * S, 5 * S), np.uint8), iterations=3) - masque
    lueur = cv2.GaussianBlur(cv2.dilate(masque, np.ones((9 * S, 9 * S), np.uint8), iterations=3) - cv2.erode(masque, np.ones((3 * S, 3 * S), np.uint8)),
                             (0, 0), max(4 * S, PW / 90)).astype(np.float32) / 255.0
    a = np.clip(lueur * 1.3, 0, 1)[..., None] * (masque == 0)[..., None]
    arr = arr * (1 - a) + rgb * a
    arr[trait > 0] = rgb
    sc = Image.new("RGB", (VW * S, ZH * S), FOND)
    sc.paste(Image.fromarray(arr.clip(0, 255).astype(np.uint8)), (ox * S, oy * S))
    pastille = None
    ys, xs = np.where(masque > 0)
    if len(xs):
        d = ImageDraw.Draw(sc)
        f1 = _police(34 * S, True)
        cx, haut = ox * S + (xs.min() + xs.max()) / 2, oy * S + ys.min()
        tw = d.textlength(nom, font=f1)
        px, py = max(8 * S, min(VW * S - tw - 40 * S, cx - tw / 2 - 16 * S)), max(8 * S, haut - 62 * S)
        d.rounded_rectangle([px, py, px + tw + 32 * S, py + 50 * S], radius=25 * S, fill=_hex(couleur))
        d.text((px + 16 * S, py + 7 * S), nom, font=f1, fill=(20, 8, 15))
        fr = lambda vx, vy: ((vx / S - ox) / pw, (vy / S - oy) / ph)
        a1, a2 = fr(px, py), fr(px + tw + 32 * S, py + 50 * S)
        pastille = (a1[0], a1[1], a2[0], a2[1])
    return sc, (ox, oy, pw, ph), pastille


def bande_replique(x, couleur, nom):
    """Le sous-titre du bas -- identique a image_replique."""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (VW, BANDE), FOND)
    d = ImageDraw.Draw(im)
    f2, f3 = _police(44, True), _police(40)
    y0 = 34
    d.rounded_rectangle([48, y0 + 8, 76, y0 + 36], radius=14, fill=_hex(couleur))
    d.text((92, y0), nom, font=f2, fill=_hex(couleur))
    lignes, cour = [], ""
    for m in (x.get("texte") or "").split():
        if d.textlength((cour + " " + m).strip(), font=f3) > VW - 96:
            lignes.append(cour); cour = m
        else:
            cour = (cour + " " + m).strip()
    lignes.append(cour)
    for i, l in enumerate(lignes[:4]):
        d.text((48, y0 + 66 + i * 52), l, font=f3, fill=(232, 236, 243))
    return im


def bande_texte(t):
    """Bandeau d'une case muette / page vide : la pastille grise du lecteur."""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (VW, BANDE), FOND)
    d = ImageDraw.Draw(im)
    f = _police(38)
    tw = d.textlength(t, font=f)
    d.rounded_rectangle([48, 40, 48 + tw + 44, 40 + 64], radius=32, fill=(28, 32, 42), outline=(58, 64, 80), width=2)
    d.text((70, 52), t, font=f, fill=(170, 180, 198))
    return im


class Rendu:
    """Les images d'UNE etape : la scene (2 niveaux contre le moire des trames) + son bandeau."""

    def __init__(self, scene, bande):
        self.niv = [(S, scene), (1, scene.reduce(S))]
        self.bande = bande

    def image(self, r):
        from PIL import Image
        f, im = self.niv[0]
        if (r[2] - r[0]) >= VW / 1.4:                     # vue large : la scene reduite (pas de moire)
            f, im = self.niv[1]
        sc = im.transform((VW, ZH), Image.EXTENT, tuple(v * f for v in r), Image.BILINEAR, fillcolor=FOND)
        out = Image.new("RGB", (VW, VH), FOND)
        out.paste(sc, (0, 0)); out.paste(self.bande, (0, ZH))
        return out


def melange(a, b, u):
    return tuple(p + (q - p) * u for p, q in zip(a, b))


def encodeur():
    """h264_nvenc si la carte le permet, sinon libx264 -- choisi UNE fois (les segments doivent etre identiques)."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=%dx%d:r=%d:d=0.2" % (VW, VH, FPS),
                        "-c:v", "h264_nvenc", "-f", "null", "-"], capture_output=True, creationflags=CREATE)
    if r.returncode == 0:
        return ["-c:v", "h264_nvenc", "-preset", "p5", "-cq", "24"]
    return ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23"]


def segment(images, n, sortie, enc):
    """images = [PIL...] (glissement + pose finale) ; la derniere est tenue jusqu'a n images au total."""
    pr = subprocess.Popen(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", "%dx%d" % (VW, VH), "-r", str(FPS), "-i", "-",
                           "-vf", "tpad=stop_mode=clone:stop_duration=%.3f,format=yuv420p" % (n / FPS + 1), "-frames:v", str(n),
                           "-an"] + enc + ["-video_track_timescale", "15360", sortie],
                          stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE)
    try:
        for im in images[:n]:
            pr.stdin.write(im.tobytes())
        pr.stdin.close()
    except (BrokenPipeError, OSError):
        pass
    err = pr.stderr.read().decode("utf-8", "replace")
    if pr.wait():
        raise RuntimeError("ffmpeg (segment) : " + err[-500:])


def pastille_frac(x, nom, geo):
    """La pastille du nom, en fractions de page, SANS rendu (meme calcul que scene_replique) : sert a cadrer d'avance."""
    from PIL import Image, ImageDraw
    ox, oy, pw, ph = geo
    if x.get("contour") and len(x["contour"]) > 2:
        xs, ys = [p[0] for p in x["contour"]], [p[1] for p in x["contour"]]
    else:
        b = x["box"]
        xs, ys = [b["x"] - .012, b["x"] + b["w"] + .012], [b["y"] - .01, b["y"] + b["h"] + .01]
    tw = ImageDraw.Draw(Image.new("RGB", (1, 1))).textlength(nom, font=_police(34 * S, True)) / S
    cx, haut = ox + (min(xs) + max(xs)) / 2 * pw, oy + min(ys) * ph
    px, py = max(8, min(VW - tw - 40, cx - tw / 2 - 16)), max(8, haut - 62)
    return ((px - ox) / pw, (py - oy) / ph, (px + tw + 32 - ox) / pw, (py + 50 - oy) / ph)


def video_etapes(etapes, durees, geo_de, prepare, tmp, progres=None, ouvriers=3):
    """etapes[i] (repliques / muettes / vides), durees[i] en s.
    geo_de(x) -> (geo, nom) bon marche ; prepare(x) -> (scene, bande) = le rendu (dans les ouvriers).
    Renvoie les segments MP4 dans l'ordre. Nombre d'images = arrondi du temps CUMULE (aucune derive avec le son)."""
    enc = encodeur()
    bornes, t = [], 0.0
    for d in durees:
        a = round(t * FPS); t += d; bornes.append((a, round(t * FPS)))
    pleine = (0.0, 0.0, float(VW), float(ZH))
    vues = []
    for x in etapes:                                          # toutes les vues d'abord (sequentiel, sans rendu)
        geo, nom = geo_de(x)
        if geo is None:
            vues.append(pleine); continue
        past = pastille_frac(x, nom, geo) if not (x.get("vide") or x.get("muette")) else None
        vues.append(vue(rect_etape(x, past), geo))
    sorties = [os.path.join(tmp, "v%05d.mp4" % i) for i in range(len(etapes))]

    def faire(i):
        x = etapes[i]
        scene, bande = prepare(x)
        a, b = bornes[i]
        n = max(1, b - a)
        # meme page : on part de la vue de l'etape d'avant ; nouvelle page : de la page entiere (le lecteur change d'image)
        depart = vues[i - 1] if i > 0 and etapes[i - 1]["page"] == x["page"] else pleine
        rd = Rendu(scene, bande)
        g = min(n - 1, round(GLISSE * FPS)) if depart != vues[i] else 0
        images = [rd.image(melange(depart, vues[i], bezier(k / g))) for k in range(g)] if g > 0 else []
        images.append(rd.image(vues[i]))
        segment(images, n, sorties[i], enc)
        if progres:
            progres(i)
        return sorties[i]

    with ThreadPoolExecutor(max_workers=ouvriers) as ex:
        list(ex.map(faire, range(len(etapes))))
    return sorties, vues
