# -*- coding: utf-8 -*-
"""Banc des routes bibliotheque du proxy (v1.76.0) : pochettes + suppression, sur une serie JETABLE.

Usage : python test_bibliotheque.py [port]   (8191 = copie patchee de test, 8190 = proxy reel)
Cree sources/banc-bib/ (copie de 5 pages d'OPM 301), l'efface a la fin. Ne touche a AUCUN vrai chapitre,
sauf les pochettes AniList de claymore et boruto-tow-blue-vortex (voulues). Verdict chiffre en sortie.
"""
import json, os, shutil, sys, time, urllib.request

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8191
BASE = "http://127.0.0.1:%d" % PORT
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
SRC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sources"))
BANC = os.path.join(SRC, "banc-bib")
OK, KO = [], []


def api(path, body=None):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


def fabrique():
    shutil.rmtree(BANC, ignore_errors=True)
    src = os.path.join(SRC, "one-punch-man", "ch_301")
    dst = os.path.join(BANC, "ch_1")
    os.makedirs(dst)
    man = json.load(open(os.path.join(src, "manifest.json"), encoding="utf-8"))
    man["pages"] = man["pages"][1:6]
    man.update(slug="banc-bib", title="Banc Bib", chapter="1", notes=[])
    for p in man["pages"]:
        shutil.copy(os.path.join(src, p["file"]), os.path.join(dst, p["file"]))
    json.dump(man, open(os.path.join(dst, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False)
    return man


def corbeille_nettoie(rel):
    if rel:
        shutil.rmtree(os.path.join(SRC, rel), ignore_errors=True)


print("=== pochettes (AniList)")
for slug, titre in (("claymore", "Claymore"), ("boruto-tow-blue-vortex", "Boruto Two Blue Vortex")):
    r = api("/manga/pochette", {"slug": slug, "source": "anilist", "titre": titre})
    check("pochette " + slug, r.get("ok") and os.path.isfile(os.path.join(SRC, r.get("pochette", "x"))), r)
items = api("/manga/sources")["items"]
check("la liste porte la pochette", any(i.get("pochette") == "claymore/pochette.png" or
                                        (i.get("pochette") or "").startswith("claymore/pochette") for i in items))

print("=== suppression de PAGES")
man = fabrique()
f0 = man["pages"][0]["file"]
r = api("/manga/source_delete", {"d": "banc-bib/ch_1", "pages": [f0]})
m2 = json.load(open(os.path.join(BANC, "ch_1", "manifest.json"), encoding="utf-8"))
check("page retiree du dossier", r.get("ok") and not os.path.exists(os.path.join(BANC, "ch_1", f0)), r)
check("page retiree du manifeste", [p["file"] for p in m2["pages"]] == [p["file"] for p in man["pages"][1:]])
check("page gardee dans la corbeille", os.path.isfile(os.path.join(SRC, r.get("corbeille", "x"), f0)))
check("note ajoutee au manifeste", any("supprimee" in n for n in m2.get("notes", [])))
corbeille_nettoie(r.get("corbeille"))

print("=== refus")
for nom, body in (("page inconnue", {"d": "banc-bib/ch_1", "pages": ["page_999.png"]}),
                  ("remontee ..", {"d": "../ch_1"}), ("serie avec /", {"slug": "banc-bib/ch_1"}),
                  ("chemin absolu", {"d": "C:/Windows"}), ("vide", {}),
                  ("page avec chemin", {"d": "banc-bib/ch_1", "pages": ["../manifest.json"]})):
    r = api("/manga/source_delete", body)
    check("refuse : " + nom, "error" in r and os.path.isdir(os.path.join(BANC, "ch_1")), r.get("error"))
pr = os.path.join(BANC, "ch_1", "narration", "t", "progress.json")
os.makedirs(os.path.dirname(pr))
json.dump({"etape": "vision", "t": time.time()}, open(pr, "w"))
r = api("/manga/source_delete", {"d": "banc-bib/ch_1"})
check("refuse : narration en cours", "narration" in (r.get("error") or "") and os.path.isdir(os.path.join(BANC, "ch_1")), r)
shutil.rmtree(os.path.join(BANC, "ch_1", "narration"))

print("=== suppression d'un CHAPITRE puis d'une SERIE")
r = api("/manga/source_delete", {"d": "banc-bib/ch_1"})
check("chapitre deplace en corbeille", r.get("ok") and not os.path.exists(os.path.join(BANC, "ch_1"))
      and os.path.isdir(os.path.join(SRC, r.get("corbeille", "x"))), r)
check("chapitre absent de la liste", not any(i["dir"] == "banc-bib/ch_1" for i in api("/manga/sources")["items"]))
corbeille_nettoie(r.get("corbeille"))
fabrique()
r = api("/manga/source_delete", {"slug": "banc-bib"})
check("serie deplacee en corbeille", r.get("ok") and not os.path.exists(BANC), r)
corbeille_nettoie(r.get("corbeille"))
check("corbeille ignoree par la liste", not any(i["dir"].startswith("_") for i in api("/manga/sources")["items"]))
check("vrais chapitres intacts", all(os.path.isdir(os.path.join(SRC, d)) for d in
      ("claymore/ch_1", "one-punch-man/ch_300", "one-punch-man/ch_301", "boruto-tow-blue-vortex/ch_1")))

shutil.rmtree(BANC, ignore_errors=True)
print("\n=== VERDICT : %d/%d" % (len(OK), len(OK) + len(KO)) + ("" if not KO else "  ECHECS : " + ", ".join(KO)))
sys.exit(1 if KO else 0)
