# -*- coding: utf-8 -*-
"""Traduire les DIALOGUES d'un chapitre entier (etape 11 b, Manga Studio v1.84.0, 22/09/2026).

Pour chaque page de sources/<chap>/ :
  1. detection des bulles (YOLO Manga109, ingest_page.detect -- reutilise tel quel) ;
  2. UN appel vision par page (Gemini par defaut) : la PAGE entiere pour le contexte + chaque bulle
     decoupee et NUMEROTEE -> transcription, type (dialogue / narration / onomatopee / vide), traduction ;
  3. effacement des SEULES bulles traduites (ingest_page.clean_bubbles, OpenCV, sans IA) : les
     onomatopees ne sont ni effacees ni traduites (choix du 22/09, usage des groupes de traduction) ;
  4. pose du texte traduit (Pillow, Comic Neue gras, OFL) a la plus grande taille qui tient ;
  5. sources/<chap>/traduction/<langue>/page_NNN.png + traduction.json (+ progress.json pour l'app).

v1.92.0 (23/09) : les bulles VUES sous le seuil sont rattrapees EN COMPLEMENT (zones_texte). Etat des lieux sur les
203 pages traduites (8 chapitres) : 206 zones sous 0,25 jamais traitees, dont 53 vraies repliques des 0,10. Baisser le
seuil tout court REMPLACAIT 10 bonnes bulles par un fragment plus petit (sans_chevauchement garde la plus petite) ->
on garde le traitement a 0,25 A L'IDENTIQUE et on n'y ajoute que les zones faibles qui ne touchent AUCUNE bulle forte.
Une zone sans texte (dessin, logo) n'est jamais effacee : on n'efface que ce que le modele lit comme dialogue.

Pixtral etait le moteur de l'onglet Ingestion : mesure du 22/09 sur Claymore p.5 -> 2 bulles / 7 non
traduites, du markdown (« **...** ») colle au texte, une faute. D'ou Gemini, comme pour la narration.

Usage (venv kohya : ultralytics + opencv) :
  python traduire_chapitre.py claymore/ch_1 --langue fr [--pages 1-20] [--engine gemini|kimi]
"""
import argparse, base64, io, json, os, re, sys, time
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import narrate_chapter as nc          # appel_vision (Gemini natif / K3), frein 18/min, couts, journal
import ingest_page as ip              # load_page, detect, clean_bubbles
import effacement_local as el         # v1.98.0 : masque des lettres + LaMa (option --effacement local)

VERSION = "1.98.0"
# v1.98.0 (24/09, feuille de route 4-nonies etape 2) : --effacement local = le texte pose sur le DESSIN est efface par
# masque des lettres (comic-text-detector) + LaMa manga (effacement_local.py) au lieu d'un rectangle blanc ; les vraies
# bulles restent videes comme avant. Option : sans elle, rien ne change.
# v1.97.0 (24/09, remontee Video Studio : cases entieres effacees, dessin compris) : l'effacement ne rebouche plus que
# les trous situes DANS la boite du texte (les lettres) -- hors du texte, un « trou » est un personnage sur fond clair.
# Et une zone de COMPLEMENT qui ne peut etre effacee qu'en boite entiere est ecartee si elle couvre > 5 % de la page
# (ch.3 p.7 : zone de 32 % de la page, toute la case du bas peinte en blanc).
# v1.96.0 (23/09, T1-bis) : le seuil « 6x » s'appliquait a TOUTES les pages et abimait les vraies bulles a texte vertical
# etroit (Black Jack : 28 bulles, texte pose en taille 8). Mesure : pages devenues blanches = >= 22,5 % du dessin blanchi ;
# pages saines (OPM, Black Jack, Noritaka) <= 13,6 %. => effacement d'avant, et SEULEMENT si > 18 % de la page a ete
# blanchie, la page est refaite avec la regle du fond (ratio 6).
SEUIL_BLANCHI = 18.0
BOITE_MAX = 0.25                      # v1.97.0 : jamais un effacement en boite entiere sur plus du quart de la page
COMPLEMENT_BOITE_MAX = 0.05           # v1.97.0 : zone de complement effacee en boite entiere > 5 % de la page = ecartee
COUVERTURE_MIN = 0.5                  # v1.95.0 : effacement qui couvre < 50 % du texte = rate -> boite entiere
# v1.93.0 (23/09/2026, remontee Video Studio : 20 pages OPM traduites devenues BLANCHES) : le seuil « bulle 6x plus
# grande que son texte = fond de case » s'applique desormais A L'EFFACEMENT (ingest_page.clean_bubbles), plus seulement
# a l'endroit ou l'on ecrit : avant, tout le fond clair etait deja peint en blanc.
RATIO_FOND = 6
FONT_BOLD = os.path.join(HERE, "fonts", "ComicNeue-Bold.ttf")
LANGUES = {"fr": "français", "en": "anglais", "es": "espagnol", "de": "allemand", "it": "italien",
           "pt": "portugais", "vi": "vietnamien"}
