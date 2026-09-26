# -*- coding: utf-8 -*-
"""Banc dialogues.py voix (D2, ROADMAP 4-septdecies) -- HORS LIGNE : faux ElevenLabs, faux solde, fausse transcription,
dossier temporaire (aucune donnee reelle, aucun credit depense).
A. 1er passage : une voix par replique lue (pas pour « non lue » ni narrateur non lu), balise de ton DANS le texte envoye,
   reglages du personnage (voix, stabilite, vitesse), credits notes au registre, progress fini
B. relance : 0 appel (empreintes)          C. vitesse de Genos changee : SEULES ses repliques refaites
D. texte corrige : SEULE cette replique     E. quota epuise au 2e appel : code 4, 1 voix gardee, ARRET (aucun appel apres,
   aucun autre moteur), progress « quota » ; reprise = seulement les manquantes
F. solde a 0 : code 4 avant tout appel      G. tons coupes : aucune balise envoyee
H. balise prononcee (transcription) : refaite une fois
I. MUTATIONS : empreinte ignoree / quota qui continue -> ROUGE
Usage : python test_dialogues_voix.py
"""
import importlib, json, os, shutil, subprocess, sys, tempfile, types

HERE = os.path.dirname(os.path.abspath(__file__))
T = tempfile.mkdtemp(prefix="banc_dvoix_")
os.environ.update(MANGA_SOURCES_DIR=T, MANGA_DEPENSES=os.path.join(T, "_depenses.jsonl"),
                  MANGA_ALERTES=os.path.join(T, "_alertes.json"), MANGA_REGLAGES=os.path.join(T, "_reglages.json"))
sys.path.insert(0, HERE)
OK, KO = [], []
MP3 = os.path.join(T, "silence.mp3")
subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "0.6", MP3], check=True)
DATA = open(MP3, "rb").read()


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail)[:170] if detail else ""))


def decor(tons=True):
    shutil.rmtree(os.path.join(T, "s"), ignore_errors=True)
    dd = os.path.join(T, "s", "ch_1", "dialogues")
    os.makedirs(dd)
    R = lambda cle, qui, texte, ton, lire=True, typ="dialogue": {"cle": cle, "page": int(cle.split("-")[0]), "id": int(cle.split("-")[1]),
        "file": "page_001.png", "type": typ, "box": {"x": 0, "y": 0, "w": .1, "h": .1}, "contour": None, "texte_origine": texte,
        "texte": texte, "qui": qui, "ton": ton, "lire": lire, "indice": "", "a_traiter": False, "corrige": {}, "voix": None}
    doc = {"version": "1", "chapitre": "s/ch_1", "repliques": [
        R("1-1", "Fille", "Et si je visais tes jambes ?", "arrogant, moqueur"),
        R("1-2", "Fille", "OÙ SONT MES JAMBES ?", "terrifié"),
        R("1-3", "Genos", "Tu ne pourras pas me semer.", "menaçant"),
        R("1-4", "Genos", "CHAIR DE POULE", "", lire=False),
        R("1-5", "narrateur", "Pendant ce temps...", "", lire=False, typ="narration")]}
    json.dump(doc, open(os.path.join(dd, "dialogues.json"), "w", encoding="utf-8"), ensure_ascii=False)
    dist = {"version": 1, "tons": tons, "balises": {}, "narrateur": {"nom": "Narrateur", "voix_el": "GEORGE", "lire": False},
            "persos": [{"nom": "Fille", "voix_el": "LILY", "expressivite": 2, "vitesse": 1.1, "couleur": "#f0f"},
                       {"nom": "Genos", "voix_el": "ADAM", "expressivite": 0, "vitesse": 1.15, "couleur": "#fa0"}]}
    json.dump(dist, open(os.path.join(T, "s", "dialogues_distribution.json"), "w", encoding="utf-8"), ensure_ascii=False)
    for f in ("_depenses.jsonl", "_alertes.json"):
        try:
            os.remove(os.path.join(T, f))
        except OSError:
            pass
    return dd


