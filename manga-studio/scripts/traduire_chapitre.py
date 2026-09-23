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

VERSION = "1.93.0"
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
Reponds UNIQUEMENT en JSON : {{"bulles":[{{"id":1,"texte":"...","type":"dialogue","trad":"..."}}]}}
avec EXACTEMENT les numeros recus."""


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
            return {int(b["id"]): b for b in nc.parse_json(texte).get("bulles") or [] if str(b.get("id", "")).isdigit()}
        except Exception as e:
            nc.log("  JSON illisible (%s), nouvel essai" % e)
    raise RuntimeError("traduction illisible apres 3 essais")


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
    a = ap.parse_args()
    if not re.match(r"^[a-z]{2}$", a.langue):
        raise SystemExit("langue invalide")
    nc.SECRET = nc._secret()
    chap = os.path.normpath(os.path.join(nc.SOURCES, a.chapitre))
    if not chap.startswith(nc.SOURCES + os.sep) or not os.path.isfile(os.path.join(chap, "manifest.json")):
        raise SystemExit("chapitre introuvable : " + a.chapitre)
    out = os.path.join(chap, "traduction", a.langue)
    os.makedirs(out, exist_ok=True)
    PROGRESS = os.path.join(out, "progress.json")
    man, pages = nc.pages_du_chapitre(chap, a.pages)
    stats = dict(tokens_in=0, tokens_out=0, cout=0.0, bulles=0, traduites=0, onomatopees=0, vides=0,
                 effacees_bulle=0, effacees_boite=0, non_effacees=0, ne_tient_pas=0, s=0.0)
    res = {"version": VERSION, "chapitre": a.chapitre, "langue": a.langue, "engine": a.engine,
           "created_at": datetime.now().isoformat(timespec="seconds"), "pages": []}
    t0 = time.time()
    nc.journal("traduction_start", chapitre=a.chapitre, langue=a.langue, pages=len(pages))
    for n, p in enumerate(pages, 1):
        progres(n - 1, len(pages), cout=round(stats["cout"], 5))       # v1.91.0 : depense cumulee, lue par la pastille des couts
        im = ip.load_page(os.path.join(chap, p["file"]))
        texts = zones_texte(im, a.conf, a.conf_complement)                 # v1.92.0 : + complement
        stats["bulles"] += len(texts)
        lignes, rendu = [], im
        if texts:
            try:
                tr = traduire_page(im, texts, a.engine, a.langue, stats)
            except Exception as e:
                nc.log("  page %d : traduction en echec (%s) -> page laissee en VO" % (p["num"], e))
                tr = {}
            a_poser = []
            for t in texts:
                b = tr.get(t["id"]) or {}
                typ, trad = b.get("type") or "?", nettoie(b.get("trad"))
                stats["onomatopees"] += typ == "onomatopee"; stats["vides"] += typ == "vide"
                lig = {"id": t["id"], "box": {k: round(t[k], 4) for k in ("x", "y", "w", "h")},
                       "type": typ, "texte": b.get("texte") or "", "trad": trad}
                if t.get("complement"):                                   # v1.92.0 : tracable (zone faible rattrapee)
                    lig["complement"], lig["conf"] = True, t.get("conf")
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
                essai, net0 = ip.clean_bubbles(im, [t for t, _ in a_poser], ratio_max=RATIO_FOND)
                e0 = {x.get("id"): x.get("etat") for x in net0}
                for t, lig in a_poser:
                    if not t.get("complement") or any(t is d[0] for d in douteux):
                        continue
                    etat, c = e0.get(t["id"]), t.get("clean")
                    if etat != "bulle" and not (etat and "boite" in etat):
                        continue                                  # non effacee : deja ecartee plus bas
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
                rendu, net = ip.clean_bubbles(im, [t for t, _ in a_poser], ratio_max=RATIO_FOND)
                etats = {s.get("id"): s.get("etat") for s in net}
                a_dessiner = []
                for t, lig in a_poser:
                    etat = etats.get(t["id"])
                    lig["effacement"] = etat
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
    print(json.dumps({"ok": True, "dir": os.path.relpath(out, nc.SOURCES).replace("\\", "/"), "stats": stats}, ensure_ascii=False))


if __name__ == "__main__":
    main()
