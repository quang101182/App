# -*- coding: utf-8 -*-
"""Narration d'un chapitre de sources/ : pages -> comprehension -> recit FR -> voix.

Consomme le format de manga-fetch (sources/<slug>/ch_<num>/ + manifest.json) et
ecrit TOUT son resultat SOUS ce meme dossier (sources/ est gitignore : ni les
pages ni les recits derives ne doivent entrer dans le depot App, qui est public).

Trois etapes, chacune mesuree (duree, tokens, cout) dans narration.json :
  1. VISION   : les pages par lots (4 par defaut) + un resume glissant de ce qui
                precede -> pour chaque page : type (histoire / credits / pub /
                couverture), faits observes, premiere narration. Moteurs : Pixtral
                (offre gratuite Mistral) ou Kimi K3 (payant, mieux mesure le 21/09 :
                Pixtral a lu une scene de cadavre comme "une explosion d'enfants").
  2. RECIT    : DeepSeek V4 Flash reecrit l'ensemble en UN recit continu, page par
                page (la segmentation reste celle des pages : c'est elle que le
                lecteur synchronise). Consigne centrale, tiree des forums : RACONTER,
                ne pas decrire l'ecran ; paraphraser, ne pas recopier les repliques.
  3. VOIX     : Google Chirp 3 HD fr-FR, une piste MP3 par page + sa duree.

Usage (depuis le venv kohya, qui a Pillow) :
    python narrate_chapter.py claymore/ch_1 --engine kimi --pages 1-20 --voice Charon
    python narrate_chapter.py claymore/ch_1 --engine pixtral --no-tts
Stdout : un seul objet JSON (le resume du run). Le bruit part sur stderr.
"""
import argparse, base64, io, json, os, re, subprocess, sys, time, urllib.request, urllib.error
from datetime import datetime

VERSION = "1.67.0"
HERE = os.path.dirname(os.path.abspath(__file__))
SOURCES = os.path.normpath(os.path.join(HERE, "..", "sources"))
GATEWAY = "https://api-gateway.quang101182.workers.dev"
LOGF = os.path.join(os.environ.get("LOCALAPPDATA", HERE), "manga-studio", "narration.log")

# Tarifs $/Mtok (entree, sortie). Pixtral : offre gratuite (plafonnee) ; si elle passe
# payante, le cout affiche sera faux dans le bon sens (sous-estime) -> a surveiller.
PRIX = {"pixtral-12b-latest": (0.0, 0.0), "kimi-k3": (3.0, 15.0), "deepseek-v4-flash": (0.30, 1.20)}
PRIX_TTS_CHAR = 30.0 / 1e6        # Chirp 3 HD, ~30 $/M caracteres (valeur deja retenue par smart-reader)
ENGINES = {"pixtral": ("/api/mistral", "pixtral-12b-latest"), "kimi": ("/api/kimi", "kimi-k3")}


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def journal(ev, **kw):
    """Journal persistant (jsonl) : une trace par etape, lisible sans relancer."""
    try:
        os.makedirs(os.path.dirname(LOGF), exist_ok=True)
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(json.dumps(dict(t=datetime.now().isoformat(timespec="seconds"), ev=ev, **kw),
                               ensure_ascii=False) + "\n")
    except Exception:
        pass


PROGRESS = None


def progres(etape, fait, total, **kw):
    """progress.json a cote du resultat : ce que l'app lit pour sa barre de progression."""
    if not PROGRESS:
        return
    try:
        with open(PROGRESS, "w", encoding="utf-8") as f:
            json.dump(dict(etape=etape, fait=fait, total=total, t=time.time(), **kw), f, ensure_ascii=False)
    except Exception:
        pass


def _secret():
    s = os.environ.get("WORKER_SECRET", "").strip()
    if s:
        return s
    p = os.path.join(os.path.expanduser("~"), "Documents", "ComfyUI", ".worker_secret")
    if os.path.isfile(p):
        v = open(p, encoding="utf-8").read().strip()
        if v:
            return v
    raise SystemExit("ARRET : secret du gateway introuvable (WORKER_SECRET ou ComfyUI/.worker_secret).")


