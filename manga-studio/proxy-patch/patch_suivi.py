# -*- coding: utf-8 -*-
"""Patch du proxy 8190 : SUIVI DE SERIES (Manga Studio v1.98.0, 22/09/2026, etape 9 -- sans plafond, decision Quang).

GET  /manga/suivi?serie=<slug> -> {config (suivi.json), file (chapitres a narrer), estimation, passage (etat.json), journal}
POST /manga/suivi {serie, actif, voix, karaoke, precedemment, video, reglages_video} -> ecrit sources/<slug>/suivi.json
POST /manga/suivi_lancer {serie?} -> lance scripts/suivi_nuit.py EN FOND (survit a une relance du proxy, comme video_lot)
La regle « quoi narrer » vit dans suivi_nuit.py (charge a la volee) : aucune copie ici.
Rejouable : python patch_suivi.py <chemin du proxy>.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "def manga_suivi(" in s:
    print("deja patche")
    sys.exit(0)


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


rep(r'''# --- « Precedemment... » et rattrapage (Manga Studio v1.94.0) ---------------------------''',
    r'''# --- Suivi de series : la nuit, tout ce qui a ete capture est narre (Manga Studio v1.98.0) --
MANGA_SUIVI = os.path.join(MANGA_ROOT, "scripts", "suivi_nuit.py")
_SUIVI_MOD = {"m": None, "t": 0}


def _suivi_mod():
    t = os.path.getmtime(MANGA_SUIVI)
    if _SUIVI_MOD["m"] is None or _SUIVI_MOD["t"] != t:
        import importlib.util
        sys.path.insert(0, os.path.dirname(MANGA_SUIVI))
        sp = importlib.util.spec_from_file_location("manga_suivi_nuit", MANGA_SUIVI)
        m = importlib.util.module_from_spec(sp)
        sp.loader.exec_module(m)
        _SUIVI_MOD.update(m=m, t=t)
    return _SUIVI_MOD["m"]


def manga_suivi(serie):
    sd = _manga_src_safe(serie) if _RE_SERIE.match(serie or "") else None
    if not sd or not os.path.isdir(sd):
        return None
    m = _suivi_mod()
    try:
        with open(os.path.join(sd, "suivi.json"), encoding="utf-8") as f: cfg = json.load(f)
    except Exception:
        cfg = {}
    file = [{"d": c["d"], "num": c["num"], "pages": c["pages"]} for c in m.a_narrer(serie)]
    pages = sum(c["pages"] for c in file)
    etat = m.lire_etat()
    etat["vivant"] = etat.get("etat") == "en cours" and m.pid_vivant(etat.get("pid"))
    if etat.get("etat") == "en cours" and not etat["vivant"]:
        etat["etat"] = "interrompu"
    jr = []
    try:
        with open(m.JOURNAL, encoding="utf-8") as f:
            for ligne in f.readlines()[-400:]:
                try:
                    x = json.loads(ligne)
                except Exception:
                    continue
                if not x.get("d") or x["d"].split("/")[0] == serie or x.get("ev") in ("debut", "fin"):
                    jr.append(x)
    except Exception:
        pass
    return {"config": cfg, "file": file, "estimation": {"cout": round(pages * 0.04, 2), "minutes": pages},
            "passage": etat, "journal": jr[-30:]}


def manga_suivi_regle(data):
    serie = data.get("serie") or ""
    sd = _manga_src_safe(serie) if _RE_SERIE.match(serie) else None
    if not sd or not os.path.isdir(sd):
        return {"error": "serie introuvable"}
    voix = data.get("voix") or "Charon"
    if not re.match(r"^[A-Z][a-z]{2,15}$", voix):
        return {"error": "voix invalide"}
    rv = data.get("reglages_video") or {}
    cfg = {"actif": bool(data.get("actif")), "voix": voix, "moteur": "kimi", "karaoke": bool(data.get("karaoke", True)),
           "precedemment": bool(data.get("precedemment", True)), "video": bool(data.get("video")),
           "reglages_video": {k: rv.get(k) for k in ("vitesse", "sous", "karaoke", "musique", "volume", "pages", "precedemment")},
           "maj": time.strftime("%Y-%m-%dT%H:%M:%S")}
    tmp = os.path.join(sd, "suivi.json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=1)
    os.replace(tmp, os.path.join(sd, "suivi.json"))
    return {"ok": True, "config": cfg}


def manga_suivi_lancer(data):
    serie = data.get("serie") or ""
    if serie and not _RE_SERIE.match(serie):
        return {"error": "serie invalide"}
    m = _suivi_mod()
    e = m.lire_etat()
    if e.get("etat") == "en cours" and m.pid_vivant(e.get("pid")):
        return {"error": "un passage tourne deja"}
    os.makedirs(m.DIR, exist_ok=True)
    lg = open(os.path.join(m.DIR, "runner.log"), "a", encoding="utf-8")
    cmd = [MANGA_PY, MANGA_SUIVI, "--declencheur", "bouton"] + (["--serie", serie] if serie else [])
    subprocess.Popen(cmd, stdout=lg, stderr=lg, cwd=os.path.dirname(MANGA_SUIVI),
                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    return {"ok": True}


# --- « Precedemment... » et rattrapage (Manga Studio v1.94.0) ---------------------------''')

rep(r'''        elif self.path.split("?", 1)[0] == "/manga/precedemment":          # Manga Studio v1.94.0''',
    r'''        elif self.path.split("?", 1)[0] == "/manga/suivi":                 # Manga Studio v1.98.0
            _r = manga_suivi((parse_qs(urlparse(self.path).query).get("serie") or [""])[0])
            if _r is None: self._json(404, {"error": "serie introuvable"})
            else: self._json(200, _r)
        elif self.path.split("?", 1)[0] == "/manga/precedemment":          # Manga Studio v1.94.0''')

rep(r'''            elif self.path == "/manga/precedemment":           # Manga Studio v1.94.0''',
    r'''            elif self.path == "/manga/suivi":                  # Manga Studio v1.98.0
                self._json(200, manga_suivi_regle(data))
            elif self.path == "/manga/suivi_lancer":
                self._json(200, manga_suivi_lancer(data))
            elif self.path == "/manga/precedemment":           # Manga Studio v1.94.0''')

open(p, "w", encoding="utf-8").write(s)
print("patch suivi OK")
