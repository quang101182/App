# -*- coding: utf-8 -*-
"""Patch du proxy 8190 : SITES VALIDES pour la capture (Manga Studio v2.3.3, etape 19).

GET /manga/sites -> le contenu de App/manga-studio/manga-fetch/sites.json (fichier VERSIONNE : la liste ne vit pas
en dur dans le HTML ; un site y entre apres une capture reelle + un test d'enchainement, cf. son champ « _lire »).
Lecture seule, aucun secret. Rejouable : python patch_sites.py <chemin du proxy>.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "def manga_sites(" in s:
    print("deja patche")
    sys.exit(0)


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


rep('''def manga_fetch_status():''',
    '''def manga_sites():
    """v2.3.3 : la liste des sites valides (manga-fetch/sites.json, versionne)."""
    try:
        with open(os.path.join(MANGA_ROOT, "manga-fetch", "sites.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        return {"error": "sites.json illisible : %s" % e, "sites": []}


def manga_fetch_status():''')

rep('''        elif self.path.split("?", 1)[0] == "/manga/fetch_status":''',
    '''        elif self.path.split("?", 1)[0] == "/manga/sites":            # Manga Studio v2.3.3
            self._json(200, manga_sites())
        elif self.path.split("?", 1)[0] == "/manga/fetch_status":''')

open(p, "w", encoding="utf-8").write(s)
print("ok")
