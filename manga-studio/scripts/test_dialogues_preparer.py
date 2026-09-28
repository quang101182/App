# -*- coding: utf-8 -*-
"""Banc dialogues.py preparer (D1, ROADMAP 4-septdecies) -- HORS LIGNE : faux modele, faux catalogue, COPIE jetable de 3 pages
(OPM ch.6 p.5-7, dans un dossier temporaire : aucune donnee reelle touchee, aucun appel paye).
A. premiere preparation : distribution creee (2 persos, voix du bon genre, couleurs distinctes), 1 entree par bulle, contour
   reel sur les vraies bulles, « CHAIR DE POULE » et « ! » non lus, encart narrateur non lu par defaut, progress fini, depense notee
B. 2e preparation : aucun doublon dans la distribution ; alias « p1 » -> Fille-Moustique ; les CORRECTIONS de Quang gagnent
C. moderation : page 6 refusee, relais COUPE -> page a traiter + alerte ; relais ACTIF -> relue par kimi, 0 alerte
D. pas de traduction francaise -> arret code 3
E. MUTATIONS : alias ignore / corrections ecrasees -> le banc doit passer au ROUGE
Usage : python test_dialogues_preparer.py
"""
import importlib, json, os, re, shutil, sys, tempfile, types

HERE = os.path.dirname(os.path.abspath(__file__))
VRAI = os.path.expanduser(r"~\Documents\MangaStudio-donnees\sources\one-punch-man\ch_6")
T = tempfile.mkdtemp(prefix="banc_dialogues_")
os.environ.update(MANGA_SOURCES_DIR=T, MANGA_DEPENSES=os.path.join(T, "_depenses.jsonl"),
                  MANGA_ALERTES=os.path.join(T, "_alertes.json"), MANGA_REGLAGES=os.path.join(T, "_reglages.json"))
sys.path.insert(0, HERE)
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail)[:160] if detail else ""))


def copie():
    ch = os.path.join(T, "opm", "ch_6")
    shutil.rmtree(os.path.join(T, "opm"), ignore_errors=True)
    os.makedirs(os.path.join(ch, "traduction", "fr"))
    tr = json.load(open(os.path.join(VRAI, "traduction", "fr", "traduction.json"), encoding="utf-8"))
    tr["pages"] = [p for p in tr["pages"] if p["page"] in (5, 6, 7)]
    json.dump(tr, open(os.path.join(ch, "traduction", "fr", "traduction.json"), "w", encoding="utf-8"), ensure_ascii=False)
    for p in tr["pages"]:
        shutil.copy(os.path.join(VRAI, "traduction", "fr", p["file"]), os.path.join(ch, "traduction", "fr", p["file"]))
    for f in ("_alertes.json", "_depenses.jsonl", "_reglages.json"):
        try:
            os.remove(os.path.join(T, f))
        except OSError:
            pass
    # 1.29.0 (S16) : les sections A-H verifient que CHAQUE bulle a son entree (« ! » compris, marque non lu) -> petits cris LUS
    json.dump({"petits_cris": True}, open(os.environ["MANGA_REGLAGES"], "w", encoding="utf-8"))
    return ch


CAT = [{"id": "ADAM", "nom": "Adam", "genre": "male", "age": "middle_aged", "desc": "Dominant, Firm"},
       {"id": "LILY", "nom": "Lily", "genre": "female", "age": "middle_aged", "desc": "Velvety Actress"},
       {"id": "BELLA", "nom": "Bella", "genre": "female", "age": "middle_aged", "desc": "Warm"},
       {"id": "JBFqnCBsd6RMkjVDRZzb", "nom": "George", "genre": "male", "age": "middle_aged", "desc": "Storyteller"}]
ETAT = {"qui5": "Fille-Moustique", "refuse": set(), "appels": []}


