# -*- coding: utf-8 -*-
"""Manga Studio v2.81.0 -- mode « DIALOGUES » cote serveur (ROADMAP § 4-septdecies, etape D3 ; maquette_dialogues_v2 validee
par Quang le 26/09/2026 23h58). SEPARE de la narration : ses routes, son suivi, ses fichiers (<chap>/dialogues/,
<serie>/dialogues_distribution.json), jamais narration/ ni traduction/.

Routes GET  /manga/dialogues?d=               etat du chapitre (doc, progression, distribution du manga, traduit ?)
            /manga/dialogues_distribution?serie=
            /manga/el_solde[?force=1]         solde ElevenLabs (cache 20 s, modele runpod_balance)
            /manga/el_voix                    catalogue des voix ElevenLabs (cache 1 h)
       POST /manga/dialogues_lancer {d, action: preparer|voix, pages}
            /manga/dialogues_arreter {d}      les voix deja faites sont gardees
            /manga/dialogues_maj {d, corrections: [{cle, texte|qui|ton|lire|annuler}]}
            /manga/dialogues_distribution {serie, persos: [{nom, voix_el, couleur, expressivite, vitesse, renomme}],
                                           ajouter: {nom, genre, voix_el}, narrateur: {...}, tons}
            /manga/dialogues_ecouter {d, cle, qui?, ton?}  -> {fichier} (a lire par /manga/source_file)
Suivi : manga_activite() connait le type « dialogues » ; manga_costs() compte la preparation (dollars) et rend a part
« elevenlabs » (credits : aujourd'hui / mois / total).
Rejouable : python patch_dialogues.py <chemin du proxy>"""
import io, sys

P = sys.argv[1]
s = io.open(P, encoding="utf-8", newline="").read()
if "MANGA_DIALOGUES =" in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"


def rep(a, b, n=1):
    global s
    a, b = a.replace("\n", NL), b.replace("\n", NL)
    assert s.count(a) == n, ("ancre", s.count(a), a[:80])
    s = s.replace(a, b)


