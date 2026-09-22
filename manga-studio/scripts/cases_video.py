# -*- coding: utf-8 -*-
"""Mode « case par case » : les cases d'un chapitre et la CAMERA qui les parcourt (Manga Studio v2.5.0, 23/09/2026).

Decision Quang (22-23/09) : la camera passe de case en case (manga : ordre droite -> gauche, le reste assombri ;
webtoon : la case remplit la largeur et defile si elle est plus haute que l'ecran). Mode PAR DEFAUT pour tous les
formats ; « page entiere » reste au choix. Le LECTEUR de l'app fait exactement la meme chose (reponse de Quang le
23/09 : « oui, lecteur aussi ») -> ce fichier est la REGLE ; manga_studio.html en porte le miroir JS (camPlan /
camPose), a garder identique.

Une seule detection par page, gardee dans sources/<chap>/cases.json. Empreinte = taille + date de chaque page : une
page remplacee SOUS LE MEME NOM (incident Claymore v2.4.6) est redetectee.
- manga : modele YOLO dedie (panel_yolo, Manga109-s, classe « frame »), local et gratuit ;
- webtoon (manifest.decoupe de manga-fetch, ou pages tres hautes) : la capture a deja coupe UNE case par page ->
  on ne garde que l'etendue du dessin (rangees non unies), sans YOLO.

Usage : python cases_video.py <serie/ch_N> [--forcer]   (ecrit le cache, affiche un resume)
"""
import json, math, os, sys, time

VERSION = "1.0.0"
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, "..", "sources"))
MODELE = os.path.join(HERE, "models", "manga_panel_detector_fp32.pt")
CACHE = "cases.json"
ALGO = 1                       # a monter si la DETECTION change : tout le cache est alors refait
_YOLO = None


# ------------------------------------------------------------------ format du chapitre
def _taille(f):
    from PIL import Image
    with Image.open(f) as im:
        return im.size


