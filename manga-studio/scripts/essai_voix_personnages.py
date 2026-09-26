# -*- coding: utf-8 -*-
"""ESSAI (hors app, 26/09/2026) -- « une voix par personnage, avec le ton qui convient » (Quang 22h00, idee StoryVoice).
ROADMAP : « Mode Lecture avance » (etape 6). Rien n'est branche a l'app ; rien d'existant n'est modifie.

1. DISTRIBUTION + ATTRIBUTION (1 appel Gemini 3.6 Flash, pages traduites vues en entier) : chaque bulle traduite
   (traduction.json, ordre des id) -> qui parle + le TON de la replique ; chaque personnage -> une voix Gemini TTS
   choisie dans le catalogue (genre, age, caractere) + une FICHE DE JEU (sa facon de parler, stable).
   StoryVoice ne regle que la VOIX par personnage (ton = par chapitre) : ici, voix + fiche + ton PAR REPLIQUE.
2. VOIX : gemini-2.5-flash-tts via le gateway (/api/gcptts, input.prompt = fiche + ton), une piste par replique.
3. VIDEO DE CONTROLE : page traduite, bulle qui parle ENCADREE, bandeau « Personnage : texte ».

Usage : python essai_voix_personnages.py one-punch-man/ch_7 --pages 2-6
Sorties : <chap>/essai_voix/ (distribution.json, repliques/*.mp3, essai.mp4, cout.json)
"""
import argparse, base64, json, os, re, subprocess, sys, time
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import narrate_chapter as nc
import karaoke_mots as km

VERSION = "0.6.0"   # 0.6.0 : un ton VIDE = aucun ton (avant : ignore -> le ton de l'IA revenait, 3e essai de Quang 23h03) ;
#          reglages « tons »: false = aucun ton ; rien a dire = AUCUNE consigne envoyee
#   # 0.5.0 (Quang 22h41) : « lire » (CHAIR DE POULE n'est pas une replique), ton cale sur le STYLE et la
#          TENSION de la scene, reglages.json (voix, caractere, intensite, vitesse, ton/locuteur par replique) lu par l'atelier
#   # 0.4.0 : option --ordre cases (cases.json). ESSAYE sur OPM ch.6 p.5 : PIRE (2 cases detectees sur 3 -> « Hein ? » lu apres
#          « C'est bizarre ») -> defaut = ordre des id, qui y etait juste
#   # 0.3.0 : --vitesse 1.5 (Quang 22h20 : « les voix sont lentes » ; mesure 8,5 car/s contre 14 pour sa narration Charon 1,05)
#   # 0.2.0 : consigne COURTE (0.1.0 : la voix LISAIT la consigne, 10 s pour « Quoi ? ») + controle Whisper
SOURCES = os.environ.get("MANGA_SOURCES_DIR") or os.path.expanduser(r"~\Documents\MangaStudio-donnees\sources")
TTS_MODELE = "gemini-2.5-flash-tts"
# Catalogue Gemini TTS (genre + timbre annonces par Google). Le narrateur reste Charon, la voix des recits.
VOIX = {
    "Puck": "homme, enjoue", "Charon": "homme, pose, informatif", "Fenrir": "homme, excitable",
    "Orus": "homme, ferme", "Enceladus": "homme, souffle", "Iapetus": "homme, clair", "Umbriel": "homme, decontracte",
    "Algieba": "homme, doux", "Algenib": "homme, rocailleux, grave", "Rasalgethi": "homme, informatif",
    "Alnilam": "homme, ferme", "Schedar": "homme, egal", "Achird": "homme, amical", "Zubenelgenubi": "homme, nonchalant",
    "Sadachbia": "homme, vif", "Sadaltager": "homme, savant",
    "Zephyr": "femme, lumineuse", "Kore": "femme, ferme", "Leda": "femme, jeune", "Aoede": "femme, legere",
    "Callirrhoe": "femme, detendue", "Autonoe": "femme, lumineuse", "Despina": "femme, douce", "Erinome": "femme, claire",
    "Laomedeia": "femme, enjouee", "Achernar": "femme, tendre", "Gacrux": "femme, mure", "Pulcherrima": "femme, directe",
    "Vindemiatrix": "femme, bienveillante", "Sulafat": "femme, chaleureuse",
}