def charger(src_patch=None):
    """Charge dialogues.py (eventuellement MUTE) comme module neuf, avec faux modele et faux catalogue."""
    import narrate_chapter as nc, moderation as mod
    importlib.reload(mod)
    src = open(os.path.join(HERE, "dialogues.py"), encoding="utf-8").read()
    for a, b in (src_patch or []):
        assert a in src, "mutation introuvable : " + a[:60]
        src = src.replace(a, b)
    m = types.ModuleType("dialogues_banc")
    m.__file__ = os.path.join(HERE, "dialogues.py")
    exec(compile(src, m.__file__, "exec"), m.__dict__)
    m.catalogue_el = lambda: CAT
    nc.SECRET = "banc"

    def faux(moteur, sys_, content, mx, **kw):
        textes = [c["text"] for c in content if c["type"] == "text"]
        pages = [int(x) for t in textes for x in re.findall(r"=== PAGE (\d+) ===", t)]
        ETAT["appels"].append((moteur, pages))
        ETAT.setdefault("textes", []).extend(textes)                     # H (1.27.0) : ce que l'IA a RECU
        if moteur == "gemini" and set(pages) & ETAT["refuse"]:
            e = m.mod.Refus("gemini", "Gemini a arrete sa reponse pour securite (PROHIBITED_CONTENT)")
            e.usage = {"prompt_tokens": 1000, "completion_tokens": 0}
            raise e
        rep, nouveaux = [], []
        if ETAT.get("chaine"):              # F (1.8.1) : le modele REUTILISE un nom s'il le voit dans la distribution recue
            tout = (sys_ or "") + " ".join(textes)
            connu = next((n for n in ETAT["chaine"] if n in tout), None)
            nom = connu or ETAT["chaine"][len(ETAT["appels"]) - 1]
            for t in textes:
                mm = re.search(r"=== PAGE (\d+) ===.*?Bulles : (\[.*\])", t, re.S)
                if mm:
                    rep += [{"page": int(mm.group(1)), "id": b["id"], "qui": nom, "ton": "ferme", "lire": True, "indice": "banc"}
                            for b in json.loads(mm.group(2))]
            nouveaux = [] if connu else [{"nom": nom, "genre": "homme", "age": "jeune", "fiche": "timide", "voix_el": "ADAM"}]
            return json.dumps({"ambiance": "tendu", "nouveaux": nouveaux, "repliques": rep}), {"prompt_tokens": 2000, "completion_tokens": 500}
        for t in textes:
            mm = re.search(r"=== PAGE (\d+) ===.*?Bulles : (\[.*\])", t, re.S)
            if not mm:
                continue
            pg = int(mm.group(1))
            for b in json.loads(mm.group(2)):
                qui = ETAT["qui5"] if pg == 5 else ("Genos" if pg == 7 or b["texte"].startswith("HOP") else "narrateur")
                lire = "CHAIR" not in b["texte"]
                rep.append({"page": pg, "id": b["id"], "qui": qui, "ton": "ferme", "lire": lire, "indice": "banc"})
        if ETAT["qui5"] == "Fille-Moustique":
            nouveaux = [{"nom": "Fille-Moustique", "genre": "femme", "age": "adulte", "fiche": "hautaine", "voix_el": "LILY"},
                        {"nom": "Genos", "genre": "homme", "age": "19", "fiche": "froid", "voix_el": "ADAM"}]
        return json.dumps({"ambiance": "shonen tendu", "nouveaux": nouveaux, "repliques": rep}), {"prompt_tokens": 2000, "completion_tokens": 500}
    nc.appel_vision = faux

    def faux_post(path, body, **kw):                 # D12 : le controle des doublons (DeepSeek) -- jamais le vrai gateway
        ETAT.setdefault("posts", []).append(path)
        rep = {"doublons": ETAT.get("doublons_rep", [])}
        return {"choices": [{"message": {"content": json.dumps(rep)}}], "usage": {"prompt_tokens": 300, "completion_tokens": 40}}
    nc.post = faux_post
    return m


def lancer(m, pages="5-7", chap="opm/ch_6"):
    return m.cmd_preparer(types.SimpleNamespace(chap=chap, pages=pages))


