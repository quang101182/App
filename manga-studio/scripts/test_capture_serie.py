# -*- coding: utf-8 -*-
"""Banc de la CAPTURE DE PLUSIEURS CHAPITRES (Manga Studio v2.3.0, etape 18 ; manga-fetch v0.4.0).

Usage : python test_capture_serie.py [port]   (8191 = copie patchee de test, 8190 = proxy reel)
Ouvre un onglet JETABLE dans la fenetre de capture (CDP 9223), capture OPM (MangaDex) sous le titre
« banc serie » -- dossier sources/banc-serie/, efface a la fin, comme l'onglet. Ne touche a aucun vrai chapitre.
1) saisies refusees (suite hors bornes, « jusqu'au » avant le depart) -- rien n'est lance ;
2) --suite 1 depuis le ch. 305 : 2 chapitres, le statut suit le chapitre EN COURS, bilan « SERIE » ;
3) --jusqua 308 depuis le ch. 307 : 2 chapitres, contenus distincts, numeros confirmes par l'API MangaDex.
"""
import glob, hashlib, json, os, shutil, sys, time, urllib.request

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8191
BASE = "http://127.0.0.1:%d" % PORT
CDP = "http://127.0.0.1:9223"
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
SRC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sources"))
BANC = os.path.join(SRC, "banc-serie")
OPM_301 = "30f3755a-7dcf-4594-964d-58e2c9e93716"      # OPM ch.301 (vi) : point d'entree dans la serie
OK, KO = [], []


def api(path, body=None):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def mdx(path):
    req = urllib.request.Request("https://api.mangadex.org" + path, headers={"User-Agent": "manga-studio-banc/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def verifie(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  OK  " if cond else "  KO  ") + nom + (("  -- " + str(detail)) if detail else ""), flush=True)


def uuid_chapitre(num):
    info = mdx("/chapter/" + OPM_301)["data"]
    manga = next(r["id"] for r in info["relationships"] if r["type"] == "manga")
    agg = mdx("/manga/%s/aggregate?translatedLanguage[]=%s" % (manga, info["attributes"]["translatedLanguage"]))
    for vol in agg["volumes"].values():
        if str(num) in vol["chapters"]:
            return vol["chapters"][str(num)]["id"]
    raise SystemExit("chapitre %s introuvable sur MangaDex" % num)


def ouvre_onglet(url):
    req = urllib.request.Request(CDP + "/json/new?" + url, method="PUT")
    with urllib.request.urlopen(req, timeout=10) as r:
        t = json.load(r)
    time.sleep(8)
    return t["id"]


def ferme_onglet(oid):
    try:
        urllib.request.urlopen(CDP + "/json/close/" + oid, timeout=5).read()
    except Exception:
        pass


def attend_fin(limite=900):
    vus, t0, s = set(), time.time(), {}
    while time.time() - t0 < limite:
        s = api("/manga/fetch_status")
        if s.get("etat") == "en cours":
            vus.add(str(s.get("chapitre")))
        else:
            return s, vus
        time.sleep(2)
    return s, vus


def serie(tab_url, depart, **opt):
    r = api("/manga/fetch_capture", dict({"tab": tab_url, "title": "banc serie", "chapter": depart}, **opt))
    if r.get("error"):
        return r, None, set()
    s, vus = attend_fin()
    return r, s, vus


def main():
    print("Banc capture en serie -- port %d" % PORT)
    shutil.rmtree(BANC, ignore_errors=True)
    onglets = []
    try:
        # 1) saisies refusees
        u305 = "https://mangadex.org/chapter/" + uuid_chapitre(305)
        onglets.append(ouvre_onglet(u305))
        for nom, opt in (("suite 301 refusee", {"suite": 301}), ("suite -1 refusee", {"suite": -1}),
                         ("jusqu'au 305 depuis 305 refuse", {"jusqua": "305"}),
                         ("jusqu'au 'abc' refuse", {"jusqua": "abc"})):
            r = api("/manga/fetch_capture", dict({"tab": u305, "title": "banc serie", "chapter": "305"}, **opt))
            verifie(nom, bool(r.get("error")), r.get("error"))
        verifie("rien lance par les refus", not os.path.isdir(BANC))

        # 2) --suite 1
        r, s, vus = serie(u305, "305", suite=1)
        verifie("suite 1 : lancee", r.get("ok"), r)
        verifie("suite 1 : finie", s and s.get("etat") == "fini", s and s.get("etat"))
        verifie("suite 1 : 2 dossiers", s and s.get("dossiers") == ["banc-serie/ch_305", "banc-serie/ch_306"],
                s and s.get("dossiers"))
        verifie("suite 1 : le statut a suivi le ch. 306 en cours", "306" in vus, sorted(vus))
        verifie("suite 1 : bilan SERIE", s and (s.get("serie") or "").startswith("SÉRIE : 2 chapitre(s) : 305, 306"),
                s and s.get("serie"))

        # 3) --jusqua
        u307 = "https://mangadex.org/chapter/" + uuid_chapitre(307)
        onglets.append(ouvre_onglet(u307))
        r, s, vus = serie(u307, "307", jusqua="308")
        verifie("jusqu'au 308 : finie", s and s.get("etat") == "fini", s and s.get("etat"))
        verifie("jusqu'au 308 : 307 et 308", s and s.get("dossiers") == ["banc-serie/ch_307", "banc-serie/ch_308"],
                s and s.get("dossiers"))
        verifie("jusqu'au 308 : arret a la borne", s and "jusqu'au ch. 308 : fait" in (s.get("serie") or ""), s and s.get("serie"))   # texte de manga-fetch 0.7.5

        # contenus : 4 chapitres distincts, numeros confirmes par MangaDex
        empreintes = {}
        for ch in ("305", "306", "307", "308"):
            d = os.path.join(BANC, "ch_" + ch)
            try:
                m = json.load(open(os.path.join(d, "manifest.json"), encoding="utf-8"))
            except OSError:
                verifie("ch.%s : manifeste" % ch, False)
                continue
            cid = m["source_url"].split("/chapter/")[1].split("/")[0]
            num = mdx("/chapter/" + cid)["data"]["attributes"]["chapter"]
            verifie("ch.%s : c'est bien le %s selon MangaDex" % (ch, ch), num == ch, num)
            verifie("ch.%s : >= 10 pages" % ch, len(m["pages"]) >= 10, len(m["pages"]))
            empreintes[ch] = {hashlib.sha1(open(f, "rb").read()).hexdigest()
                              for f in glob.glob(os.path.join(d, "page_*"))}
        # les pages de credits du traducteur reviennent d'un chapitre a l'autre (mesure 22/09 : 2) -> tolerance 3
        for a in empreintes:
            for b in empreintes:
                if a < b:
                    commun = len(empreintes[a] & empreintes[b])
                    verifie("ch.%s / ch.%s : contenus distincts" % (a, b), commun <= 3, "%d image(s) commune(s)" % commun)
    finally:
        for o in onglets:
            ferme_onglet(o)
        shutil.rmtree(BANC, ignore_errors=True)
    print("\nVERDICT : %d/%d" % (len(OK), len(OK) + len(KO)) + ("" if not KO else "  -- KO : " + " ; ".join(KO)))
    return 0 if not KO else 1


if __name__ == "__main__":
    sys.exit(main())
