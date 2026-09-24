# -*- coding: utf-8 -*-
"""LANGUE d'un chapitre capture (Manga Studio v2.2.0, 22/09/2026 -- Quang 12h43 : « c'est marque VO original ; j'etais sur
un chapitre deja en francais [...] j'aurais pu lancer une traduction francais vers francais »).

1. Source = un chapitre MangaDex (…/chapter/<uuid>) : l'API publique donne translatedLanguage. Exact, gratuit.
2. Sinon (MANGA Plus, page de titre MangaDex…) : Gemini lit 2 pages du milieu (pas la couverture ni les credits) et
   nomme la langue des bulles (code ISO 639-1). ~0,002 $.
Ecrit sources/<serie>/ch_N/langue.json {langue, methode, confiance, quand, cout} : detecte UNE fois.

Usage : python langue_chapitre.py <serie/ch_N> [--force]      (stdout : le JSON)
"""
import argparse, base64, json, os, re, sys, time, urllib.request
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

VERSION = "2.2.1"
SRC = os.path.normpath(os.environ.get("MANGA_SOURCES_DIR") or os.path.join(HERE, "..", "sources"))
RE_MDX = re.compile(r"mangadex\.org/chapter/([0-9a-f-]{36})")
SYS = ("Tu regardes des pages de manga. Dans quelle langue est ecrit le texte des BULLES (pas les onomatopees dessinees, "
       "pas un logo) ? Reponds en JSON : {\"langue\": \"code ISO 639-1 en minuscules (fr, en, vi, es, ja, zh, ko...)\", "
       "\"confiance\": 0.0 a 1.0} -- UN SEUL objet pour toutes les pages, rien d'autre.")


def lire(d):
    f = os.path.join(SRC, d, "langue.json")
    try:
        return json.load(open(f, encoding="utf-8"))
    except Exception:
        return None


def par_mangadex(url):
    m = RE_MDX.search(url or "")
    if not m:
        return None
    req = urllib.request.Request("https://api.mangadex.org/chapter/" + m.group(1), headers={"User-Agent": "manga-studio/" + VERSION})
    with urllib.request.urlopen(req, timeout=15) as r:
        lg = (((json.load(r).get("data") or {}).get("attributes") or {}).get("translatedLanguage") or "").lower()
    return {"langue": lg.split("-")[0], "variante": lg, "methode": "mangadex", "confiance": 1.0, "cout": 0.0} if lg else None


def par_images(cd, man):
    import narrate_chapter as nc
    nc.SECRET = nc.SECRET or nc._secret()
    fichiers = [p["file"] for p in man.get("pages") or [] if os.path.isfile(os.path.join(cd, p["file"]))]
    if not fichiers:
        raise RuntimeError("aucune page")
    choix = sorted({fichiers[len(fichiers) // 3], fichiers[len(fichiers) // 2]})
    content = []
    for f in choix:
        content.append({"type": "text", "text": "PAGE " + f})
        content.append({"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,"
                                                          + base64.b64encode(nc.page_jpeg(os.path.join(cd, f), 900)).decode()}})
    stats = {}
    # v2.2.1 : 400 tokens ne suffisaient pas -- Gemini en passait 396 a REFLECHIR et la reponse sortait coupee
    # (Boruto ch.2, 22/09 : 28 caracteres, « langue illisible »). 2000 = marge, cout < 0,01 $.
    texte, u = nc.appel_vision("gemini", SYS, content, 2000)
    # Gemini rend parfois UN objet par page (mesure 22/09 : « Extra data ») : on les lit tous, la langue majoritaire gagne
    votes = []
    for bloc in re.findall(r"\{[^{}]*\}", texte or ""):
        try:
            j = json.loads(bloc)
        except ValueError:
            continue
        lg = str(j.get("langue") or "").lower().strip()[:5].split("-")[0]
        if re.match(r"^[a-z]{2}$", lg):
            votes.append((lg, float(j.get("confiance") or 0)))
    if not votes:
        raise RuntimeError("langue illisible : %r" % (texte or "")[:80])
    lg = max({v[0] for v in votes}, key=lambda x: (sum(1 for v in votes if v[0] == x), sum(v[1] for v in votes if v[0] == x)))
    conf = round(sum(v[1] for v in votes if v[0] == lg) / len(votes), 2)
    return {"langue": lg, "variante": lg, "methode": "pages", "pages": choix, "votes": [v[0] for v in votes],
            "confiance": conf, "cout": round(nc.cout("gemini-3.6-flash", u), 5)}


def detecter(d, force=False):
    d = d.strip("/")
    cd = os.path.normpath(os.path.join(SRC, d))
    if not cd.startswith(SRC + os.sep) or not os.path.isfile(os.path.join(cd, "manifest.json")):
        raise SystemExit("chapitre introuvable : " + d)
    if not force:
        deja = lire(d)
        if deja:
            return deja
    man = json.load(open(os.path.join(cd, "manifest.json"), encoding="utf-8"))
    r = None
    try:
        r = par_mangadex(man.get("source_url"))
    except Exception as e:                      # API injoignable : on regarde les pages plutot que de ne rien dire
        r = None
        print("mangadex : %s" % e, file=sys.stderr)
    if r is None:
        r = par_images(cd, man)
    r.update(version=VERSION, quand=datetime.now().isoformat(timespec="seconds"))
    tmp = os.path.join(cd, "langue.json.tmp")
    json.dump(r, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.replace(tmp, os.path.join(cd, "langue.json"))
    return r


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("chapitre"); ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    print(json.dumps(detecter(a.chapitre, a.force), ensure_ascii=False))
