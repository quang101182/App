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
import argparse, base64, json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import narrate_chapter as nc
import moderation as mod
import depenses
import reglages

VERSION = "1.25.0"  # 1.25.0 (27/09) : cout des voix MESURE (solde avant / apres), tarif recale a chaque mesure ;  # 1.24.0 (27/09) : musique de fond de la serie dans la video des Dialogues (optionnelle) ;  # 1.23.0 (27/09) : texte et personnage inchanges -> ANCIEN ton garde (la voix n'est pas repayee) ;  # 1.22.1 (27/09) : bulle entouree effacee LETTRES SEULES (jamais la case entiere) ;  # 1.22.0 (27/09) : bulle ENTOUREE sur une page traduite -> traduite et REECRITE en francais sur la page ;  # 1.21.1 (27/09) : bulle lue sur l'image PAS en francais -> TRADUITE (ajout reste en anglais) ;  # 1.21.0 (27/09) : commande « tout » (preparer -> ARRET si doute -> voix -> video) ;  # 1.20.0 (27/09) : refaire une plage RETIRE les repliques qui ne sont plus produites (bulle exclue / disparue) ;  # 1.19.0 (R30, 27/09) : 🔍 bulles VERIFIEES par Quang avant la preparation (exclues, ajoutees, ORDRE) + commande « detecter » (gratuite) ;  # 1.18.0 (27/09, Quang : « un homme a une couleur rose, ca parait bizarre ») : couleur d'office tiree dans la FAMILLE du genre (hommes : froides / franches ; femmes : chaudes / pastel) ;  # 1.17.0 (R24, 27/09) : voix PREFEREES en tete de la distribution automatique ;  # 1.16.0 (R18, 27/09) : nouveau personnage = vitesses PAR DEFAUT de son genre (reglages de l'instance) ;  # 1.15.0 (R19, 27/09) : distribution automatique en voix 100 % FRANCAISES ;  # 1.14.0 (R17, 27/09) : vitesse d'ECOUTE par personnage appliquee a la video, gratuite ;  # 1.13.0 (R14, 27/09) : les textes ecartes POUR L'IMAGE (zone trop grande...) sont lus ;  # 1.12.0 (R13, 27/09) : une page de traduction jamais LUE par le modele est retraduite (--traduire) ;  # 1.11.0 (D12, Quang 02h28 : « que la solution devienne de plus en plus fiable dans la globalite ») : apres
#          une preparation qui cree de NOUVEAUX personnages, controle des DOUBLONS probables (DeepSeek, texte seul) ->
#          distrib["doublons"] ; jamais de fusion sans Quang (bouton « Fusionner » de l'app) ; « pas_doublons » = ne plus proposer
#   # 1.10.0 : 1.10.0 (R3-bis, Quang 03h08 : « plusieurs videos sur un meme chapitre, p.5-10 et p.35-42 ») : video --pages a-b
#          = UNE video par portee (dialogues_p5-10.mp4), chacune gardee ; doc.videos {portee: ...} ; plan rend « videos »
#   # 1.9.2 : 1.9.2 (R1-bis) : la VIDEO montre aussi les pages sans dialogue de la portee (2,2 s, tampon, silence)
#   # 1.9.1 : 1.9.1 (R1-bis, Quang 02h35 : « des pages ont ete sautees ») : pages_vues = TOUTES les pages de la portee
#          preparee (meme sans bulle), pour que le lecteur et la video les montrent
#   # 1.9.0 : 1.9.0 (27/09, R1) : etat_voix() = UNE definition de « voix a jour » (plan ET video) ; la video REFUSE
#          tant qu'une replique lue n'a pas sa voix a jour (avant : elle sautait ces repliques en silence)
#   # 1.8.1 : 1.8.1 (27/09, Quang 02h26 : « plus de personnages que prevu, un homme et une femme p.44-65 ») : les
#          personnages decouverts dans un lot rejoignent la distribution AVANT le lot suivant (avant : fusion a la fin -> un
#          meme homme nomme 4 fois, « cheveux blancs / argentes / clairs / gris », un nom par lot de 4 pages)
#   # 1.8.0 : 1.8.0 (27/09, Quang) : preparer --traduire = traduit d'abord les pages DEMANDEES qui ne le sont pas
#          (traduire_chapitre.py --pages --via dialogues : ajoutees a la traduction, tracees), jamais sans ce drapeau
#   # 1.7.0 : 1.7.0 (D8, 27/09) : credits = tarif MESURE du v3 (0,28/caractere), plus 1/caractere
#   # 1.6.1 : 1.6.1 : contour degenere (< 3 points / < 20 % de la boite) -> repli ovale
#   # 1.6.0 (Quang 27/09 00h47, Solo Leveling) : chapitre en FRANCAIS D'ORIGINE -- bulles detectees
#          sur les pages d'origine (meme detection que la traduction), texte LU par Gemini ; img_rel = page a afficher
#   # 1.5.2 : video/dialogues.json -> nom de telechargement juste (FR, sous-titres)
#   # 1.5.1 : plan dit si la video est a jour / perimee / absente
#   # 1.5.0 (27/09) : video (MP4 1080x1920, meme rendu que le lecteur, dialogues/video/)
#   # 1.4.1 : page refusee lisible une fois QUI choisi par Quang ; plan dit « a_traiter »
#   # 1.4.0 (27/09) : lot (plusieurs chapitres, arret net au quota, reprise)
#   # 1.3.0 (27/09) : plan (etat de chaque replique + credits a prevoir, sans appel paye)
#   # 1.2.0 (27/09) : ecouter (▶ de la preparation ; la voix exacte d'une replique devient definitive)
#   # 1.1.0 (27/09) : D2 voix ElevenLabs v3 (empreintes, balises, arret net au quota)
SOURCES = os.environ.get("MANGA_SOURCES_DIR") or os.path.join(HERE, "..", "sources")
LOT_PAGES = 4                       # pages par appel (essai 26/09 : 3 pages = 12 s, 5 pages = 26 s)
PALETTE = ["#ff5fa2", "#ffb347", "#6fb8ff", "#b58cff", "#5fe3a1", "#ff7a5c", "#f5e663", "#4fd6e8", "#e88aff", "#c7a17a"]
PALETTE_H = ["#6fb8ff", "#4fd6e8", "#5fe3a1", "#ffb347", "#f5e663", "#c7a17a", "#7f8cff"]   # 1.18.0 : hommes (meme liste que l'app)
PALETTE_F = ["#ff5fa2", "#e88aff", "#b58cff", "#ff7a5c", "#ff9ec7", "#f7b2ff"]              # 1.18.0 : femmes
NARRATEUR_VOIX = "JBFqnCBsd6RMkjVDRZzb"     # George -- homme, conteur pose et constant (Quang 26/09 23h55 : un homme, constant)
DISTRIB_VERSION = 1
# Tarif REEL d'eleven_v3, mesure au solde du compte le 27/09 (D8) : 789 car. -> 218 cr., 33 -> 9, 23 -> 6.
# Le gateway ne renvoie pas les en-tetes de cout : seul le solde fait foi, a re-mesurer si ElevenLabs change ses prix.
TARIF_V3 = 0.28


def tarif_el():
    """1.25.0 : credits / caractere MESURE (sources/_elevenlabs_tarif.json), sinon TARIF_V3."""
    t = (lire_json(os.path.join(SOURCES, "_elevenlabs_tarif.json")) or {}).get("par_car")
    return float(t) if t and 0.01 < float(t) < 5 else TARIF_V3


