# -*- coding: utf-8 -*-
"""Video d'un chapitre narre, EXACTEMENT comme le lecteur de l'app (Manga Studio v1.93.0, 22/09/2026, etape 5).

Quang : « la video doit refleter exactement ce qui est affiche aujourd'hui avec les parametrages ». Donc on rejoue
le lecteur (montrerPage / musTick / karTick de manga_studio.html) au lieu d'inventer :
- une page reste le temps de SA voix a la vitesse choisie + 0,45 s (page muette : 2,5 s) ;
- zoom lent : kb (1 -> 1,07, monte de 1,5 %) / kb2 (l'inverse) une page sur deux, duree max(4, dur/vitesse + 1) s,
  ease-out, sur TOUTE la scene (marges comprises, comme le CSS) ;
- sous-titres : texte de la page, ou karaoke (mot en cours jaune #ffd700, mots dits clairs, suite attenuee) ;
- musique : morceaux coches, ordre aleatoire (graine gardee), fondu enchaine 3 s, gain = volume x 0,4, -7 dB sous la
  voix, baisse en 0,3 s / remonte en ~2,5 s (meme pas de 100 ms que musTick).
Format 9:16 (1080 x 1920) : titre en haut, scene, bandeau de sous-titres en bas. Encodage NVENC, 0 $.

Usage : python video_chapitre.py <serie/ch_N> <tag> --reglages '<json>' [--pages 1-3] [--sortie x.mp4]
reglages = {vitesse, sous, karaoke, musique, volume, musique_noms: [...], pages: "" | "fr", graine, precedemment, camera}
v1.96.0 (23/09) : camera = "page" (le zoom lent historique) | "cases" (defaut, decision Quang : la camera parcourt les
cases -- regle dans cases_video.py, que le lecteur de l'app rejoue a l'identique). Absent = "page" (videos d'avant).
Ecrit sources/<chap>/video/<tag>.mp4 + <tag>.json (reglages, empreinte, duree) ; progression dans <tag>.progress.json.
"""
import argparse, hashlib, json, os, random, shutil, subprocess, sys, tempfile, time
# numpy n'est importe QUE pour fabriquer (pcm, mixer) : le proxy importe ce module pour empreinte() sans en dependre

VERSION = "1.98.0"
# v1.97.0 (23/09) : VERSION DU RENDU. A monter A LA MAIN, et seulement pour une vraie amelioration visible du moteur
# (pas pour une retouche) : toutes les videos plus anciennes passent alors « a refaire : le moteur video a ete
# ameliore », et « Tout traiter » / « perimees » les reprennent. Quang 23/09 : « tout regenerer lors de mises a jour
# de ce genre » -- sans bouton de plus. Tant que RENDU vaut 1, rien ne change (cle absente de l'empreinte).
RENDU = 1
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, "..", "sources"))
W, H, FPS, SR = 1080, 1920, 30, 44100
HAUT_TITRE, HAUT_SOUS = 96, 360                   # bandeau titre / bandeau sous-titres ; la scene prend le reste
SCENE_H = H - HAUT_TITRE - HAUT_SOUS
FOND = "0x050608"
GAP, MUETTE = 0.45, 2.5                           # montrerPage : 450 ms apres la voix ; page muette 2,5 s
GAIN_MAX, DUCK, FONDU = 0.4, 0.45, 3.0            # musTick / musEnveloppe
NOW = lambda: time.time()
CREATE = getattr(subprocess, "CREATE_NO_WINDOW", 0)
PROG = None


def progres(etape, fait, total, **kw):
    if PROG:
        json.dump(dict(etape=etape, fait=fait, total=total, t=NOW(), pid=os.getpid(), **kw),
                  open(PROG, "w", encoding="utf-8"), ensure_ascii=False)


def ff(args, **kw):
    r = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + args, capture_output=True, text=True,
                       creationflags=CREATE, **kw)
    if r.returncode:
        raise RuntimeError("ffmpeg : " + (r.stderr or "")[-600:])