BLOC = '''# --- MODE DIALOGUES (Manga Studio v2.81.0, ROADMAP 4-septdecies) : une voix par personnage, ElevenLabs v3 ---------------
# Separe de la narration. Aucun moteur de secours : quota ElevenLabs epuise = le script s'arrete (code 4), l'app le dit.
MANGA_DIALOGUES = os.path.join(MANGA_ROOT, "scripts", "dialogues.py")
_DLG_JOBS = {}                                    # chapitre -> Popen
_EL_SOLDE = {"t": 0.0, "v": None}
_EL_VOIX = {"t": 0.0, "v": None}
_RE_DLG_PAGES = re.compile(r"^\\d{1,4}(-\\d{1,4})?$")
_RE_COULEUR = re.compile(r"^#[0-9a-fA-F]{6}$")
_RE_VOIX_EL = re.compile(r"^[A-Za-z0-9]{10,40}$")


def _dlg_lire(f):
    try:
        with open(f, encoding="utf-8") as h:
            return json.load(h)
    except Exception:
        return None


def _dlg_ecrire(f, doc):
    tmp = f + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as h:
        json.dump(doc, h, ensure_ascii=False, indent=1)
    os.replace(tmp, f)


def _dlg_base(d):
    base = _manga_src_safe(d)
    if not base or not os.path.isfile(os.path.join(base, "manifest.json")):
        return None
    return base


def _dlg_vivant(d):
    p = _DLG_JOBS.get(d)
    if p is not None and p.poll() is None:
        return True
    base = _dlg_base(d)
    pr = _dlg_lire(os.path.join(base, "dialogues", "progress.json")) if base else None
    return bool(pr and _run_vivant(pr))


def manga_dialogues(d):
    base = _dlg_base(d)
    if not base:
        return None
    dd = os.path.join(base, "dialogues")
    return {"d": d, "traduit": os.path.isfile(os.path.join(base, "traduction", "fr", "traduction.json")),
            "doc": _dlg_lire(os.path.join(dd, "dialogues.json")), "progress": _dlg_lire(os.path.join(dd, "progress.json")),
            "en_cours": _dlg_vivant(d), "distribution": _dlg_lire(os.path.join(os.path.dirname(base), "dialogues_distribution.json"))}


def manga_dialogues_lancer(d, action, pages=""):
    if action not in ("preparer", "voix"):
        return {"error": "action inconnue"}
    if pages and not _RE_DLG_PAGES.match(pages):
        return {"error": "plage de pages invalide"}
    base = _dlg_base(d)
    if not base:
        return {"error": "chapitre introuvable"}
    dd = os.path.join(base, "dialogues")
    if action == "preparer" and not os.path.isfile(os.path.join(base, "traduction", "fr", "traduction.json")):
        return {"error": "traduis d'abord ce chapitre en français"}
    if action == "voix" and not os.path.isfile(os.path.join(dd, "dialogues.json")):
        return {"error": "prépare d'abord les dialogues de ce chapitre"}
    if _dlg_vivant(d):
        return {"error": "les dialogues de ce chapitre sont déjà en cours"}
    if not os.path.isfile(MANGA_PY) or not os.path.isfile(MANGA_DIALOGUES):
        return {"error": "venv kohya ou dialogues.py introuvable"}
    os.makedirs(dd, exist_ok=True)
    try:
        os.remove(os.path.join(dd, "progress.json"))     # un vieux progres ferait croire a un run en cours
    except Exception:
        pass
    cmd = [MANGA_PY, MANGA_DIALOGUES, action, d] + (["--pages", pages] if pages else [])
    lg = open(os.path.join(dd, "run.log"), "w", encoding="utf-8")
    _DLG_JOBS[d] = subprocess.Popen(cmd, stdout=lg, stderr=lg, cwd=os.path.dirname(MANGA_DIALOGUES),
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return {"ok": True}


def manga_dialogues_arreter(d):
    base = _dlg_base(d)
    if not base:
        return {"error": "chapitre introuvable"}
    pf = os.path.join(base, "dialogues", "progress.json")
    pr = _dlg_lire(pf) or {}
    p = _DLG_JOBS.get(d)
    pid = p.pid if (p is not None and p.poll() is None) else pr.get("pid")
    if not pid or not _pid_vivant(pid):
        return {"ok": True, "deja": True}
    subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True,
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    pr.update(fini=True, etape="arrete", arret="arrêté à ta demande", t=time.time())
    try:
        _dlg_ecrire(pf, pr)
    except Exception:
        pass
    return {"ok": True}


def manga_dialogues_maj(data):
    """Corrections de Quang (texte, qui, ton, lire) : gardees dans « corrige » -- une nouvelle preparation ne les ecrase pas.
    La page traduite n'est JAMAIS touchee (decision 26/09)."""
    d = str(data.get("d") or "")
    base = _dlg_base(d)
    if not base:
        return {"error": "chapitre introuvable"}
    if _dlg_vivant(d):
        return {"error": "attends la fin du travail en cours sur ce chapitre"}
    f = os.path.join(base, "dialogues", "dialogues.json")
    doc = _dlg_lire(f)
    if not doc:
        return {"error": "chapitre pas encore préparé"}
    par = {x["cle"]: x for x in doc.get("repliques") or []}
    n = 0
    for c in (data.get("corrections") or [])[:500]:
        x = par.get(str(c.get("cle") or ""))
        if not x:
            continue
        if c.get("annuler"):
            x["corrige"] = {}
            x["texte"] = x.get("texte_origine", x.get("texte"))
            n += 1
            continue
        for k in ("texte", "qui", "ton", "lire"):
            if k not in c:
                continue
            v = c[k]
            if k == "lire":
                v = bool(v)
            elif not isinstance(v, str) or len(v) > 600:
                continue
            else:
                v = v.strip()
            x[k] = v
            x.setdefault("corrige", {})[k] = v
            n += 1
    doc["maj"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    _dlg_ecrire(f, doc)
    return {"ok": True, "n": n}


def manga_dialogues_distribution(serie, data=None):
    """La distribution du MANGA (commune a tous ses chapitres). POST : voix, couleur, expressivite, vitesse, renommer (l'ancien
    nom devient un alias et les chapitres deja prepares suivent), ajouter, narrateur, tons."""
    if not re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,120}$", serie or ""):
        return {"error": "série invalide"}
    sd = _manga_src_safe(serie)
    if not sd or not os.path.isdir(sd):
        return {"error": "série introuvable"}
    f = os.path.join(sd, "dialogues_distribution.json")
    doc = _dlg_lire(f) or {"version": 1, "persos": [], "tons": True, "balises": {},
                           "narrateur": {"nom": "Narrateur", "voix_el": "JBFqnCBsd6RMkjVDRZzb", "lire": False,
                                         "expressivite": 1, "vitesse": 1.05, "couleur": "#9aa6b8"}}
    if data is None:
        return {"distribution": doc}
    persos = {p["nom"]: p for p in doc.get("persos") or []}
    renommes = {}

    def regler(p, m):
        if _RE_VOIX_EL.match(str(m.get("voix_el") or "")):
            p["voix_el"] = m["voix_el"]
        if _RE_COULEUR.match(str(m.get("couleur") or "")):
            p["couleur"] = m["couleur"]
        if "expressivite" in m:
            p["expressivite"] = max(0, min(2, int(m["expressivite"])))
        if "vitesse" in m:
            p["vitesse"] = round(max(0.7, min(1.2, float(m["vitesse"]))), 2)
        if "lire" in m:
            p["lire"] = bool(m["lire"])
    for m in (data.get("persos") or [])[:100]:
        p = persos.get(str(m.get("nom") or ""))
        if not p:
            continue
        regler(p, m)
        nv = str(m.get("renomme") or "").strip()[:40]
        if nv and nv != p["nom"] and nv not in persos and nv.lower() not in ("narrateur", "inconnu"):
            p["alias"] = list(dict.fromkeys((p.get("alias") or []) + [p["nom"]]))
            renommes[p["nom"]] = nv
            p["nom"] = nv
    aj = data.get("ajouter") or {}
    nom = str(aj.get("nom") or "").strip()[:40]
    if nom and nom not in persos and nom.lower() not in ("narrateur", "inconnu"):
        pris = {p.get("couleur") for p in doc["persos"]}
        pal = ["#ff5fa2", "#ffb347", "#6fb8ff", "#b58cff", "#5fe3a1", "#ff7a5c", "#f5e663", "#4fd6e8", "#e88aff", "#c7a17a"]
        p = {"nom": nom, "alias": [], "genre": str(aj.get("genre") or "?")[:10], "age": "", "fiche": "", "voix_el": None,
             "expressivite": 1, "vitesse": 1.1, "couleur": next((c for c in pal if c not in pris), pal[0])}
        regler(p, aj)
        doc["persos"].append(p)
    if isinstance(data.get("narrateur"), dict):
        regler(doc["narrateur"], data["narrateur"])
    if "tons" in data:
        doc["tons"] = bool(data["tons"])
    _dlg_ecrire(f, doc)
    if renommes:                                     # les chapitres deja prepares suivent le nouveau nom
        for ch in os.listdir(sd):
            fc = os.path.join(sd, ch, "dialogues", "dialogues.json")
            c = _dlg_lire(fc)
            if not c:
                continue
            for x in c.get("repliques") or []:
                if x.get("qui") in renommes:
                    x["qui"] = renommes[x["qui"]]
                if (x.get("corrige") or {}).get("qui") in renommes:
                    x["corrige"]["qui"] = renommes[x["corrige"]["qui"]]
            _dlg_ecrire(fc, c)
    return {"ok": True, "distribution": doc, "renommes": renommes}


def manga_dialogues_ecouter(data):
    d = str(data.get("d") or "")
    base = _dlg_base(d)
    if not base:
        return {"error": "chapitre introuvable"}
    cle = str(data.get("cle") or "")
    if not re.match(r"^\\d{1,4}-\\d{1,4}$", cle):
        return {"error": "réplique invalide"}
    cmd = [MANGA_PY, MANGA_DIALOGUES, "ecouter", d, "--cle", cle]
    if data.get("qui"):
        cmd += ["--qui", str(data["qui"])[:40]]
    if data.get("ton") is not None:
        cmd += ["--ton", str(data["ton"])[:80]]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=150,
                           cwd=os.path.dirname(MANGA_DIALOGUES), creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        out = json.loads((r.stdout or "").strip().splitlines()[-1])
    except Exception as e:
        return {"error": "écoute impossible : " + str(e)[:160]}
    if out.get("fichier"):
        out["chemin"] = d + "/" + out["fichier"]
    return out


def _el_get(path):
    req = urllib.request.Request(GATEWAY + path, headers={"Authorization": "Bearer " + SECRET, "User-Agent": "manga-studio/el"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def manga_el_solde(force=False):
    if not force and _EL_SOLDE["v"] and time.time() - _EL_SOLDE["t"] < 20:
        return _EL_SOLDE["v"]
    try:
        s_ = _el_get("/api/elevenlabs/v1/user/subscription")
        lim, uti = int(s_.get("character_limit") or 0), int(s_.get("character_count") or 0)
        v = {"ok": True, "utilises": uti, "limite": lim, "restants": max(0, lim - uti), "forfait": s_.get("tier"),
             "renouvellement": s_.get("next_character_count_reset_unix")}
    except Exception as e:
        v = {"ok": False, "error": "solde ElevenLabs illisible : " + str(e)[:120]}
    _EL_SOLDE.update(t=time.time(), v=v)
    return v


def manga_el_voix():
    if _EL_VOIX["v"] and time.time() - _EL_VOIX["t"] < 3600:
        return _EL_VOIX["v"]
    try:
        out = []
        for x in _el_get("/api/elevenlabs/v1/voices").get("voices") or []:
            lb = x.get("labels") or {}
            n = x.get("name") or ""
            out.append({"id": x.get("voice_id"), "nom": n.split(" - ")[0].strip(), "genre": lb.get("gender") or "?",
                        "age": lb.get("age") or "?", "desc": (n.split(" - ", 1)[1] if " - " in n else "") or lb.get("descriptive") or ""})
        v = {"ok": True, "voix": out}
    except Exception as e:
        v = {"ok": False, "error": str(e)[:160], "voix": []}
    _EL_VOIX.update(t=time.time(), v=v)
    return v


def _credits_el(lignes):
    auj, mois = time.strftime("%Y-%m-%d"), time.strftime("%Y-%m")
    t = {"aujourdhui": 0, "mois": 0, "total": 0}
    for e in lignes:
        c = int(e.get("credits") or 0)
        t["total"] += c
        if (e.get("t") or "").startswith(mois): t["mois"] += c
        if (e.get("t") or "").startswith(auj): t["aujourdhui"] += c
    return t


'''
rep("def manga_activite():\n", BLOC + "def manga_activite():\n")

