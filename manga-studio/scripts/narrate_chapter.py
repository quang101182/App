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
  3. VOIX     : Google Chirp 3 HD fr-FR (en-US avec --langue en, v2.0.0), une piste MP3 par page + sa duree.

Usage (depuis le venv kohya, qui a Pillow) :
    python narrate_chapter.py claymore/ch_1 --engine kimi --pages 1-20 --voice Charon
    python narrate_chapter.py claymore/ch_1 --engine pixtral --no-tts
Stdout : un seul objet JSON (le resume du run). Le bruit part sur stderr.
"""
import argparse, base64, io, json, os, re, subprocess, sys, threading, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import moderation as mod             # v2.6.0 : refus reconnus, alertes persistantes
import depenses as dep               # v2.6.0 : registre des depenses en ajout seul
from datetime import datetime

VERSION = "2.9.0"
HERE = os.path.dirname(os.path.abspath(__file__))
SOURCES = os.path.normpath(os.environ.get("MANGA_SOURCES_DIR") or os.path.join(HERE, "..", "sources"))
GATEWAY = "https://api-gateway.quang101182.workers.dev"
LOGF = os.path.join(os.environ.get("LOCALAPPDATA", HERE), "manga-studio", "narration.log")

# Tarifs $/Mtok (entree, sortie). Pixtral : offre gratuite (plafonnee) ; si elle passe
# payante, le cout affiche sera faux dans le bon sens (sous-estime) -> a surveiller.
# gemini-3.6-flash : tarif de LANCEMENT jusqu'au 31/12/2026 (0,75 / 3,75), puis 1,50 / 7,50 ; le raisonnement
# ("thoughts") est facture au prix de la sortie (OpenRouter / pricepertoken, releve le 21/09/2026).
PRIX = {"pixtral-12b-latest": (0.0, 0.0), "kimi-k3": (3.0, 15.0), "deepseek-v4-flash": (0.30, 1.20),
        "gemini-3.6-flash": (0.75, 3.75)}
PRIX_TTS_CHAR = 30.0 / 1e6        # Chirp 3 HD, ~30 $/M caracteres (valeur deja retenue par smart-reader)
ENGINES = {"pixtral": ("/api/mistral", "pixtral-12b-latest"), "kimi": ("/api/kimi", "kimi-k3"),
           # Gemini passe par son API NATIVE : l'interface compatible OpenAI exige la cle dans l'en-tete
           # Authorization, que le gateway occupe deja (HTTP 400 mesure le 21/09).
           "gemini": ("/api/gemini/v1beta/models/gemini-3.6-flash:generateContent", "gemini-3.6-flash"),
           # v2.5.0 (feuille de route 4-nonies, etape 3 -- ESSAI) : analyse des pages en LOCAL (Ollama, carte graphique, 0 $)
           "local": ("http://127.0.0.1:11434/api/chat", "qwen3-vl:8b-instruct")}


# v2.8.0 (24/09) : la REFLEXION de Gemini 3.6 Flash est facturee au prix de la sortie et n'etait jamais bornee.
# Mesure sur la question des noms (Claymore ch.1, 12 p.) : defaut 6 700 jetons de reflexion = 2/3 du cout ; « minimal » 0.
# Vide = defaut de Google (inchange) ; sinon minimal | low | medium | high. Vaut pour noms, analyse ET traduction.
REFLEXION_GEMINI = os.environ.get("MANGA_GEMINI_REFLEXION", "").strip()
# Le REPERAGE DES NOMS (question courte : quels prenons, qui les porte) passe en « minimal » par defaut : banc du 24/09,
# OPM ch.301, 4 passages -> les MEMES 5 noms a chaque fois (la reflexion par defaut en oubliait 2 une fois sur deux),
# 0,03 $ au lieu de 0,12-0,13 $. L'analyse des pages (d'ou vient le recit) garde sa reflexion : la couper la degrade
# (2 juges a l'aveugle voyant les pages, OPM ch.2 : 10-2 et 7-3 pour la reflexion complete). Vide = defaut de Google.
REFLEXION_NOMS = os.environ.get("MANGA_GEMINI_REFLEXION_NOMS", "minimal").strip()


def appel_vision(engine, system, content, max_tokens, reflexion=None):
    """Un appel vision, quel que soit le moteur. Rend (texte, usage au format OpenAI)."""
    path, model = ENGINES[engine]
    if engine == "local":                      # v2.5.0 : API native d'Ollama (contexte elargi, images dans l'ordre)
        textes, images = [], []
        for c in content:
            if c["type"] == "text":
                textes.append(c["text"])
            else:
                images.append(c["image_url"]["url"].split(";base64,", 1)[1])
                textes.append("[image %d ci-jointe]" % len(images))
        body = {"model": model, "stream": False, "format": "json", "keep_alive": "15m",
                "options": {"num_ctx": 32768, "temperature": 0.2, "num_predict": max_tokens},
                "messages": [{"role": "system", "content": system},
                             {"role": "user", "content": " ".join(textes), "images": images}]}
        try:
            req = urllib.request.Request(path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
            r = json.load(urllib.request.urlopen(req, timeout=max(600, max_tokens // 10)))
        except urllib.error.HTTPError as e:    # banc 24/09 : 500 d'Ollama sur 1 lot sur 8 en JSON impose -> sans contrainte
            log("  analyse locale : HTTP %s, nouvel essai sans format JSON impose" % e.code)
            body.pop("format", None)
            req = urllib.request.Request(path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
            r = json.load(urllib.request.urlopen(req, timeout=max(600, max_tokens // 10)))
        return r["message"]["content"], {"prompt_tokens": r.get("prompt_eval_count", 0), "completion_tokens": r.get("eval_count", 0)}
    if engine != "gemini":
        body = {"model": model, "max_tokens": max_tokens,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": content}]}
        if engine == "pixtral":
            body["temperature"] = 0.1
        # v1.75 : delai proportionnel au budget. A 32 000 tokens, K3 raisonne plus de 240 s : 5 timeouts
        # d'affilee ont tue un run le 21/09 (22h15). ~40 tokens/s mesures -> 1 s par tranche de 40 tokens.
        r = post(path, body, timeout=max(240, max_tokens // 40))
        motif = mod.refus_openai(r)
        if motif:
            raise mod.Refus(engine, motif)
        texte = r["choices"][0]["message"].get("content")
        motif = mod.refus_texte(texte)
        if motif:
            raise mod.Refus(engine, motif)
        return texte, (r.get("usage") or {})
    parts = []
    for c in content:
        if c["type"] == "text":
            parts.append({"text": c["text"]})
        else:
            mime, data = c["image_url"]["url"][5:].split(";base64,", 1)
            parts.append({"inline_data": {"mime_type": mime, "data": data}})
    r = post(path, {"systemInstruction": {"parts": [{"text": system}]},
                    "contents": [{"role": "user", "parts": parts}],
                    "generationConfig": dict({"maxOutputTokens": max_tokens, "responseMimeType": "application/json"},
                                             **({"thinkingConfig": {"thinkingLevel": niv}} if (niv := REFLEXION_GEMINI if reflexion is None else reflexion) else {}))})
    motif = mod.refus_gemini(r)                    # v2.6.0 : avant, lu comme « JSON illisible » -> 3 essais PAYES
    if motif:
        raise mod.Refus("gemini", motif)
    um = r.get("usageMetadata") or {}
    texte = "".join(p.get("text", "") for p in ((r.get("candidates") or [{}])[0].get("content") or {}).get("parts", []))
    return texte, {"prompt_tokens": um.get("promptTokenCount", 0),
                   "completion_tokens": um.get("candidatesTokenCount", 0) + um.get("thoughtsTokenCount", 0)}


def log(*a):
    # v2.3.0 : un journal ne fait JAMAIS planter une narration (23/09 : « 傑諾斯=Genos » vers une console cp1252 -> code 1)
    try:
        print(*a, file=sys.stderr, flush=True)
    except UnicodeEncodeError:
        enc = getattr(sys.stderr, "encoding", None) or "ascii"
        print(*(str(x).encode(enc, "replace").decode(enc) for x in a), file=sys.stderr, flush=True)


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
STATS = None                  # v1.91.0 : les stats du run en cours -> la depense cumulee part dans progress.json


def progres(etape, fait, total, **kw):
    """progress.json a cote du resultat : ce que l'app lit pour sa barre de progression.
    v1.91.0 : porte aussi `couts` (depense cumulee par poste) : la pastille des couts compte un run EN COURS,
    au lieu de le decouvrir a la fin (Quang, 22/09 : « le cout n'a pas ete calcule et affiche »)."""
    if not PROGRESS:
        return
    if STATS is not None and "couts" not in kw:
        kw["couts"] = {k: round(v, 5) for k, v in STATS.items() if k.startswith("cout_") and k != "cout_total" and v}
    try:
        with open(PROGRESS, "w", encoding="utf-8") as f:
            json.dump(dict(etape=etape, fait=fait, total=total, t=time.time(), pid=os.getpid(), **kw), f, ensure_ascii=False)
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
# v1.99.1 (22/09) : le gateway v1.60 donne a Manga Studio (User-Agent « manga-studio/ ») SON compteur a 60/min -> 54 ici
# (marge : compteur KV « fire-and-forget »). Avant : 18 sur 20 partages avec tout le PC -> 17 min de reperage des noms
# pour un chapitre de 49 pages.
MAX_PAR_MIN = 54
_APPELS = []


# v1.99.0 : le frein est COMMUN a tous les programmes (narration, traduction, karaoke, Precedemment, suivi de nuit).
# Chacun se freinait seul a 18/min : a deux, ils depassaient les 20/min du gateway (limite PAR IP = tout le PC) et se
# faisaient refuser. Un compteur partage sur disque, sous verrou (msvcrt, Windows).
FREIN_F = os.path.join(os.path.dirname(LOGF), "frein_gateway.json")


def _frein_local():
    while True:
        now = time.time()
        while _APPELS and now - _APPELS[0] > 60:
            _APPELS.pop(0)
        if len(_APPELS) < MAX_PAR_MIN:
            _APPELS.append(now)
            return
        time.sleep(60 - (now - _APPELS[0]) + 0.5)


def _frein():
    try:
        import msvcrt
        os.makedirs(os.path.dirname(FREIN_F), exist_ok=True)
    except Exception:
        return _frein_local()
    while True:
        attente = 0.0
        try:
            with open(FREIN_F, "a+", encoding="utf-8") as f:
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)          # un seul programme a la fois dans ce bloc
                try:
                    f.seek(0)
                    try:
                        l = [t for t in json.loads(f.read() or "[]") if isinstance(t, (int, float))]
                    except ValueError:
                        l = []
                    now = time.time()
                    l = [t for t in l if now - t < 60]
                    if len(l) < MAX_PAR_MIN:
                        l.append(now)
                        f.seek(0); f.truncate(); f.write(json.dumps(l)); f.flush()
                        return
                    attente = 60 - (now - min(l)) + 0.3
                finally:
                    f.seek(0)
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            attente = 0.5                                          # verrou pris trop longtemps : on repasse
        time.sleep(max(0.2, attente))


