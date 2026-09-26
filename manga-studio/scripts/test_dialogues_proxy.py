# -*- coding: utf-8 -*-
"""Banc D3 (ROADMAP 4-septdecies) : les routes « Dialogues » du proxy PATCHE, sur une instance de TEST (8191, proxy_8191.py),
pointee sur une COPIE temporaire (OPM ch.6 p.5-7) -- ni les donnees reelles, ni les instances 8190 / 8192 ne sont touchees.
Appels REELS : preparation Gemini (~0,014 $) + voix ElevenLabs de la page 7 seulement (~180 credits).
Usage : python test_dialogues_proxy.py <proxy_patche.py> [--sans-credits-el]   (mutation : le banc doit etre ROUGE)
"""
import json, os, shutil, subprocess, sys, tempfile, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PROXY = os.path.abspath(sys.argv[1])
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
VRAI = os.path.expanduser(r"~\Documents\MangaStudio-donnees\sources\one-punch-man\ch_6")
BASE = "http://127.0.0.1:8191"
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail)[:180] if detail else ""), flush=True)


def get(path):
    r = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + KEY})
    with urllib.request.urlopen(r, timeout=60) as h:
        return json.load(h) if "json" in (h.headers.get("Content-Type") or "") else (h.status, h.headers.get("Content-Type"), len(h.read()))