SYS = """Tu prepares le DOUBLAGE en francais d'un extrait de manga : chaque replique sera lue par la voix de son personnage.
Tu recois les pages (deja traduites en francais, dans l'ordre de lecture) et, pour chaque page, la liste NUMEROTEE des
bulles (id, type, texte traduit, position x,y,w,h en fractions de la page). Tu recois aussi ce qu'on sait deja des
personnages et des faits de chaque page (analyse precedente) : c'est un indice, l'IMAGE fait foi.

1. Pour CHAQUE bulle, dis QUI la prononce : la queue de la bulle, la case, qui est dessine, le sens de la phrase.
   - « narrateur » pour un encart de recit sans personnage ; si l'encart est le monologue d'un personnage (souvenir
     raconte a la 1re personne), c'est CE personnage.
   - « inconnu » si tu ne peux pas trancher : n'invente pas.
   - Une bulle qui ne contient que des points ou des « !! » : locuteur quand meme, et "muet": true.
   - "lire": false pour tout ce qui N'EST PAS PRONONCE : bruitage, onomatopee, sensation ou effet ecrit sur le dessin
     (« CHAIR DE POULE », « BOUM », « frissons »), texte du decor (panneau, affiche). Une bulle de parole ou de pensee
     et un encart de recit se lisent ("lire": true).
2. D'abord l'AMBIANCE : le style du manga (ex. shonen d'action, comedie, drame) et la tension de CETTE scene.
   Puis, pour chaque replique, le TON en quelques mots de consigne d'acteur, en francais (ex. « menacant, glacial »,
   « murmure, gene », « plat, blase »). Il doit servir l'AMBIANCE : dans une scene tendue ou effrayante, pas de jeu
   comique ni surjoue ; l'exces ne va qu'aux scenes comiques. Base-toi sur le dessin (visage, taille des lettres,
   bulle herissee) ET le sens.
3. Pour chaque personnage qui parle, choisis UNE voix dans ce catalogue (nom exact), selon son genre, son age et son
   caractere ; deux personnages ne partagent pas la meme voix. Le narrateur a la voix Charon (ne la donne a personne).
   Ecris sa FICHE DE JEU : une phrase qui decrit comment il parle d'habitude (debit, energie, registre), pour un acteur.
CATALOGUE : %s

Reponds UNIQUEMENT en JSON :
{"ambiance": "style du manga ; tension de la scene, en une phrase",
 "distribution": [{"nom": "...", "genre": "homme|femme|?", "age": "...", "voix": "...", "fiche": "...", "pourquoi": "..."}],
 "repliques": [{"page": 2, "id": 3, "locuteur": "nom exact de la distribution | narrateur | inconnu", "ton": "...",
                "muet": false, "lire": true, "indice": "ce qui designe le locuteur, en 10 mots max"}]}
"""


def args_():
    a = argparse.ArgumentParser()
    a.add_argument("chap")
    a.add_argument("--pages", default="2-6")
    a.add_argument("--langue", default="fr")
    a.add_argument("--vitesse", type=float, default=1.5,
                   help="speakingRate Gemini TTS (respecte, mesure : 1.0 = 9 car/s, 1.3 = 12,4, 1.6 = 15 ; narration Charon 1,05 = 14)")
    a.add_argument("--ordre", choices=("id", "cases"), default="id")
    a.add_argument("--refaire", action="store_true", help="refait la distribution (sinon reprise du fichier)")
    return a.parse_args()


