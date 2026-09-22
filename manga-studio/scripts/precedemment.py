# -*- coding: utf-8 -*-
"""« Precedemment... » et RATTRAPAGE d'un chapitre (Manga Studio v1.94.0, 22/09/2026, etape 7).

Decision Quang (22/09 08h40) : les deux formes.
  ouverture  : ~30-45 s avant le ch. N, ce qu'il faut avoir en tete (surtout le chapitre juste avant).
  rattrapage : les chapitres 1 -> N-1 de la serie, un court paragraphe par chapitre (reprendre apres une pause).

Source : le RECIT deja ecrit de chaque chapitre precedent (pages[].narration de sa narration la plus recente
avec voix, sinon la plus recente tout court) -- jamais les images : 0 lecture, donc aucune nouvelle erreur de
« qui est qui ». Resume DeepSeek V4 Flash SANS ajout (seuls les faits du texte), voix Chirp 3 HD.
Ecrit sous sources/<serie>/ch_N/precedemment/ :  <mode>.json (+ progress.json pendant) et ses MP3.
Chaque JSON garde ses SOURCES (chapitre, tag, created_at) : l'app sait qu'il est perime si l'une a change.

Usage : python precedemment.py <serie/ch_N> --mode ouverture|rattrapage [--voice Charon] [--rate 1.05]
"""
import argparse, base64, json, os, sys, time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import narrate_chapter as nc          # GATEWAY, secret, frein 18/min, post(), duree_mp3, tarifs

VERSION = "1.94.0"
SRC = nc.SOURCES
# Longueur visee (mots). ~2,4 mots/s a 1,05 : 90 mots ~ 40 s. Rattrapage : par chapitre.
MOTS = {"ouverture": 90, "rattrapage": 110}

SYS = """Tu es le narrateur d'une lecture à voix haute de manga, en français.
On te donne le RÉCIT déjà écrit de chapitres précédents. Tu écris un résumé à dire à voix haute.
RÈGLES ABSOLUES :
- N'AJOUTE RIEN : chaque fait, chaque nom, chaque lien entre personnages doit être DANS le texte fourni.
  Pas de déduction, pas de motivation inventée, pas d'anticipation de la suite.
- Garde les noms EXACTEMENT comme écrits. Un personnage sans nom reste anonyme (« un villageois »).
- Raconte (passé composé ou présent de narration), phrases courtes, faciles à suivre à l'oreille.
- Français correct avec tous ses accents. Pas de titre, pas de liste, pas de dialogue entre guillemets, pas de numéro de page."""

CONSIGNE = {
    "ouverture": ("Écris le « Précédemment… » à dire juste AVANT le chapitre {n}. Commence par « Précédemment, ». "
                  "AU PLUS {mots} mots — un résumé, pas une réécriture. Concentre-toi sur le chapitre le plus récent (ce qu'on doit avoir en tête "
                  "pour comprendre la suite, surtout la situation à la fin) ; les chapitres plus anciens : une phrase "
                  "de contexte au plus. Réponds en JSON : {{\"texte\": \"...\"}}"),
    "rattrapage": ("Écris un RATTRAPAGE : un paragraphe par chapitre fourni, dans l'ordre, AU PLUS {mots} mots "
                   "chacun — c'est un RÉSUMÉ de l'essentiel, surtout pas une réécriture du récit —, pour qu'on reprenne la série au chapitre {n} sans rien relire. Chaque paragraphe commence "
                   "par « Chapitre X. ». Réponds en JSON : {{\"chapitres\": [{{\"chapitre\": \"X\", \"texte\": \"...\"}}]}}"),
}


def chap_key(c):
    try:
        return (0, float(c), "")
    except (TypeError, ValueError):
        return (1, 0.0, str(c))


