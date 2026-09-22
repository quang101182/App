# -*- coding: utf-8 -*-
"""Patch du proxy 8190 : LANGUE d'un chapitre + securite de traduction (Manga Studio v2.2.0, 22/09/2026, Quang 12h43).
GET /manga/langue?d=<serie/ch_N> -> langue.json (detectee a la 1re demande : API MangaDex, sinon Gemini sur 2 pages ;
scripts/langue_chapitre.py charge a la volee). /manga/resume porte « langue » par chapitre (ce qui est deja connu).
POST /manga/traduire : REFUSE de traduire vers la langue d'origine, sauf « force » (Quang confirme dans l'app).
Rejouable : python patch_langue.py <chemin du proxy>. Suppose patch_resume.py applique.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "def manga_langue(" in s:
    print("deja patche")
    sys.exit(0)


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


rep('''def manga_traduire(d, langue, engine="gemini"):
    if not re.match(r"^[a-z]{2}$", langue or ""):
        return {"error": "langue invalide"}''',
    '''MANGA_LANGUE = os.path.join(MANGA_ROOT, "scripts", "langue_chapitre.py")
_LANGUE_MOD = {"m": None, "t": 0}


def _langue_mod():
    t = os.path.getmtime(MANGA_LANGUE)
    if _LANGUE_MOD["m"] is None or _LANGUE_MOD["t"] != t:
        import importlib.util
        sys.path.insert(0, os.path.dirname(MANGA_LANGUE))
        sp = importlib.util.spec_from_file_location("manga_langue_chapitre", MANGA_LANGUE)
        m = importlib.util.module_from_spec(sp)
        sp.loader.exec_module(m)
        _LANGUE_MOD.update(m=m, t=t)
    return _LANGUE_MOD["m"]


def manga_langue(d, force=False):
    """v2.2.0 : la langue du chapitre (detectee une fois, gardee dans langue.json)."""
    base = _manga_src_safe((d or "").strip("/"))
    if not base or not os.path.isfile(os.path.join(base, "manifest.json")):
        return None
    try:
        return _langue_mod().detecter(d.strip("/"), force)
    except BaseException as e:
        return {"error": "detection impossible : %s" % str(e)[:160]}


def _langue_connue(base):
    try:
        with open(os.path.join(base, "langue.json"), encoding="utf-8") as f:
            return json.load(f).get("langue")
    except Exception:
        return None


def manga_traduire(d, langue, engine="gemini", force=False):
    if not re.match(r"^[a-z]{2}$", langue or ""):
        return {"error": "langue invalide"}
    _b = _manga_src_safe(d)
    if _b and not force and _langue_connue(_b) == langue:       # v2.2.0 : pas de « francais -> francais »
        return {"error": "ce chapitre est deja en %s" % langue, "meme_langue": True}''')
rep('''                self._json(200, manga_traduire(data.get("d") or "", data.get("langue") or "fr",
                                               data.get("engine") or "gemini"))''',
    '''                self._json(200, manga_traduire(data.get("d") or "", data.get("langue") or "fr",
                                               data.get("engine") or "gemini", bool(data.get("force"))))''')
rep('''            it["prec"] = os.path.isfile(os.path.join(cd, "precedemment", "ouverture.json"))''',
    '''            it["prec"] = os.path.isfile(os.path.join(cd, "precedemment", "ouverture.json"))
            it["langue"] = _langue_connue(cd)                                         # v2.2.0''')
rep(r'''        elif self.path.split("?", 1)[0] == "/manga/resume":                # Manga Studio v2.1.0''',
    r'''        elif self.path.split("?", 1)[0] == "/manga/langue":                # Manga Studio v2.2.0
            _q = parse_qs(urlparse(self.path).query)
            _r = manga_langue((_q.get("d") or [""])[0], (_q.get("force") or [""])[0] == "1")
            if _r is None: self._json(404, {"error": "chapitre introuvable"})
            else: self._json(200, _r)
        elif self.path.split("?", 1)[0] == "/manga/resume":                # Manga Studio v2.1.0''')
open(p, "w", encoding="utf-8").write(s)
print("patch langue OK")
