# -*- coding: utf-8 -*-
"""Patch du proxy 8190 : TELECOMMANDE de la fenetre de capture depuis le telephone (Manga Studio v2.0.0, etape 17).

Quang (22/09 10h29) : se placer correctement dans la fenetre de capture depuis le smartphone avant de lancer la capture ;
(10h30) « il faut que ca reste pilotable, ergonomique au niveau des onglets et de la navigation ».
Par le port CDP de la fenetre dediee (9223, celle de manga-fetch -- manga-fetch n'est PAS modifie) :
GET  /manga/pilote_onglets            -> [{id, url, titre, actif}]
GET  /manga/pilote_ecran?id=<onglet>  -> JPEG de la zone visible (en-tetes X-Url / X-Titre / X-Largeur / X-Hauteur)
POST /manga/pilote {id, action, ...}  -> clic (x,y fractions), molette (dy), touche, texte, url, retour, avant, recharger,
                                         activer, fermer, nouvel (url)
Refuse pendant une capture (on ne deplace pas la page qu'on est en train de lire). Client websocket : scripts/cdp_mini.py.
Rejouable : python patch_pilote.py <chemin du proxy>.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "def manga_pilote(" in s:
    print("deja patche")
    sys.exit(0)


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


rep(r'''def manga_fetch_edge():''',
    r'''# --- Telecommande de la fenetre de capture (Manga Studio v2.0.0) ------------------------
MANGA_CDP_MINI = os.path.join(MANGA_ROOT, "scripts", "cdp_mini.py")
_CDP_MOD = {"m": None, "t": 0}
_PILOTE_ACTIF = {"id": None}


def _cdp_mod():
    t = os.path.getmtime(MANGA_CDP_MINI)
    if _CDP_MOD["m"] is None or _CDP_MOD["t"] != t:
        import importlib.util
        sp = importlib.util.spec_from_file_location("manga_cdp_mini", MANGA_CDP_MINI)
        m = importlib.util.module_from_spec(sp)
        sp.loader.exec_module(m)
        _CDP_MOD.update(m=m, t=t)
    return _CDP_MOD["m"]


def _pilote_liste():
    with urllib.request.urlopen(MF_CDP + "/json/list", timeout=3) as r:
        return [t for t in json.load(r) if t.get("type") == "page"]


def manga_pilote_onglets():
    try:
        l = _pilote_liste()
    except Exception:
        return {"edge": False, "onglets": []}
    ids = [t.get("id") for t in l]
    if _PILOTE_ACTIF["id"] not in ids:
        _PILOTE_ACTIF["id"] = ids[0] if ids else None           # /json/list : le 1er = le plus recemment actif
    return {"edge": True, "capture": bool(_FETCH["proc"] is not None and _FETCH["proc"].poll() is None),
            "onglets": [{"id": t.get("id"), "url": t.get("url", ""), "titre": (t.get("title") or "")[:120],
                         "actif": t.get("id") == _PILOTE_ACTIF["id"]} for t in l]}


def _pilote_ws(oid):
    for t in _pilote_liste():
        if t.get("id") == oid:
            return t.get("webSocketDebuggerUrl")
    return None


def manga_pilote_ecran(oid):
    ws = _pilote_ws(oid) if re.match(r"^[A-Za-z0-9]{8,64}$", oid or "") else None
    if not ws:
        return None
    return _cdp_mod().ecran(ws)


def manga_pilote(data):
    oid, action = data.get("id") or "", data.get("action") or ""
    if _FETCH["proc"] is not None and _FETCH["proc"].poll() is None:
        return {"error": "une capture est en cours : on ne touche pas a la fenetre"}
    try:
        if action == "nouvel":
            u = str(data.get("url") or "about:blank").strip()
            if u != "about:blank" and not u.startswith(("http://", "https://")):
                u = "https://" + u
            req = urllib.request.Request(MF_CDP + "/json/new?" + quote(u, safe=":/?&=%#"), method="PUT")
            with urllib.request.urlopen(req, timeout=5) as r:
                t = json.load(r)
            _PILOTE_ACTIF["id"] = t.get("id")
            return {"ok": True, "id": t.get("id")}
        if not re.match(r"^[A-Za-z0-9]{8,64}$", oid):
            return {"error": "onglet invalide"}
        if action in ("activer", "fermer"):
            with urllib.request.urlopen(MF_CDP + "/json/%s/%s" % ("activate" if action == "activer" else "close", oid), timeout=5) as r:
                r.read()
            if action == "activer":
                _PILOTE_ACTIF["id"] = oid
            elif _PILOTE_ACTIF["id"] == oid:
                _PILOTE_ACTIF["id"] = None
            return {"ok": True}
        ws = _pilote_ws(oid)
        if not ws:
            return {"error": "onglet introuvable (ferme ?)"}
        _PILOTE_ACTIF["id"] = oid
        return _cdp_mod().piloter(ws, action, **{k: v for k, v in data.items() if k not in ("id", "action")})
    except Exception as e:
        return {"error": str(e)[:200]}


def manga_fetch_edge():''')

rep(r'''        elif self.path.split("?", 1)[0] == "/manga/fetch_tabs":''',
    r'''        elif self.path.split("?", 1)[0] == "/manga/pilote_onglets":        # Manga Studio v2.0.0
            self._json(200, manga_pilote_onglets())
        elif self.path.split("?", 1)[0] == "/manga/pilote_ecran":
            try:
                _r = manga_pilote_ecran((parse_qs(urlparse(self.path).query).get("id") or [""])[0])
            except Exception as _e:
                _r = None; self._json(502, {"error": str(_e)[:200]})
            else:
                if _r is None: self._json(404, {"error": "onglet introuvable"})
                else:
                    _img, _w, _h, _u, _t = _r
                    self.send_response(200); self._cors()
                    self.send_header("Content-Type", "image/jpeg"); self.send_header("Cache-Control", "no-store")
                    self.send_header("Access-Control-Expose-Headers", "X-Url, X-Titre, X-Largeur, X-Hauteur")
                    self.send_header("X-Url", quote(_u[:500], safe=""));  self.send_header("X-Titre", quote(_t[:200], safe=""))
                    self.send_header("X-Largeur", str(int(_w))); self.send_header("X-Hauteur", str(int(_h)))
                    self.send_header("Content-Length", str(len(_img))); self.end_headers(); self.wfile.write(_img)
        elif self.path.split("?", 1)[0] == "/manga/fetch_tabs":''')

rep(r'''            elif self.path == "/manga/fetch_capture":''',
    r'''            elif self.path == "/manga/pilote":                 # Manga Studio v2.0.0
                self._json(200, manga_pilote(data))
            elif self.path == "/manga/fetch_capture":''')

open(p, "w", encoding="utf-8").write(s)
print("patch pilote OK")