def recaler_tarif(credits, caracteres):
    """1.25.0 : une mesure reelle (credits consommes pour N caracteres envoyes) -> moyenne glissante du tarif."""
    if credits <= 0 or caracteres < 20:
        return
    f = os.path.join(SOURCES, "_elevenlabs_tarif.json")
    d = lire_json(f) or {}
    mesure = credits / float(caracteres)
    anc, n = d.get("par_car"), int(d.get("mesures") or 0)
    d["par_car"] = round(mesure if not anc else (anc * min(n, 9) + mesure) / (min(n, 9) + 1), 4)
    d["mesures"] = n + 1
    d["derniere"] = {"credits": credits, "caracteres": caracteres, "par_car": round(mesure, 4), "t": time.strftime("%Y-%m-%dT%H:%M:%S")}
    ecrire_json(f, d)


def cout_el(envoye):
    return max(1, round(len(envoye) * tarif_el()))


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


def deja_francais(chap_dir):
    """Chapitre capture directement en francais (langue.json de l'app : langue fr) et SANS traduction francaise."""
    lg = lire_json(os.path.join(chap_dir, "langue.json")) or {}
    return lg.get("langue") == "fr" and not os.path.isfile(os.path.join(chap_dir, "traduction", "fr", "traduction.json"))


def ecarte_pour_image(b):
    """1.13.0 (R14) : texte ecarte par la traduction pour PROTEGER LE DESSIN (sa pose sur l'image), pas parce qu'il est faux
    -> les Dialogues le lisent. « moins de 2 lettres » (« ...! ») reste exclu."""
    return bool(b.get("ecarte")) and not str(b.get("ecarte")).startswith("moins de 2")


def source_bulles(chap_dir, plage=""):
    """{pages: [{page, file, img_rel, bulles}]} : la traduction francaise si elle existe ; sinon, pour un chapitre deja en
    francais, les bulles DETECTEES sur les pages d'origine (traduire_chapitre.zones_texte : meme detection, memes seuils),
    texte vide -- Gemini le lit dans l'appel de preparation. None si ni l'un ni l'autre."""
    tr = lire_json(os.path.join(chap_dir, "traduction", "fr", "traduction.json"))
    if tr:
        for p in tr["pages"]:
            p["img_rel"] = "traduction/fr/" + p["file"]
        return tr
    if not deja_francais(chap_dir):
        return None
    import ingest_page as ip
    import traduire_chapitre as tc
    man = lire_json(os.path.join(chap_dir, "manifest.json")) or {}
    fichiers = [(q.get("file") or q.get("path") or q) if isinstance(q, (dict, str)) else None for q in man.get("pages") or []]
    fichiers = [os.path.basename(f) for f in fichiers if f] or sorted(f for f in os.listdir(chap_dir) if re.match(r"page_\d+\.(png|jpe?g|webp)$", f))
    voulues = set(nc_plage(plage, list(range(1, len(fichiers) + 1))))
    pages = []
    for n, f in enumerate(fichiers, 1):
        if n not in voulues or not os.path.isfile(os.path.join(chap_dir, f)):
            continue
        nc.progres("detection", len(pages), len(voulues))
        texts = tc.zones_texte(ip.load_page(os.path.join(chap_dir, f)), 0.25)
        pages.append({"page": n, "file": f, "img_rel": f, "bulles": [
            {"id": t["id"], "type": "dialogue", "box": {k: round(t[k], 4) for k in ("x", "y", "w", "h")}, "trad": "", "a_lire": True}
            for t in texts]})
    return {"pages": pages, "source": "vf"}


# ---------------------------------------------------------------- catalogue de voix ElevenLabs (via le gateway)
def voix_francaises():
    """1.15.0 (R19) : les voix FRANCAISES de la bibliotheque publique ElevenLabs ([] si elle ne repond pas)."""
    import urllib.request
    try:
        r = urllib.request.Request(nc.GATEWAY + "/api/elevenlabs/v1/shared-voices?page_size=100&language=fr&sort=cloned_by_count",
                                   headers={"Authorization": "Bearer " + nc.SECRET, "User-Agent": "manga-studio/dialogues-" + VERSION})
        v = json.load(urllib.request.urlopen(r, timeout=30)).get("voices") or []
    except Exception as e:
        log("  bibliotheque de voix francaises illisible (%s) : catalogue du compte" % str(e)[:120])
        return []
    out, vus = [], set()
    for x in v:
        if not x.get("free_users_allowed", True) or x.get("gender") not in ("male", "female") or x.get("voice_id") in vus:
            continue
        vus.add(x["voice_id"])
        n = x.get("name") or ""
        out.append({"id": x["voice_id"], "nom": n.split(" - ")[0].strip(), "genre": x["gender"], "age": x.get("age") or "?",
                    "desc": ((n.split(" - ", 1)[1] if " - " in n else "") or x.get("descriptive") or "")[:60], "fr": True})
    return out


def avec_preferees(cat):
    """1.17.0 (R24) : les voix PREFEREES de l'instance (reglages.voix_favorites) en tete, marquees pour le modele ; une preferee
    absente du catalogue (voix du compte) y est ajoutee depuis catalogue_el()."""
    try:
        import reglages
        fav = reglages._brut().get("voix_favorites") or []
    except Exception:
        fav = []
    if not fav:
        return cat
    tous = {v["id"]: v for v in cat}
    if any(i not in tous for i in fav):
        for v in catalogue_el():
            tous.setdefault(v["id"], v)
    tete = [dict(tous[i], desc="⭐ preferee de Quang -- " + (tous[i].get("desc") or ""), prefere=True) for i in fav if i in tous]
    return tete + [v for v in cat if v["id"] not in fav]


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
    if gris.ndim == 3:                  # ultralytics (detection VF) REMPLACE cv2.imread : le gris revient en (H, W, 1)
        gris = gris[..., 0] if gris.shape[2] == 1 else cv2.cvtColor(gris, cv2.COLOR_BGR2GRAY)
        cache[img_path] = gris
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
    grand = max(cs, key=cv2.contourArea)
    if cv2.contourArea(grand) < 0.2 * bw * bh:        # 27/09 (Solo Leveling) : contour DEGENERE (1 point) -> repli ovale
        return None
    c = cv2.approxPolyDP(grand, max(1.5, 0.004 * max(W, H)), True)
    if len(c) < 3:
        return None
    return [[round(float(p[0][0]) / W, 4), round(float(p[0][1]) / H, 4)] for p in c]


# ---------------------------------------------------------------- l'appel « qui parle / quel ton / quoi lire »
SYS = """Tu prepares le DOUBLAGE en francais d'un manga : chaque replique sera lue par la voix de son personnage.
Tu recois des pages (deja traduites en francais, dans l'ordre de lecture) et, pour chaque page, la liste NUMEROTEE des bulles
(id, type, texte, position x,y,w,h en fractions de la page). Tu recois aussi la DISTRIBUTION DU MANGA (personnages deja connus
d'autres chapitres) et des indices sur ce chapitre : l'IMAGE fait foi.

0. Si le texte d'une bulle est VIDE (bulle ajoutee a la main, ou page deja en francais), LIS-le sur l'image et rends-le dans
   "texte" : s'il est deja en FRANCAIS, mot pour mot, sans rien corriger ni ajouter ; s'il est dans une AUTRE langue (anglais,
   japonais...), TRADUIS-le en francais naturel et oral -- c'est ce que la voix dira, jamais la VO. Casse normale (pas tout en
   majuscules), ponctuation d'origine.
1. Pour CHAQUE bulle, QUI la prononce (queue de la bulle, case, qui est dessine, sens de la phrase) :
   - un personnage CONNU : son nom EXACT de la distribution (n'invente pas un 2e nom pour lui). Meme role, meme allure aux
     nuances du dessin pres (couleur des cheveux ou des yeux qui varie avec l'encrage ou la lumiere) = LE MEME personnage ;
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
 "repliques": [{"page": 5, "id": 2, "texte": "(seulement si la bulle etait vide)", "qui": "...", "ton": "...", "lire": true,
                "indice": "ce qui designe le locuteur, 10 mots max"}]}
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
        img = os.path.join(chap_dir, *p["img_rel"].split("/"))
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
            stats.setdefault("_ajoutes", []).extend(fusionner_distribution(distrib, r.get("nouveaux"), cat))   # 1.8.1 : connu du lot suivant
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
                    stats.setdefault("_ajoutes", []).extend(fusionner_distribution(distrib, r.get("nouveaux"), cat))
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
def defaut_reglage(cle, sinon):
    """1.16.0 (R18) : valeur par defaut de l'instance (reglages.py, meme MANGA_SOURCES_DIR) ; `sinon` si illisible."""
    try:
        import reglages
        return reglages.defaut(cle, sinon)
    except Exception:
        return sinon


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
        fam = {"homme": PALETTE_H, "femme": PALETTE_F}.get((n.get("genre") or "").lower(), PALETTE_H + PALETTE_F)   # 1.18.0
        couleur = next((c for c in fam if c not in couleurs), fam[len(distrib["persos"]) % len(fam)])
        gk = {"homme": "h", "femme": "f"}.get((n.get("genre") or "").lower())      # 1.16.0 (R18) : defauts du genre
        p = {"nom": nom, "alias": [], "genre": n.get("genre") or "?", "age": n.get("age") or "", "fiche": n.get("fiche") or "",
             "voix_el": v, "expressivite": 1, "vitesse": defaut_reglage("voix_%s_vitesse" % gk, 1.1) if gk else 1.1,
             "couleur": couleur}
        ec = defaut_reglage("voix_%s_ecoute" % gk, 1) if gk else 1
        if ec != 1:
            p["ecoute"] = ec
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


