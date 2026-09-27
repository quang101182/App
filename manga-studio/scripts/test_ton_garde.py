# -*- coding: utf-8 -*-
"""Banc dialogues.py 1.23.0 (27/09) -- TON GARDE : texte et personnage inchanges -> l'ancien ton (donc la voix) est garde, meme si l'IA en propose un autre ; texte change -> nouveau ton.
(adapte de test_prep_retire_exclues.py) Banc dialogues.py 1.20.0 (27/09) : refaire la preparation d'une plage APRES avoir exclu une bulle et en avoir ajoute une
-> la replique exclue est RETIREE, l'ajout apparait, l'ordre verifie est suivi, les pages hors plage sont intactes.
La VRAIE fonction cmd_preparer tourne sur une COPIE legere du chapitre ; seuls l'appel a l'IA (preparer_pages), le catalogue
de voix et les reglages sont remplaces par des faux : 0 appel paye, vraies donnees intouchees.
Usage : python test_prep_retire_exclues.py <serie/ch_N traduit et prepare> [--ancien dialogues_1190.py]"""
import importlib.util, json, os, shutil, sys, tempfile, types

HERE = os.path.dirname(os.path.abspath(__file__))
args = [x for x in sys.argv[1:] if not x.startswith("--")]
CH = args[0]
MOD = sys.argv[sys.argv.index("--ancien") + 1] if "--ancien" in sys.argv else os.path.join(HERE, "dialogues.py")
SRC = os.path.expanduser(r"~\Documents\MangaStudio-donnees\sources")
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail)[:170] if detail else ""), flush=True)


T = tempfile.mkdtemp(prefix="prep_")
serie, chap = CH.split("/"); sd, cd = os.path.join(SRC, serie), os.path.join(SRC, serie, chap)
os.makedirs(os.path.join(T, serie, chap, "traduction", "fr"))
for f in os.listdir(sd):
    if f.endswith(".json") and os.path.isfile(os.path.join(sd, f)):
        shutil.copy2(os.path.join(sd, f), os.path.join(T, serie, f))
for f in os.listdir(cd):
    if f.endswith(".json"):
        shutil.copy2(os.path.join(cd, f), os.path.join(T, serie, chap, f))
shutil.copytree(os.path.join(cd, "dialogues"), os.path.join(T, serie, chap, "dialogues"),
                ignore=shutil.ignore_patterns("voix", "video", "_oubliees", "*.avant_oubli_*", "bulles_verifiees.json"))
tf = os.path.join(cd, "traduction", "fr")
shutil.copy2(os.path.join(tf, "traduction.json"), os.path.join(T, serie, chap, "traduction", "fr", "traduction.json"))
doc0 = json.load(open(os.path.join(T, CH, "dialogues", "dialogues.json"), encoding="utf-8"))
pp = sorted({x["page"] for x in doc0["repliques"]}); A = pp[0]
for n in pp:
    f = os.path.join(tf, "page_%03d.png" % n)
    if os.path.isfile(f):
        shutil.copy2(f, os.path.join(T, serie, chap, "traduction", "fr", "page_%03d.png" % n))
tr = json.load(open(os.path.join(tf, "traduction.json"), encoding="utf-8"))
bl = [b for p in tr["pages"] if p["page"] == A for b in p["bulles"] if b.get("type") in ("dialogue", "narration") and (b.get("trad") or "").strip()]
assert len(bl) >= 2, "il faut 2 bulles sur la 1re page"
exclue, garde = bl[0], bl[1:]
ajout = {"id": 901, "box": {"x": 0.05, "y": 0.9, "w": 0.1, "h": 0.05}}
ordre = [{"id": b["id"], "box": b["box"]} for b in reversed(garde)] + [ajout]
ancien = {x["cle"]: x for x in doc0["repliques"]}
change = "%d-%d" % (A, garde[0]["id"])                               # une replique dont le TEXTE change (trad modifiee)
for p_ in tr["pages"]:
    if p_["page"] == A:
        for b_ in p_["bulles"]:
            if b_["id"] == garde[0]["id"]: b_["trad"] = (b_.get("trad") or "") + " (modifie)"
json.dump(tr, open(os.path.join(T, serie, chap, "traduction", "fr", "traduction.json"), "w", encoding="utf-8"), ensure_ascii=False)
os.environ["MANGA_SOURCES_DIR"] = T
sys.path.insert(0, HERE)
spec = importlib.util.spec_from_file_location("dlg_banc", MOD); m = importlib.util.module_from_spec(spec)
sys.argv = ["x"]
try:
    spec.loader.exec_module(m)
except SystemExit:
    pass
m.SOURCES = T
m.voix_francaises = lambda: [{"id": "v1", "nom": "V", "genre": "male", "age": "", "desc": "", "fr": True}]
m.catalogue_el = lambda: m.voix_francaises()
m.avec_preferees = lambda c: c
m.reglages = types.SimpleNamespace(relais_moderation=lambda: False, defaut=lambda c, s: s)
m.preparer_pages = lambda chap_dir, chap, pages, distrib, narr, cat, stats, relais: (
    [{"repliques": [{"page": p["page"], "id": b["id"], "qui": (ancien.get("%d-%d" % (p["page"], b["id"])) or {}).get("qui", "narrateur"), "ton": "TON_NOUVEAU_IA",
                     "texte": "lu", "lire": True} for p in pages for b in p["_bulles"]]}], [])
try:
    rc = m.cmd_preparer(types.SimpleNamespace(chap=CH, pages="%d-%d" % (A, A), traduire=False))
    doc = json.load(open(os.path.join(T, CH, "dialogues", "dialogues.json"), encoding="utf-8"))
    page = [x for x in doc["repliques"] if x["page"] == A]
    check("preparation terminee (code 0)", rc in (0, None), rc)
    gardes = [x for x in page if x["cle"] != change and (ancien.get(x["cle"]) or {}).get("ton") is not None and (ancien[x["cle"]].get("corrige") or {}).get("ton") is None]
    check("texte et personnage inchanges -> ANCIEN ton garde (%d repliques)" % len(gardes), gardes and all(x["ton"] == ancien[x["cle"]]["ton"] for x in gardes),
          [(x["cle"], x["ton"], ancien[x["cle"]]["ton"]) for x in gardes][:3])
    x = next(x for x in page if x["cle"] == change)
    check("texte change -> ton propose par l'IA", x["ton"] == "TON_NOUVEAU_IA", x["ton"])
finally:
    shutil.rmtree(T, ignore_errors=True)
print("\nVERDICT : %d/%d" % (len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
