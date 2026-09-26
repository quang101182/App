# -*- coding: utf-8 -*-
"""MODE « DIALOGUES » de Manga Studio -- une voix par personnage (ROADMAP § 4-septdecies, maquette_dialogues_v2.html validee
par Quang le 26/09/2026 23h58). SEPARE de la narration : il LIT la traduction francaise, n'ecrit JAMAIS dans narration/ ni
traduction/.

  python dialogues.py preparer <serie/ch_N> [--pages a-b]   qui parle, quel ton, quoi lire (Gemini, pages vues) -- AUCUNE voix
  python dialogues.py voix     <serie/ch_N> [--pages a-b]   ElevenLabs v3, seules les voix manquantes ou modifiees ;
                                                            quota epuise = ARRET (code 4), aucun autre moteur

Fichiers :
  <serie>/dialogues_distribution.json   la distribution du MANGA (commune a tous les chapitres) : nom, alias, genre, voix
                                        ElevenLabs, expressivite, vitesse, couleur ; narrateur (encarts NON lus par defaut)
  <serie>/ch_N/dialogues/dialogues.json les repliques du chapitre (texte d'origine + corrige, qui, ton, lire, contour de bulle)
  <serie>/ch_N/dialogues/progress.json  l'avancement lu par l'app ; run.log a cote
Decisions de Quang : toujours lu en FRANCAIS (traduction fr obligatoire) ; relais de moderation = SON interrupteur ;
aucun moteur de secours pour les voix ; une correction reste propre aux Dialogues.
"""
import argparse, base64, json, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import narrate_chapter as nc
import moderation as mod
import depenses
import reglages

VERSION = "1.4.1"   # 1.4.1 : page refusee lisible une fois QUI choisi par Quang ; plan dit « a_traiter »
#   # 1.4.0 (27/09) : lot (plusieurs chapitres, arret net au quota, reprise)
#   # 1.3.0 (27/09) : plan (etat de chaque replique + credits a prevoir, sans appel paye)
#   # 1.2.0 (27/09) : ecouter (▶ de la preparation ; la voix exacte d'une replique devient definitive)
#   # 1.1.0 (27/09) : D2 voix ElevenLabs v3 (empreintes, balises, arret net au quota)
SOURCES = os.environ.get("MANGA_SOURCES_DIR") or os.path.join(HERE, "..", "sources")
LOT_PAGES = 4                       # pages par appel (essai 26/09 : 3 pages = 12 s, 5 pages = 26 s)
PALETTE = ["#ff5fa2", "#ffb347", "#6fb8ff", "#b58cff", "#5fe3a1", "#ff7a5c", "#f5e663", "#4fd6e8", "#e88aff", "#c7a17a"]
NARRATEUR_VOIX = "JBFqnCBsd6RMkjVDRZzb"     # George -- homme, conteur pose et constant (Quang 26/09 23h55 : un homme, constant)
DISTRIB_VERSION = 1


def log(*a):
    nc.log(*a)


# ---------------------------------------------------------------- fichiers
def chemins(chap):
    chap_dir = os.path.join(SOURCES, chap.replace("/", os.sep))
    serie_dir = os.path.dirname(chap_dir)
    dd = os.path.join(chap_dir, "dialogues")
    return chap_dir, serie_dir, dd


def lire_json(f, defaut=None):
    try:
        return json.load(open(f, encoding="utf-8"))
    except (OSError, ValueError):
        return defaut


def ecrire_json(f, doc):
    """Ecriture atomique (l'app peut lire au meme moment)."""
    os.makedirs(os.path.dirname(f), exist_ok=True)
    tmp = f + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as h:
        json.dump(doc, h, ensure_ascii=False, indent=1)
    os.replace(tmp, f)


def distribution(serie_dir):
    d = lire_json(os.path.join(serie_dir, "dialogues_distribution.json")) or {}
    d.setdefault("version", DISTRIB_VERSION)
    d.setdefault("persos", [])
    d.setdefault("narrateur", {"nom": "Narrateur", "voix_el": NARRATEUR_VOIX, "lire": False, "expressivite": 1,
                               "vitesse": 1.05, "couleur": "#9aa6b8"})
    d.setdefault("tons", True)
    d.setdefault("balises", {})
    return d


# ---------------------------------------------------------------- catalogue de voix ElevenLabs (via le gateway)
def catalogue_el():
    """[{id, nom, genre, age, desc}] ; vide si le gateway ne repond pas (la preparation ne choisit alors pas de voix :
    Quang la choisira -- jamais une voix inventee)."""
    import urllib.request
    try:
        r = urllib.request.Request(nc.GATEWAY + "/api/elevenlabs/v1/voices",
                                   headers={"Authorization": "Bearer " + nc.SECRET, "User-Agent": "manga-studio/dialogues-" + VERSION})
        v = json.load(urllib.request.urlopen(r, timeout=30))["voices"]
    except Exception as e:
        log("  catalogue ElevenLabs illisible (%s) : voix a choisir a la main" % str(e)[:120])
        return []
    out = []
    for x in v:
        lb = x.get("labels") or {}
        out.append({"id": x["voice_id"], "nom": x["name"].split(" - ")[0].strip(), "genre": lb.get("gender") or "?",
                    "age": lb.get("age") or "?", "desc": (x["name"].split(" - ", 1)[1] if " - " in x["name"] else "")
                    or lb.get("descriptive") or lb.get("description") or ""})
    return out


