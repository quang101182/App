# -*- coding: utf-8 -*-
"""Manga Studio v3.5.5 -- telecommande de la fenetre de capture (principale ET secondaire) : les onglets dans l'ORDRE DU PC.
/json/list (CDP) rend les onglets du plus recemment actif au plus ancien -> toucher un onglet le faisait passer en tete
(Quang 27/09 21h55 : « deroutant »). Desormais : (1) ordre REEL de la barre d'onglets, lu en LECTURE SEULE par l'accessibilite
de Windows (scripts/ordre_onglets.py, cache 4 s) ; (2) sinon ordre STABLE (premier vu, nouveaux a la fin) : un onglet touche
ne bouge plus. La fenetre elle-meme n'est jamais touchee. Champ « ordre » : barre | stable. Rejouable."""
import io, sys

P = sys.argv[1]
s = io.open(P, encoding="utf-8", newline="").read()
if "def _pilote_ordonner(" in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", NL), b.replace("\n", NL)
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %s" % (s.count(a), a[:70]))
    s = s.replace(a, b)


rep('''def manga_pilote_onglets():
    try:
        l = _pilote_liste()
    except Exception:
        return {"edge": False, "onglets": []}
    ids = [t.get("id") for t in l]
    if _PILOTE_ACTIF["id"] not in ids:
        _PILOTE_ACTIF["id"] = ids[0] if ids else None           # /json/list : le 1er = le plus recemment actif
    return {"edge": True, "capture": bool(_FETCH["proc"] is not None and _FETCH["proc"].poll() is None),''',
'''_PILOTE_ORDRE = {"ids": [], "barre": None, "t": 0.0}          # v3.5.5 : ordre des onglets comme sur le PC
MANGA_ORDRE_ONGLETS = os.path.join(MANGA_ROOT, "scripts", "ordre_onglets.py")
PY_UIA = r"C:\\Users\\quang\\AppData\\Local\\Programs\\Python\\Python311\\python.exe"   # a comtypes (accessibilite Windows)


def _pilote_titres_barre():
    """v3.5.5 : titres des onglets dans l'ordre de la BARRE (lecture seule, accessibilite Windows), cache 4 s ; None sinon."""
    if time.time() - _PILOTE_ORDRE["t"] < 4:
        return _PILOTE_ORDRE["barre"]
    t = None
    try:
        port = int(MF_CDP.rsplit(":", 1)[1])
        r = subprocess.run([PY_UIA if os.path.isfile(PY_UIA) else sys.executable, MANGA_ORDRE_ONGLETS, str(port)],
                           capture_output=True, text=True, timeout=12, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        d = json.loads((r.stdout or "").strip().splitlines()[-1])
        t = d.get("titres") if d.get("ok") else None
    except Exception:
        t = None
    _PILOTE_ORDRE.update(barre=t, t=time.time())
    return t


def _pilote_ordonner(l):
    """v3.5.5 : l (ordre CDP = recemment actif d'abord) -> (onglets dans l'ordre du PC, « barre » | « stable »)."""
    import html as _h
    par = {t.get("id"): t for t in l}
    o = [i for i in _PILOTE_ORDRE["ids"] if i in par] + [t.get("id") for t in l if t.get("id") not in _PILOTE_ORDRE["ids"]]
    source = "stable"
    barre = _pilote_titres_barre()
    if barre:
        norm = lambda x: " ".join(_h.unescape(x or "").split()).lower()
        libres, rang = list(o), {}
        for k, nom in enumerate(barre):
            n = norm(nom)
            for i in libres:
                ti = norm(par[i].get("title")) or norm(par[i].get("url"))
                if ti and (n.startswith(ti[:60]) or ti.startswith(n[:60])):
                    rang[i] = k
                    libres.remove(i)
                    break
        if o and len(rang) >= 0.8 * len(o):
            o = sorted(o, key=lambda i: (rang.get(i, 10000), o.index(i)))
            source = "barre"
    _PILOTE_ORDRE["ids"] = o
    return [par[i] for i in o], source


def manga_pilote_onglets():
    try:
        l = _pilote_liste()
    except Exception:
        return {"edge": False, "onglets": []}
    ids = [t.get("id") for t in l]
    if _PILOTE_ACTIF["id"] not in ids:
        _PILOTE_ACTIF["id"] = ids[0] if ids else None           # /json/list : le 1er = le plus recemment actif
    l, ordre = _pilote_ordonner(l)                               # v3.5.5 : affichage dans l'ordre du PC
    return {"edge": True, "ordre": ordre, "capture": bool(_FETCH["proc"] is not None and _FETCH["proc"].poll() is None),''')

# un onglet ouvert / ferme -> relire la barre tout de suite
rep('''def manga_pilote(data):
    oid, action = data.get("id") or "", data.get("action") or ""''',
    '''def manga_pilote(data):
    oid, action = data.get("id") or "", data.get("action") or ""
    _PILOTE_ORDRE["t"] = 0.0                                     # v3.5.5 : la barre a pu changer''')

io.open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
