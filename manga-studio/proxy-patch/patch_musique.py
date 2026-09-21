# -*- coding: utf-8 -*-
"""Patch du proxy 8190 : musique de fond PAR SERIE (Manga Studio v1.85.0, 22/09/2026, etape 13).

Les morceaux vivent sous sources/<serie>/musique/ (donc sur C:, servis par /manga/source_file avec Range).
GET  /manga/musiques?serie=      -> {items:[{nom, fichier, taille}], choix}
POST /manga/musique_import       {serie, nom, data (base64)} -> ajoute un morceau (mp3/wav/ogg/m4a/flac)
POST /manga/musique_choix        {serie, nom | ""}           -> le morceau joue sous la narration ("" = aucun)
POST /manga/musique_suppr        {serie, nom}                -> corbeille (sources/_corbeille/), jamais d'effacement
Rejouable : python patch_musique.py <chemin du proxy>. Suppose patch_bibliotheque.py + patch_traduction.py appliques.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "def manga_musiques(" in s:
    print("deja patche")
    sys.exit(0)


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


rep('''# --- Traduction des dialogues d'un chapitre (Manga Studio v1.84.0) ---------------------''',
    '''# --- Musique de fond par serie (Manga Studio v1.85.0) -----------------------------------
_MUS_EXT = (".mp3", ".wav", ".ogg", ".m4a", ".flac")


def _mus_dir(serie):
    serie = (serie or "").strip("/")
    sd = _manga_src_safe(serie) if _RE_SERIE.match(serie) else None
    return (sd, os.path.join(sd, "musique")) if sd and os.path.isdir(sd) else (None, None)


def _mus_ext(b):
    if b[:3] == b"ID3" or (len(b) > 1 and b[0] == 0xFF and (b[1] & 0xE0) == 0xE0): return ".mp3"
    if b[:4] == b"RIFF" and b[8:12] == b"WAVE": return ".wav"
    if b[:4] == b"OggS": return ".ogg"
    if b[:4] == b"fLaC": return ".flac"
    if b[4:8] == b"ftyp": return ".m4a"
    return None


def _mus_nom(nom):
    nom = unicodedata.normalize("NFKD", os.path.splitext(nom or "")[0]).encode("ascii", "ignore").decode()
    nom = re.sub(r"[^A-Za-z0-9 ._()-]+", " ", nom)
    return re.sub(r"\\s+", " ", nom).strip(" .")[:80]


def manga_musiques(serie):
    sd, md = _mus_dir(serie)
    if not sd:
        return None
    items, choix = [], ""
    if os.path.isdir(md):
        for f in sorted(os.listdir(md), key=str.lower):
            if f.lower().endswith(_MUS_EXT):
                items.append({"nom": os.path.splitext(f)[0], "fichier": serie.strip("/") + "/musique/" + f,
                              "taille": os.path.getsize(os.path.join(md, f))})
        try:
            with open(os.path.join(md, "choix.json"), encoding="utf-8") as fh:
                choix = json.load(fh).get("nom") or ""
        except Exception:
            pass
    if choix and not any(x["nom"] == choix for x in items):
        choix = ""
    return {"items": items, "choix": choix}


def manga_musique_import(data):
    sd, md = _mus_dir(data.get("serie"))
    if not sd:
        return {"error": "serie introuvable"}
    try:
        b = base64.b64decode((data.get("data") or "").split(",")[-1])
    except Exception:
        return {"error": "fichier illisible"}
    ext = _mus_ext(b[:16])
    if not ext or len(b) < 10000:
        return {"error": "ce n'est pas un fichier audio (mp3, wav, ogg, m4a, flac)"}
    nom = _mus_nom(data.get("nom")) or "morceau"
    os.makedirs(md, exist_ok=True)
    base, k = nom, 2
    while any(os.path.isfile(os.path.join(md, nom + e)) for e in _MUS_EXT):
        nom = "%s (%d)" % (base, k); k += 1
    with open(os.path.join(md, nom + ext), "wb") as f:
        f.write(b)
    r = manga_musiques(data.get("serie"))
    if not r["choix"]:                            # le premier morceau d'une serie devient celui qui joue
        manga_musique_choix({"serie": data.get("serie"), "nom": nom})
    return {"ok": True, "nom": nom}


def manga_musique_choix(data):
    sd, md = _mus_dir(data.get("serie"))
    if not sd:
        return {"error": "serie introuvable"}
    nom = data.get("nom") or ""
    if nom and not any(x["nom"] == nom for x in manga_musiques(data.get("serie"))["items"]):
        return {"error": "morceau introuvable"}
    os.makedirs(md, exist_ok=True)
    with open(os.path.join(md, "choix.json"), "w", encoding="utf-8") as f:
        json.dump({"nom": nom}, f, ensure_ascii=False)
    return {"ok": True, "choix": nom}


def manga_musique_suppr(data):
    sd, md = _mus_dir(data.get("serie"))
    if not sd:
        return {"error": "serie introuvable"}
    it = [x for x in manga_musiques(data.get("serie"))["items"] if x["nom"] == data.get("nom")]
    if not it:
        return {"error": "morceau introuvable"}
    f = os.path.basename(it[0]["fichier"])
    os.makedirs(MANGA_CORBEILLE, exist_ok=True)
    dest = os.path.join(MANGA_CORBEILLE, time.strftime("%Y%m%d-%H%M%S") + "_" + data["serie"].strip("/") + "__musique__" + f)
    shutil.move(os.path.join(md, f), dest)
    try:                                          # c'etait celui qui jouait -> plus aucun
        with open(os.path.join(md, "choix.json"), encoding="utf-8") as fh:
            if json.load(fh).get("nom") == data.get("nom"):
                manga_musique_choix({"serie": data.get("serie"), "nom": ""})
    except Exception:
        pass
    return {"ok": True, "corbeille": os.path.relpath(dest, MANGA_SOURCES)}


# --- Traduction des dialogues d'un chapitre (Manga Studio v1.84.0) ---------------------''')

rep('''        elif self.path.split("?", 1)[0] == "/manga/traductions":           # Manga Studio v1.84.0''',
    '''        elif self.path.split("?", 1)[0] == "/manga/musiques":              # Manga Studio v1.85.0
            _r = manga_musiques((parse_qs(urlparse(self.path).query).get("serie") or [""])[0])
            if _r is None: self._json(404, {"error": "serie introuvable"})
            else: self._json(200, _r)
        elif self.path.split("?", 1)[0] == "/manga/traductions":           # Manga Studio v1.84.0''')

rep('''            elif self.path == "/manga/traduire":               # Manga Studio v1.84.0''',
    '''            elif self.path == "/manga/musique_import":         # Manga Studio v1.85.0
                self._json(200, manga_musique_import(data))
            elif self.path == "/manga/musique_choix":
                self._json(200, manga_musique_choix(data))
            elif self.path == "/manga/musique_suppr":
                self._json(200, manga_musique_suppr(data))
            elif self.path == "/manga/traduire":               # Manga Studio v1.84.0''')

open(p, "w", encoding="utf-8").write(s)
print("patch musique OK")