SECRET = None


# Le gateway limite a 20 requetes/min PAR IP, fenetre fixe alignee sur la minute, compteur KV
# "fire-and-forget" (App/api-gateway/src/index.js) -> on vise 18, pas 20. Sans ce frein, la voix
# d'un chapitre de 62 pages (62 appels a ~1 s) prenait des 429 : constate au banc du 21/09.
MAX_PAR_MIN = 18
_APPELS = []


def _frein():
    while True:
        now = time.time()
        while _APPELS and now - _APPELS[0] > 60:
            _APPELS.pop(0)
        if len(_APPELS) < MAX_PAR_MIN:
            _APPELS.append(now)
            return
        time.sleep(60 - (now - _APPELS[0]) + 0.5)


def post(path, body, timeout=240):
    req = urllib.request.Request(GATEWAY + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + SECRET,
                                          "User-Agent": "manga-studio/" + VERSION})
    last = None
    for essai in range(5):
        _frein()
        attente = 4 * (essai + 1)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            brut = e.read()[:300].decode("utf-8", "replace")
            last = "HTTP %d %s" % (e.code, brut[:200])
            if e.code not in (429, 500, 502, 503, 504):
                break
            if e.code == 429:           # le gateway dit combien attendre : on l'ecoute (60 s en pratique)
                try:
                    attente = float(json.loads(brut).get("retry_after") or 60) + 1
                except Exception:
                    attente = 61
                journal("429", path=path, attente=attente)
                log("  429 sur %s : pause %.0f s" % (path, attente))
        except Exception as e:          # timeout reseau, coupure
            last = str(e)
        time.sleep(attente)
    raise RuntimeError(path + " : " + str(last))


def parse_json(txt):
    """Le modele entoure parfois son JSON de ``` ou de prose : on prend l'objet le plus large."""
    t = (txt or "").strip()
    a, b = t.find("{"), t.rfind("}")
    if a < 0 or b <= a:
        raise ValueError("pas de JSON dans la reponse : " + t[:200])
    return json.loads(t[a:b + 1])


def cout(model, usage):
    pi, po = PRIX.get(model, (0, 0))
    return (usage.get("prompt_tokens", 0) * pi + usage.get("completion_tokens", 0) * po) / 1e6


def page_jpeg(path, largeur=1000):
    """Page reduite a 1000 px de large : ~1 000 tokens image au lieu de ~2 000, texte des bulles
    encore lisible (mesure sonde 21/09 sur Claymore 1080x1620)."""
    from PIL import Image
    im = Image.open(path).convert("RGB")
    if im.width > largeur:
        im = im.resize((largeur, round(im.height * largeur / im.width)), Image.LANCZOS)
    b = io.BytesIO()
    im.save(b, "JPEG", quality=85)
    return b.getvalue()


SYS_VISION = """Tu es un conteur de recaps manga (style video "manga recap" en francais).
Tu recois des PAGES CONSECUTIVES d'un chapitre, dans l'ordre de lecture, et le resume de ce qui precede.
Les bulles peuvent etre en anglais ou en japonais : comprends-les, mais NE LES RECOPIE PAS.

Pour CHAQUE page recue, dans l'ordre, donne :
- "type" : "histoire" | "credits" (page de l'equipe de traduction/scan, remerciements, recrutement) | "pub" | "couverture" (titre du chapitre sans action)
- "faits" : ce qui se passe reellement, factuel et precis (qui, quoi, ou, pourquoi) en 1-3 phrases. C'est ta preuve de lecture.
- "narration" : 1 a 3 phrases en francais, au PRESENT, voix de conteur. On RACONTE l'histoire (tension, enjeux,
  consequences), on ne decrit pas l'image ("on voit", "sur cette page", "la case montre" sont INTERDITS).
  Paraphrase toujours : aucune replique citee mot pour mot. Vide si type != histoire.

Puis :
- "resume" : resume de TOUTE l'histoire jusqu'a la derniere page recue (max 120 mots), pour le lot suivant.
- "personnages" : liste {nom, qui} des personnages identifies (nom tel qu'ecrit dans le manga ; sinon un surnom
  descriptif stable comme "le garcon aux cheveux clairs"). Reprends les noms deja connus, ne les change pas.

Reponds UNIQUEMENT par un objet JSON :
{"pages":[{"page":N,"type":"...","faits":"...","narration":"..."}],"resume":"...","personnages":[{"nom":"...","qui":"..."}]}"""