def doc(ch):
    return json.load(open(os.path.join(ch, "dialogues", "dialogues.json"), encoding="utf-8"))


def distrib():
    return json.load(open(os.path.join(T, "opm", "dialogues_distribution.json"), encoding="utf-8"))


def scenario(m, verbeux=True):
    """A + B ; rend True si tout est vert (pour les mutations)."""
    k0 = len(KO)
    ch = copie()
    ETAT.update(qui5="Fille-Moustique", refuse=set(), appels=[])
    code = lancer(m)
    d, dist = doc(ch), distrib()
    noms = {p["nom"]: p for p in dist["persos"]}
    check("A. code 0", code == 0, code)
    check("A. distribution : Fille-Moustique + Genos", set(noms) == {"Fille-Moustique", "Genos"}, list(noms))
    check("A. voix du bon genre", noms.get("Fille-Moustique", {}).get("voix_el") == "LILY" and noms.get("Genos", {}).get("voix_el") == "ADAM")
    check("A. couleurs distinctes", len({p["couleur"] for p in dist["persos"]}) == 2)
    tr = json.load(open(os.path.join(ch, "traduction", "fr", "traduction.json"), encoding="utf-8"))
    nb = sum(1 for p in tr["pages"] for b in p["bulles"] if b["type"] in ("dialogue", "narration") and not b.get("ecarte") and (b.get("trad") or "").strip())
    check("A. une entree par bulle", len(d["repliques"]) == nb, (len(d["repliques"]), nb))
    avec = sum(1 for x in d["repliques"] if x["contour"])
    check("A. contour reel sur la plupart des bulles", avec >= nb * 0.6, "%d/%d" % (avec, nb))
    chair = [x for x in d["repliques"] if "CHAIR" in x["texte"]]
    check("A. CHAIR DE POULE non lue", chair and not chair[0]["lire"], chair[:1])
    excl = [x for x in d["repliques"] if x["texte"].strip() == "!"]
    check("A. « ! » non lu", excl and not excl[0]["lire"])
    pr = json.load(open(os.path.join(ch, "dialogues", "progress.json"), encoding="utf-8"))
    check("A. progress fini", pr.get("fini") and pr.get("etape") == "fini", pr)
    dep = [json.loads(l) for l in open(os.environ["MANGA_DEPENSES"], encoding="utf-8")]
    check("A. depense 'dialogues' notee", dep and dep[-1]["type"] == "dialogues" and dep[-1]["paye"] > 0, dep[-1:])
    check("A. rien ecrit hors dialogues/ et la distribution", sorted(os.listdir(ch)) == ["dialogues", "traduction"], os.listdir(ch))
    # B : alias + corrections
    dist["persos"][[p["nom"] for p in dist["persos"]].index("Fille-Moustique")]["alias"] = ["p1"]
    json.dump(dist, open(os.path.join(T, "opm", "dialogues_distribution.json"), "w", encoding="utf-8"), ensure_ascii=False)
    d0 = doc(ch)
    cible = next(x for x in d0["repliques"] if x["page"] == 5 and x["lire"])
    cible["corrige"] = {"texte": "Texte corrige par Quang", "qui": "Genos"}
    json.dump(d0, open(os.path.join(ch, "dialogues", "dialogues.json"), "w", encoding="utf-8"), ensure_ascii=False)
    ETAT["qui5"] = "p1"
    lancer(m)
    d2, dist2 = doc(ch), distrib()
    check("B. pas de doublon dans la distribution", len(dist2["persos"]) == 2, [p["nom"] for p in dist2["persos"]])
    p5 = [x for x in d2["repliques"] if x["page"] == 5 and x["cle"] != cible["cle"]]
    check("B. alias p1 -> Fille-Moustique", p5 and all(x["qui"] == "Fille-Moustique" for x in p5), [x["qui"] for x in p5])
    c2 = next(x for x in d2["repliques"] if x["cle"] == cible["cle"])
    check("B. correction gardee (texte + qui)", c2["texte"] == "Texte corrige par Quang" and c2["qui"] == "Genos", (c2["texte"], c2["qui"]))
    check("B. texte d'origine conserve a cote", c2["texte_origine"] != c2["texte"])
    return len(KO) == k0