def post(path, body, timeout=240):
    req = urllib.request.Request(GATEWAY + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + SECRET,
                                          "User-Agent": "manga-studio/" + VERSION})
    last = None
    essai, refus = 0, 0
    while essai < 5:
        _frein()
        attente = 4 * (essai + 1)
        essai += 1
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            brut = e.read()[:300].decode("utf-8", "replace")
            last = "HTTP %d %s" % (e.code, brut[:200])
            motif = mod.refus_http(e.code, brut)              # v2.6.0 : refus de moderation = JAMAIS un nouvel essai
            if motif:
                journal("moderation", path=path, code=e.code, motif=motif[:200])
                raise mod.Refus(path.split("/")[2] if path.count("/") >= 2 else path, motif)
            if e.code not in (429, 500, 502, 503, 504, 520, 521, 522, 523, 524):   # 52x = Cloudflare, passager
                break
            if e.code == 429:           # le gateway dit combien attendre : on l'ecoute (60 s en pratique)
                try:
                    attente = float(json.loads(brut).get("retry_after") or 60) + 1
                except Exception:
                    attente = 61
                # v1.99.0 : « attends » n'est pas un echec -> ne consomme pas d'essai (5 refus d'affilee faisaient
                # echouer une narration entiere sans aucune panne) ; borne : 15 refus (~15 min) par appel
                refus += 1
                if refus <= 15:
                    essai -= 1
                journal("429", path=path, attente=attente, refus=refus)
                log("  429 sur %s : pause %.0f s" % (path, attente))
        except Exception as e:          # timeout reseau, coupure
            last = str(e)
            # v1.98.3 : un delai depasse ne laissait AUCUNE trace (22/09 : K3 a 6-17 min par lot sur Frieren, sans
            # qu'on puisse dire s'il reflechissait ou si l'appel etait coupe a 240 s puis relance -- et refacture)
            journal("reseau", path=path, essai=essai, timeout=timeout, err=str(e)[:160])
            log("  %s : %s (essai %d, delai %d s)" % (path, str(e)[:120], essai, timeout))
        time.sleep(attente)
    raise RuntimeError(path + " : " + str(last))


def parse_json(txt):
    """Le modele entoure parfois son JSON de ``` ou de prose : on prend l'objet le plus large."""
    t = (txt or "").strip()
    a, b = t.find("{"), t.rfind("}")
    if a < 0 or b <= a:
        raise ValueError("pas de JSON dans la reponse : " + t[:200])
    return json.loads(t[a:b + 1])


def reparer_json(texte, stats, cle="cout_vision"):
    """v1.98.1 : un JSON MAL FORME (virgule oubliee, guillemet de dialogue non echappe) se REPARE, il ne se redemande
    pas. Mesure 22/09 (Frieren ch.143, lot 1-2) : K3 rendait « Expecting ',' delimiter » ; relire les images avec un
    budget double 3 fois = 27 min et le chapitre abandonne. Ici : un appel TEXTE a DeepSeek (~0,001 $, quelques s),
    consigne stricte de ne rien changer au contenu. Rend l'objet, ou None."""
    try:
        r = post("/api/deepseek", {"model": "deepseek-v4-flash", "max_tokens": 8000, "temperature": 0,
                                   "thinking": {"type": "disabled"}, "response_format": {"type": "json_object"},
                                   "messages": [{"role": "system", "content": "Tu repares du JSON invalide. Rends EXACTEMENT le meme contenu "
                                                 "(memes cles, memes valeurs, meme texte mot pour mot), seulement rendu valide : virgules, "
                                                 "guillemets internes echappes, accolades. Rien d'autre que le JSON."},
                                                {"role": "user", "content": texte or ""}]}, timeout=120)
        stats[cle] = stats.get(cle, 0.0) + cout("deepseek-v4-flash", r.get("usage") or {})
        return parse_json(r["choices"][0]["message"].get("content"))
    except Exception as e:
        log("  reparation du JSON impossible : %s" % e)
        return None


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
    # v1.98.2 : l'etape s'annonce DES son debut. Sinon l'app affichait l'etape precedente terminee (« noms 19/19,
    # < 1 min ») pendant tout le 1er lot, plusieurs minutes chez K3 (Quang, 22/09 10h26 : « bloquee a une minute »).
    progres("vision", 0, len(pages))
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


# =====================================================================================
# v2 (21/09, apres le banc de fidelite) : FAITS d'abord, STYLE ensuite, personnages FIGES.
# Mesure v1 sur Claymore ch.1 : 6 pages graves / 20, toutes de la MEME racine -- le jeune
# Raki et l'adolescent Zaki fusionnes en un seul "Zaki". Page isolee : "RAKI" lu 6/6. C'est
# le SUIVI des personnages qui deraillait, et la consigne v1 "reprends les noms deja connus"
# verrouillait l'erreur. Remede (recherche web + retour XianScan) : une FICHE des personnages
# (description visuelle stable) ou un nom n'est pose qu'avec une PREUVE lue dans la page.
# =====================================================================================
SYS_VISION_V2 = """Tu relis des pages de manga pour en extraire les FAITS, sans aucun style. Precision absolue :
une erreur sur QUI fait ou dit QUOI est la pire faute possible.

Tu recois : la FICHE des personnages deja rencontres (id, description visuelle, nom si PROUVE), un resume
des faits precedents, puis des images. Chaque image est precedee d'une etiquette "PAGE N" : utilise
EXACTEMENT ce numero.

Pour chaque page :
- "type" : "histoire" | "credits" | "pub" | "couverture" (page titre sans action)
- "faits" : ce qui se passe, case par case dans l'ordre de lecture (droite->gauche pour un manga), en
  phrases factuelles : QUI (id de la fiche + nom s'il est prouve) fait/dit QUOI a QUI. Paraphrase les
  repliques, ne les recopie pas. Aucune emotion ni intention non visibles.
  LOCUTEURS : n'attribue une replique a un personnage de la fiche que si la queue de la bulle pointe vers
  lui ET qu'il est reconnaissable dans la case. Sinon : "un villageois", "une voix dans la foule". Un
  personnage nomme qui est present sur la page n'est PAS pour autant celui qui parle.
- "presents" : ids des personnages de la fiche visibles sur la page.

Fiche : ajoute un personnage nouveau avec un id court (p1, p2...) et une description VISUELLE qui le
distingue des autres (age apparent, taille, coiffure, vetements). Un NOM ne s'attache a un personnage que
si la page le PROUVE : quelqu'un l'appelle par ce nom, ou le texte le nomme. Donne cette preuve. Deux
personnages d'ages differents ne sont JAMAIS le meme id. Si une page contredit la fiche (le nom etait
attache au mauvais personnage), signale-le dans "corrections".

ALPHABET : ecris tout en francais et en alphabet latin. Un nom ecrit en caracteres chinois, japonais ou coreens
prend sa forme latine d'usage (edition francaise ou anglaise) ; une replique dans ces ecritures se traduit.

Reponds UNIQUEMENT en JSON :
{"pages":[{"page":N,"type":"...","faits":"...","presents":["p1"]}],
 "nouveaux":[{"id":"p3","description":"...","nom":null}],
 "noms":[{"id":"p2","nom":"...","preuve":"page N : ..."}],
 "corrections":[{"id":"p2","probleme":"..."}],
 "resume":"faits essentiels depuis le debut du chapitre (max 120 mots)"}"""

