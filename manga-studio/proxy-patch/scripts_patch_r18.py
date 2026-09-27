# -*- coding: utf-8 -*-
"""R18 phase 1 (27/09 -- Quang 13h13 : « les voix d'homme en general, la vitesse de 1 est trop lente, voire 1,10 […] un bouton
pour indiquer que c'est la valeur par defaut que je souhaite desormais […] tu separes ces valeurs entre la principale et la
secondaire ») -- scripts :
- reglages.py 1.4.0 : « defauts » {cle: nombre} dans _reglages.json de CHAQUE instance (donc separes principale / secondaire) ;
  ecrire(defauts=...) FUSIONNE (une cle a la fois) ; cles connues seulement, nombres bornes.
- dialogues.py 1.16.0 : un NOUVEAU personnage recoit la vitesse de diction et la vitesse d'ecoute par defaut de son genre
  (homme / femme ; sinon celles d'avant : 1,1 et 1).
Rejouable : python scripts_patch_r18.py <dossier scripts>"""
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
    ('VERSION = "1.3.0"', 'VERSION = "1.4.0"   # 1.4.0 (R18, 27/09) : valeurs PAR DEFAUT (par instance) : « defauts »'),
    ('''          "flou_discretion": True}                       # v1.3.0 : flou de la secondaire hors focus (Quang 25/09 : optionnel)''',
     '''          "flou_discretion": True,                       # v1.3.0 : flou de la secondaire hors focus (Quang 25/09 : optionnel)
          "defauts": {}}                                 # v1.4.0 (R18) : {cle: nombre} -- voir DEFAUTS_BORNES
# v1.4.0 (R18) : les valeurs par defaut reglables (« ⭐ » dans l'app), bornees. voix_<h|f|n>_<vitesse|ecoute> : personnages
# (homme, femme, narrateur) ; les curseurs de lecture s'ajoutent ici (phase 2). Une cle inconnue est refusee.
DEFAUTS_BORNES = {"voix_h_vitesse": (0.7, 1.2), "voix_f_vitesse": (0.7, 1.2), "voix_n_vitesse": (0.7, 1.2),
                  "voix_h_ecoute": (0.7, 1.5), "voix_f_ecoute": (0.7, 1.5), "voix_n_ecoute": (0.7, 1.5)}'''),
    ('''    r["flou_discretion"] = r.get("flou_discretion") is not False       # v1.3.0 : absent = OUI (comportement d'avant)
    return r''', '''    r["flou_discretion"] = r.get("flou_discretion") is not False       # v1.3.0 : absent = OUI (comportement d'avant)
    d = r.get("defauts") if isinstance(r.get("defauts"), dict) else {}      # v1.4.0 : on ne garde que le connu et le borne
    r["defauts"] = {k: v for k, v in d.items() if k in DEFAUTS_BORNES and isinstance(v, (int, float))
                    and DEFAUTS_BORNES[k][0] <= v <= DEFAUTS_BORNES[k][1]}
    return r'''),
    ('''    r = _brut()
    r.update({k: v for k, v in kw.items() if k in DEFAUT})''', '''    r = _brut()
    if "defauts" in kw:                                  # v1.4.0 (R18) : FUSION, une cle a la fois, jamais tout remplace
        d = kw.pop("defauts")
        if not isinstance(d, dict):
            raise ValueError("defauts : {cle: nombre}")
        for k, v in d.items():
            if k not in DEFAUTS_BORNES:
                raise ValueError("defaut inconnu : %s" % k)
            if v is None:
                r["defauts"].pop(k, None); continue
            lo, hi = DEFAUTS_BORNES[k]
            r["defauts"][k] = round(max(lo, min(hi, float(v))), 2)
    r.update({k: v for k, v in kw.items() if k in DEFAUT})'''),
    ('''def sur_pc():''', '''def defaut(cle, sinon):
    """v1.4.0 (R18) : la valeur par defaut reglee pour cette instance, sinon `sinon`."""
    return _brut()["defauts"].get(cle, sinon)


def sur_pc():'''),
], "def defaut(cle, sinon)")

patcher("dialogues.py", [
    ('VERSION = "1.15.0"', 'VERSION = "1.16.0"  # 1.16.0 (R18, 27/09) : nouveau personnage = vitesses PAR DEFAUT de son genre (reglages de l\'instance) ;'),
    ('''        p = {"nom": nom, "alias": [], "genre": n.get("genre") or "?", "age": n.get("age") or "", "fiche": n.get("fiche") or "",
             "voix_el": v, "expressivite": 1, "vitesse": 1.1, "couleur": couleur}''',
     '''        gk = {"homme": "h", "femme": "f"}.get((n.get("genre") or "").lower())      # 1.16.0 (R18) : defauts du genre
        p = {"nom": nom, "alias": [], "genre": n.get("genre") or "?", "age": n.get("age") or "", "fiche": n.get("fiche") or "",
             "voix_el": v, "expressivite": 1, "vitesse": defaut_reglage("voix_%s_vitesse" % gk, 1.1) if gk else 1.1,
             "couleur": couleur}
        ec = defaut_reglage("voix_%s_ecoute" % gk, 1) if gk else 1
        if ec != 1:
            p["ecoute"] = ec'''),
    ('''def fusionner_distribution(distrib, nouveaux, cat):''', '''def defaut_reglage(cle, sinon):
    """1.16.0 (R18) : valeur par defaut de l'instance (reglages.py, meme MANGA_SOURCES_DIR) ; `sinon` si illisible."""
    try:
        import reglages
        return reglages.defaut(cle, sinon)
    except Exception:
        return sinon


def fusionner_distribution(distrib, nouveaux, cat):'''),
], "def defaut_reglage(")
