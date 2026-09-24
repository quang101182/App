# -*- coding: utf-8 -*-
"""DOUBLE ESTIMATION « ☁ En ligne / 🖥 Sur mon PC » (feuille de route 4-undecies, 24/09/2026). v1.0.0

Quang : « partout tu m'affiches les deux estimations de cout avant de generer quoi que ce soit […] ainsi que le temps de
traitement […] dynamique selon le switch ».

Les chiffres ne sont PAS des constantes devinees : ils sont RECALCULES depuis les passages reels deja faits
(narration.json -> stats, traduction.json -> stats), mediane par page, et gardes en cache une heure dans
sources/_etalonnage.json. Tant qu'il y a moins de 3 mesures pour un poste, la valeur mesuree a la main le 24/09 sert
de repli (et l'etalonnage le dit : "source": "repli").

Ce qui change entre les deux modes (reglages.py) : la VOIX (Gemini TTS payante <-> Chatterbox sur la carte, 0 $) et
l'EFFACEMENT du texte pose sur le dessin (local, quelques secondes). L'analyse des pages, le recit, la traduction et le
karaoke restent en ligne dans les deux modes ; la video est toujours faite sur le PC (ffmpeg, 0 $).
"""
import glob, json, os, re, statistics, time

VERSION = "1.0.0"
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.environ.get("MANGA_SOURCES_DIR") or os.path.join(HERE, "..", "sources"))
CACHE = os.path.join(SRC, "_etalonnage.json")
TTL = 3600
MIN_ECH = 3

# Replis = mediane mesuree le 24/09 sur les passages reels (21 narrations Gemini, 3 Kimi, 12 traductions, voix locale OPM ch.1).
REPLI = {
    "narration": {
        "gemini": {"analyse_usd": 0.0093, "voix_usd": 0.0065, "analyse_s": 9.3, "voix_s": 2.0, "car": 216},
        "kimi":   {"analyse_usd": 0.0430, "voix_usd": 0.0069, "analyse_s": 73.5, "voix_s": 2.1, "car": 229},
    },
    "voix_pc_s_car": 0.078,         # Chatterbox + recalage du debit, chargement compris (224,6 s / 2864 car., OPM ch.1)
    "voix_pc_charge_s": 14,         # chargement du modele, une fois par chapitre
    "traduction": {"usd": 0.0090, "s": 9.5},
    "effacement_pc_s": 0.3,         # par page (3-6 s par chapitre mesures)
    "karaoke": {"usd": 0.003, "s": 60},
    "precedemment": {"usd": 0.013, "s": 60},
    "video_s": 6,                   # par page, file du proxy (0 $)
}
RE_PAGE = re.compile(r"page_\d+\.(jpe?g|png|webp)$", re.I)


def _med(v):
    return statistics.median(v) if len(v) >= MIN_ECH else None


