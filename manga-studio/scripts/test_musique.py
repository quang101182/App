# -*- coding: utf-8 -*-
"""Banc des routes MUSIQUE du proxy (v1.90.0) sur une serie JETABLE sources/banc-mus/ (effacee a la fin, ainsi que
ce que le banc a mis a la corbeille). Ne touche a aucune vraie serie.
v1.90 : noms « Titre N » (jamais un numero supprime reutilise), selection de la serie (5 max), selection propre
d'un chapitre, « enlever d'un chapitre » != « supprimer de la base ».
Usage : python test_musique.py <fichier audio> [port]   (8191 = copie patchee de test, 8190 = proxy reel)
"""
import base64, json, os, shutil, sys, urllib.error, urllib.request

AUDIO = sys.argv[1]
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8191
BASE = "http://127.0.0.1:%d" % PORT
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
SRC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sources"))
BANC = os.path.join(SRC, "banc-mus")
OK, KO = [], []


def api(path, body=None, raw=False, headers=None):
    h = {"Authorization": "Bearer " + KEY, "Content-Type": "application/json"}
    h.update(headers or {})
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode() if body is not None else None, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, (r.read() if raw else json.load(r))
    except urllib.error.HTTPError as e:
        return e.code, {}


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


def importe():
    return api("/manga/musique_import", {"serie": "banc-mus", "nom": "n'importe quoi [moteur1].mp3", "data": b64})[1]


shutil.rmtree(BANC, ignore_errors=True)
for ch in ("ch_1", "ch_2"):
    os.makedirs(os.path.join(BANC, ch))
    json.dump({"slug": "banc-mus", "title": "Banc Mus", "chapter": ch[3:], "pages": []},
              open(os.path.join(BANC, ch, "manifest.json"), "w", encoding="utf-8"))
