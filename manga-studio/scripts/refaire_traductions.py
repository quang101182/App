"""T4 + T5 (4-sexies, 23/09/2026) : retraduire les chapitres d'une serie avec traduire_chapitre >= v1.96.0, puis refaire
les videos qui montrent ces pages traduites.

Par chapitre : copie de l'ancienne traduction dans la corbeille de l'app (une seule fois), traduction COMPLETE (jamais
--pages : il reecrirait traduction.json avec les seules pages refaites), controle (pages blanches). Puis, seulement si
TOUT est vert : pour chaque video dont les reglages montrent ces pages (pages == langue), l'ancienne part a la corbeille
(route de l'app) et une nouvelle est demandee avec les MEMES reglages (sauf graine et liste figee des morceaux).
Usage : python refaire_traductions.py one-punch-man 1-10 [--langue fr] [--sans-videos]
"""
import argparse, json, os, shutil, subprocess, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, "..", "sources"))
PY = r"D:\Download\02-Apps-Web\kohya-trainer\.venv\Scripts\python.exe"
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def api(path, body):
    r = urllib.request.Request("http://127.0.0.1:8190" + path, data=json.dumps(body).encode(),
                               headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=60))


ap = argparse.ArgumentParser()
ap.add_argument("serie"); ap.add_argument("chapitres"); ap.add_argument("--langue", default="fr")
ap.add_argument("--sans-videos", action="store_true")
ap.add_argument("--rerendu", action="store_true", help="v1.97.0 : effacement + pose refaits depuis traduction.json, 0 appel")
ap.add_argument("--version-min", default="1.96.0")
a = ap.parse_args()
lo, _, hi = a.chapitres.partition("-")
chs = sorted((d for d in os.listdir(os.path.join(SRC, a.serie)) if d.startswith("ch_") and float(lo) <= float(d[3:]) <= float(hi or lo)),
             key=lambda d: float(d[3:]))
bilan, cout = {}, 0.0
for ch in chs:
    d = a.serie + "/" + ch
    td = os.path.join(SRC, a.serie, ch, "traduction", a.langue)
    marque = d.replace("/", "__") + "__traduction__" + a.langue + ("-avant-v197" if a.rerendu else "-avant-v196")
    if os.path.isdir(td) and not any(marque in x for x in os.listdir(os.path.join(SRC, "_corbeille"))):
        shutil.copytree(td, os.path.join(SRC, "_corbeille", time.strftime("%Y%m%d-%H%M%S") + "_" + marque))
    t0 = time.time()
    r = subprocess.run([PY, os.path.join(HERE, "traduire_chapitre.py"), d, "--langue", a.langue, "--engine", "gemini"] + (["--rerendu"] if a.rerendu else []),
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENV)
    t = json.load(open(os.path.join(td, "traduction.json"), encoding="utf-8"))
    st = t.get("stats") or {}
    cout += st.get("cout", 0)
    ok = r.returncode == 0 and t.get("version", "") >= a.version_min
    bilan[d] = ok
    print("%s : code %d, v%s, %d pages, %d traduites, hors zones %d, pages prudentes %d, %.0f s, %.3f $" % (
        d, r.returncode, t.get("version"), len(t["pages"]), st.get("traduites", 0), st.get("hors_zones", 0),
        st.get("pages_prudentes", 0), time.time() - t0, st.get("cout", 0)), flush=True)
c = subprocess.run([PY, os.path.join(HERE, "controle_traduction.py"), a.serie, a.chapitres, "--langue", a.langue],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENV)
print(c.stdout, flush=True)
tout_vert = all(bilan.values()) and c.returncode == 0
print("traductions : %s ; cout %.3f $" % ("TOUT VERT" if tout_vert else "ECHEC -> videos NON refaites", cout), flush=True)
if tout_vert and not a.sans_videos:
    par_reg = {}
    for ch in chs:
        vd = os.path.join(SRC, a.serie, ch, "video")
        for f in (os.listdir(vd) if os.path.isdir(vd) else []):
            if not f.endswith(".json") or f.endswith(".progress.json"):
                continue
            v = json.load(open(os.path.join(vd, f), encoding="utf-8"))
            rg = v.get("reglages") or {}
            if rg.get("pages") != a.langue:
                continue                                       # video en VO : la traduction n'y figure pas
            d, tag = a.serie + "/" + ch, f[:-5]
            print("corbeille video", d, tag, api("/manga/video_suppr", {"d": d, "tag": tag}), flush=True)
            cle = json.dumps({k: x for k, x in rg.items() if k not in ("musique_noms", "graine")}, sort_keys=True)
            par_reg.setdefault(cle, []).append({"d": d, "tag": tag})
    for cle, entrees in par_reg.items():
        print("videos demandees", [e["d"] for e in entrees], api("/manga/video", {"entrees": entrees, "reglages": json.loads(cle)}), flush=True)