m = charger()
print("=== A + B")
scenario(m)

print("=== C. moderation")
ch = copie()
ETAT.update(qui5="Fille-Moustique", refuse={6}, appels=[])
lancer(m)
d = doc(ch)
al = json.load(open(os.environ["MANGA_ALERTES"], encoding="utf-8"))["alertes"] if os.path.exists(os.environ["MANGA_ALERTES"]) else []
check("C. relais coupe : page 6 a traiter", all(x["a_traiter"] for x in d["repliques"] if x["page"] == 6) and not any(x["a_traiter"] for x in d["repliques"] if x["page"] != 6))
check("C. relais coupe : alerte 'dialogues' page 6", any(a["etape"] == "dialogues" and a["pages"] == [6] for a in al), al)
check("C. relais coupe : aucun appel kimi", not any(mo == "kimi" for mo, _ in ETAT["appels"]), ETAT["appels"])
ch = copie()
json.dump({"relais_moderation": True, "petits_cris": True}, open(os.environ["MANGA_REGLAGES"], "w", encoding="utf-8"))
ETAT.update(qui5="Fille-Moustique", refuse={6}, appels=[])
lancer(m)
d = doc(ch)
al = json.load(open(os.environ["MANGA_ALERTES"], encoding="utf-8"))["alertes"] if os.path.exists(os.environ["MANGA_ALERTES"]) else []
check("C. relais actif : page 6 relue par kimi", ("kimi", [6]) in ETAT["appels"], ETAT["appels"])
check("C. relais actif : 0 page a traiter, 0 alerte", not any(x["a_traiter"] for x in d["repliques"]) and not al, al)
check("C. relais actif : Genos toujours reconnu p.6", any(x["page"] == 6 and x["qui"] == "Genos" for x in d["repliques"]))

print("=== D. sans traduction")
os.makedirs(os.path.join(T, "opm", "ch_99"), exist_ok=True)
check("D. arret code 3", lancer(m, chap="opm/ch_99") == 3)

def scenario_lots(m, verbeux=True):
    """F (1.8.1, Quang 02h26) : 3 lots d'UNE page, aucune distribution au depart ; le modele invente un nom au 1er lot et le
    reutilise s'il le voit ensuite. Attendu : UN seul personnage, pas un par lot."""
    k0 = len(KO)
    copie()
    try: os.remove(os.path.join(T, "opm", "dialogues_distribution.json"))
    except FileNotFoundError: pass
    ETAT.update(chaine=["Homme aux cheveux blancs", "Homme aux cheveux gris", "Homme aux cheveux argentes"], refuse=set(), appels=[])
    m.LOT_PAGES = 1
    try:
        lancer(m)
    finally:
        ETAT.pop("chaine", None)
    noms = [p["nom"] for p in distrib()["persos"]]
    check("F. 3 lots, un seul homme : le nom du 1er lot est repris ensuite", noms == ["Homme aux cheveux blancs"] and len(ETAT["appels"]) == 3, (noms, ETAT["appels"]))
    return len(KO) == k0

print("=== F. personnages nommes au fil des lots")
scenario_lots(charger())

print("=== G. doublons probables (D12)")
copie()
ETAT.update(qui5="Fille-Moustique", refuse=set(), appels=[], posts=[], doublons_rep=[{"noms": ["Genos", "Fille-Moustique"], "raison": "banc"}])
m_g = charger(); lancer(m_g)
dg = distrib()
check("G. controle appele apres de NOUVEAUX personnages (faux DeepSeek, rien ne sort)", "/api/deepseek" in ETAT["posts"], ETAT["posts"])
check("G. resultat range dans la distribution, rien fusionne", dg.get("doublons") and dg["doublons"][0]["avec"] and len(dg["persos"]) == 2, dg.get("doublons"))
ETAT.update(posts=[])
dg["pas_doublons"] = [sorted(["Genos", "Fille-Moustique"])]
json.dump(dg, open(os.path.join(T, "opm", "dialogues_distribution.json"), "w", encoding="utf-8"), ensure_ascii=False)
st = {}
g2 = m_g.doublons_probables(m_g.distribution(os.path.join(T, "opm")), os.path.join(T, "opm"), st)
check("G. un groupe REFUSE par Quang n'est plus propose", g2 == [], g2)
ETAT.pop("doublons_rep", None)

