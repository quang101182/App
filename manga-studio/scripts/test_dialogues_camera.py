# -*- coding: utf-8 -*-
"""Banc dialogues.py 1.31.0 : video des Dialogues avec la camera « case par case » (dialogues_camera.py).
LECTURE SEULE sur les donnees de Quang : le chapitre est COPIE dans un dossier jetable (MANGA_SOURCES_DIR).

U. Logique (miroir du lecteur) :
  U1 dllFile : repliques en cases 2 puis 0 sur 4 cases -> [muette 1, rep(2), rep(0), muette 3]
  U2 page sans replique a 3 cases -> ses 3 cases muettes, l'etape « vide » disparait
  U3 page a 1 case -> file inchangee
  U4 vue : zoom borne a [1, 3], vue dans l'ecran ; une pastille dans la MARGE n'est pas coupee
  U5 glissement : courbe 0 -> 1 croissante
R. Reel (venv du serveur, copie de noritaka/ch_1, pages 5-6) :
  R1 la video existe ; image et son a moins de 50 ms
  R2 a chaque frontiere d'etape, l'image change (>= 90 % des frontieres)
  R3 la camera ZOOME (>= 80 % des repliques cadrees plus serre que la page)
  R4 3 cases sans dialogue intercalees (celles du lecteur sur ces pages)
  R5 la video d'avant (pages fixes, empreinte du depot) est dite « perimee » ; la nouvelle « a jour »
Usage : python test_dialogues_camera.py [--script dialogues.py] [--sans-reel]"""
import json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dialogues_camera as dc

a = sys.argv[1:]
SCRIPT = a[a.index("--script") + 1] if "--script" in a else os.path.join(HERE, "dialogues.py")
PY = r"D:\Download\02-Apps-Web\kohya-trainer\.venv\Scripts\python.exe"
SRC = r"C:\Users\quang\Documents\MangaStudio-donnees\sources"
OK, KO = [], []


def check(nom, cond, d=""):
    (OK if cond else KO).append(nom); print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(d)[:160] if d else ""), flush=True)


print("=== U. logique")
pg4 = {"W": 1000, "H": 1000, "cases": [[0, 0, 500, 500], [500, 0, 1000, 500], [0, 500, 500, 1000], [500, 500, 1000, 1000]]}
cases = {"pages": {"p1.jpg": pg4, "p2.jpg": {"W": 1000, "H": 1000, "cases": pg4["cases"][:3]}, "p3.jpg": {"W": 1000, "H": 1000, "cases": [[0, 0, 1000, 1000]]}}}
fich = ["p1.jpg", "p2.jpg", "p3.jpg"]
A = {"page": 1, "file": "p1.jpg", "box": {"x": .1, "y": .6, "w": .1, "h": .1}, "cle": "A"}      # case 2
B = {"page": 1, "file": "p1.jpg", "box": {"x": .1, "y": .1, "w": .1, "h": .1}, "cle": "B"}      # case 0
f = dc.file_cases([A, B], cases, fich)
sig = [("m%d" % x["k"]) if x.get("muette") else x["cle"] for x in f]
check("U1 cases muettes intercalees comme le lecteur", sig == ["m1", "A", "B", "m3"], sig)
f2 = dc.file_cases([{"page": 2, "file": "p2.jpg", "vide": True, "src": "x"}], cases, fich)
check("U2 page sans dialogue -> ses cases une a une", [x.get("k") for x in f2] == [0, 1, 2] and all(x.get("muette") for x in f2), [x.get("k") for x in f2])
V = {"page": 3, "file": "p3.jpg", "vide": True, "src": "x"}
check("U3 page a 1 case -> inchangee", dc.file_cases([V], cases, fich) == [V])
geo = (240, 0, 600, 900)                                  # page etroite centree : marges de 240 px a gauche et a droite
v = dc.vue((.4, .4, .45, .45), geo)
k = dc.VW / (v[2] - v[0])
check("U4 zoom borne a 3 et vue dans l'ecran", abs(k - 3) < 1e-6 and v[0] >= 0 and v[2] <= dc.VW and v[1] >= 0 and v[3] <= dc.ZH, (round(k, 3), v))
v = dc.vue((.6, .3, 1.15, .5), geo)                       # pastille qui deborde a DROITE de la page (dans la marge)
check("U4 pastille dans la marge : pas coupee", v[2] >= geo[0] + 1.15 * geo[2] - 1, (v, geo[0] + 1.15 * geo[2]))
xs = [dc.bezier(i / 20) for i in range(21)]
check("U5 glissement 0 -> 1 croissant", xs[0] == 0 and xs[-1] == 1 and all(b >= a_ for a_, b in zip(xs, xs[1:])))