def ordre_par_cases(chap_dir, p):
    """Range les bulles dans l'ordre des CASES (cases.json, deja dans l'ordre de lecture manga pour la video « case par
    case »), puis dans la case : de haut en bas par bandes, de droite a gauche. Une bulle hors de toute case va a la case
    la plus proche. Sans cases.json : ordre des id (bandes de 1/8 de page, cases ignorees)."""
    try:
        c = json.load(open(os.path.join(chap_dir, "cases.json"), encoding="utf-8"))["pages"][p["file"]]
    except (OSError, KeyError, ValueError):
        return p["_bulles"], False
    W, H, cases = c["W"], c["H"], c["cases"]
    if not cases:
        return p["_bulles"], False

    def case_de(b):
        cx, cy = (b["box"]["x"] + b["box"]["w"] / 2) * W, (b["box"]["y"] + b["box"]["h"] / 2) * H
        for k, (x1, y1, x2, y2) in enumerate(cases):
            if x1 <= cx <= x2 and y1 <= cy <= y2:
                return k
        return min(range(len(cases)), key=lambda k: (max(cases[k][0] - cx, 0, cx - cases[k][2]) ** 2
                                                     + max(cases[k][1] - cy, 0, cy - cases[k][3]) ** 2))
    triees = sorted(p["_bulles"], key=lambda b: (case_de(b), round(b["box"]["y"] * 8), -b["box"]["x"]))
    return triees, [b["id"] for b in triees] != [b["id"] for b in p["_bulles"]]


def plage(s):
    a, _, b = s.partition("-")
    return list(range(int(a), int(b or a) + 1))


