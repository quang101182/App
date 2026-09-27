# -*- coding: utf-8 -*-
"""Manga Studio v3.1.0 -- mode Dialogues, 12e patch serveur (R30, maquette_verif_bulles_v1 validee 27/09 17h17) :
  * /manga/dialogues_lancer accepte action « detecter » (dialogues.py 1.19.0 : detection SEULE, gratuite, pages non traduites) ;
  * GET /manga/dialogues_bulles?d=&pages=a-b : pour chaque page, les bulles que la PREPARATION lira (meme filtre que
    dialogues.py : dialogue / narration, ecartee seulement pour l'image, texte ou « a lire »), sinon celles de detection.json,
    l'image a afficher (traduite si elle existe), + la verification deja enregistree ;
  * POST /manga/dialogues_verif {d, pages: {n: {ordre, exclues, ajouts}}} : enregistre la verification de Quang
    (dialogues/bulles_verifiees.json, page par page, fusionnee) -- valeurs controlees (fractions 0..1, ids entiers).
Rejouable : python patch_dialogues_12.py <proxy>"""
import io, sys

P = sys.argv[1]
s = io.open(P, encoding="utf-8", newline="").read()
if "def manga_dialogues_bulles(" in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", NL), b.replace("\n", NL)
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %s" % (s.count(a), a[:60]))
    s = s.replace(a, b)


rep('''    if action not in ("preparer", "voix", "video"):          # v2.81.0 D7 : la video des dialogues''',
    '''    if action not in ("preparer", "voix", "video", "detecter"):          # v2.81.0 D7 : la video des dialogues ; v3.1.0 (R30) : detection seule''')

FN = r'''

def _dlg_box_ok(b):
    try:
        v = {k: float(b[k]) for k in ("x", "y", "w", "h")}
    except Exception:
        return None
    if not all(0 <= v[k] <= 1 for k in v) or v["w"] <= 0.003 or v["h"] <= 0.003 or v["x"] + v["w"] > 1.001 or v["y"] + v["h"] > 1.001:
        return None
    return {k: round(v[k], 4) for k in v}


def manga_dialogues_bulles(d, pages):
    """v3.1.0 (R30) : les bulles a verifier d'une plage de pages."""
    base = _dlg_base(d)
    if not base:
        return {"error": "chapitre introuvable"}
    if not _RE_DLG_PAGES.match(pages or ""):
        return {"error": "plage de pages invalide"}
    a, b = (int(x) for x in (pages + "-" + pages).split("-")[:2]) if "-" not in pages else (int(x) for x in pages.split("-"))
    man = [x.get("file") for x in ((_dlg_lire(os.path.join(base, "manifest.json")) or {}).get("pages") or [])]
    tr = _dlg_lire(os.path.join(base, "traduction", "fr", "traduction.json")) or {}
    trp = {p.get("page"): p for p in tr.get("pages") or []}
    det = ((_dlg_lire(os.path.join(base, "dialogues", "detection.json")) or {}).get("pages")) or {}
    verif = ((_dlg_lire(os.path.join(base, "dialogues", "bulles_verifiees.json")) or {}).get("pages")) or {}
    out = []
    for n in range(max(1, a), min(len(man), b) + 1):
        p = trp.get(n)
        if p is not None and p.get("bulles") is not None:
            bl = [{"id": x["id"], "box": x["box"], "type": x.get("type"), "texte": (x.get("trad") or "").strip()}
                  for x in p["bulles"] if x.get("type") in ("dialogue", "narration") and x.get("box")
                  and (not x.get("ecarte") or not str(x.get("ecarte")).startswith("moins de 2"))
                  and ((x.get("trad") or "").strip() or x.get("a_lire"))]
            src, img = "traduction", "traduction/fr/" + p.get("file", "page_%03d.png" % n)
        elif str(n) in det:
            bl = [{"id": x["id"], "box": x["box"], "type": "dialogue", "texte": ""} for x in det[str(n)].get("bulles") or []]
            src, img = "detection", man[n - 1]
        else:
            bl, src, img = [], None, man[n - 1]
        out.append({"page": n, "source": src, "img": img, "bulles": sorted(bl, key=lambda x: x["id"]), "verif": verif.get(str(n))})
    return {"d": d, "pages": out, "en_cours": _dlg_vivant(d)}


def manga_dialogues_verif(d, pages):
    base = _dlg_base(d)
    if not base:
        return {"error": "chapitre introuvable"}
    if not isinstance(pages, dict) or not pages or len(pages) > 400:
        return {"error": "rien a enregistrer"}
    f = os.path.join(base, "dialogues", "bulles_verifiees.json")
    doc = _dlg_lire(f) or {"pages": {}}
    for k, v in pages.items():
        if not str(k).isdigit() or not isinstance(v, dict):
            return {"error": "page invalide"}
        e = {}
        for cle in ("ordre", "exclues", "ajouts"):
            l = []
            for r in (v.get(cle) or [])[:200]:
                bx = _dlg_box_ok((r or {}).get("box") or {})
                try:
                    i = int((r or {}).get("id"))
                except Exception:
                    i = None
                if bx is None or i is None:
                    return {"error": "zone invalide (%s, page %s)" % (cle, k)}
                l.append({"id": i, "box": bx})
            e[cle] = l
        e["t"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        doc["pages"][str(int(k))] = e
    os.makedirs(os.path.dirname(f), exist_ok=True)
    _dlg_ecrire(f, doc)
    return {"ok": True, "pages": sorted(int(k) for k in pages)}
'''
rep('''            "en_cours": _dlg_vivant(d), "distribution": _dlg_lire(os.path.join(os.path.dirname(base), "dialogues_distribution.json"))}''',
    '''            "en_cours": _dlg_vivant(d), "distribution": _dlg_lire(os.path.join(os.path.dirname(base), "dialogues_distribution.json")),
            "verif_pages": sorted(int(k) for k in (((_dlg_lire(os.path.join(dd, "bulles_verifiees.json")) or {}).get("pages")) or {}))}   # v3.1.0 (R30)''')
a = "def manga_dialogues_arreter(d):" + NL
if s.count(a) != 1:
    raise SystemExit("ancre fonction introuvable")
i = s.index(a)
s = s[:i] + FN.replace("\n", NL).lstrip(NL) + NL + NL + s[i:]

rep('''        elif self.path.split("?", 1)[0] == "/manga/dialogues_plan":
''', '''        elif self.path.split("?", 1)[0] == "/manga/dialogues_bulles":      # Manga Studio v3.1.0 (R30)
            _q = parse_qs(urlparse(self.path).query)
            self._json(200, manga_dialogues_bulles((_q.get("d") or [""])[0], (_q.get("pages") or [""])[0]))
        elif self.path.split("?", 1)[0] == "/manga/dialogues_plan":
''')
rep('''            elif self.path == "/manga/dialogues_arreter":
''', '''            elif self.path == "/manga/dialogues_verif":        # Manga Studio v3.1.0 (R30)
                self._json(200, manga_dialogues_verif(str(data.get("d") or ""), data.get("pages")))
            elif self.path == "/manga/dialogues_arreter":
''')
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