SYS_RECIT_V2 = """Tu es le narrateur d'une video "manga recap" en francais, de celles qu'on ecoute avec plaisir.
On te donne les FAITS de chaque page, releves par un lecteur minutieux, et la fiche des personnages.
Ecris la narration de chaque page pour que l'ensemble, lu a voix haute, forme un RECIT prenant :
- c'est une HISTOIRE que tu racontes, pas une description d'images : present de narration, phrases courtes
  et orales, tension, enchainements ("Mais", "Soudain", "Pendant ce temps"), chute a la fin du chapitre ;
- la dramatisation passe par le RYTHME et le CHOIX DES MOTS, jamais par des ajouts : aucun fait, lieu,
  personnage, emotion ou intention absent des faits fournis. Une emotion peut etre nommee si les faits
  la montrent (peur, stupeur, colere) ;
- ne cite pas de locuteur que les faits n'identifient pas ("un villageois" reste "un villageois") ;
- les personnages : utilise EXACTEMENT les noms de la fiche, et seulement pour le personnage qui porte ce
  nom ; sans nom, une description courte et stable ("le jeune garcon", "l'adolescent") ;
- INTERDIT (description d'ecran) : "on voit", "gros plan", "montre", "la case", "cette page", "l'image",
  "apparait", "est represente". Un gros plan sur un visage devient une phrase sur le personnage
  ("Son regard est glacial"), pas sur le cadrage ;
- paraphrase, jamais de replique recopiee mot pour mot ;
- une page peut rester muette ("") si elle n'apporte rien ; 1 a 3 phrases par page.
Reponds UNIQUEMENT en JSON : {"titre":"accroche courte","pages":[{"page":N,"narration":"..."}]}
avec EXACTEMENT les memes numeros de page que l'entree, dans le meme ordre."""


# v2.0.0 (22/09/2026, etude « outil auteurs ») : narration dans une AUTRE langue que le francais. Les faits restent
# releves en francais (consignes eprouvees, mesurees) ; seul le RECIT change de langue, puis la voix suit.
LANGUE = "fr"                                    # fixe par --langue
LANGUES_NARR = {"fr": ("francais", "fr-FR"), "en": ("anglais", "en-US")}
CONSIGNE_LANGUE = """
LANGUE DE SORTIE : ecris le titre et TOUTE la narration en %s naturel et oral (le style des chaines "recap"
anglophones pour l'anglais), meme si les faits fournis sont en francais. Les memes interdits valent dans cette
langue (en anglais : "we see", "close-up", "shows", "the panel", "this page", "the image", "appears", "is depicted")."""


def _consigne_langue():
    return "" if LANGUE == "fr" else CONSIGNE_LANGUE % LANGUES_NARR[LANGUE][0]


def _fiche_texte(fiche):
    return json.dumps([dict(id=k, **v) for k, v in fiche.items()], ensure_ascii=False)


