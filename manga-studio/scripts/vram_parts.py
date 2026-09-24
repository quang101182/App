# -*- coding: utf-8 -*-
"""La jauge VRAM VENTILEE par moteur (Manga Studio v2.13.0, demande Quang 24/09 15h11). v1.0.0

Quang : « des couleurs afin de distinguer quel moteur occupe quelle quantite de [V]RAM. Le gris represente le systeme,
et les couleurs l'application. »

- Le TOTAL fait autorite : nvidia-smi (memoire utilisee / totale de la carte).
- Chaque moteur DECLARE sa part (Windows ne ventile pas la VRAM par processus, cf. declaration_gpu.py) :
    ComfyUI (dessin, :8188)          -> /system_stats (memoire tenue par PyTorch)
    moteur musique Generate Studio   -> :8388/vram (torch_reserved_mo)
    Ollama (analyse locale, :11434)  -> /api/ps (size_vram de chaque modele charge)
    nos scripts (voix locale, traduction/effacement, cases) -> sources/_gpu/<pid>.json (battement < 15 s, PID vivant)
- Le GRIS = tout le reste : Windows, navigateurs, jeux… et la surcharge propre a chaque moteur (contexte CUDA, qu'aucun
  moteur ne compte). Il est calcule, jamais devine : total - somme des parts, jamais negatif.
Cache 4 s (l'app interroge souvent). Charge a chaud par le proxy (GET /manga/vram).
"""
import glob, json, os, subprocess, time, urllib.request

VERSION = "1.0.0"
HERE = os.path.dirname(os.path.abspath(__file__))
GPU_DIR = os.path.normpath(os.path.join(HERE, "..", "sources", "_gpu"))
CREATE = getattr(subprocess, "CREATE_NO_WINDOW", 0)
FRAIS_S = 15
# cle -> libelle ; l'ordre est celui des segments dans la barre (les couleurs sont dans l'app)
MOTEURS = [("comfyui", "ComfyUI (dessin)"), ("voix", "Voix locale"), ("traduction", "Traduction · effacement"),
           ("cases", "Découpage des cases"), ("ollama", "Analyse locale (Ollama)"), ("musique", "Musique (Generate Studio)"),
           ("autre", "Autre moteur")]
_CACHE = {"t": 0, "r": None}


def _json(url, timeout=1.5):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode() or "{}")
    except Exception:
        return None


def _pid_vivant(pid):
    try:
        out = subprocess.run(["tasklist", "/FI", "PID eq %d" % int(pid), "/NH"], capture_output=True, text=True,
                             creationflags=CREATE, timeout=8).stdout
        return str(int(pid)) in out
    except Exception:
        return False


def mesurer():
    r = {"version": VERSION, "total": None, "used": None, "parts": {}, "detail": [], "t": time.time()}
    try:
        o = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, timeout=8, creationflags=CREATE).stdout
        u, t = [int(x.strip()) for x in o.splitlines()[0].split(",")]
        r.update(used=u, total=t)
    except Exception as e:
        r["erreur"] = "nvidia-smi : %s" % str(e)[:80]
        return r
    parts = {}
    # les 3 moteurs en PARALLELE : sous Windows un port ferme fait attendre ~1 s chacun (mesure : 3,3 s en serie)
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(3) as ex:
        s, y, o = ex.map(_json, ["http://127.0.0.1:8188/system_stats", "http://127.0.0.1:8388/vram",
                                 "http://127.0.0.1:11434/api/ps"])
    if s:
        d = (s.get("devices") or [{}])[0]
        mo = max(0, int(d.get("torch_vram_total", 0)) - int(d.get("torch_vram_free", 0))) // (1024 * 1024)
        if mo:
            parts["comfyui"] = mo
    if y and y.get("torch_reserved_mo"):
        parts["musique"] = int(y["torch_reserved_mo"])
    if o:
        mo = sum(int(m.get("size_vram") or 0) for m in o.get("models") or []) // (1024 * 1024)
        if mo:
            parts["ollama"] = mo
            r["detail"] += [{"cle": "ollama", "quoi": m.get("name"), "mo": int(m.get("size_vram") or 0) // (1024 * 1024)}
                            for m in o.get("models") or []]
    for f in glob.glob(os.path.join(GPU_DIR, "*.json")):
        try:
            with open(f, encoding="utf-8") as h:
                x = json.load(h)
        except Exception:
            continue
        if time.time() - float(x.get("t") or 0) > FRAIS_S or not _pid_vivant(x.get("pid")):
            if time.time() - float(x.get("t") or 0) > 60:  # orphelin (processus tue sans pouvoir s'effacer) : on range
                try: os.remove(f)
                except OSError: pass
            continue                                   # battement perime ou processus mort : il ne compte plus
        cle = x.get("nom") if x.get("nom") in dict(MOTEURS) else "autre"
        if int(x.get("mo") or 0):
            parts[cle] = parts.get(cle, 0) + int(x["mo"])
            r["detail"].append({"cle": cle, "quoi": "PID %s" % x.get("pid"), "mo": int(x["mo"])})
    somme = sum(parts.values())
    if somme > r["used"]:                               # des declarations plus grosses que la carte : on les ramene
        k = r["used"] / float(somme)
        parts = {c: int(v * k) for c, v in parts.items()}
        r["reduit"] = True
    r["parts"] = [{"cle": c, "nom": n, "mo": parts[c]} for c, n in MOTEURS if parts.get(c)]
    r["systeme"] = max(0, r["used"] - sum(parts.values()))
    return r


def lire():
    if _CACHE["r"] is None or time.time() - _CACHE["t"] > 4:
        _CACHE.update(t=time.time(), r=mesurer())
    return _CACHE["r"]


if __name__ == "__main__":
    print(json.dumps(mesurer(), ensure_ascii=False, indent=1))