PROGRESS = None


def progres(fait, total, **kw):
    if PROGRESS:
        try:
            with open(PROGRESS, "w", encoding="utf-8") as f:
                json.dump(dict(etape="traduction", fait=fait, total=total, t=time.time(), pid=os.getpid(), **kw), f)
        except Exception:
            pass


SYS = """Tu es traducteur de manga. On te donne une PAGE entiere (pour le contexte : qui parle, le ton, la
scene) puis des BULLES decoupees et numerotees de cette page. Pour CHAQUE bulle numerotee :
- "texte" : transcription exacte de ce qui est ecrit (vide si rien de lisible) ;
- "type" : "dialogue" (paroles, pensees), "narration" (cartouche, recitatif), "onomatopee" (bruit dessine :
  BOOM, SLASH, ドン...), ou "vide" ;
- "trad" : traduction NATURELLE en {langue}, au registre de l'original (crie, chuchote, familier...), fidele,
  sans rien ajouter ; en MAJUSCULES si l'original est en majuscules. Pour une onomatopee ou une bulle vide :
  "trad" = "". Jamais de markdown, jamais d'asterisques, jamais de guillemets autour de la traduction.
ENSUITE, regarde la PAGE ENTIERE : liste dans "hors_zones" chaque texte lisible qui N'EST DANS AUCUNE des bulles
numerotees (encadre ou cartouche de narration, pensee, texte vertical, cri ecrit, panneau). PAS les onomatopees
dessinees (effets sonores integres au dessin). Pour chacun : "texte", "type" ("dialogue" | "narration"), "trad"
(memes regles), et "box" = [ymin, xmin, ymax, xmax] du texte en milliemes de la page (0-1000), au plus juste.
Rien hors des bulles : "hors_zones" = [].
Reponds UNIQUEMENT en JSON : {{"bulles":[{{"id":1,"texte":"...","type":"dialogue","trad":"..."}}],
"hors_zones":[{{"texte":"...","type":"narration","trad":"...","box":[0,0,0,0]}}]}}
avec EXACTEMENT les numeros recus pour les bulles."""


