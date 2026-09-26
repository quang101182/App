# -*- coding: utf-8 -*-
"""ATELIER de l'essai « une voix par personnage » (hors app, 26/09/2026, Quang 22h41 : « je peux choisir la voix, le ton,
cliquer sur Play pour ecouter au moins une phrase […] ce seraient mes reglages » ; 22h42 : vitesse de diction PAR personnage).

Petit serveur LOCAL (127.0.0.1 seulement) : la page et l'API sur la meme origine, le secret du gateway reste ici (jamais
dans la page). Il ne touche QUE <chapitre>/essai_voix/ (reglages.json, apercus/) et lance essai_voix_personnages.py.

Usage : python essai_voix_atelier.py one-punch-man/ch_6 --pages 5-7    -> http://127.0.0.1:8196/
"""
import argparse, base64, hashlib, json, os, subprocess, sys, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import narrate_chapter as nc
import essai_voix_personnages as ev

VERSION = "0.2.0"   # 0.2.0 : ton vide garde vide (etait remplace par celui de l'IA) ; interrupteur « tons »
PAGE = os.path.join(HERE, "essai_voix_atelier.html")
A = None
VERROU = threading.Lock()
GEN = {"etat": "repos", "log": "", "stats": None}


def dossier():
    return os.path.join(ev.SOURCES, A.chap.replace("/", os.sep), "essai_voix")


def etat():
    chap_dir = os.path.join(ev.SOURCES, A.chap.replace("/", os.sep))
    dist = json.load(open(os.path.join(dossier(), "distribution.json"), encoding="utf-8"))
    reg = ev.reglages(dossier())
    t = json.load(open(os.path.join(chap_dir, "traduction", "fr", "traduction.json"), encoding="utf-8"))
    rep = {(r["page"], r["id"]): r for r in dist["repliques"]}
    voulues = set(ev.plage(A.pages))
    lignes = []
    for p in t["pages"]:
        if p["page"] not in voulues:
            continue
        for b in sorted([b for b in p["bulles"] if b["type"] in ("dialogue", "narration") and not b.get("ecarte")
                         and (b.get("trad") or "").strip()], key=lambda b: b["id"]):
            r = dict(rep.get((p["page"], b["id"])) or {"locuteur": "inconnu", "ton": "neutre"})
            cle = "%d-%d" % (p["page"], b["id"])
            r.update({k: v for k, v in ((reg.get("repliques") or {}).get(cle) or {}).items()
                      if v is not None and (v != "" or k == "ton")})
            lignes.append({"cle": cle, "page": p["page"], "id": b["id"], "texte": b["trad"], "locuteur": r.get("locuteur"),
                           "ton": r.get("ton") or "", "lire": r.get("lire") is not False, "muet": bool(r.get("muet")),
                           "indice": r.get("indice") or ""})
    persos = []
    noms = [c["nom"] for c in dist["distribution"]] + ["narrateur"]
    for nom in noms:
        c = next((x for x in dist["distribution"] if x["nom"] == nom), {"nom": nom, "voix": "Charon", "genre": "?"})
        o = (reg.get("persos") or {}).get(nom) or {}
        persos.append({"nom": nom, "genre": c.get("genre", "?"), "fiche": c.get("fiche", ""),
                       "voix": o.get("voix") or c.get("voix"), "caractere": o.get("caractere", ""),
                       "intensite": o.get("intensite", ev.INTENSITE_DEFAUT), "vitesse": o.get("vitesse"),
                       "renomme": o.get("renomme", "")})
    video = os.path.join(dossier(), "essai.mp4")
    return {"version": VERSION, "chap": A.chap, "pages": A.pages, "ambiance": dist.get("ambiance", ""),
            "persos": persos, "lignes": lignes, "vitesse": reg.get("vitesse") or 1.5, "tons": reg.get("tons") is not False,
            "voix": ev.VOIX, "intensite": ev.INTENSITE, "gen": GEN,
            "video_t": os.path.getmtime(video) if os.path.isfile(video) else 0}