def scenario_qui(m, verbeux=True):
    """H (S4, 1.27.0) : une bulle attribuee par Quang a la verification -> la replique est a lui, l'IA l'a recu, les autres : l'IA."""
    k0 = len(KO)
    ch = copie()
    ETAT.update(qui5="Fille-Moustique", refuse=set(), appels=[], textes=[])
    tr = json.load(open(os.path.join(ch, "traduction", "fr", "traduction.json"), encoding="utf-8"))
    p5 = [b for b in next(p for p in tr["pages"] if p["page"] == 5)["bulles"] if b["type"] == "dialogue" and (b.get("trad") or "").strip()]
    b0 = sorted(p5, key=lambda b: b["id"])[0]
    os.makedirs(os.path.join(ch, "dialogues"), exist_ok=True)
    # 1.29.0 : l'app enregistre l'ordre COMPLET (toutes les bulles non exclues) -- fixture alignee sur le vrai format
    json.dump({"pages": {"5": {"ordre": [{"id": b0["id"], "box": b0["box"], "qui": "Genos"}]
                                         + [{"id": b["id"], "box": b["box"]} for b in sorted(p5, key=lambda b: b["id"])[1:]],
                               "exclues": [], "ajouts": []}}},
              open(os.path.join(ch, "dialogues", "bulles_verifiees.json"), "w", encoding="utf-8"), ensure_ascii=False)
    lancer(m)
    d = doc(ch)
    x = next(y for y in d["repliques"] if y["cle"] == "5-%d" % b0["id"])
    autres = [y["qui"] for y in d["repliques"] if y["page"] == 5 and y["cle"] != x["cle"] and y["type"] == "dialogue"]
    check("H. la bulle attribuee par Quang est a lui (l'IA disait Fille-Moustique)", x["qui"] == "Genos", x["qui"])
    check("H. les bulles laissees libres : l'IA decide", autres and all(q == "Fille-Moustique" for q in autres), autres)
    check("H. l'IA a RECU le choix (champ « qui » de la bulle envoyee)", any('"qui": "Genos"' in t for t in ETAT["textes"]), "")
    check("H. consigne : regle 5 (attribution de l'utilisateur)", "attribuee par l'UTILISATEUR" in m.SYS)
    return len(KO) == k0


print("=== H. (S4, 1.27.0) qui parle choisi a la verification des bulles")
scenario_qui(charger())

