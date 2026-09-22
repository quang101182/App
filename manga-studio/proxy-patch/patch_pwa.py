# -*- coding: utf-8 -*-
"""Patch du proxy 8190 : Manga Studio INSTALLABLE (PWA, v1.95.0, 22/09/2026, etape 14 -- demande Quang 08h36).

GET /manga/manifest.webmanifest, /manga/sw.js, /manga/icon-*.png -> fichiers de App/manga-studio/pwa/, PUBLICS
(avant le controle du jeton) : le navigateur charge le manifeste et ses icones SANS jeton ni cookie (spec :
credentials omit). Ils ne contiennent aucun secret. Liste FERMEE de noms : rien d'autre de pwa/ n'est servi.
Rejouable : python patch_pwa.py <chemin du proxy>.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "MANGA_PWA" in s:
    print("deja patche")
    sys.exit(0)


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


rep('''        if self.path.split("?", 1)[0] in ("/manga", "/manga/", "/manga.html"):
            self.serve_manga_html(); return''',
    '''        if self.path.split("?", 1)[0] in ("/manga", "/manga.html"):     # v1.95.0 : HORS de la portee PWA
            self.send_response(302); self._cors()                              # (/manga/) -> Chrome n'y proposait
            self.send_header("Location", "/manga/" + (("?" + self.path.split("?", 1)[1]) if "?" in self.path else ""))
            self.send_header("Content-Length", "0"); self.end_headers(); return  # pas l'installation
        if self.path.split("?", 1)[0] in ("/manga", "/manga/", "/manga.html"):
            self.serve_manga_html(); return
        if self.path.split("?", 1)[0] in MANGA_PWA:                        # Manga Studio v1.95.0 : PWA, PUBLIC
            self.serve_manga_pwa(MANGA_PWA[self.path.split("?", 1)[0]]); return''')

rep('''    def serve_manga_html(self):''',
    '''    def serve_manga_pwa(self, nom):
        """v1.95.0 : manifeste, service worker, icones (App/manga-studio/pwa/). Aucun secret dedans."""
        f = os.path.join(MANGA_ROOT, "pwa", nom)
        if not os.path.isfile(f):
            self._json(404, {"error": "not found"}); return
        with open(f, "rb") as fh: data = fh.read()
        ct = {".webmanifest": "application/manifest+json", ".js": "text/javascript; charset=utf-8",
              ".png": "image/png"}[os.path.splitext(nom)[1]]
        self.send_response(200); self._cors()
        self.send_header("Content-Type", ct)
        if nom == "sw.js":
            self.send_header("Service-Worker-Allowed", "/manga/")
            self.send_header("Cache-Control", "no-cache")
        else:
            self.send_header("Cache-Control", "public, max-age=3600")
        self.send_header("Content-Length", str(len(data))); self.end_headers()
        self.wfile.write(data)

    def serve_manga_html(self):''')

rep('''MANGA_PREC = os.path.join(MANGA_ROOT, "scripts", "precedemment.py")''',
    '''MANGA_PREC = os.path.join(MANGA_ROOT, "scripts", "precedemment.py")
MANGA_PWA = {"/manga/" + n: n for n in ("manifest.webmanifest", "sw.js", "icon-192.png", "icon-512.png",
                                         "icon-maskable-512.png")}                      # v1.95.0''')

open(p, "w", encoding="utf-8").write(s)
print("patch pwa OK")