SYS_RECIT = """Tu es le narrateur d'une video "manga recap" en francais. On te donne, page par page, les faits
observes et une premiere narration d'un chapitre. Reecris la NARRATION de chaque page pour que l'ensemble,
lu a voix haute a la suite, forme UN recit fluide et captivant :
- present de narration, phrases courtes et orales, rythme (tension, chute, cliffhanger en fin de chapitre) ;
- enchaine les pages (pas de redite, pas de "ensuite" mecanique), garde les memes noms de personnages ;
- RACONTE, ne decris pas l'ecran : "on voit", "cette page", "la case" sont interdits ;
- paraphrase : aucune replique recopiee mot pour mot ;
- reste fidele aux faits : n'invente ni evenement ni nom ;
- une page peut rester muette ("") si elle n'apporte rien ; vise en moyenne 1 a 3 phrases par page.
Reponds UNIQUEMENT par un JSON : {"titre":"accroche courte du chapitre","pages":[{"page":N,"narration":"..."}]}
avec EXACTEMENT les memes numeros de page que l'entree, dans le meme ordre."""


def etape_vision(chap_dir, pages, engine, batch, stats):
    path, model = ENGINES[engine]
    resume, persos, sortie = "", [], []
    for i in range(0, len(pages), batch):
        lot = pages[i:i + batch]
        nums = [p["num"] for p in lot]
        ctx = ("Resume de ce qui precede : " + (resume or "(debut du chapitre)")
               + "\nPersonnages deja identifies : " + (json.dumps(persos, ensure_ascii=False) if persos else "(aucun)")
               + "\nPages recues dans l'ordre : " + ", ".join(map(str, nums)))
        content = [{"type": "text", "text": ctx}]
        for p in lot:
            b64 = base64.b64encode(page_jpeg(os.path.join(chap_dir, p["file"]))).decode()
            content.append({"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + b64}})
        body = {"model": model, "max_tokens": 6000,
                "messages": [{"role": "system", "content": SYS_VISION}, {"role": "user", "content": content}]}
        if engine == "pixtral":
            body["temperature"] = 0.3
        t = time.time()
        j = None
        for essai in range(2):             # une reponse non-JSON = on redemande une fois, pas plus
            r = post(path, body)
            u = r.get("usage") or {}
            stats["vision_tokens_in"] += u.get("prompt_tokens", 0)
            stats["vision_tokens_out"] += u.get("completion_tokens", 0)
            stats["cout_vision"] += cout(model, u)
            try:
                j = parse_json(r["choices"][0]["message"].get("content"))
                break
            except Exception as e:
                log("  lot %s : JSON illisible (%s), nouvel essai" % (nums, e))
        dt = time.time() - t
        if j is None:
            raise RuntimeError("lot %s : JSON illisible deux fois" % nums)
        recus = {int(x.get("page", 0)): x for x in j.get("pages", []) if str(x.get("page", "")).isdigit()}
        # Le modele numerote parfois 1..n dans le lot au lieu des vrais numeros : on remappe par position.
        if not set(nums) <= set(recus) and len(j.get("pages", [])) == len(lot):
            recus = {n: x for n, x in zip(nums, j["pages"])}
        for p in lot:
            x = recus.get(p["num"]) or {"type": "histoire", "faits": "", "narration": ""}
            sortie.append({"page": p["num"], "file": p["file"], "type": x.get("type", "histoire"),
                           "faits": x.get("faits", ""), "narration": x.get("narration", "")})
        resume = j.get("resume", resume) or resume
        persos = j.get("personnages", persos) or persos
        stats["vision_s"] += dt
        progres("vision", min(i + batch, len(pages)), len(pages))
        journal("vision_lot", engine=engine, pages=nums, s=round(dt, 1))
        log("  vision %s pages %s : %.1fs" % (engine, nums, dt))
    return sortie, resume, persos


def etape_recit(pages, resume, persos, stats):
    entree = [{"page": p["page"], "type": p["type"], "faits": p["faits"], "narration": p["narration"]}
              for p in pages if p["type"] == "histoire"]
    if not entree:
        return "", pages
    body = {"model": "deepseek-v4-flash", "max_tokens": 8000, "temperature": 0.7,
            "thinking": {"type": "disabled"},
            "messages": [{"role": "system", "content": SYS_RECIT},
                         {"role": "user", "content": "Personnages : " + json.dumps(persos, ensure_ascii=False)
                          + "\nResume final : " + resume
                          + "\nPages :\n" + json.dumps(entree, ensure_ascii=False)}]}
    t = time.time()
    r = post("/api/deepseek", body)
    u = r.get("usage") or {}
    stats["cout_recit"] += cout("deepseek-v4-flash", u)
    stats["recit_s"] += time.time() - t
    j = parse_json(r["choices"][0]["message"].get("content"))
    neuf = {int(x["page"]): x.get("narration", "") for x in j.get("pages", []) if "page" in x}
    manquantes = [p["page"] for p in entree if p["page"] not in neuf]
    if manquantes:                       # on garde la narration d'origine plutot que du silence
        log("  recit : pages non rendues %s -> narration vision conservee" % manquantes)
    for p in pages:
        p["narration_vision"] = p["narration"]
        if p["type"] != "histoire":
            p["narration"] = ""
        elif p["page"] in neuf:
            p["narration"] = neuf[p["page"]]
    journal("recit", s=round(stats["recit_s"], 1), manquantes=manquantes)
    return j.get("titre", ""), pages


def duree_mp3(path):
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                              "-of", "default=nw=1:nk=1", path], capture_output=True, text=True, timeout=30)
        return round(float(out.stdout.strip()), 2)
    except Exception:
        return None


