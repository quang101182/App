"""ESSAI (24/09, autorise par Quang) : effacer le texte pose sur le DESSIN par inpainting LaMa (local, GPU) au lieu d'un
rectangle blanc -- et traduire enfin les grands cris / legendes laissees en VO par la v1.97.0.

Ne modifie RIEN dans l'app : lit sources/<serie>/<ch>/ + traduction/fr/traduction.json, ecrit dans --out des planches
« original | actuel (v1.97) | essai LaMa ».
  - vraie bulle (etat « bulle ») : videe comme aujourd'hui (clean_bubbles, deterministe) ;
  - texte sur le dessin (boite entiere, fond de case, zone ecartee) : masque -> LaMa reconstitue le dessin dessous ;
    masque = la boite (elargie) si elle est petite, sinon seulement les traits tres sombres / tres clairs de la boite ;
  - le francais est pose avec un CONTOUR blanc (lisible sur un dessin).
Lance avec le Python du trainer (torch CUDA) :
  D:/Download/02-Apps-Web/kohya-trainer/.venv/Scripts/python.exe essai_inpaint.py one-punch-man ch_3:7 ch_4:17 --out DIR
"""
import argparse, json, os, sys, time
import numpy as np
import cv2
import torch
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import ingest_page as ip
SRC = os.path.normpath(os.path.join(HERE, "..", "sources"))
# modeles locaux lourds sur C: (Quang 24/09 : D: est petit) -- a cote des donnees de l'app, hors depot
MODELES = os.path.join(os.path.expanduser("~"), "Documents", "MangaStudio-donnees", "modeles")
MODELE = os.path.join(MODELES, "big-lama.pt")
GRANDE = 0.06            # boite > 6 % de la page : on ne masque que les traits du texte, pas toute la boite
_LAMA = {}
MODE = "boite"
SEUIL = 0.3
HALO = 7                      # v1 : boite (ou traits) ; v2 : « ctd » = masque des lettres


MOTEUR = "big"                      # « big » = big-lama generaliste (TorchScript) ; « manga » = lama_large_512px (manga)


def _modele():
    if MOTEUR not in _LAMA:
        if MOTEUR == "big":
            _LAMA[MOTEUR] = torch.jit.load(MODELE, map_location="cuda").eval()
        else:
            import lama_manga_arch as la
            _LAMA[MOTEUR] = la.load_lama_mpe(os.path.join(MODELES, "lama_large_512px.ckpt"), "cuda",
                                             use_mpe=False, large_arch=True)
    return _LAMA[MOTEUR]


def _lama_crop(img, masque):
    """Une zone : a sa resolution si <= 1024 px, sinon reduite (echelle d'entrainement), puis recollee."""
    H, W = masque.shape
    k = min(1.0, 1024 / max(H, W))
    x, m = img, masque
    if k < 1:
        x = cv2.resize(img, (int(W * k), int(H * k)), interpolation=cv2.INTER_AREA)
        m = cv2.resize(masque, (int(W * k), int(H * k)), interpolation=cv2.INTER_NEAREST)
    h, w = m.shape
    ph, pw = (8 - h % 8) % 8, (8 - w % 8) % 8
    x = np.pad(x, ((0, ph), (0, pw), (0, 0)), mode="reflect")
    m = np.pad(m, ((0, ph), (0, pw)), mode="reflect")
    xt = torch.from_numpy(x).permute(2, 0, 1)[None].float().cuda() / 255
    mt = (torch.from_numpy(m)[None, None].float().cuda() > 127).float()
    with torch.no_grad():
        xt = xt * (1 - mt)                                         # comme manga-image-translator : pixels masques a 0
        out = _modele()(xt, mt)
    out = (out[0].float().permute(1, 2, 0).clamp(0, 1).cpu().numpy() * 255).astype(np.uint8)[:h, :w]
    if k < 1:
        out = cv2.resize(out, (W, H), interpolation=cv2.INTER_CUBIC)
    return out


