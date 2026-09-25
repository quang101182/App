# -*- coding: utf-8 -*-
"""Banc narrate_chapter 2.10.0 + reglages 1.2.0 : relais AUTOMATIQUE de moderation (Quang 25/09 09h50). HORS LIGNE :
aucun appel paye -- appel_vision est SIMULE (gemini refuse la page 2 ; kimi l'accepte ou la refuse selon le cas).
1. relais ACTIF : la page 2 refusee par gemini est relue par KIMI, dans la meme boucle, avec le MEME contexte (la fiche
   et les « faits precedents » de la page 1 sont dans sa requete) ; aucune alerte ; ordre des pages garde ;
2. relais ACTIF mais kimi refuse aussi : page mise de cote + alerte (moteur = kimi), pas de boucle infinie ;
3. relais COUPE : comportement d'avant (mise de cote apres le refus de gemini, kimi jamais appele) ;
4. reglages : cle absente = NON ; ecrire(True) / ecrire(False) ; valeur non booleenne refusee ; le mode n'est pas touche.
Usage : python test_relais_moderation.py
"""
import json, os, sys, tempfile
ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


import narrate_chapter as nc
import moderation as mod
nc.progres = lambda *a, **k: None
nc.journal = lambda *a, **k: None
nc.log = lambda *a, **k: None
nc.page_jpeg = lambda path: b"\xff\xd8banc"
APPELS = []


def faux_appel(kimi_refuse):
    def appel(engine, sys_, content, budget):
        txt = " ".join(c.get("text", "") for c in content if c.get("type") == "text")
        pages = [int(x.split()[1]) for x in txt.split("PAGE ")[0:0]] or \
                [int(c["text"].split()[1]) for c in content if c.get("type") == "text" and c["text"].startswith("PAGE ")]
        APPELS.append((engine, pages, txt))
        if engine == "gemini" and 2 in pages:
            raise mod.Refus("gemini", "Gemini a arrete sa reponse pour securite (PROHIBITED_CONTENT)")
        if engine == "kimi" and kimi_refuse:
            raise mod.Refus("kimi", "refus kimi (banc)")
        return json.dumps({"pages": [{"page": p, "type": "histoire", "faits": "faits p%d par %s" % (p, engine), "presents": []}
                                     for p in pages], "resume": "RESUME-APRES-%s" % pages, "nouveaux": [], "noms": []}), \
            {"prompt_tokens": 10, "completion_tokens": 10}
    return appel


PAGES = [{"num": 1, "file": "a.jpg"}, {"num": 2, "file": "b.jpg"}, {"num": 3, "file": "c.jpg"}]


def lancer(relais, kimi_refuse):
    del APPELS[:]
    nc.RELAIS = relais
    nc.appel_vision = faux_appel(kimi_refuse)
    stats = {"vision_tokens_in": 0, "vision_tokens_out": 0, "cout_vision": 0.0, "vision_s": 0.0}
    sortie, resume, persos = nc.etape_vision_v2("x", PAGES, "gemini", 1, stats)
    return sortie, stats


print("=== 1. relais ACTIF, kimi accepte")
s, st = lancer(True, False)
p2 = [x for x in s if x["page"] == 2][0]
k = [a for a in APPELS if a[0] == "kimi"]
check("page 2 relue par kimi (une seule fois)", len(k) == 1 and k[0][1] == [2], [(a[0], a[1]) for a in APPELS])
check("page 2 analysée (pas mise de côté)", p2["type"] == "histoire" and "kimi" in p2["faits"], p2)
check("MÊME contexte : les faits de la page 1 sont dans la requête de kimi", "RESUME-APRES-[1]" in k[0][2])
check("aucune alerte", not st.get("moderation"), st.get("moderation"))
check("relais noté dans les stats", st.get("relais") == [{"page": 2, "de": "gemini", "vers": "kimi"}], st.get("relais"))
check("ordre des pages gardé", [x["page"] for x in s] == [1, 2, 3], [x["page"] for x in s])
check("page 3 revenue à gemini", [a[0] for a in APPELS if a[1] == [3]] == ["gemini"])
u = {"prompt_tokens": 10, "completion_tokens": 10}
attendu = 2 * nc.cout(nc.ENGINES["gemini"][1], u) + nc.cout(nc.ENGINES["kimi"][1], u)
check("COÛT juste : 2 appels gemini au tarif gemini + 1 appel kimi au tarif KIMI", abs(st["cout_vision"] - attendu) < 1e-12
      and nc.cout(nc.ENGINES["gemini"][1], u) != nc.cout(nc.ENGINES["kimi"][1], u), (st["cout_vision"], attendu))
print("=== 2. relais ACTIF, kimi refuse aussi")
s, st = lancer(True, True)
p2 = [x for x in s if x["page"] == 2][0]
check("page 2 mise de côté après les DEUX refus", p2["type"] == "moderation", p2.get("type"))
check("alerte au nom du 2e moteur (kimi)", [m["moteur"] for m in st.get("moderation", [])] == ["kimi"], st.get("moderation"))
check("pas de boucle : gemini 1× + kimi 1× pour la page 2", [a[0] for a in APPELS if a[1] == [2]] == ["gemini", "kimi"])
print("=== 3. relais COUPÉ")
s, st = lancer(False, False)
check("kimi jamais appelé", not [a for a in APPELS if a[0] == "kimi"])
check("page 2 mise de côté comme avant", [x["type"] for x in s if x["page"] == 2] == ["moderation"])
check("COÛT relais coupé : 2 appels gemini facturés (le refusé ne l'est pas, comme avant)",
      abs(st["cout_vision"] - 2 * nc.cout(nc.ENGINES["gemini"][1], u)) < 1e-12, st["cout_vision"])
print("=== 4. reglages")
import importlib
d = tempfile.mkdtemp(); f = os.path.join(d, "_reglages.json")
os.environ["MANGA_REGLAGES"] = f
import reglages; importlib.reload(reglages)
open(f, "w").write('{"mode": "pc"}')
check("clé absente = relais NON", reglages.relais_moderation() is False)
reglages.ecrire(relais_moderation=True)
check("ecrire(True) → OUI, le mode reste « pc »", reglages.relais_moderation() is True and reglages.sur_pc())
reglages.ecrire(relais_moderation=False)
check("ecrire(False) → NON", reglages.relais_moderation() is False)
try:
    reglages.ecrire(relais_moderation="oui"); refuse = False
except ValueError:
    refuse = True
check("valeur non booléenne refusée", refuse)
print("\nVERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