def etape_vision_v2(chap_dir, pages, engine, batch, stats, noms=None):
    path, model = ENGINES[engine]
    fiche, resume, sortie, journal_fiche = {}, "", [], []
    for nom, v in (noms or {}).items():        # v2.2 : noms FIGES par la passe des noms (votes)
        desc = ", ".join(x for x in (v["age"], v["cheveux"], v.get("teint") and "teint " + v["teint"], v.get("tenue")) if x)
        fiche[nom.lower()] = {"description": desc, "nom": nom,
                              "preuve": "vote %s, pages %s" % (v["votes"], v["pages"]), "fige": True}
    # v1.98.2 : l'etape s'annonce DES son debut. Sinon l'app affichait l'etape precedente terminee (« noms 19/19,
    # < 1 min ») pendant tout le 1er lot, plusieurs minutes chez K3 (Quang, 22/09 10h26 : « bloquee a une minute »).
    progres("vision", 0, len(pages))
    file_lots = [pages[i:i + batch] for i in range(0, len(pages), batch)]
    faites = 0
    while file_lots:                          # v2.6.0 : une FILE -- un lot refuse y revient page par page
        lot = file_lots.pop(0)
        nums = [p["num"] for p in lot]
        content = [{"type": "text", "text": ("NOMS ETABLIS (verifies par vote, ne les change jamais, n'en ajoute "
                                             "aucun ; identifie ces personnages par leur AGE et leurs cheveux"
                                             + (", leur TEINT et leur TENUE ; un personnage qui differe sur un seul de ces "
                                                "traits est un AUTRE personnage, anonyme" if NOMS_VERSION == "v3" else "")
                                             + ") : "
                                             + json.dumps({k: v["description"] for k, v in fiche.items() if v.get("fige")},
                                                          ensure_ascii=False) + "\n" if noms else "")
                    + "FICHE : " + (_fiche_texte(fiche) if fiche else "(vide)")
                    + "\nFAITS PRECEDENTS : " + (resume or "(debut du chapitre)")
                    + "\nPages de ce lot : " + ", ".join(map(str, nums))}]
        portraits = [(n, v["portrait"]) for n, v in (noms or {}).items() if v.get("portrait")]
        if portraits:                          # v1.69 : EXEMPLES visuels des personnages nommes (approche Magi v2)
            content.append({"type": "text", "text": (
                "PORTRAITS DE REFERENCE : ces personnages nommes, et SEULEMENT eux, peuvent etre designes par leur "
                "nom. Compare visage, coiffure et COULEUR DES CHEVEUX (cheveux blancs/clairs = zones claires ; "
                "noirs/fonces = zones sombres ou tramees). Un personnage qui ne ressemble a aucun portrait est un "
                "anonyme (\"un villageois\", \"un homme brun\"), meme s'il a le meme age.")})
            for n, rel in portraits:
                content.append({"type": "text", "text": "PORTRAIT DE %s (reference, ce n'est pas une page)" % n})
                b64 = base64.b64encode(open(os.path.join(chap_dir, rel), "rb").read()).decode()
                content.append({"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + b64}})
        for p in lot:                         # etiquette AVANT chaque image (anti-decalage multi-images)
            content.append({"type": "text", "text": "PAGE %d" % p["num"]})
            b64 = base64.b64encode(page_jpeg(os.path.join(chap_dir, p["file"]))).decode()
            content.append({"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + b64}})
        t = time.time()
        j = None
        # v1.75 : budget DOUBLE a chaque essai. Mesure 21/09 (OPM 301, p11-12, consigne v3) : K3 passait
        # 7 997 des 8 000 tokens a RAISONNER (finish_reason=length) et rendait un contenu vide, 4 fois sur 4
        # -> le chapitre entier etait abandonne. (Chaque essai rate est FACTURE : ~0,12 $ de raisonnement.)
        try:
            for essai, budget in enumerate((8000, 16000, 32000)):
                texte, u = appel_vision(engine, SYS_VISION_V2, content, budget)
                stats["vision_tokens_in"] += u.get("prompt_tokens", 0)
                stats["vision_tokens_out"] += u.get("completion_tokens", 0)
                stats["cout_vision"] += cout(model, u)
                try:
                    j = parse_json(texte)
                    break
                except Exception as e:
                    if (texte or "").strip():                     # mal forme (pas vide) : on REPARE avant de relire
                        j = reparer_json(texte, stats)
                        journal("json_repare", pages=nums, ok=j is not None, err=str(e)[:120])
                        if j is not None:
                            log("  lot %s : JSON mal forme (%s) -> repare" % (nums, e))
                            break
                    log("  lot %s : JSON illisible (%s), nouvel essai" % (nums, e))
        except mod.Refus as e:
            if len(lot) > 1:
                log("  lot %s REFUSE par la moderation (%s) -> repris page par page" % (nums, e.motif[:80]))
                journal("moderation", etape="analyse", pages=nums, moteur=e.moteur, motif=e.motif[:200])
                file_lots[0:0] = [[q] for q in lot]
                continue
            q = lot[0]
            log("  page %d REFUSEE par la moderation de %s (%s) -> mise de cote, le chapitre continue" % (q["num"], e.moteur, e.motif[:80]))
            journal("moderation", etape="analyse", pages=nums, moteur=e.moteur, motif=e.motif[:200])
            stats.setdefault("moderation", []).append({"page": q["num"], "etape": "analyse", "moteur": e.moteur, "motif": e.motif})
            sortie.append({"page": q["num"], "file": q["file"], "type": "moderation", "faits": "", "presents": [],
                           "narration": "", "moderation": e.motif})
            faites += 1
            progres("vision", faites, len(pages))
            continue
        if j is None:
            raise RuntimeError("lot %s : JSON illisible apres 3 essais (budget jusqu'a 32 000 tokens)" % nums)
        for n in j.get("nouveaux") or []:
            if n.get("id") and n["id"] not in fiche:
                fiche[n["id"]] = {"description": n.get("description", ""), "nom": None, "preuve": None}
        for n in ([] if noms else (j.get("noms") or [])):   # noms figes -> le modele n'en pose plus
            if n.get("id") in fiche and n.get("nom") and n.get("preuve"):
                ancien = fiche[n["id"]]["nom"]
                if ancien and ancien != n["nom"]:
                    journal_fiche.append({"lot": nums, "conflit": n, "ancien": ancien})
                fiche[n["id"]].update(nom=n["nom"], preuve=n["preuve"])
        for c in j.get("corrections") or []:
            journal_fiche.append({"lot": nums, "correction": c})
        recus = {}
        for x in j.get("pages") or []:
            try: recus[int(x.get("page"))] = x
            except (TypeError, ValueError): pass
        for p in lot:
            x = recus.get(p["num"]) or {"type": "histoire", "faits": "", "presents": []}
            if p["num"] not in recus:
                journal_fiche.append({"lot": nums, "page_absente": p["num"]})
            sortie.append({"page": p["num"], "file": p["file"], "type": x.get("type", "histoire"),
                           "faits": x.get("faits", ""), "presents": x.get("presents") or [], "narration": ""})
        resume = j.get("resume") or resume
        dt = time.time() - t
        stats["vision_s"] += dt
        faites += len(lot)
        progres("vision", faites, len(pages))
        journal("vision_lot_v2", engine=engine, pages=nums, s=round(dt, 1), fiche=len(fiche))
        log("  vision v2 %s pages %s : %.1fs (fiche : %s)" % (engine, nums, dt,
            ", ".join("%s=%s" % (k, v["nom"] or "?") for k, v in fiche.items())))
    persos = [{"id": k, "nom": v["nom"] or "", "qui": v["description"], "preuve": v["preuve"]} for k, v in fiche.items()]
    stats["fiche_journal"] = journal_fiche
    return sortie, resume, persos


# v2.2.0 (23/09/2026) : le recit se demande PAR LOTS. Claymore ch.1 recapture en tome (180 pages) partait en UN
# appel plafonne a 8 000 tokens : reponse illisible (« Expecting ',' delimiter », char 26 885), 180 pages SANS
# texte, 0 voix -- et le run se disait « ok ». 40 pages = ~2 500 tokens de sortie, large marge.
RECIT_LOT = 40


class _RecitTronque(Exception):
    pass


def _appel_recit_v2(lot, persos, stats, contexte):
    body = {"model": "deepseek-v4-flash", "max_tokens": 8000, "temperature": 0.6,
            "thinking": {"type": "disabled"},
            "messages": [{"role": "system", "content": SYS_RECIT_V2 + _consigne_langue()},
                         {"role": "user", "content": "Fiche des personnages : " + json.dumps(persos, ensure_ascii=False)
                          + contexte + "\nPages :\n" + json.dumps(lot, ensure_ascii=False)}]}
    r = post("/api/deepseek", body)
    stats["cout_recit"] += cout("deepseek-v4-flash", r.get("usage") or {})
    ch = r["choices"][0]
    txt = ch["message"].get("content")
    if ch.get("finish_reason") == "length":
        raise _RecitTronque("reponse tronquee (%d pages demandees)" % len(lot))
    try:
        return parse_json(txt)
    except ValueError as e:                  # JSONDecodeError en herite
        log("  recit : JSON mal forme (%s) -> reparation" % str(e)[:80])
        j = reparer_json(txt, stats, "cout_recit")
        if j is None:
            raise
        return j


def _suite(fin):
    return ("\nLe recit deja ecrit juste avant se termine ainsi : " + json.dumps(fin, ensure_ascii=False)
            + " -- CONTINUE-le sans le repeter ni re-presenter les personnages.") if fin else ""


def _contexte_lot(k, n, fin):
    if n == 1:
        return ""
    return ("\nCHAPITRE LONG raconte en %d parties : voici la partie %d/%d. " % (n, k + 1, n)
            + ("La chute de fin de chapitre est pour CETTE partie." if k == n - 1
               else "PAS de chute ni de conclusion ici : le recit continue dans la partie suivante.")
            + _suite(fin))


def _recit_lot(lot, persos, stats, contexte):
    """Un lot ; tronque ou illisible -> coupe en deux (le 2e demi-lot recoit la fin du 1er)."""
    try:
        return _appel_recit_v2(lot, persos, stats, contexte)
    except mod.Refus as e:                      # v2.6.0 : refus du recit -> on isole la ou les pages en cause
        if len(lot) == 1:
            stats.setdefault("moderation", []).append({"page": lot[0]["page"], "etape": "recit", "moteur": e.moteur, "motif": e.motif})
            log("  recit : page %s REFUSEE par la moderation (%s) -> sans narration, alerte" % (lot[0]["page"], e.motif[:80]))
            return {"titre": "", "pages": [{"page": lot[0]["page"], "narration": ""}]}
        m = len(lot) // 2
        j1 = _recit_lot(lot[:m], persos, stats, contexte)
        j2 = _recit_lot(lot[m:], persos, stats, contexte)
        return {"titre": j1.get("titre", "") or j2.get("titre", ""), "pages": (j1.get("pages") or []) + (j2.get("pages") or [])}
    except (_RecitTronque, ValueError) as e:
        if len(lot) <= 4:
            raise
        m = len(lot) // 2
        log("  recit : %s -> lot coupe en %d + %d pages" % (str(e)[:80], m, len(lot) - m))
        j1 = _recit_lot(lot[:m], persos, stats, contexte)
        fin = [x.get("narration", "") for x in (j1.get("pages") or []) if (x.get("narration") or "").strip()][-2:]
        j2 = _recit_lot(lot[m:], persos, stats, contexte + _suite(fin))
        return {"titre": j1.get("titre", ""), "pages": (j1.get("pages") or []) + (j2.get("pages") or [])}


def _lire_pages_recit(j, neuf, seulement=None):
    for x in j.get("pages") or []:
        try:
            n = int(x["page"])
        except (KeyError, TypeError, ValueError):
            continue
        if seulement is None or (n in seulement and (x.get("narration") or "").strip()):
            neuf[n] = x.get("narration", "")


def etape_recit_v2(pages, resume, persos, stats):
    entree = [{"page": p["page"], "type": p["type"], "faits": p["faits"]} for p in pages if p["type"] == "histoire"]
    if not entree:
        return "", pages
    lots = [entree[i:i + RECIT_LOT] for i in range(0, len(entree), RECIT_LOT)]
    t = time.time()
    neuf, titre = {}, ""
    for k, lot in enumerate(lots):
        fin = [neuf[x["page"]] for x in entree[:k * RECIT_LOT] if (neuf.get(x["page"]) or "").strip()][-2:]
        ctx = _contexte_lot(k, len(lots), fin)
        j = _recit_lot(lot, persos, stats, ctx)
        titre = titre or j.get("titre", "")
        _lire_pages_recit(j, neuf)
        manq = [x["page"] for x in lot if not (neuf.get(x["page"]) or "").strip()]
        if manq:                              # K3 v2 : la p20 (essentielle) est sortie VIDE -> on redemande
            log("  recit : pages rendues vides %s -> nouvelle demande" % manq)
            j2 = _recit_lot(lot, persos, stats, ctx + "\nATTENTION : ecris OBLIGATOIREMENT une narration non vide "
                            "pour les pages " + ", ".join(map(str, manq)) + ".")
            _lire_pages_recit(j2, neuf, set(manq))
        progres("recit", k + 1, len(lots))
    stats["recit_s"] += time.time() - t
    for p in pages:
        p["narration_vision"] = ""
        p["narration"] = neuf.get(p["page"], "") if p["type"] == "histoire" else ""
    manq = [x["page"] for x in entree if not (neuf.get(x["page"]) or "").strip()]
    journal("recit_v2", s=round(stats["recit_s"], 1), lots=len(lots), manquantes=manq)
    return titre, pages


# =====================================================================================
# v2.2 : les NOMS se resolvent a part, par VOTE, avant le releve des faits.
# Mesure 21/09 : un meme pipeline v2 donnait 2 pages graves sur un run et 7 sur le suivant (Raki/Zaki
# inverses) -- l'attribution d'un nom lu dans une bulle ("Zaki !") hesitait entre celui qui PARLE et celui
# qu'on APPELLE. Question ciblee, une page par appel : Gemini 11/12 votes justes, 4/4 pages en majorite
# de 3 (K3 : 3/4, 4-5x plus lent). Les noms retenus sont ensuite FIGES pour le releve des faits.
# =====================================================================================
Q_NOMS = ("Page de manga. 1) Liste les PRENOMS de personnages ecrits dans les bulles (pas les noms communs, pas "
          "les titres). 2) Pour chacun : qui PORTE ce prenom (celui qu'on appelle ainsi, PAS celui qui parle) ? "
          "Donne son age apparent (enfant | adolescent | adulte) et sa coiffure / couleur de cheveux, et qui "
          "prononce la bulle. 3) Donne le cadre du VISAGE + epaules du porteur, le plus grand ou il est visible "
          "sur la page : porteur_box = [ymin, xmin, ymax, xmax] en milliemes de la page (0-1000). "
          "Aucun prenom : liste vide. JSON : {\"noms\":[{\"nom\":\"...\",\"porteur_age\":"
          "\"enfant|adolescent|adulte\",\"porteur_cheveux\":\"...\",\"dit_par\":\"...\",\"porteur_box\":[0,0,0,0]}]} "
          # v2.3.0 : un scan chinois (OPM ch.5-8, zh-hk) faisait figer « 傑諾斯 » au lieu de Genos
          "Ecris chaque prenom en ALPHABET LATIN, sous sa forme d'usage dans l'edition francaise ou anglaise de la serie "
          "(jamais de caracteres chinois, japonais ou coreens).")
# v1.75 (21/09, verrou mesure sur OPM ch.301) : le vote prouvait qu'un nom est ECRIT, pas QUI le porte.
# "M. McCoy ?" (absent, parti aux toilettes) etait fige puis colle a l'homme du fauteuil ; un heros anonyme
# au teint sombre etait pris pour Blue (memes age et cheveux courts). v3 = on demande si le porteur est
# DESSINE sur la page, et son teint et sa tenue, pour distinguer deux personnages qui se ressemblent.
Q_NOMS_V3 = Q_NOMS + (" 4) porteur_visible : le porteur est-il DESSINE sur cette page ? false s'il est seulement "
          "cite, absent, appele au telephone ou hors champ. 5) porteur_teint : clair | mat | sombre. "
          "6) porteur_tenue : sa tenue en quelques mots (ex. hoodie dechire, costume sombre). "
          "Ajoute ces 3 champs (porteur_visible, porteur_teint, porteur_tenue) a chaque entree du JSON.")
NOMS_VERSION = "v2"                             # fixe par --noms
VOTES_NOMS = 3


_VERROU_STATS = threading.Lock()


def fusion_accents(votes):
    """v1.99.2 : « Fräse » et « Fràse » = UN personnage (la page ecrit « Frāse » ; mesure 22/09, Frieren ch.143, 3 runs).
    Deux orthographes a un accent pres faisaient deux personnages pour le recit. On regroupe par la forme sans accents ;
    l'orthographe la plus votee l'emporte (a egalite, la premiere vue)."""
    import unicodedata
    cle = lambda n: unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode().lower()
    groupes = {}
    for nom, vs in votes.items():
        groupes.setdefault(cle(nom), []).append((nom, vs))
    out = {}
    for membres in groupes.values():
        nom = max(membres, key=lambda m: len(m[1]))[0]
        out[nom] = [v for _n, vs in membres for v in vs]
    return out
PAGES_NOMS_EN_PARALLELE = 4                      # v1.99.2 : x (1 + votes) appels en vol ; le frein commun garde le rythme


def _question_noms(chap_dir, p, stats):
    img = base64.b64encode(page_jpeg(os.path.join(chap_dir, p["file"]))).decode()
    content = [{"type": "text", "text": Q_NOMS_V3 if NOMS_VERSION == "v3" else Q_NOMS},
               {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + img}}]
    try:
        txt, u = appel_vision("gemini", "Reponds uniquement en JSON.", content, 4000, reflexion=REFLEXION_NOMS)
    except mod.Refus as e:                       # v2.6.0 : page refusee -> aucun nom tire d'elle, on continue
        journal("moderation", etape="noms", page=p.get("num"), motif=e.motif[:200])
        return []
    with _VERROU_STATS:                          # v1.99.2 : appele depuis plusieurs fils a la fois
        stats["cout_noms"] = stats.get("cout_noms", 0.0) + cout("gemini-3.6-flash", u)
    try:
        return [x for x in (parse_json(txt).get("noms") or []) if (x.get("nom") or "").strip()]
    except Exception:
        return []


def _portrait(chap_dir, fichier, box, dest):
    """Decoupe le porteur d'un nom (cadre 0-1000 rendu par Gemini) : l'EXEMPLE visuel qui sert ensuite a le
    reconnaitre (approche Magi v2). Rend le chemin, ou None si le cadre est absurde."""
    try:
        y0, x0, y1, x1 = [float(v) for v in box]
    except Exception:
        return None
    if not (0 <= y0 < y1 <= 1000 and 0 <= x0 < x1 <= 1000) or (y1 - y0) * (x1 - x0) < 400:
        return None                              # cadre vide ou minuscule (< 2 % x 2 % de la page)
    from PIL import Image
    im = Image.open(os.path.join(chap_dir, fichier)).convert("RGB")
    W, H = im.size
    my, mx = (y1 - y0) * 0.08, (x1 - x0) * 0.08  # un peu de marge : la coiffure deborde souvent du cadre
    c = im.crop((max(0, int((x0 - mx) * W / 1000)), max(0, int((y0 - my) * H / 1000)),
                 min(W, int((x1 + mx) * W / 1000)), min(H, int((y1 + my) * H / 1000))))
    if c.width > 480:
        c = c.resize((480, round(c.height * 480 / c.width)))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    c.save(dest, "JPEG", quality=88)
    return dest


# =====================================================================================
# v1.74 (etape 2 de la feuille de route) : FICHE PERSONNAGES PAR SERIE.
# Un nom prouve par vote dans un chapitre de la serie est connu des chapitres suivants : il n'a plus besoin
# de 2 votes, et il est transmis a la lecture meme sur les pages ou personne ne le prononce.
# Construite A LA VOLEE depuis les narration.json des AUTRES chapitres (rien a tenir a jour, rien de perime).
# =====================================================================================
def fiche_serie(chap_dir):
    serie_dir, courant = os.path.dirname(chap_dir), os.path.basename(chap_dir)
    connus = {}
    for ch in sorted(os.listdir(serie_dir)):
        nd = os.path.join(serie_dir, ch, "narration")
        if ch == courant or not os.path.isdir(nd):
            continue
        runs = []
        for tag in os.listdir(nd):
            f = os.path.join(nd, tag, "narration.json")
            if os.path.isfile(f):
                runs.append((os.path.getmtime(f), f))
        for _, f in sorted(runs, reverse=True):          # le run le plus recent qui a des noms
            try: noms = (json.load(open(f, encoding="utf-8")).get("stats") or {}).get("noms") or {}
            except Exception: noms = {}
            if noms:
                for nom, v in noms.items():
                    c = connus.setdefault(nom, {"age": v.get("age", "?"), "cheveux": v.get("cheveux", ""), "chapitres": [],
                                                "teint": v.get("teint", ""), "tenue": v.get("tenue", "")})
                    c["chapitres"].append(ch)
                break
    return connus


def etape_noms(chap_dir, pages, stats, outdir=None, serie=None):
    """Rend {nom: {age, cheveux, votes, pages, portrait}} : noms PROUVES par la majorite des votes, et pour
    chacun un portrait decoupe (v1.69 : exemple visuel, pour ne plus nommer un anonyme qui lui ressemble)."""
    t = time.time()
    votes = {}                                   # nom -> liste de (page, age, cheveux, box, fichier)
    # v1.99.2 : les pages sont INDEPENDANTES (les votes ne sont regroupes qu'ensuite) -> on les interroge en parallele.
    # Mesure 22/09 : une question = ~6 s ; posees une par une, Frieren 19 p. = 364 s et Boruto 49 p. = 17 min, sans AUCUN
    # refus du gateway (ce n'etait pas le plafond, c'etait l'attente). Le regroupement reste fait dans l'ordre des pages.
    faites = [0]

    def une_page(p):
        premiers = _question_noms(chap_dir, p, stats)
        lus = [premiers]
        if premiers:                             # un prenom lu : 2 votes de plus sur CETTE page (en meme temps)
            with ThreadPoolExecutor(max_workers=max(1, VOTES_NOMS - 1)) as ex:
                lus += list(ex.map(lambda _: _question_noms(chap_dir, p, stats), range(VOTES_NOMS - 1)))
        with _VERROU_STATS:
            faites[0] += 1
            progres("noms", faites[0], len(pages))
        return lus

    with ThreadPoolExecutor(max_workers=PAGES_NOMS_EN_PARALLELE) as ex:
        resultats = list(ex.map(une_page, pages))
    for p, lus in zip(pages, resultats):
        for lot in lus:
            for x in lot:
                nom = x["nom"].strip().strip(".,!?").capitalize()
                votes.setdefault(nom, []).append((p["num"], x.get("porteur_age") or "?", x.get("porteur_cheveux") or "",
                                                  x.get("porteur_box"), p["file"],
                                                  x.get("porteur_visible") is not False,
                                                  (x.get("porteur_teint") or "").strip(),
                                                  (x.get("porteur_tenue") or "").strip()))
    votes = fusion_accents(votes)
    retenus = {}
    for nom, vs in votes.items():
        pages_nom = sorted({v[0] for v in vs})
        # un nom vu sur une SEULE page et une seule fois = lecture douteuse : on ne le fige pas
        # (v1.74 : sauf s'il est deja prouve dans un autre chapitre de la serie)
        if len(vs) < 2 and nom not in (serie or {}):
            continue
        if NOMS_VERSION == "v3":                 # v1.75 : un nom dont le porteur n'est DESSINE nulle part = cite, pas vu
            vus = [v for v in vs if v[5]]
            if len(vus) * 2 < len(vs):
                log("  nom ecarte (porteur jamais dessine) : %s (%d/%d votes le voient)" % (nom, len(vus), len(vs)))
                stats.setdefault("noms_ecartes", []).append(nom)
                continue
            vs = vus                             # age, cheveux et decompte : sur les votes qui le VOIENT
        ages = {}
        for v in vs:
            ages[v[1]] = ages.get(v[1], 0) + 1
        age, n_age = max(ages.items(), key=lambda kv: kv[1])
        cheveux = max((v[2] for v in vs if v[1] == age), key=len, default="")
        retenus[nom] = {"age": age, "cheveux": cheveux, "votes": "%d/%d" % (n_age, len(vs)), "pages": pages_nom}
        if NOMS_VERSION == "v3":
            def plus_frequent(i):
                c = {}
                for v in vs:
                    if v[i]: c[v[i]] = c.get(v[i], 0) + 1
                return max(c.items(), key=lambda kv: kv[1])[0] if c else ""
            retenus[nom].update(teint=plus_frequent(6), tenue=plus_frequent(7))
        if outdir:                               # portrait : le plus GRAND cadre parmi les votes majoritaires
            def aire(v):
                try: return (float(v[3][2]) - float(v[3][0])) * (float(v[3][3]) - float(v[3][1]))
                except Exception: return -1
            for v in sorted((v for v in vs if v[1] == age), key=aire, reverse=True):
                chemin = _portrait(chap_dir, v[4], v[3], os.path.join(outdir, "portraits", nom.lower() + ".jpg"))
                if chemin:
                    retenus[nom].update(portrait=os.path.relpath(chemin, chap_dir).replace("\\", "/"),
                                        portrait_page=v[0])
                    break
    stats["noms_s"] = round(time.time() - t, 1)
    stats["noms"] = retenus                      # ce chapitre SEUL : c'est ce qui alimente la fiche de la serie
    journal("noms", retenus=retenus)
    log("  noms figes : " + (", ".join("%s=%s (%s)" % (k, v["age"], v["votes"]) for k, v in retenus.items()) or "aucun"))
    if serie:                                    # v1.74 : les connus de la serie absents des votes de ce chapitre
        ajoutes = {nom: {"age": c["age"], "cheveux": c["cheveux"], "teint": c.get("teint", ""), "tenue": c.get("tenue", ""),
                         "votes": "serie " + ",".join(c["chapitres"]),
                         "pages": []} for nom, c in serie.items() if nom not in retenus}
        stats["noms_serie"] = sorted(ajoutes)
        log("  noms de la serie ajoutes : " + (", ".join(sorted(ajoutes)) or "aucun"))
        return dict(retenus, **ajoutes)
    return retenus


# =====================================================================================
# v2.3 : VERIFICATION des attributions nommees, page par page, contre l'image.
# Mesure v2.2 (3 runs) : la grande confusion Raki/Zaki a disparu, mais il reste 3 pages graves par run,
# toutes du meme type et toutes nees au RELEVE : une replique ou une emotion d'un anonyme attribuee a
# un personnage NOMME present sur la page (p4 "Raki en larmes annonce la 6e victime" = un adulte de dos ;
# p16 une replique de villageois donnee a Zaki). Remede recommande par la recherche (generateur ->
# critique) : ne re-verifier QUE les phrases qui nomment quelqu'un, sur l'image seule de la page.
# =====================================================================================
SYS_VERIF = """Tu VERIFIES un releve de faits d'une page de manga contre l'image de cette page.
On te donne la fiche des personnages NOMMES (age apparent, cheveux) et le releve. Pour CHAQUE phrase du
releve qui attribue une parole, une action ou une emotion a un personnage NOMME :
- verifie sur l'image que ce personnage (reconnaissable a son age et ses cheveux) est bien celui qui
  parle (la queue de la bulle pointe vers lui) ou qui agit ;
- si ce n'est pas lui, ou si tu ne peux pas l'affirmer, remplace le nom par un sujet anonyme exact
  ("un villageois", "un homme de dos", "une voix") ;
- supprime toute emotion (larmes, peur...) qui n'est pas visible sur son visage.
Ne touche a rien d'autre : ni l'ordre, ni les faits non nommes. N'ajoute rien.
Reponds UNIQUEMENT en JSON : {"faits":"releve corrige","corrections":["<ce que tu as change et pourquoi>"]}"""


def etape_verif(chap_dir, pages, noms, stats):
    if not noms:
        return pages
    t = time.time()
    fiche = json.dumps({n: "%s, %s" % (v["age"], v["cheveux"]) for n, v in noms.items()}, ensure_ascii=False)
    motif = re.compile(r"\b(" + "|".join(re.escape(n) for n in noms) + r")\b", re.I)
    corr = []
    for p in pages:
        if p["type"] != "histoire" or not motif.search(p.get("faits") or ""):
            continue
        img = base64.b64encode(page_jpeg(os.path.join(chap_dir, p["file"]))).decode()
        content = [{"type": "text", "text": "FICHE : %s\nRELEVE de la page %d : %s" % (fiche, p["page"], p["faits"])},
                   {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + img}}]
        try:
            txt, u = appel_vision("gemini", SYS_VERIF, content, 6000)
            stats["cout_verif"] = stats.get("cout_verif", 0.0) + cout("gemini-3.6-flash", u)
            j = parse_json(txt)
        except Exception as e:
            log("  verif p%d en echec (%s) : releve garde tel quel" % (p["page"], e))
            continue
        if (j.get("faits") or "").strip():
            if j["faits"].strip() != p["faits"].strip():
                p["faits_avant_verif"] = p["faits"]
            p["faits"] = j["faits"].strip()
        for c in j.get("corrections") or []:
            corr.append({"page": p["page"], "correction": c})
        progres("verification", p["page"], pages[-1]["page"])
    stats["verif_s"] = round(time.time() - t, 1)
    stats["verif_corrections"] = corr
    journal("verif", corrections=len(corr))
    log("  verification : %d correction(s)" % len(corr))
    return pages


def duree_mp3(path):
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                              "-of", "default=nw=1:nk=1", path], capture_output=True, text=True, timeout=30)
        return round(float(out.stdout.strip()), 2)
    except Exception:
        return None


