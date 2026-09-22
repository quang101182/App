# -*- coding: utf-8 -*-
"""Patch du proxy 8190 : RESUME de la bibliotheque (Manga Studio v2.1.0, 22/09/2026 -- Quang 10h58 : « en page principale
les informations simples et rapides des videos, narrations et musique presentes par manga, mais surtout par chapitre »).

GET /manga/resume -> {chapitres: {d: {narr, voix[], karaoke, video, trad[], prec}}, series: {slug: {musique, suivi, moteur}}}
Une lecture du disque ; les narration.json (seuls fichiers lourds) sont gardes en cache par date de modification.
Rejouable : python patch_resume.py <chemin du proxy>.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "def manga_resume(" in s:
    print("deja patche")
    sys.exit(0)


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


rep(r'''def manga_activite():''',
    r'''_RESUME_NARR = {}                                # chemin -> (mtime, (avec_voix, voix, karaoke))
_AUDIO_EXT = (".mp3", ".ogg", ".m4a", ".wav", ".opus", ".flac")


def _resume_narr(f):
    try:
        t = os.path.getmtime(f)
    except OSError:
        return None
    c = _RESUME_NARR.get(f)
    if c and c[0] == t:
        return c[1]
    try:
        with open(f, encoding="utf-8") as h:
            n = json.load(h)
        r = (any(p.get("audio") for p in n.get("pages") or []), n.get("voice") or "", bool((n.get("stats") or {}).get("karaoke")))
    except Exception:
        r = None
    _RESUME_NARR[f] = (t, r)
    return r


def manga_resume():
    """Ce que chaque chapitre et chaque serie possede deja (Manga Studio v2.1.0)."""
    chaps, series = {}, {}
    try:
        noms = sorted(x for x in os.listdir(MANGA_SOURCES) if not x.startswith(("_", ".")))
    except OSError:
        noms = []
    for se in noms:
        sd = os.path.join(MANGA_SOURCES, se)
        if not os.path.isdir(sd):
            continue
        md = os.path.join(sd, "musique")
        sv = {}
        try:
            with open(os.path.join(sd, "suivi.json"), encoding="utf-8") as f: sv = json.load(f)
        except Exception:
            pass
        series[se] = {"musique": len([x for x in (os.listdir(md) if os.path.isdir(md) else []) if x.lower().endswith(_AUDIO_EXT)]),
                      "suivi": bool(sv.get("actif")), "moteur": sv.get("moteur") or ""}
        for ch in os.listdir(sd):
            cd = os.path.join(sd, ch)
            if not ch.startswith("ch_") or not os.path.isfile(os.path.join(cd, "manifest.json")):
                continue
            it = {"narr": 0, "voix": [], "karaoke": False, "video": False, "trad": [], "prec": False}
            nd = os.path.join(cd, "narration")
            for tag in (os.listdir(nd) if os.path.isdir(nd) else []):
                r = _resume_narr(os.path.join(nd, tag, "narration.json"))
                if r and r[0]:
                    it["narr"] += 1
                    if r[1] and r[1] not in it["voix"]:
                        it["voix"].append(r[1])
                    it["karaoke"] = it["karaoke"] or r[2]
            vd = os.path.join(cd, "video")
            it["video"] = any(x.endswith(".mp4") for x in (os.listdir(vd) if os.path.isdir(vd) else []))
            td = os.path.join(cd, "traduction")
            it["trad"] = sorted(lg for lg in (os.listdir(td) if os.path.isdir(td) else [])
                                if os.path.isfile(os.path.join(td, lg, "traduction.json")))
            it["prec"] = os.path.isfile(os.path.join(cd, "precedemment", "ouverture.json"))
            chaps[se + "/" + ch] = it
    return {"chapitres": chaps, "series": series}


def manga_activite():''')

rep(r'''        elif self.path.split("?", 1)[0] == "/manga/activite":              # Manga Studio v1.88.0''',
    r'''        elif self.path.split("?", 1)[0] == "/manga/resume":                # Manga Studio v2.1.0
            self._json(200, manga_resume())
        elif self.path.split("?", 1)[0] == "/manga/activite":              # Manga Studio v1.88.0''')

open(p, "w", encoding="utf-8").write(s)
print("patch resume OK")
