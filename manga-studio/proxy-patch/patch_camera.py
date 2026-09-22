# -*- coding: utf-8 -*-
"""Patch du proxy 8190 : camera « case par case » (Manga Studio v2.5.0, 23/09/2026).

Decision Quang (22/09 23h58, puis 23/09 00h08) : la video passe de case en case, mode PAR DEFAUT pour tous les
formats ; « page entiere » (le zoom lent d'avant) reste au choix, par serie ou en defaut general. Le LECTEUR de l'app
fait la meme chose (reponse de Quang le 23/09 : « oui, lecteur aussi »).

- reglage video « camera » (« cases » | « page ») garde dans la liste blanche de /manga/video ; absent = « page »
  (une ancienne version de l'app n'envoie rien : on ne change pas ce qu'elle a demande) ;
- nom de fichier lisible : « cases » en plus ;
- GET  /manga/cases?d=<serie/ch_N> : les cases deja detectees (cache sources/<chap>/cases.json) + la camera de la
  serie ; s'il en manque, lance la detection (cases_video.py, avec le Python de Manga Studio, qui a YOLO) et repond
  « calcul » : le lecteur montre la page entiere en attendant et redemande ;
- POST /manga/camera {serie, camera} : le choix du lecteur devient celui de la serie (profil suivi.json).
Rejouable : python patch_camera.py <chemin du proxy>.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "# v2.5.0 : camera" in s:
    print("deja patche")
    sys.exit(0)


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


rep('''              "precedemment": bool(reg.get("precedemment"))}                         # v1.95.1''',
    '''              "precedemment": bool(reg.get("precedemment")),                         # v1.95.1
              "camera": "cases" if reg.get("camera") == "cases" else "page"}         # v2.5.0 : camera''')
rep('''    if r.get("precedemment"):
        morceaux.append("précédemment")''',
    '''    if r.get("precedemment"):
        morceaux.append("précédemment")
    if r.get("camera") == "cases":                                                   # v2.5.0
        morceaux.append("cases")''')
rep('''    return {"chapitres": chaps}


def manga_video_ajoute(data):''',
    '''    return {"chapitres": chaps, "camera": _camera_serie(serie)}                     # v2.5.0 : camera


def manga_video_ajoute(data):''')
rep('''# --- « Precedemment... » et rattrapage (Manga Studio v1.94.0) ---------------------------''',
    '''# --- Camera « case par case » (Manga Studio v2.5.0) ------------------------------------
MANGA_CASES = os.path.join(MANGA_ROOT, "scripts", "cases_video.py")
_CASES_MOD = {"m": None, "t": 0}
_CASES_JOBS, _CASES_ECHEC = {}, {}


def _cases_mod():
    """cases_video.py charge a la volee (etat() ne fait que LIRE le cache : ni YOLO ni torch dans le proxy)."""
    t = os.path.getmtime(MANGA_CASES)
    if _CASES_MOD["m"] is None or _CASES_MOD["t"] != t:
        import importlib.util
        sp = importlib.util.spec_from_file_location("manga_cases_video", MANGA_CASES)
        m = importlib.util.module_from_spec(sp)
        sp.loader.exec_module(m)
        _CASES_MOD.update(m=m, t=t)
    return _CASES_MOD["m"]


def _camera_serie(serie):
    try:
        return _suivi_mod().profil(serie)[0]["reglages_video"].get("camera") or "cases"
    except Exception:
        return "cases"


def manga_cases(d):
    d = (d or "").strip("/")
    base = _manga_src_safe(d)
    if not base or not os.path.isfile(os.path.join(base, "manifest.json")):
        return None
    e = _cases_mod().etat(d)
    if e is None:
        return None
    job = _CASES_JOBS.get(d)
    vivant = bool(job and job.poll() is None)
    if job and not vivant and job.returncode:
        _CASES_ECHEC[d] = time.time()
        _CASES_JOBS.pop(d, None)
    # une detection qui plante n'est pas relancee en boucle : 10 min de repos
    if e["manquantes"] and not vivant and time.time() - _CASES_ECHEC.get(d, 0) > 600:
        lg_dir = os.path.join(MANGA_SOURCES, "_suivi")
        os.makedirs(lg_dir, exist_ok=True)
        lg = open(os.path.join(lg_dir, "cases.log"), "a", encoding="utf-8")
        _CASES_JOBS[d] = subprocess.Popen([MANGA_PY, MANGA_CASES, d], stdout=lg, stderr=lg, cwd=os.path.dirname(MANGA_CASES),
                                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                                          env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        vivant = True
    e.update(camera=_camera_serie(d.split("/")[0]), calcul=vivant,
             echec=bool(e["manquantes"] and not vivant and d in _CASES_ECHEC))
    return e


def manga_camera(data):
    serie, cam = data.get("serie") or "", data.get("camera")
    sd = _manga_src_safe(serie) if _RE_SERIE.match(serie) else None
    if not sd or not os.path.isdir(sd):
        return {"error": "serie introuvable"}
    if cam not in ("cases", "page"):
        return {"error": "camera invalide"}
    m = _suivi_mod()
    cfg = m.profil(serie)[0]
    cfg["reglages_video"]["camera"] = cam
    cfg = m.normaliser(cfg)
    cfg["maj"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    tmp = os.path.join(sd, "suivi.json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=1)
    os.replace(tmp, os.path.join(sd, "suivi.json"))
    return {"ok": True, "camera": cam}


# --- « Precedemment... » et rattrapage (Manga Studio v1.94.0) ---------------------------''')
rep('''        elif self.path.split("?", 1)[0] == "/manga/profil_defaut":         # Manga Studio v2.4.0''',
    '''        elif self.path.split("?", 1)[0] == "/manga/cases":                 # Manga Studio v2.5.0
            _r = manga_cases((parse_qs(urlparse(self.path).query).get("d") or [""])[0])
            if _r is None: self._json(404, {"error": "chapitre introuvable"})
            else: self._json(200, _r)
        elif self.path.split("?", 1)[0] == "/manga/profil_defaut":         # Manga Studio v2.4.0''')
rep('''            elif self.path == "/manga/profil_defaut":          # Manga Studio v2.4.0''',
    '''            elif self.path == "/manga/camera":                 # Manga Studio v2.5.0
                self._json(200, manga_camera(data))
            elif self.path == "/manga/profil_defaut":          # Manga Studio v2.4.0''')
open(p, "w", encoding="utf-8").write(s)
print("patche")