E = {"appels": [], "quota_a": None, "solde": 10000, "fuite": set(), "autres": []}


def charger(patch=None):
    import narrate_chapter as nc
    src = open(os.path.join(HERE, "dialogues.py"), encoding="utf-8").read()
    for a, b in (patch or []):
        assert a in src, "mutation introuvable : " + a[:60]
        src = src.replace(a, b)
    m = types.ModuleType("dialogues_banc")
    m.__file__ = os.path.join(HERE, "dialogues.py")
    exec(compile(src, m.__file__, "exec"), m.__dict__)
    nc.SECRET = "banc"

    def el_post(path, body):
        E["appels"].append((path, body))
        if E["quota_a"] is not None and len(E["appels"]) >= E["quota_a"]:
            raise m.QuotaEpuise('{"detail":{"status":"quota_exceeded"}}')
        return DATA
    m.el_post = el_post
    m.el_solde = lambda: {"utilises": 10000 - E["solde"], "limite": 10000, "restants": E["solde"], "renouvellement": 0}

    def post(path, body, timeout=240):
        E["autres"].append(path)
        if "deepseek" in path:
            fr = json.loads(body["messages"][1]["content"])
            return {"choices": [{"message": {"content": json.dumps({t: "[tag%s]" % chr(65 + i) for i, t in enumerate(fr)})}}],   # des MOTS (un chiffre est refuse)
                    "usage": {"prompt_tokens": 100, "completion_tokens": 20}}
        raise AssertionError("appel inattendu : " + path)
    nc.post = post

    def fuite(mp3, texte, stats):
        if texte in E["fuite"]:
            E["fuite"].discard(texte)
            return True, "tagA " + texte
        return False, texte
    m.fuite_balise = fuite
    return m


def voix(m, pages=""):
    return m.cmd_voix(types.SimpleNamespace(chap="s/ch_1", pages=pages))


def lire(dd):
    return {x["cle"]: x for x in json.load(open(os.path.join(dd, "dialogues.json"), encoding="utf-8"))["repliques"]}