def mesurer(src=SRC):
    """Parcourt les passages reels et rend l'etalonnage (memes cles que REPLI + d'ou vient chaque chiffre)."""
    et = json.loads(json.dumps(REPLI))
    origine = {}
    par = {}                                    # moteur -> listes par page
    voix_pc = []                                # (secondes, caracteres) des voix faites sur la carte
    for f in glob.glob(os.path.join(src, "*", "*", "narration", "*", "narration.json")):
        try:
            with open(f, encoding="utf-8") as fh:
                d = json.load(fh)
        except Exception:
            continue
        s, n, e = d.get("stats") or {}, len(d.get("pages") or []), d.get("engine")
        if not n or e not in et["narration"] or "cout_vision" not in s:
            continue
        if s.get("tts_moteur") == "local":
            if s.get("tts_s") and s.get("tts_chars"):
                voix_pc.append((s["tts_s"], s["tts_chars"]))
            continue
        if d.get("reuse_vision") or not s.get("total_s"):
            continue                            # analyse reprise : ni son cout ni sa duree ne sont representatifs
        L = par.setdefault(e, {"analyse_usd": [], "voix_usd": [], "analyse_s": [], "voix_s": [], "car": []})
        L["analyse_usd"].append((s.get("cout_vision", 0) + s.get("cout_noms", 0) + s.get("cout_recit", 0)) / n)
        L["analyse_s"].append((s["total_s"] - s.get("tts_s", 0)) / n)
        if s.get("tts_chars"):                  # un banc sans voix ne dit rien du prix de la voix
            L["voix_usd"].append(s.get("cout_tts", 0) / n)
            L["voix_s"].append(s.get("tts_s", 0) / n)
            L["car"].append(s["tts_chars"] / n)
    for e, L in par.items():
        for k, v in L.items():
            m = _med(v)
            if m is not None:
                et["narration"][e][k] = round(m, 5 if k.endswith("usd") else 1)
                origine["narration." + e + "." + k] = len(v)
    if voix_pc:
        et["voix_pc_s_car"] = round(sum(a for a, _ in voix_pc) / sum(b for _, b in voix_pc), 4)
        origine["voix_pc_s_car"] = len(voix_pc)
    tu, ts = [], []
    for f in glob.glob(os.path.join(src, "*", "*", "traduction", "*", "traduction.json")):
        try:
            with open(f, encoding="utf-8") as fh:
                s = (json.load(fh).get("stats") or {})
        except Exception:
            continue
        if not s.get("cout"):
            continue                            # re-rendu sans appel (0 $) : ne dit rien du prix
        cd = os.path.dirname(os.path.dirname(os.path.dirname(f)))
        try:
            n = len([p for p in os.listdir(cd) if RE_PAGE.match(p)])
        except OSError:
            n = 0
        if n:
            tu.append(s["cout"] / n); ts.append(s.get("s", 0) / n)
    if _med(tu) is not None:
        et["traduction"] = {"usd": round(_med(tu), 5), "s": round(_med(ts), 1)}
        origine["traduction"] = len(tu)
    et.update(version=VERSION, maj=time.strftime("%Y-%m-%dT%H:%M:%S"), origine=origine)
    return et


def etalonnage(forcer=False):
    """L'etalonnage courant (cache une heure ; un cache illisible est recalcule)."""
    if not forcer:
        try:
            if time.time() - os.path.getmtime(CACHE) < TTL:
                with open(CACHE, encoding="utf-8") as f:
                    et = json.load(f)
                if et.get("version") == VERSION:
                    return et
        except Exception:
            pass
    et = mesurer()
    try:
        tmp = CACHE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(et, f, ensure_ascii=False, indent=1)
        os.replace(tmp, CACHE)
    except OSError:
        pass
    return et


def chapitre(pages, etapes, moteur="gemini", et=None):
    """Les DEUX estimations d'un chapitre. etapes = ensemble parmi narration, karaoke, traduction, precedemment, video.
    Rend {"cloud": {usd, min}, "pc": {usd, min, gpu_min}} -- minutes = duree totale, gpu_min = carte graphique occupee."""
    et = et or etalonnage()
    n = max(0, int(pages or 0))
    nar = et["narration"].get(moteur) or et["narration"]["gemini"]
    c_usd = p_usd = c_s = p_s = gpu_s = 0.0
    if "narration" in etapes and n:
        c_usd += n * (nar["analyse_usd"] + nar["voix_usd"]); p_usd += n * nar["analyse_usd"]
        voix_pc = n * nar["car"] * et["voix_pc_s_car"] + et["voix_pc_charge_s"]
        c_s += n * (nar["analyse_s"] + nar["voix_s"]); p_s += n * nar["analyse_s"] + voix_pc; gpu_s += voix_pc
    if "traduction" in etapes and n:
        t = et["traduction"]; c_usd += n * t["usd"]; p_usd += n * t["usd"]; c_s += n * t["s"]
        eff = n * et["effacement_pc_s"]; p_s += n * t["s"] + eff; gpu_s += eff
    for k in ("karaoke", "precedemment"):
        if k in etapes:
            c_usd += et[k]["usd"]; p_usd += et[k]["usd"]; c_s += et[k]["s"]; p_s += et[k]["s"]
    if "video" in etapes and n:
        c_s += n * et["video_s"]; p_s += n * et["video_s"]
    return {"cloud": {"usd": round(c_usd, 4), "min": round(c_s / 60, 1)},
            "pc": {"usd": round(p_usd, 4), "min": round(p_s / 60, 1), "gpu_min": round(gpu_s / 60, 1)}}


if __name__ == "__main__":
    import sys
    e = etalonnage(forcer="--forcer" in sys.argv)
    print(json.dumps(e, ensure_ascii=False, indent=1))
    print("OPM 24 p. narration+karaoke+video :", chapitre(24, {"narration", "karaoke", "video"}, "gemini", e))
