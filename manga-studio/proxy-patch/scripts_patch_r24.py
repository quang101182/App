# -*- coding: utf-8 -*-
"""R24 (27/09 -- Quang 14h19 : « conserver les voix preferees, meme pour une nouvelle generation ou un nouveau manga, afin que
ce soit priorise ») -- scripts :
- reglages.py 1.6.0 : « voix_favorites » = liste d'ids de voix, PAR INSTANCE (principale / secondaire separees) ; ecrire
  accepte {"ajouter": id} / {"retirer": id} ou la liste entiere ; ids verifies, 40 au plus.
- dialogues.py 1.17.0 : la distribution AUTOMATIQUE met les voix PREFEREES en tete de son catalogue (marquees « ⭐ preferee »
  pour le modele) : un nouveau personnage recoit d'abord une preferee de son genre, puis une voix francaise.
Suppose scripts_patch_r18b.py et scripts_patch_r19.py. Rejouable : python scripts_patch_r24.py <dossier scripts>"""
import os, sys

D = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")


def patcher(nom, reps, marque):
    p = os.path.join(D, nom)
    s = open(p, encoding="utf-8", newline="").read()
    if marque in s:
        print(nom, ": deja applique"); return
    N = "\r\n" if "\r\n" in s else "\n"
    for a, b in reps:
        a, b = a.replace("\n", N), b.replace("\n", N)
        assert s.count(a) == 1, (nom, a[:70], s.count(a))
        s = s.replace(a, b)
    open(p, "w", encoding="utf-8", newline="").write(s)
    print(nom, ": ok")


patcher("reglages.py", [
    ('VERSION = "1.5.0"', 'VERSION = "1.6.0"   # 1.6.0 (R24) : voix PREFEREES (voix_favorites) ;'),
    ('''          "defauts": {}}                                 # v1.4.0 (R18) : {cle: nombre} -- voir DEFAUTS_BORNES''',
     '''          "defauts": {},                                 # v1.4.0 (R18) : {cle: nombre} -- voir DEFAUTS_BORNES
          "voix_favorites": []}                          # v1.6.0 (R24) : ids des voix preferees (en tete, choisies d'abord)'''),
    ('''    r["defauts"] = {k: v for k, v in d.items() if k in DEFAUTS_BORNES and isinstance(v, (int, float))
                    and DEFAUTS_BORNES[k][0] <= v <= DEFAUTS_BORNES[k][1]}
    return r''', '''    r["defauts"] = {k: v for k, v in d.items() if k in DEFAUTS_BORNES and isinstance(v, (int, float))
                    and DEFAUTS_BORNES[k][0] <= v <= DEFAUTS_BORNES[k][1]}
    f = r.get("voix_favorites") if isinstance(r.get("voix_favorites"), list) else []          # v1.6.0
    r["voix_favorites"] = [x for x in f if isinstance(x, str) and _ID_VOIX.match(x)][:40]
    return r'''),
    ('''def _brut():''', '''import re
_ID_VOIX = re.compile(r"^[A-Za-z0-9]{8,40}$")


def _brut():'''),
    ('''    r.update({k: v for k, v in kw.items() if k in DEFAUT})
    if r["mode"] not in ("cloud", "pc"):''', '''    if "voix_favorites" in kw:                           # v1.6.0 (R24) : {ajouter: id} / {retirer: id} / [ids]
        v = kw.pop("voix_favorites")
        if isinstance(v, dict):
            i = str(v.get("ajouter") or v.get("retirer") or "")
            if not _ID_VOIX.match(i):
                raise ValueError("voix inconnue")
            f = [x for x in r["voix_favorites"] if x != i]
            r["voix_favorites"] = ([i] + f)[:40] if v.get("ajouter") else f
        elif isinstance(v, list) and all(isinstance(x, str) and _ID_VOIX.match(x) for x in v):
            r["voix_favorites"] = list(dict.fromkeys(v))[:40]
        else:
            raise ValueError("voix_favorites : {ajouter|retirer: id} ou liste d'ids")
    r.update({k: v for k, v in kw.items() if k in DEFAUT})
    if r["mode"] not in ("cloud", "pc"):'''),
], "_ID_VOIX = re.compile")

patcher("dialogues.py", [
    ('VERSION = "1.16.0"', 'VERSION = "1.17.0"  # 1.17.0 (R24, 27/09) : voix PREFEREES en tete de la distribution automatique ;'),
    ('''    cat = voix_francaises() or catalogue_el()                  # 1.15.0 (R19) : 100 % francaises, sinon le compte''',
     '''    cat = voix_francaises() or catalogue_el()                  # 1.15.0 (R19) : 100 % francaises, sinon le compte
    cat = avec_preferees(cat)                                   # 1.17.0 (R24) : les PREFEREES d'abord'''),
    ('''def catalogue_el():''', '''def avec_preferees(cat):
    """1.17.0 (R24) : les voix PREFEREES de l'instance (reglages.voix_favorites) en tete, marquees pour le modele ; une preferee
    absente du catalogue (voix du compte) y est ajoutee depuis catalogue_el()."""
    try:
        import reglages
        fav = reglages._brut().get("voix_favorites") or []
    except Exception:
        fav = []
    if not fav:
        return cat
    tous = {v["id"]: v for v in cat}
    if any(i not in tous for i in fav):
        for v in catalogue_el():
            tous.setdefault(v["id"], v)
    tete = [dict(tous[i], desc="⭐ preferee de Quang -- " + (tous[i].get("desc") or ""), prefere=True) for i in fav if i in tous]
    return tete + [v for v in cat if v["id"] not in fav]


def catalogue_el():'''),
], "def avec_preferees(")