def plages_contigues(nums):
    out = []
    for n in sorted(nums):
        if out and n == out[-1][1] + 1:
            out[-1][1] = n
        else:
            out.append([n, n])
    return out


def traduire_manquantes(a, chap_dir, dd):
    """--traduire (1.8.0) : traduit -- et paie -- les pages DEMANDEES qui ne sont pas encore en francais, par
    traduire_chapitre.py --via dialogues (elles s'AJOUTENT a la traduction, marquees « via dialogues »). 0 = rien a faire ou fait."""
    if deja_francais(chap_dir):
        return 0
    total = len(nc.pages_du_chapitre(chap_dir, "")[1])
    voulues = [n for n in nc_plage(a.pages, list(range(1, total + 1))) if 1 <= n <= total]
    tr = lire_json(os.path.join(chap_dir, "traduction", "fr", "traduction.json")) or {}
    # 1.12.0 (R13) : MEME regle que traduire_chapitre.page_lue -- lue si « lue », sinon (avant 2.2.0) au moins une bulle
    faites = {p["page"] for p in tr.get("pages") or [] if (bool(p.get("lue")) if "lue" in p else bool(p.get("bulles")))}
    manq = [n for n in voulues if n not in faites]
    if not manq:
        return 0
    os.makedirs(dd, exist_ok=True)
    nc.PROGRESS = os.path.join(dd, "progress.json")
    tp = os.path.join(chap_dir, "traduction", "fr", "progress.json")
    log("dialogues %s : %d page(s) a traduire d'abord (%s)" % (VERSION, len(manq), ", ".join("%d-%d" % tuple(x) for x in plages_contigues(manq))))
    fait = 0
    for de, fin in plages_contigues(manq):
        nc.progres("traduction", fait, len(manq))
        sys.stdout.flush()
        pr = subprocess.Popen([sys.executable, os.path.join(HERE, "traduire_chapitre.py"), a.chap, "--langue", "fr",
                               "--pages", "%d-%d" % (de, fin), "--via", "dialogues"])
        while pr.poll() is None:
            time.sleep(2)
            q = lire_json(tp) or {}
            nc.progres("traduction", fait + int(q.get("fait") or 0), len(manq))
        if pr.returncode != 0:
            nc.progres("erreur", fait, len(manq), fini=True, arret="traduction des pages %d-%d en echec" % (de, fin))
            print("ARRET : traduction des pages %d-%d en echec (code %s) -- rien n'est prepare" % (de, fin, pr.returncode))
            return 4
        fait += fin - de + 1
    return 0


# ---------------------------------------------------------------- 1.19.0 (R30) : bulles verifiees par Quang
def iou(a, b):
    x1, y1 = max(a["x"], b["x"]), max(a["y"], b["y"])
    x2, y2 = min(a["x"] + a["w"], b["x"] + b["w"]), min(a["y"] + a["h"], b["y"] + b["h"])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    uni = a["w"] * a["h"] + b["w"] * b["h"] - inter
    return inter / uni if uni > 0 else 0.0


def apparier(ref, bulles):
    """La bulle de la source qui correspond a une entree verifiee : meme zone (IoU >= 0.5), sinon meme id si la zone est proche."""
    best, bi = None, 0.0
    for b in bulles:
        v = iou(ref["box"], b["box"])
        if v > bi:
            best, bi = b, v
    if bi >= 0.5:
        return best
    same = [b for b in bulles if b["id"] == ref.get("id")]
    return same[0] if same and iou(ref["box"], same[0]["box"]) >= 0.2 else None


def appliquer_verif(page, bulles, verif):
    """bulles de la page (deja filtrees) + la verification de Quang -> liste dans SON ordre, exclues retirees, ajouts (lus sur
    l'image par Gemini, comme une page deja en VF). Sans verification : inchangee. Chaque bulle recoit « ordre »."""
    v = ((verif or {}).get("pages") or {}).get(str(page))
    if not v:
        return bulles
    ex = [apparier(r, bulles) for r in v.get("exclues") or []]
    ids_ex = {id(b) for b in ex if b is not None}
    reste = [b for b in bulles if id(b) not in ids_ex]
    for k, z in enumerate(v.get("ajouts") or []):
        if not any(iou(z["box"], b["box"]) >= 0.5 for b in reste):
            reste.append({"id": int(z.get("id") or 900 + k), "type": "dialogue", "box": {q: round(float(z["box"][q]), 4) for q in ("x", "y", "w", "h")},
                          "trad": "", "a_lire": True, "ajout": True})
    rang = {}
    for i, r in enumerate(v.get("ordre") or []):
        b = next((x for x in reste if x.get("ajout") and x["id"] == r.get("id") and iou(r["box"], x["box"]) >= 0.5), None) or apparier(r, reste)
        if b is not None and id(b) not in rang:
            rang[id(b)] = i
    base = len(rang)
    for b in sorted(reste, key=lambda x: x["id"]):
        b["ordre"] = rang.get(id(b), base + b["id"] / 10000.0)
    return sorted(reste, key=lambda x: x["ordre"])


def rang(x):
    """Cle de tri d'une replique dans sa page : l'ordre verifie par Quang s'il existe, sinon le n° de detection."""
    o = x.get("ordre")
    return o if o is not None else (x.get("id") or 0)


