# -*- coding: utf-8 -*-
"""Patch du proxy 8190 : « Precedemment... » + rattrapage (Manga Studio v1.94.0, 22/09/2026, etape 7).

GET  /manga/precedemment?d=serie/ch_N -> {possible, modes:{ouverture|rattrapage: {etat, perime, raisons, data}}}
POST /manga/precedemment {d, mode, voice} -> lance scripts/precedemment.py EN FOND.
Couts : sources/<serie>/ch_N/precedemment/<mode>.json (stats) -> /manga/costs, poste « precedemment » (corbeille
comprise). Activite : les resumes en cours. La regle « quelles narrations sources » vit dans precedemment.py
(charge a la volee) : aucune copie ici.
Rejouable : python patch_precedemment.py <chemin du proxy>. Suppose patch_video.py applique.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "def manga_precedemment(" in s:
    print("deja patche")
    sys.exit(0)


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


rep('''# --- Karaoke d'une narration (Manga Studio v1.86.0) ------------------------------------''',
    '''# --- « Precedemment... » et rattrapage (Manga Studio v1.94.0) ---------------------------
MANGA_PREC = os.path.join(MANGA_ROOT, "scripts", "precedemment.py")
_PREC_JOBS = {}                                  # (chapitre, mode) -> Popen
_PREC_MOD = {"m": None, "t": 0}
_PREC_MODES = ("ouverture", "rattrapage")


def _prec_mod():
    t = os.path.getmtime(MANGA_PREC)
    if _PREC_MOD["m"] is None or _PREC_MOD["t"] != t:
        import importlib.util
        sp = importlib.util.spec_from_file_location("manga_precedemment", MANGA_PREC)
        m = importlib.util.module_from_spec(sp)
        sys.path.insert(0, os.path.dirname(MANGA_PREC))
        sp.loader.exec_module(m)
        _PREC_MOD.update(m=m, t=t)
    return _PREC_MOD["m"]


def _prec_vivant(d, mode):
    p = _PREC_JOBS.get((d, mode))
    return bool(p and p.poll() is None)


def manga_precedemment(d):
    d = (d or "").strip("/")
    base = _manga_src_safe(d)
    if not base or not os.path.isfile(os.path.join(base, "manifest.json")) or d.count("/") != 1:
        return None
    try:
        with open(os.path.join(base, "manifest.json"), encoding="utf-8") as f:
            num = str(json.load(f).get("chapter") or d.split("/")[1][3:])
        prec = _prec_mod().chapitres_precedents(os.path.dirname(base), num)
    except Exception as e:
        return {"possible": False, "err": str(e)[:200], "modes": {}}
    courant = {x["ch"]: (x["narr"][2], x["narr"][1]) for x in prec if x["narr"]}
    out = {"possible": bool(courant), "precedents": len(prec), "narres": len(courant), "modes": {}}
    pd = os.path.join(base, "precedemment")
    for mode in _PREC_MODES:
        it = {"etat": "aucun"}
        jf, pf = os.path.join(pd, mode + ".json"), os.path.join(pd, mode + ".progress.json")
        if _prec_vivant(d, mode):
            it["etat"] = "en cours"
            try:
                with open(pf, encoding="utf-8") as f: it["progress"] = json.load(f)
            except Exception:
                pass
        elif os.path.isfile(jf):
            try:
                with open(jf, encoding="utf-8") as f: data = json.load(f)
            except Exception:
                data = None
            if data:
                it.update(etat="fini", data=data, base=d + "/precedemment")
                raisons = []
                src = {x.get("ch"): (x.get("tag"), x.get("created_at")) for x in data.get("sources") or []}
                utiles = set(courant) if mode == "rattrapage" else set([x["ch"] for x in prec if x["narr"]][-3:])
                if any(src.get(c) != courant[c] for c in utiles if c in src):
                    raisons.append("une narration d'un chapitre précédent a été refaite")
                if utiles - set(src):
                    raisons.append("un chapitre précédent a été narré depuis")
                if set(src) - set(courant):
                    raisons.append("un chapitre précédent n'a plus de narration")
                it["perime"], it["raisons"] = bool(raisons), raisons
        if it["etat"] == "aucun" and os.path.isfile(os.path.join(pd, mode + ".log")) and not os.path.isfile(jf):
            try:
                with open(os.path.join(pd, mode + ".log"), encoding="utf-8", errors="replace") as f:
                    it.update(etat="echec", err=(f.read().strip().splitlines() or [""])[-1][:300])
            except Exception:
                pass
        out["modes"][mode] = it
    return out


def manga_precedemment_lance(data):
    d, mode = (data.get("d") or "").strip("/"), data.get("mode") or ""
    voix = data.get("voice") or "Charon"
    if mode not in _PREC_MODES or not re.match(r"^[A-Za-z]{2,20}$", voix):
        return {"error": "mode ou voix invalide"}
    info = manga_precedemment(d)
    if info is None:
        return {"error": "chapitre introuvable"}
    if not info.get("possible"):
        return {"error": "aucun chapitre précédent n'est narré"}
    if _prec_vivant(d, mode):
        return {"error": "déjà en cours"}
    if not os.path.isfile(MANGA_PY):
        return {"error": "venv kohya introuvable"}
    pd = os.path.join(_manga_src_safe(d), "precedemment")
    os.makedirs(pd, exist_ok=True)
    lg = open(os.path.join(pd, mode + ".log"), "w", encoding="utf-8")
    _PREC_JOBS[(d, mode)] = subprocess.Popen(
        [MANGA_PY, MANGA_PREC, d, "--mode", mode, "--voice", voix], stdout=lg, stderr=lg,
        cwd=os.path.dirname(MANGA_PREC), creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    return {"ok": True}


# --- Karaoke d'une narration (Manga Studio v1.86.0) ------------------------------------''')

# couts : les resumes (chapitres vivants)
rep('''                # v1.91.0 : les TRADUCTIONS sont des depenses aussi (finies ET en cours)''',
    '''                for mode in ("ouverture", "rattrapage") if ch.startswith("ch_") else ():   # v1.94.0
                    pj = os.path.join(sd, ch, "precedemment", mode + ".json")
                    try:
                        if os.path.isfile(pj):
                            with open(pj, encoding="utf-8") as f: pq = json.load(f)
                            runs.append({"chap": slug + "/" + ch, "tag": mode, "engine": "deepseek",
                                         "date": (pq.get("created_at") or "")[:19], "prompt": "precedemment", "reuse": None,
                                         "st": {"cout_precedemment": (pq.get("stats") or {}).get("cout_total", 0)}})
                    except Exception:
                        pass
                # v1.91.0 : les TRADUCTIONS sont des depenses aussi (finies ET en cours)''')

# couts : les resumes d'un chapitre mis a la corbeille
rep('''        if "fidelite.json" in fichiers:
            try:
                with open(os.path.join(dp, "fidelite.json"), encoding="utf-8") as f: fj = json.load(f)
                runs.append({"chap": "corbeille/" + rel,''',
    '''        for mode in ("ouverture", "rattrapage") if os.path.basename(dp) == "precedemment" else ():   # v1.94.0
            if mode + ".json" in fichiers:
                try:
                    with open(os.path.join(dp, mode + ".json"), encoding="utf-8") as f: pq = json.load(f)
                    runs.append({"chap": "corbeille/" + rel, "tag": mode + " (supprime)", "engine": "deepseek",
                                 "date": (pq.get("created_at") or "")[:19], "prompt": "precedemment", "reuse": None,
                                 "st": {"cout_precedemment": (pq.get("stats") or {}).get("cout_total", 0)}})
                except Exception:
                    pass
        if "fidelite.json" in fichiers:
            try:
                with open(os.path.join(dp, "fidelite.json"), encoding="utf-8") as f: fj = json.load(f)
                runs.append({"chap": "corbeille/" + rel,''')

rep('''              "traduction": "cout_traduction", "karaoke": "cout_karaoke"}                  # v1.91.0''',
    '''              "traduction": "cout_traduction", "karaoke": "cout_karaoke",                  # v1.91.0
              "precedemment": "cout_precedemment"}                                         # v1.94.0''')

# activite
rep('''    try:                                                     # v1.93.0 : les videos (en cours, puis en attente)''',
    '''    for (pd_, pm_), _pp in list(_PREC_JOBS.items()):          # v1.94.0 : les resumes en cours
        if _pp.poll() is None:
            out.append({"type": "precedemment", "d": pd_, "tag": pm_, "titre": pd_.split("/")[0],
                        "chapitre": pd_.split("/")[-1][3:], "etape": pm_})
    try:                                                     # v1.93.0 : les videos (en cours, puis en attente)''')

# routes
rep('''        elif self.path.split("?", 1)[0] == "/manga/activite":              # Manga Studio v1.88.0''',
    '''        elif self.path.split("?", 1)[0] == "/manga/precedemment":          # Manga Studio v1.94.0
            _r = manga_precedemment((parse_qs(urlparse(self.path).query).get("d") or [""])[0])
            if _r is None: self._json(404, {"error": "chapitre introuvable"})
            else: self._json(200, _r)
        elif self.path.split("?", 1)[0] == "/manga/activite":              # Manga Studio v1.88.0''')

rep('''            elif self.path == "/manga/karaoke":                # Manga Studio v1.86.0''',
    '''            elif self.path == "/manga/precedemment":           # Manga Studio v1.94.0
                self._json(200, manga_precedemment_lance(data))
            elif self.path == "/manga/karaoke":                # Manga Studio v1.86.0''')

open(p, "w", encoding="utf-8").write(s)
print("patch precedemment OK")
