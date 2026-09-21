# -*- coding: utf-8 -*-
"""Patch du proxy 8190 : requetes partielles (Range) sur les fichiers manga (Manga Studio v1.83.0, 22/09/2026).

Mesure : « Range: bytes=1000-2000 » -> 200 + fichier entier, sans Accept-Ranges. Chrome ne peut alors PAS
se positionner dans un MP3 : la barre de temps du lecteur sautait bien a la bonne PAGE, mais l'audio
repartait du debut de la page. On repond 206 + Content-Range, et Accept-Ranges partout.
Rejouable : python patch_range.py <chemin du proxy>.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "Content-Range" in s and "serve_manga_file" in s and "v1.83.0 : Range" in s:
    print("deja patche")
    sys.exit(0)
a = '''        try:
            with open(full, "rb") as f: data = f.read()
            self.send_response(200); self._cors()
            self.send_header("Content-Type", ct)
            self.send_header("Cache-Control", "max-age=86400")  # immuable par nom
            self.send_header("Content-Length", str(len(data))); self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self._json(500, {"error": str(e)})'''
if s.count(a) != 1:
    raise SystemExit("ancre introuvable (%d)" % s.count(a))
s = s.replace(a, '''        try:
            with open(full, "rb") as f: data = f.read()
            # v1.83.0 : Range -> 206 (sinon Chrome ne sait pas se positionner dans un MP3)
            m = re.match(r"bytes=(\\d*)-(\\d*)$", (self.headers.get("Range") or "").strip())
            debut, fin = 0, len(data) - 1
            if m and (m.group(1) or m.group(2)):
                if m.group(1):
                    debut = int(m.group(1)); fin = min(int(m.group(2)) if m.group(2) else fin, fin)
                else:                                       # bytes=-N : les N derniers octets
                    debut = max(0, len(data) - int(m.group(2)))
                if debut > fin:
                    self.send_response(416); self._cors()
                    self.send_header("Content-Range", "bytes */%d" % len(data)); self.end_headers(); return
                self.send_response(206); self._cors()
                self.send_header("Content-Range", "bytes %d-%d/%d" % (debut, fin, len(data)))
            else:
                self.send_response(200); self._cors()
            morceau = data[debut:fin + 1]
            self.send_header("Content-Type", ct)
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Cache-Control", "max-age=86400")  # immuable par nom
            self.send_header("Content-Length", str(len(morceau))); self.end_headers()
            self.wfile.write(morceau)
        except Exception as e:
            self._json(500, {"error": str(e)})''')
open(p, "w", encoding="utf-8").write(s)
print("patch range OK")
