# -*- coding: utf-8 -*-
"""MODE « DIALOGUES » de Manga Studio -- une voix par personnage (ROADMAP § 4-septdecies, maquette_dialogues_v2.html validee
par Quang le 26/09/2026 23h58). SEPARE de la narration : il LIT la traduction francaise, n'ecrit JAMAIS dans narration/ ni
traduction/.

  python dialogues.py preparer <serie/ch_N> [--pages a-b]   qui parle, quel ton, quoi lire (Gemini, pages vues) -- AUCUNE voix
  python dialogues.py voix     <serie/ch_N>                 (etape D2)

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

VERSION = "1.0.0"
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
    a = p.parse_args()
    nc.SECRET = nc._secret()
    if a.cmd == "preparer":
        return cmd_preparer(a)


if __name__ == "__main__":
    sys.exit(main() or 0)