# activite : le type « dialogues »
rep('''            d = se + "/" + ch
            nd, td = os.path.join(sd, ch, "narration"), os.path.join(sd, ch, "traduction")''',
    '''            d = se + "/" + ch
            _gp = _dlg_lire(os.path.join(sd, ch, "dialogues", "progress.json"))      # v2.81.0 : mode Dialogues
            if _gp and _run_vivant(_gp):
                out.append({"type": "dialogues", "d": d, "titre": se, "chapitre": ch[3:], "etape": _gp.get("etape"),
                            "fait": _gp.get("fait"), "total": _gp.get("total")})
            nd, td = os.path.join(sd, ch, "narration"), os.path.join(sd, ch, "traduction")''')

# couts : la preparation (dollars) + les credits ElevenLabs a part
rep('''    reg = os.path.join(racine, "_depenses.jsonl")
    if os.path.isfile(reg):''', '''    _cred = []                                   # v2.81.0 : credits ElevenLabs (mode Dialogues), jamais melanges aux dollars
    reg = os.path.join(racine, "_depenses.jsonl")
    if os.path.isfile(reg):''')
rep('''                "essai": "cout_essai"}''', '''                "essai": "cout_essai", "dialogues": "cout_dialogues"}''')
rep('''                ty = e.get("type")
                if ty not in cles:
                    continue''', '''                ty = e.get("type")
                if e.get("credits"):
                    _cred.append(e)
                if ty not in cles:
                    continue''')
