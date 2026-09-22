# -*- coding: utf-8 -*-
"""Patch du proxy 8190 : VIDEOS des chapitres narres (Manga Studio v1.93.0, 22/09/2026, etape 5).

GET  /manga/videos?serie=      -> par chapitre : narrations avec voix, videos (a jour / a refaire + RAISONS), file
POST /manga/video              {entrees:[{d, tag?}], reglages} -> demandes deposees dans sources/_videos_file/, le
                                programme scripts/video_lot.py les fabrique une par une (lance s'il ne tourne pas)
POST /manga/video_suppr        {d, tag}  -> video + fiche a la corbeille
POST /manga/video_annule       {id}      -> retire une demande en attente (ou une erreur)
GET  /manga/video_file?p=&dl=  -> la video EN FLUX (Range, jamais lue en entier en memoire ; dl=1 = telecharger)
/manga/activite : + les videos en cours et en attente.
« A refaire » : l'empreinte gardee avec la video (video_chapitre.empreinte) est recalculee sur l'etat actuel ;
chaque poste qui differe donne une raison lisible. + la selection de musique du chapitre a-t-elle change ?
Rejouable : python patch_video.py <chemin du proxy>. Suppose patch_activite / run_vivant / musique_selection appliques.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "def manga_videos(" in s:
    print("deja patche")
    sys.exit(0)


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


rep('''# --- Karaoke d'une narration (Manga Studio v1.86.0) ------------------------------------''',
    '''# --- Videos des chapitres (Manga Studio v1.93.0) ----------------------------------------
MANGA_VIDEO_MOD = os.path.join(MANGA_ROOT, "scripts", "video_chapitre.py")
MANGA_VIDEO_LOT = os.path.join(MANGA_ROOT, "scripts", "video_lot.py")
MANGA_VIDEO_FILE = os.path.join(MANGA_SOURCES, "_videos_file")
_VIDEO_MOD = {"m": None, "t": 0}
_VIDEO_LBL = {"narration": "la narration a été refaite", "karaoke": "le karaoké a été recalé",
              "voix": "la voix a changé", "pages": "des pages ont changé (ajout, suppression)",
              "traduction": "la traduction a été refaite", "musique": "un morceau de musique a changé"}


def _video_mod():
    """video_chapitre.py charge a la volee (sa fonction empreinte() est LA regle ; aucune copie ici)."""
    t = os.path.getmtime(MANGA_VIDEO_MOD)
    if _VIDEO_MOD["m"] is None or _VIDEO_MOD["t"] != t:
        import importlib.util
        sp = importlib.util.spec_from_file_location("manga_video_chapitre", MANGA_VIDEO_MOD)
        m = importlib.util.module_from_spec(sp)
        sp.loader.exec_module(m)
        _VIDEO_MOD.update(m=m, t=t)
    return _VIDEO_MOD["m"]


def _video_demandes():
    out = []
    for n in (os.listdir(MANGA_VIDEO_FILE) if os.path.isdir(MANGA_VIDEO_FILE) else []):
        if n.startswith("_") or not n.endswith(".json"):
            continue
        try:
            with open(os.path.join(MANGA_VIDEO_FILE, n), encoding="utf-8") as f:
                e = json.load(f)
        except Exception:
            continue
        if e.get("etat") == "en cours" and e.get("pid") and not _pid_vivant(e["pid"]) \\
                and time.time() - float(e.get("debut") or 0) > 60:
            e.update(etat="echec", err="le programme de fabrication s'est arrete")
        out.append(e)
    return sorted(out, key=lambda e: e.get("t") or 0)


def _video_raisons(d, tag, info):
    td = _narr_dir(d, tag)
    if not td or not os.path.isfile(os.path.join(td, "narration.json")):
        return ["la narration n'existe plus"]
    reg = info.get("reglages") or {}
    try:
        cur = _video_mod().empreinte(d, tag, reg)
    except Exception as e:
        return ["empreinte illisible : %s" % str(e)[:80]]
    old, r = info.get("empreinte") or {}, []
    for k, v in cur.items():
        if k == "reglages" or (k == "karaoke" and not (reg.get("sous") and reg.get("karaoke"))):
            continue
        if old.get(k) != v:
            r.append(_VIDEO_LBL.get(k, k))
    if reg.get("musique"):
        eff = (manga_musiques(d.split("/")[0], d) or {}).get("effectif") or []
        if eff != (reg.get("musique_noms") or []):
            r.append("la sélection de musique a changé")
    return r


def _video_narrs(d):
    n = [{"tag": it["tag"], "created_at": it.get("created_at"), "voice": it.get("voice")}
         for it in ((manga_narrations(d) or {}).get("items") or []) if it.get("etat") == "fini" and it.get("audio")]
    return sorted(n, key=lambda x: x.get("created_at") or "", reverse=True)


def manga_videos(serie):
    sd = _manga_src_safe(serie) if _RE_SERIE.match(serie or "") else None
    if not sd or not os.path.isdir(sd):
        return None
    dem = _video_demandes()
    chaps = []
    for ch in sorted(os.listdir(sd), key=lambda c: _chap_key(c[3:]) if c.startswith("ch_") else (2, 0.0, c)):
        cd = os.path.join(sd, ch)
        if not os.path.isfile(os.path.join(cd, "manifest.json")):
            continue
        d = serie + "/" + ch
        try:
            with open(os.path.join(cd, "manifest.json"), encoding="utf-8") as f:
                m = json.load(f)
        except Exception:
            m = {}
        vids, vd = [], os.path.join(cd, "video")
        for fn in (sorted(os.listdir(vd)) if os.path.isdir(vd) else []):
            if not fn.endswith(".json") or fn.endswith(".progress.json"):
                continue
            try:
                with open(os.path.join(vd, fn), encoding="utf-8") as f:
                    info = json.load(f)
            except Exception:
                continue
            tag, mp4 = info.get("tag") or fn[:-5], os.path.join(vd, (info.get("tag") or fn[:-5]) + ".mp4")
            if not os.path.isfile(mp4):
                continue
            raisons = _video_raisons(d, tag, info)
            vids.append({"tag": tag, "created_at": info.get("created_at"), "duree_s": info.get("duree_s"),
                         "taille": os.path.getsize(mp4), "reglages": info.get("reglages"), "raisons": raisons,
                         "etat": "a_refaire" if raisons else "a_jour", "fichier": d + "/video/" + tag + ".mp4",
                         "v": int(os.path.getmtime(mp4))})
        file = []
        for e in dem:
            if e.get("d") != d:
                continue
            x = {k: e.get(k) for k in ("id", "tag", "etat", "err", "t")}
            if e.get("etat") == "en cours":
                try:
                    with open(os.path.join(vd, e["tag"] + ".progress.json"), encoding="utf-8") as f:
                        x["progress"] = json.load(f)
                except Exception:
                    pass
            file.append(x)
        chaps.append({"d": d, "chapitre": str(m.get("chapter") or ch[3:]), "titre": m.get("title") or serie,
                      "narrations": _video_narrs(d), "videos": vids, "file": file})
    return {"chapitres": chaps}


def manga_video_ajoute(data):
    reg = data.get("reglages") or {}
    try:
        vit = min(2.0, max(0.5, float(reg.get("vitesse") or 1)))
    except (TypeError, ValueError):
        vit = 1.0
    propre = {"vitesse": vit, "sous": bool(reg.get("sous")), "karaoke": bool(reg.get("karaoke")),
              "musique": bool(reg.get("musique")), "volume": max(0, min(100, int(reg.get("volume") or 0))),
              "pages": reg.get("pages") if re.match(r"^[a-z]{2}$", reg.get("pages") or "") else ""}
    dem = [e for e in _video_demandes() if e.get("etat") in ("attente", "en cours")]
    os.makedirs(MANGA_VIDEO_FILE, exist_ok=True)
    ok, refus = [], []
    for en in data.get("entrees") or []:
        d = (en.get("d") or "").strip("/")
        base = _manga_src_safe(d)
        if not base or not os.path.isfile(os.path.join(base, "manifest.json")):
            refus.append({"d": d, "raison": "chapitre introuvable"}); continue
        narrs = [x["tag"] for x in _video_narrs(d)]
        tag = en.get("tag") or (narrs[0] if narrs else "")
        if tag not in narrs:
            refus.append({"d": d, "raison": "pas de narration avec voix"}); continue
        if any(e.get("d") == d and e.get("tag") == tag for e in dem):
            refus.append({"d": d, "raison": "déjà dans la file"}); continue
        r = dict(propre)
        r["musique_noms"] = ((manga_musiques(d.split("/")[0], d) or {}).get("effectif") or []) if r["musique"] else []
        if r["pages"] and not os.path.isfile(os.path.join(base, "traduction", r["pages"], "traduction.json")):
            r["pages"] = ""                                  # pas traduit dans cette langue : la video montre la VO
        e = {"id": time.strftime("%Y%m%d-%H%M%S") + "-%04d" % random.randrange(10000), "d": d, "tag": tag,
             "reglages": r, "etat": "attente", "t": time.time()}
        with open(os.path.join(MANGA_VIDEO_FILE, e["id"] + ".json"), "w", encoding="utf-8") as f:
            json.dump(e, f, ensure_ascii=False)
        ok.append({"d": d, "tag": tag, "id": e["id"]})
    if ok:
        vivant = False
        try:
            with open(os.path.join(MANGA_VIDEO_FILE, "_runner.json"), encoding="utf-8") as f:
                vivant = _pid_vivant(json.load(f).get("pid") or 0)
        except Exception:
            pass
        if not vivant:
            lg = open(os.path.join(MANGA_VIDEO_FILE, "_runner.log"), "a", encoding="utf-8")
            subprocess.Popen([MANGA_PY, MANGA_VIDEO_LOT], stdout=lg, stderr=lg, cwd=os.path.dirname(MANGA_VIDEO_LOT),
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return {"ok": True, "ajoutees": ok, "refusees": refus}


def manga_video_suppr(data):
    d, tag = (data.get("d") or "").strip("/"), data.get("tag") or ""
    base = _manga_src_safe(d)
    if not base or not _RE_TAG.match(tag):
        return {"error": "video introuvable"}
    if any(e.get("d") == d and e.get("tag") == tag and e.get("etat") == "en cours" for e in _video_demandes()):
        return {"error": "cette video est en cours de fabrication"}
    vd = os.path.join(base, "video")
    fichiers = [os.path.join(vd, tag + x) for x in (".mp4", ".json") if os.path.isfile(os.path.join(vd, tag + x))]
    if not fichiers:
        return {"error": "video introuvable"}
    dest = os.path.join(MANGA_CORBEILLE, time.strftime("%Y%m%d-%H%M%S") + "_" + d.replace("/", "__") + "__video__" + tag)
    os.makedirs(dest, exist_ok=True)
    for f in fichiers:
        shutil.move(f, os.path.join(dest, os.path.basename(f)))
    return {"ok": True, "corbeille": os.path.relpath(dest, MANGA_SOURCES)}


def manga_video_annule(data):
    i = data.get("id") or ""
    if not re.match(r"^[0-9-]{10,40}$", i):
        return {"error": "demande introuvable"}
    f = os.path.join(MANGA_VIDEO_FILE, i + ".json")
    try:
        with open(f, encoding="utf-8") as h:
            e = json.load(h)
    except Exception:
        return {"error": "demande introuvable"}
    if e.get("etat") == "en cours":
        return {"error": "déjà en cours de fabrication"}
    for x in (f, os.path.join(MANGA_VIDEO_FILE, i + ".log")):
        try:
            os.remove(x)
        except OSError:
            pass
    return {"ok": True}


# --- Karaoke d'une narration (Manga Studio v1.86.0) ------------------------------------''')

# ---------- activite : videos en cours + en attente ----------
rep('''    try:
        fs = manga_fetch_status()''',
    '''    try:                                                     # v1.93.0 : les videos (en cours, puis en attente)
        for e in _video_demandes():
            if e.get("etat") not in ("en cours", "attente"):
                continue
            d = e.get("d") or ""
            it = {"type": "video", "d": d, "tag": e.get("tag"), "titre": d.split("/")[0], "chapitre": d.split("/")[-1][3:],
                  "etape": "attente" if e.get("etat") == "attente" else None}
            try:
                with open(os.path.join(MANGA_SOURCES, d, "manifest.json"), encoding="utf-8") as f:
                    mm = json.load(f)
                it.update(titre=mm.get("title") or it["titre"], chapitre=str(mm.get("chapter") or it["chapitre"]))
            except Exception:
                pass
            if e.get("etat") == "en cours":
                try:
                    with open(os.path.join(MANGA_SOURCES, d, "video", e["tag"] + ".progress.json"), encoding="utf-8") as f:
                        pr = json.load(f)
                    it.update(etape=pr.get("etape"), fait=pr.get("fait"), total=pr.get("total"))
                except Exception:
                    pass
            out.append(it)
    except Exception:
        pass
    try:
        fs = manga_fetch_status()''')

# ---------- routes ----------
rep('''        elif self.path.split("?", 1)[0] == "/manga/activite":              # Manga Studio v1.88.0''',
    '''        elif self.path.split("?", 1)[0] == "/manga/videos":                # Manga Studio v1.93.0
            _r = manga_videos((parse_qs(urlparse(self.path).query).get("serie") or [""])[0])
            if _r is None: self._json(404, {"error": "serie introuvable"})
            else: self._json(200, _r)
        elif self.path.split("?", 1)[0] == "/manga/video_file":
            _q = parse_qs(urlparse(self.path).query)
            self.serve_manga_video((_q.get("p") or [""])[0], (_q.get("dl") or [""])[0] == "1")
        elif self.path.split("?", 1)[0] == "/manga/activite":              # Manga Studio v1.88.0''')
rep('''            elif self.path == "/manga/karaoke":                # Manga Studio v1.86.0''',
    '''            elif self.path == "/manga/video":                  # Manga Studio v1.93.0
                self._json(200, manga_video_ajoute(data))
            elif self.path == "/manga/video_suppr":
                self._json(200, manga_video_suppr(data))
            elif self.path == "/manga/video_annule":
                self._json(200, manga_video_annule(data))
            elif self.path == "/manga/karaoke":                # Manga Studio v1.86.0''')
rep('''    def serve_manga_file(self, rel, sources=False):''',
    '''    def serve_manga_video(self, rel, telecharger=False):
        """v1.93.0 : une video EN FLUX depuis le disque (Range) — serve_manga_file lit tout en memoire,
        intenable pour 160 Mo a chaque saut de lecture. dl=1 : « enregistrer sous » (PC et telephone)."""
        full = _manga_src_safe(rel)
        if not full or not full.lower().endswith(".mp4") or os.sep + "video" + os.sep not in full or not os.path.isfile(full):
            self._json(404, {"error": "not found"}); return
        taille = os.path.getsize(full)
        m = re.match(r"bytes=(\\d*)-(\\d*)$", (self.headers.get("Range") or "").strip())
        debut, fin = 0, taille - 1
        try:
            if m and (m.group(1) or m.group(2)):
                if m.group(1):
                    debut = int(m.group(1)); fin = min(int(m.group(2)) if m.group(2) else fin, fin)
                else:
                    debut = max(0, taille - int(m.group(2)))
                if debut > fin:
                    self.send_response(416); self._cors()
                    self.send_header("Content-Range", "bytes */%d" % taille); self.end_headers(); return
                self.send_response(206); self._cors()
                self.send_header("Content-Range", "bytes %d-%d/%d" % (debut, fin, taille))
            else:
                self.send_response(200); self._cors()
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Cache-Control", "no-cache")        # une video se REFAIT sous le meme nom
            if telecharger:
                parts = rel.replace("\\\\", "/").strip("/").split("/")
                nom = re.sub(r"[^A-Za-z0-9._-]+", "-", "%s-%s-%s" % (parts[0], parts[1] if len(parts) > 1 else "", parts[-1]))
                self.send_header("Content-Disposition", 'attachment; filename="%s"' % nom)
            self.send_header("Content-Length", str(fin - debut + 1)); self.end_headers()
            with open(full, "rb") as f:
                f.seek(debut)
                reste = fin - debut + 1
                while reste > 0:
                    bloc = f.read(min(1 << 20, reste))
                    if not bloc:
                        break
                    self.wfile.write(bloc); reste -= len(bloc)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass                                                   # le lecteur a saute ailleurs : normal

    def serve_manga_file(self, rel, sources=False):''')

open(p, "w", encoding="utf-8").write(s)
print("patch video OK")