corb_avant = set(os.listdir(os.path.join(SRC, "_corbeille"))) if os.path.isdir(os.path.join(SRC, "_corbeille")) else set()
b64 = base64.b64encode(open(AUDIO, "rb").read()).decode()
try:
    s, r = api("/manga/musiques?serie=banc-mus")
    check("serie sans musique -> vide", s == 200 and r["items"] == [] and r["effectif"] == [], r)
    n1, n2 = importe().get("nom"), importe().get("nom")
    check("import -> nom du MANGA numerote (le nom du fichier est ignore)", (n1, n2) == ("Banc Mus 1", "Banc Mus 2"), (n1, n2))
    s, r = api("/manga/musiques?serie=banc-mus&d=banc-mus/ch_1")
    check("les importes rejoignent la selection de la serie", r["serie_sel"] == ["Banc Mus 1", "Banc Mus 2"], r["serie_sel"])
    check("un chapitre suit la serie par defaut", r["chapitre"]["mode"] == "serie" and r["effectif"] == r["serie_sel"], r.get("chapitre"))
    check("duree mesuree", r["items"][0]["dur"] > 10, r["items"][0]["dur"])
    f = r["items"][0]["fichier"]
    s, bb = api("/manga/source_file?p=" + urllib.request.quote(f), raw=True, headers={"Range": "bytes=1000-1999"})
    check("fichier servi avec Range (206)", s == 206 and len(bb) == 1000, (s, len(bb)))
    # numerotation : supprimer le PLUS GRAND numero ne le fait pas renaitre
    api("/manga/musique_suppr", {"serie": "banc-mus", "nom": "Banc Mus 2"})
    n3 = importe().get("nom")
    check("« Banc Mus 2 » supprime -> le suivant est 3, jamais un 2 reutilise", n3 == "Banc Mus 3", n3)
    for _ in range(4):
        importe()
    s, r = api("/manga/musiques?serie=banc-mus")
    check("la selection de la serie s'arrete a 5", len(r["serie_sel"]) == 5 and len(r["items"]) == 6, (r["serie_sel"], len(r["items"])))
    s, r = api("/manga/musique_selection", {"serie": "banc-mus", "noms": [x["nom"] for x in r["items"]]})
    check("6 morceaux dans une selection -> refuse", "au plus" in (r.get("error") or ""), r)
    # chapitre 2 : sa propre selection
    s, r = api("/manga/musique_selection", {"serie": "banc-mus", "d": "banc-mus/ch_2", "mode": "propre", "noms": ["Banc Mus 3", "Banc Mus 1"]})
    check("chapitre 2 : selection propre", r.get("effectif") == ["Banc Mus 3", "Banc Mus 1"] and r["chapitre"]["mode"] == "propre", r.get("effectif"))
    s, r = api("/manga/musiques?serie=banc-mus&d=banc-mus/ch_1")
    check("chapitre 1 n'est pas touche (suit toujours la serie)", r["chapitre"]["mode"] == "serie" and r["effectif"] == r["serie_sel"], r["effectif"])
    # ENLEVER d'un chapitre (decocher) : le fichier reste dans la base
    s, r = api("/manga/musique_selection", {"serie": "banc-mus", "d": "banc-mus/ch_2", "mode": "propre", "noms": ["Banc Mus 1"]})
    s, r = api("/manga/musiques?serie=banc-mus&d=banc-mus/ch_2")
    check("enlever du chapitre : retire de SA selection, le fichier reste", r["effectif"] == ["Banc Mus 1"]
          and any(x["nom"] == "Banc Mus 3" for x in r["items"]), r["effectif"])
    # SUPPRIMER de la base : partout
    api("/manga/musique_selection", {"serie": "banc-mus", "d": "banc-mus/ch_2", "mode": "propre", "noms": ["Banc Mus 1", "Banc Mus 3"]})
    s, r = api("/manga/musique_suppr", {"serie": "banc-mus", "nom": "Banc Mus 1"})
    check("supprimer de la base -> corbeille", r.get("ok") and os.path.isfile(os.path.join(SRC, r.get("corbeille", ""))), r)
    s, r2 = api("/manga/musiques?serie=banc-mus&d=banc-mus/ch_2")
    check("... retire de la serie ET des chapitres", "Banc Mus 1" not in r2["serie_sel"] and r2["effectif"] == ["Banc Mus 3"]
          and all(x["nom"] != "Banc Mus 1" for x in r2["items"]), (r2["serie_sel"], r2["effectif"]))
    # retour a la serie
    s, r = api("/manga/musique_selection", {"serie": "banc-mus", "d": "banc-mus/ch_2", "mode": "serie", "noms": []})
    check("chapitre 2 revient a « celle de la serie »", r["effectif"] == r["serie_sel"], r["effectif"])
    # l'ancien format (v1.85) est relu
    json.dump({"nom": "Banc Mus 3"}, open(os.path.join(BANC, "musique", "choix.json"), "w", encoding="utf-8"))
    s, r = api("/manga/musiques?serie=banc-mus")
    check("ancien choix.json {nom} relu comme selection", r["serie_sel"] == ["Banc Mus 3"], r["serie_sel"])
    check("... et le numero suivant reste au-dela des existants", importe().get("nom") == "Banc Mus 8")
    s, r = api("/manga/musique_selection", {"serie": "banc-mus", "d": "claymore/ch_1", "noms": []})
    check("chapitre d'une AUTRE serie refuse", r.get("error") == "chapitre introuvable", r)
    s, r = api("/manga/musique_import", {"serie": "banc-mus", "nom": "faux.mp3", "data": base64.b64encode(b"x" * 20000).decode()})
    check("un faux fichier est refuse", "audio" in (r.get("error") or ""), r)
    s, r = api("/manga/musique_import", {"serie": "../banc-mus", "nom": "a.mp3", "data": b64})
    check("serie '../' refusee", r.get("error") == "serie introuvable", r)
    s, r = api("/manga/musiques?serie=nexiste-pas")
    check("serie inexistante -> 404", s == 404, s)
finally:
    shutil.rmtree(BANC, ignore_errors=True)
    cb = os.path.join(SRC, "_corbeille")
    for x in (set(os.listdir(cb)) - corb_avant) if os.path.isdir(cb) else ():
        if "banc-mus" in x:
            pth = os.path.join(cb, x)
            shutil.rmtree(pth) if os.path.isdir(pth) else os.remove(pth)
print("\n=== VERDICT : %d/%d" % (len(OK), len(OK) + len(KO)) + ("" if not KO else "  ECHECS : " + ", ".join(KO)))
sys.exit(1 if KO else 0)