# v2.1.0 (23/09, etape N2 de la ROADMAP) : aucun caractere japonais / chinois / coreen ne va a la voix. Remontee de
# Video Studio : « un nom en kanji fait derailler la voix francaise » (vu avec Kimi). Non reproduit dans les textes LUS de
# la bibliotheque (les kanji ne sont que dans les notes de lecture), mais rien ne l'empechait. On nettoie le TEXTE de la
# page (pas seulement ce qu'on envoie a la voix) : sous-titres et karaoke restent alignes mot pour mot sur ce qui est dit.
_RE_CJK = r"[　-〿぀-ヿㇰ-ㇿ㐀-䶿一-鿿가-힯豈-﫿＀-￯]"


# v2.3.0 (23/09/2026, remontee Video Studio) : OPM ch.5-8 captures en chinois de Hong Kong (MangaDex zh-hk) -> les noms
# lus dans les bulles etaient figes en chinois (傑諾斯 = Genos, 埼玉 = Saitama, 土龍 = Taupe), le recit les recopiait et
# sans_cjk() les effacait : « En bas, lève sa main mécanique » (ch.6 p.2), 39 pages amputees EN SILENCE. Regle de Quang
# (feedback_affichage_alphabet_latin) : ce qu'il lit ou entend est en alphabet latin, et une consigne ne suffit pas.
# => Avant le recit, tout mot CJK restant (fiche, faits, presents, resume) est converti en UN appel texte (DeepSeek,
#    ~0,001 $), redemande une fois, journalise. Idempotent : rien a faire si le texte est deja latin (0 appel).
Q_LATIN = ("Manga : %s. Voici des mots en caracteres chinois, japonais ou coreens releves dans ses pages (noms de "
           "personnages, repliques, mots isoles). Rends pour CHACUN sa forme francaise en alphabet latin : un NOM de "
           "personnage -> son nom d'usage dans l'edition francaise ou anglaise de la serie (ex. 埼玉 -> Saitama) ; sinon "
           "une traduction francaise courte. Aucun caractere non latin dans les valeurs. "
           "JSON uniquement : {\"<mot>\": \"<forme latine>\"}.\nMots : %s")


