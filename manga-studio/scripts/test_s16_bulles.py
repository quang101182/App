"""Banc S16 (28/09/2026) -- verification des bulles apres traduction + petits cris + reponse illisible (dialogues.py 1.29.0).

Vecu (chapitre de la secondaire, geometrie reelle ci-dessous, AUCUN texte ni nom) : Quang valide p.4-15 sur la DETECTION,
puis « Tout faire » les traduit ; la traduction ajoute des « complements » (n° 1xx). Avant 1.29.0 : les 3 bulles qu'il avait
ENTOUREES (p.8) etaient lues 2 fois, et des cris jamais vus (p.9, p.11) entraient dans la preparation.
  A. appliquer_verif : p.8 = 5 bulles dans SON ordre, zero doublon ; p.9 = rien (il avait tout exclu) ; p.11 = ses 2 bulles.
  B. est_gimmick : table de reference partagee avec l'app (cas_petits_cris.json).
  C. preparer_pages : un lot dont la reponse est illisible -> scinde, la page fautive « a traiter », jamais un plantage.
Usage : python test_s16_bulles.py [--mutation]   (--mutation : 1.28.0 -> doit etre ROUGE)
"""
import json, os, sys, types
ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

if "--mutation" in sys.argv:
    import importlib.util, importlib.machinery
    _f = os.path.join(ICI, "dialogues.py.bak-1280")
    sp = importlib.util.spec_from_file_location("dialogues", _f, loader=importlib.machinery.SourceFileLoader("dialogues", _f))
    d = importlib.util.module_from_spec(sp); sys.modules["dialogues"] = d; sp.loader.exec_module(d)
else:
    import dialogues as d

OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print("  [%s] %s%s" % ("OK" if cond else "KO", nom, (" -- %s" % str(detail)[:140]) if detail != "" else ""))


GEO = json.loads(r'''{"8":{"verif":{"ordre":[{"id":1,"box":{"x":0.032,"y":0.0386,"w":0.1161,"h":0.1117}},{"id":900,"box":{"x":0.3464,"y":0.1812,"w":0.2645,"h":0.1711}},{"id":901,"box":{"x":0.0906,"y":0.4518,"w":0.1518,"h":0.1977}},{"id":902,"box":{"x":0.7028,"y":0.6226,"w":0.2369,"h":0.2189}},{"id":2,"box":{"x":0.202,"y":0.8015,"w":0.0825,"h":0.0695}}],"exclues":[],"ajouts":[{"id":900,"box":{"x":0.3464,"y":0.1812,"w":0.2645,"h":0.1711}},{"id":901,"box":{"x":0.0906,"y":0.4518,"w":0.1518,"h":0.1977}},{"id":902,"box":{"x":0.7028,"y":0.6226,"w":0.2369,"h":0.2189}}]},"bulles":[{"id":1,"box":{"x":0.032,"y":0.0386,"w":0.1161,"h":0.1117},"type":"dialogue"},{"id":2,"box":{"x":0.202,"y":0.8015,"w":0.0825,"h":0.0695},"type":"dialogue"},{"id":102,"box":{"x":0.4348,"y":0.2215,"w":0.1044,"h":0.138},"type":"dialogue"},{"id":103,"box":{"x":0.0973,"y":0.5052,"w":0.1404,"h":0.1705},"type":"dialogue"},{"id":104,"box":{"x":0.8132,"y":0.6478,"w":0.1566,"h":0.1914},"type":"dialogue"}]},"9":{"verif":{"ordre":[],"exclues":[{"id":1,"box":{"x":0.2253,"y":0.4043,"w":0.1641,"h":0.1557}},{"id":2,"box":{"x":0.942,"y":0.7365,"w":0.0408,"h":0.0435}}],"ajouts":[]},"bulles":[{"id":1,"box":{"x":0.2253,"y":0.4043,"w":0.1641,"h":0.1557},"type":"dialogue"},{"id":2,"box":{"x":0.942,"y":0.7365,"w":0.0408,"h":0.0435},"type":"dialogue"},{"id":102,"box":{"x":0.0604,"y":0.793,"w":0.0371,"h":0.058},"type":"dialogue"},{"id":103,"box":{"x":0.3295,"y":0.7669,"w":0.036,"h":0.0592},"type":"dialogue"}]},"11":{"verif":{"ordre":[{"id":3,"box":{"x":0.2284,"y":0.661,"w":0.0823,"h":0.0698}},{"id":4,"box":{"x":0.0557,"y":0.7321,"w":0.0864,"h":0.107}}],"exclues":[{"id":1,"box":{"x":0.2194,"y":0.1878,"w":0.0225,"h":0.0404}},{"id":2,"box":{"x":0.651,"y":0.3808,"w":0.0687,"h":0.1408}}],"ajouts":[]},"bulles":[{"id":3,"box":{"x":0.2284,"y":0.661,"w":0.0823,"h":0.0698},"type":"dialogue"},{"id":4,"box":{"x":0.0557,"y":0.7321,"w":0.0864,"h":0.107},"type":"dialogue"},{"id":104,"box":{"x":0.6688,"y":0.0506,"w":0.0464,"h":0.0638},"type":"dialogue"},{"id":105,"box":{"x":0.8216,"y":0.0794,"w":0.0499,"h":0.0673},"type":"dialogue"},{"id":106,"box":{"x":0.3002,"y":0.554,"w":0.0406,"h":0.0441},"type":"dialogue"},{"id":107,"box":{"x":0.449,"y":0.5522,"w":0.0441,"h":0.0255},"type":"dialogue"}]}}''')
d.log = lambda *a: None