def pcm(path, tempo=1.0):
    import numpy as np
    """Decode en float32 stereo 44,1 kHz (atempo = vitesse sans changer la hauteur, comme playbackRate)."""
    af = ["-af", "atempo=%.4f" % tempo] if abs(tempo - 1) > 1e-3 else []
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", path] + af +
                       ["-f", "f32le", "-ac", "2", "-ar", str(SR), "-"], capture_output=True, creationflags=CREATE)
    if r.returncode:
        raise RuntimeError("decodage %s : %s" % (path, r.stderr[-300:]))
    return np.frombuffer(r.stdout, dtype=np.float32).reshape(-1, 2)


# ---------------------------------------------------------------- donnees du chapitre
def charger(chap, tag, reglages, plage=None):
    cd = os.path.join(SRC, chap)
    nd = os.path.join(cd, "narration", tag)
    n = json.load(open(os.path.join(nd, "narration.json"), encoding="utf-8"))
    man = json.load(open(os.path.join(cd, "manifest.json"), encoding="utf-8"))
    presentes = {p["file"] for p in man.get("pages") or []}
    pages = [p for p in n["pages"] if (p.get("type") == "histoire" or p.get("audio")) and p.get("file") in presentes]
    if plage:
        a, b = (int(x) for x in (plage.split("-") + [plage])[:2])
        pages = [p for p in pages if a <= int(p["page"]) <= b]
    trad = {}
    lg = reglages.get("pages") or ""
    if lg:
        tj = os.path.join(cd, "traduction", lg, "traduction.json")
        if os.path.isfile(tj):
            trad = {x["source"]: os.path.join(cd, "traduction", lg, x["file"]) for x in json.load(open(tj, encoding="utf-8")).get("pages") or []}
    # v1.95.0 : « Precedemment... » en tete, comme le lecteur quand la case 📜 est cochee (decision Quang 22/09)
    oj = os.path.join(cd, "precedemment", "ouverture.json")
    pre = []
    if reglages.get("precedemment") and not plage and os.path.isfile(oj):
        for x in json.load(open(oj, encoding="utf-8")).get("items") or []:
            if x.get("audio") and os.path.isfile(os.path.join(cd, "precedemment", x["audio"])):
                pre.append({"page": "résumé", "type": "histoire", "narration": x.get("narration"), "audio": x["audio"],
                            "dur": x.get("dur"), "_prec": True, "_src_img": os.path.join(SRC, x["img"]) if x.get("img") else None,
                            "_src_audio": os.path.join(cd, "precedemment", x["audio"])})
    pages = [p for p in pre if p["_src_img"] and os.path.isfile(p["_src_img"])] + pages
    v = float(reglages.get("vitesse") or 1)
    t = 0.0
    for i, p in enumerate(pages):
        if p.get("_prec"):
            p["_img"], p["_audio"] = p["_src_img"], p["_src_audio"]
        else:
            p["_img"] = trad.get(p["file"]) or os.path.join(cd, p["file"])
            p["_audio"] = os.path.join(nd, p["audio"]) if p.get("audio") else None
        p["_voix"] = (p.get("dur") or 3) / v if p["_audio"] else 0.0
        p["_duree"] = p["_voix"] + GAP if p["_audio"] else MUETTE
        p["_anim"] = max(4.0, (p.get("dur") or 3) / v + 1)      # --kb du lecteur
        p["_kb2"] = i % 2 == 1
        p["_t0"] = t
        t += p["_duree"]
    return n, man, pages, t


