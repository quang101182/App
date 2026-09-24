# -*- coding: utf-8 -*-
"""Banc S1 (compartiment secret, 24/09/2026) : l'instance privee (8192) et l'instance normale (8190) ne se voient pas.

Pre-requis : les deux serveurs tournent (espace_prive.py pour 8192).
1. 8192 sert la MEME app que 8190.
2. Un chapitre importe cote prive (vrai manga_fetch import, MANGA_SOURCES_DIR = dossier prive) : visible sur 8192,
   absent de 8190 ; et l'inverse avec un chapitre importe cote normal.
3. Une ecriture faite PAR le serveur prive (bibliotheque : masquer) atterrit dans le dossier prive ; le fichier de
   l'espace normal ne change pas d'un octet.
Tout ce que le banc cree est efface a la fin ; la bibliotheque privee est remise dans son etat d'avant.
"""
import json, os, shutil, subprocess, sys, tempfile, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
MS = os.path.dirname(HERE)
NORMAL = os.path.normpath(os.path.join(MS, "sources"))
PRIVE = os.path.expanduser(r"~\Documents\MangaStudio-donnees\prive")
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
MF_PY = os.path.join(os.environ.get("LOCALAPPDATA", ""), "manga-fetch", "venv", "Scripts", "python.exe")
MF = os.path.join(MS, "manga-fetch", "manga_fetch.py")
ok = ko = 0


def check(nom, cond, detail=""):
    global ok, ko
    ok += bool(cond); ko += not cond
    print("  [%s] %s%s" % ("OK" if cond else "KO", nom, (" -- " + str(detail)) if detail and not cond else ""))


def brut(port, path, body=None):
    r = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path),
                               data=json.dumps(body).encode() if body is not None else None,
                               headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=60) as x:
        return x.read()


def api(port, path, body=None):
    return json.loads(brut(port, path, body))


def dirs(port):
    return {i["dir"] for i in api(port, "/manga/sources")["items"]}


def importer(racine, titre, pages):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    env.pop("MANGA_SOURCES_DIR", None)
    if racine != NORMAL:
        env["MANGA_SOURCES_DIR"] = racine
    avant = set(os.listdir(racine))
    r = subprocess.run([MF_PY, MF, "import", pages, "--title", titre, "--chapter", "1"], env=env, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=180)
    nouveaux = sorted(set(os.listdir(racine)) - avant)
    return r, nouveaux


pages = tempfile.mkdtemp(prefix="banc-espace-pages-")
src = next(os.path.join(r, d) for r, ds, _f in os.walk(NORMAL) for d in ds
           if d.startswith("ch_") and not os.path.relpath(r, NORMAL).startswith("_")
           and len([x for x in os.listdir(os.path.join(r, d)) if x.lower().endswith((".jpg", ".png", ".webp"))]) >= 2)
for x in sorted(y for y in os.listdir(src) if y.lower().endswith((".jpg", ".png", ".webp")))[:2]:
    shutil.copyfile(os.path.join(src, x), os.path.join(pages, x))
BIB_P = os.path.join(PRIVE, "_bibliotheque.json")
BIB_N = os.path.join(NORMAL, "_bibliotheque.json")
bib_p_avant = open(BIB_P, "rb").read() if os.path.isfile(BIB_P) else None
bib_n_avant = open(BIB_N, "rb").read() if os.path.isfile(BIB_N) else None
crees = []
try:
    print("1. meme app")
    check("8192 sert /manga/ identique a 8190", brut(8192, "/manga/") == brut(8190, "/manga/"))
    d_n0, d_p0 = dirs(8190), dirs(8192)
    check("rien de l'espace normal dans l'espace prive", not (d_n0 & d_p0), sorted(d_n0 & d_p0)[:5])
    if ko:   # securite : un 8192 qui voit les donnees normales ferait ecrire l'etape 3 dans la VRAIE bibliotheque
        raise SystemExit("\nARRET (etape 1 en echec, rien n'est ecrit)\n%d/%d" % (ok, ok + ko))

    print("2. capture de chaque cote")
    r, nv = importer(PRIVE, "zz banc espace prive", pages)
    crees += [os.path.join(PRIVE, n) for n in nv]
    check("import prive : code 0 et une serie creee dans le dossier prive", r.returncode == 0 and len(nv) == 1,
          (nv, (r.stdout + r.stderr)[-200:]))
    slug_p = nv[0] if nv else "?"
    check("visible sur 8192", any(d.startswith(slug_p + "/") for d in dirs(8192)))
    check("ABSENT de 8190", not any(d.startswith(slug_p + "/") for d in dirs(8190)))
    check("absent du dossier normal", not os.path.exists(os.path.join(NORMAL, slug_p)))

    r, nv = importer(NORMAL, "zz banc espace normal", pages)
    crees += [os.path.join(NORMAL, n) for n in nv]
    check("import normal : code 0 et une serie creee dans le dossier normal", r.returncode == 0 and len(nv) == 1,
          (nv, (r.stdout + r.stderr)[-200:]))
    slug_n = nv[0] if nv else "?"
    check("visible sur 8190", any(d.startswith(slug_n + "/") for d in dirs(8190)))
    check("ABSENT de 8192", not any(d.startswith(slug_n + "/") for d in dirs(8192)))
    check("absent du dossier prive", not os.path.exists(os.path.join(PRIVE, slug_n)))

    print("3. ecriture faite par le serveur prive")
    m = api(8192, "/manga/bibliotheque", {"action": "masquer", "slug": slug_p})
    check("masquee cote prive", slug_p in m.get("masquees", []), m)
    check("ecrite dans le dossier prive", os.path.isfile(BIB_P) and slug_p in open(BIB_P, encoding="utf-8").read())
    check("bibliotheque normale inchangee a l'octet",
          (open(BIB_N, "rb").read() if os.path.isfile(BIB_N) else None) == bib_n_avant)
    check("8190 ne la voit pas masquee", slug_p not in api(8190, "/manga/bibliotheque").get("masquees", []))
finally:
    for c in crees:
        shutil.rmtree(c, ignore_errors=True)
    if bib_p_avant is None:
        if os.path.isfile(BIB_P): os.remove(BIB_P)
    else:
        open(BIB_P, "wb").write(bib_p_avant)
    shutil.rmtree(pages, ignore_errors=True)
check("nettoyage : series de test effacees", not any(os.path.exists(c) for c in crees))
print("\n%d/%d" % (ok, ok + ko))
sys.exit(1 if ko else 0)
