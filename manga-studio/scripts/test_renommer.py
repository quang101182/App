# -*- coding: utf-8 -*-
"""Banc v2.4.2 : RENOMMER une serie = dossier d'abord, reessais sur verrou Windows (Quang 22/09 16h35-16h39).

Usage : python test_renommer.py [port]   (8191 = copie, 8190 = reel). Serie jetable sources/banc-ren/ (1 chapitre, 3 pages).
1. renommage normal -> dossier + manifeste + serie.json coherents ;
2. un fichier de la serie gardé OUVERT en ecriture exclusive pendant 8 s -> refus clair, RIEN de change (dossier ET titre) ;
3. verrou relache au bout de 2 s -> le renommage REUSSIT grace aux reessais ;
4. la serie renommee se SUPPRIME (corbeille) : plus d'etat incoherent. Tout est nettoye.
"""
import json, os, shutil, sys, threading, time, urllib.request, msvcrt

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8191
BASE = "http://127.0.0.1:%d" % PORT
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
SRC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sources"))
OK, KO = [], []


def api(path, body=None):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""), flush=True)


def titre_de(slug):
    return json.load(open(os.path.join(SRC, slug, "ch_1", "manifest.json"), encoding="utf-8"))


def verrou(chemin, duree):
    """Garde le fichier ouvert SANS partage (comme un lecteur qui le tient) pendant `duree` s."""
    import ctypes
    k32 = ctypes.windll.kernel32
    h = k32.CreateFileW(chemin, 0x80000000, 0, None, 3, 0x80, None)     # GENERIC_READ, share=0, OPEN_EXISTING
    time.sleep(duree)
    k32.CloseHandle(h)


def main():
    for d in ("banc-ren", "banc-ren-2", "banc-ren-3"):
        shutil.rmtree(os.path.join(SRC, d), ignore_errors=True)
    cs, cd = os.path.join(SRC, "one-punch-man", "ch_298"), os.path.join(SRC, "banc-ren", "ch_1")
    os.makedirs(cd)
    man = json.load(open(os.path.join(cs, "manifest.json"), encoding="utf-8"))
    man.update(pages=man["pages"][1:4], chapter="1", slug="banc-ren", title="banc ren")
    for p in man["pages"]:
        shutil.copy(os.path.join(cs, p["file"]), os.path.join(cd, p["file"]))
    json.dump(man, open(os.path.join(cd, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    page = os.path.join(cd, man["pages"][0]["file"])
    try:
        r = api("/manga/serie_renommer", {"slug": "banc-ren", "titre": "banc ren 2"})
        check("renommage normal", r.get("ok") and os.path.isdir(os.path.join(SRC, "banc-ren-2")) and not os.path.isdir(os.path.join(SRC, "banc-ren")), r)
        check("… manifeste cohérent (slug = dossier)", titre_de("banc-ren-2")["slug"] == "banc-ren-2" and titre_de("banc-ren-2")["title"] == "banc ren 2")
        page = os.path.join(SRC, "banc-ren-2", "ch_1", man["pages"][0]["file"])
        th = threading.Thread(target=verrou, args=(page, 9)); th.start(); time.sleep(0.5)
        t0 = time.time()
        r = api("/manga/serie_renommer", {"slug": "banc-ren-2", "titre": "banc ren 3"})
        th.join()
        check("verrou de 9 s : refus clair", "rien n'a été changé" in (r.get("error") or ""), (r, round(time.time() - t0, 1)))
        check("… RIEN de changé (dossier ET titre)", os.path.isdir(os.path.join(SRC, "banc-ren-2")) and titre_de("banc-ren-2")["title"] == "banc ren 2")
        th = threading.Thread(target=verrou, args=(page, 2)); th.start(); time.sleep(0.3)
        r = api("/manga/serie_renommer", {"slug": "banc-ren-2", "titre": "banc ren 3"})
        th.join()
        check("verrou de 2 s : réussi grâce aux réessais", r.get("ok") and os.path.isdir(os.path.join(SRC, "banc-ren-3"))
              and titre_de("banc-ren-3")["slug"] == "banc-ren-3", r)
        r = api("/manga/source_delete", {"slug": "banc-ren-3"})
        check("la série renommée se supprime", r.get("ok") and not os.path.isdir(os.path.join(SRC, "banc-ren-3")), r)
        if r.get("corbeille"):
            shutil.rmtree(os.path.join(SRC, r["corbeille"]), ignore_errors=True)
    finally:
        for d in ("banc-ren", "banc-ren-2", "banc-ren-3"):
            shutil.rmtree(os.path.join(SRC, d), ignore_errors=True)
    print("\nVERDICT : %d/%d" % (len(OK), len(OK) + len(KO)) + ("" if not KO else "  -- KO : " + " ; ".join(KO)))
    return 0 if not KO else 1


if __name__ == "__main__":
    sys.exit(main())
