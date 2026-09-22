# -*- coding: utf-8 -*-
"""Patch du proxy 8190 : un GROUPE de videos en UNE archive .zip (Manga Studio v1.97.0, 22/09/2026, etape 15).

Quang (09h17) : « telecharger un groupe de videos d'un manga avec une selection [...] il peut y avoir beaucoup de
chapitres ». Plusieurs telechargements d'affilee : le telephone en bloque une partie. Donc
GET /manga/videos_zip?serie=<slug>&d=ch_1,ch_2,... -> une archive .zip EN FLUX : les MP4 sont STOCKES (deja
compresses, recompresser = du temps pour rien), zip64, rien en memoire ni sur disque. Noms = _video_nom().
Rejouable : python patch_videos_zip.py <chemin du proxy>. Suppose patch_video_prec.py applique (_video_nom).
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "def serve_manga_videos_zip(" in s:
    print("deja patche")
    sys.exit(0)


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


rep(r'''        elif self.path.split("?", 1)[0] == "/manga/video_file":''',
    r'''        elif self.path.split("?", 1)[0] == "/manga/videos_zip":            # Manga Studio v1.97.0
            _q = parse_qs(urlparse(self.path).query)
            self.serve_manga_videos_zip((_q.get("serie") or [""])[0], (_q.get("d") or [""])[0])
        elif self.path.split("?", 1)[0] == "/manga/video_file":''')

rep(r'''    def serve_manga_video(self, rel, telecharger=False):''',
    r'''    def serve_manga_videos_zip(self, serie, ds):
        """v1.97.0 : les videos choisies d'une serie en UNE archive, en flux (MP4 stockes, zip64)."""
        import zipfile
        info = manga_videos(serie)
        if info is None:
            self._json(404, {"error": "serie introuvable"}); return
        voulus = {x.strip() for x in (ds or "").split(",") if x.strip()}
        items = []
        for c in info.get("chapitres") or []:
            if c["d"].split("/")[-1] in voulus and c.get("videos"):
                rel = c["videos"][0]["fichier"]
                full = _manga_src_safe(rel)
                if full and os.path.isfile(full):
                    items.append((rel, full, c))
        if not items:
            self._json(404, {"error": "aucune video parmi les chapitres demandes"}); return
        titre = items[0][2].get("titre") or serie
        num = lambda c: str(c.get("chapitre") or "").zfill(3) if str(c.get("chapitre") or "").isdigit() else str(c.get("chapitre") or "")
        nom = "%s - vidéos ch%s à ch%s (%d) - %s.zip" % (titre, num(items[0][2]), num(items[-1][2]), len(items),
                                                          time.strftime("%Y-%m-%d %Hh%M"))
        nom = re.sub(r'[\/:*?"<>|]+', " ", nom)
        ascii_ = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode() or "videos.zip"
        self.send_response(200); self._cors()
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Disposition", "attachment; filename=\"%s\"; filename*=UTF-8''%s"
                         % (ascii_.replace('"', ""), quote(nom, safe="")))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True
        try:
            with zipfile.ZipFile(self.wfile, "w", zipfile.ZIP_STORED, allowZip64=True) as z:
                vus = set()
                for rel, full, _c in items:
                    n = _video_nom(rel, full)
                    while n in vus:
                        n = n[:-4] + " (bis).mp4"
                    vus.add(n)
                    zi = zipfile.ZipInfo(n, date_time=time.localtime(os.path.getmtime(full))[:6])
                    zi.compress_type = zipfile.ZIP_STORED
                    with open(full, "rb") as f, z.open(zi, "w", force_zip64=True) as out:
                        while True:
                            bloc = f.read(1 << 20)
                            if not bloc:
                                break
                            out.write(bloc)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass                                                # telechargement annule : rien a faire

    def serve_manga_video(self, rel, telecharger=False):''')

open(p, "w", encoding="utf-8").write(s)
print("patch videos zip OK")