def jpeg_b64(im, largeur=None):
    from PIL import Image
    if largeur and im.width > largeur:
        im = im.resize((largeur, int(im.height * largeur / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.convert("RGB").save(buf, "JPEG", quality=88)
    return base64.b64encode(buf.getvalue()).decode()


def decoupe(im, t, marge=0.12, mini=220):
    """La bulle avec une marge, agrandie a `mini` px de haut au moins (lisibilite du petit texte)."""
    from PIL import Image
    W, H = im.size
    x1 = max(0, int((t["x"] - marge * t["w"]) * W)); y1 = max(0, int((t["y"] - marge * t["h"]) * H))
    x2 = min(W, int((t["x"] + t["w"] * (1 + marge)) * W)); y2 = min(H, int((t["y"] + t["h"] * (1 + marge)) * H))
    c = im.crop((x1, y1, max(x2, x1 + 2), max(y2, y1 + 2)))
    if c.height < mini:
        k = mini / c.height
        c = c.resize((max(1, int(c.width * k)), mini), Image.LANCZOS)
    return c


def traduire_page(im, texts, engine, langue, stats):
    path, model = nc.ENGINES[engine]
    content = [{"type": "text", "text": "PAGE ENTIERE (contexte) :"},
               {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + jpeg_b64(im, 1000)}}]
    for t in texts:
        content.append({"type": "text", "text": "BULLE %d" % t["id"]})
        content.append({"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + jpeg_b64(decoupe(im, t))}})
    sysp = SYS.format(langue=LANGUES.get(langue, langue))
    for essai, budget in enumerate((6000, 12000, 24000)):     # budget double si un modele raisonneur vide tout
        texte, u = nc.appel_vision(engine, sysp, content, budget)
        stats["tokens_in"] += u.get("prompt_tokens", 0); stats["tokens_out"] += u.get("completion_tokens", 0)
        stats["cout"] += nc.cout(model, u)
        try:
            j = nc.parse_json(texte)
            HORS_ZONES[:] = [h for h in (j.get("hors_zones") or []) if isinstance(h, dict)]      # v1.94.0
            return {int(b["id"]): b for b in j.get("bulles") or [] if str(b.get("id", "")).isdigit()}
        except Exception as e:
            nc.log("  JSON illisible (%s), nouvel essai" % e)
    raise RuntimeError("traduction illisible apres 3 essais")


# v1.94.0 (T2, remontee Video Studio 23/09) : encadres a texte vertical, cartouches et cris que YOLO ne detecte pas
# restaient en chinois (ch.2 p.10, ch.5 p.2/3/14...). Gemini voit deja la page entiere : il rend aussi ces textes-la,
# avec une boite approximative ; ils deviennent des zones de COMPLEMENT (memes garde-fous : 2 lettres au moins,
# traduction qui tient, aucun chevauchement avec une bulle detectee).
HORS_ZONES = []


def zones_hors(hors, texts, marge=0.08):
    """Les textes « hors zones » de Gemini -> zones (x, y, w, h en fractions), sans celles qui touchent une zone detectee."""
    out, prochain = [], max([t["id"] for t in texts] or [0]) + 100
    for h in hors:
        b = h.get("box") or []
        if len(b) != 4 or not all(isinstance(v, (int, float)) for v in b) or not (h.get("trad") or "").strip():
            continue
        if (h.get("type") or "") not in ("dialogue", "narration"):
            continue
        y1, x1, y2, x2 = (max(0.0, min(1.0, v / 1000.0)) for v in b)
        if x2 - x1 < 0.01 or y2 - y1 < 0.01:
            continue
        mx, my = marge * (x2 - x1), marge * (y2 - y1)
        z = {"id": prochain, "x": max(0.0, x1 - mx), "y": max(0.0, y1 - my), "w": min(1.0, x2 + mx) - max(0.0, x1 - mx),
             "h": min(1.0, y2 + my) - max(0.0, y1 - my), "complement": True, "hors_zone": True, "conf": None, "_h": h}
        if any(min(z["x"] + z["w"], t["x"] + t["w"]) > max(z["x"], t["x"]) and min(z["y"] + z["h"], t["y"] + t["h"]) > max(z["y"], t["y"])
               for t in texts + out):
            continue
        out.append(z); prochain += 1
    return out


def blanchiment(im, rendu, texts):
    """% de la page BLANCHIE par l'effacement : pixels non blancs devenus blancs, hors boites de texte (v1.96.0)."""
    import numpy as np
    A = np.array(im.convert("L")); B = np.array(rendu.convert("L")); H, W = A.shape
    m = (B >= 250) & (A < 250)
    for t in texts:
        m[int(t["y"] * H):int((t["y"] + t["h"]) * H) + 1, int(t["x"] * W):int((t["x"] + t["w"]) * W) + 1] = False
    return 100.0 * float(m.mean())


def nettoyer(im, texts, stats=None):
    """Effacement v1.96.0 : comme avant ; si la page est anormalement blanchie (> SEUIL_BLANCHI), refait en prudent."""
    r, net = ip.clean_bubbles(im, texts, couverture_min=COUVERTURE_MIN, trous_dans_texte=True, boite_max=BOITE_MAX)
    b = blanchiment(im, r, texts)
    if b > SEUIL_BLANCHI:
        r, net = ip.clean_bubbles(im, texts, ratio_max=RATIO_FOND, couverture_min=COUVERTURE_MIN, trous_dans_texte=True, boite_max=BOITE_MAX)
        if stats is not None:
            stats["pages_prudentes"] = stats.get("pages_prudentes", 0) + 1
        nc.log("  effacement prudent : %.0f %% de la page aurait ete blanchie" % b)
    return r, net


def effacer_local(im, a_poser, etats, stats):
    """v1.98.0 : vraies bulles videes comme avant ; tout le reste (boite entiere, fond de case, zone trop grande, non
    effacee) -> lettres trouvees par comic-text-detector puis dessin reconstitue par LaMa. Une zone ou aucune lettre
    n'est trouvee garde l'effacement d'avant. -> (rendu, {id: boite reelle des lettres})."""
    import numpy as np
    from PIL import Image
    W, H = im.size
    # v1.98.0 (banc OPM ch.3, 3 essais) : le detecteur voit AUSSI les onomatopees DESSINEES -- applique a tout le texte
    # hors bulle, il en abimait (p.9 « ズゴゴゴ ») et gonflait des zones deja correctes. Variante PRUDENTE retenue : le
    # local ne traite QUE les zones que le mode standard laisse en VO (cris, legendes geantes) ; le reste = inchange.
    def laissee_en_vo(t):
        e = etats.get(t["id"]) or ""
        return e == "trop grande -> non effacee" or (t.get("complement") and e != "bulle"
                                                      and t["w"] * t["h"] > COMPLEMENT_BOITE_MAX)
    dessin = [t for t, _ in a_poser if laissee_en_vo(t)]
    locaux, m = {}, None
    if dessin:
        proba = el.proba_lettres(im)
        m = np.zeros((H, W), np.uint8)
        for t in dessin:
            mz, reel = el.zone_lettres(proba, t, W, H)
            if mz is not None:
                m |= mz
                locaux[t["id"]] = reel
    # deux zones de lettres qui se chevauchent : chacune reprend SA boite pour la pose (sinon textes superposes)
    ids = list(locaux)
    for i, a_ in enumerate(ids):
        for b_ in ids[i + 1:]:
            if el.chevauche(locaux[a_], locaux[b_]):
                for k in (a_, b_):
                    t = next(t for t, _ in a_poser if t["id"] == k)
                    locaux[k] = {c: t[c] for c in ("x", "y", "w", "h")}
    garde = [dict(t) for t, _ in a_poser if t["id"] not in locaux]           # bulles + zones sans lettres trouvees
    rendu, _ = ip.clean_bubbles(im, garde, couverture_min=COUVERTURE_MIN, trous_dans_texte=True, boite_max=BOITE_MAX)
    for t, _ in a_poser:                                                      # « clean » (boite videe) pour la pose
        g = next((x for x in garde if x.get("id") == t["id"]), None)
        if g is not None and g.get("clean"):
            t["clean"] = g["clean"]
    if locaux:
        t0 = time.time()
        rendu = Image.fromarray(el.reconstituer(np.array(rendu.convert("RGB")), m))
        stats["local_s"] = round(stats.get("local_s", 0) + time.time() - t0, 1)
    return rendu, locaux


def sans_chevauchement(texts, seuil=0.3):
    """Deux zones de texte qui se chevauchent (> 30 % de la plus petite) : on garde la plus PETITE. Page 9 de
    Claymore (22/09) : une 2e zone detectee sur une bulle a recu la meme replique, posee en travers de la page."""
    garde = []
    for t in sorted(texts, key=lambda q: q["w"] * q["h"]):     # la PLUS PETITE d'abord : c'est la vraie bulle
        ok = True
        for g in garde:
            ix = max(0, min(t["x"] + t["w"], g["x"] + g["w"]) - max(t["x"], g["x"]))
            iy = max(0, min(t["y"] + t["h"], g["y"] + g["h"]) - max(t["y"], g["y"]))
            if ix * iy > seuil * min(t["w"] * t["h"], g["w"] * g["h"]):
                ok = False; break
        if ok:
            garde.append(t)
    return sorted(garde, key=lambda q: q["id"])


CONF_COMPLEMENT = 0.10


def zones_texte(im, conf, conf_complement=CONF_COMPLEMENT):
    """v1.92.0 : les bulles de la page. 1) celles d'avant, A L'IDENTIQUE : detection >= conf, sans_chevauchement ;
    2) EN PLUS, les zones faibles (conf_complement <= confiance < conf) qui ne touchent AUCUNE zone forte -- jamais a
    leur place (baisser le seuil tout court remplacait des bonnes bulles par un fragment, mesure 23/09)."""
    bas = min(conf, conf_complement) if conf_complement else conf
    _, tous = ip.detect(im, bas)
    fortes = [t for t in tous if t["conf"] >= conf]
    garde = sans_chevauchement(fortes)
    if not conf_complement or conf_complement >= conf:
        return garde

    def touche(t, g, marge=0.15):
        # marge = 15 % de la taille de la zone faible : collee a une bulle forte = un MORCEAU de la meme bulle
        # (Black Jack p.2 : deux traductions superposees dans une seule grande bulle, essai du 23/09)
        mx, my = marge * t["w"], marge * t["h"]
        return (min(t["x"] + t["w"] + mx, g["x"] + g["w"]) > max(t["x"] - mx, g["x"])
                and min(t["y"] + t["h"] + my, g["y"] + g["h"]) > max(t["y"] - my, g["y"]))
    faibles = sans_chevauchement([t for t in tous if t["conf"] < conf and not any(touche(t, g) for g in fortes)])
    for t in faibles:
        t["complement"] = True
    return sorted(garde + faibles, key=lambda q: q["id"])


def nettoie(trad):
    # sauts de ligne -> espace : Pillow refuse de mesurer un texte multiligne (essai 20 pages du 22/09 : plantage)
    # Gemini suit la typo francaise : espace FINE insecable U+202F avant ? ! (absente de Comic Neue = carres)
    t = re.sub(r"[    ]", " ", trad or "")
    t = re.sub(r"\s+", " ", re.sub(r"\*+", "", t)).strip()
    return t.strip('"«» “”')


def poser_texte(im, boite, texte, est_bulle, taille_max=None, dessiner=True):
    """Ecrit `texte` centre dans `boite` (fractions de page), a la plus grande taille qui tient.
    Bulle videe = ellipse -> on vise le rectangle inscrit (~71 %) ; cartouche = rectangle quasi plein."""
    from PIL import ImageDraw, ImageFont
    W, H = im.size
    bx, by, bw, bh = boite["x"] * W, boite["y"] * H, boite["w"] * W, boite["h"] * H
    cx, cy = bx + bw / 2, by + bh / 2
    d = ImageDraw.Draw(im)
    # espace INSECABLE avant ! ? : ; » et apres « : sinon « MASSACRER / ! » (ponctuation seule sur sa ligne)
    texte = re.sub(r" ([!?:;\u00bb])", lambda m: "\u00a0" + m.group(1), texte).replace("\u00ab ", "\u00ab\u00a0")   # "\1" dans une chaine normale = chr(1) : les ? ! devenaient des carres
    mots = [m for m in texte.split(" ") if m]

    def largeur_dispo(y0, y1):
        """Largeur utilisable entre y0 et y1. Bulle = ELLIPSE : plus etroite en haut et en bas -- la traiter
        en rectangle (1er essai du 22/09) ecrivait trop petit ET debordait sur le dessin en bas de bulle."""
        if not est_bulle:
            return bw * 0.92
        ry, rx = bh * 0.47, bw * 0.47
        pire = max(abs(y0 - cy), abs(y1 - cy))
        if pire >= ry:
            return 0
        return 2 * rx * (1 - (pire / ry) ** 2) ** 0.5 * 0.94

    def essaie(taille, cible):
        f = ImageFont.truetype(FONT_BOLD, taille)
        lignes, cur = [], ""
        for m in mots:
            essai = (cur + " " + m).strip()
            if d.textlength(essai.replace(" ", " "), font=f) <= cible or not cur:
                cur = essai
            else:
                lignes.append(cur); cur = m
        if cur:
            lignes.append(cur)
        il = int(taille * 1.12)
        haut = il * len(lignes)
        y = cy - haut / 2
        if haut > bh * (0.86 if est_bulle else 0.94):
            return None
        pos = []
        for l in lignes:
            if d.textlength(l.replace(" ", " "), font=f) > largeur_dispo(y, y + il):
                return None
            pos.append((l, y)); y += il
        return f, pos

    debut = max(12, int(min(bh * 0.30, H * 0.034)))
    if taille_max:
        debut = min(debut, taille_max)
    for taille in range(debut, 7, -1):
        for part in (0.95, 0.85, 0.75, 0.65, 0.55):          # largeur de coupe : de large a etroit
            r = essaie(taille, bw * part * (0.94 if est_bulle else 0.92))
            if r:
                f, pos = r
                for l, y in (pos if dessiner else []):
                    l = l.replace(" ", " ")        # Comic Neue n'a PAS le glyphe U+00A0 (carres a l'ecran)
                    d.text((cx - d.textlength(l, font=f) / 2, y), l, font=f, fill=(0, 0, 0))
                return {"taille": taille, "lignes": len(pos), "tient": True}
    # ne tient pas meme en 8 px : on l'ecrit quand meme (signale), plutot que de laisser une bulle vide
    if not dessiner:
        return {"taille": 8, "lignes": len(mots), "tient": False}
    f = ImageFont.truetype(FONT_BOLD, 8)
    d.multiline_text((bx + 2, by + 2), "\n".join(mots), font=f, fill=(0, 0, 0))
    return {"taille": 8, "lignes": len(mots), "tient": False}


def main():
    global PROGRESS
    ap = argparse.ArgumentParser()
    ap.add_argument("chapitre", help="sous sources/, ex. claymore/ch_1")
    ap.add_argument("--langue", default="fr", help="code langue cible : " + ", ".join(LANGUES))
    ap.add_argument("--engine", choices=["gemini", "kimi"], default="gemini")
    ap.add_argument("--pages", default="", help="plage, ex. 1-20 (defaut : tout)")
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--conf-complement", type=float, default=CONF_COMPLEMENT,
                    help="v1.92.0 : zones faibles ajoutees si elles ne touchent aucune bulle (0 = desactive)")
    ap.add_argument("--sortie", default="", help="v1.98.0 (bancs) : dossier de sortie a la place de traduction/<langue>")
    ap.add_argument("--effacement", choices=["standard", "local"], default="standard",
                    help="v1.98.0 : local = texte sur le dessin efface par masque des lettres + LaMa (carte graphique)")
    ap.add_argument("--rerendu", action="store_true",
                    help="v1.97.0 : refait effacement + pose depuis traduction.json (memes zones, memes textes, 0 appel)")
    a = ap.parse_args()
    if not re.match(r"^[a-z]{2}$", a.langue):
        raise SystemExit("langue invalide")
    nc.SECRET = nc._secret()
    chap = os.path.normpath(os.path.join(nc.SOURCES, a.chapitre))
    if not chap.startswith(nc.SOURCES + os.sep) or not os.path.isfile(os.path.join(chap, "manifest.json")):
        raise SystemExit("chapitre introuvable : " + a.chapitre)
    out = os.path.join(chap, "traduction", a.langue)
    lu = out                                          # --rerendu lit TOUJOURS la traduction de l'app
    if a.sortie:
        out = os.path.abspath(a.sortie)
    os.makedirs(out, exist_ok=True)
    PROGRESS = os.path.join(out, "progress.json")
    man, pages = nc.pages_du_chapitre(chap, a.pages)
    avant = {}
    if a.rerendu:                                  # v1.97.0 : zones et traductions deja payees, deja relues
        if a.pages:
            raise SystemExit("--rerendu refait le chapitre entier (--pages reecrirait traduction.json incomplet)")
        avant = {x["page"]: x for x in json.load(open(os.path.join(lu, "traduction.json"), encoding="utf-8"))["pages"]}
    stats = dict(tokens_in=0, tokens_out=0, cout=0.0, bulles=0, traduites=0, onomatopees=0, vides=0,
                 effacees_bulle=0, effacees_boite=0, non_effacees=0, ne_tient_pas=0, s=0.0)
    res = {"version": VERSION, "chapitre": a.chapitre, "langue": a.langue, "engine": a.engine, "effacement": a.effacement,
           "created_at": datetime.now().isoformat(timespec="seconds"), "pages": []}
    t0 = time.time()
    nc.journal("traduction_start", chapitre=a.chapitre, langue=a.langue, pages=len(pages))
    for n, p in enumerate(pages, 1):
        progres(n - 1, len(pages), cout=round(stats["cout"], 5))       # v1.91.0 : depense cumulee, lue par la pastille des couts
        im = ip.load_page(os.path.join(chap, p["file"]))
        if a.rerendu:
            anc = (avant.get(p["num"]) or {}).get("bulles") or []
            texts = [dict(b["box"], id=b["id"], complement=b.get("complement", False), conf=b.get("conf"),
                          **({"hors_zone": True} if b.get("hors_zone") else {})) for b in anc]
            tr0 = {b["id"]: {"type": b.get("type"), "texte": b.get("texte"), "trad": b.get("trad")} for b in anc}
        else:
            texts = zones_texte(im, a.conf, a.conf_complement)             # v1.92.0 : + complement
        stats["bulles"] += len(texts)
        lignes, rendu = [], im
        if texts:
            HORS_ZONES[:] = []
            try:
                tr = tr0 if a.rerendu else traduire_page(im, texts, a.engine, a.langue, stats)
            except Exception as e:
                nc.log("  page %d : traduction en echec (%s) -> page laissee en VO" % (p["num"], e))
                tr = {}
            hors = [] if a.rerendu else zones_hors(HORS_ZONES, texts)      # v1.94.0 (T2)
            for z in hors:
                tr[z["id"]] = z.pop("_h")
            stats["hors_zones"] = stats.get("hors_zones", 0) + len(hors)
            texts = texts + hors
            a_poser = []
            for t in texts:
                b = tr.get(t["id"]) or {}
                typ, trad = b.get("type") or "?", nettoie(b.get("trad"))
                stats["onomatopees"] += typ == "onomatopee"; stats["vides"] += typ == "vide"
                lig = {"id": t["id"], "box": {k: round(t[k], 4) for k in ("x", "y", "w", "h")},
                       "type": typ, "texte": b.get("texte") or "", "trad": trad}
                if t.get("complement"):                                   # v1.92.0 : tracable (zone faible rattrapee)
                    lig["complement"], lig["conf"] = True, t.get("conf")
                    if t.get("hors_zone"):
                        lig["hors_zone"] = True                           # v1.94.0 : vu par Gemini, pas par YOLO
                    stats["complements"] = stats.get("complements", 0) + 1
                if trad and typ in ("dialogue", "narration", "?"):
                    a_poser.append((t, lig))
                lignes.append(lig)
            # v1.92.0 : une zone de COMPLEMENT (incertaine par nature) n'est posee que si c'est franc :
            # du texte (pas seulement « ... » / « ! ») et une traduction qui TIENT dans la zone effacee (essai a
            # blanc). Essai du 23/09 : les ratés (anglais visible sous le francais, « CADRE » sur un ideogramme)
            # etaient tous « ne tient pas » ou de la ponctuation seule.
            douteux = []
            for t, lig in a_poser:
                # au moins 2 lettres : « ... », « ! », un ideogramme isole, ou le logo « Đ » d'un groupe de scan (lu
                # « D », efface puis remplace par un « D » -- 5 fois sur OPM 297-301, essai du 23/09) sont laisses
                if t.get("complement") and not re.search(r"\w\w", lig["texte"] or ""):
                    douteux.append((t, lig, "moins de 2 lettres"))
            if any(t.get("complement") for t, _ in a_poser):
                essai, net0 = nettoyer(im, [t for t, _ in a_poser])
                e0 = {x.get("id"): x.get("etat") for x in net0}
                for t, lig in a_poser:
                    if not t.get("complement") or any(t is d[0] for d in douteux):
                        continue
                    etat, c = e0.get(t["id"]), t.get("clean")
                    if etat != "bulle" and not (etat and "boite" in etat):
                        continue                                  # non effacee : deja ecartee plus bas
                    if etat != "bulle" and t["w"] * t["h"] > COMPLEMENT_BOITE_MAX and a.effacement != "local":
                        douteux.append((t, lig, "zone trop grande pour une boite entiere")); continue
                    if etat == "bulle" and c and c["w"] * c["h"] > 6 * t["w"] * t["h"]:
                        etat, c = "case", None
                    boite = c if etat == "bulle" and c else lig["box"]
                    if not poser_texte(essai, boite, lig["trad"], etat == "bulle", dessiner=False)["tient"]:
                        douteux.append((t, lig, "ne tiendrait pas"))
            for t, lig, pourquoi in douteux:
                lig["ecarte"] = pourquoi
                stats["complements_ecartes"] = stats.get("complements_ecartes", 0) + 1
            a_poser = [(t, lig) for t, lig in a_poser if not any(t is d[0] for d in douteux)]
            if a_poser:
                rendu, net = nettoyer(im, [t for t, _ in a_poser], stats)
                etats = {s.get("id"): s.get("etat") for s in net}
                locaux = {}                                   # id -> boite reelle des lettres (effacement local)
                if a.effacement == "local":
                    rendu, locaux = effacer_local(im, a_poser, etats, stats)
                a_dessiner = []
                for t, lig in a_poser:
                    etat = etats.get(t["id"])
                    lig["effacement"] = etat
                    if t["id"] in locaux:                     # v1.98.0 : lettres effacees, dessin reconstitue
                        lig["effacement"] = "local (lettres + LaMa)"
                        stats["effacees_local"] = stats.get("effacees_local", 0) + 1
                        a_dessiner.append((locaux[t["id"]], lig, "halo",
                                           poser_texte(rendu, locaux[t["id"]], lig["trad"], False, dessiner=False)["taille"]))
                        continue
                    if etat == "bulle":
                        stats["effacees_bulle"] += 1
                    elif etat and "boite" in etat:
                        stats["effacees_boite"] += 1
                    else:
                        stats["non_effacees"] += 1
                        continue                              # pas d'effacement = on ne pose rien par-dessus
                    c = t.get("clean")
                    # « bulle » effacee 6x plus grande que son texte = le fond blanc d'une CASE, pas une bulle
                    # (page 9 : la replique etait posee au milieu de la case) -> on ecrit dans la zone detectee
                    if etat == "bulle" and c and c["w"] * c["h"] > 6 * t["w"] * t["h"]:
                        etat, c = "case", None
                        lig["effacement"] = "fond de case -> zone detectee"
                    boite = c if etat == "bulle" and c else lig["box"]
                    a_dessiner.append((boite, lig, etat == "bulle",
                                       poser_texte(rendu, boite, lig["trad"], etat == "bulle", dessiner=False)["taille"]))
                # une taille COMMUNE a la page (la mediane des tailles possibles) : sinon chaque bulle a sa propre
                # taille et la page fait amateur ; une bulle trop petite pour la mediane garde la sienne.
                tailles = sorted(x[3] for x in a_dessiner)
                commune = tailles[len(tailles) // 2] if tailles else None
                for boite, lig, est_bulle, _ in a_dessiner:
                    if est_bulle == "halo":
                        rendu, r = el.poser_avec_halo(rendu, boite, lig["trad"], commune, poser_texte)
                    else:
                        r = poser_texte(rendu, boite, lig["trad"], est_bulle, taille_max=commune)
                    lig.update(r)
                    stats["traduites"] += 1
                    stats["ne_tient_pas"] += not r["tient"]
        f = "page_%03d.png" % p["num"]
        rendu.save(os.path.join(out, f))
        res["pages"].append({"page": p["num"], "source": p["file"], "file": f, "bulles": lignes})
        nc.log("  page %d : %d bulle(s), %d posee(s)" % (p["num"], len(texts), sum(1 for l in lignes if l.get("tient") is not None)))
    stats["s"] = round(time.time() - t0, 1)
    stats["cout"] = round(stats["cout"], 4)
    res["stats"] = stats
    with open(os.path.join(out, "traduction.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    progres(len(pages), len(pages), fini=True, cout=stats["cout"])
    nc.journal("traduction_done", chapitre=a.chapitre, langue=a.langue, **{k: v for k, v in stats.items()})
    try:
        rel = os.path.relpath(out, nc.SOURCES).replace("\\", "/")
    except ValueError:                                # --sortie sur un autre disque (bancs)
        rel = out
    print(json.dumps({"ok": True, "dir": rel, "stats": stats}, ensure_ascii=False))


if __name__ == "__main__":
    main()