def _mots_cjk(*textes):
    return sorted({m for t in textes for m in re.findall(_RE_CJK + "+", t or "")}, key=len, reverse=True)


def latiniser(vis, resume, persos, noms, titre, stats):
    """(vis, resume, persos, noms, table) -- memes structures, mots CJK remplaces par leur forme latine."""
    mots = _mots_cjk(resume, json.dumps(persos, ensure_ascii=False), " ".join(noms or {}),
                     *[(p.get("faits") or "") + " " + (p.get("narration") or "") + " " + " ".join(map(str, p.get("presents") or []))
                       for p in vis])
    if not mots:
        return vis, resume, persos, noms, {}
    table = {}
    for _ in (1, 2):                                      # redemande UNE fois ce qui manque ou revient non latin
        manq = [m for m in mots if m not in table]
        if not manq:
            break
        try:
            r = post("/api/deepseek", {"model": "deepseek-v4-flash", "max_tokens": 3000, "temperature": 0,
                                       "thinking": {"type": "disabled"}, "response_format": {"type": "json_object"},
                                       "messages": [{"role": "user", "content": Q_LATIN % (titre or "?", json.dumps(manq, ensure_ascii=False))}]},
                     timeout=120)
            stats["cout_recit"] = stats.get("cout_recit", 0.0) + cout("deepseek-v4-flash", r.get("usage") or {})
            j = parse_json(r["choices"][0]["message"].get("content"))
        except Exception as e:
            log("  latin : appel en echec (%s)" % str(e)[:120]); j = {}
        for m in manq:
            v = str(j.get(m) or "").strip()
            if v and not re.search(_RE_CJK, v):
                table[m] = v
    reste = [m for m in mots if m not in table]
    log("  latin : %d mot(s) converti(s) %s%s" % (len(table), ", ".join("%s=%s" % kv for kv in list(table.items())[:8]),
                                                  (" ; NON convertis : %s" % reste) if reste else ""))
    journal("latin", table=table, reste=reste)

    def lat(t):
        if not isinstance(t, str):
            return t
        for m in mots:                                    # les plus longs d'abord : « 傑諾斯 » avant « 傑 »
            if m in table:
                t = t.replace(m, table[m])
        return t
    for p in vis:
        for k in ("faits", "narration", "faits_avant_verif", "narration_vision"):
            if isinstance(p.get(k), str):
                p[k] = lat(p[k])
        if isinstance(p.get("presents"), list):
            p["presents"] = [lat(x) for x in p["presents"]]
    persos = json.loads(lat(json.dumps(persos, ensure_ascii=False)))
    noms = {lat(k): v for k, v in (noms or {}).items()}
    stats["latin"] = table
    return vis, lat(resume), persos, noms, table


def sans_cjk(txt):
    """(texte nettoye, nombre de caracteres retires). « Saito (研修医) arrive » -> « Saito arrive »."""
    if not re.search(_RE_CJK, txt or ""):
        return txt, 0
    n = len(re.findall(_RE_CJK, txt))
    t = re.sub(r"\s*[(\[（【「『«“\"]\s*(?:%s|\s|[・、。,.])+\s*[)\]）】」』»”\"]" % _RE_CJK, "", txt)
    t = re.sub(_RE_CJK + "+", "", t)
    t = re.sub(r"\s+([,.…])", r"\1", t)                 # le francais garde son espace avant ! ? ; :
    t = re.sub(r"([,;:])(\s*[,;:])+", r"\1", t)
    t = re.sub(r"\s{2,}", " ", t).strip()
    return t, n