def format_chapitre(cd, man=None):
    """« webtoon » si manga-fetch a redecoupe le chapitre (manifest.decoupe) ou si les pages sont tres hautes."""
    if man is None:
        try:
            man = json.load(open(os.path.join(cd, "manifest.json"), encoding="utf-8"))
        except Exception:
            man = {}
    if man.get("decoupe"):
        return "webtoon"
    r = []
    for p in (man.get("pages") or [])[:40]:
        f = os.path.join(cd, p.get("file") or "")
        if os.path.isfile(f):
            try:
                w, h = _taille(f)
                r.append(h / float(w))
            except Exception:
                pass
    r.sort()
    return "webtoon" if r and r[len(r) // 2] >= 2.5 else "manga"


# ------------------------------------------------------------------ detection
def _yolo():
    global _YOLO
    if _YOLO is None:
        from ultralytics import YOLO
        _YOLO = YOLO(MODELE)
    return _YOLO


def ordonner(boites, W):
    """Ordre de lecture MANGA : rangees de haut en bas ; dans une rangee, colonnes de droite a gauche, puis de haut en bas."""
    boites = sorted(boites, key=lambda b: b[1])
    rangees = []
    for b in boites:
        for r in rangees:
            if b[1] < max(x[3] for x in r) - 0.3 * (b[3] - b[1]):
                r.append(b)
                break
        else:
            rangees.append([b])
    out = []
    for r in rangees:
        cols = []
        for b in sorted(r, key=lambda b: -b[2]):
            for c in cols:
                ux0, ux1 = min(x[0] for x in c), max(x[2] for x in c)
                if min(b[2], ux1) - max(b[0], ux0) > 0.5 * (b[2] - b[0]):
                    c.append(b)
                    break
            else:
                cols.append([b])
        for c in sorted(cols, key=lambda c: -max(x[2] for x in c)):
            out += sorted(c, key=lambda b: b[1])
    return out


def nettoyer(boites, W, H):
    """Sans les miettes (< 1,5 % de la page) ni les cases contenues a 80 % dans une autre."""
    b = [[max(0, x0), max(0, y0), min(W, x1), min(H, y1)] for x0, y0, x1, y1 in boites]
    b = [x for x in b if (x[2] - x[0]) * (x[3] - x[1]) >= 0.015 * W * H]
    garde = []
    for i, x in enumerate(sorted(b, key=lambda x: -(x[2] - x[0]) * (x[3] - x[1]))):
        a = (x[2] - x[0]) * (x[3] - x[1])
        if any(max(0, min(x[2], o[2]) - max(x[0], o[0])) * max(0, min(x[3], o[3]) - max(x[1], o[1])) > 0.8 * a for o in garde):
            continue
        garde.append(x)
    return garde


def cases_manga(chemins, conf=0.25):
    """{chemin: (W, H, [cases ordonnees])} -- une double page (W > H) : moitie DROITE d'abord, puis la gauche."""
    m = _yolo()
    out = {}
    for f in chemins:
        r = m.predict(f, conf=conf, verbose=False)[0]
        H, W = r.orig_shape[0], r.orig_shape[1]
        bs = [[round(float(v)) for v in b.xyxy[0]] for b in r.boxes
              if any(k in m.names[int(b.cls[0])].lower() for k in ("frame", "panel"))]
        bs = nettoyer(bs, W, H)
        if W > H:
            # une « case » large comme la double page (le dessin entier) : on garde la lecture moitie par moitie
            # (vu sur OPM ch.300 p.10 : sinon la camera dezoomait sur toute la double page en 2e case)
            bs = [b for b in bs if b[2] - b[0] <= 0.6 * W]
            d = [b for b in bs if (b[0] + b[2]) / 2 >= W / 2]
            g = [b for b in bs if (b[0] + b[2]) / 2 < W / 2]
            bs = (ordonner(d, W) or [[W // 2, 0, W, H]]) + (ordonner(g, W) or [[0, 0, W // 2, H]])
        else:
            bs = ordonner(bs, W)
        out[f] = (W, H, bs)
    return out


def case_webtoon(f, tol=24, gmin=14):
    """L'etendue du dessin d'une case de webtoon : de la 1re a la derniere rangee NON unie, pleine largeur."""
    import numpy as np
    from PIL import Image
    with Image.open(f) as im:
        a = np.asarray(im.convert("L"), dtype=np.int16)
    H, W = a.shape
    pleine = np.where((a.max(axis=1) - a.min(axis=1)) > tol)[0]
    if not len(pleine):
        return W, H, []
    y0, y1 = int(pleine[0]), int(pleine[-1]) + 1
    if y1 - y0 >= 0.95 * H:
        y0, y1 = 0, H
    return W, H, [[0, y0, W, y1]]


# ------------------------------------------------------------------ cache du chapitre
def _sig(f):
    st = os.stat(f)
    return [st.st_size, int(st.st_mtime)]


def lire_cache(cd):
    try:
        c = json.load(open(os.path.join(cd, CACHE), encoding="utf-8"))
        return c if c.get("algo") == ALGO else None
    except Exception:
        return None


def etat(chap):
    """Sans rien calculer (le proxy) : {format, pages: {fichier: {W,H,cases}}, manquantes: n}."""
    cd = os.path.join(SRC, chap)
    try:
        man = json.load(open(os.path.join(cd, "manifest.json"), encoding="utf-8"))
    except Exception:
        return None
    c = lire_cache(cd) or {}
    pages, manq = {}, 0
    for p in man.get("pages") or []:
        f = os.path.join(cd, p.get("file") or "")
        e = (c.get("pages") or {}).get(p.get("file"))
        if not os.path.isfile(f):
            continue
        if e and e.get("sig") == _sig(f):
            pages[p["file"]] = {k: e[k] for k in ("W", "H", "cases")}
        else:
            manq += 1
    return {"format": c.get("format") or format_chapitre(cd, man), "pages": pages, "manquantes": manq}


def cases_chapitre(chap, forcer=False, journal=None):
    """Detecte ce qui manque (ou a change) et ecrit le cache. Renvoie le cache complet."""
    cd = os.path.join(SRC, chap)
    man = json.load(open(os.path.join(cd, "manifest.json"), encoding="utf-8"))
    c = (None if forcer else lire_cache(cd)) or {}
    fmt = format_chapitre(cd, man)
    if c.get("format") != fmt:
        c = {}
    anciens, pages, a_faire = c.get("pages") or {}, {}, []
    for p in man.get("pages") or []:
        f = os.path.join(cd, p.get("file") or "")
        if not os.path.isfile(f):
            continue
        e = anciens.get(p["file"])
        if e and e.get("sig") == _sig(f):
            pages[p["file"]] = e
        else:
            a_faire.append(p["file"])
    t0 = time.time()
    if a_faire:
        if fmt == "webtoon":
            res = {n: case_webtoon(os.path.join(cd, n)) for n in a_faire}
        else:
            r = cases_manga([os.path.join(cd, n) for n in a_faire])
            res = {n: r[os.path.join(cd, n)] for n in a_faire}
        for n, (W, H, bs) in res.items():
            pages[n] = {"sig": _sig(os.path.join(cd, n)), "W": W, "H": H, "cases": bs}
    out = {"version": VERSION, "algo": ALGO, "format": fmt, "maj": time.strftime("%Y-%m-%dT%H:%M:%S"), "pages": pages}
    if a_faire or c.get("pages") != pages:
        tmp = os.path.join(cd, CACHE + ".tmp")
        json.dump(out, open(tmp, "w", encoding="utf-8"), ensure_ascii=False)
        os.replace(tmp, os.path.join(cd, CACHE))
    if journal:
        journal("cases : %s (%s) %d page(s) detectee(s) en %.1f s, %d en cache" % (chap, fmt, len(a_faire), time.time() - t0,
                                                                                      len(pages) - len(a_faire)))
    return out


# ------------------------------------------------------------------ CAMERA (miroir JS : camPlan / camPose)
# Tout est en pixels de l'IMAGE ; A = largeur / hauteur de la scene (9:16 moins les bandeaux en video, l'ecran au lecteur).
APERCU, GLISSE, ZOOM_CASE, PAD = 0.10, 0.5, 1.035, 0.035
VOILE = 170 / 255.0


def cadre(b, A, pad=PAD):
    x0, y0, x1, y1 = b
    w, h = x1 - x0, y1 - y0
    x0, x1, y0, y1 = x0 - w * pad, x1 + w * pad, y0 - h * pad, y1 + h * pad
    w, h = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if w / h < A:
        w = h * A
    else:
        h = w / A
    return [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]


def lisse(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


def melange(a, b, u):
    return [x + (y - x) * u for x, y in zip(a, b)]


def zoome(r, k):
    cx, cy, w, h = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2, (r[2] - r[0]) / k, (r[3] - r[1]) / k
    return [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]


def plan(e, fmt, A, T):
    """Le trajet de la camera sur UNE page affichee T secondes. e = {W, H, cases}."""
    W, H, bs = e["W"], e["H"], e.get("cases") or []
    page = cadre([0, 0, W, H], A, 0)
    if fmt == "webtoon":
        b = bs[0] if bs else [0, 0, W, H]
        hv = W / A                                            # hauteur visible quand la case remplit la largeur
        if b[3] - b[1] > hv * 1.02:                           # plus haute que l'ecran : on la parcourt de haut en bas
            return {"type": "defile", "T": T, "de": [0, b[1], W, b[1] + hv], "vers": [0, b[3] - hv, W, b[3]], "case": b}
        return {"type": "fixe", "T": T, "r": cadre(b, A, 0.02), "z": 1.04, "case": b}
    if len(bs) <= 1:                                          # une seule case (ou aucune) : la page, zoom lent
        return {"type": "fixe", "T": T, "r": page, "z": 1.06, "case": None}
    t0 = min(1.0, APERCU * T)
    aires = [math.sqrt((b[2] - b[0]) * (b[3] - b[1])) for b in bs]
    segs, t = [], t0
    for b, a in zip(bs, aires):
        d = (T - t0) * a / sum(aires)
        segs.append({"a": t, "b": t + d, "r": cadre(b, A), "case": b})
        t += d
    return {"type": "cases", "T": T, "page": page, "apercu": t0, "segs": segs}


def pose(pl, t):
    """(rectangle vu, case eclairee ou None, opacite du voile 0..1) a l'instant t de la page."""
    T = pl["T"]
    if pl["type"] == "defile":
        return melange(pl["de"], pl["vers"], lisse((t / T - 0.12) / 0.76)), pl["case"], 1.0
    if pl["type"] == "fixe":
        return zoome(pl["r"], 1 + (pl["z"] - 1) * min(1.0, max(0.0, t / T))), pl["case"], 1.0 if pl["case"] else 0.0
    if t < pl["apercu"]:
        return pl["page"], None, 0.0
    segs = pl["segs"]
    k = 0
    while k < len(segs) - 1 and t >= segs[k]["b"]:
        k += 1
    s = segs[k]
    u = min(1.0, max(0.0, (t - s["a"]) / max(0.01, s["b"] - s["a"])))
    r = zoome(s["r"], 1 + (ZOOM_CASE - 1) * u)
    g = min(GLISSE, (s["b"] - s["a"]) / 2)
    if t - s["a"] < g:                                        # glisse depuis la ou la camera etait
        e = lisse((t - s["a"]) / g)
        if k == 0:
            return melange(pl["page"], r, e), s["case"], e
        p = segs[k - 1]
        return melange(zoome(p["r"], ZOOM_CASE), r, e), melange(p["case"], s["case"], e), 1.0
    return r, s["case"], 1.0


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit(__doc__)
    c = cases_chapitre(args[0].strip("/"), forcer="--forcer" in sys.argv, journal=lambda m: print(m, flush=True))
    n = [len(e["cases"]) for e in c["pages"].values()]
    print("OK %s : %d pages, %d cases (%s)" % (c["format"], len(n), sum(n), ", ".join(str(x) for x in n[:40])))


if __name__ == "__main__":
    main()