def etape_voix(pages, outdir, voice, rate, stats):
    os.makedirs(outdir, exist_ok=True)
    for p in pages:
        p["audio"], p["dur"] = None, 0.0
        txt = (p.get("narration") or "").strip()
        if not txt:
            continue
        body = {"input": {"text": txt}, "voice": {"languageCode": "fr-FR", "name": "fr-FR-Chirp3-HD-" + voice},
                "audioConfig": {"audioEncoding": "MP3", "speakingRate": rate}}
        t = time.time()
        r = post("/api/gcptts/v1/text:synthesize", body, timeout=90)
        f = "p%03d.mp3" % p["page"]
        with open(os.path.join(outdir, f), "wb") as fh:
            fh.write(base64.b64decode(r["audioContent"]))
        p["audio"], p["dur"] = f, duree_mp3(os.path.join(outdir, f)) or 0.0
        stats["tts_chars"] += len(txt)
        stats["tts_s"] += time.time() - t
        progres("voix", p["page"], pages[-1]["page"])
    stats["cout_tts"] = stats["tts_chars"] * PRIX_TTS_CHAR


def pages_du_chapitre(chap_dir, plage):
    man = json.load(open(os.path.join(chap_dir, "manifest.json"), encoding="utf-8"))
    files = [p["file"] for p in man.get("pages", []) if os.path.isfile(os.path.join(chap_dir, p["file"]))]
    pages = [{"num": i + 1, "file": f} for i, f in enumerate(files)]
    if plage:
        a, _, b = plage.partition("-")
        a, b = int(a), int(b or a)
        pages = [p for p in pages if a <= p["num"] <= b]
    return man, pages


