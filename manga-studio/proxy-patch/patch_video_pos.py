# -*- coding: utf-8 -*-
"""Patch du proxy : POSITION DE REPRISE des videos (Manga Studio v2.68.0, maquette_lecteur_video_v1 validee 26/09/2026 11h05, D).

`sources/_bibliotheque.json` (un par application) gagne `videos_pos: {fichier: {pos, duree, t}}` -- commun PC + telephone.
Action POST /manga/bibliotheque {action:"video_pos", slug, fichier, pos, duree}.
- `fichier` = le chemin relatif de la video tel que /manga/videos le donne (v.fichier) ; il doit commencer par « slug/ » ;
- pos < 5 s ou a moins de 10 s de la fin (video finie) -> l'entree est RETIREE (on repart du debut) ;
- au plus 500 entrees (les plus anciennes partent).
⚠ `_biblio_lire` doit RENDRE `videos_pos`, sinon toute autre action (masquer, lecture…) l'effacerait a la reecriture.
Rejouable : python patch_video_pos.py <chemin du proxy>.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "v2.68.0 : video_pos" in s:
    print("deja patche")
    sys.exit(0)


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


rep('''            "lectures": {k: v for k, v in (b.get("lectures") or {}).items()           # v2.62.0 : lectures
                         if isinstance(v, dict) and isinstance(v.get("d"), str)}}''',
    '''            "lectures": {k: v for k, v in (b.get("lectures") or {}).items()           # v2.62.0 : lectures
                         if isinstance(v, dict) and isinstance(v.get("d"), str)},
            "videos_pos": {k: v for k, v in (b.get("videos_pos") or {}).items()       # v2.68.0 : video_pos
                           if isinstance(v, dict) and isinstance(v.get("pos"), (int, float))}}''')
rep('''    if action not in ("masquer", "afficher", "ouverte", "lecture"):
        return {"error": "action inconnue"}''',
    '''    if action not in ("masquer", "afficher", "ouverte", "lecture", "video_pos"):
        return {"error": "action inconnue"}
    if action == "video_pos":                                                # v2.68.0 : la video DOIT etre de la serie
        fichier = str(data.get("fichier") or "").replace("\\\\", "/").strip("/")
        if not fichier.startswith(slug + "/") or ".." in fichier or len(fichier) > 300:
            return {"error": "video introuvable"}
        try:
            pos, duree = float(data.get("pos") or 0), float(data.get("duree") or 0)
        except (TypeError, ValueError):
            return {"error": "position invalide"}''')
rep('''            b["lectures"][slug] = n
        tmp = MANGA_BIBLIO + ".tmp"''',
    '''            b["lectures"][slug] = n
        elif action == "video_pos":
            if pos < 5 or (duree > 0 and pos > duree - 10):
                b["videos_pos"].pop(fichier, None)                           # debut ou fin : on repartira du debut
            else:
                b["videos_pos"][fichier] = {"pos": round(pos, 1), "duree": round(duree, 1), "t": int(time.time())}
                if len(b["videos_pos"]) > 500:
                    for k in sorted(b["videos_pos"], key=lambda k: b["videos_pos"][k].get("t", 0))[:len(b["videos_pos"]) - 500]:
                        b["videos_pos"].pop(k, None)
        tmp = MANGA_BIBLIO + ".tmp"''')
open(p, "w", encoding="utf-8").write(s)
print("patche")