def narration_retenue(chap_dir):
    """La narration la plus recente AVEC voix (celle que le lecteur et la video prennent), sinon la plus recente."""
    nd, best = os.path.join(chap_dir, "narration"), []
    for tag in (os.listdir(nd) if os.path.isdir(nd) else []):
        f = os.path.join(nd, tag, "narration.json")
        if not os.path.isfile(f):
            continue
        try:
            n = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        pages = [p for p in n.get("pages") or [] if (p.get("narration") or "").strip()]
        if not pages:
            continue
        audio = any(p.get("audio") for p in pages)
        best.append((audio, n.get("created_at") or "", tag, n, pages))
    if not best:
        return None
    best.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return best[0]


def chapitres_precedents(serie_dir, num):
    out = []
    for ch in os.listdir(serie_dir):
        cd = os.path.join(serie_dir, ch)
        if not ch.startswith("ch_") or not os.path.isfile(os.path.join(cd, "manifest.json")):
            continue
        man = json.load(open(os.path.join(cd, "manifest.json"), encoding="utf-8"))
        c = str(man.get("chapter") or ch[3:])
        if chap_key(c) >= chap_key(num):
            continue
        r = narration_retenue(cd)
        out.append({"ch": ch, "chapitre": c, "narr": r})
    return sorted(out, key=lambda x: chap_key(x["chapitre"]))


def image_de(serie, ch, pages, derniere):
    """L'image montree pendant le resume : la derniere page d'histoire (ouverture) ou la premiere (rattrapage)."""
    h = [p for p in pages if p.get("type", "histoire") == "histoire" and p.get("file")]
    if not h:
        return None
    return serie + "/" + ch + "/" + (h[-1] if derniere else h[0])["file"]


