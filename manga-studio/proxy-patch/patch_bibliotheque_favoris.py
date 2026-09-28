# -*- coding: utf-8 -*-
"""Manga Studio v3.5.7 -- FAVORIS (Quang 28/09 16h53 : « mettre en favori les mangas qui me plaisent pour les avoir en debut de
liste […] simple et rapide, principale et secondaire », chacune les siens) : /manga/bibliotheque garde « favoris » (liste de
slugs) dans le fichier de bibliotheque DE L'INSTANCE (donc separe principale / secondaire, commun a tous les appareils) ;
actions « favori » / « pas_favori ». Rejouable."""
import io, sys

P = sys.argv[1]
s = io.open(P, encoding="utf-8", newline="").read()
if '"pas_favori"' in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", NL), b.replace("\n", NL)
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %s" % (s.count(a), a[:70]))
    s = s.replace(a, b)


rep('''    return {"masquees": [x for x in b.get("masquees") or [] if isinstance(x, str)],''',
    '''    return {"masquees": [x for x in b.get("masquees") or [] if isinstance(x, str)],
            "favoris": [x for x in b.get("favoris") or [] if isinstance(x, str)],          # v3.5.7 : favoris (en tete de liste)''')
rep('''    if action not in ("masquer", "afficher", "ouverte", "lecture", "video_pos"):''',
    '''    if action not in ("masquer", "afficher", "ouverte", "lecture", "video_pos", "favori", "pas_favori"):''')
rep('''        if action == "masquer" and slug not in b["masquees"]:
            b["masquees"].append(slug)''', '''        if action == "masquer" and slug not in b["masquees"]:
            b["masquees"].append(slug)
        elif action == "favori" and slug not in b["favoris"]:                    # v3.5.7
            b["favoris"].append(slug)
        elif action == "pas_favori":
            b["favoris"] = [x for x in b["favoris"] if x != slug]''')
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