def ecouter(d):
    cons = ev.consigne(d.get("ton") if d.get("tons", True) else "", d.get("caractere", ""), d.get("intensite", ev.INTENSITE_DEFAUT))
    vit = float(d.get("vitesse") or 1.5)
    texte = ev.texte_lu(d.get("texte") or "")
    cle = hashlib.sha1(json.dumps([texte, d.get("voix"), cons, vit]).encode()).hexdigest()[:16]
    os.makedirs(os.path.join(dossier(), "apercus"), exist_ok=True)
    f = os.path.join(dossier(), "apercus", cle + ".mp3")
    if not os.path.isfile(f):
        ev.dire(texte, d.get("voix"), cons, f, {}, vit)
    return open(f, "rb").read(), cons or "(aucune consigne : la voix lit le texte)"


def generer():
    GEN.update(etat="en cours", log="", stats=None)
    try:
        r = subprocess.run([sys.executable, os.path.join(HERE, "essai_voix_personnages.py"), A.chap, "--pages", A.pages],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        GEN["log"] = (r.stdout + r.stderr)[-4000:]
        ok = r.returncode == 0
        if ok:
            GEN["stats"] = json.load(open(os.path.join(dossier(), "cout.json"), encoding="utf-8"))["stats"]
        GEN["etat"] = "fini" if ok else "echec"
    except Exception as e:
        GEN.update(etat="echec", log=str(e))


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _envoi(self, code, corps, ctype="application/json; charset=utf-8", extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(corps)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(corps)

    def _json(self, o, code=200):
        self._envoi(code, json.dumps(o, ensure_ascii=False).encode())

    def do_GET(self):
        chemin = self.path.split("?")[0]
        try:
            if chemin == "/":
                return self._envoi(200, open(PAGE, "rb").read(), "text/html; charset=utf-8")
            if chemin == "/etat":
                return self._json(etat())
            if chemin == "/video":
                f = os.path.join(dossier(), "essai.mp4")
                data = open(f, "rb").read()
                rg = self.headers.get("Range")
                if rg and rg.startswith("bytes="):
                    a_, _, b_ = rg[6:].partition("-")
                    a_ = int(a_ or 0); b_ = int(b_) if b_ else len(data) - 1
                    return self._envoi(206, data[a_:b_ + 1], "video/mp4",
                                       {"Content-Range": "bytes %d-%d/%d" % (a_, b_, len(data)), "Accept-Ranges": "bytes"})
                return self._envoi(200, data, "video/mp4", {"Accept-Ranges": "bytes"})
            self._json({"erreur": "introuvable"}, 404)
        except Exception as e:
            self._json({"erreur": str(e)[:300]}, 500)

    def do_POST(self):
        chemin = self.path.split("?")[0]
        try:
            d = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
            if chemin == "/ecouter":
                mp3, cons = ecouter(d)
                return self._envoi(200, mp3, "audio/mpeg", {"X-Consigne": base64.b64encode(cons.encode()).decode()})
            if chemin == "/reglages":
                with VERROU:
                    json.dump({"vitesse": d.get("vitesse"), "tons": d.get("tons", True), "persos": d.get("persos") or {}, "repliques": d.get("repliques") or {}},
                              open(os.path.join(dossier(), "reglages.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
                return self._json({"ok": True})
            if chemin == "/generer":
                if GEN["etat"] == "en cours":
                    return self._json({"erreur": "generation deja en cours"}, 409)
                threading.Thread(target=generer, daemon=True).start()
                return self._json({"ok": True})
            self._json({"erreur": "introuvable"}, 404)
        except Exception as e:
            self._json({"erreur": str(e)[:300]}, 500)


def main():
    global A
    p = argparse.ArgumentParser()
    p.add_argument("chap"); p.add_argument("--pages", default="5-7"); p.add_argument("--port", type=int, default=8196)
    A = p.parse_args()
    nc._sorties_utf8()
    nc.SECRET = nc._secret()
    if not os.path.isfile(os.path.join(dossier(), "distribution.json")):
        raise SystemExit("lancer d'abord essai_voix_personnages.py %s --pages %s" % (A.chap, A.pages))
    print("atelier v%s -> http://127.0.0.1:%d/  (%s p.%s, PID %d)" % (VERSION, A.port, A.chap, A.pages, os.getpid()), flush=True)
    ThreadingHTTPServer(("127.0.0.1", A.port), H).serve_forever()


if __name__ == "__main__":
    main()