def scenario_cris(m, verbeux=True):
    """I (S16, 1.29.0) : interrupteur « petits cris » ETEINT -> « Ah... » et « ! » n'arrivent plus a l'IA ; une page VERIFIEE par
    Quang ou il a GARDE un cri -> ce cri reste (sa liste fait loi) ; une bulle apparue apres sa validation -> exclue."""
    k0 = len(KO)
    ch = copie()
    json.dump({"petits_cris": False}, open(os.environ["MANGA_REGLAGES"], "w", encoding="utf-8"))
    ETAT.update(qui5="Fille-Moustique", refuse=set(), appels=[], textes=[])
    tr = json.load(open(os.path.join(ch, "traduction", "fr", "traduction.json"), encoding="utf-8"))
    bl = {p["page"]: sorted([b for b in p["bulles"] if b["type"] in ("dialogue", "narration") and (b.get("trad") or "").strip()],
                            key=lambda b: b["id"]) for p in tr["pages"]}
    cri7 = next(b for b in bl[7] if (b.get("trad") or "").strip() == "!")
    # page 7 verifiee par Quang : il GARDE le « ! » et toutes les autres bulles SAUF la derniere (qui devient « apparue apres »)
    garde7 = [b for b in bl[7] if b is not bl[7][-1]]
    json.dump({"pages": {"7": {"ordre": [{"id": b["id"], "box": b["box"]} for b in garde7], "exclues": [], "ajouts": []}}},
              open(os.path.join(ch, "dialogues", "bulles_verifiees.json") if os.path.isdir(os.path.join(ch, "dialogues"))
                   else (os.makedirs(os.path.join(ch, "dialogues")) or os.path.join(ch, "dialogues", "bulles_verifiees.json")),
                   "w", encoding="utf-8"), ensure_ascii=False)
    lancer(m)
    d = doc(ch)
    textes = [(x["page"], (x.get("texte") or "").strip()) for x in d["repliques"]]
    envoye = "\n".join(ETAT["textes"])
    check("I. page 5 non verifiee : « Ah... » ignore (jamais envoye a l'IA)", (5, "Ah...") not in textes and '"texte": "Ah..."' not in envoye, textes)
    check("I. page 7 verifiee : le « ! » GARDE par Quang reste", any(x["page"] == 7 and x["cle"] == "7-%d" % cri7["id"] for x in d["repliques"]),
          [x["cle"] for x in d["repliques"] if x["page"] == 7])
    check("I. page 7 : la bulle absente de sa validation n'est pas lue", not any(x["cle"] == "7-%d" % bl[7][-1]["id"] for x in d["repliques"]),
          bl[7][-1]["id"])
    check("I. les vraies repliques de la page 5 sont toutes la", all(any(x["cle"] == "5-%d" % b["id"] for x in d["repliques"])
                                                                   for b in bl[5] if not m.est_gimmick(b.get("trad"))))
    return len(KO) == k0


print("=== I. (S16, 1.29.0) petits cris ignores + liste de Quang qui fait loi")
scenario_cris(charger())

print("=== E. mutations (doivent rendre le banc ROUGE)")
for nom, patch in (("alias ignore", [('if q.lower() == p["nom"].lower() or q.lower() in [a.lower() for a in p.get("alias", [])]:',
                                      'if q.lower() == p["nom"].lower():')]),
                   ("corrections ecrasees", [('neuf.update({k: v for k, v in corr.items() if k in ("texte", "qui", "ton", "lire")})',
                                              'pass')])):
    pass
for nom, patch, sc in (("fusion en fin de preparation (avant 1.8.1)", [('            stats.setdefault("_ajoutes", []).extend(fusionner_distribution(distrib, r.get("nouveaux"), cat))   # 1.8.1 : connu du lot suivant',
                                                                        '            pass')], scenario_lots),
                       ("alias ignore", [('if q.lower() == p["nom"].lower() or q.lower() in [a.lower() for a in p.get("alias", [])]:',
                                          'if q.lower() == p["nom"].lower():')], scenario),
                       ("corrections ecrasees", [('neuf.update({k: v for k, v in corr.items() if k in ("texte", "qui", "ton", "lire")})',
                                                  'pass')], scenario),
                       ("petits cris jamais filtres (avant 1.29.0)", [('if not cris:', 'if False:')], scenario_cris),
                       ("bulle apparue apres la verification gardee (avant 1.29.0)", [('    if nouvelles:', '    if False:')], scenario_cris),
                       ("qui de Quang ignore (avant 1.27.0)", [('"qui": (nom_connu(distrib, b["qui_impose"]) if b.get("qui_impose")',
                                                                '"qui": (nom_connu(distrib, b["qui_impose"]) if False')], scenario_qui)):
    avant, avant_ok = len(KO), len(OK)
    print("  (sabotage « %s » : vérifications ci-dessous attendues en partie ROUGES)" % nom)
    vert = sc(charger(patch), verbeux=False)
    del KO[avant:]; del OK[avant_ok:]          # le scenario sabote ne compte pas dans le verdict, seul son resultat compte
    check("E. mutation « %s » detectee" % nom, not vert)

shutil.rmtree(T, ignore_errors=True)
print("\n%d OK, %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