def voix(txt, dest, voice, rate, stats):
    body = {"input": {"text": txt}, "voice": {"languageCode": "fr-FR", "name": "fr-FR-Chirp3-HD-" + voice},
            "audioConfig": {"audioEncoding": "MP3", "speakingRate": rate}}
    r = nc.post("/api/gcptts/v1/text:synthesize", body, timeout=90)
    with open(dest, "wb") as fh:
        fh.write(base64.b64decode(r["audioContent"]))
    stats["tts_chars"] += len(txt)
    stats["cout_tts"] += len(txt) * nc.PRIX_TTS_CHAR
    return nc.duree_mp3(dest) or 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("chapitre", help="serie/ch_N sous sources/")
    ap.add_argument("--mode", choices=sorted(MOTS), default="ouverture")
    ap.add_argument("--voice", default="Charon")
    ap.add_argument("--rate", type=float, default=1.05)
    ap.add_argument("--dry", action="store_true", help="texte seulement (pas de voix), rien d'ecrit : pour le banc")
    a = ap.parse_args()
    nc.SECRET = nc._secret()

    chap_dir = os.path.normpath(os.path.join(SRC, a.chapitre))
    if not chap_dir.startswith(SRC + os.sep) or not os.path.isfile(os.path.join(chap_dir, "manifest.json")):
        raise SystemExit("chapitre introuvable : " + a.chapitre)
    serie, ch = a.chapitre.strip("/").split("/")[:2]
    man = json.load(open(os.path.join(chap_dir, "manifest.json"), encoding="utf-8"))
    num = str(man.get("chapter") or ch[3:])
    outdir = os.path.join(chap_dir, "precedemment")
    os.makedirs(outdir, exist_ok=True)
    nc.PROGRESS = None if a.dry else os.path.join(outdir, a.mode + ".progress.json")
    stats = {"cout_recit": 0.0, "cout_tts": 0.0, "tts_chars": 0}
    nc.STATS = stats
    t0 = time.time()
    nc.progres("resume", 0, 1)

    prec = chapitres_precedents(os.path.dirname(chap_dir), num)
    avec = [x for x in prec if x["narr"]]
    manquants = [x["chapitre"] for x in prec if not x["narr"]]
    if not avec:
        nc.progres("fini", 1, 1, err="aucun chapitre precedent narre")
        raise SystemExit("aucun chapitre precedent narre pour " + a.chapitre)
    if a.mode == "ouverture":
        avec = avec[-3:]                       # au-dela, une phrase de contexte n'apporte plus rien
    corps = "\n\n".join("=== Chapitre %s ===\n%s" % (x["chapitre"], " ".join(p["narration"].strip() for p in x["narr"][4]))
                        for x in avec)
    body = {"model": "deepseek-v4-flash", "max_tokens": 4000, "temperature": 0.3, "thinking": {"type": "disabled"},
            "messages": [{"role": "system", "content": SYS},
                         {"role": "user", "content": CONSIGNE[a.mode].format(n=num, mots=MOTS[a.mode]) + "\n\n" + corps}]}
    j = None
    for essai in range(2):              # banc 22/09 : 1er jet du rattrapage = le chapitre recopie (600 mots / 110)
        r = nc.post("/api/deepseek", body)
        stats["cout_recit"] += nc.cout("deepseek-v4-flash", r.get("usage") or {})
        j = nc.parse_json(r["choices"][0]["message"].get("content"))
        textes = [j.get("texte") or ""] if a.mode == "ouverture" else [c.get("texte") or "" for c in j.get("chapitres") or []]
        trop = max([len(t.split()) for t in textes] or [0])
        if trop <= 2 * MOTS[a.mode]:
            break
        nc.log("  resume trop long (%d mots, cible %d) : nouvelle demande" % (trop, MOTS[a.mode]))
        body["messages"].append({"role": "assistant", "content": r["choices"][0]["message"].get("content") or ""})
        body["messages"].append({"role": "user", "content": "Beaucoup trop long (%d mots). Recommence : AU PLUS %d mots "
                                 "par texte, l'essentiel seulement, même format JSON." % (trop, MOTS[a.mode])})
    if a.mode == "ouverture":
        x = avec[-1]
        items = [{"chapitre": x["chapitre"], "narration": (j.get("texte") or "").strip(),
                  "img": image_de(serie, x["ch"], x["narr"][3].get("pages") or [], True)}]
    else:
        par = {str(c.get("chapitre")).strip(): (c.get("texte") or "").strip() for c in j.get("chapitres") or []}
        items = [{"chapitre": x["chapitre"], "narration": par.get(x["chapitre"], ""),
                  "img": image_de(serie, x["ch"], x["narr"][3].get("pages") or [], False)} for x in avec]
    vides = [it["chapitre"] for it in items if not it["narration"]]
    if vides:
        raise SystemExit("resume vide pour le(s) chapitre(s) " + ", ".join(vides))
    if a.dry:
        print(json.dumps({"items": items, "stats": stats}, ensure_ascii=False, indent=1))
        return

    for k, it in enumerate(items):
        nc.progres("voix", k, len(items))
        f = "%s_%02d.mp3" % (a.mode, k + 1)
        it["audio"], it["dur"] = f, voix(it["narration"], os.path.join(outdir, f), a.voice, a.rate, stats)
    stats["total_s"] = round(time.time() - t0, 1)
    stats["cout_total"] = round(stats["cout_recit"] + stats["cout_tts"], 5)
    res = {"version": VERSION, "mode": a.mode, "chapitre": a.chapitre.strip("/"), "numero": num, "voice": a.voice,
           "rate": a.rate, "created_at": datetime.now().isoformat(timespec="seconds"),
           "sources": [{"ch": x["ch"], "chapitre": x["chapitre"], "tag": x["narr"][2], "created_at": x["narr"][1]}
                       for x in avec],
           "sans_narration": manquants, "stats": {k: round(v, 5) if isinstance(v, float) else v for k, v in stats.items()},
           "items": items}
    # les anciens MP3 de ce mode qui ne servent plus (rattrapage plus court qu'avant)
    garde = {it["audio"] for it in items}
    for fn in os.listdir(outdir):
        if fn.startswith(a.mode + "_") and fn.endswith(".mp3") and fn not in garde:
            os.remove(os.path.join(outdir, fn))
    with open(os.path.join(outdir, a.mode + ".json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    nc.progres("fini", 1, 1, cout=stats["cout_total"])
    nc.journal("precedemment", chapitre=a.chapitre, mode=a.mode, cout=stats["cout_total"], s=stats["total_s"])
    print(json.dumps({"ok": True, "mode": a.mode, "items": len(items), "stats": res["stats"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
