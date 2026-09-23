"""Reprise ponctuelle v2.3.0 (23/09/2026) : OPM ch.5-10, narrations amputees par un scan chinois (remontee Video Studio).

Pour chaque chapitre : copie de l'ancienne narration dans la corbeille de l'app, narration refaite en REPRENANT
l'analyse des pages (--reuse-vision : rien n'est relu en image), karaoke, controle (0 page amputee, 0 caractere CJK,
une voix par page narree). Puis, seulement si TOUT est vert : anciennes videos a la corbeille (route de l'app) et
nouvelles demandees avec EXACTEMENT les reglages des anciennes.  Usage : python refaire_opm_latin.py [5-10]
"""
import json, os, re, shutil, subprocess, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, "..", "sources"))
PY = r"D:\Download\02-Apps-Web\kohya-trainer\.venv\Scripts\python.exe"
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
TAG = "gemini-charon"
R = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]")
a, _, b = (sys.argv[1] if len(sys.argv) > 1 else "5-10").partition("-")
CHAPS = ["one-punch-man/ch_%d" % n for n in range(int(a), int(b or a) + 1)]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def api(path, body):
    r = urllib.request.Request("http://127.0.0.1:8190" + path, data=json.dumps(body).encode(),
                               headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=60))


bilan, reglages = {}, {}
for d in CHAPS:
    nd = os.path.join(SRC, *d.split("/"), "narration", TAG)
    vj = os.path.join(SRC, *d.split("/"), "video", TAG + ".json")
    if os.path.isfile(vj):
        reglages[d] = json.load(open(vj, encoding="utf-8")).get("reglages") or {}
    dest = os.path.join(SRC, "_corbeille", time.strftime("%Y%m%d-%H%M%S") + "_" + d.replace("/", "__") + "__narration__" + TAG + "-avant-latin")
    shutil.copytree(nd, dest)
    t0 = time.time()
    p = subprocess.run([PY, os.path.join(HERE, "narrate_chapter.py"), d, "--engine", "gemini", "--voice", "Charon",
                        "--tag", TAG, "--reuse-vision", TAG], capture_output=True, text=True, encoding="utf-8", errors="replace")
    open(os.path.join(nd, "run.log"), "a", encoding="utf-8").write("\n===== %s · reprise alphabet latin =====\n%s%s"
                                                                   % (time.strftime("%Y-%m-%dT%H:%M:%S"), p.stderr, p.stdout))
    if p.returncode != 0:
        bilan[d] = "ECHEC narration (code %d) : %s" % (p.returncode, (p.stdout or p.stderr).strip().splitlines()[-1][:200])
        print(d, bilan[d], flush=True); continue
    k = subprocess.run([PY, os.path.join(HERE, "karaoke_mots.py"), d, TAG, "--force"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    n = json.load(open(os.path.join(nd, "narration.json"), encoding="utf-8"))
    pages = n["pages"]
    narrees = [x for x in pages if (x.get("narration") or "").strip()]
    amput = [x["page"] for x in pages if x.get("cjk_retires")]
    cjk = [x["page"] for x in pages if R.search(x.get("narration") or "")]
    sans_voix = [x["page"] for x in narrees if not x.get("audio")]
    ok = not amput and not cjk and not sans_voix and k.returncode == 0
    bilan[d] = "%s : %d/%d pages narrees, amputees %s, CJK %s, sans voix %s, karaoke %s, latin %s, %.0f s, %.3f $" % (
        "OK" if ok else "KO", len(narrees), len(pages), amput or 0, cjk or 0, sans_voix or 0, "ok" if k.returncode == 0 else "ECHEC",
        (n.get("stats") or {}).get("latin"), time.time() - t0, (n.get("stats") or {}).get("cout_recit", 0) + (n.get("stats") or {}).get("cout_tts", 0))
    print(d, bilan[d], flush=True)

tous_ok = all(v.startswith("OK") for v in bilan.values())
print("\nnarrations : %s" % ("TOUT VERT" if tous_ok else "au moins un chapitre en echec -> videos NON refaites"), flush=True)
if tous_ok:
    for d in CHAPS:
        if d in reglages:
            print("corbeille video", d, api("/manga/video_suppr", {"d": d, "tag": TAG}), flush=True)
    par_reg = {}
    for d, rg in reglages.items():
        par_reg.setdefault(json.dumps({k: v for k, v in rg.items() if k not in ("musique_noms", "graine")}, sort_keys=True), []).append(d)
    for rg, ds in par_reg.items():
        print("videos demandees", ds, api("/manga/video", {"entrees": [{"d": d, "tag": TAG} for d in ds], "reglages": json.loads(rg)}), flush=True)