def scenario(m):
    k0 = len(KO)
    dd = decor()
    E.update(appels=[], quota_a=None, solde=10000, fuite=set(), autres=[])
    code = voix(m)
    r = lire(dd)
    check("A. code 0", code == 0, code)
    check("A. 3 appels (lues seulement)", len(E["appels"]) == 3, [b["text"] for _, b in E["appels"]])
    check("A. voix faites sur les 3 lues, aucune sur non lues", all(r[c]["voix"] for c in ("1-1", "1-2", "1-3")) and not r["1-4"]["voix"] and not r["1-5"]["voix"])
    t1 = E["appels"][0][1]
    check("A. balise de ton en tete du texte", t1["text"].startswith("[tag") and "jambes" in t1["text"], t1["text"])
    check("A. CAPITALES lues en casse normale", any("Où sont mes jambes" in b["text"] for _, b in E["appels"]), [b["text"] for _, b in E["appels"]])
    g = next(b for p, b in E["appels"] if "/ADAM" in p)
    check("A. reglages de Genos : voix ADAM, stabilite 1.0 (retenue), vitesse 1.15",
          g["voice_settings"]["stability"] == 1.0 and g["voice_settings"]["speed"] == 1.15 and g["model_id"] == "eleven_v3", g)
    dep = [json.loads(l) for l in open(os.environ["MANGA_DEPENSES"], encoding="utf-8")]
    cr = sum(len(b["text"]) for _, b in E["appels"])
    check("A. credits notes au registre (paye 0)", any(x.get("credits") == cr and x["paye"] == 0 for x in dep), dep)
    pr = json.load(open(os.path.join(dd, "progress.json"), encoding="utf-8"))
    check("A. progress fini", pr["etape"] == "fini" and pr.get("fini"), pr)
    check("A. seul autre appel = DeepSeek (balises)", set(E["autres"]) == {"/api/deepseek"}, E["autres"])
    E["appels"].clear(); E["autres"].clear()
    voix(m)
    check("B. relance : 0 appel ElevenLabs, 0 DeepSeek", not E["appels"] and not E["autres"], (E["appels"], E["autres"]))
    dist = json.load(open(os.path.join(T, "s", "dialogues_distribution.json"), encoding="utf-8"))
    dist["persos"][1]["vitesse"] = 1.0
    json.dump(dist, open(os.path.join(T, "s", "dialogues_distribution.json"), "w", encoding="utf-8"), ensure_ascii=False)
    voix(m)
    check("C. vitesse de Genos : seule 1-3 refaite", len(E["appels"]) == 1 and "/ADAM" in E["appels"][0][0], len(E["appels"]))
    E["appels"].clear()
    doc = json.load(open(os.path.join(dd, "dialogues.json"), encoding="utf-8"))
    doc["repliques"][0]["texte"] = "Et si je visais TES BRAS ?"
    json.dump(doc, open(os.path.join(dd, "dialogues.json"), "w", encoding="utf-8"), ensure_ascii=False)
    voix(m)
    check("D. texte corrige : seule 1-1 refaite", len(E["appels"]) == 1 and "BRAS" in E["appels"][0][1]["text"], [b["text"] for _, b in E["appels"]])
    # E : quota
    dd = decor()
    E.update(appels=[], quota_a=2, autres=[])
    code = voix(m)
    r = lire(dd)
    pr = json.load(open(os.path.join(dd, "progress.json"), encoding="utf-8"))
    check("E. quota : code 4", code == 4, code)
    check("E. quota : ARRET au 2e appel (aucun 3e)", len(E["appels"]) == 2, len(E["appels"]))
    check("E. quota : 1 voix gardee", sum(1 for c in ("1-1", "1-2", "1-3") if r[c]["voix"]) == 1)
    check("E. quota : progress « quota » + message", pr["etape"] == "quota" and "quota" in (pr.get("arret") or ""), pr)
    check("E. quota : aucun autre moteur de voix", all("deepseek" in x for x in E["autres"]), E["autres"])
    E.update(appels=[], quota_a=None)
    voix(m)
    check("E. reprise : seulement les 2 manquantes", len(E["appels"]) == 2, len(E["appels"]))
    return len(KO) == k0


m = charger()
print("=== A-E")
scenario(m)
print("=== F. solde a 0")
dd = decor(); E.update(appels=[], solde=0, quota_a=None)
check("F. code 4 avant tout appel", voix(m) == 4 and not E["appels"], len(E["appels"]))
print("=== G. tons coupes")
dd = decor(tons=False); E.update(appels=[], solde=10000, autres=[])
voix(m)
check("G. aucune balise, aucun DeepSeek", E["appels"] and not any("[" in b["text"] for _, b in E["appels"]) and not E["autres"], [b["text"] for _, b in E["appels"]])
print("=== H. balise prononcee")
dd = decor(); E.update(appels=[], fuite={"Tu ne pourras pas me semer."})
voix(m)
check("H. refaite une fois (4 appels pour 3 repliques)", len(E["appels"]) == 4, len(E["appels"]))
print("=== I. mutations (doivent rendre le banc ROUGE)")
for nom, patch in (("empreinte ignoree", [('if v.get("empreinte") == emp and os.path.isfile', 'if False and os.path.isfile')]),
                   ("quota qui continue", [('            arret = "quota ElevenLabs epuise"\n            log("  ARRET a %s : %s" % (x["cle"], e))\n            break',
                                            '            arret = "quota ElevenLabs epuise"\n            continue')])):
    a0, o0 = len(KO), len(OK)
    print("  (sabotage « %s »)" % nom)
    vert = scenario(charger(patch))
    del KO[a0:]; del OK[o0:]
    check("I. mutation « %s » detectee" % nom, not vert)
shutil.rmtree(T, ignore_errors=True)
print("\n%d OK, %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