# ---------------------------------------------------------------- contour de la bulle (halo du lecteur)
def contour_bulle(img_path, box, cache={}):
    """Contour REEL de la zone blanche de la bulle (meme principe que ingest_page : floodFill depuis le pixel le plus clair de
    la boite), simplifie, en FRACTIONS de la page. Repli : None (le lecteur dessine un ovale doux dans la boite)."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        return None
    if img_path not in cache:
        im = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        cache.clear()
        cache[img_path] = im
    gris = cache[img_path]
    if gris is None:
        return None
    H, W = gris.shape[:2]
    x1, y1 = int(box["x"] * W), int(box["y"] * H)
    x2, y2 = min(W, x1 + max(4, int(box["w"] * W))), min(H, y1 + max(4, int(box["h"] * H)))
    boite = gris[y1:y2, x1:x2]
    if boite.size == 0 or int(boite.max()) < 150:
        return None
    oy, ox = np.unravel_index(int(np.argmax(boite)), boite.shape)
    m = np.zeros((H + 2, W + 2), np.uint8)
    cv2.floodFill(gris.copy(), m, (x1 + int(ox), y1 + int(oy)), 0, (60,), (60,),
                  4 | cv2.FLOODFILL_MASK_ONLY | cv2.FLOODFILL_FIXED_RANGE | (255 << 8))
    comp = (m[1:H + 1, 1:W + 1] > 0).astype(np.uint8)
    aire = int(comp.sum())
    bw, bh = x2 - x1, y2 - y1
    if aire == 0 or aire > 0.08 * W * H or aire > 12 * bw * bh:   # fond ouvert (pas une bulle) -> repli ovale
        return None
    comp = cv2.morphologyEx(comp, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    cs, _ = cv2.findContours(comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cs:
        return None
    c = cv2.approxPolyDP(max(cs, key=cv2.contourArea), max(1.5, 0.004 * max(W, H)), True)
    return [[round(float(p[0][0]) / W, 4), round(float(p[0][1]) / H, 4)] for p in c]


# ---------------------------------------------------------------- l'appel « qui parle / quel ton / quoi lire »
SYS = """Tu prepares le DOUBLAGE en francais d'un manga : chaque replique sera lue par la voix de son personnage.
Tu recois des pages (deja traduites en francais, dans l'ordre de lecture) et, pour chaque page, la liste NUMEROTEE des bulles
(id, type, texte, position x,y,w,h en fractions de la page). Tu recois aussi la DISTRIBUTION DU MANGA (personnages deja connus
d'autres chapitres) et des indices sur ce chapitre : l'IMAGE fait foi.

1. Pour CHAQUE bulle, QUI la prononce (queue de la bulle, case, qui est dessine, sens de la phrase) :
   - un personnage CONNU : son nom EXACT de la distribution (n'invente pas un 2e nom pour lui) ;
   - un personnage NOUVEAU : un nom court (son vrai nom s'il est dit ou ecrit, sinon une description courte comme « Vieil
     homme ») et decris-le dans "nouveaux" ;
   - « narrateur » pour un encart de recit sans personnage ; le monologue d'un personnage (souvenir a la 1re personne) = CE
     personnage ;
   - « inconnu » si tu ne peux pas trancher : n'invente pas.
2. "lire": false pour ce qui N'EST PAS PRONONCE : bruitage, onomatopee, sensation ou effet ecrit sur le dessin (« CHAIR DE
   POULE », « BOUM »), texte du decor (panneau, affiche), bulle sans mots (« ! », « ... ») ; sinon "lire": true.
3. D'abord l'AMBIANCE de ces pages (style du manga, tension). Puis pour chaque replique lue, le TON en 2-4 mots de consigne
   d'acteur, en francais, au service de l'ambiance (scene tendue : pas de jeu comique ni surjoue).
4. Pour chaque NOUVEAU personnage : genre (homme|femme|?), age apparent, une phrase sur sa facon de parler, et la voix la plus
   juste dans le CATALOGUE ci-dessous (id exact), differente de celles deja prises si possible.
CATALOGUE : %s

Reponds UNIQUEMENT en JSON :
{"ambiance": "...",
 "nouveaux": [{"nom": "...", "genre": "...", "age": "...", "fiche": "...", "voix_el": "<id du catalogue>"}],
 "repliques": [{"page": 5, "id": 2, "qui": "...", "ton": "...", "lire": true, "indice": "ce qui designe le locuteur, 10 mots max"}]}
"""


def appel(moteur, sys_, content, stats):
    t0 = time.time()
    txt, usage = nc.appel_vision(moteur, sys_, content, 16000)
    moteur = getattr(nc.appel_vision, "moteur", moteur)          # relais : le moteur reellement appele
    c = nc.cout(nc.ENGINES[moteur][1], usage)
    stats["cout_preparation"] = stats.get("cout_preparation", 0.0) + c
    stats.setdefault("moteurs", {})[moteur] = stats.get("moteurs", {}).get(moteur, 0) + 1
    return nc.parse_json(txt), round(time.time() - t0, 1)


def preparer_lot(chap_dir, lot, distrib, narr, cat, stats):
    """Un lot de pages -> reponse JSON. Refus de moderation : le lot est scinde page par page ; une page refusee passe au
    relais SI l'interrupteur de Quang est actif (meme chaine que la narration), sinon -> « a traiter »."""
    connus = [{"nom": p["nom"], "genre": p.get("genre"), "age": p.get("age"), "fiche": p.get("fiche"),
               "alias": p.get("alias", [])} for p in distrib["persos"]]
    faits = {p["page"]: p.get("faits") for p in (narr or {}).get("pages") or []}
    content = [{"type": "text", "text": "DISTRIBUTION DU MANGA (connus) : " + json.dumps(connus, ensure_ascii=False)}]
    if narr and narr.get("personnages"):
        content.append({"type": "text", "text": "Indices de la narration de ce chapitre (ids p1, p2... = noms provisoires) : "
                        + json.dumps([{"id": p.get("id"), "nom": p.get("nom"), "qui": p.get("qui")} for p in narr["personnages"]],
                                     ensure_ascii=False)})
    for p in lot:
        img = os.path.join(chap_dir, "traduction", "fr", p["file"])
        b64 = base64.b64encode(nc.page_jpeg(img, 1200)).decode()
        content.append({"type": "text", "text": "=== PAGE %d ===\nFaits (indice) : %s\nBulles : %s" % (
            p["page"], faits.get(p["page"], "?"), json.dumps([{"id": b["id"], "type": b["type"], "texte": b["trad"],
                                                                "pos": [round(b["box"][k], 3) for k in ("x", "y", "w", "h")]}
                                                               for b in p["_bulles"]], ensure_ascii=False))})
        content.append({"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + b64}})
    cat_txt = "; ".join("%s = %s (%s, %s, %s)" % (v["id"], v["nom"], v["genre"], v["age"], v["desc"]) for v in cat) or "(indisponible : voix_el vide)"
    return appel("gemini", SYS % cat_txt, content, stats)


def preparer_pages(chap_dir, d, pages, distrib, narr, cat, stats, relais):
    """-> (reponses par page, pages a traiter). Scinde sur refus, relais selon l'interrupteur."""
    reponses, a_traiter = [], []
    lots = [pages[i:i + LOT_PAGES] for i in range(0, len(pages), LOT_PAGES)]
    fait = 0
    while lots:
        lot = lots.pop(0)
        nums = [p["page"] for p in lot]
        nc.progres("preparation", fait, len(pages), pages=nums)
        try:
            r, dt = preparer_lot(chap_dir, lot, distrib, narr, cat, stats)
            log("  pages %s : %d repliques en %.1f s" % (nums, len(r.get("repliques") or []), dt))
            reponses.append(r)
            fait += len(lot)
        except mod.Refus as e:
            stats["cout_preparation"] = stats.get("cout_preparation", 0.0) + nc.cout(nc.ENGINES[e.moteur][1] if e.moteur in nc.ENGINES else "gemini-3.6-flash", getattr(e, "usage", None) or {})
            if len(lot) > 1:
                log("  pages %s REFUSEES (%s) -> une par une" % (nums, e.motif[:80]))
                lots[:0] = [[p] for p in lot]
                continue
            p = lot[0]
            lu = None
            for autre in (nc.RELAIS_CHAINE.get("gemini", []) if relais else []):
                try:
                    log("  page %d refusee par gemini -> RELAIS %s" % (p["page"], autre))
                    r, dt = _appel_relais(chap_dir, [p], distrib, narr, cat, stats, autre)
                    lu = autre
                    reponses.append(r)
                    stats.setdefault("relais", []).append({"page": p["page"], "de": "gemini", "vers": autre})
                    break
                except mod.Refus as e2:
                    e = e2
                    continue
                except Exception as e3:
                    log("  relais %s en echec : %s" % (autre, str(e3)[:120]))
                    continue
            if lu is None:
                a_traiter.append(p["page"])
                mod.ajouter_alerte(d, "dialogues", [p["page"]], e.moteur, e.motif, detail="preparation des dialogues")
                log("  page %d A TRAITER (%s)" % (p["page"], e.motif[:80]))
            fait += 1
    return reponses, a_traiter


def _appel_relais(chap_dir, lot, distrib, narr, cat, stats, moteur):
    """preparer_lot avec un autre moteur (relais de moderation) : meme demande, meme contexte."""
    orig = nc.appel_vision

    def via(m, s, c, mx, **kw):
        return orig(moteur, s, c, mx, **kw)
    via.moteur = moteur
    try:
        nc.appel_vision = via
        return preparer_lot(chap_dir, lot, distrib, narr, cat, stats)
    finally:
        nc.appel_vision = orig


# ---------------------------------------------------------------- fusion dans la distribution et le chapitre
def fusionner_distribution(distrib, nouveaux, cat):
    """Ajoute les nouveaux personnages (voix + couleur d'office, jamais fusionnes en silence avec un existant)."""
    ids_cat = {v["id"] for v in cat}
    prises = {p.get("voix_el") for p in distrib["persos"]} | {distrib["narrateur"].get("voix_el")}
    couleurs = {p.get("couleur") for p in distrib["persos"]}
    noms = {p["nom"].lower() for p in distrib["persos"]}
    ajoutes = []
    for n in nouveaux or []:
        nom = (n.get("nom") or "").strip()
        if not nom or nom.lower() in noms or nom.lower() in ("narrateur", "inconnu"):
            continue
        v = n.get("voix_el") if n.get("voix_el") in ids_cat else None
        if v is None or v in prises:                         # voix absente / deja prise -> une libre du bon genre
            g = {"homme": "male", "femme": "female"}.get((n.get("genre") or "").lower())
            libre = [x["id"] for x in cat if x["id"] not in prises and (g is None or x["genre"] == g)]
            v = libre[0] if libre else v
        couleur = next((c for c in PALETTE if c not in couleurs), PALETTE[len(distrib["persos"]) % len(PALETTE)])
        p = {"nom": nom, "alias": [], "genre": n.get("genre") or "?", "age": n.get("age") or "", "fiche": n.get("fiche") or "",
             "voix_el": v, "expressivite": 1, "vitesse": 1.1, "couleur": couleur}
        distrib["persos"].append(p)
        prises.add(v); couleurs.add(couleur); noms.add(nom.lower())
        ajoutes.append(nom)
    return ajoutes


def nom_connu(distrib, qui):
    """« p1 » ou un alias -> le nom de la distribution ; sinon tel quel."""
    q = (qui or "").strip()
    for p in distrib["persos"]:
        if q.lower() == p["nom"].lower() or q.lower() in [a.lower() for a in p.get("alias", [])]:
            return p["nom"]
    return q or "inconnu"


def cmd_preparer(a):
    chap_dir, serie_dir, dd = chemins(a.chap)
    ftr = os.path.join(chap_dir, "traduction", "fr", "traduction.json")
    tr = lire_json(ftr)
    if not tr:
        print("ARRET : pas de traduction francaise pour %s -- traduis d'abord ce chapitre en francais" % a.chap)
        return 3
    os.makedirs(dd, exist_ok=True)
    nc.PROGRESS = os.path.join(dd, "progress.json")
    stats = {}
    nc.STATS = stats
    voulues = set(nc_plage(a.pages, [p["page"] for p in tr["pages"]]))
    pages = []
    for p in tr["pages"]:
        if p["page"] in voulues:
            p["_bulles"] = sorted([b for b in p["bulles"] if b["type"] in ("dialogue", "narration") and not b.get("ecarte")
                                   and (b.get("trad") or "").strip()], key=lambda b: b["id"])
            if p["_bulles"]:
                pages.append(p)
    if not pages:
        print("ARRET : aucune bulle a lire dans ces pages")
        return 3
    distrib = distribution(serie_dir)
    narr_d = os.path.join(chap_dir, "narration")
    tags = sorted(os.listdir(narr_d)) if os.path.isdir(narr_d) else []
    narr = lire_json(os.path.join(narr_d, tags[0], "narration.json")) if tags else None
    cat = catalogue_el()
    relais = reglages.relais_moderation()
    log("dialogues %s preparer %s : %d pages, %d bulles, %d personnages connus, relais %s" % (
        VERSION, a.chap, len(pages), sum(len(p["_bulles"]) for p in pages), len(distrib["persos"]), "oui" if relais else "non"))
    t0 = time.time()
    reponses, a_traiter = preparer_pages(chap_dir, a.chap, pages, distrib, narr, cat, stats, relais)
    ajoutes = []
    for r in reponses:
        ajoutes += fusionner_distribution(distrib, r.get("nouveaux"), cat)
    rep = {}
    for r in reponses:
        for x in r.get("repliques") or []:
            rep[(int(x.get("page", 0)), int(x.get("id", -1)))] = x
    # le chapitre : les pages hors portee sont gardees ; une replique CORRIGEE par Quang garde ses corrections
    fch = os.path.join(dd, "dialogues.json")
    ancien = lire_json(fch) or {}
    par_cle = {x["cle"]: x for x in ancien.get("repliques") or []}
    for p in pages:
        img = os.path.join(chap_dir, "traduction", "fr", p["file"])
        for b in p["_bulles"]:
            cle = "%d-%d" % (p["page"], b["id"])
            x = rep.get((p["page"], b["id"]))
            vieux = par_cle.get(cle) or {}
            corr = vieux.get("corrige") or {}
            texte = (b.get("trad") or "").strip()
            neuf = {"cle": cle, "page": p["page"], "id": b["id"], "file": p["file"], "type": b["type"],
                    "box": b["box"], "contour": contour_bulle(img, b["box"]),
                    "texte_origine": texte, "texte": texte,
                    "qui": nom_connu(distrib, x.get("qui")) if x else "inconnu",
                    "ton": (x or {}).get("ton") or "", "lire": bool((x or {}).get("lire", True)) and bool(re.search(r"\w", texte)),
                    "indice": (x or {}).get("indice") or "", "a_traiter": p["page"] in a_traiter,
                    "corrige": corr, "voix": vieux.get("voix")}
            if b["type"] == "narration" and neuf["qui"] == "narrateur":
                neuf["lire"] = neuf["lire"] and bool(distrib["narrateur"].get("lire"))
            neuf.update({k: v for k, v in corr.items() if k in ("texte", "qui", "ton", "lire")})   # les corrections gagnent
            par_cle[cle] = neuf
    ambiances = [r.get("ambiance") for r in reponses if r.get("ambiance")]
    doc = {"version": VERSION, "chapitre": a.chap, "maj": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "ambiance": " / ".join(ambiances)[:400] if ambiances else ancien.get("ambiance", ""),
           "repliques": sorted(par_cle.values(), key=lambda x: (x["page"], x["id"]))}
    ecrire_json(fch, doc)
    ecrire_json(os.path.join(serie_dir, "dialogues_distribution.json"), distrib)
    cout = round(stats.get("cout_preparation", 0.0), 5)
    depenses.noter("dialogues", a.chap, "preparation", "gemini", cout, pages=[p["page"] for p in pages],
                   relais=stats.get("relais"))
    lues = sum(1 for x in doc["repliques"] if x["lire"] and x["page"] in voulues)
    nc.progres("fini", len(pages), len(pages), fini=True, repliques=lues, a_traiter=a_traiter, nouveaux=ajoutes,
               cout=cout, s=round(time.time() - t0, 1))
    log("OK %d repliques a lire, nouveaux : %s, a traiter : %s, %.4f $, %.0f s" % (lues, ajoutes, a_traiter, cout, time.time() - t0))
    return 0



# ================================================================ D2 : les VOIX (ElevenLabs v3, AUCUN moteur de secours)
MODELE_EL = "eleven_v3"
STABILITE = {0: 1.0, 1: 0.5, 2: 0.0}      # v3 : 3 reglages (Robust / Natural / Creative) = retenue / naturelle / expressive
CODE_QUOTA = 4


class QuotaEpuise(Exception):
    """Credits ElevenLabs epuises : on S'ARRETE (Quang 26/09 : « si le quota est bloque, il est bloque »)."""


def el_post(path, body):
    """POST ElevenLabs via le gateway -> octets MP3. Quota epuise -> QuotaEpuise (aucun nouvel essai, aucun autre moteur)."""
    import urllib.request, urllib.error
    req = urllib.request.Request(nc.GATEWAY + path, data=json.dumps(body).encode(), headers={
        "Content-Type": "application/json", "Authorization": "Bearer " + nc.SECRET, "User-Agent": "manga-studio/dialogues-" + VERSION})
    for essai in range(3):
        nc._frein()
        try:
            return urllib.request.urlopen(req, timeout=120).read()
        except urllib.error.HTTPError as e:
            brut = e.read()[:400].decode("utf-8", "replace")
            bl = brut.lower()
            if "quota_exceeded" in bl or ("quota" in bl and e.code in (401, 402, 403, 429)):
                raise QuotaEpuise(brut[:200])
            motif = mod.refus_http(e.code, brut)
            if motif:
                raise mod.Refus("elevenlabs", motif)
            if e.code not in (429, 500, 502, 503, 504, 520, 521, 522, 523, 524) or essai == 2:
                raise RuntimeError("ElevenLabs HTTP %d %s" % (e.code, brut[:200]))
            time.sleep(8 * (essai + 1))


def el_solde():
    """{utilises, limite, restants, renouvellement} ou None (gateway muet : on ne bloque pas sur une lecture ratee)."""
    import urllib.request
    try:
        r = urllib.request.Request(nc.GATEWAY + "/api/elevenlabs/v1/user/subscription",
                                   headers={"Authorization": "Bearer " + nc.SECRET, "User-Agent": "manga-studio/dialogues-" + VERSION})
        s = json.load(urllib.request.urlopen(r, timeout=30))
        return {"utilises": s.get("character_count", 0), "limite": s.get("character_limit", 0),
                "restants": max(0, s.get("character_limit", 0) - s.get("character_count", 0)),
                "renouvellement": s.get("next_character_count_reset_unix")}
    except Exception as e:
        log("  solde ElevenLabs illisible : %s" % str(e)[:120])
        return None


def texte_lu(t):
    """Les CAPITALES de manga (cri) se lisent mieux en casse normale : le ton porte deja le cri (essai 26/09)."""
    lettres = [c for c in t if c.isalpha()]
    if lettres and sum(c.isupper() for c in lettres) / len(lettres) > 0.8:
        t = t.lower()
        t = re.sub(r"(^|[.!?…]\s+)([a-zà-ÿ])", lambda m: m.group(1) + m.group(2).upper(), t)
    return t.strip()


def balises(distrib, tons, stats):
    """Ton francais -> balises anglaises v3 (« [sarcastic] [mocking] »), gardees dans la distribution : memes tons = 0 appel."""
    manque = sorted({t for t in tons if t and t not in distrib["balises"]})
    if manque:
        r = nc.post("/api/deepseek", {"model": "deepseek-v4-flash", "max_tokens": 3000, "temperature": 0,
                    "thinking": {"type": "disabled"}, "response_format": {"type": "json_object"},
                    "messages": [{"role": "system", "content": "Convert each French acting direction into ElevenLabs v3 audio tags: "
                                  "1 or 2 short English emotion/delivery tags in square brackets, e.g. \"[sarcastic] [mocking]\", "
                                  "\"[terrified]\", \"[cold] [calm]\". Answer JSON {\"<french>\": \"<tags>\"}."},
                                 {"role": "user", "content": json.dumps(manque, ensure_ascii=False)}]})
        rep = nc.parse_json(r["choices"][0]["message"]["content"])
        for t in manque:
            b = str(rep.get(t) or "").strip()
            distrib["balises"][t] = b if re.fullmatch(r"(\[[A-Za-z ,'-]{1,30}\]\s*){1,3}", b) else ""
        stats["cout_balises"] = stats.get("cout_balises", 0.0) + nc.cout("deepseek-v4-flash", r.get("usage") or {})
    return distrib["balises"]


def reglage_voix(distrib, qui):
    if qui == "narrateur":
        return distrib["narrateur"]
    return next((p for p in distrib["persos"] if p["nom"] == qui), None)


def a_dire(x, distrib, bal):
    """(texte envoye, parametres, empreinte) d'une replique -- ou None si elle ne se lit pas / n'a pas de voix."""
    if not x.get("lire") or (x.get("a_traiter") and not (x.get("corrige") or {}).get("qui")):
        return None                                  # page refusee : lisible des que Quang a choisi QUI parle (sa correction)
    p = reglage_voix(distrib, x.get("qui"))
    if not p or not p.get("voix_el"):
        return None
    texte = texte_lu(x.get("texte") or "")
    if not re.search(r"\w", texte):
        return None
    tag = bal.get(x.get("ton") or "", "") if distrib.get("tons", True) else ""
    envoye = (tag + " " + texte).strip()
    reg = {"voix": p["voix_el"], "modele": MODELE_EL, "stabilite": STABILITE.get(int(p.get("expressivite", 1)), 0.5),
           "vitesse": round(min(1.2, max(0.7, float(p.get("vitesse", 1.1)))), 2)}
    import hashlib
    emp = hashlib.sha1(json.dumps([envoye, reg], sort_keys=True).encode()).hexdigest()[:16]
    return envoye, texte, reg, emp


def fuite_balise(mp3, texte, stats):
    """La voix a-t-elle PRONONCE une balise ([mocking]...) ? Transcription nettement plus longue que le texte."""
    import karaoke_mots as km
    try:
        t = (km.whisper(mp3, "") or {}).get("text", "")
    except Exception:
        return False, ""
    stats["whisper"] = stats.get("whisper", 0) + 1
    n = lambda s: re.sub(r"[^a-zà-ÿ]", "", s.lower())
    return len(n(t)) > len(n(texte)) * 1.6 + 6, t.strip()


def cmd_voix(a):
    chap_dir, serie_dir, dd = chemins(a.chap)
    fch = os.path.join(dd, "dialogues.json")
    doc = lire_json(fch)
    if not doc:
        print("ARRET : chapitre pas encore prepare (dialogues.py preparer %s)" % a.chap)
        return 3
    distrib = distribution(serie_dir)
    nc.PROGRESS = os.path.join(dd, "progress.json")
    stats = {}
    nc.STATS = stats
    voulues = set(nc_plage(a.pages, sorted({x["page"] for x in doc["repliques"]})))
    reps = [x for x in doc["repliques"] if x["page"] in voulues]
    bal = balises(distrib, [x.get("ton") for x in reps if x.get("lire")], stats) if distrib.get("tons", True) else {}
    ecrire_json(os.path.join(serie_dir, "dialogues_distribution.json"), distrib)
    os.makedirs(os.path.join(dd, "voix"), exist_ok=True)
    plan = []
    for x in reps:
        d_ = a_dire(x, distrib, bal)
        if d_ is None:
            continue
        envoye, texte, reg, emp = d_
        v = x.get("voix") or {}
        if v.get("empreinte") == emp and os.path.isfile(os.path.join(dd, "voix", v.get("fichier", "?"))):
            continue                                                     # deja faite avec ces reglages : jamais repayee
        plan.append((x, envoye, texte, reg, emp))
    besoin = sum(len(p[1]) for p in plan)
    solde = el_solde()
    log("dialogues %s voix %s : %d a faire (%d deja faites), ~%d credits, solde %s" % (
        VERSION, a.chap, len(plan), sum(1 for x in reps if a_dire(x, distrib, bal)) - len(plan), besoin,
        solde["restants"] if solde else "?"))
    nc.progres("voix", 0, len(plan), credits_estimes=besoin, solde=solde)
    if solde is not None and solde["restants"] <= 0 and plan:
        nc.progres("quota", 0, len(plan), fini=True, arret="quota ElevenLabs epuise", solde=solde)
        print("ARRET : quota ElevenLabs epuise (0 credit restant) -- aucune voix faite, aucun autre moteur")
        return CODE_QUOTA
    t0, faits, credits, arret = time.time(), 0, 0, None
    for k, (x, envoye, texte, reg, emp) in enumerate(plan):
        nc.progres("voix", k, len(plan), credits=credits, cle=x["cle"])
        f = os.path.join(dd, "voix", emp + ".mp3")
        body = {"text": envoye, "model_id": reg["modele"], "language_code": "fr",
                "voice_settings": {"stability": reg["stabilite"], "similarity_boost": 0.75, "speed": reg["vitesse"]}}
        try:
            for essai in range(2):
                open(f, "wb").write(el_post("/api/elevenlabs/v1/text-to-speech/%s?output_format=mp3_44100_128" % reg["voix"], body))
                credits += len(envoye)
                fu, t_ = fuite_balise(f, texte, stats) if envoye != texte else (False, "")
                if not fu:
                    break
                log("  %s : balise prononcee (%s) -> refaite" % (x["cle"], t_[:60]))
        except QuotaEpuise as e:
            arret = "quota ElevenLabs epuise"
            log("  ARRET a %s : %s" % (x["cle"], e))
            break
        except mod.Refus as e:
            mod.ajouter_alerte(a.chap, "dialogues", [x["page"]], "elevenlabs", e.motif, detail="voix de la replique " + x["cle"])
            x["a_traiter"] = True
            log("  %s refusee par ElevenLabs : %s" % (x["cle"], e.motif[:100]))
            continue
        x["voix"] = {"empreinte": emp, "fichier": emp + ".mp3", "duree": nc.duree_mp3(f), "fuite": bool(fu),
                     "t": time.strftime("%Y-%m-%dT%H:%M:%S")}
        faits += 1
        doc["maj"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        ecrire_json(fch, doc)                                             # chaque voix faite est gardee tout de suite
    depenses.noter_credits("dialogues", a.chap, "voix", "elevenlabs", credits, repliques=faits)
    depenses.noter("dialogues", a.chap, "balises", "deepseek", round(stats.get("cout_balises", 0.0), 5))
    solde2 = el_solde()
    reste = len(plan) - faits
    nc.progres("quota" if arret else "fini", faits, len(plan), fini=True, arret=arret, credits=credits, solde=solde2,
               reste=reste, s=round(time.time() - t0, 1))
    log("%s %d voix faites, %d restantes, %d credits, %.0f s" % ("ARRET" if arret else "OK", faits, reste, credits, time.time() - t0))
    return CODE_QUOTA if arret else 0


def cmd_ecouter(a):
    """▶ de l'ecran de preparation : UNE replique (--cle), eventuellement dite par un autre personnage (--qui) ou avec un autre
    ton (--ton). Sortie JSON sur stdout {fichier (relatif au chapitre), credits, deja}. Si la voix demandee est EXACTEMENT celle
    de la replique (memes texte, ton, reglages), elle devient sa voix definitive : jamais payee deux fois."""
    chap_dir, serie_dir, dd = chemins(a.chap)
    doc = lire_json(os.path.join(dd, "dialogues.json"))
    if not doc:
        print(json.dumps({"error": "chapitre pas encore prepare"})); return 3
    x0 = next((x for x in doc["repliques"] if x["cle"] == a.cle), None)
    if not x0:
        print(json.dumps({"error": "replique inconnue"})); return 3
    distrib = distribution(serie_dir)
    x = dict(x0, lire=True, a_traiter=False)
    if a.qui:
        x["qui"] = a.qui
    if a.ton is not None:
        x["ton"] = a.ton
    stats = {}
    bal = balises(distrib, [x.get("ton")], stats) if distrib.get("tons", True) and x.get("ton") else {}
    if stats.get("cout_balises"):
        ecrire_json(os.path.join(serie_dir, "dialogues_distribution.json"), distrib)
        depenses.noter("dialogues", a.chap, "balises", "deepseek", round(stats["cout_balises"], 5))
    d_ = a_dire(x, distrib, bal)
    if d_ is None:
        print(json.dumps({"error": "rien a dire (pas de voix pour ce personnage, ou texte vide)"})); return 3
    envoye, texte, reg, emp = d_
    for rel in ("voix/" + emp + ".mp3", "apercus/" + emp + ".mp3"):
        if os.path.isfile(os.path.join(dd, rel.replace("/", os.sep))):
            print(json.dumps({"fichier": "dialogues/" + rel, "credits": 0, "deja": True})); return 0
    propre = (x0.get("qui") == x["qui"] and (x0.get("ton") or "") == (x.get("ton") or "") and x0.get("lire") and not x0.get("a_traiter"))
    rel = ("voix/" if propre else "apercus/") + emp + ".mp3"
    f = os.path.join(dd, rel.replace("/", os.sep))
    os.makedirs(os.path.dirname(f), exist_ok=True)
    body = {"text": envoye, "model_id": reg["modele"], "language_code": "fr",
            "voice_settings": {"stability": reg["stabilite"], "similarity_boost": 0.75, "speed": reg["vitesse"]}}
    try:
        open(f, "wb").write(el_post("/api/elevenlabs/v1/text-to-speech/%s?output_format=mp3_44100_128" % reg["voix"], body))
    except QuotaEpuise:
        print(json.dumps({"error": "quota ElevenLabs epuise", "quota": True})); return CODE_QUOTA
    except mod.Refus as e:
        print(json.dumps({"error": "refusee par ElevenLabs : " + e.motif[:160]})); return 3
    depenses.noter_credits("dialogues", a.chap, "ecoute", "elevenlabs", len(envoye), repliques=1)
    if propre:                                                  # c'est SA voix : on la garde comme definitive
        doc = lire_json(os.path.join(dd, "dialogues.json"))
        for y in doc["repliques"]:
            if y["cle"] == a.cle:
                y["voix"] = {"empreinte": emp, "fichier": emp + ".mp3", "duree": nc.duree_mp3(f), "fuite": False,
                             "t": time.strftime("%Y-%m-%dT%H:%M:%S")}
        ecrire_json(os.path.join(dd, "dialogues.json"), doc)
    print(json.dumps({"fichier": "dialogues/" + rel, "credits": len(envoye), "deja": False, "definitive": bool(propre)}))
    return 0


def cmd_plan(a):
    """Ce qui reste a faire, SANS aucun appel paye : {repliques: {cle: etat}, a_faire, credits, deja}. etat = « faite » (voix a
    jour), « a_faire » (jamais faite), « a_refaire » (texte, ton, voix ou reglages changes), « sans_voix » (personnage sans voix
    choisie), « non_lue ». Les tons pas encore traduits en balises sont comptes a ~20 caracteres (estimation)."""
    chap_dir, serie_dir, dd = chemins(a.chap)
    doc = lire_json(os.path.join(dd, "dialogues.json"))
    if not doc:
        print(json.dumps({"error": "pas prepare"})); return 3
    distrib = distribution(serie_dir)
    bal = dict(distrib.get("balises") or {})
    tons = distrib.get("tons", True)
    etats, credits, a_faire, deja = {}, 0, 0, 0
    for x in doc["repliques"]:
        if not x.get("lire") or (x.get("a_traiter") and not (x.get("corrige") or {}).get("qui")):
            etats[x["cle"]] = "a_traiter" if x.get("a_traiter") and x.get("lire") else "non_lue"; continue
        estime = dict(bal)
        if tons and x.get("ton") and x["ton"] not in estime:
            estime[x["ton"]] = "[xxxxxxxx] [xxxxxxx]"
        d_ = a_dire(x, distrib, estime)
        if d_ is None:
            p = reglage_voix(distrib, x.get("qui"))
            etats[x["cle"]] = "sans_voix" if (p is None or not p.get("voix_el")) else "non_lue"; continue
        envoye, texte, reg, emp = d_
        v = x.get("voix") or {}
        if v.get("empreinte") == emp and os.path.isfile(os.path.join(dd, "voix", v.get("fichier", "?"))):
            etats[x["cle"]] = "faite"; deja += 1
        else:
            etats[x["cle"]] = "a_refaire" if v else "a_faire"; a_faire += 1; credits += len(envoye)
    print(json.dumps({"repliques": etats, "a_faire": a_faire, "credits": credits, "deja": deja}, ensure_ascii=False))
    return 0


def chapitres_de_serie(serie_dir, de, a):
    """[(numero, dossier)] des chapitres de la serie entre de et a (numeros du manifeste), dans l'ordre."""
    out = []
    for ch in os.listdir(serie_dir):
        m = lire_json(os.path.join(serie_dir, ch, "manifest.json"))
        if not m:
            continue
        try:
            n = float(str(m.get("chapter") or ch[3:]).replace(",", "."))
        except ValueError:
            continue
        if de <= n <= a:
            out.append((n, ch))
    return sorted(out)


def cmd_lot(a):
    """Portee « plusieurs chapitres » (Quang 26/09 23h43). Chapitres dans l'ordre ; seuls les chapitres TRADUITS en francais ;
    action preparer | voix | tout (preparer puis voix, « sans relecture »). Quota ElevenLabs epuise = ARRET net de tout le lot
    (ce qui est fait est garde) ; relancer = reprendre (un chapitre deja prepare n'est pas repaye, une voix faite non plus).
    Etat : <serie>/dialogues_lot.json."""
    serie_dir = os.path.join(SOURCES, a.serie)
    fl = os.path.join(serie_dir, "dialogues_lot.json")
    chs = chapitres_de_serie(serie_dir, a.de, a.a)
    etat = {"version": VERSION, "serie": a.serie, "de": a.de, "a": a.a, "action": a.action, "pid": os.getpid(),
            "debut": time.strftime("%Y-%m-%dT%H:%M:%S"), "etat": "en cours", "chapitres": [], "t": time.time()}
    for n, ch in chs:
        tr = os.path.isfile(os.path.join(serie_dir, ch, "traduction", "fr", "traduction.json"))
        etat["chapitres"].append({"num": n, "ch": ch, "etat": "attente" if tr else "non traduit"})
    ecrire_json(fl, etat)
    code = 0
    for c in etat["chapitres"]:
        if c["etat"] == "non traduit":
            continue
        d = a.serie + "/" + c["ch"]
        c["etat"] = "en cours"; etat["en_cours"] = d; etat["t"] = time.time(); ecrire_json(fl, etat)
        prepare = os.path.isfile(os.path.join(serie_dir, c["ch"], "dialogues", "dialogues.json"))
        try:
            if a.action in ("preparer", "tout") and not prepare:
                r = cmd_preparer(argparse.Namespace(chap=d, pages=""))
                if r:
                    c["etat"] = "echec preparation"; continue
            if a.action in ("voix", "tout"):
                r = cmd_voix(argparse.Namespace(chap=d, pages=""))
                if r == CODE_QUOTA:
                    c["etat"] = "quota"; etat["arret"] = "quota ElevenLabs epuise au ch. %s" % c["ch"][3:]; code = CODE_QUOTA
                    break
                if r:
                    c["etat"] = "echec voix"; continue
            c["etat"] = "fait"
        finally:
            etat["t"] = time.time(); ecrire_json(fl, etat)
    etat.update(etat="arrete" if code else "fini", fin=time.strftime("%Y-%m-%dT%H:%M:%S"), en_cours=None, t=time.time())
    ecrire_json(fl, etat)
    log("LOT %s : %s" % (etat["etat"], [(c["ch"], c["etat"]) for c in etat["chapitres"]]))
    return code

def nc_plage(s, toutes):
    if not s:
        return toutes
    a_, _, b_ = s.partition("-")
    return list(range(int(a_), int(b_ or a_) + 1))


def main():
    nc._sorties_utf8()
    p = argparse.ArgumentParser()
    sp = p.add_subparsers(dest="cmd", required=True)
    pr = sp.add_parser("preparer"); pr.add_argument("chap"); pr.add_argument("--pages", default="")
    vo = sp.add_parser("voix"); vo.add_argument("chap"); vo.add_argument("--pages", default="")
    ec = sp.add_parser("ecouter"); ec.add_argument("chap"); ec.add_argument("--cle", required=True)
    ec.add_argument("--qui", default=""); ec.add_argument("--ton", default=None)
    pl = sp.add_parser("plan"); pl.add_argument("chap")
    lo = sp.add_parser("lot"); lo.add_argument("serie"); lo.add_argument("--de", type=float, required=True)
    lo.add_argument("--a", type=float, required=True); lo.add_argument("--action", choices=("preparer", "voix", "tout"), default="preparer")
    a = p.parse_args()
    nc.SECRET = nc._secret()
    if a.cmd == "preparer":
        return cmd_preparer(a)
    if a.cmd == "voix":
        return cmd_voix(a)
    if a.cmd == "ecouter":
        return cmd_ecouter(a)
    if a.cmd == "plan":
        return cmd_plan(a)
    if a.cmd == "lot":
        return cmd_lot(a)


if __name__ == "__main__":
    sys.exit(main() or 0)
