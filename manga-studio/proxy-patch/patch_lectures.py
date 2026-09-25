# -*- coding: utf-8 -*-
"""Patch du proxy 8190 : historique de LECTURE par serie (Manga Studio v2.62.0, 25/09/2026, bouton « ▶ Reprendre »).

`sources/_bibliotheque.json` (un par application : la principale et la secondaire ont chacune leur MANGA_SOURCES_DIR,
donc leur historique -- la principale ne voit rien de la secondaire) gagne un champ
    lectures: {slug: {d, page, t, appareil, prec: {d, page} | absent}}
- d = « serie/ch_N » (le DERNIER chapitre ouvert dans ce manga), page = index 0.. de la page atteinte ;
- prec = le chapitre ouvert juste AVANT dans ce manga (dans un chapitre ouvert, « ▶ » y ramene d'un geste).
Action POST /manga/bibliotheque {action:"lecture", slug, d, page, appareil}. Un autre chapitre que `d` fait glisser
l'ancien dans `prec` ; le meme chapitre ne met a jour que la page, l'heure et l'appareil.
⚠ `_biblio_lire` doit RENDRE `lectures`, sinon « masquer » / « ouverte » l'effaceraient a la reecriture du fichier.
Rejouable : python patch_lectures.py <chemin du proxy>.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "v2.62.0 : lectures" in s:
    print("deja patche")
    sys.exit(0)


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


rep('''            "ouvertes": {k: v for k, v in (b.get("ouvertes") or {}).items() if isinstance(v, (int, float))}}''',
    '''            "ouvertes": {k: v for k, v in (b.get("ouvertes") or {}).items() if isinstance(v, (int, float))},
            "lectures": {k: v for k, v in (b.get("lectures") or {}).items()           # v2.62.0 : lectures
                         if isinstance(v, dict) and isinstance(v.get("d"), str)}}''')
rep('''    if action not in ("masquer", "afficher", "ouverte"):
        return {"error": "action inconnue"}''',
    '''    if action not in ("masquer", "afficher", "ouverte", "lecture"):
        return {"error": "action inconnue"}
    if action == "lecture":                                                  # v2.62.0 : le chapitre DOIT etre de la serie
        d = (data.get("d") or "").strip("/")
        if not d.startswith(slug + "/") or ".." in d or not os.path.isdir(_manga_src_safe(d) or ""):
            return {"error": "chapitre introuvable"}
        try:
            page = max(0, min(9999, int(data.get("page") or 0)))
        except (TypeError, ValueError):
            page = 0
        appareil = re.sub(r"[^\\w\\s.-]", "", str(data.get("appareil") or ""))[:20]''')
rep('''        elif action == "ouverte":
            b["ouvertes"][slug] = int(time.time())''',
    '''        elif action == "ouverte":
            b["ouvertes"][slug] = int(time.time())
        elif action == "lecture":
            a = b["lectures"].get(slug) or {}
            n = {"d": d, "page": page, "t": int(time.time()), "appareil": appareil}
            if a.get("d") and a["d"] != d:
                n["prec"] = {"d": a["d"], "page": int(a.get("page") or 0)}
            elif a.get("prec"):
                n["prec"] = a["prec"]
            b["lectures"][slug] = n''')
open(p, "w", encoding="utf-8").write(s)
print("patche")
