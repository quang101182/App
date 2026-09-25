# -*- coding: utf-8 -*-
"""Banc narrate_chapter 2.10.0 -> 2.12.0 + traduire_chapitre 2.0.0 + reglages 1.2.0 : relais AUTOMATIQUE de moderation (Quang 25/09 09h50). HORS LIGNE :
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


def faux_appel(kimi_refuse, pixtral_refuse=False):
    def appel(engine, sys_, content, budget):
        txt = " ".join(c.get("text", "") for c in content if c.get("type") == "text")
        pages = [int(x.split()[1]) for x in txt.split("PAGE ")[0:0]] or \
                [int(c["text"].split()[1]) for c in content if c.get("type") == "text" and c["text"].startswith("PAGE ")]
        APPELS.append((engine, pages, txt))
        def refuse(m, motif):
            e = mod.Refus(m, motif); e.usage = {"prompt_tokens": 1000, "completion_tokens": 0}; raise e   # image lue = facturee
        if engine == "gemini" and 2 in pages:
            refuse("gemini", "Gemini a arrete sa reponse pour securite (PROHIBITED_CONTENT)")
        if engine == "kimi" and kimi_refuse:
            refuse("kimi", "refus kimi (banc)")
        if engine == "pixtral" and pixtral_refuse:
            refuse("pixtral", "refus pixtral (banc)")
        return json.dumps({"pages": [{"page": p, "type": "histoire", "faits": "faits p%d par %s" % (p, engine), "presents": []}
                                     for p in pages], "resume": "RESUME-APRES-%s" % pages, "nouveaux": [], "noms": []}), \
            {"prompt_tokens": 10, "completion_tokens": 10}
    return appel


PAGES = [{"num": 1, "file": "a.jpg"}, {"num": 2, "file": "b.jpg"}, {"num": 3, "file": "c.jpg"}]


def lancer(relais, kimi_refuse, pixtral_refuse=False):
    del APPELS[:]
    nc.RELAIS = relais
    nc.appel_vision = faux_appel(kimi_refuse, pixtral_refuse)
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
tr = p2.get("trace") or {}
check("TRACE : lue par kimi, refusée par gemini (motif + heure), « relais automatique »",
      tr.get("lu_par") == "kimi" and [r["moteur"] for r in tr.get("refuse_par", [])] == ["gemini"]
      and "PROHIBITED" in tr["refuse_par"][0]["motif"] and tr["refuse_par"][0]["t"] and tr.get("comment") == "relais automatique", tr)
check("TRACE : les pages sans refus n'en portent pas", all("trace" not in x for x in s if x["page"] != 2))
check("ordre des pages gardé", [x["page"] for x in s] == [1, 2, 3], [x["page"] for x in s])
check("page 3 revenue à gemini", [a[0] for a in APPELS if a[1] == [3]] == ["gemini"])
u = {"prompt_tokens": 10, "completion_tokens": 10}; R = {"prompt_tokens": 1000, "completion_tokens": 0}
G, K = nc.ENGINES["gemini"][1], nc.ENGINES["kimi"][1]
attendu = 2 * nc.cout(G, u) + nc.cout(G, R) + nc.cout(K, u)
check("COÛT juste : 2 appels gemini + le REFUS de gemini (facturé) + 1 appel kimi au tarif KIMI", abs(st["cout_vision"] - attendu) < 1e-12
      and nc.cout(nc.ENGINES["gemini"][1], u) != nc.cout(nc.ENGINES["kimi"][1], u), (st["cout_vision"], attendu))
print("=== 2. relais ACTIF, kimi refuse aussi -> PIXTRAL en dernier recours")
s, st = lancer(True, True)
p2 = [x for x in s if x["page"] == 2][0]
check("page 2 lue par PIXTRAL après gemini puis kimi", [a[0] for a in APPELS if a[1] == [2]] == ["gemini", "kimi", "pixtral"]
      and p2["type"] == "histoire" and "pixtral" in p2["faits"], [a[0] for a in APPELS if a[1] == [2]])
check("TRACE : lue par pixtral, refusée par gemini puis kimi", (p2.get("trace") or {}).get("lu_par") == "pixtral"
      and [r["moteur"] for r in p2["trace"]["refuse_par"]] == ["gemini", "kimi"], p2.get("trace"))
check("aucune alerte", not st.get("moderation"), st.get("moderation"))
check("COÛT : refus gemini + refus kimi facturés à leur tarif, pixtral à 0 $ (offre gratuite)",
      abs(st["cout_vision"] - (2 * nc.cout(G, u) + nc.cout(G, R) + nc.cout(K, R) + 0.0)) < 1e-12, st["cout_vision"])
print("=== 2b. relais ACTIF, les TROIS refusent")
s, st = lancer(True, True, True)
p2 = [x for x in s if x["page"] == 2][0]
check("page 2 mise de côté après gemini, kimi, pixtral (pas de boucle)", p2["type"] == "moderation"
      and [a[0] for a in APPELS if a[1] == [2]] == ["gemini", "kimi", "pixtral"], [a[0] for a in APPELS if a[1] == [2]])
check("alerte au nom du dernier moteur (pixtral)", [m["moteur"] for m in st.get("moderation", [])] == ["pixtral"], st.get("moderation"))
check("TRACE : non lue, refusée par les trois, « mise de côté (alerte) »", (p2.get("trace") or {}).get("lu_par") is None
      and [r["moteur"] for r in p2["trace"]["refuse_par"]] == ["gemini", "kimi", "pixtral"]
      and p2["trace"]["comment"] == "mise de côté (alerte)", p2.get("trace"))
print("=== 2c. reprise CHOISIE par Quang (« À traiter ») : la trace se complète")
nc.RELAIS = False; nc.appel_vision = faux_appel(False)
vis = nc.reprendre_moderation("x", [dict(p2), dict(s[0])], "kimi", {"vision_tokens_in": 0, "vision_tokens_out": 0,
                              "cout_vision": 0.0, "vision_s": 0.0}, {}, "gemini")
r2 = [x for x in vis if x["page"] == 2][0]
check("reprise : lue par kimi, les refus d'avant gardés, « reprise choisie dans « À traiter » »",
      r2["trace"]["lu_par"] == "kimi" and [r["moteur"] for r in r2["trace"]["refuse_par"]] == ["gemini", "kimi", "pixtral"]
      and "À traiter" in r2["trace"]["comment"], r2.get("trace"))
print("=== 3. relais COUPÉ")
s, st = lancer(False, False)
check("kimi jamais appelé", not [a for a in APPELS if a[0] == "kimi"])
check("page 2 mise de côté comme avant", [x["type"] for x in s if x["page"] == 2] == ["moderation"])
check("COÛT relais coupé : 2 appels gemini + le refus de gemini (désormais compté)",
      abs(st["cout_vision"] - (2 * nc.cout(G, u) + nc.cout(G, R))) < 1e-12, st["cout_vision"])
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
print("=== 5. NOMS (narrate 2.12.0) : relais + coût des refus")
def faux_noms(refusent):
    def appel(engine, sys_, content, budget, **kw):
        APPELS.append((engine, budget, kw))
        if engine in refusent:
            e = mod.Refus(engine, "refus %s (banc)" % engine); e.usage = {"prompt_tokens": 1000, "completion_tokens": 0}; raise e
        return json.dumps({"noms": [{"nom": "Raki", "porteur_age": "adulte"}]}), {"prompt_tokens": 10, "completion_tokens": 10}
    return appel
PAGE5 = {"num": 5, "file": "a.jpg"}
del APPELS[:]; nc.RELAIS = True; nc.appel_vision = faux_noms({"gemini"}); st = {}
r = nc._question_noms("x", PAGE5, st)
check("noms, relais ACTIF : gemini refuse → kimi répond (même question)", r and r[0]["nom"] == "Raki"
      and [a[0] for a in APPELS] == ["gemini", "kimi"], [a[0] for a in APPELS])
check("noms : kimi reçoit un budget qui laisse place à son raisonnement (≥ 16 000)", APPELS[1][1] >= 16000, APPELS[1][1])
check("noms : relais noté (étape noms)", st.get("relais") == [{"page": 5, "de": "gemini", "vers": "kimi", "etape": "noms"}], st.get("relais"))
check("noms : COÛT = refus gemini (tarif gemini) + réponse kimi (tarif kimi)",
      abs(st["cout_noms"] - (nc.cout(G, R) + nc.cout(K, u))) < 1e-12, st.get("cout_noms"))
del APPELS[:]; nc.RELAIS = False; nc.appel_vision = faux_noms({"gemini"}); st = {}
r = nc._question_noms("x", PAGE5, st)
check("noms, relais COUPÉ : aucun nom, kimi jamais appelé", r == [] and [a[0] for a in APPELS] == ["gemini"], [a[0] for a in APPELS])
check("noms, relais COUPÉ : le refus est COMPTÉ (avant : perdu)", abs(st.get("cout_noms", 0) - nc.cout(G, R)) < 1e-12
      and st.get("refus_noms", [{}])[0].get("moteur") == "gemini", (st.get("cout_noms"), st.get("refus_noms")))
del APPELS[:]; nc.RELAIS = True; nc.appel_vision = faux_noms({"gemini", "kimi", "pixtral"}); st = {}
r = nc._question_noms("x", PAGE5, st)
check("noms : les trois refusent → aucun nom, pas de boucle", r == [] and [a[0] for a in APPELS] == ["gemini", "kimi", "pixtral"])

print("=== 6. RÉCIT (narrate 2.12.0) : DeepSeek → Kimi → Gemini, même contexte")
POSTS = []
def faux_post(refus_mode):
    def post(path, body, timeout=240):
        lot = json.loads(body["messages"][1]["content"].split("\nPages :\n", 1)[1])
        nums = [x["page"] for x in lot]; POSTS.append(nums)
        if 2 in nums:
            if refus_mode == "http":
                raise mod.Refus("deepseek", "Content Exists Risk (banc)")
            return {"choices": [{"message": {"content": "I'm sorry, but I can't help with that."}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 500, "completion_tokens": 12}}
        return {"choices": [{"message": {"content": json.dumps({"titre": "T", "pages": [{"page": n, "narration": "p%d par deepseek" % n} for n in nums]})},
                             "finish_reason": "stop"}], "usage": u}
    return post
def faux_relais_recit(refusent):
    def appel(engine, sys_, content, budget, **kw):
        txt = content[0]["text"]; APPELS.append((engine, budget, txt))
        if engine in refusent:
            e = mod.Refus(engine, "refus %s (banc)" % engine); e.usage = {"prompt_tokens": 800, "completion_tokens": 0}; raise e
        lot = json.loads(txt.split("\nPages :\n", 1)[1])
        return json.dumps({"titre": "", "pages": [{"page": x["page"], "narration": "p%d par %s" % (x["page"], engine)} for x in lot]}), u
    return appel
def recit(relais, refus_mode, refusent=()):
    del APPELS[:]; del POSTS[:]; nc.TRACES_RECIT.clear()
    nc.RELAIS = relais; nc.post = faux_post(refus_mode); nc.appel_vision = faux_relais_recit(set(refusent))
    pages = [{"page": n, "type": "histoire", "faits": "faits %d" % n} for n in (1, 2, 3)]
    st = {"cout_recit": 0.0, "recit_s": 0.0}
    titre, pages = nc.etape_recit_v2(pages, "", [{"id": "A", "nom": "Raki"}], st)
    return {p["page"]: p for p in pages}, st
DS = "deepseek-v4-flash"
P, st = recit(True, "http")
check("récit, refus HTTP : page 2 écrite par KIMI, les autres par DeepSeek",
      [P[n]["narration"] for n in (1, 2, 3)] == ["p1 par deepseek", "p2 par kimi", "p3 par deepseek"], [P[n]["narration"] for n in (1, 2, 3)])
check("récit : MÊME contexte pour kimi (fiche des personnages + consigne)", APPELS and "Raki" in APPELS[0][2] and "Fiche des personnages" in APPELS[0][2])
check("récit : TRACE « ✍ récit par kimi (refusé par deepseek) » sur la page 2 seulement",
      (P[2].get("trace_recit") or {}).get("lu_par") == "kimi" and [r["moteur"] for r in P[2]["trace_recit"]["refuse_par"]] == ["deepseek"]
      and not any("trace_recit" in P[n] for n in (1, 3)), P[2].get("trace_recit"))
check("récit : aucune alerte, relais noté", not st.get("moderation") and {"page": 2, "de": "deepseek", "vers": "kimi", "etape": "recit"} in st.get("relais", []))
n_ok = sum(1 for x in POSTS if 2 not in x)
check("récit : COÛT = appels DeepSeek réussis + kimi à son tarif (refus HTTP non facturé)",
      abs(st["cout_recit"] - (n_ok * nc.cout(DS, u) + nc.cout(K, u))) < 1e-12, (st["cout_recit"], POSTS))
P, st = recit(True, "texte")
n_ref = sum(1 for x in POSTS if 2 in x)
check("récit, refus EN TOUTES LETTRES (200) : reconnu comme refus → relais kimi (avant : « JSON illisible »)",
      P[2]["narration"] == "p2 par kimi", P[2]["narration"])
check("récit : le refus en toutes lettres est FACTURÉ (jetons comptés)",
      abs(st["cout_recit"] - (n_ok * nc.cout(DS, u) + n_ref * nc.cout(DS, {"prompt_tokens": 500, "completion_tokens": 12}) + nc.cout(K, u))) < 1e-12,
      st["cout_recit"])
P, st = recit(True, "http", ("kimi",))
check("récit : kimi refuse aussi → GEMINI écrit, trace deepseek puis kimi",
      P[2]["narration"] == "p2 par gemini" and [r["moteur"] for r in P[2]["trace_recit"]["refuse_par"]] == ["deepseek", "kimi"])
check("récit : refus de kimi facturé à son tarif", abs(st["cout_recit"] - (n_ok * nc.cout(DS, u) + nc.cout(K, {"prompt_tokens": 800, "completion_tokens": 0})
      + nc.cout(G, u))) < 1e-12, st["cout_recit"])
P, st = recit(True, "http", ("kimi", "gemini"))
check("récit : tous refusent → page sans narration + ALERTE (dernier moteur : gemini)", P[2]["narration"] == ""
      and [m["moteur"] for m in st.get("moderation", [])] == ["gemini"] and P[2]["trace_recit"]["lu_par"] is None, st.get("moderation"))
P, st = recit(False, "http")
check("récit, relais COUPÉ : comportement d'avant (alerte deepseek, aucun relais)", P[2]["narration"] == "" and not APPELS
      and [m["moteur"] for m in st.get("moderation", [])] == ["deepseek"])
check("récit : une page REFUSÉE n'est pas redemandée comme « vide » (aucun appel payé en trop)",
      POSTS == [[1, 2, 3], [1], [2, 3], [2], [3]], POSTS)

print("=== 7. TRADUCTION (traduire_chapitre 2.0.0) : relais + coût des refus")
import traduire_chapitre as tc
from PIL import Image
IM = Image.new("RGB", (300, 400), "white"); TX = [{"id": 1, "x": 0.1, "y": 0.1, "w": 0.3, "h": 0.1}]
def faux_trad(refusent):
    def appel(engine, sys_, content, budget, **kw):
        APPELS.append((engine, budget, len(content)))
        if engine in refusent:
            e = mod.Refus(engine, "refus %s (banc)" % engine); e.usage = {"prompt_tokens": 1500, "completion_tokens": 0}; raise e
        return json.dumps({"bulles": [{"id": 1, "type": "bulle", "texte": "x", "trad": "y par " + engine}]}), u
    return appel
def trad(refusent, relais):
    del APPELS[:]; tc.nc.appel_vision = faux_trad(set(refusent))
    st = dict(tokens_in=0, tokens_out=0, cout=0.0)
    try:
        tr, trace = tc.traduire_avec_relais(IM, TX, "gemini", "fr", st, relais); return tr, trace, st, None
    except mod.Refus as e:
        return None, None, st, e
tr, trace, st, e = trad({"gemini"}, True)
check("traduction, relais ACTIF : gemini refuse → kimi traduit la MÊME page (mêmes bulles)",
      tr and tr[1]["trad"] == "y par kimi" and [a[0] for a in APPELS] == ["gemini", "kimi"] and APPELS[0][2] == APPELS[1][2], APPELS)
check("traduction : trace (lue par kimi, refusée par gemini)", trace and trace["lu_par"] == "kimi"
      and [r["moteur"] for r in trace["refuse_par"]] == ["gemini"] and st.get("relais") == [{"de": "gemini", "vers": "kimi"}], trace)
check("traduction : COÛT = refus gemini + kimi à son tarif", abs(st["cout"] - (nc.cout(G, {"prompt_tokens": 1500, "completion_tokens": 0}) + nc.cout(K, u))) < 1e-12, st["cout"])
tr, trace, st, e = trad({"gemini"}, False)
check("traduction, relais COUPÉ : refus levé (page en VO + alerte), kimi jamais appelé",
      e is not None and [a[0] for a in APPELS] == ["gemini"] and e.trace["lu_par"] is None)
check("traduction, relais COUPÉ : le refus est COMPTÉ (avant : perdu)", abs(st["cout"] - nc.cout(G, {"prompt_tokens": 1500, "completion_tokens": 0})) < 1e-12, st["cout"])
tr, trace, st, e = trad({"gemini", "kimi", "pixtral"}, True)
check("traduction : les trois refusent → refus levé, trace des trois, alerte au nom de pixtral",
      e is not None and e.moteur == "pixtral" and [r["moteur"] for r in e.trace["refuse_par"]] == ["gemini", "kimi", "pixtral"])
tr, trace, st, e = trad(set(), True)
check("traduction sans refus : aucune trace, un seul appel", trace is None and len(APPELS) == 1)
print("\nVERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