def post(path, body):
    r = urllib.request.Request(BASE + path, data=json.dumps(body).encode(), headers={"Authorization": "Bearer " + KEY,
                               "Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=200) as h:
        return json.load(h)


def attendre_fin(d, delai=240, vu_activite=None):
    t0 = time.time()
    while time.time() - t0 < delai:
        if vu_activite is not None and any(i.get("type") == "dialogues" and i.get("d") == d for i in get("/manga/activite")["items"]):
            vu_activite.append(1)
        e = get("/manga/dialogues?d=" + urllib.parse.quote(d))
        pr = e.get("progress") or {}
        if not e["en_cours"] and pr.get("fini"):
            return e
        time.sleep(0.7)
    return get("/manga/dialogues?d=" + urllib.parse.quote(d))


T = tempfile.mkdtemp(prefix="banc_dproxy_")
ch = os.path.join(T, "opm", "ch_6")
os.makedirs(os.path.join(ch, "traduction", "fr"))
tr = json.load(open(os.path.join(VRAI, "traduction", "fr", "traduction.json"), encoding="utf-8"))
tr["pages"] = [p for p in tr["pages"] if p["page"] in (5, 6, 7)]
json.dump(tr, open(os.path.join(ch, "traduction", "fr", "traduction.json"), "w", encoding="utf-8"), ensure_ascii=False)
for p in tr["pages"]:
    shutil.copy(os.path.join(VRAI, "traduction", "fr", p["file"]), os.path.join(ch, "traduction", "fr", p["file"]))
shutil.copy(os.path.join(VRAI, "manifest.json"), os.path.join(ch, "manifest.json"))
os.makedirs(os.path.join(T, "opm", "ch_7"))
shutil.copy(os.path.join(VRAI, "manifest.json"), os.path.join(T, "opm", "ch_7", "manifest.json"))   # sans traduction
env = dict(os.environ, MANGA_SOURCES_DIR=T, PYTHONIOENCODING="utf-8")
srv = subprocess.Popen([sys.executable, os.path.join(HERE, "proxy_8191.py"), PROXY], env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
try:
    for _ in range(60):
        try:
            get("/manga/el_solde"); break
        except Exception:
            time.sleep(1)
    D = "opm/ch_6"
    print("=== preparer (reel)")
    r = post("/manga/dialogues_lancer", {"d": D, "action": "preparer", "pages": "5-7"})
    check("lancer preparer", r.get("ok"), r)
    r2 = post("/manga/dialogues_lancer", {"d": D, "action": "preparer"})
    check("2e lancement refuse pendant le 1er", "déjà en cours" in (r2.get("error") or ""), r2)
    vu = []
    e = attendre_fin(D, vu_activite=vu)
    check("activite : type « dialogues » vu pendant le travail", bool(vu))
    check("preparation finie, 12 repliques", e["progress"].get("etape") == "fini" and len((e["doc"] or {}).get("repliques") or []) == 12, e["progress"])
    check("distribution du manga : 2 personnages", len((e["distribution"] or {}).get("persos") or []) == 2, [p["nom"] for p in (e["distribution"] or {}).get("persos") or []])
    check("sans traduction -> refus lisible", "traduis d'abord" in (post("/manga/dialogues_lancer", {"d": "opm/ch_7", "action": "preparer"}).get("error") or ""))
    print("=== corrections + distribution")
    r = post("/manga/dialogues_maj", {"d": D, "corrections": [{"cle": "7-2", "texte": "Tu ne pourras jamais me semer."}]})
    check("correction de texte", r.get("n") == 1, r)
    persos = e["distribution"]["persos"]
    fem = next(p for p in persos if p.get("genre", "").startswith("f"))
    gen = next(p for p in persos if p is not fem)
    r = post("/manga/dialogues_distribution", {"serie": "opm", "persos": [{"nom": fem["nom"], "renomme": "Fille-Moustique"},
                                                                          {"nom": gen["nom"], "vitesse": 1.0}]})
    check("renommer (alias gardé) + vitesse", r.get("renommes") == {fem["nom"]: "Fille-Moustique"} and fem["nom"] in
          next(p for p in r["distribution"]["persos"] if p["nom"] == "Fille-Moustique")["alias"], r.get("renommes"))
    e = get("/manga/dialogues?d=opm/ch_6")
    check("le chapitre suit le nouveau nom", any(x["qui"] == "Fille-Moustique" for x in e["doc"]["repliques"])
          and not any(x["qui"] == fem["nom"] for x in e["doc"]["repliques"]))
    check("correction gardee dans « corrige »", next(x for x in e["doc"]["repliques"] if x["cle"] == "7-2")["corrige"].get("texte"))
    print("=== voix page 7 (reel)")
    r = post("/manga/dialogues_lancer", {"d": D, "action": "voix", "pages": "7"})
    check("lancer voix", r.get("ok"), r)
    e = attendre_fin(D)
    faites = [x["cle"] for x in e["doc"]["repliques"] if x.get("voix")]
    check("voix : page 7 lues seulement", sorted(faites) == ["7-2", "7-3", "7-6", "7-7"], faites)
    post("/manga/dialogues_lancer", {"d": D, "action": "voix", "pages": "7"})
    e2 = attendre_fin(D)
    check("relance : 0 voix a refaire", e2["progress"].get("total") == 0, e2["progress"])
    r = post("/manga/dialogues_ecouter", {"d": D, "cle": "7-2"})
    check("ecouter une voix faite = gratuite", r.get("deja") and r.get("credits") == 0, r)
    st = get("/manga/source_file?p=" + urllib.parse.quote(r.get("chemin", "")) + "&_k=" + urllib.parse.quote(KEY))
    check("le MP3 se lit par /manga/source_file", isinstance(st, tuple) and st[0] == 200 and "audio" in (st[1] or ""), st)
    c = get("/manga/costs")
    check("couts : credits ElevenLabs a part", (c.get("elevenlabs") or {}).get("mois", 0) > 0, c.get("elevenlabs"))
    check("couts : preparation comptee en dollars", (c.get("par_etape") or {}).get("dialogues", 0) > 0, c.get("par_etape"))
    s = get("/manga/el_solde")
    check("solde ElevenLabs lu", s.get("ok") and s.get("limite", 0) > 0, s)
    v = get("/manga/el_voix")
    check("catalogue des voix", v.get("ok") and len(v.get("voix") or []) >= 10, len(v.get("voix") or []))
    print("=== arreter")
    post("/manga/dialogues_lancer", {"d": D, "action": "preparer", "pages": "5"})
    time.sleep(1.5)
    r = post("/manga/dialogues_arreter", {"d": D})
    time.sleep(2)
    e = get("/manga/dialogues?d=opm/ch_6")
    check("arret : plus en cours, motif ecrit", r.get("ok") and not e["en_cours"] and e["progress"].get("etape") in ("arrete", "fini"), e["progress"])
    check("arret : les voix deja faites sont gardees", sum(1 for x in e["doc"]["repliques"] if x.get("voix")) == 4)
finally:
    srv.kill()
    try:
        os.remove(os.path.expanduser(r"~\Documents\ComfyUI\_studio_llm_proxy_8191.py"))
    except OSError:
        pass
    shutil.rmtree(T, ignore_errors=True)
print("\n%d OK, %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
