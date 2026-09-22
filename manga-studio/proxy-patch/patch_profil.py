# -*- coding: utf-8 -*-
"""Patch du proxy 8190 : PROFIL DE SERIE + « TOUT TRAITER » (Manga Studio v2.4.0, etape 27, phase 2).

La logique vit dans scripts/suivi_nuit.py v2.4.0 (profil(), profil_defaut(), plan_serie(), normaliser()) que le proxy
charge deja (_suivi_mod, recharge a chaque modification) ; ici, seulement les routes :
- GET  /manga/suivi?serie=   : + profil EFFECTIF (defaut general si la serie n'a pas le sien), a_profil, defaut,
                               plan (etapes par chapitre, sans detection de langue payante), estimation du « pas termine ».
- POST /manga/suivi          : le profil est normalise par suivi_nuit.normaliser (accepte « traduction »).
- GET/POST /manga/profil_defaut : lire ; {serie, action: "depuis_serie"} = « en faire mes reglages par defaut »
                               (sans « actif » : la nuit se regle serie par serie) ; {serie, action: "vers_serie"} =
                               « reprendre mes defauts » (garde « actif » de la serie).
- POST /manga/suivi_lancer   : + {chapitres: [d...], refaire} -> un LOT (--declencheur lot).
- GET  /manga/activite       : + un item « lot » tant que la chaine tourne (chapitre, etape, n/N).
Rejouable : python patch_profil.py <chemin du proxy>.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "def manga_profil_defaut(" in s:
    print("deja patche")
    sys.exit(0)


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


# --- GET /manga/suivi : profil effectif + plan
rep('''    prix, minutes = _SUIVI_TARIF.get(cfg.get("moteur") or "kimi", _SUIVI_TARIF["kimi"])
    return {"config": cfg, "file": file, "estimation": {"cout": round(pages * prix, 2), "minutes": round(pages * minutes)},
            "passage": etat, "journal": jr[-30:]}''',
    '''    # v2.4.0 : le PROFIL effectif (defaut general si la serie n'a pas le sien) et le PLAN de chaque chapitre
    try:
        profil, a_profil = m.profil(serie)
        plan = m.plan_serie(serie, cfg=profil)
        plan_refaire = m.plan_serie(serie, cfg=profil, refaire=True)     # l'estimation quand « refaire » est coche
        defaut = m.profil_defaut()
    except Exception as e:
        return {"error": "profil illisible : %s" % str(e)[:200]}
    afaire = [x for x in plan if x["a_faire"]]
    return {"config": profil, "a_profil": a_profil, "defaut": defaut, "file": file, "plan": plan,
            "refaire": {x["d"]: {"cout": x["cout"], "minutes": x["minutes"]} for x in plan_refaire},
            "estimation": {"cout": round(sum(x["cout"] for x in afaire), 2), "minutes": round(sum(x["minutes"] for x in afaire)),
                           "chapitres": len(afaire)},
            "passage": etat, "journal": jr[-30:]}''')

# --- POST /manga/suivi : profil normalise (accepte « traduction »)
rep('''    rv = data.get("reglages_video") or {}
    cfg = {"actif": bool(data.get("actif")), "voix": voix, "moteur": data.get("moteur") if data.get("moteur") in _SUIVI_TARIF else "kimi",
           "karaoke": bool(data.get("karaoke", True)),
           "precedemment": bool(data.get("precedemment", True)), "video": bool(data.get("video")),
           "reglages_video": {k: rv.get(k) for k in ("vitesse", "sous", "karaoke", "musique", "volume", "pages", "precedemment")},
           "maj": time.strftime("%Y-%m-%dT%H:%M:%S")}''',
    '''    cfg = _suivi_mod().normaliser(dict(data, voix=voix))          # v2.4.0 : + « traduction », valeurs bornees
    cfg["maj"] = time.strftime("%Y-%m-%dT%H:%M:%S")''')

# --- defaut general
rep('''def manga_suivi_lancer(data):''',
    '''def manga_profil_defaut(data=None):
    """v2.4.0 : les reglages par defaut de toute NOUVELLE serie (sources/_profil_defaut.json)."""
    m = _suivi_mod()
    if not data:
        return {"defaut": m.profil_defaut()}
    serie, action = data.get("serie") or "", data.get("action") or ""
    sd = _manga_src_safe(serie) if _RE_SERIE.match(serie) else None
    if not sd or not os.path.isdir(sd):
        return {"error": "serie introuvable"}
    if action == "depuis_serie":
        d = dict(m.profil(serie)[0], actif=False)                    # la nuit se regle serie par serie
        d["maj"], d["depuis"] = time.strftime("%Y-%m-%dT%H:%M:%S"), serie
        f = m.DEFAUT_F
    elif action == "vers_serie":
        d = dict(m.profil_defaut(), actif=m.profil(serie)[0].get("actif", False))
        d["maj"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        f = os.path.join(sd, "suivi.json")
    else:
        return {"error": "action inconnue"}
    tmp = f + ".tmp"
    with open(tmp, "w", encoding="utf-8") as h:
        json.dump(d, h, ensure_ascii=False, indent=1)
    os.replace(tmp, f)
    return {"ok": True, "defaut": m.profil_defaut(), "config": m.profil(serie)[0]}


def manga_suivi_lancer(data):''')

# --- lancement d'un LOT
rep('''    os.makedirs(m.DIR, exist_ok=True)
    lg = open(os.path.join(m.DIR, "runner.log"), "a", encoding="utf-8")
    cmd = [MANGA_PY, MANGA_SUIVI, "--declencheur", "bouton"] + (["--serie", serie] if serie else [])''',
    '''    os.makedirs(m.DIR, exist_ok=True)
    lg = open(os.path.join(m.DIR, "runner.log"), "a", encoding="utf-8")
    cmd = [MANGA_PY, MANGA_SUIVI, "--declencheur", "bouton"] + (["--serie", serie] if serie else [])
    if data.get("lot"):                                           # v2.4.0 : « Tout traiter » (serie ou selection)
        if not serie:
            return {"error": "serie obligatoire pour un lot"}
        ch = data.get("chapitres") or []
        if not isinstance(ch, list) or any(not isinstance(x, str) or not x.startswith(serie + "/ch_") or "," in x
                                           or ".." in x for x in ch):
            return {"error": "selection de chapitres invalide"}
        cmd = [MANGA_PY, MANGA_SUIVI, "--declencheur", "lot", "--serie", serie]
        if ch:
            cmd += ["--chapitres", ",".join(ch)]
        if data.get("refaire"):
            cmd.append("--refaire")''')

# --- activite : le lot en cours
rep('''    for (pd_, pm_), _pp in list(_PREC_JOBS.items()):          # v1.94.0 : les resumes en cours''',
    '''    try:                                                     # v2.4.0 : la chaine (lot ou nuit) en cours
        _m = _suivi_mod(); _e = _m.lire_etat()
        if _e.get("etat") == "en cours" and _m.pid_vivant(_e.get("pid")):
            _ec = _e.get("en_cours") or {}
            _d = _ec.get("d") or ""
            out.insert(0, {"type": "lot", "d": _d, "titre": (_d.split("/")[0] if _d else (_e.get("serie") or "")),
                           "chapitre": _ec.get("num") or "", "etape": _ec.get("etape"),
                           "fait": len(_e.get("fait") or []) + len(_e.get("erreurs") or []), "total": len(_e.get("file") or []),
                           "declencheur": _e.get("declencheur")})
    except Exception:
        pass
    for (pd_, pm_), _pp in list(_PREC_JOBS.items()):          # v1.94.0 : les resumes en cours''')

# --- routes
rep('''        elif self.path.split("?", 1)[0] == "/manga/suivi":                 # Manga Studio v1.98.0''',
    '''        elif self.path.split("?", 1)[0] == "/manga/profil_defaut":         # Manga Studio v2.4.0
            self._json(200, manga_profil_defaut())
        elif self.path.split("?", 1)[0] == "/manga/suivi":                 # Manga Studio v1.98.0''')
rep('''            elif self.path == "/manga/suivi_lancer":''',
    '''            elif self.path == "/manga/profil_defaut":          # Manga Studio v2.4.0
                self._json(200, manga_profil_defaut(data))
            elif self.path == "/manga/suivi_lancer":''')

open(p, "w", encoding="utf-8").write(s)
print("ok")
