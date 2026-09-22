# -*- coding: utf-8 -*-
"""Patch du proxy 8190 : les pages et MP3 ne sont plus « immuables par nom » (Manga Studio v2.4.6, 22/09/2026).

Incident (Quang, 22/09 23h32) : Claymore ch.1 supprime (62 pages EN, MANGA Plus) puis recapture (180 pages FR, Raijin).
Le disque etait juste, mais l'app montrait les 62 PREMIERES pages en anglais : serve_manga_file envoyait
« Cache-Control: max-age=86400 # immuable par nom », et les nouvelles pages portent les MEMES noms (page_001.png...).
Le navigateur les ressortait de son cache pendant 24 h sans rien demander.

Desormais : ETag = date de modification + taille du fichier, « Cache-Control: no-cache » (le navigateur garde l'image
mais REDEMANDE a chaque fois) et 304 sans corps quand rien n'a change (If-None-Match). Aucune autre route touchee.
Rejouable : python patch_cache_pages.py <chemin du proxy>.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "# v2.4.6 : ETag" in s:
    print("deja patche")
    sys.exit(0)


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


rep('''        ext = os.path.splitext(full)[1].lower()
        ct = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
              ".webp": "image/webp", ".mp3": "audio/mpeg"}.get(ext, "application/octet-stream")''',
    '''        ext = os.path.splitext(full)[1].lower()
        ct = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
              ".webp": "image/webp", ".mp3": "audio/mpeg"}.get(ext, "application/octet-stream")
        # v2.4.6 : ETag -- un chapitre supprime puis recapture reprend les MEMES noms de pages (incident Claymore 22/09)
        _st = os.stat(full)
        etag = '"%x-%x"' % (_st.st_mtime_ns, _st.st_size)
        if not self.headers.get("Range") and etag in (self.headers.get("If-None-Match") or ""):
            self.send_response(304); self._cors()
            self.send_header("ETag", etag); self.send_header("Cache-Control", "no-cache"); self.end_headers(); return''')
rep('''            self.send_header("Cache-Control", "max-age=86400")  # immuable par nom''',
    '''            self.send_header("ETag", etag)
            self.send_header("Cache-Control", "no-cache")          # v2.4.6 : garde, mais revalide (ETag -> 304)''')
open(p, "w", encoding="utf-8").write(s)
print("patche")