def cmd_detecter(a):
    """Detection SEULE (gratuite, sur le PC) des pages demandees qui ne sont PAS encore traduites -> dialogues/detection.json.
    Memes fonction et seuils que la traduction (traduire_chapitre.zones_texte) : ses n° correspondent aux siens."""
    chap_dir, serie_dir, dd = chemins(a.chap)
    os.makedirs(dd, exist_ok=True)
    nc.PROGRESS = os.path.join(dd, "progress.json")
    import ingest_page as ip
    import traduire_chapitre as tc
    man = lire_json(os.path.join(chap_dir, "manifest.json")) or {}
    fichiers = [os.path.basename(q.get("file") or "") for q in man.get("pages") or []]
    tr = lire_json(os.path.join(chap_dir, "traduction", "fr", "traduction.json")) or {}
    deja = {p["page"] for p in tr.get("pages") or [] if p.get("bulles") is not None}
    voulues = [n for n in nc_plage(a.pages, list(range(1, len(fichiers) + 1))) if n not in deja]
    f = os.path.join(dd, "detection.json")
    doc = lire_json(f) or {"pages": {}}
    for k, n in enumerate(voulues):
        nc.progres("detection", k, len(voulues))
        img = os.path.join(chap_dir, fichiers[n - 1])
        if not os.path.isfile(img):
            continue
        try:                                             # une image illisible ne bloque pas les autres pages
            texts = tc.zones_texte(ip.load_page(img), 0.25)
        except Exception as e:
            log("  page %d : detection impossible (%s)" % (n, str(e)[:120]))
            texts = []
        doc["pages"][str(n)] = {"file": fichiers[n - 1], "bulles": [{"id": t["id"], "box": {q: round(t[q], 4) for q in ("x", "y", "w", "h")}} for t in texts]}
    doc["maj"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    ecrire_json(f, doc)
    nc.progres("detection", len(voulues), len(voulues), fini=True)
    print("detection : %d page(s)" % len(voulues))
    return 0


def doutes(doc, distrib, plage):
    """1.21.0 : ce qui doit passer par ✏ AVANT de payer des voix, dans la portee : repliques « a traiter », personnage
    « inconnu » (lues), doublons probables de la distribution."""
    pv = set(nc_plage(plage, sorted({x["page"] for x in doc.get("repliques") or []}))) if plage else None
    reps = [x for x in doc.get("repliques") or [] if (pv is None or x["page"] in pv)]
    trait = [x["cle"] for x in reps if x.get("a_traiter") and not ((x.get("corrige") or {}).get("qui"))]
    inconnu = [x["cle"] for x in reps if x.get("lire") and (x.get("qui") or "inconnu") == "inconnu"]
    dbl = [g for g in distrib.get("doublons") or [] if g.get("garder") and g.get("avec")]
    return trait, inconnu, dbl


def cmd_tout(a):
    """1.21.0 : tout d'un coup, avec UN arret humain possible : avant les voix, si l'IA doute."""
    chap_dir, serie_dir, dd = chemins(a.chap)
    if not getattr(a, "sans_preparation", False):
        rc = cmd_preparer(a)
        if rc:
            return rc
    doc = lire_json(os.path.join(dd, "dialogues.json"))
    if not doc:
        print("ARRET : chapitre pas encore prepare"); return 3
    trait, inconnu, dbl = doutes(doc, distribution(serie_dir), a.pages)
    if trait or inconnu or dbl:
        motif = "; ".join(t for t in (
            ("%d replique(s) a traiter" % len(trait)) if trait else "",
            ("%d replique(s) sans personnage reconnu" % len(inconnu)) if inconnu else "",
            ("%d doublon(s) probable(s) de personnage" % len(dbl)) if dbl else "") if t)
        nc.PROGRESS = os.path.join(dd, "progress.json")
        nc.progres("doute", 0, 0, fini=True, arret=motif, cles=(trait + inconnu)[:40])
        log("ARRET avant les voix (doute de l'IA) : %s -- a regler dans ✏, puis relancer" % motif)
        return 5
    rc = cmd_voix(a)
    if rc:
        return rc
    return cmd_video(a)


def traduire_ajouts(chap_dir, dd, a, voulues):
    """1.22.0 : les bulles ajoutees par Quang sur des pages TRADUITES -> traduites et posees sur l'image, puis ajoutees a
    traduction.json. Retourne le nombre de bulles posees. Sans verification / sans traduction : rien."""
    verif = lire_json(os.path.join(dd, "bulles_verifiees.json")) or {}
    tf = os.path.join(chap_dir, "traduction", "fr", "traduction.json")
    tr = lire_json(tf)
    if not tr or not verif.get("pages"):
        return 0
    trp = {p["page"]: p for p in tr.get("pages") or []}
    man = lire_json(os.path.join(chap_dir, "manifest.json")) or {}
    fich = [os.path.basename(q.get("file") or "") for q in man.get("pages") or []]
    faites, st, pages_touchees = 0, {"tokens_in": 0, "tokens_out": 0, "cout": 0.0}, []
    for k, v in sorted(verif["pages"].items(), key=lambda kv: int(kv[0])):
        n = int(k)
        p = trp.get(n)
        if n not in voulues or not p or p.get("bulles") is None or not (0 < n <= len(fich)):
            continue
        nouveaux = [z for z in v.get("ajouts") or [] if not any(iou(z["box"], b["box"]) >= 0.5 for b in p["bulles"] if b.get("box"))]
        if not nouveaux:
            continue
        import ingest_page as ip
        import traduire_chapitre as tc
        img_t = os.path.join(chap_dir, "traduction", "fr", p.get("file") or "page_%03d.png" % n)
        if not os.path.isfile(img_t):
            continue
        texts = [dict(z["box"], id=int(z["id"]), conf=1.0) for z in nouveaux]
        try:
            lu = tc.traduire_page(ip.load_page(os.path.join(chap_dir, fich[n - 1])), texts, "gemini", "fr", st)
        except Exception as e:
            log("  page %d : bulle(s) ajoutee(s) non traduite(s) (%s) -- lue(s) a la preparation" % (n, str(e)[:120]))
            continue
        a_poser = [(t, lu.get(t["id"]) or {}) for t in texts if ((lu.get(t["id"]) or {}).get("trad") or "").strip()]
        if not a_poser:
            continue
        from PIL import ImageDraw
        rendu = ip.load_page(img_t).convert("RGB")
        W, H = rendu.size
        for t, b in a_poser:
            serre = tc.boite_lettres(rendu, t)                         # texte net sur fond clair, sinon None
            if serre:
                ImageDraw.Draw(rendu).rectangle([int(serre["x"] * W), int(serre["y"] * H), int((serre["x"] + serre["w"]) * W),
                                                 int((serre["y"] + serre["h"]) * H)], fill=(255, 255, 255))
                r, etat = tc.poser_texte(rendu, serre, b["trad"].strip(), False), "lettres seules"
            else:
                r, etat = {}, "non effacee (fond charge : image laissee telle quelle)"
            typ = b.get("type") if b.get("type") in ("dialogue", "narration") else "dialogue"
            p["bulles"].append(dict({"id": t["id"], "box": {q: round(t[q], 4) for q in ("x", "y", "w", "h")}, "type": typ,
                                     "texte": (b.get("texte") or "").strip(), "trad": b["trad"].strip(), "effacement": etat,
                                     "ajout": True}, **{q: r[q] for q in ("taille", "lignes", "tient") if q in r}))
            faites += 1
        if not os.path.isfile(img_t + ".avant_ajouts"):
            import shutil as _sh
            _sh.copy2(img_t, img_t + ".avant_ajouts")
        rendu.save(img_t)
        pages_touchees.append(n)
        log("  page %d : %d bulle(s) ajoutee(s) traduite(s) (%s)" % (n, len(a_poser), ", ".join(x.get("effacement", "") for x in p["bulles"][-len(a_poser):])))
    if faites:
        if not os.path.isfile(tf + ".avant_ajouts"):
            import shutil as _sh
            _sh.copy2(tf, tf + ".avant_ajouts")
        ecrire_json(tf, tr)
        depenses.noter("dialogues", a.chap, "traduction des bulles ajoutees", "gemini", round(st["cout"], 5), pages=pages_touchees)
    return faites


def piste_musique(musique, serie_dir, segments, sortie):
    """1.24.0 : la musique de fond de la video des Dialogues, MEME regle que video_chapitre.mixer. segments = [(duree, parle)].
    Ecrit un WAV stereo de la duree totale (gain applique) ; None si aucun morceau."""
    import numpy as np, random, wave
    import video_chapitre as vc
    md = os.path.join(serie_dir, "musique")
    dispo = os.listdir(md) if os.path.isdir(md) else []
    fichiers = [os.path.join(md, f[0]) for f in ([x for x in dispo if os.path.splitext(x)[0] == nom] for nom in musique.get("noms") or []) if f]
    if not fichiers:
        return None
    SR, total = vc.SR, sum(d for d, _ in segments)
    N_ = int((total + 0.5) * SR)
    rnd = random.Random(musique.get("graine") or 1)
    seq, mus, t, k = [], np.zeros((N_, 2), np.float32), 0.0, 0
    while t < total + 1:
        if len(seq) <= k:
            tour = list(range(len(fichiers))); rnd.shuffle(tour)
            if len(fichiers) > 1 and seq and tour[0] == seq[-1]:
                tour.append(tour.pop(0))
            seq += tour
        x = vc.pcm(fichiers[seq[k]])
        d = len(x) / SR
        env = np.minimum(1.0, np.minimum(np.arange(len(x)) / SR / vc.FONDU, (d - np.arange(len(x)) / SR) / vc.FONDU)).clip(0, 1)
        i0 = int(t * SR); i1 = min(N_, i0 + len(x))
        if i1 > i0:
            mus[i0:i1] += x[: i1 - i0] * env[: i1 - i0, None]
        t += max(1.0, d - vc.FONDU); k += 1
    parle, t = np.zeros(int(total * 10) + 2, bool), 0.0
    for d, p in segments:
        if p:
            parle[int(t * 10): int((t + max(0.0, d - 0.4)) * 10) + 1] = True    # le silence de fin de replique (apad 0,4 s) laisse remonter
        t += d
    base = float(musique.get("volume", 25)) / 100 * vc.GAIN_MAX
    g, gains = 0.0, []
    for st in range(int((total + 1.2) * 10) + 1):
        cible = 0.0 if st / 10 >= total else base * (vc.DUCK if st < len(parle) and parle[st] else 1)
        g += max(-0.02, min(max(0.004, cible * 0.04), cible - g))
        gains.append(g)
    gain = np.interp(np.arange(N_) / SR, np.arange(len(gains)) / 10, np.array(gains)).astype(np.float32)
    mus = np.clip(mus * gain[:, None], -1, 1)
    with wave.open(sortie, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mus * 32767).astype("<i2").tobytes())
    return sortie


