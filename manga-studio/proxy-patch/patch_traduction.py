# -*- coding: utf-8 -*-
"""Patch du proxy 8190 : traduire les dialogues d'un chapitre (Manga Studio v1.84.0, 22/09/2026).

POST /manga/traduire {d, langue, engine} -> lance scripts/traduire_chapitre.py (venv kohya) EN FOND,
comme la narration ; GET /manga/traductions?d= -> langues disponibles, progression, stats, pages.
Les pages traduites vivent sous sources/<chap>/traduction/<langue>/ (servies par /manga/source_file).
Rejouable : python patch_traduction.py <chemin du proxy>. Suppose patch_bibliotheque.py applique.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "def manga_traduire(" in s:
    print("deja patche")
    sys.exit(0)


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


rep('''def manga_narrations(d):''',
    '''# --- Traduction des dialogues d'un chapitre (Manga Studio v1.84.0) ---------------------
MANGA_TRADUIRE = os.path.join(MANGA_ROOT, "scripts", "traduire_chapitre.py")
_TRAD_JOBS = {}                                  # (chapitre, langue) -> Popen


def manga_traduire(d, langue, engine="gemini"):
    if not re.match(r"^[a-z]{2}$", langue or ""):
        return {"error": "langue invalide"}
    if engine not in ("gemini", "kimi"):
        return {"error": "moteur inconnu"}
    base = _manga_src_safe(d)
    if not base or not os.path.isfile(os.path.join(base, "manifest.json")):
        return {"error": "chapitre introuvable"}
    if not os.path.isfile(MANGA_PY) or not os.path.isfile(MANGA_TRADUIRE):
        return {"error": "venv kohya ou traduire_chapitre.py introuvable"}
    job = _TRAD_JOBS.get((d, langue))
    if job and job.poll() is None:
        return {"error": "une traduction %s tourne deja sur ce chapitre" % langue}
    td = os.path.join(base, "traduction", langue)
    os.makedirs(td, exist_ok=True)
    try: os.remove(os.path.join(td, "progress.json"))
    except Exception: pass
    lg = open(os.path.join(td, "run.log"), "w", encoding="utf-8")
    _TRAD_JOBS[(d, langue)] = subprocess.Popen(
        [MANGA_PY, MANGA_TRADUIRE, d, "--langue", langue, "--engine", engine], stdout=lg, stderr=lg,
        cwd=os.path.dirname(MANGA_TRADUIRE), creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return {"ok": True, "langue": langue}


def manga_traductions(d):
    base = _manga_src_safe(d)
    if not base or not os.path.isdir(base):
        return None
    racine, out = os.path.join(base, "traduction"), []
    for lg in sorted(os.listdir(racine)) if os.path.isdir(racine) else []:
        td = os.path.join(racine, lg)
        it = {"langue": lg, "etat": "vide"}
        try:
            with open(os.path.join(td, "progress.json"), encoding="utf-8") as f:
                it["progress"] = json.load(f)
        except Exception:
            pass
        job = _TRAD_JOBS.get((d.strip("/"), lg))
        vivant = (job and job.poll() is None) or (
            it.get("progress") and not it["progress"].get("fini") and time.time() - float(it["progress"].get("t") or 0) < 180)
        tj = os.path.join(td, "traduction.json")
        if vivant:
            it["etat"] = "en cours"
        elif os.path.isfile(tj):
            try:
                with open(tj, encoding="utf-8") as f:
                    t = json.load(f)
                it.update(etat="fini", stats=t.get("stats"), engine=t.get("engine"), created_at=t.get("created_at"),
                          pages={x["source"]: d.strip("/") + "/traduction/" + lg + "/" + x["file"] for x in t.get("pages") or []})
            except Exception as e:
                it.update(etat="illisible", err=str(e))
        elif os.path.isfile(os.path.join(td, "run.log")):
            try:
                it.update(etat="echec", err=open(os.path.join(td, "run.log"), encoding="utf-8", errors="replace").read()[-400:])
            except Exception:
                it["etat"] = "echec"
        out.append(it)
    return {"items": out}


def manga_narrations(d):''')

rep('''        elif self.path.split("?", 1)[0] == "/manga/narrations":''',
    '''        elif self.path.split("?", 1)[0] == "/manga/traductions":           # Manga Studio v1.84.0
            _r = manga_traductions((parse_qs(urlparse(self.path).query).get("d") or [""])[0])
            if _r is None: self._json(404, {"error": "chapitre introuvable"})
            else: self._json(200, _r)
        elif self.path.split("?", 1)[0] == "/manga/narrations":''')

rep('''            elif self.path == "/manga/serie_renommer":         # Manga Studio v1.80.0''',
    '''            elif self.path == "/manga/traduire":               # Manga Studio v1.84.0
                self._json(200, manga_traduire(data.get("d") or "", data.get("langue") or "fr",
                                               data.get("engine") or "gemini"))
            elif self.path == "/manga/serie_renommer":         # Manga Studio v1.80.0''')

open(p, "w", encoding="utf-8").write(s)
print("patch traduction OK")