rep('''              "essais et bancs": "cout_essai"}''', '''              "essais et bancs": "cout_essai",
              "dialogues": "cout_dialogues"}                                               # v2.81.0''')
rep('''"par_etape": arr(par_etape), "par_moteur": arr(par_moteur), "runs": lignes[:40], "n": len(lignes)}''',
    '''"par_etape": arr(par_etape), "par_moteur": arr(par_moteur), "runs": lignes[:40], "n": len(lignes),
            "elevenlabs": _credits_el(_cred)}''')

# routes GET
rep('''        elif self.path.split("?", 1)[0] == "/manga/costs":
            self._json(200, manga_costs())''', '''        elif self.path.split("?", 1)[0] == "/manga/costs":
            self._json(200, manga_costs())
        elif self.path.split("?", 1)[0] == "/manga/dialogues":             # Manga Studio v2.81.0
            _r = manga_dialogues((parse_qs(urlparse(self.path).query).get("d") or [""])[0])
            if _r is None: self._json(404, {"error": "chapitre introuvable"})
            else: self._json(200, _r)
        elif self.path.split("?", 1)[0] == "/manga/dialogues_distribution":
            self._json(200, manga_dialogues_distribution((parse_qs(urlparse(self.path).query).get("serie") or [""])[0]))
        elif self.path.split("?", 1)[0] == "/manga/el_solde":
            self._json(200, manga_el_solde(bool((parse_qs(urlparse(self.path).query).get("force") or [""])[0])))
        elif self.path.split("?", 1)[0] == "/manga/el_voix":
            self._json(200, manga_el_voix())''')

# routes POST
rep('''            elif self.path == "/manga/interrompre":            # Manga Studio v2.12.0 (4-undecies)''',
    '''            elif self.path == "/manga/dialogues_lancer":       # Manga Studio v2.81.0 (mode Dialogues)
                self._json(200, manga_dialogues_lancer(str(data.get("d") or ""), str(data.get("action") or ""),
                                                       str(data.get("pages") or "")))
            elif self.path == "/manga/dialogues_arreter":
                self._json(200, manga_dialogues_arreter(str(data.get("d") or "")))
            elif self.path == "/manga/dialogues_maj":
                self._json(200, manga_dialogues_maj(data))
            elif self.path == "/manga/dialogues_distribution":
                self._json(200, manga_dialogues_distribution(str(data.get("serie") or ""), data))
            elif self.path == "/manga/dialogues_ecouter":
                self._json(200, manga_dialogues_ecouter(data))
            elif self.path == "/manga/interrompre":            # Manga Studio v2.12.0 (4-undecies)''')

io.open(P, "w", encoding="utf-8", newline="").write(s)
print("proxy patche")
