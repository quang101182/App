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
MODELE = os.path.join(HERE, "models", "big-lama.pt")
GRANDE = 0.06            # boite > 6 % de la page : on ne masque que les traits du texte, pas toute la boite
_LAMA = {}


def lama(img, masque):
    """img RGB uint8 HxWx3, masque uint8 HxW (255 = a reconstituer) -> RGB uint8."""
    if "m" not in _LAMA:
        _LAMA["m"] = torch.jit.load(MODELE, map_location="cuda").eval()
    H, W = masque.shape
    ph, pw = (8 - H % 8) % 8, (8 - W % 8) % 8
    x = np.pad(img, ((0, ph), (0, pw), (0, 0)), mode="reflect")
    m = np.pad(masque, ((0, ph), (0, pw)), mode="reflect")
    xt = torch.from_numpy(x).permute(2, 0, 1)[None].float().cuda() / 255
    mt = (torch.from_numpy(m)[None, None].float().cuda() > 127).float()
    with torch.no_grad():
        out = _LAMA["m"](xt, mt)
    out = (out[0].permute(1, 2, 0).clamp(0, 1).cpu().numpy() * 255).astype(np.uint8)[:H, :W]
    return np.where(masque[..., None] > 127, out, img)


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


def poser(rendu, boite, texte, est_bulle, taille_max):
    """Texte pose par la fonction de l'app, sur un calque ; contour blanc s'il est pose sur le dessin."""
    import traduire_chapitre as tc
    calque = Image.new("RGB", rendu.size, (255, 255, 255))
    r = tc.poser_texte(calque, boite, texte, est_bulle, taille_max=taille_max)
    a = np.array(calque.convert("L")) < 128                      # les lettres
    base = np.array(rendu)
    if not est_bulle:
        halo = cv2.dilate(a.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
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
        places.append((b["box"], b["trad"], False))
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
    nom = "%s_%s_p%03d" % (serie, ch, num)
    planche.save(os.path.join(out, nom + "_planche.png"))
    rendu.save(os.path.join(out, nom + "_essai.png"))
    print("%s : %d vraie(s) bulle(s), %d zone(s) sur le dessin (%.1f %% de la page masquee), LaMa %.2f s"
          % (nom, len(vraies), len(dessin), 100 * (m > 0).mean(), dt))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("serie"); ap.add_argument("pages", nargs="+", help="ch_3:7 ...")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for x in a.pages:
        ch, n = x.split(":")
        page(a.serie, ch, int(n), a.out)
