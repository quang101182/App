# -*- coding: utf-8 -*-
"""Patch du proxy 8190 : une video telechargee peut REPRENDRE apres une coupure (Manga Studio v2.7.0, 23/09/2026).

`serve_manga_video` servait deja des plages (Range, 206) mais sans ETag ni Last-Modified : le gestionnaire de
telechargement d'Android ne peut alors pas savoir si le fichier a change et repart de zero (ou echoue) apres une
coupure -- lecon payee sur Telegramme Video le 16/08 (`reference_telechargement_reprenable_etag`). Une video se
REFAIT sous le meme nom : l'ETag (taille + date) change donc a chaque nouvelle fabrication, et If-Range qui ne
correspond plus renvoie le fichier ENTIER (200) au lieu d'un morceau du nouveau colle a l'ancien.
Rejouable : python patch_video_etag.py <chemin du proxy>.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "v2.7.0 : ETag video" in s:
    print("deja patche")
    sys.exit(0)


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


rep('''        taille = os.path.getsize(full)
        m = re.match(r"bytes=(\\d*)-(\\d*)$", (self.headers.get("Range") or "").strip())''',
    '''        taille = os.path.getsize(full)
        st = os.stat(full)                                   # v2.7.0 : ETag video -- reprise d'un telechargement coupe
        etag = '"v%x-%x"' % (st.st_size, int(st.st_mtime))
        modif = formatdate(st.st_mtime, usegmt=True)
        plage = (self.headers.get("Range") or "").strip()
        si = (self.headers.get("If-Range") or "").strip()
        if plage and si and si not in (etag, modif):
            plage = ""                                       # le fichier a change : on renvoie TOUT, jamais un melange
        m = re.match(r"bytes=(\\d*)-(\\d*)$", plage)''')
rep('''            self.send_header("Cache-Control", "no-cache")        # une video se REFAIT sous le meme nom''',
    '''            self.send_header("Cache-Control", "no-cache")        # une video se REFAIT sous le meme nom
            self.send_header("ETag", etag); self.send_header("Last-Modified", modif)''')
if "from email.utils import formatdate" not in s:
    rep("from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer",
        "from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer\nfrom email.utils import formatdate  # v2.7.0")
open(p, "w", encoding="utf-8").write(s)
print("patche")