def etape_voix(pages, outdir, voice, rate, stats):
    os.makedirs(outdir, exist_ok=True)
    for p in pages:
        p["audio"], p["dur"] = None, 0.0
        propre, retires = sans_cjk((p.get("narration") or "").strip())
        if retires:
            log("  page %s : %d caractere(s) japonais/chinois/coreen retire(s) avant la voix" % (p.get("page"), retires))
            p["narration"], p["cjk_retires"] = propre, retires
            stats["cjk_retires"] = stats.get("cjk_retires", 0) + retires
        txt = (p.get("narration") or "").strip()
        if not txt:
            continue
        loc = LANGUES_NARR[LANGUE][1]
        body = {"input": {"text": txt}, "voice": {"languageCode": loc, "name": loc + "-Chirp3-HD-" + voice.split("@")[0]},
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


TTS_LOCAL_PY = r"C:/Users/quang/AppData/Local/manga-tts/venv/Scripts/python.exe"   # venv voix, sur C: (24/09)
TTS_LOCAL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts_local.py")


def etape_voix_locale(pages, outdir, voice, stats):
    """v2.4.0 (feuille de route 4-nonies, etape 1) : voix LOCALE (Chatterbox, carte graphique), meme nettoyage du texte
    et memes fichiers pNNN.mp3 que la voix en ligne ; 0 $. Attend une carte libre (tts_local.py), sinon echoue net."""
    os.makedirs(outdir, exist_ok=True)
    jobs = []
    for p in pages:
        p["audio"], p["dur"] = None, 0.0
        propre, retires = sans_cjk((p.get("narration") or "").strip())
        if retires:
            log("  page %s : %d caractere(s) japonais/chinois/coreen retire(s) avant la voix" % (p.get("page"), retires))
            p["narration"], p["cjk_retires"] = propre, retires
            stats["cjk_retires"] = stats.get("cjk_retires", 0) + retires
        txt = (p.get("narration") or "").strip()
        if txt:
            jobs.append({"id": "p%03d" % p["page"], "texte": txt})
    if not jobs:
        return
    if not os.path.isfile(TTS_LOCAL_PY):
        raise SystemExit("voix locale : environnement introuvable (%s)" % TTS_LOCAL_PY)
    jf = os.path.join(outdir, "tts_local_jobs.json")
    json.dump(jobs, open(jf, "w", encoding="utf-8"), ensure_ascii=False)
    t = time.time()
    proc = subprocess.Popen([TTS_LOCAL_PY, TTS_LOCAL, "--jobs", jf, "--voix", voice, "--out", outdir, "--langue", LANGUE],
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
                            errors="replace", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    faits, ids = 0, {j["id"] for j in jobs}
    for ligne in proc.stdout:
        try:
            ev = json.loads(ligne)
        except Exception:
            continue
        if ev.get("id") in ids:
            faits += 1
            progres("voix", faits, len(jobs), moteur="local")
        elif ev.get("gpu") in ("attente", "occupee") or ev.get("erreur") or ev.get("modele"):
            log("  voix locale : %s" % json.dumps(ev, ensure_ascii=False))
            journal("voix_locale", **ev)
    rc = proc.wait()
    if rc == 3:
        raise SystemExit("voix locale : carte graphique occupee trop longtemps (ComfyUI ?) -- relancer plus tard ou choisir la voix en ligne")
    if rc != 0:
        raise SystemExit("voix locale : echec (code %d)" % rc)
    for p in pages:
        f = "p%03d.mp3" % p["page"]
        if "p%03d" % p["page"] in ids and os.path.isfile(os.path.join(outdir, f)):
            p["audio"], p["dur"] = f, duree_mp3(os.path.join(outdir, f)) or 0.0
            stats["tts_chars"] += len(p["narration"].strip())
    stats["tts_s"] += time.time() - t
    stats["cout_tts"] = 0.0
    stats["tts_moteur"] = "local"
    journal("voix_locale_fin", pages=len(jobs), s=round(time.time() - t, 1))


VOISINES = ("(Page NON analysee : refusee par la moderation. Ecris seulement une TRANSITION breve et neutre entre la page "
            "precedente et la suivante, sans inventer d'evenement ni decrire de contenu.)")


def reprendre_moderation(chap_dir, vis, mode, stats, noms):
    """v2.7.0 (feuille de route 4-decies) : SEULES les pages refusees sont reprises, sur choix de Quang dans l'app."""
    cible = [p for p in vis if p.get("type") == "moderation"]
    log("  reprise moderation (%s) : pages %s" % (mode, [p["page"] for p in cible]))
    if not cible:
        return vis
    if mode == "voisines":
        for p in cible:
            p.update(type="histoire", faits=VOISINES)
        return vis
    stats.pop("moderation", None)
    nouv, _r, _p = etape_vision_v2(chap_dir, [{"num": p["page"], "file": p["file"]} for p in cible], mode, 1, stats, noms)
    par = {x["page"]: x for x in nouv}
    return [dict(p, **{k: par[p["page"]][k] for k in ("type", "faits", "presents") if k in par[p["page"]]})
            if p["page"] in par else p for p in vis]


def pages_du_chapitre(chap_dir, plage):
    man = json.load(open(os.path.join(chap_dir, "manifest.json"), encoding="utf-8"))
    files = [p["file"] for p in man.get("pages", []) if os.path.isfile(os.path.join(chap_dir, p["file"]))]
    pages = [{"num": i + 1, "file": f} for i, f in enumerate(files)]
    if plage:
        a, _, b = plage.partition("-")
        a, b = int(a), int(b or a)
        pages = [p for p in pages if a <= p["num"] <= b]
    return man, pages


def _sorties_utf8():
    """v2.3.0 : stdout/stderr en UTF-8 quoi qu'il arrive. Lance par le proxy (bouton de l'app), la sortie part dans un
    FICHIER encode cp1252 : le 23/09, le json final (table « 傑諾斯 -> Genos ») plantait APRES avoir tout ecrit et paye -> code 1,
    lu comme un echec, voix refaite et payee une 2e fois (OPM ch.5-10, ~0,8 $)."""
    for f in (sys.stdout, sys.stderr):
        try:
            f.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main():
    global SECRET, PROGRESS, STATS
    _sorties_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("chapitre", help="chemin relatif sous sources/, ex. claymore/ch_1")
    ap.add_argument("--engine", choices=sorted(ENGINES), default="kimi")   # v1.70 : K3 v2.2 = 4 graves/60 pages vs Gemini 7 (21/09)
    ap.add_argument("--pages", default="", help="plage, ex. 1-20 (defaut : tout)")
    ap.add_argument("--batch", type=int, default=0, help="pages par appel vision (defaut : 2 en v2, 4 en v1)")
    ap.add_argument("--prompt", choices=["v1", "v2"], default="v2",
                    help="v2 = faits + fiche des personnages prouvee + recit sans invention (defaut, 21/09)")
    ap.add_argument("--voice", default="Charon", help="voix Chirp 3 HD (Charon, Fenrir, Orus, Kore...), dans la langue de --langue")
    ap.add_argument("--langue", choices=sorted(LANGUES_NARR), default="fr",
                    help="v2.0.0 : langue de la narration et de la voix (defaut fr ; en = anglais, prompt v2 seulement)")
    ap.add_argument("--rate", type=float, default=1.05)
    ap.add_argument("--tts", choices=["cloud", "local"], default="cloud",
                    help="v2.4.0 : voix en ligne (Chirp 3 HD, defaut) ou LOCALE (Chatterbox, carte graphique, 0 $)")
    ap.add_argument("--tag", default="", help="nom du run (defaut : <engine>-<voix>)")
    ap.add_argument("--no-tts", action="store_true")
    ap.add_argument("--portraits", action="store_true",
                    help="v2.4 : portraits de reference des personnages nommes (mesure SANS gain le 21/09 : 3/5/2 graves"
                         " contre 3/3/3 sans ; Raki et Zaki se ressemblent, l'exemple visuel les confond)")
    ap.add_argument("--verif", action="store_true", help="v2 : verification des attributions nommees (mesuree SANS gain le 21/09, en option)")
    ap.add_argument("--reuse-vision", default="", help="reprend l'etape vision d'un run existant (tag)")
    ap.add_argument("--reprendre-moderation", choices=["", "gemini", "kimi", "local", "voisines"], default="",
                    help="v2.7.0 (avec --reuse-vision) : ne relit QUE les pages refusees par la moderation -- avec un autre "
                         "moteur, en local (carte graphique), ou « voisines » (recit de transition depuis les pages voisines)")
    ap.add_argument("--noms", choices=["v2", "v3"], default="v2",
                    help="v3 (v1.75) : ecarte les noms dont le porteur n'est jamais dessine ; teint + tenue dans la fiche")
    ap.add_argument("--serie", action="store_true",
                    help="v1.74 (etape 2) : reprend les noms prouves dans les AUTRES chapitres de la serie")
    a = ap.parse_args()
    global NOMS_VERSION, LANGUE
    NOMS_VERSION = a.noms
    LANGUE = a.langue
    if LANGUE != "fr" and a.prompt != "v2":
        raise SystemExit("--langue %s : seulement avec --prompt v2 (le v1 ecrit sa narration des la lecture)" % LANGUE)
    SECRET = _secret()

    chap_dir = os.path.normpath(os.path.join(SOURCES, a.chapitre))
    if not chap_dir.startswith(SOURCES + os.sep) or not os.path.isfile(os.path.join(chap_dir, "manifest.json")):
        raise SystemExit("chapitre introuvable sous sources/ : " + a.chapitre)
    # v2.4.0 : la voix locale ne remplace jamais l'en-ligne (etiquette distincte)
    # S7 (24/09) : « Voix@1.0 » = voix LOCALE avec son ton (intensite d'expression) ; le tag l'ecrit « voix-ton10 » (sans point : les tags n'en acceptent pas)
    tag = a.tag or "%s-%s" % (a.engine, a.voice.lower().replace("@", "-ton").replace(".", "")) + ("" if a.langue == "fr" else "-" + a.langue) + ("-local" if a.tts == "local" else "")
    outdir = os.path.join(chap_dir, "narration", tag)
    os.makedirs(outdir, exist_ok=True)
    PROGRESS = os.path.join(outdir, "progress.json")
    man, pages = pages_du_chapitre(chap_dir, a.pages)
    stats = dict(vision_tokens_in=0, vision_tokens_out=0, cout_vision=0.0, cout_recit=0.0, cout_tts=0.0,
                 tts_chars=0, vision_s=0.0, recit_s=0.0, tts_s=0.0)
    STATS = stats
    journal("start", chapitre=a.chapitre, engine=a.engine, pages=len(pages), tag=tag)
    t0 = time.time()

    if a.reuse_vision:
        # v2.2.0 : vision.json = l'analyse des pages, gardee MEME si la suite echoue (~90 % du cout d'un run)
        src = os.path.join(chap_dir, "narration", a.reuse_vision)
        src = next((os.path.join(src, f) for f in ("narration.json", "vision.json") if os.path.isfile(os.path.join(src, f))),
                   os.path.join(src, "narration.json"))
        log("  analyse des pages reprise de " + os.path.relpath(src, SOURCES))
        prev = json.load(open(src, encoding="utf-8"))
        vis = [dict(page=p["page"], file=p["file"], type=p["type"], faits=p.get("faits_avant_verif") or p["faits"],
                    narration=p.get("narration_vision", p["narration"])) for p in prev["pages"]]
        if a.pages:            # v2.9.0 (24/09) : la PLAGE s'applique aussi a une analyse reprise (ignoree avant : 40 p. au lieu de 2)
            voulues = {p["file"] for p in pages}
            vis = [v for v in vis if v["file"] in voulues]
        resume, persos = prev.get("resume", ""), prev.get("personnages", [])
        noms = (prev.get("stats") or {}).get("noms") or {}
        for k in ("vision_tokens_in", "vision_tokens_out", "cout_vision", "vision_s"):
            stats[k] = prev["stats"][k]
        stats["cout_vision_recopie"] = stats.get("cout_vision", 0)          # v2.7.0 : pour le registre des depenses
        if a.reprendre_moderation:
            vis = reprendre_moderation(chap_dir, vis, a.reprendre_moderation, stats, noms)
    else:
        if a.prompt == "v2":
            serie = fiche_serie(chap_dir) if a.serie else None
            if serie is not None:
                log("  fiche de la serie : " + (", ".join("%s (%s)" % (n, ",".join(c["chapitres"])) for n, c in serie.items()) or "vide"))
            noms = etape_noms(chap_dir, pages, stats, outdir if a.portraits else None, serie)
            vis, resume, persos = etape_vision_v2(chap_dir, pages, a.engine, a.batch or 2, stats, noms)
        else:
            vis, resume, persos = etape_vision(chap_dir, pages, a.engine, a.batch or 4, stats)
    def _resultat(pages_):
        return {"version": VERSION, "prompt": a.prompt, "reuse_vision": a.reuse_vision or None, "serie": bool(a.serie), "noms_version": a.noms, "chapitre": a.chapitre, "title": man.get("title"), "chapter": man.get("chapter"),
                "tag": tag, "engine": a.engine, "model": ENGINES[a.engine][1], "voice": a.voice, "rate": a.rate, "langue": a.langue, "tts": a.tts,
                "titre": titre, "resume": resume, "personnages": persos, "created_at": datetime.now().isoformat(timespec="seconds"),
                "stats": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in stats.items()},
                "pages": pages_}

    def _echec(msg):
        """v2.2.0 : un run qui n'a rien produit d'ecoutable ECHOUE (code 3), il ne se dit plus « ok »."""
        log("  ECHEC : " + msg)
        journal("echec_resultat", err=msg)
        depense = round(sum(v for k, v in stats.items() if k.startswith("cout_") and isinstance(v, float)), 4)
        progres("echec", 0, 1, erreur=msg, cout=depense)
        print(json.dumps({"ok": False, "error": msg, "dir": os.path.relpath(outdir, SOURCES).replace("\\", "/")},
                         ensure_ascii=False))
        raise SystemExit(3)

    titre = ""
    if a.prompt == "v2":                # v2.3.0 : alphabet latin AVANT le recit (fiche, faits, presents, resume)
        vis, resume, persos, noms, _ = latiniser(vis, resume, persos, noms, man.get("title"), stats)
        if stats.get("noms") is not None:
            stats["noms"] = noms
    if not a.reuse_vision:              # v2.2.0 : l'analyse payee survit a un echec de la suite
        with open(os.path.join(outdir, "vision.json"), "w", encoding="utf-8") as f:
            json.dump(_resultat(vis), f, ensure_ascii=False, indent=1)
    if a.prompt == "v2" and a.verif:
        vis = etape_verif(chap_dir, vis, noms if a.prompt == "v2" else {}, stats)
        stats["noms"] = noms
    progres("recit", 0, 1)
    try:
        titre, vis = (etape_recit_v2 if a.prompt == "v2" else etape_recit)(vis, resume, persos, stats)
    except Exception as e:              # v1 : la narration de la lecture reste ; v2 : il n'y en a PAS (garde-fou ci-dessous)
        log("  recit en echec (%s)%s" % (e, " : narration vision conservee" if a.prompt == "v1" else ""))
        journal("recit_echec", err=str(e)[:200])
        titre = ""
    # v2.6.0 (feuille de route 4-decies) : les pages REFUSEES par la moderation sont mises de cote, le chapitre continue,
    # et une alerte persistante les signale a Quang (bouton d'activite, onglet « A traiter »)
    refusees = {}
    for m_ in stats.get("moderation") or []:
        refusees.setdefault(m_["etape"], []).append(m_)
    for etape_, lst in refusees.items():
        for p in vis:
            if p["page"] in {x["page"] for x in lst}:
                p["moderation"] = lst[0]["motif"]
        mod.ajouter_alerte(a.chapitre, "narration", [x["page"] for x in lst], lst[0]["moteur"], lst[0]["motif"],
                           detail="etape %s" % etape_, tag=tag)
        log("  ALERTE moderation : %d page(s) refusee(s) a l'etape %s -> a traiter dans l'app" % (len(lst), etape_))
    histoire = [p for p in vis if p.get("type") == "histoire" and not p.get("moderation")]
    vides = [p["page"] for p in histoire if not (p.get("narration") or "").strip()]
    if not histoire:
        _echec("aucune page d'histoire reconnue")
    if len(vides) > max(2, len(histoire) // 10):
        _echec("narration vide sur %d page(s) d'histoire sur %d (%s) -- analyse des pages gardee, un nouvel essai la reprend"
               % (len(vides), len(histoire), ",".join(map(str, vides[:12])) + ("..." if len(vides) > 12 else "")))
    if vides:
        log("  %d page(s) d'histoire restee(s) muette(s) : %s" % (len(vides), vides))
    cjk = [p["page"] for p in vis if re.search(_RE_CJK, p.get("narration") or "")]
    if cjk:                             # v2.3.0 : jamais de phrase amputee en silence (« En bas, lève sa main mécanique »)
        _echec("caracteres chinois/japonais/coreens dans la narration des pages %s (ex. %s) -- analyse gardee, un nouvel essai la reprend"
               % (",".join(map(str, cjk[:12])), (next(p for p in vis if p["page"] == cjk[0]).get("narration") or "")[:80]))
    if not a.no_tts:
        if a.tts == "local":
            etape_voix_locale(vis, outdir, a.voice, stats)
        else:
            etape_voix(vis, outdir, a.voice, a.rate, stats)
        sans_voix = [p["page"] for p in vis if (p.get("narration") or "").strip() and not p.get("audio")]
        if sans_voix or not any(p.get("audio") for p in vis):
            _echec("voix manquante sur %d page(s) narree(s) (%s)" % (len(sans_voix), ",".join(map(str, sans_voix[:12]))))
    stats["total_s"] = round(time.time() - t0, 1)
    stats["cout_total"] = round(stats["cout_vision"] + stats["cout_recit"] + stats["cout_tts"]
                                + stats.get("cout_noms", 0.0) + stats.get("cout_verif", 0.0), 4)
    # v1.72 : un run --reuse-vision recopie les stats de lecture de son run source : le suivi des couts
    # ne doit compter QUE ce que ce run a depense (recit + voix), sinon la lecture est comptee deux fois.
    res = _resultat(vis)
    with open(os.path.join(outdir, "narration.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    progres("fini", 1, 1, cout=stats["cout_total"])
    journal("done", tag=tag, cout=stats["cout_total"], s=stats["total_s"])
    if a.reprendre_moderation and not stats.get("moderation"):      # v2.7.0 : plus rien de refuse -> alerte close
        n_ = mod.clore(a.chapitre, "narration", note="traitee : " + a.reprendre_moderation)
        log("  moderation : %d alerte(s) close(s), videos du chapitre relancees" % n_)
    # v2.6.0 : registre des depenses en AJOUT SEUL (ce qui a ete paye ICI : jamais l'analyse recopiee d'un autre run)
    dep.noter("narration", a.chapitre, tag, a.engine,
              stats["cout_total"] - (stats.get("cout_vision_recopie", 0) if a.reuse_vision else 0),
              reuse=a.reuse_vision or None, voix=a.tts)
    print(json.dumps({"ok": True, "dir": os.path.relpath(outdir, SOURCES).replace("\\", "/"),
                      "pages": len(vis), "stats": res["stats"]}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except BaseException as e:          # v1.98.0 : la CAUSE d'un echec reste dans le journal persistant (le run.log
        if not isinstance(e, SystemExit) or e.code not in (0, None):     # d'un nouvel essai l'ecrasait)
            journal("echec", err=(type(e).__name__ + " : " + str(e))[:400])
        raise