print("=== A. la liste validee par Quang fait loi apres la traduction (geometrie reelle)")
verif = {"pages": {k: v["verif"] for k, v in GEO.items()}}
r = {k: d.appliquer_verif(int(k), [dict(b, trad="texte %d" % b["id"]) for b in v["bulles"]], verif) for k, v in GEO.items()}
check("A. p.8 : 5 bulles (ses 2 detectees + ses 3 entourees), pas 8", len(r["8"]) == 5, [b["id"] for b in r["8"]])
check("A. p.8 : ses entourees = les complements 102-104 (un seul numero chacune)", sorted(b["id"] for b in r["8"]) == [1, 2, 102, 103, 104],
      [b["id"] for b in r["8"]])
check("A. p.8 : dans SON ordre (1, entourees, 2)", [b["id"] for b in r["8"]][0] == 1 and [b["id"] for b in r["8"]][-1] == 2, [b["id"] for b in r["8"]])
check("A. p.9 : il avait TOUT exclu -> rien (les cris 102-103 apparus apres ne rentrent pas)", r["9"] == [], [b["id"] for b in r["9"]])
check("A. p.11 : ses 2 bulles seulement (104-107 apparus apres : exclus)", [b["id"] for b in r["11"]] == [3, 4], [b["id"] for b in r["11"]])

print("=== B. petits cris : table de reference (commune a l'app)")
T = json.load(open(os.path.join(ICI, "cas_petits_cris.json"), encoding="utf-8"))
if hasattr(d, "est_gimmick"):
    fx = [t for t in T["cris"] if not d.est_gimmick(t)]
    fr = [t for t in T["repliques"] if d.est_gimmick(t)]
    check("B. %d cris reconnus" % len(T["cris"]), not fx, fx)
    check("B. %d vraies repliques jamais prises pour un cri" % len(T["repliques"]), not fr, fr)
else:
    check("B. est_gimmick existe", False)

print("=== C. reponse illisible pendant la preparation : jamais un plantage")
appels = []


def faux_lot(chap_dir, lot, distrib, narr, cat, stats):
    appels.append([p["page"] for p in lot])
    if any(p["page"] == 6 for p in lot):
        raise ValueError("pas de JSON dans la reponse : texte libre")
    return {"repliques": [{"page": p["page"]} for p in lot], "nouveaux": []}, 0.0


d.preparer_lot = faux_lot
d.fusionner_distribution = lambda *a, **k: []
d.nc.progres = lambda *a, **k: None
try:
    rep, a_traiter = d.preparer_pages("x", "x/ch_1", [{"page": n} for n in (5, 6, 7)], {"persos": []}, None, [], {}, False)
    check("C. pas d'exception", True)
    check("C. lot scinde puis page 6 « a traiter »", a_traiter == [6], (appels, a_traiter))
    check("C. pages 5 et 7 preparees", sorted(x["page"] for r_ in rep for x in r_["repliques"]) == [5, 7])
except Exception as e:
    check("C. pas d'exception", False, "%s %s" % (type(e).__name__, str(e)[:100]))

print("\nVERDICT %s : %d/%d" % ("VERT" if not KO else "ROUGE", len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
