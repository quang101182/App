# -*- coding: utf-8 -*-
"""Manga Studio v2.81.0 -- mode Dialogues, 2e patch serveur (ROADMAP 4-septdecies, D4-bis + D5). Suppose patch_dialogues.py.
  GET  /manga/dialogues_plan?d=          etat de chaque replique + credits a prevoir (dialogues.py plan : AUCUN appel paye)
  GET  /manga/dialogues_lot?serie=       etat du lot de la serie (<serie>/dialogues_lot.json)
  POST /manga/dialogues_lot {serie, de, a, action: preparer|voix|tout}    plusieurs chapitres, dans l'ordre
  POST /manga/dialogues_lot_arreter {serie}
Activite : le lot en cours apparait (type « dialogues_lot »).
Rejouable : python patch_dialogues_2.py <chemin du proxy>"""
import io, sys

P = sys.argv[1]
s = io.open(P, encoding="utf-8", newline="").read()
if "MANGA_DIALOGUES =" not in s:
    print("ERREUR : appliquer d'abord patch_dialogues.py"); sys.exit(1)
if "def manga_dialogues_plan(" in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"


def rep(a, b, n=1):
    global s
    a, b = a.replace("\n", NL), b.replace("\n", NL)
    assert s.count(a) == n, ("ancre", s.count(a), a[:80])
    s = s.replace(a, b)


BLOC = '''_DLG_LOTS = {}                                    # serie -> Popen


def manga_dialogues_plan(d):
    if not _dlg_base(d):
        return {"error": "chapitre introuvable"}
    try:
        r = subprocess.run([MANGA_PY, MANGA_DIALOGUES, "plan", d], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=60, cwd=os.path.dirname(MANGA_DIALOGUES),
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return json.loads((r.stdout or "").strip().splitlines()[-1])
    except Exception as e:
        return {"error": "plan illisible : " + str(e)[:160]}


def _dlg_serie_dir(serie):
    if not re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,120}$", serie or ""):
        return None
    sd = _manga_src_safe(serie)
    return sd if sd and os.path.isdir(sd) else None


def _dlg_lot_vivant(serie):
    p = _DLG_LOTS.get(serie)
    if p is not None and p.poll() is None:
        return True
    sd = _dlg_serie_dir(serie)
    e = _dlg_lire(os.path.join(sd, "dialogues_lot.json")) if sd else None
    return bool(e and e.get("etat") == "en cours" and e.get("pid") and _pid_vivant(e["pid"]) and time.time() - float(e.get("t") or 0) < 3600)


def manga_dialogues_lot(serie, data=None):
    sd = _dlg_serie_dir(serie)
    if not sd:
        return {"error": "série introuvable"}
    if data is None:
        return {"lot": _dlg_lire(os.path.join(sd, "dialogues_lot.json")), "en_cours": _dlg_lot_vivant(serie)}
    action = str(data.get("action") or "")
    if action not in ("preparer", "voix", "tout"):
        return {"error": "action inconnue"}
    try:
        de, a = float(data.get("de")), float(data.get("a"))
    except (TypeError, ValueError):
        return {"error": "chapitres invalides"}
    if a < de or a - de > 300:
        return {"error": "plage de chapitres invalide (300 au plus)"}
    if _dlg_lot_vivant(serie):
        return {"error": "un lot de dialogues tourne déjà sur cette série"}
    lg = open(os.path.join(sd, "dialogues_lot.log"), "w", encoding="utf-8")
    _DLG_LOTS[serie] = subprocess.Popen([MANGA_PY, MANGA_DIALOGUES, "lot", serie, "--de", str(de), "--a", str(a), "--action", action],
                                        stdout=lg, stderr=lg, cwd=os.path.dirname(MANGA_DIALOGUES),
                                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return {"ok": True}


def manga_dialogues_lot_arreter(serie):
    sd = _dlg_serie_dir(serie)
    if not sd:
        return {"error": "série introuvable"}
    fl = os.path.join(sd, "dialogues_lot.json")
    e = _dlg_lire(fl) or {}
    p = _DLG_LOTS.get(serie)
    pid = p.pid if (p is not None and p.poll() is None) else e.get("pid")
    if pid and _pid_vivant(pid):
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if e:
        e.update(etat="arrete", arret="arrêté à ta demande", t=time.time())
        for c in e.get("chapitres") or []:
            if c.get("etat") == "en cours":
                c["etat"] = "arrete"
                pf = os.path.join(sd, c["ch"], "dialogues", "progress.json")
                pr = _dlg_lire(pf)
                if pr and not pr.get("fini"):
                    pr.update(fini=True, etape="arrete", arret="arrêté à ta demande"); _dlg_ecrire(pf, pr)
        _dlg_ecrire(fl, e)
    return {"ok": True}


'''
rep("def _credits_el(lignes):\n", BLOC + "def _credits_el(lignes):\n")

rep('''    for se in series:
        sd = os.path.join(MANGA_SOURCES, se)
        if not os.path.isdir(sd):
            continue''', '''    for se in series:
        sd = os.path.join(MANGA_SOURCES, se)
        if not os.path.isdir(sd):
            continue
        _gl = _dlg_lire(os.path.join(sd, "dialogues_lot.json"))                 # v2.81.0 : lot de dialogues
        if _gl and _gl.get("etat") == "en cours" and _dlg_lot_vivant(se):
            _ch = _gl.get("chapitres") or []
            out.append({"type": "dialogues_lot", "d": _gl.get("en_cours") or se, "titre": se, "chapitre": "",
                        "fait": sum(1 for c in _ch if c.get("etat") == "fait"),
                        "total": sum(1 for c in _ch if c.get("etat") != "non traduit")})''')

rep('''        elif self.path.split("?", 1)[0] == "/manga/el_voix":
            self._json(200, manga_el_voix())''', '''        elif self.path.split("?", 1)[0] == "/manga/el_voix":
            self._json(200, manga_el_voix())
        elif self.path.split("?", 1)[0] == "/manga/dialogues_plan":
            self._json(200, manga_dialogues_plan((parse_qs(urlparse(self.path).query).get("d") or [""])[0]))
        elif self.path.split("?", 1)[0] == "/manga/dialogues_lot":
            self._json(200, manga_dialogues_lot((parse_qs(urlparse(self.path).query).get("serie") or [""])[0]))''')

rep('''            elif self.path == "/manga/dialogues_ecouter":
                self._json(200, manga_dialogues_ecouter(data))''', '''            elif self.path == "/manga/dialogues_ecouter":
                self._json(200, manga_dialogues_ecouter(data))
            elif self.path == "/manga/dialogues_lot":
                self._json(200, manga_dialogues_lot(str(data.get("serie") or ""), data))
            elif self.path == "/manga/dialogues_lot_arreter":
                self._json(200, manga_dialogues_lot_arreter(str(data.get("serie") or "")))''')

io.open(P, "w", encoding="utf-8", newline="").write(s)
print("proxy patche (2)")