def cmd_preparer(a):
    chap_dir, serie_dir, dd = chemins(a.chap)
    if getattr(a, "traduire", False):
        rc = traduire_manquantes(a, chap_dir, dd)
        if rc:
            return rc
    try:                                                                   # 1.22.0 : bulles entourees -> traduites sur la page
        _tr0 = lire_json(os.path.join(chap_dir, "traduction", "fr", "traduction.json")) or {}
        traduire_ajouts(chap_dir, dd, a, set(nc_plage(a.pages, [p["page"] for p in _tr0.get("pages") or []])))
    except Exception as e:
        log("  bulles ajoutees : traduction sur la page impossible (%s) -- elles seront lues a la preparation" % str(e)[:160])
    tr = source_bulles(chap_dir, a.pages)
    if not tr:
        print("ARRET : pas de traduction francaise pour %s -- traduis d'abord ce chapitre en francais" % a.chap)
        return 3
    os.makedirs(dd, exist_ok=True)
    nc.PROGRESS = os.path.join(dd, "progress.json")
    stats = {}
    nc.STATS = stats
    voulues = set(nc_plage(a.pages, [p["page"] for p in tr["pages"]]))
    verif = lire_json(os.path.join(dd, "bulles_verifiees.json"))              # 1.19.0 (R30)
    pages = []
    for p in tr["pages"]:
        if p["page"] in voulues:
            p["_bulles"] = sorted([b for b in p["bulles"] if b["type"] in ("dialogue", "narration") and (not b.get("ecarte") or ecarte_pour_image(b))
                                   and ((b.get("trad") or "").strip() or b.get("a_lire"))], key=lambda b: b["id"])
            p["_bulles"] = appliquer_verif(p["page"], p["_bulles"], verif)      # 1.19.0 (R30) : exclues / ajouts / ORDRE de Quang
            if p["_bulles"]:
                pages.append(p)
    if not pages:
        print("ARRET : aucune bulle a lire dans ces pages")
        return 3
    distrib = distribution(serie_dir)
    narr_d = os.path.join(chap_dir, "narration")
    tags = sorted(os.listdir(narr_d)) if os.path.isdir(narr_d) else []
    narr = lire_json(os.path.join(narr_d, tags[0], "narration.json")) if tags else None
    cat = voix_francaises() or catalogue_el()                  # 1.15.0 (R19) : 100 % francaises, sinon le compte
    cat = avec_preferees(cat)                                   # 1.17.0 (R24) : les PREFEREES d'abord
    relais = reglages.relais_moderation()
    log("dialogues %s preparer %s : %d pages, %d bulles, %d personnages connus, relais %s" % (
        VERSION, a.chap, len(pages), sum(len(p["_bulles"]) for p in pages), len(distrib["persos"]), "oui" if relais else "non"))
    t0 = time.time()
    reponses, a_traiter = preparer_pages(chap_dir, a.chap, pages, distrib, narr, cat, stats, relais)
    ajoutes = stats.pop("_ajoutes", [])                      # 1.8.1 : fusionnes au fil des lots
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
    generes = set()                                                     # 1.20.0 : ce que CETTE preparation produit
    for p in pages:
        img = os.path.join(chap_dir, *p["img_rel"].split("/"))
        for b in p["_bulles"]:
            cle = "%d-%d" % (p["page"], b["id"])
            generes.add(cle)
            x = rep.get((p["page"], b["id"]))
            vieux = par_cle.get(cle) or {}
            corr = vieux.get("corrige") or {}
            texte = ((b.get("trad") or "").strip() or ((x or {}).get("texte") or "").strip())   # VF : lu par Gemini
            neuf = {"cle": cle, "page": p["page"], "id": b["id"], "file": p["file"], "img_rel": p["img_rel"], "type": b["type"],
                    "box": b["box"], "contour": contour_bulle(img, b["box"]), "ordre": b.get("ordre", b["id"]),
                    "texte_origine": texte, "texte": texte,
                    "qui": nom_connu(distrib, x.get("qui")) if x else "inconnu",
                    "ton": (x or {}).get("ton") or "", "lire": bool((x or {}).get("lire", True)) and bool(re.search(r"\w", texte)),
                    "indice": (x or {}).get("indice") or "", "a_traiter": p["page"] in a_traiter,
                    "corrige": corr, "voix": vieux.get("voix")}
            if b["type"] == "narration" and neuf["qui"] == "narrateur":
                neuf["lire"] = neuf["lire"] and bool(distrib["narrateur"].get("lire"))
            neuf.update({k: v for k, v in corr.items() if k in ("texte", "qui", "ton", "lire")})   # les corrections gagnent
            if (vieux and "ton" not in corr and vieux.get("ton") is not None and vieux.get("qui") == neuf["qui"]
                    and (vieux.get("texte") or "").strip() == (neuf.get("texte") or "").strip()):
                neuf["ton"] = vieux["ton"]                   # 1.23.0 : meme texte, meme personnage -> meme ton -> meme voix
            par_cle[cle] = neuf
    traitees = voulues & {p["page"] for p in tr["pages"]}               # 1.20.0 : pages de la plage connues de la source
    retirees = [c for c, x in par_cle.items() if x.get("page") in traitees and c not in generes]
    for c in retirees:
        par_cle.pop(c)
    if retirees:
        log("  %d replique(s) retiree(s) : bulle exclue ou plus detectee (%s)" % (len(retirees), ", ".join(sorted(retirees)[:12])))
    ambiances = [r.get("ambiance") for r in reponses if r.get("ambiance")]
    try:
        total = len(nc.pages_du_chapitre(chap_dir, "")[1])
    except Exception:                                    # pas de manifest (banc, import) : les pages connues de la traduction
        total = max([p["page"] for p in tr["pages"]] or [0])
    vues = set(ancien.get("pages_vues") or []) | {n for n in voulues if 1 <= n <= total}     # 1.9.1 : pages SANS bulle comprises
    doc = {"version": VERSION, "chapitre": a.chap, "maj": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "ambiance": " / ".join(ambiances)[:400] if ambiances else ancien.get("ambiance", ""),
           "pages_vues": sorted(vues),
           "portees": [x for x in (ancien.get("portees") or []) if x != (a.pages or "tout")] + [a.pages or "tout"],   # 1.9.1 : la derniere en fin
           "repliques": sorted(par_cle.values(), key=lambda x: (x["page"], rang(x)))}
    ecrire_json(fch, doc)
    if ajoutes:                                                          # 1.11.0 (D12) : de nouveaux noms -> doublons probables ?
        try:
            dbl = doublons_probables(distrib, serie_dir, stats)
            if dbl:
                log("  doublons probables (a confirmer dans l'app) : %s" % "; ".join(g["garder"] + " = " + ", ".join(g["avec"]) for g in dbl))
        except Exception as e:
            log("  controle des doublons impossible : %s" % str(e)[:120])
    ecrire_json(os.path.join(serie_dir, "dialogues_distribution.json"), distrib)
    cout = round(stats.get("cout_preparation", 0.0) + stats.get("cout_doublons", 0.0), 5)
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