def main():
    global SECRET, PROGRESS
    ap = argparse.ArgumentParser()
    ap.add_argument("chapitre", help="chemin relatif sous sources/, ex. claymore/ch_1")
    ap.add_argument("--engine", choices=sorted(ENGINES), default="kimi")
    ap.add_argument("--pages", default="", help="plage, ex. 1-20 (defaut : tout)")
    ap.add_argument("--batch", type=int, default=4)
    ap.add_argument("--voice", default="Charon", help="voix Chirp 3 HD fr-FR (Charon, Fenrir, Orus, Kore...)")
    ap.add_argument("--rate", type=float, default=1.05)
    ap.add_argument("--tag", default="", help="nom du run (defaut : <engine>-<voix>)")
    ap.add_argument("--no-tts", action="store_true")
    ap.add_argument("--reuse-vision", default="", help="reprend l'etape vision d'un run existant (tag)")
    a = ap.parse_args()
    SECRET = _secret()

    chap_dir = os.path.normpath(os.path.join(SOURCES, a.chapitre))
    if not chap_dir.startswith(SOURCES + os.sep) or not os.path.isfile(os.path.join(chap_dir, "manifest.json")):
        raise SystemExit("chapitre introuvable sous sources/ : " + a.chapitre)
    tag = a.tag or "%s-%s" % (a.engine, a.voice.lower())
    outdir = os.path.join(chap_dir, "narration", tag)
    os.makedirs(outdir, exist_ok=True)
    PROGRESS = os.path.join(outdir, "progress.json")
    man, pages = pages_du_chapitre(chap_dir, a.pages)
    stats = dict(vision_tokens_in=0, vision_tokens_out=0, cout_vision=0.0, cout_recit=0.0, cout_tts=0.0,
                 tts_chars=0, vision_s=0.0, recit_s=0.0, tts_s=0.0)
    journal("start", chapitre=a.chapitre, engine=a.engine, pages=len(pages), tag=tag)
    t0 = time.time()

    if a.reuse_vision:
        prev = json.load(open(os.path.join(chap_dir, "narration", a.reuse_vision, "narration.json"), encoding="utf-8"))
        vis = [dict(page=p["page"], file=p["file"], type=p["type"], faits=p["faits"],
                    narration=p.get("narration_vision", p["narration"])) for p in prev["pages"]]
        resume, persos = prev.get("resume", ""), prev.get("personnages", [])
        for k in ("vision_tokens_in", "vision_tokens_out", "cout_vision", "vision_s"):
            stats[k] = prev["stats"][k]
    else:
        vis, resume, persos = etape_vision(chap_dir, pages, a.engine, a.batch, stats)
    progres("recit", 0, 1)
    try:
        titre, vis = etape_recit(vis, resume, persos, stats)
    except Exception as e:              # le recit est un polissage : sans lui, la narration vision reste lisible
        log("  recit en echec (%s) : narration vision conservee" % e)
        journal("recit_echec", err=str(e)[:200])
        titre = ""
    if not a.no_tts:
        etape_voix(vis, outdir, a.voice, a.rate, stats)
    stats["total_s"] = round(time.time() - t0, 1)
    stats["cout_total"] = round(stats["cout_vision"] + stats["cout_recit"] + stats["cout_tts"], 4)
    res = {"version": VERSION, "chapitre": a.chapitre, "title": man.get("title"), "chapter": man.get("chapter"),
           "tag": tag, "engine": a.engine, "model": ENGINES[a.engine][1], "voice": a.voice, "rate": a.rate,
           "titre": titre, "resume": resume, "personnages": persos, "created_at": datetime.now().isoformat(timespec="seconds"),
           "stats": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in stats.items()},
           "pages": vis}
    with open(os.path.join(outdir, "narration.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    progres("fini", 1, 1, cout=stats["cout_total"])
    journal("done", tag=tag, cout=stats["cout_total"], s=stats["total_s"])
    print(json.dumps({"ok": True, "dir": os.path.relpath(outdir, SOURCES).replace("\\", "/"),
                      "pages": len(vis), "stats": res["stats"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