def empreinte(chap, tag, reglages):
    """Tout ce qui fabrique la video, par poste : si un poste change, la video est « a refaire » (et on sait POURQUOI)."""
    cd = os.path.join(SRC, chap)
    nd = os.path.join(cd, "narration", tag)
    h = lambda o: hashlib.sha1(json.dumps(o, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
    st = lambda f: [os.path.basename(f), os.path.getsize(f), int(os.path.getmtime(f))] if os.path.isfile(f) else [os.path.basename(f), None]
    n = json.load(open(os.path.join(nd, "narration.json"), encoding="utf-8"))
    man = json.load(open(os.path.join(cd, "manifest.json"), encoding="utf-8"))
    lg = reglages.get("pages") or ""
    tj = os.path.join(cd, "traduction", lg, "traduction.json") if lg else ""
    md = os.path.join(SRC, chap.split("/")[0], "musique")
    mus = []
    for nom in reglages.get("musique_noms") or []:
        f = [x for x in (os.listdir(md) if os.path.isdir(md) else []) if os.path.splitext(x)[0] == nom]
        mus.append(st(os.path.join(md, f[0])) if f else [nom, None])
    out = {
        "narration": h([(p.get("page"), p.get("file"), p.get("narration"), p.get("audio"), p.get("dur")) for p in n["pages"]]),
        "karaoke": h([p.get("mots") for p in n["pages"]]),
        "voix": h([st(os.path.join(nd, p["audio"])) for p in n["pages"] if p.get("audio")]),
        "pages": h([(p["file"], st(os.path.join(cd, p["file"]))) for p in man.get("pages") or []]),
        "traduction": h(st(tj)) if tj else "",
        "musique": h(mus),
        "reglages": h({k: reglages.get(k) for k in ("vitesse", "sous", "karaoke", "musique", "volume", "musique_noms", "pages")}),
    }
    if RENDU > 1:                             # v1.97.0 : une video d'un rendu plus ancien n'a pas cette valeur
        out["moteur"] = RENDU
    if camera(reglages) != "page":            # v1.96.0 : comme precedemment -> une video « page » d'avant garde son empreinte
        out["reglages"] = h([out["reglages"], camera(reglages)])
    if reglages.get("precedemment"):          # v1.95.0 : SEULEMENT si demande -> les videos d'avant ne passent pas « a refaire »
        # le CONTENU (texte, voix, date de fabrication), pas la date du fichier : une copie a l'identique ne rend
        # pas la video « a refaire » (banc du 22/09 : restaurer ouverture.json suffisait a la faire passer 🟠)
        oj = os.path.join(cd, "precedemment", "ouverture.json")
        try:
            o = json.load(open(oj, encoding="utf-8"))
            out["precedemment"] = h([o.get("created_at"), o.get("voice"), [(x.get("narration"), x.get("audio"), x.get("dur"), x.get("img"))
                                                                          for x in o.get("items") or []]])
        except Exception:
            out["precedemment"] = h(None)
    return out


def camera(reglages):
    return "cases" if reglages.get("camera") == "cases" else "page"


# ---------------------------------------------------------------- image
def preparer_cases(chap, pages):
    """v1.96.0 : le trajet de camera de chaque page (cases_video.plan). Le « Precedemment... » garde le zoom lent."""
    sys.path.insert(0, HERE)
    import cases_video as cv
    c = cv.cases_chapitre(chap, journal=lambda m: print(m, flush=True))
    A = W / float(SCENE_H)
    for p in pages:
        e = (c["pages"] or {}).get(p.get("file")) if not p.get("_prec") else None
        if not e:
            continue
        from PIL import Image
        with Image.open(p["_img"]) as im:
            iw, ih = im.size
        if (iw, ih) != (e["W"], e["H"]):                       # page traduite : meme dessin, autre taille
            sx, sy = iw / float(e["W"]), ih / float(e["H"])
            e = {"W": iw, "H": ih, "cases": [[b[0] * sx, b[1] * sy, b[2] * sx, b[3] * sy] for b in e["cases"]]}
        p["_plan"] = cv.plan(e, c["format"], A, p["_duree"])
        p["_format"] = c["format"]
    return cv


class Camera:
    """v1.96.0 : les images d'UNE page en mode cases (meme scene que clip_page : 1080 x SCENE_H sous le titre)."""

    def __init__(self, p, cv):
        from PIL import Image
        self.p, self.cv = p, cv
        self.fond = tuple(int(FOND[2:][k:k + 2], 16) for k in (0, 2, 4))
        img = Image.open(p["_img"]).convert("RGB")
        # Echantillonnage BILINEAIRE (2,6x plus rapide que bicubique, mesure 23/09) sur une image agrandie UNE fois en
        # Lanczos (au moins 2x la scene : le gros plan reste net) puis reduite par 2, 4... (pas de moire sur les trames)
        self.s = max(1.0, 2.0 * SCENE_H / img.size[1], 2.0 * W / img.size[0] if img.size[0] > img.size[1] else 0)
        if self.s > 1.0:
            img = img.resize((round(img.size[0] * self.s), round(img.size[1] * self.s)), Image.LANCZOS)
        self.niveaux = [(1, img)]
        while min(self.niveaux[-1][1].size) > 1200:
            f, im = self.niveaux[-1]
            self.niveaux.append((f * 2, im.reduce(2)))
        self.voile_plein = Image.new("RGB", (W, SCENE_H), self.fond)

    def image(self, t):
        from PIL import Image, ImageDraw
        cam, case, a = self.cv.pose(self.p["_plan"], t)
        s = self.s
        f, im = self.niveaux[0]
        for f2, im2 in self.niveaux[1:]:
            if (cam[2] - cam[0]) * s / W >= f2 * 1.2:
                f, im = f2, im2
        scene = im.transform((W, SCENE_H), Image.EXTENT, tuple(x * s / f for x in cam), Image.BILINEAR, fillcolor=self.fond)
        if case is not None and a > 0:
            sx, sy = W / (cam[2] - cam[0]), SCENE_H / (cam[3] - cam[1])
            bx = [round((case[0] - cam[0]) * sx), round((case[1] - cam[1]) * sy),
                  round((case[2] - cam[0]) * sx) - 1, round((case[3] - cam[1]) * sy) - 1]
            m = Image.new("L", (W, SCENE_H), round(255 * self.cv.VOILE * a))
            ImageDraw.Draw(m).rectangle(bx, fill=0)
            scene = Image.composite(self.voile_plein, scene, m)
        return scene


def clip_cases(p, tmp, i, enc, cv, avant=None):
    """v1.96.0 : une page en mode cases, image par image. avant = la page precedente si elle est aussi en mode cases :
    webtoon -> fondu de 0,3 s depuis sa derniere image (comme la demo validee par Quang). Independant des autres
    pages (la derniere image d'avant est recalculee ici) -> les pages se fabriquent en parallele."""
    from PIL import Image
    n = max(1, round(p["_duree"] * FPS))
    cam = Camera(p, cv)
    fin_avant = None
    if avant is not None and p.get("_format") == "webtoon":
        fin_avant = Camera(avant, cv).image((max(1, round(avant["_duree"] * FPS)) - 1) / float(FPS))
    out = os.path.join(tmp, "p%04d.mp4" % i)
    pr = subprocess.Popen(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", "%dx%d" % (W, SCENE_H), "-r", str(FPS), "-i", "-",
                           "-vf", "pad=%d:%d:0:%d:color=%s,format=yuv420p" % (W, H, HAUT_TITRE, FOND), "-frames:v", str(n)]
                          + enc + [out], stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE)
    try:
        for k in range(n):
            t = k / float(FPS)
            scene = cam.image(t)
            if fin_avant is not None and t < 0.3:
                scene = Image.blend(fin_avant, scene, t / 0.3)
            pr.stdin.write(scene.tobytes())
        pr.stdin.close()
    except (BrokenPipeError, OSError):
        pass
    err = pr.stderr.read().decode("utf-8", "replace")
    if pr.wait():
        raise RuntimeError("ffmpeg (cases) : " + err[-600:])
    return out


def clip_page(p, tmp, i, enc):
    """La scene du lecteur : page « contain » sur fond sombre, zoom kb/kb2 sur TOUTE la scene, ease-out."""
    n = max(1, round(p["_duree"] * FPS))
    na = p["_anim"] * FPS
    e = "(1-pow(1-min(on/%.3f,1),2))" % na                    # ease-out
    if p["_kb2"]:
        z, dy = "(1.07-0.07*%s)" % e, "(-0.015*ih*(1-%s))" % e
    else:
        z, dy = "(1+0.07*%s)" % e, "(0.015*ih*%s)" % e
    k = 3                                                     # sur-echantillonnage : pas de tremblement du zoom
    vf = ("scale=%d:%d:force_original_aspect_ratio=decrease:flags=lanczos,pad=%d:%d:(ow-iw)/2:(oh-ih)/2:color=%s,"
          "scale=%d:%d:flags=lanczos,"
          "zoompan=z='%s':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2+%s':d=%d:s=%dx%d:fps=%d,"
          "pad=%d:%d:0:%d:color=%s,format=yuv420p") % (
        W, SCENE_H, W, SCENE_H, FOND, W * k, SCENE_H * k, z, dy, n, W, SCENE_H, FPS, W, H, HAUT_TITRE, FOND)
    out = os.path.join(tmp, "p%04d.mp4" % i)
    ff(["-loop", "1", "-framerate", str(FPS), "-i", p["_img"], "-vf", vf, "-frames:v", str(n)] + enc + [out])
    return out


# ---------------------------------------------------------------- sous-titres (ASS)
def ass_temps(t):
    t = max(0.0, t)
    return "%d:%02d:%02d.%02d" % (t // 3600, t % 3600 // 60, int(t % 60), int(round(t * 100)) % 100)


def ass_txt(s):
    return (s or "").replace("\\", "\\\\").replace("{", "(").replace("}", ")").replace("\n", " ")


def ecrire_ass(path, n, pages, reglages, total):
    kar = bool(reglages.get("karaoke"))
    lignes = ["[Script Info]", "ScriptType: v4.00+", "PlayResX: %d" % W, "PlayResY: %d" % H, "WrapStyle: 0", "",
              "[V4+ Styles]",
              "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
              "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
              "Style: Sous,Arial,46,&H00EDEDED,&H00EDEDED,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,8,48,48,%d,1" % (H - HAUT_SOUS + 22),
              "Style: Titre,Arial,34,&H00BFC4CC,&H00BFC4CC,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,0,0,8,40,40,28,1", "",
              "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    ev = lambda a, b, style, txt: lignes.append("Dialogue: 0,%s,%s,%s,,0,0,0,,%s" % (ass_temps(a), ass_temps(b), style, txt))
    v = float(reglages.get("vitesse") or 1)
    for i, p in enumerate(pages):
        a, b = p["_t0"], p["_t0"] + p["_duree"]
        ev(a, b, "Titre", ass_txt(("Précédemment… (%d/%d)" % (i + 1, len(pages))) if p.get("_prec") else
                                  "%s ch. %s · page %s (%d/%d)" % (n.get("title") or "", n.get("chapter") or "", p["page"], i + 1, len(pages))))
        texte = (p.get("narration") or "").strip()
        if not reglages.get("sous") or not texte:
            continue
        # v1.95.0 : un texte long (le « Precedemment... » fait ~430 caracteres) debordait du bandeau de 360 px en 46 px :
        # la taille baisse avec la longueur (surface ~ fs^2), plancher 30 px
        fs = 46 if len(texte) <= 220 else max(30, int(46 * (220.0 / len(texte)) ** 0.5))
        fz = "" if fs == 46 else "{\\fs%d}" % fs
        if not (kar and p["_audio"]):
            ev(a, b, "Sous", fz + ass_txt(texte))
            continue
        toks = texte.split()
        if isinstance(p.get("mots"), list) and len(p["mots"]) == len(toks):
            deb = [m[0] for m in p["mots"]]
        else:                                                 # repli du lecteur : au prorata de la longueur
            poids = [len(x) + 1 for x in toks]; tot = float(sum(poids)) or 1; c = 0; deb = []
            for w_ in poids:
                deb.append(c / tot * (p.get("dur") or 3)); c += w_
        # karTick : le mot k est « en cours » des que deb[k] <= t + 0.05 (t = temps du MP3) -> temps video = /vitesse
        bornes = [a] + [a + max(0.0, d - 0.05) / v for d in deb[1:]] + [b]
        debut_k0 = a + max(0.0, deb[0] - 0.05) / v
        ev(a, max(a, debut_k0), "Sous", fz + "".join("{\\alpha&H80&}" + ass_txt(x) + " " for x in toks).strip())
        for k in range(len(toks)):
            t1, t2 = max(bornes[k], debut_k0) if k == 0 else bornes[k], bornes[k + 1]
            if t2 <= t1:
                continue
            txt = ""
            for j, x in enumerate(toks):
                if j < k:
                    txt += "{\\alpha&H00&\\c&HEDEDED&}"
                elif j == k:
                    txt += "{\\alpha&H00&\\c&H00D7FF&}"
                else:
                    txt += "{\\alpha&H80&\\c&HEDEDED&}"
                txt += ass_txt(x) + " "
            ev(t1, t2, "Sous", fz + txt.strip())
    open(path, "w", encoding="utf-8").write("\n".join(lignes) + "\n")


# ---------------------------------------------------------------- son
def mixer(pages, reglages, total, sortie):
    import numpy as np
    v = float(reglages.get("vitesse") or 1)
    N = int((total + 1.2) * SR)
    voix = np.zeros((N, 2), np.float32)
    parle = np.zeros(int(total * 10) + 20, bool)               # la voix joue-t-elle ? au pas de 100 ms, comme musTick
    for p in pages:
        if not p["_audio"]:
            continue
        x = pcm(p["_audio"], v)
        i0 = int(p["_t0"] * SR)
        i1 = min(N, i0 + len(x))
        voix[i0:i1] += x[: i1 - i0]
        parle[int(p["_t0"] * 10): int((p["_t0"] + len(x) / SR) * 10) + 1] = True
    if reglages.get("musique") and reglages.get("musique_liste"):
        # playlist : tours melanges (meme regle que musIdx), graine gardee -> la meme video se refait a l'identique
        rnd = random.Random(reglages.get("graine") or 1)
        fichiers = reglages["musique_liste"]; seq = []
        mus = np.zeros((N, 2), np.float32); t = 0.0; k = 0
        while t < total + 1:
            if len(seq) <= k:
                tour = list(range(len(fichiers))); rnd.shuffle(tour)
                if len(fichiers) > 1 and seq and tour[0] == seq[-1]:
                    tour.append(tour.pop(0))
                seq += tour
            x = pcm(fichiers[seq[k]])
            d = len(x) / SR
            env = np.minimum(1.0, np.minimum(np.arange(len(x)) / SR / FONDU, (d - np.arange(len(x)) / SR) / FONDU)).clip(0, 1)
            i0 = int(t * SR); i1 = min(N, i0 + len(x))
            if i1 > i0:
                mus[i0:i1] += x[: i1 - i0] * env[: i1 - i0, None]
            t += max(1.0, d - FONDU); k += 1
        # gain : musTick rejoue a 10 Hz (baisse 0,02 / pas ; remonte max(0.004, cible*0.04) / pas ; 0 a la fin)
        base = float(25 if reglages.get("volume") is None else reglages["volume"]) / 100 * GAIN_MAX   # v1.94 : 0 % restait 25 %
        g, gains = 0.0, []
        for s in range(int((total + 1.2) * 10) + 1):
            cible = 0.0 if s / 10 >= total else base * (DUCK if s < len(parle) and parle[s] else 1)
            g += max(-0.02, min(max(0.004, cible * 0.04), cible - g))
            gains.append(g)
        gain = np.interp(np.arange(N) / SR, np.arange(len(gains)) / 10, np.array(gains)).astype(np.float32)
        voix += mus * gain[:, None]
    np.clip(voix, -1, 1, out=voix)
    import wave
    with wave.open(sortie, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((voix * 32767).astype("<i2").tobytes())


# ---------------------------------------------------------------- tout
def main():
    global PROG
    ap = argparse.ArgumentParser()
    ap.add_argument("chap"); ap.add_argument("tag")
    ap.add_argument("--reglages", default="{}"); ap.add_argument("--pages"); ap.add_argument("--sortie")
    # compression : banc du 22/09 sur Claymore p.5-12 -> CQ 25 = 5,3 Mbit/s, CQ 28/3M = 3,0, CQ 30/2M = 2,1 ; a l'oeil,
    # identiques en gros plan 1:1 -> CQ 30 / 2 Mbit/s (~16 Mo la minute au lieu de 40 : telechargeable sur le telephone)
    ap.add_argument("--cq", default="30"); ap.add_argument("--maxrate", default="2M")
    ap.add_argument("--malgre-alertes", action="store_true",
                    help="v1.98.0 : faire la video meme si le chapitre a une alerte de moderation OUVERTE")
    a = ap.parse_args()
    reglages = json.loads(a.reglages)
    reglages.setdefault("graine", random.randrange(1, 10 ** 6))
    chap = a.chap.strip("/")
    # v1.98.0 (feuille de route 4-decies, Quang 24/09) : un chapitre avec des pages refusees par la moderation n'est PAS mis
    # en video tant que l'alerte est ouverte -- code 4, la file la garde « en attente de moderation », rien n'est gache
    sys.path.insert(0, HERE)
    import moderation as mod
    ouv = [] if a.malgre_alertes else mod.ouvertes_pour(chap)
    if ouv:
        print("VIDEO EN ATTENTE : %d alerte(s) de moderation ouverte(s) sur %s (pages %s) -- a traiter dans l'app (onglet "
              "« A traiter »), ou --malgre-alertes" % (len(ouv), chap, sorted({p for x in ouv for p in x["pages"]})), flush=True)
        sys.exit(4)
    vd = os.path.join(SRC, chap, "video")
    os.makedirs(vd, exist_ok=True)
    sortie = a.sortie or os.path.join(vd, a.tag + ".mp4")
    PROG = os.path.join(vd, a.tag + ".progress.json")
    t0 = NOW()
    n, man, pages, total = charger(chap, a.tag, reglages, a.pages)
    if not pages:
        raise SystemExit("aucune page a mettre en video")
    md = os.path.join(SRC, chap.split("/")[0], "musique")
    liste = []
    for nom in reglages.get("musique_noms") or []:
        f = [x for x in (os.listdir(md) if os.path.isdir(md) else []) if os.path.splitext(x)[0] == nom]
        if f:
            liste.append(os.path.join(md, f[0]))
    reglages["musique_liste"] = liste
    tmp = tempfile.mkdtemp(prefix="mangavid_")
    enc = ["-c:v", "h264_nvenc", "-preset", "p5", "-cq", a.cq, "-pix_fmt", "yuv420p"]
    if a.maxrate:
        enc[-2:-2] = ["-maxrate", a.maxrate, "-bufsize", str(2 * int(a.maxrate.rstrip("Mk"))) + a.maxrate[-1]]
    try:
        cv = None
        if camera(reglages) == "cases":
            progres("cases", 0, len(pages))
            cv = preparer_cases(chap, pages)
        # v1.96.0 : 3 pages a la fois (le rendu image par image du mode cases occupe le processeur ; 3 sessions NVENC)
        from concurrent.futures import ThreadPoolExecutor
        fait = [0]

        def une(i):
            p = pages[i]
            prec = pages[i - 1] if i and pages[i - 1].get("_plan") else None
            c = clip_cases(p, tmp, i, enc, cv, prec) if p.get("_plan") else clip_page(p, tmp, i, enc)
            fait[0] += 1
            progres("images", fait[0], len(pages))
            return c
        progres("images", 0, len(pages))
        with ThreadPoolExecutor(max_workers=3) as ex:
            clips = list(ex.map(une, range(len(pages))))
        progres("son", len(pages), len(pages))
        wav = os.path.join(tmp, "son.wav")
        mixer(pages, reglages, total, wav)
        ass = os.path.join(tmp, "sous.ass")
        ecrire_ass(ass, n, pages, reglages, total)
        lst = os.path.join(tmp, "liste.txt")
        open(lst, "w", encoding="utf-8").write("".join("file '%s'\n" % c.replace("\\", "/") for c in clips))
        progres("assemblage", len(pages), len(pages))
        part = sortie + ".part.mp4"
        # ass= lit un chemin : on travaille DANS tmp (les deux-points de C: cassent la syntaxe du filtre sous Windows)
        ff(["-f", "concat", "-safe", "0", "-i", "liste.txt", "-i", "son.wav", "-vf", "ass=sous.ass",
            "-map", "0:v", "-map", "1:a"] + enc + ["-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", part],
           cwd=tmp)
        os.replace(part, sortie)
        info = {"version": VERSION, "chapitre": chap, "tag": a.tag, "titre": n.get("titre"), "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "reglages": {k: v for k, v in reglages.items() if k != "musique_liste"},
                "empreinte": empreinte(chap, a.tag, reglages), "pages": len(pages), "duree_s": round(total, 1),
                "taille": os.path.getsize(sortie), "fabrication_s": round(NOW() - t0, 1), "format": "%dx%d" % (W, H)}
        if not a.sortie:
            json.dump(info, open(os.path.join(vd, a.tag + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        progres("fini", 1, 1, fini=True)
        print("OK : %s (%d pages, %.1f min, %.1f Mo) en %.0f s" % (sortie, len(pages), total / 60, info["taille"] / 1e6, NOW() - t0))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