def doublons_probables(distrib, serie_dir, stats):
    """1.11.0 (D12) : groupes de noms qui designent PROBABLEMENT le meme personnage (l'IA de preparation, lot par lot, a pu
    le nommer deux fois selon le dessin). Ecrits dans distrib["doublons"] = [{garder, avec, raison}] ; JAMAIS fusionnes ici."""
    persos = distrib.get("persos") or []
    if len(persos) < 2:
        distrib["doublons"] = []
        return []
    ex, nb = {p["nom"]: [] for p in persos}, {p["nom"]: 0 for p in persos}
    for ch in sorted(os.listdir(serie_dir)):
        d = lire_json(os.path.join(serie_dir, ch, "dialogues", "dialogues.json")) if ch.startswith("ch_") else None
        for x in (d or {}).get("repliques") or []:
            q = x.get("qui")
            if q in ex:
                nb[q] += 1
                if len(ex[q]) < 5 and (x.get("texte") or "").strip():
                    ex[q].append("%s p.%s : %s" % (ch, x.get("page"), x["texte"][:90]))
    ecartes = {tuple(sorted(e)) for e in distrib.get("pas_doublons") or []}
    donnees = [{"nom": p["nom"], "genre": p.get("genre"), "age": p.get("age"), "fiche": p.get("fiche"), "alias": p.get("alias") or [],
                "repliques": ex[p["nom"]]} for p in persos]
    r = nc.post("/api/deepseek", {"model": "deepseek-v4-flash", "max_tokens": 2000, "temperature": 0,
                "thinking": {"type": "disabled"}, "response_format": {"type": "json_object"},
                "messages": [{"role": "system", "content": "Tu recois les personnages d'UN manga, reperes page par page par une IA qui a pu "
                              "donner deux noms au MEME personnage (description differente selon le dessin : couleur des cheveux ou des yeux "
                              "qui varie avec l'encrage, eclairage, angle). Rends les groupes de noms qui designent TRES PROBABLEMENT la meme "
                              "personne. Sois prudent : meme genre obligatoire, meme role ; deux personnages qui se REPONDENT dans une meme scene "
                              "ne sont PAS la meme personne. JSON {\"doublons\": [{\"noms\": [\"...\", \"...\"], \"raison\": \"courte, en francais\"}]}, "
                              "liste vide si aucun."},
                             {"role": "user", "content": json.dumps(donnees, ensure_ascii=False)}]})
    rep_ = nc.parse_json(r["choices"][0]["message"]["content"]) or {}
    stats["cout_doublons"] = stats.get("cout_doublons", 0.0) + nc.cout("deepseek-v4-flash", r.get("usage") or {})
    groupes = []
    for g in rep_.get("doublons") or []:
        noms = list(dict.fromkeys(n for n in (g.get("noms") or []) if n in ex))
        if len(noms) < 2 or tuple(sorted(noms)) in ecartes:
            continue
        noms.sort(key=lambda n: -nb[n])                                   # on garde celui qui parle le plus
        groupes.append({"garder": noms[0], "avec": noms[1:], "raison": str(g.get("raison") or "")[:200]})
    distrib["doublons"] = groupes
    return groupes


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
    besoin = sum(cout_el(p[1]) for p in plan)
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
                credits += cout_el(envoye)
                stats["_car_envoyes"] = stats.get("_car_envoyes", 0) + len(envoye)     # 1.25.0 : pour recaler le tarif
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
    time.sleep(2)                                                          # 1.25.0 : le compteur ElevenLabs suit en ~1 s
    solde2 = el_solde()
    estime = credits
    if faits and solde and solde2 and solde2.get("limite") == solde.get("limite") and solde2["utilises"] >= solde["utilises"]:
        reel = solde2["utilises"] - solde["utilises"]
        if reel > 0:
            recaler_tarif(reel, stats.get("_car_envoyes", 0))
            credits = reel
            log("  credits MESURES : %d (estimation : %d)" % (reel, estime))
    depenses.noter_credits("dialogues", a.chap, "voix", "elevenlabs", credits, repliques=faits)
    depenses.noter("dialogues", a.chap, "balises", "deepseek", round(stats.get("cout_balises", 0.0), 5))
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
    depenses.noter_credits("dialogues", a.chap, "ecoute", "elevenlabs", cout_el(envoye), repliques=1)
    if propre:                                                  # c'est SA voix : on la garde comme definitive
        doc = lire_json(os.path.join(dd, "dialogues.json"))
        for y in doc["repliques"]:
            if y["cle"] == a.cle:
                y["voix"] = {"empreinte": emp, "fichier": emp + ".mp3", "duree": nc.duree_mp3(f), "fuite": False,
                             "t": time.strftime("%Y-%m-%dT%H:%M:%S")}
        ecrire_json(os.path.join(dd, "dialogues.json"), doc)
    print(json.dumps({"fichier": "dialogues/" + rel, "credits": cout_el(envoye), "deja": False, "definitive": bool(propre)}))
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
    etats, credits, a_faire, deja = etat_voix(doc, distrib, dd)
    # la video est-elle a jour ? (meme empreinte que cmd_video) -- 1.10.0 : une par portee
    vid = "absente"
    if doc.get("video") and os.path.isfile(os.path.join(dd, "video", "dialogues.mp4")):
        vid = "a_jour" if empreinte_video(doc, distrib, dd)[1] == doc["video"].get("empreinte") else "perimee"
    videos = {}
    for portee, v in (doc.get("videos") or {}).items():
        if not os.path.isfile(os.path.join(dd, "video", os.path.basename(v.get("fichier", "?")))):
            continue
        videos[portee] = "a_jour" if empreinte_video(doc, distrib, dd, "" if portee == "tout" else portee)[1] == v.get("empreinte") else "perimee"
    print(json.dumps({"repliques": etats, "a_faire": a_faire, "credits": credits, "deja": deja, "video": vid, "videos": videos}, ensure_ascii=False))


def dans_portee(page, portee):
    if not portee:
        return True
    a_, _, b_ = portee.partition("-")
    return int(a_) <= page <= int(b_ or a_)


def ecoute_de(distrib, qui):
    """1.14.0 (R17) : la vitesse d'ECOUTE du personnage (1 = telle que generee). Jamais envoyee a ElevenLabs."""
    try:
        return round(max(0.7, min(1.5, float((reglage_voix(distrib, qui) or {}).get("ecoute") or 1))), 2)
    except (TypeError, ValueError):
        return 1.0


