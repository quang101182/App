# -*- coding: utf-8 -*-
"""Patch du proxy 8190 : ACTIVITE en cours de tout Manga Studio (v1.88.0, 22/09/2026, demande Quang 05h12).

GET /manga/activite -> {items:[{type, d, titre, chapitre, tag|langue, etape, fait, total}], t}
  Tous les chapitres, pas seulement celui ouvert : plusieurs narrations / traductions peuvent tourner a la fois.
  REUTILISE manga_narrations() / manga_traductions() / manga_fetch_status() : la cellule d'en-tete montre
  exactement ce que montre le chapitre, sans regle d'etat dupliquee.
Karaoke : _kar_vivant() lit aussi karaoke_progress.json (ecrit par karaoke_mots.py v1.88) -> l'etat survit a
  un redemarrage du proxy, comme la narration et la traduction (regle des 3 min).
Rejouable : python patch_activite.py <chemin du proxy>. Suppose patch_karaoke.py + patch_traduction.py appliques.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "def manga_activite(" in s:
    print("deja patche")
    sys.exit(0)


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


rep('''def _kar_vivant(d, tag):
    p = _KAR_JOBS.get((d.strip("/"), tag))
    return bool(p and p.poll() is None)''',
    '''def _kar_vivant(d, tag):
    p = _KAR_JOBS.get((d.strip("/"), tag))
    if p is not None:
        return p.poll() is None
    # v1.88.0 : lance avant un redemarrage du proxy -> on lit sa progression (vivante si < 3 min)
    td = _narr_dir(d, tag)
    try:
        with open(os.path.join(td, "karaoke_progress.json"), encoding="utf-8") as f:
            pr = json.load(f)
        return not pr.get("fini") and time.time() - float(pr.get("t") or 0) < 180
    except Exception:
        return False


def _kar_progress(d, tag):
    try:
        with open(os.path.join(_narr_dir(d, tag), "karaoke_progress.json"), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def manga_activite():
    """Tout ce qui travaille en ce moment, tous chapitres confondus (Manga Studio v1.88.0)."""
    out = []
    try:
        series = sorted(x for x in os.listdir(MANGA_SOURCES) if not x.startswith("_"))
    except OSError:
        series = []
    for se in series:
        sd = os.path.join(MANGA_SOURCES, se)
        if not os.path.isdir(sd):
            continue
        for ch in sorted(os.listdir(sd)):
            man = os.path.join(sd, ch, "manifest.json")
            if not os.path.isfile(man):
                continue
            d = se + "/" + ch
            nd, td = os.path.join(sd, ch, "narration"), os.path.join(sd, ch, "traduction")
            if not os.path.isdir(nd) and not os.path.isdir(td):
                continue
            try:
                with open(man, encoding="utf-8") as f:
                    m = json.load(f)
            except Exception:
                m = {}
            base = {"d": d, "titre": m.get("title") or se, "chapitre": str(m.get("chapter") or ch)}
            for it in ((manga_narrations(d) or {}).get("items") or []) if os.path.isdir(nd) else []:
                pr = it.get("progress") or {}
                if it.get("etat") == "en cours":
                    out.append(dict(base, type="narration", tag=it.get("tag"), etape=pr.get("etape"),
                                    fait=pr.get("fait"), total=pr.get("total")))
                if it.get("karaoke_en_cours"):
                    kp = _kar_progress(d, it.get("tag"))
                    out.append(dict(base, type="karaoke", tag=it.get("tag"), fait=kp.get("fait"), total=kp.get("total")))
            for it in ((manga_traductions(d) or {}).get("items") or []) if os.path.isdir(td) else []:
                if it.get("etat") == "en cours":
                    pr = it.get("progress") or {}
                    out.append(dict(base, type="traduction", langue=it.get("langue"), fait=pr.get("fait"), total=pr.get("total")))
    try:
        fs = manga_fetch_status()
        if fs.get("etat") == "en cours":
            out.append({"type": "capture", "titre": fs.get("titre"), "chapitre": str(fs.get("chapitre") or ""),
                        "fait": fs.get("pages"), "total": None, "d": None})
    except Exception:
        pass
    return {"items": out, "t": time.time()}''')

rep('''        elif self.path.split("?", 1)[0] == "/manga/musiques":              # Manga Studio v1.85.0''',
    '''        elif self.path.split("?", 1)[0] == "/manga/activite":              # Manga Studio v1.88.0
            self._json(200, manga_activite())
        elif self.path.split("?", 1)[0] == "/manga/musiques":              # Manga Studio v1.85.0''')

open(p, "w", encoding="utf-8").write(s)
print("patch activite OK")
