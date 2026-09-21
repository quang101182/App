# -*- coding: utf-8 -*-
"""Banc des routes MUSIQUE du proxy (v1.85.0) sur une serie JETABLE sources/banc-mus/ (effacee a la fin,
ainsi que ce que le banc a mis a la corbeille). Ne touche a aucune vraie serie.
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


shutil.rmtree(BANC, ignore_errors=True)
os.makedirs(os.path.join(BANC, "ch_1"))
corb_avant = set(os.listdir(os.path.join(SRC, "_corbeille"))) if os.path.isdir(os.path.join(SRC, "_corbeille")) else set()
b64 = base64.b64encode(open(AUDIO, "rb").read()).decode()
try:
    s, r = api("/manga/musiques?serie=banc-mus")
    check("serie sans musique -> liste vide", s == 200 and r == {"items": [], "choix": ""}, r)
    s, r = api("/manga/musique_import", {"serie": "banc-mus", "nom": "Thème [moteur1].mp3", "data": b64})
    check("import -> nom nettoye (accents, crochets)", r.get("nom") == "Theme moteur1", r)
    s, r = api("/manga/musique_import", {"serie": "banc-mus", "nom": "Thème [moteur1].mp3", "data": b64})
    check("import du meme nom -> suffixe (2), rien d'ecrase", r.get("nom") == "Theme moteur1 (2)", r)
    s, r = api("/manga/musiques?serie=banc-mus")
    check("2 morceaux listes", len(r.get("items", [])) == 2, [x["nom"] for x in r.get("items", [])])
    check("le 1er importe est celui qui joue", r.get("choix") == "Theme moteur1", r.get("choix"))
    f = r["items"][0]["fichier"]
    s, bb = api("/manga/source_file?p=" + urllib.request.quote(f), raw=True, headers={"Range": "bytes=1000-1999"})
    check("fichier servi avec Range (206, 1000 octets)", s == 206 and len(bb) == 1000, (s, len(bb)))
    s, r = api("/manga/musique_choix", {"serie": "banc-mus", "nom": "Theme moteur1 (2)"})
    s, r = api("/manga/musiques?serie=banc-mus")
    check("choix change", r.get("choix") == "Theme moteur1 (2)", r.get("choix"))
    s, r = api("/manga/musique_choix", {"serie": "banc-mus", "nom": "inexistant"})
    check("choix d'un morceau inexistant refuse", r.get("error") == "morceau introuvable", r)
    s, r = api("/manga/musique_suppr", {"serie": "banc-mus", "nom": "Theme moteur1 (2)"})
    check("suppression -> corbeille", r.get("ok") and "_corbeille" in r.get("corbeille", "").replace("\\", "/")
          or r.get("ok") and os.path.isfile(os.path.join(SRC, r.get("corbeille", ""))), r)
    s, r = api("/manga/musiques?serie=banc-mus")
    check("supprime celui qui jouait -> plus aucun choix", r.get("choix") == "" and len(r["items"]) == 1, r)
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
            p = os.path.join(cb, x)
            shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
print("\n=== VERDICT : %d/%d" % (len(OK), len(OK) + len(KO)) + ("" if not KO else "  ECHECS : " + ", ".join(KO)))
sys.exit(1 if KO else 0)