def empreinte_video(doc, distrib, dd, portee=""):
    """1.10.0 : (repliques de la video, empreinte) -- la meme pour plan et video."""
    import hashlib
    couleur = lambda q: (reglage_voix(distrib, q) or {}).get("couleur") or "#9aa6b8"
    liste = [x for x in doc["repliques"] if x.get("lire") and x.get("voix") and dans_portee(x["page"], portee)
             and os.path.isfile(os.path.join(dd, "voix", x["voix"]["fichier"]))]
    # 1.14.0 : l'ecoute n'entre que si elle differe de 1 (les videos d'avant restent « a jour »)
    return liste, hashlib.sha1(json.dumps([[x["cle"], x["voix"]["empreinte"], x.get("texte"), couleur(x["qui"]), x["qui"]]
                                           + ([ecoute_de(distrib, x["qui"])] if ecoute_de(distrib, x["qui"]) != 1 else [])
                                           for x in liste]).encode()).hexdigest()[:16]


def etat_voix(doc, distrib, dd):
    """1.9.0 -- la SEULE definition de « voix a jour » (plan, video) : ({cle: etat}, credits, a_faire, deja)."""
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
            etats[x["cle"]] = "a_refaire" if v else "a_faire"; a_faire += 1; credits += cout_el(envoye)
    return etats, credits, a_faire, deja


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
        tr = os.path.isfile(os.path.join(serie_dir, ch, "traduction", "fr", "traduction.json")) or deja_francais(os.path.join(serie_dir, ch))
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


# ================================================================ D7 : la VIDEO des dialogues (MP4, pour le telephone hors ligne)
VW, VH, BANDE = 1080, 1920, 330