if "--sans-reel" not in a:
    print("=== R. reel (copie jetable de noritaka/ch_1, pages 5-6)")
    tmp = tempfile.mkdtemp(prefix="banc_dlgcam_")
    try:
        for n in os.listdir(os.path.join(SRC, "noritaka")):
            s_ = os.path.join(SRC, "noritaka", n)
            if n.startswith("ch_") or n == "tomes":
                continue
            (shutil.copytree if os.path.isdir(s_) else shutil.copy2)(s_, os.path.join(tmp, "noritaka", n)) if os.makedirs(os.path.join(tmp, "noritaka"), exist_ok=True) is None else None
        shutil.copytree(os.path.join(SRC, "noritaka", "ch_1"), os.path.join(tmp, "noritaka", "ch_1"))
        dd = os.path.join(tmp, "noritaka", "ch_1", "dialogues")
        avant = json.load(open(os.path.join(dd, "dialogues.json"), encoding="utf-8"))
        env = dict(os.environ, MANGA_SOURCES_DIR=tmp)
        plan = lambda: json.loads((lambda t: t[t.find("{"):])(subprocess.run([PY, SCRIPT, "plan", "noritaka/ch_1"], env=env, cwd=HERE,
                                  capture_output=True, text=True, encoding="utf-8").stdout))
        p0 = plan()
        check("R5 video d'avant (pages fixes) dite a refaire", (p0.get("videos") or {}).get("5-6") == "perimee", p0.get("videos"))
        r = subprocess.run([PY, SCRIPT, "video", "noritaka/ch_1", "--pages", "5-6"], env=env, cwd=HERE, capture_output=True, text=True, encoding="utf-8")
        out = r.stdout + r.stderr
        mp4 = os.path.join(dd, "video", "dialogues_p5-6.mp4")
        dur = lambda t: float(subprocess.run(["ffprobe", "-v", "error", "-select_streams", t, "-show_entries", "stream=duration", "-of", "csv=p=0", mp4],
                                             capture_output=True, text=True).stdout.strip() or 0)
        dv, da = (dur("v:0"), dur("a:0")) if os.path.isfile(mp4) else (0, 0)
        check("R1 video faite, image et son a < 50 ms", r.returncode == 0 and dv > 10 and abs(dv - da) < 0.05, (r.returncode, dv, da, out[-200:]))
        p1 = plan()
        check("R5 nouvelle video dite a jour", (p1.get("videos") or {}).get("5-6") == "a_jour", p1.get("videos"))
        m = [l for l in out.splitlines() if "camera case par case" in l]
        check("R4 3 cases sans dialogue intercalees", bool(m) and "dont 3 case" in m[0], m)
        # R2 / R3 : on rejoue le plan de camera en memoire (memes fonctions que la video) et on lit les images aux frontieres
        sys.path.insert(0, HERE)
        os.environ["MANGA_SOURCES_DIR"] = tmp
        import cases_video as cv
        cs = cv.cases_chapitre("noritaka/ch_1")
        doc = json.load(open(os.path.join(dd, "dialogues.json"), encoding="utf-8"))
        man = json.load(open(os.path.join(tmp, "noritaka", "ch_1", "manifest.json"), encoding="utf-8"))
        fi = [q.get("file") for q in man.get("pages") or []]
        reps = sorted([x for x in doc["repliques"] if x.get("lire") and 5 <= x["page"] <= 6], key=lambda x: (x["page"], x.get("ordre") if x.get("ordre") is not None else x.get("id") or 0))
        fl = dc.file_cases(reps, cs, fi)
        zoom = [x for x in fl if not x.get("muette")]
        serres = 0
        for x in zoom:
            png = os.path.join(tmp, "noritaka", "ch_1", *(x.get("img_rel") or "traduction/fr/" + x["file"]).split("/"))
            from PIL import Image
            with Image.open(png) as im:
                g = dc._place(im)
            vv = dc.vue(dc.rect_etape(x, dc.pastille_frac(x, x["qui"], g)), g)
            serres += (vv[2] - vv[0]) < dc.VW * 0.95
        check("R3 la camera zoome sur les repliques", serres >= 0.8 * len(zoom), "%d / %d" % (serres, len(zoom)))
        # frontieres : duree de chaque etape = son de chaque etape (lu dans la video via les silences ? non : on compte les changements)
        fr = subprocess.run(["ffmpeg", "-v", "error", "-i", mp4, "-vf", "scale=54:96,format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
        n = len(fr) // (54 * 96)
        imgs = [fr[i * 5184:(i + 1) * 5184] for i in range(n)]
        diff = [sum(abs(p - q) for p, q in zip(imgs[i][::7], imgs[i + 1][::7])) for i in range(n - 1)]
        bouge = [d > 1500 for d in diff]                      # une SERIE d'images qui bougent = un glissement (ou une coupe)
        # le halo change d'un coup a la frontiere, puis la camera glisse (depart lent) : ecart <= 5 images = le MEME mouvement
        debuts, dern = [], -99
        for i, b in enumerate(bouge):
            if b:
                if i - dern > 5:
                    debuts.append(i)
                dern = i
        series = len(debuts)
        tenues = sum(1 for d in diff if d == 0)
        check("R2 un mouvement par etape, image tenue entre deux", abs(series - len(fl)) <= 2 and tenues > 0.4 * n,
              "%d mouvements pour %d etapes, images tenues %d / %d" % (series, len(fl), tenues, n))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
print("\nVERDICT : %d/%d" % (len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
