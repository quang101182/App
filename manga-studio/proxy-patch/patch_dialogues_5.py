# -*- coding: utf-8 -*-
"""Manga Studio v2.81.5 -- mode Dialogues, 5e patch serveur (Quang 27/09 01h53 : « traduire seulement les pages lues » ;
01h55 : « une tracabilite pour que le mode normal ne confonde pas »). Avec traduire_chapitre.py >= 2.1.0 (traduction.json :
complete, pages_chapitre, via par page, historique) et dialogues.py >= 1.8.0 (preparer --traduire) :
- /manga/dialogues rend trad_pages (pages deja en francais) et vf (chapitre deja en francais) ;
- /manga/dialogues_lancer accepte « traduire » : traduit d'abord les pages demandees qui manquent (JAMAIS sans ce drapeau) ;
- /manga/traductions rend complete / n / total / via_dialogues / historique ;
- bibliotheque : « trad » = langues COMPLETES seulement, « trad_partiel » = traduites en partie (badge distinct dans l'app).
Suppose patch_dialogues_4.py. Rejouable : python patch_dialogues_5.py <chemin du proxy>"""
import io, sys

P = sys.argv[1]
s = io.open(P, encoding="utf-8", newline="").read()
if "def _dlg_francais(" not in s:
    print("ERREUR : appliquer d'abord patch_dialogues_4.py"); sys.exit(1)
if "def _trad_etat(" in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", NL), b.replace("\n", NL)
    assert s.count(a) == 1, ("ancre", s.count(a), a[:80])
    s = s.replace(a, b)


rep('''def _dlg_francais(base):''', '''_TRAD_ETAT_CACHE = {}


def _trad_etat(td):
    """v2.81.5 : {complete, pages, total, via_dialogues, historique} d'une traduction (cache par date du fichier) ; None si absente.
    Un fichier d'avant traduire_chapitre 2.1.0 (sans « complete ») = chapitre entier."""
    tj = os.path.join(td, "traduction.json")
    try:
        mt = os.path.getmtime(tj)
    except OSError:
        return None
    c = _TRAD_ETAT_CACHE.get(tj)
    if c and c[0] == mt:
        return c[1]
    try:
        with open(tj, encoding="utf-8") as f:
            t = json.load(f)
    except Exception:
        return None
    pages = sorted(x["page"] for x in t.get("pages") or [])
    e = {"complete": bool(t.get("complete", True)), "pages": pages, "total": t.get("pages_chapitre") or len(pages),
         "via_dialogues": [x["page"] for x in t.get("pages") or [] if x.get("via") == "dialogues"],
         "historique": t.get("historique") or []}
    _TRAD_ETAT_CACHE[tj] = (mt, e)
    return e


def _dlg_francais(base):''')
rep('''    return {"d": d, "traduit": _dlg_francais(base),''',
    '''    _te = _trad_etat(os.path.join(base, "traduction", "fr"))
    return {"d": d, "traduit": _dlg_francais(base), "trad_pages": (_te or {}).get("pages") or [],
            "trad_complete": bool(_te and _te["complete"]),
            "vf": not _te and (_dlg_lire(os.path.join(base, "langue.json")) or {}).get("langue") == "fr",''')
rep('''def manga_dialogues_lancer(d, action, pages=""):''', '''def manga_dialogues_lancer(d, action, pages="", traduire=False):''')
rep('''    if action == "preparer" and not _dlg_francais(base):''',
    '''    if action == "preparer" and not _dlg_francais(base) and not (traduire and pages):''')
rep('''    cmd = [MANGA_PY, MANGA_DIALOGUES, action, d] + (["--pages", pages] if pages and action != "video" else [])''',
    '''    cmd = [MANGA_PY, MANGA_DIALOGUES, action, d] + (["--pages", pages] if pages and action != "video" else []) \
        + (["--traduire"] if traduire and action == "preparer" else [])          # v2.81.5 : sur demande EXPLICITE seulement''')
rep('''                self._json(200, manga_dialogues_lancer(str(data.get("d") or ""), str(data.get("action") or ""),
                                                       str(data.get("pages") or "")))''',
    '''                self._json(200, manga_dialogues_lancer(str(data.get("d") or ""), str(data.get("action") or ""),
                                                       str(data.get("pages") or ""), data.get("traduire") is True))''')
rep('''                it.update(etat="fini", stats=t.get("stats"), engine=t.get("engine"), created_at=t.get("created_at"),''',
    '''                _te = _trad_etat(td) or {}                                         # v2.81.5 : tracabilite
                it.update(complete=_te.get("complete", True), n=len(_te.get("pages") or []), total=_te.get("total"),
                          via_dialogues=_te.get("via_dialogues") or [], historique=_te.get("historique") or [])
                it.update(etat="fini", stats=t.get("stats"), engine=t.get("engine"), created_at=t.get("created_at"),''')
rep('''            it["trad"] = sorted(lg for lg in (os.listdir(td) if os.path.isdir(td) else [])
                                if os.path.isfile(os.path.join(td, lg, "traduction.json")))''',
    '''            _tl = {lg: _trad_etat(os.path.join(td, lg)) for lg in (os.listdir(td) if os.path.isdir(td) else [])}
            it["trad"] = sorted(lg for lg, e in _tl.items() if e and e["complete"])            # v2.81.5 : COMPLETES
            it["trad_partiel"] = sorted(lg for lg, e in _tl.items() if e and not e["complete"])''')
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("proxy patche (5)")