def _police(taille, gras=False):
    from PIL import ImageFont
    for f in (("arialbd.ttf" if gras else "arial.ttf"), "DejaVuSans-Bold.ttf" if gras else "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(f, taille)
        except OSError:
            continue
    return ImageFont.load_default()


def _hex(c):
    c = (c or "#9aa6b8").lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def image_replique(page_png, x, couleur, nom, dest):
    """Meme rendu que le lecteur : page voilee, halo au contour reel (repli ovale), pastille au nom, sous-titre en bas."""
    import numpy as np, cv2
    from PIL import Image, ImageDraw, ImageFilter
    pg = Image.open(page_png).convert("RGB")
    k = min(VW / pg.width, (VH - BANDE) / pg.height)
    pw, ph = round(pg.width * k), round(pg.height * k)
    pg = pg.resize((pw, ph), Image.LANCZOS)
    ox, oy = (VW - pw) // 2, (VH - BANDE - ph) // 2
    masque = np.zeros((ph, pw), np.uint8)
    if x.get("contour") and len(x["contour"]) > 2:
        pts = np.array([[int(p[0] * pw), int(p[1] * ph)] for p in x["contour"]], np.int32)
        cv2.fillPoly(masque, [pts], 255)
    else:
        b = x["box"]
        cv2.ellipse(masque, (int((b["x"] + b["w"] / 2) * pw), int((b["y"] + b["h"] / 2) * ph)),
                    (int(b["w"] * pw / 2 + pw * .012), int(b["h"] * ph / 2 + ph * .01)), 0, 0, 360, 255, -1)
    arr = np.asarray(pg).astype(np.float32)
    dehors = (masque == 0)[..., None]
    arr = np.where(dehors, arr * 0.62, arr)                                      # voile ~38 % hors de la bulle
    rgb = np.array(_hex(couleur), np.float32)
    trait = cv2.dilate(masque, np.ones((5, 5), np.uint8), iterations=3) - masque
    lueur = cv2.GaussianBlur(cv2.dilate(masque, np.ones((9, 9), np.uint8), iterations=3) - cv2.erode(masque, np.ones((3, 3), np.uint8)),
                             (0, 0), max(4, pw / 90)).astype(np.float32) / 255.0
    a = np.clip(lueur * 1.3, 0, 1)[..., None] * (masque == 0)[..., None]
    arr = arr * (1 - a) + rgb * a
    arr[trait > 0] = rgb
    page = Image.fromarray(arr.clip(0, 255).astype(np.uint8))
    im = Image.new("RGB", (VW, VH), (7, 8, 11))
    im.paste(page, (ox, oy))
    d = ImageDraw.Draw(im)
    ys, xs = np.where(masque > 0)
    f1 = _police(34, True)
    if len(xs):
        cx, haut = ox + (xs.min() + xs.max()) / 2, oy + ys.min()
        tw = d.textlength(nom, font=f1)
        px, py = max(8, min(VW - tw - 40, cx - tw / 2 - 16)), max(8, haut - 62)
        d.rounded_rectangle([px, py, px + tw + 32, py + 50], radius=25, fill=_hex(couleur))
        d.text((px + 16, py + 7), nom, font=f1, fill=(20, 8, 15))
    f2, f3 = _police(44, True), _police(40)
    y0 = VH - BANDE + 34
    d.rounded_rectangle([48, y0 + 8, 76, y0 + 36], radius=14, fill=_hex(couleur))
    d.text((92, y0), nom, font=f2, fill=_hex(couleur))
    lignes, cour = [], ""
    for m in (x.get("texte") or "").split():
        if d.textlength((cour + " " + m).strip(), font=f3) > VW - 96:
            lignes.append(cour); cour = m
        else:
            cour = (cour + " " + m).strip()
    lignes.append(cour)
    for i, l in enumerate(lignes[:4]):
        d.text((48, y0 + 66 + i * 52), l, font=f3, fill=(232, 236, 243))
    im.save(dest)


def image_page_vide(page_png, num, dest):
    """1.9.2 : une page de la portee SANS replique -- page entiere + tampon « SANS DIALOGUE » (comme le lecteur)."""
    from PIL import Image, ImageDraw
    pg = Image.open(page_png).convert("RGB")
    k = min(VW / pg.width, (VH - BANDE) / pg.height)
    pw, ph = round(pg.width * k), round(pg.height * k)
    im = Image.new("RGB", (VW, VH), (7, 8, 11))
    im.paste(pg.resize((pw, ph), Image.LANCZOS), ((VW - pw) // 2, (VH - BANDE - ph) // 2))
    d = ImageDraw.Draw(im)
    f = _police(34, True)
    t = "SANS DIALOGUE"
    tw = d.textlength(t, font=f)
    d.rounded_rectangle([VW - tw - 84, 40, VW - 40, 100], radius=10, outline=(229, 83, 75), width=4, fill=(7, 8, 11))
    d.text((VW - tw - 62, 52), t, font=f, fill=(255, 157, 150))
    d.text((48, VH - BANDE + 40), "page %d" % num, font=_police(40), fill=(138, 148, 168))
    im.save(dest)


def cmd_video(a):
    import hashlib, shutil, subprocess
    chap_dir, serie_dir, dd = chemins(a.chap)
    doc = lire_json(os.path.join(dd, "dialogues.json"))
    if not doc:
        print("ARRET : chapitre pas encore prepare"); return 3
    distrib = distribution(serie_dir)
    portee = getattr(a, "pages", "") or ""                          # 1.10.0 : la video d'une PORTEE
    etats, _cr, _m, _ = etat_voix(doc, distrib, dd)                  # 1.9.0 : jamais de trou silencieux dans la video
    pages_de = {x["cle"]: x["page"] for x in doc["repliques"]}
    manq = sum(1 for c, v in etats.items() if v in ("a_faire", "a_refaire", "sans_voix", "a_traiter") and dans_portee(pages_de.get(c, 0), portee))
    if manq:
        print("ARRET : %d replique(s) sans voix a jour -- genere d'abord les voix (la video ne saute aucune replique)" % manq); return 3
    liste = [x for x in doc["repliques"] if etats.get(x["cle"]) == "faite" and dans_portee(x["page"], portee)]
    if not liste:
        print("ARRET : aucune voix faite -- lance d'abord les voix"); return 3
    # 1.9.2 : les pages de la portee SANS replique ont leur plan (comme le lecteur) -- page traduite si elle existe
    avec = {x["page"] for x in doc["repliques"] if x.get("lire")}
    fich = [q.get("file") for q in (lire_json(os.path.join(chap_dir, "manifest.json")) or {}).get("pages") or []]
    etapes = list(liste)
    for n in doc.get("pages_vues") or []:
        if n in avec or not dans_portee(n, portee):
            continue
        tr = os.path.join(chap_dir, "traduction", "fr", "page_%03d.png" % n)
        src = tr if os.path.isfile(tr) else (os.path.join(chap_dir, fich[n - 1]) if 0 < n <= len(fich) else None)
        if src and os.path.isfile(src):
            etapes.append({"page": n, "id": 0, "vide": True, "src": src})
    etapes.sort(key=lambda x: (x["page"], rang(x) if not x.get("vide") else -1))     # 1.19.0 : l'ordre verifie
    nc.PROGRESS = os.path.join(dd, "progress.json")
    vd = os.path.join(dd, "video")
    tmp = os.path.join(vd, "_tmp")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp, exist_ok=True)
    couleur = lambda q: (reglage_voix(distrib, q) or {}).get("couleur") or "#9aa6b8"
    t0 = time.time()
    segs, imgs = [], []
    for k, x in enumerate(etapes):
        nc.progres("video", k, len(etapes))
        if x.get("vide"):
            img, seg = os.path.join(tmp, "i%04d.png" % k), os.path.join(tmp, "a%04d.m4a" % k)
            image_page_vide(x["src"], x["page"], img)
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", "2.2",
                            "-c:a", "aac", "-b:a", "160k", seg], check=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            segs.append(seg); imgs.append((img, 2.2))
            continue
        png = os.path.join(chap_dir, *(x.get("img_rel") or "traduction/fr/" + x["file"]).split("/"))
        img = os.path.join(tmp, "i%04d.png" % k)
        image_replique(png, x, couleur(x["qui"]), "Narrateur" if x["qui"] == "narrateur" else x["qui"], img)
        seg = os.path.join(tmp, "a%04d.m4a" % k)
        ec = ecoute_de(distrib, x["qui"])                     # 1.14.0 (R17) : vitesse d'ecoute, hauteur conservee
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", os.path.join(dd, "voix", x["voix"]["fichier"]),
                        "-af", ("atempo=%g," % ec if ec != 1 else "") + "apad=pad_dur=0.4",
                        "-ar", "44100", "-ac", "2", "-c:a", "aac", "-b:a", "160k", seg], check=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        segs.append(seg); imgs.append((img, nc.duree_mp3(seg) or ((x["voix"].get("duree") or 1.5) + 0.4)))
    with open(os.path.join(tmp, "a.txt"), "w", encoding="utf-8") as f:
        f.writelines("file '%s'\n" % s.replace("\\", "/") for s in segs)
    with open(os.path.join(tmp, "i.txt"), "w", encoding="utf-8") as f:
        for i_, du in imgs:
            f.write("file '%s'\nduration %.3f\n" % (i_.replace("\\", "/"), du))
        f.write("file '%s'\n" % imgs[-1][0].replace("\\", "/"))
    nc.progres("video", len(liste), len(liste), etape_video="assemblage")
    nom = "dialogues_p%s" % portee if portee else "dialogues"
    sortie = os.path.join(vd, nom + ".mp4")
    base = ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", os.path.join(tmp, "i.txt"), "-f", "concat", "-safe", "0",
            "-i", os.path.join(tmp, "a.txt"), "-vf", "fps=30,format=yuv420p"]
    fin = ["-c:a", "copy", "-shortest", "-movflags", "+faststart", sortie]
    musique = json.loads(getattr(a, "musique", "") or "null") if getattr(a, "musique", "") else None     # 1.24.0
    piste = None
    if musique and musique.get("noms"):
        try:
            piste = piste_musique(musique, serie_dir, [(du, not x.get("vide")) for (_i, du), x in zip(imgs, etapes)], os.path.join(tmp, "musique.wav"))
        except Exception as e:
            log("  musique de fond impossible (%s) : video sans musique" % str(e)[:160])
    if piste:
        base = [x for x in base if x not in ("-vf", "fps=30,format=yuv420p")] + ["-i", piste, "-filter_complex",
                "[0:v]fps=30,format=yuv420p[v];[1:a][2:a]amix=inputs=2:duration=first:normalize=0[a]", "-map", "[v]", "-map", "[a]"]
        fin = ["-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", sortie]
    r = subprocess.run(base + ["-c:v", "h264_nvenc", "-preset", "p5", "-cq", "24"] + fin, capture_output=True, text=True,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if r.returncode:                                                          # pas de carte NVIDIA : encodeur logiciel
        r2 = subprocess.run(base + ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23"] + fin, capture_output=True, text=True,
                            errors="replace", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if r2.returncode:                                                     # 1.24.0 : l'erreur d'ffmpeg dans le journal
            log("ECHEC ffmpeg (nvenc : %s) (x264 : %s)" % ((r.stderr or "")[-300:], (r2.stderr or "")[-300:]))
            raise RuntimeError("video : ffmpeg a echoue (voir le journal)")
    shutil.rmtree(tmp, ignore_errors=True)
    emp = empreinte_video(doc, distrib, dd, portee)[1]
    doc = lire_json(os.path.join(dd, "dialogues.json"))
    vides = [x["page"] for x in etapes if x.get("vide")]
    v = {"fichier": a.chap + "/dialogues/video/" + nom + ".mp4", "empreinte": emp, "repliques": len(liste), "pages_sans_dialogue": vides,
         "duree": nc.duree_mp3(sortie), "t": time.strftime("%Y-%m-%dT%H:%M:%S"), "portee": portee or "tout",
         "musique": ({"noms": musique.get("noms"), "volume": musique.get("volume")} if piste else None)}   # 1.24.0
    doc.setdefault("videos", {})[portee or "tout"] = v
    if not portee:
        doc["video"] = v                                                # l'ancienne cle (chapitre entier) reste lue
    ecrire_json(os.path.join(dd, "dialogues.json"), doc)
    # le nom du fichier telecharge (/manga/video_file?dl=1) se lit dans <video>.json : pages FR, sous-titres, sans musique
    ecrire_json(os.path.join(vd, nom + ".json"), {"tag": nom, "created_at": v["t"],
                                                     "reglages": {"pages": "fr", "sous": True, "musique": bool(piste)}})
    nc.progres("fini", len(liste), len(liste), fini=True, video=v, s=round(time.time() - t0, 1))
    log("OK video %s : %d repliques, %.0f s de video, %.0f s de fabrication" % (sortie, len(liste), v["duree"] or 0, time.time() - t0))
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
    pr.add_argument("--traduire", action="store_true", help="1.8.0 : traduire d'abord les pages demandees qui ne le sont pas")
    vo = sp.add_parser("voix"); vo.add_argument("chap"); vo.add_argument("--pages", default="")
    ec = sp.add_parser("ecouter"); ec.add_argument("chap"); ec.add_argument("--cle", required=True)
    ec.add_argument("--qui", default=""); ec.add_argument("--ton", default=None)
    pl = sp.add_parser("plan"); pl.add_argument("chap")
    vi = sp.add_parser("video"); vi.add_argument("chap"); vi.add_argument("--pages", default="", help="1.10.0 : la video de cette portee seulement")
    vi.add_argument("--musique", default="", help="1.24.0 : JSON {noms, volume} -- musique de fond de la serie")
    de = sp.add_parser("detecter"); de.add_argument("chap"); de.add_argument("--pages", default="")     # 1.19.0 (R30)
    to = sp.add_parser("tout"); to.add_argument("chap"); to.add_argument("--pages", default="")         # 1.21.0
    to.add_argument("--traduire", action="store_true"); to.add_argument("--sans-preparation", action="store_true", dest="sans_preparation")
    to.add_argument("--musique", default="")                                                             # 1.24.0
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
    if a.cmd == "video":
        return cmd_video(a)
    if a.cmd == "lot":
        return cmd_lot(a)
    if a.cmd == "detecter":
        return cmd_detecter(a)
    if a.cmd == "tout":
        return cmd_tout(a)


if __name__ == "__main__":
    sys.exit(main() or 0)
