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

VERSION = "1.69.0"
HERE = os.path.dirname(os.path.abspath(__file__))
SOURCES = os.path.normpath(os.path.join(HERE, "..", "sources"))
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
           "gemini": ("/api/gemini/v1beta/models/gemini-3.6-flash:generateContent", "gemini-3.6-flash")}


def appel_vision(engine, system, content, max_tokens):
    """Un appel vision, quel que soit le moteur. Rend (texte, usage au format OpenAI)."""
    path, model = ENGINES[engine]
    if engine != "gemini":
        body = {"model": model, "max_tokens": max_tokens,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": content}]}
        if engine == "pixtral":
            body["temperature"] = 0.1
        r = post(path, body)
        return r["choices"][0]["message"].get("content"), (r.get("usage") or {})
    parts = []
    for c in content:
        if c["type"] == "text":
            parts.append({"text": c["text"]})
        else:
            mime, data = c["image_url"]["url"][5:].split(";base64,", 1)
            parts.append({"inline_data": {"mime_type": mime, "data": data}})
    r = post(path, {"systemInstruction": {"parts": [{"text": system}]},
                    "contents": [{"role": "user", "parts": parts}],
                    "generationConfig": {"maxOutputTokens": max_tokens, "responseMimeType": "application/json"}})
    um = r.get("usageMetadata") or {}
    texte = "".join(p.get("text", "") for p in ((r.get("candidates") or [{}])[0].get("content") or {}).get("parts", []))
    return texte, {"prompt_tokens": um.get("promptTokenCount", 0),
                   "completion_tokens": um.get("candidatesTokenCount", 0) + um.get("thoughtsTokenCount", 0)}


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
            if e.code not in (429, 500, 502, 503, 504, 520, 521, 522, 523, 524):   # 52x = Cloudflare, passager
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


def _fiche_texte(fiche):
    return json.dumps([dict(id=k, **v) for k, v in fiche.items()], ensure_ascii=False)


def etape_vision_v2(chap_dir, pages, engine, batch, stats, noms=None):
    path, model = ENGINES[engine]
    fiche, resume, sortie, journal_fiche = {}, "", [], []
    for nom, v in (noms or {}).items():        # v2.2 : noms FIGES par la passe des noms (votes)
        fiche[nom.lower()] = {"description": "%s, %s" % (v["age"], v["cheveux"]), "nom": nom,
                              "preuve": "vote %s, pages %s" % (v["votes"], v["pages"]), "fige": True}
    for i in range(0, len(pages), batch):
        lot = pages[i:i + batch]
        nums = [p["num"] for p in lot]
        content = [{"type": "text", "text": ("NOMS ETABLIS (verifies par vote, ne les change jamais, n'en ajoute "
                                             "aucun ; identifie ces personnages par leur AGE et leurs cheveux) : "
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
        for essai in range(2):
            texte, u = appel_vision(engine, SYS_VISION_V2, content, 8000)
            stats["vision_tokens_in"] += u.get("prompt_tokens", 0)
            stats["vision_tokens_out"] += u.get("completion_tokens", 0)
            stats["cout_vision"] += cout(model, u)
            try:
                j = parse_json(texte)
                break
            except Exception as e:
                log("  lot %s : JSON illisible (%s), nouvel essai" % (nums, e))
        if j is None:
            raise RuntimeError("lot %s : JSON illisible deux fois" % nums)
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
        progres("vision", min(i + batch, len(pages)), len(pages))
        journal("vision_lot_v2", engine=engine, pages=nums, s=round(dt, 1), fiche=len(fiche))
        log("  vision v2 %s pages %s : %.1fs (fiche : %s)" % (engine, nums, dt,
            ", ".join("%s=%s" % (k, v["nom"] or "?") for k, v in fiche.items())))
    persos = [{"id": k, "nom": v["nom"] or "", "qui": v["description"], "preuve": v["preuve"]} for k, v in fiche.items()]
    stats["fiche_journal"] = journal_fiche
    return sortie, resume, persos


def etape_recit_v2(pages, resume, persos, stats):
    entree = [{"page": p["page"], "type": p["type"], "faits": p["faits"]} for p in pages if p["type"] == "histoire"]
    if not entree:
        return "", pages
    body = {"model": "deepseek-v4-flash", "max_tokens": 8000, "temperature": 0.6,
            "thinking": {"type": "disabled"},
            "messages": [{"role": "system", "content": SYS_RECIT_V2},
                         {"role": "user", "content": "Fiche des personnages : " + json.dumps(persos, ensure_ascii=False)
                          + "\nPages :\n" + json.dumps(entree, ensure_ascii=False)}]}
    t = time.time()
    r = post("/api/deepseek", body)
    stats["cout_recit"] += cout("deepseek-v4-flash", r.get("usage") or {})
    stats["recit_s"] += time.time() - t
    j = parse_json(r["choices"][0]["message"].get("content"))
    neuf = {}
    for x in j.get("pages") or []:
        try: neuf[int(x["page"])] = x.get("narration", "")
        except (KeyError, TypeError, ValueError): pass
    for p in pages:
        p["narration_vision"] = ""
        p["narration"] = neuf.get(p["page"], "") if p["type"] == "histoire" else ""
    manq = [p["page"] for p in entree if p["page"] not in neuf or not (neuf[p["page"]] or "").strip()]
    if manq:                                  # K3 v2 : la p20 (essentielle) est sortie VIDE -> on redemande
        log("  recit : pages rendues vides %s -> nouvelle demande" % manq)
        body["messages"][1]["content"] += ("\nATTENTION : ecris OBLIGATOIREMENT une narration non vide pour les pages "
                                           + ", ".join(map(str, manq)) + ".")
        r = post("/api/deepseek", body)
        stats["cout_recit"] += cout("deepseek-v4-flash", r.get("usage") or {})
        for x in (parse_json(r["choices"][0]["message"].get("content")).get("pages") or []):
            try:
                if int(x["page"]) in manq and (x.get("narration") or "").strip():
                    neuf[int(x["page"])] = x["narration"]
            except (KeyError, TypeError, ValueError):
                pass
        for p in pages:
            if p["page"] in manq and p["type"] == "histoire":
                p["narration"] = neuf.get(p["page"], "")
        manq = [m for m in manq if not (neuf.get(m) or "").strip()]
    journal("recit_v2", s=round(stats["recit_s"], 1), manquantes=manq)
    return j.get("titre", ""), pages


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
          "\"enfant|adolescent|adulte\",\"porteur_cheveux\":\"...\",\"dit_par\":\"...\",\"porteur_box\":[0,0,0,0]}]}")
VOTES_NOMS = 3


def _question_noms(chap_dir, p, stats):
    img = base64.b64encode(page_jpeg(os.path.join(chap_dir, p["file"]))).decode()
    content = [{"type": "text", "text": Q_NOMS},
               {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + img}}]
    txt, u = appel_vision("gemini", "Reponds uniquement en JSON.", content, 4000)
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


def etape_noms(chap_dir, pages, stats, outdir=None):
    """Rend {nom: {age, cheveux, votes, pages, portrait}} : noms PROUVES par la majorite des votes, et pour
    chacun un portrait decoupe (v1.69 : exemple visuel, pour ne plus nommer un anonyme qui lui ressemble)."""
    t = time.time()
    votes = {}                                   # nom -> liste de (page, age, cheveux, box, fichier)
    for p in pages:
        premiers = _question_noms(chap_dir, p, stats)
        lus = [premiers]
        if premiers:                             # un prenom lu : 2 votes de plus sur CETTE page
            lus += [_question_noms(chap_dir, p, stats) for _ in range(VOTES_NOMS - 1)]
        for lot in lus:
            for x in lot:
                nom = x["nom"].strip().strip(".,!?").capitalize()
                votes.setdefault(nom, []).append((p["num"], x.get("porteur_age") or "?", x.get("porteur_cheveux") or "",
                                                  x.get("porteur_box"), p["file"]))
        progres("noms", p["num"], pages[-1]["num"])
    retenus = {}
    for nom, vs in votes.items():
        pages_nom = sorted({v[0] for v in vs})
        ages = {}
        for v in vs:
            ages[v[1]] = ages.get(v[1], 0) + 1
        age, n_age = max(ages.items(), key=lambda kv: kv[1])
        # un nom vu sur une SEULE page et une seule fois = lecture douteuse : on ne le fige pas
        if len(vs) < 2:
            continue
        cheveux = max((v[2] for v in vs if v[1] == age), key=len, default="")
        retenus[nom] = {"age": age, "cheveux": cheveux, "votes": "%d/%d" % (n_age, len(vs)), "pages": pages_nom}
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
    stats["noms"] = retenus
    journal("noms", retenus=retenus)
    log("  noms figes : " + (", ".join("%s=%s (%s)" % (k, v["age"], v["votes"]) for k, v in retenus.items()) or "aucun"))
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
    ap.add_argument("--engine", choices=sorted(ENGINES), default="gemini")   # v1.68 : banc de fidelite 21/09
    ap.add_argument("--pages", default="", help="plage, ex. 1-20 (defaut : tout)")
    ap.add_argument("--batch", type=int, default=0, help="pages par appel vision (defaut : 2 en v2, 4 en v1)")
    ap.add_argument("--prompt", choices=["v1", "v2"], default="v2",
                    help="v2 = faits + fiche des personnages prouvee + recit sans invention (defaut, 21/09)")
    ap.add_argument("--voice", default="Charon", help="voix Chirp 3 HD fr-FR (Charon, Fenrir, Orus, Kore...)")
    ap.add_argument("--rate", type=float, default=1.05)
    ap.add_argument("--tag", default="", help="nom du run (defaut : <engine>-<voix>)")
    ap.add_argument("--no-tts", action="store_true")
    ap.add_argument("--portraits", action="store_true",
                    help="v2.4 : portraits de reference des personnages nommes (mesure SANS gain le 21/09 : 3/5/2 graves"
                         " contre 3/3/3 sans ; Raki et Zaki se ressemblent, l'exemple visuel les confond)")
    ap.add_argument("--verif", action="store_true", help="v2 : verification des attributions nommees (mesuree SANS gain le 21/09, en option)")
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
        vis = [dict(page=p["page"], file=p["file"], type=p["type"], faits=p.get("faits_avant_verif") or p["faits"],
                    narration=p.get("narration_vision", p["narration"])) for p in prev["pages"]]
        resume, persos = prev.get("resume", ""), prev.get("personnages", [])
        noms = (prev.get("stats") or {}).get("noms") or {}
        for k in ("vision_tokens_in", "vision_tokens_out", "cout_vision", "vision_s"):
            stats[k] = prev["stats"][k]
    else:
        if a.prompt == "v2":
            noms = etape_noms(chap_dir, pages, stats, outdir if a.portraits else None)
            vis, resume, persos = etape_vision_v2(chap_dir, pages, a.engine, a.batch or 2, stats, noms)
        else:
            vis, resume, persos = etape_vision(chap_dir, pages, a.engine, a.batch or 4, stats)
    if a.prompt == "v2" and a.verif:
        vis = etape_verif(chap_dir, vis, noms if a.prompt == "v2" else {}, stats)
        stats["noms"] = noms
    progres("recit", 0, 1)
    try:
        titre, vis = (etape_recit_v2 if a.prompt == "v2" else etape_recit)(vis, resume, persos, stats)
    except Exception as e:              # le recit est un polissage : sans lui, la narration vision reste lisible
        log("  recit en echec (%s) : narration vision conservee" % e)
        journal("recit_echec", err=str(e)[:200])
        titre = ""
    if not a.no_tts:
        etape_voix(vis, outdir, a.voice, a.rate, stats)
    stats["total_s"] = round(time.time() - t0, 1)
    stats["cout_total"] = round(stats["cout_vision"] + stats["cout_recit"] + stats["cout_tts"]
                                + stats.get("cout_noms", 0.0) + stats.get("cout_verif", 0.0), 4)
    res = {"version": VERSION, "prompt": a.prompt, "chapitre": a.chapitre, "title": man.get("title"), "chapter": man.get("chapter"),
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