def lama(img, masque, contexte=192):
    """img RGB uint8 HxWx3, masque uint8 HxW (255 = a reconstituer) -> RGB uint8. Une passe PAR ZONE (recadree avec du
    contexte) : la page entiere reduite a 1024 px rendait les zones floues."""
    res = img.copy()
    n, lab, st, _ = cv2.connectedComponentsWithStats((cv2.dilate(masque, np.ones((25, 25), np.uint8)) > 0).astype(np.uint8), 8)
    H, W = masque.shape
    for i in range(1, n):
        x, y, w, h = st[i, 0], st[i, 1], st[i, 2], st[i, 3]
        x1, y1, x2, y2 = max(0, x - contexte), max(0, y - contexte), min(W, x + w + contexte), min(H, y + h + contexte)
        mc = masque[y1:y2, x1:x2] * (lab[y1:y2, x1:x2] == i)
        if not mc.any():
            continue
        out = _lama_crop(res[y1:y2, x1:x2], mc)
        sel = mc > 127
        res[y1:y2, x1:x2][sel] = out[sel]
    return res


def masque_zone(gris, b, H, W):
    x1, y1 = int(b["x"] * W), int(b["y"] * H)
    x2, y2 = int((b["x"] + b["w"]) * W), int((b["y"] + b["h"]) * H)
    m = np.zeros((H, W), np.uint8)
    if b["w"] * b["h"] <= GRANDE:
        e = 6
        m[max(0, y1 - e):y2 + e, max(0, x1 - e):x2 + e] = 255
    else:                               # grande zone : les traits du texte (noir plein + contour blanc), pas les demi-teintes
        z = gris[y1:y2, x1:x2]
        t = ((z < 70) | (z > 240)).astype(np.uint8) * 255
        t = cv2.morphologyEx(t, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        m[y1:y2, x1:x2] = cv2.dilate(t, np.ones((5, 5), np.uint8))
    return m


def zone_ctd(proba, b, H, W, marge=0.35, marge_long=0.8):
    """v2 : les MORCEAUX du masque de lettres (comic-text-detector) qui touchent la boite elargie -- chacun EN ENTIER
    (une boite a cote des lettres n'ampute plus le cri). -> (masque a effacer, boite reelle du texte) ou (None, None)."""
    bx, by, bw, bh = b["x"] * W, b["y"] * H, b["w"] * W, b["h"] * H
    mx, my = (marge_long, marge) if bw > bh else (marge, marge_long)    # plus large dans le SENS de la colonne de texte
    x1, y1 = int(max(0, bx - mx * bw - 10)), int(max(0, by - my * bh - 10))
    x2, y2 = int(min(W, bx + bw * (1 + mx) + 10)), int(min(H, by + bh * (1 + my) + 10))
    lettres = cv2.dilate(proba, np.ones((9, 9), np.uint8))          # une lettre = un morceau (traits voisins soudes)
    n, lab, st, _ = cv2.connectedComponentsWithStats((lettres > 0).astype(np.uint8), 8)
    ids = set(np.unique(lab[y1:y2, x1:x2])) - {0}
    ids = [i for i in ids if st[i, cv2.CC_STAT_AREA] >= 150]       # les poussieres du dessin ne comptent pas
    if not ids:
        return None, None
    m = np.isin(lab, ids).astype(np.uint8) * 255
    m = cv2.dilate(m, np.ones((5, 5), np.uint8))                    # + le contour blanc des cris
    ys, xs = np.where(m > 0)
    return m, {"x": xs.min() / W, "y": ys.min() / H, "w": (xs.max() - xs.min() + 1) / W, "h": (ys.max() - ys.min() + 1) / H}


def poser(rendu, boite, texte, est_bulle, taille_max):
    """Texte pose par la fonction de l'app, sur un calque ; contour blanc s'il est pose sur le dessin."""
    import traduire_chapitre as tc
    calque = Image.new("RGB", rendu.size, (255, 255, 255))
    r = tc.poser_texte(calque, boite, texte, est_bulle, taille_max=taille_max)
    a = np.array(calque.convert("L")) < 128                      # les lettres
    base = np.array(rendu)
    if not est_bulle:
        halo = cv2.dilate(a.astype(np.uint8), np.ones((HALO, HALO), np.uint8)) > 0
        base[halo] = 255
    base[a] = 0
    return Image.fromarray(base), r


def page(serie, ch, num, out):
    t = json.load(open(os.path.join(SRC, serie, ch, "traduction", "fr", "traduction.json"), encoding="utf-8"))
    p = [x for x in t["pages"] if x["page"] == num][0]
    im = ip.load_page(os.path.join(SRC, serie, ch, p["source"])).convert("RGB")
    W, H = im.size
    gris = np.array(im.convert("L"))
    bulles = [b for b in p["bulles"] if (b.get("trad") or "").strip() and b.get("type") in ("dialogue", "narration", "?")]
    vraies = [b for b in bulles if b.get("effacement") == "bulle"]
    dessin = [b for b in bulles if b not in vraies and (b.get("effacement") or b.get("ecarte"))]
    # 1. vraies bulles : comme aujourd'hui
    rendu, _ = ip.clean_bubbles(im, [dict(b["box"], id=b["id"]) for b in vraies], couverture_min=0.5, trous_dans_texte=True)
    # 2. texte sur le dessin : LaMa
    m = np.zeros((H, W), np.uint8)
    if MODE == "ctd":
        from essai_masque_texte import masque_texte
        proba = masque_texte(im, seuil=SEUIL)
        for b in dessin:
            mz, reel = zone_ctd(proba, b["box"], H, W)
            if mz is not None:
                m |= mz
                b["box_pose"] = reel
    else:
        for b in dessin:
            m |= masque_zone(gris, b["box"], H, W)
    t0 = time.time()
    arr = lama(np.array(rendu), m) if m.any() else np.array(rendu)
    dt = time.time() - t0
    rendu = Image.fromarray(arr)
    # 3. le francais : bulles videes dans leur bulle, le reste dans sa zone avec contour blanc
    places = []
    for b in vraies:
        c = [x for x in [b] if x.get("box")][0]["box"]
        places.append((c, b["trad"], True))
    for b in dessin:
        places.append((b.get("box_pose") or b["box"], b["trad"], False))
    tailles = sorted(__import__("traduire_chapitre").poser_texte(rendu.copy(), c, tx, eb, dessiner=False)["taille"] for c, tx, eb in places) or [None]
    commune = tailles[len(tailles) // 2]
    for c, tx, eb in places:
        rendu, _ = poser(rendu, c, tx, eb, commune)
    actuel = Image.open(os.path.join(SRC, serie, ch, "traduction", "fr", p["file"])).convert("RGB")
    hh = 900
    ims = [x.resize((int(x.width * hh / x.height), hh)) for x in (im, actuel, rendu)]
    planche = Image.new("RGB", (sum(x.width for x in ims) + 20, hh), (255, 0, 0)); xo = 0
    for x in ims:
        planche.paste(x, (xo, 0)); xo += x.width + 10
    nom = "%s_%s_p%03d_%s_%s" % (serie, ch, num, MODE, MOTEUR)
    planche.save(os.path.join(out, nom + "_planche.png"))
    rendu.save(os.path.join(out, nom + "_essai.png"))
    print("%s : %d vraie(s) bulle(s), %d zone(s) sur le dessin (%.1f %% de la page masquee), LaMa %.2f s"
          % (nom, len(vraies), len(dessin), 100 * (m > 0).mean(), dt))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("serie"); ap.add_argument("pages", nargs="+", help="ch_3:7 ...")
    ap.add_argument("--out", required=True)
    ap.add_argument("--mode", default="boite", choices=["boite", "ctd"])
    ap.add_argument("--moteur", default="big", choices=["big", "manga"])
    ap.add_argument("--seuil", type=float, default=0.3)
    ap.add_argument("--halo", type=int, default=7)
    a = ap.parse_args()
    MODE, MOTEUR, SEUIL, HALO = a.mode, a.moteur, a.seuil, a.halo
    os.makedirs(a.out, exist_ok=True)
    for x in a.pages:
        ch, n = x.split(":")
        page(a.serie, ch, int(n), a.out)