def distribuer(chap_dir, pages_t, narr, stats):
    content = []
    persos = narr.get("personnages") or []
    faits = {p["page"]: p.get("faits") for p in narr.get("pages") or []}
    content.append({"type": "text", "text": "PERSONNAGES CONNUS (analyse precedente) : " + json.dumps(
        [{"nom": p.get("nom") or p.get("id"), "qui": p.get("qui")} for p in persos], ensure_ascii=False)})
    for p in pages_t:
        img = os.path.join(chap_dir, "traduction", "fr", p["file"])
        if not os.path.isfile(img):
            img = os.path.join(chap_dir, p["file"])
        b64 = base64.b64encode(nc.page_jpeg(img, 1200)).decode()
        bulles = [{"id": b["id"], "type": b["type"], "texte": b["trad"],
                   "pos": [round(b["box"][k], 3) for k in ("x", "y", "w", "h")]} for b in p["_bulles"]]
        content.append({"type": "text", "text": "=== PAGE %d ===\nFaits (indice) : %s\nBulles : %s" % (
            p["page"], faits.get(p["page"], "?"), json.dumps(bulles, ensure_ascii=False))})
        content.append({"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + b64}})
    cat = "; ".join("%s (%s)" % kv for kv in VOIX.items() if kv[0] != "Charon")
    t0 = time.time()
    txt, usage = nc.appel_vision("gemini", SYS % cat, content, 24000)
    stats["distribution_s"] = round(time.time() - t0, 1)
    stats["cout_distribution"] = round(nc.cout("gemini-3.6-flash", usage), 4)
    return nc.parse_json(txt)


VITESSE = 1.5


def dire(texte, voix, consigne, dest, stats, vitesse=None):
    body = {"input": dict({"text": texte}, **({"prompt": consigne} if consigne else {})),
            "voice": {"languageCode": "fr-FR", "name": voix, "model_name": TTS_MODELE},
            "audioConfig": {"audioEncoding": "MP3", "speakingRate": float(vitesse or VITESSE)}}
    r = nc.post("/api/gcptts/v1/text:synthesize", body, timeout=90)
    open(dest, "wb").write(base64.b64decode(r["audioContent"]))
    stats["tts_car"] = stats.get("tts_car", 0) + len(texte) + len(consigne)
    return nc.duree_mp3(dest) or 1.0


def _norm(s):
    return re.sub(r"[^a-zà-ÿ]", "", s.lower())


def fuite(mp3, texte, stats):
    """La voix a-t-elle dit AUTRE CHOSE que la replique (consigne lue, repetition) ? Mesure : transcription Whisper
    nettement plus longue que le texte. Banc 26/09 : consigne longue = 2 fuites/3 ; « Dis ceci d'un ton X » = 0/6."""
    t = (km.whisper(mp3, "") or {}).get("text", "")
    stats["whisper"] = stats.get("whisper", 0) + 1
    return len(_norm(t)) > len(_norm(texte)) * 1.6 + 6, t.strip()


INTENSITE = {0: "avec beaucoup de retenue", 1: "avec retenue", 2: "", 3: "de façon très expressive"}
INTENSITE_DEFAUT = 1          # Quang 22h22 : « diminuer un peu l'exageration de la comedie »


def consigne(ton, caractere="", intensite=INTENSITE_DEFAUT):
    """Consigne COURTE (une longue est lue a voix haute, mesure 26/09). Caractere = 2-5 mots, jamais une fiche."""
    ton = ", ".join(x for x in ((ton or "").strip(), (caractere or "").strip()) if x)
    inten = INTENSITE.get(int(intensite), "")
    if ton and inten:
        return "Dis ceci d'un ton %s, %s, en français." % (ton, inten)
    if ton:
        return "Dis ceci d'un ton %s, en français." % ton
    if inten:
        return "Dis ceci %s, en français." % inten
    return ""                                   # rien a dire : la voix lit le texte, sans consigne


def reglages(out):
    try:
        return json.load(open(os.path.join(out, "reglages.json"), encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def texte_lu(t):
    """Les CAPITALES de manga (cri) se lisent mieux en casse normale : le ton porte deja le cri."""
    lettres = [c for c in t if c.isalpha()]
    if lettres and sum(c.isupper() for c in lettres) / len(lettres) > 0.8:
        t = t.lower()
        t = re.sub(r"(^|[.!?…]\s+)([a-zà-ÿ])", lambda m: m.group(1) + m.group(2).upper(), t)
    return t.strip()


def image_replique(page_png, box, nom, texte, dest, W=1080, H=1920):
    pg = Image.open(page_png).convert("RGB")
    bande = 360
    k = min(W / pg.width, (H - bande) / pg.height)
    pg = pg.resize((round(pg.width * k), round(pg.height * k)), Image.LANCZOS)
    im = Image.new("RGB", (W, H), (12, 12, 16))
    ox, oy = (W - pg.width) // 2, (H - bande - pg.height) // 2
    im.paste(pg, (ox, oy))
    d = ImageDraw.Draw(im)
    if box:
        x, y, w, h = (box[c] for c in ("x", "y", "w", "h"))
        r = [ox + x * pg.width - 8, oy + y * pg.height - 8, ox + (x + w) * pg.width + 8, oy + (y + h) * pg.height + 8]
        d.rounded_rectangle(r, 14, outline=(255, 200, 40), width=7)
    try:
        f1 = ImageFont.truetype("arialbd.ttf", 46); f2 = ImageFont.truetype("arial.ttf", 40)
    except OSError:
        f1 = f2 = ImageFont.load_default()
    y0 = H - bande + 30
    d.text((48, y0), nom, font=f1, fill=(255, 200, 40))
    lignes, cour = [], ""
    for m in texte.split():
        if d.textlength(cour + " " + m, font=f2) > W - 96:
            lignes.append(cour); cour = m
        else:
            cour = (cour + " " + m).strip()
    lignes.append(cour)
    for i, l in enumerate(lignes[:4]):
        d.text((48, y0 + 70 + i * 52), l, font=f2, fill=(235, 235, 240))
    im.save(dest)


def main():
    nc._sorties_utf8()
    a = args_()
    global VITESSE
    VITESSE = a.vitesse
    nc.SECRET = nc._secret()
    chap_dir = os.path.join(SOURCES, a.chap.replace("/", os.sep))
    out = os.path.join(chap_dir, "essai_voix")
    os.makedirs(os.path.join(out, "repliques"), exist_ok=True)
    os.makedirs(os.path.join(out, "images"), exist_ok=True)
    t = json.load(open(os.path.join(chap_dir, "traduction", a.langue, "traduction.json"), encoding="utf-8"))
    narr_d = os.path.join(chap_dir, "narration")
    tags = sorted(os.listdir(narr_d)) if os.path.isdir(narr_d) else []
    narr = json.load(open(os.path.join(narr_d, tags[0], "narration.json"), encoding="utf-8")) if tags else {}
    voulues = set(plage(a.pages))
    pages_t = []
    for p in t["pages"]:
        if p["page"] in voulues:
            p["_bulles"] = sorted([b for b in p["bulles"] if b["type"] in ("dialogue", "narration")
                                   and not b.get("ecarte") and (b.get("trad") or "").strip()], key=lambda b: b["id"])
            p["_bulles"], change = ordre_par_cases(chap_dir, p) if a.ordre == "cases" else (p["_bulles"], False)
            if change:
                print("  p%d : ordre par cases %s (ordre des id : %s)" % (p["page"], [b["id"] for b in p["_bulles"]],
                                                                        sorted(b["id"] for b in p["_bulles"])))
            pages_t.append(p)
    stats = {"version": VERSION, "chap": a.chap, "pages": a.pages, "tts": TTS_MODELE, "vitesse": VITESSE}
    fdist = os.path.join(out, "distribution.json")
    if a.refaire or not os.path.isfile(fdist):
        print("1. distribution + attribution (%d pages, %d bulles)..." % (len(pages_t), sum(len(p["_bulles"]) for p in pages_t)))
        dist = distribuer(chap_dir, pages_t, narr, stats)
        json.dump(dist, open(fdist, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    else:
        dist = json.load(open(fdist, encoding="utf-8"))
    reg = reglages(out)
    if reg.get("vitesse"):
        VITESSE = float(reg["vitesse"])
    casting = {c["nom"]: c for c in dist["distribution"]}
    for nom, o in (reg.get("persos") or {}).items():          # reglages de Quang (atelier) > choix de l'IA
        casting.setdefault(nom, {"nom": nom}).update({k: v for k, v in o.items() if v not in (None, "")})
    casting.setdefault("narrateur", {"nom": "narrateur", "voix": "Charon", "fiche": "Narrateur de recap manga, pose et clair."})
    for c in dist["distribution"]:
        if c.get("voix") not in VOIX:
            print("  voix hors catalogue pour %s : %s -> Schedar" % (c["nom"], c.get("voix"))); c["voix"] = "Schedar"
        print("  %-14s %-6s %-12s %s" % (c["nom"], c.get("genre", ""), c["voix"], c.get("fiche", "")))
    print("  ambiance :", dist.get("ambiance"))
    rep = {(r["page"], r["id"]): r for r in dist["repliques"]}
    print("2. voix + 3. images...")
    plan, n = [], 0
    for p in pages_t:
        png = os.path.join(chap_dir, "traduction", a.langue, p["file"])
        for b in p["_bulles"]:
            r = dict(rep.get((p["page"], b["id"])) or {"locuteur": "inconnu", "ton": "neutre"})
            r.update({k: v for k, v in ((reg.get("repliques") or {}).get("%d-%d" % (p["page"], b["id"])) or {}).items()
                      if v is not None and (v != "" or k == "ton")})      # 0.6.0 : ton "" = efface par Quang
            if reg.get("tons") is False:
                r["ton"] = ""
            if r.get("lire") is False:
                print("  -- p%d b%-3d NON LUE (%s)" % (p["page"], b["id"], b["trad"][:40])); continue
            qui = r.get("locuteur") or "inconnu"
            c = casting.get(qui) or {"voix": "Schedar", "fiche": "Voix neutre."}
            n += 1
            nom_f = "r%03d_p%d_b%d" % (n, p["page"], b["id"])
            mp3, img = os.path.join(out, "repliques", nom_f + ".mp3"), os.path.join(out, "images", nom_f + ".png")
            texte = texte_lu(b["trad"])
            muet = r.get("muet") or not re.search(r"\w", texte)
            cons = None
            if muet:
                duree = 1.2
                subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                                "-t", str(duree), mp3], check=True)
            else:
                # 0.2.0 : la fiche de jeu N'EST PAS envoyee a la voix (elle la lisait) -- elle sert au choix du timbre et
                # au ton ecrit replique par replique, qui la porte deja (« plat, blase » pour Saitama)
                cons = consigne(r.get("ton"), c.get("caractere", ""), c.get("intensite", INTENSITE_DEFAUT))
                duree = dire(texte, c["voix"], cons, mp3, stats, c.get("vitesse"))
                f_, t_ = fuite(mp3, texte, stats)
                if f_:
                    print("    fuite (%s) -> refaite" % t_[:60]); stats["refaites"] = stats.get("refaites", 0) + 1
                    duree = dire(texte, c["voix"], cons, mp3, stats, c.get("vitesse"))
                    f_, t_ = fuite(mp3, texte, stats)
                    if f_:
                        stats["fuites_restantes"] = stats.get("fuites_restantes", 0) + 1; print("    FUITE RESTANTE : " + t_[:80])
            affiche = c.get("renomme") or qui                     # atelier : « p1 » -> « Fille-Moustique »
            image_replique(png, b["box"], ("%s  (%s)" % (affiche, r.get("ton", ""))) if not muet else affiche, b["trad"], img)
            plan.append({"n": n, "page": p["page"], "id": b["id"], "locuteur": qui, "voix": c["voix"], "ton": r.get("ton"),
                         "texte": b["trad"], "indice": r.get("indice"), "consigne": cons, "duree": duree, "mp3": mp3, "img": img})
            print("  %2d p%d b%-3d %-12s %-10s %-24s %s" % (n, p["page"], b["id"], qui[:12], c["voix"], (r.get("ton") or "")[:24], b["trad"][:50]))
    # montage : chaque replique = son image pendant sa voix + 0,35 s de respiration
    lst = os.path.join(out, "montage.txt")
    with open(lst, "w", encoding="utf-8") as f:
        for x in plan:
            f.write("file '%s'\n" % x["mp3"].replace("\\", "/"))
    wav = os.path.join(out, "voix.m4a")
    seg = []
    for x in plan:
        s = x["mp3"][:-4] + "_pad.m4a"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", x["mp3"], "-af", "apad=pad_dur=0.35", "-ar", "24000", "-ac", "1",
                        "-c:a", "aac", s], check=True)
        x["duree_totale"] = nc.duree_mp3(s) or (x["duree"] + 0.35)
        seg.append(s)
    with open(lst, "w", encoding="utf-8") as f:
        for s in seg:
            f.write("file '%s'\n" % s.replace("\\", "/"))
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", wav], check=True)
    ilst = os.path.join(out, "images.txt")
    with open(ilst, "w", encoding="utf-8") as f:
        for x in plan:
            f.write("file '%s'\nduration %.3f\n" % (x["img"].replace("\\", "/"), x["duree_totale"]))
        f.write("file '%s'\n" % plan[-1]["img"].replace("\\", "/"))
    mp4 = os.path.join(out, "essai.mp4")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", ilst, "-i", wav,
                    "-vf", "fps=25,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                    "-c:a", "aac", "-shortest", mp4], check=True)
    # Gemini 2.5 Flash TTS : 0,50 $/M jetons texte + 10 $/M jetons audio (25 jetons/s) -> l'audio domine
    audio_s = sum(x["duree"] for x in plan)
    stats.update(repliques=len(plan), audio_s=round(audio_s, 1), cout_voix=round(audio_s * 25 * 10 / 1e6 + stats.get("tts_car", 0) / 4 * 0.5 / 1e6, 4))
    stats["cout_total"] = round(stats.get("cout_distribution", 0) + stats["cout_voix"], 4)
    json.dump({"stats": stats, "plan": plan}, open(os.path.join(out, "cout.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("OK", mp4, json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    main()
