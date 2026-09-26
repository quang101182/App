# -*- coding: utf-8 -*-
"""REDECOUPER des chapitres deja captures avec le decoupage de manga-fetch >= 0.8.2 (ROADMAP § 4-quindecies, bandes).

Pour chaque chapitre (dossier ch_*) :
  - SAUVEGARDE complete du dossier dans <racine>/_avant_redecoupe/<serie>__<ch>__<horodatage>/ (rien n'est jamais efface) ;
  - si le chapitre a DEJA ete decoupe (manifest.decoupe + originaux/manifest.json) : on repart des ORIGINAUX (les pages
    decoupees sont retirees, les originaux et leur manifeste remis en place) ;
  - decouper_bandes() ; puis mesure « raccords dans le dessin » avant -> apres.
REFUSE un chapitre qui porte des donnees liees aux numeros de page (narration, traduction, video…) : il est liste, pas touche.
  --ecarter-lies (accord explicite de Quang, 26/09 02h46 : « pas besoin de refaire la narration, la video ; occupe-toi des
  images ») : ces donnees sont RETIREES du chapitre (elles decrivent les anciennes pages) et restent dans la sauvegarde ;
  une video deja rendue (video/*.mp4) ne depend plus des pages : elle reste.
Usage : python redecouper.py <racine> <serie> <ch1> [<ch2> …] [--essai] [--ecarter-lies]
N'imprime pas le nom de la serie (numero de chapitre seulement).
"""
import importlib.util, json, os, shutil, sys, tempfile, time
import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
Image.MAX_IMAGE_PIXELS = None
ICI = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("mf", os.path.join(ICI, "..", "manga-fetch", "manga_fetch.py"))
mf = importlib.util.module_from_spec(spec); spec.loader.exec_module(mf)
RAC, SERIE, CHS = sys.argv[1], sys.argv[2], [a for a in sys.argv[3:] if not a.startswith("--")]
ESSAI = "--essai" in sys.argv
ECARTER = "--ecarter-lies" in sys.argv
GARDES = {"video"}                                            # --ecarter-lies : ce qui reste dans le chapitre
AUTORISES = {"manifest.json", "langue.json", "originaux"}


def dessin(d):
    man = json.load(open(os.path.join(d, "manifest.json"), encoding="utf-8"))
    b = []
    for p in man["pages"]:
        with Image.open(os.path.join(d, p["file"])) as im:
            a = np.asarray(im.convert("L"), dtype=np.int16)
        b.append((a.shape[1], a[:8], a[-8:]))
    return len(b), sum(1 for x, y in zip(b, b[1:]) if x[0] == y[0] and mf._coupe_dans_dessin(x[2], y[1]))


def remettre_originaux(d):
    man = json.load(open(os.path.join(d, "manifest.json"), encoding="utf-8"))
    orig = os.path.join(d, "originaux")
    for p in man["pages"]:                                   # pages decoupees : retirees (elles sont dans la sauvegarde)
        f = os.path.join(d, p["file"])
        if os.path.isfile(f): os.remove(f)
    om = json.load(open(os.path.join(orig, "manifest.json"), encoding="utf-8"))
    for p in om["pages"]:
        os.replace(os.path.join(orig, p["file"]), os.path.join(d, p["file"]))
    os.replace(os.path.join(orig, "manifest.json"), os.path.join(d, "manifest.json"))
    shutil.rmtree(orig, ignore_errors=True)


horo = time.strftime("%Y%m%d-%H%M%S")
tot = {"faits": 0, "refuses": 0, "avant": 0, "apres": 0}
for ch in CHS:
    src = os.path.join(RAC, SERIE, "ch_" + ch)
    if not os.path.isfile(os.path.join(src, "manifest.json")):
        print("ch.%s : absent" % ch); continue
    autres = [f for f in os.listdir(src) if not os.path.splitext(f)[1].lower() in mf.IMG_EXTS and f not in AUTORISES]
    if autres and ECARTER and not ESSAI:
        pass
    elif autres:
        print("ch.%s : REFUSÉ (données liées aux pages : %s)" % (ch, ", ".join(autres[:4]))); tot["refuses"] += 1; continue
    tmp = None
    if ESSAI:
        tmp = tempfile.mkdtemp(prefix="redecoupe_essai_"); d = os.path.join(tmp, "ch"); shutil.copytree(src, d)
    else:
        sauve = os.path.join(RAC, "_avant_redecoupe", "%s__ch_%s__%s" % (SERIE, ch, horo))
        shutil.copytree(src, sauve); d = src
        for f in (autres if ECARTER else []):
            if f in GARDES: continue
            x = os.path.join(d, f)
            shutil.rmtree(x) if os.path.isdir(x) else os.remove(x)
            print("ch.%s : « %s » retiré du chapitre (gardé dans la sauvegarde)" % (ch, f))
    p0, d0 = dessin(d)
    man = json.load(open(os.path.join(d, "manifest.json"), encoding="utf-8"))
    if man.get("decoupe") and os.path.isfile(os.path.join(d, "originaux", "manifest.json")):
        remettre_originaux(d)
    r = mf.decouper_bandes(d)
    p1, d1 = dessin(d)
    tot["faits"] += 1; tot["avant"] += d0; tot["apres"] += d1
    print("ch.%-5s %4d p. -> %4d p. · raccords dans le dessin %3d -> %d%s" % (ch, p0, p1, d0, d1, "" if r else " · (rien à découper)"))
    if tmp: shutil.rmtree(tmp, ignore_errors=True)
print("\n%s : %d chapitre(s) traité(s), %d refusé(s) · raccords dans le dessin %d -> %d%s"
      % ("ESSAI (copies)" if ESSAI else "FAIT", tot["faits"], tot["refuses"], tot["avant"], tot["apres"],
         "" if ESSAI else " · sauvegardes : _avant_redecoupe/"))
