# -*- coding: utf-8 -*-
"""Banc manga-fetch 0.8.1 : webtoon decoupe en bandes PRESQUE CARREES (ROADMAP § 4-quindecies, « Hors perimetre », B1-B3).

Capture l'onglet donne (fenetre CDP au choix) avec le manga_fetch.py donne, dans un dossier de sortie et un journal
TEMPORAIRES (aucune donnee reelle touchee, tout est efface a la fin), puis compare aux images DISTINCTES de la page
(meme largeur que les pages) : verdict « toutes les bandes » ou « tronque ». N'imprime ni adresse ni titre.

Usage : python banc_bandes_carrees.py <port CDP> <filtre d'onglet> [chemin de manga_fetch.py]
  ex. : python banc_bandes_carrees.py 9224 275006                      (code courant -> doit etre VERT)
        python banc_bandes_carrees.py 9224 275006 manga_fetch.py.bak-… (code 0.8.0 = mutation -> doit etre ROUGE)
"""
import os, subprocess, sys, tempfile, shutil, json
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
PORT, FILTRE = sys.argv[1], sys.argv[2]
ICI = os.path.dirname(os.path.abspath(__file__))
MF = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith("--") else os.path.join(ICI, "..", "manga-fetch", "manga_fetch.py")
PY = os.path.join(os.environ.get("LOCALAPPDATA", ""), "manga-fetch", "venv", "Scripts", "python.exe")

# 1) la verite de la page : images DISTINCTES de la largeur dominante (hors commentaires)
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:" + PORT)
    pg = next(x for c in b.contexts for x in c.pages if FILTRE in x.url)
    ref = pg.evaluate("""() => { const t = [...document.images].filter(i => (i.currentSrc||i.src) && !(i.currentSrc||i.src).startsWith('data:')
                                   && !i.closest('#comments, .comments, .comment, [id^="comment"], #disqus_thread') && i.naturalWidth > 250);
        const n = {}; t.forEach(i => n[i.naturalWidth] = (n[i.naturalWidth] || 0) + 1);
        const W = +Object.entries(n).sort((a, b) => b[1] - a[1])[0][0];
        return { W, distinctes: new Set(t.filter(i => i.naturalWidth === W).map(i => i.currentSrc || i.src)).size }; }""")
print("page : largeur dominante %d px, %d bandes distinctes" % (ref["W"], ref["distinctes"]))

tmp = tempfile.mkdtemp(prefix="banc_bandes_")
try:
    env = dict(os.environ, MANGA_CAPTURE_PORT=PORT, MANGA_CAPTURE_DONNEES=os.path.join(tmp, "donnees"),
               PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
    os.makedirs(env["MANGA_CAPTURE_DONNEES"])
    r = subprocess.run([PY, MF, "capture", "--tab", FILTRE, "--title", "banc bandes", "--chapter", "1", "--page-1",
                        "--out", os.path.join(tmp, "out")], env=env, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=1200)
    lignes = [l for l in r.stdout.splitlines() if l.startswith(("OK :", "ÉCHEC", "ECHEC", "Mode", "Webtoon"))]   # jamais « Notes » : elles portent des adresses
    for l in lignes:
        print("  |", l.split(" -> ")[0][:160])
    ch = os.path.join(tmp, "out", "banc-bandes", "ch_1")
    man = json.load(open(os.path.join(ch, "manifest.json"), encoding="utf-8")) if os.path.isfile(os.path.join(ch, "manifest.json")) else {}
    ok_l = next((l for l in r.stdout.splitlines() if l.startswith("OK :")), "")
    prises = int(ok_l.split("/")[0].split()[-1]) if ok_l else 0
    echec = any("ECHEC" in n for n in man.get("notes", [])) or r.returncode not in (0, 3) or not ok_l
    # une bande de < 10 Ko est ECARTEE par la regle existante (bande blanche d'espacement) : comptee, pas perdue
    ecartees = sum(1 for n in man.get("notes", []) if n.startswith("écartée"))
    print("code %s · bandes prises %d + écartées (quasi vides) %d / %d distinctes · ECHEC ecrit : %s"
          % (r.returncode, prises, ecartees, ref["distinctes"], echec))
    vert = (not echec) and prises + ecartees >= ref["distinctes"] - 1   # tolerance : 1 image de la largeur hors histoire
    # v0.8.2 : la QUALITE du decoupage (Quang 26/09 : « des bulles decoupees en plein milieu »). Une coupe « dans le dessin » =
    # une ligne de coupe dont les pixels ne sont pas unis (meme regle que _coupes_webtoon : ecart a la mediane > 24 sur > 2 %).
    from PIL import Image
    import numpy as np
    def dans_le_dessin(bas, haut):
        n = 0
        for img, rang in ((bas, -1), (haut, 0)):
            a = np.asarray(img.convert("L"), dtype=np.int16)[rang]
            n = max(n, int((np.abs(a - np.median(a)) > 24).sum()))
        return n > 0.02 * bas.width
    dec = man.get("decoupe")
    orig = os.path.join(ch, "originaux")
    if dec and os.path.isdir(orig):
        om = json.load(open(os.path.join(orig, "manifest.json"), encoding="utf-8"))["pages"]
        ims = [Image.open(os.path.join(orig, p["file"])) for p in om]
        avant = sum(dans_le_dessin(x, y) for x, y in zip(ims, ims[1:]) if x.width == y.width)
        print("découpage : %d tuiles -> %d pages · coupes dans le dessin : %d aux bords des tuiles d'origine -> %d après"
              % (dec["bandes"], dec["pages"], avant, dec["coupes_hors_gouttiere"]))
        vert = vert and dec["coupes_hors_gouttiere"] <= max(2, avant // 10)
    else:
        print("découpage : AUCUN (les tuiles restent telles que le site les a tranchées)")
        vert = False
    print("VERDICT :", "VERT — toutes les bandes, recoupées aux gouttières" if vert else "ROUGE")
finally:
    if "--garder" in sys.argv:
        print("sortie GARDÉE (à effacer après analyse) :", tmp)
    else:
        shutil.rmtree(tmp, ignore_errors=True)
sys.exit(0 if vert else 1)
