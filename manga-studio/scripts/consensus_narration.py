# -*- coding: utf-8 -*-
"""CONSENSUS de deux releves independants d'un meme chapitre : « desaccord = prudence ».

Constat du banc de fidelite (21/09) : les erreurs graves restantes CHANGENT d'un run a l'autre (K3 :
1/2/1, pas les memes pages ; Gemini : repliques de figurants donnees a Raki/Zaki). Deux lectures
independantes se trompent donc rarement AU MEME ENDROIT. On fusionne leurs FAITS page par page
(texte seul, DeepSeek) :
  - un nom n'est garde que si les DEUX releves attribuent la meme parole/action au meme personnage ;
  - desaccord ou doute -> sujet anonyme ("une voix", "un villageois") : une prudence, jamais un contresens ;
  - un evenement vu par un seul releve et CONTREDIT par l'autre est retire.
Puis le recit v2 est reecrit sur ces faits fusionnes (meme fonction que narrate_chapter).

Usage : python consensus_narration.py claymore/ch_1 <tagA> <tagB> <tag_sortie>
"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import narrate_chapter as nc

SYS_FUSION = """Deux lecteurs INDEPENDANTS ont releve les faits des memes pages de manga. Fusionne-les en un releve
unique, le plus SUR possible :
- QUI parle / agit : garde un NOM de personnage seulement si les DEUX releves attribuent cette parole ou cette
  action au MEME personnage nomme. S'ils divergent, ou si l'un des deux l'attribue a un anonyme ou a quelqu'un
  d'autre, ecris un sujet anonyme exact ("une voix", "un villageois", "un homme", "un garcon").
- evenements : garde ce que les deux rapportent (meme formule differemment). Un element present chez un seul
  lecteur est garde seulement s'il ne CONTREDIT pas l'autre et reste secondaire ; s'il le contredit, retire-le.
- n'invente rien, ne commente pas, garde l'ordre des cases.
- "type" : si les deux lecteurs divergent, prends "histoire".
Reponds UNIQUEMENT en JSON : {"pages":[{"page":N,"type":"...","faits":"...","desaccords":["..."]}]}"""


def charger(chap, tag):
    return json.load(open(os.path.join(nc.SOURCES, chap, "narration", tag, "narration.json"), encoding="utf-8"))


def fusion(chap, tag_a, tag_b, tag_out, lot=5):
    a, b = charger(chap, tag_a), charger(chap, tag_b)
    pa, pb = {p["page"]: p for p in a["pages"]}, {p["page"]: p for p in b["pages"]}
    noms = (a.get("stats") or {}).get("noms") or {}
    stats = dict(cout_recit=0.0, recit_s=0.0, cout_fusion=0.0)
    pages_num = sorted(set(pa) & set(pb))
    fusionnes, desaccords = {}, []
    for i in range(0, len(pages_num), lot):
        grp = pages_num[i:i + lot]
        entree = [{"page": n, "type_A": pa[n]["type"], "faits_A": pa[n]["faits"],
                   "type_B": pb[n]["type"], "faits_B": pb[n]["faits"]} for n in grp]
        body = {"model": "deepseek-v4-flash", "max_tokens": 6000, "temperature": 0, "thinking": {"type": "disabled"},
                "messages": [{"role": "system", "content": SYS_FUSION},
                             {"role": "user", "content": "Personnages nommes (age, cheveux) : "
                              + json.dumps({k: "%s, %s" % (v["age"], v["cheveux"]) for k, v in noms.items()}, ensure_ascii=False)
                              + "\nPages :\n" + json.dumps(entree, ensure_ascii=False)}]}
        r = nc.post("/api/deepseek", body)
        stats["cout_fusion"] += nc.cout("deepseek-v4-flash", r.get("usage") or {})
        for x in nc.parse_json(r["choices"][0]["message"]["content"]).get("pages") or []:
            try:
                fusionnes[int(x["page"])] = x
            except (KeyError, TypeError, ValueError):
                pass
    pages = []
    for n in pages_num:
        x = fusionnes.get(n) or {"type": pa[n]["type"], "faits": pa[n]["faits"], "desaccords": ["fusion absente"]}
        pages.append({"page": n, "file": pa[n]["file"], "type": x.get("type", "histoire"), "faits": x.get("faits", ""),
                      "faits_A": pa[n]["faits"], "faits_B": pb[n]["faits"], "narration": ""})
        desaccords += [{"page": n, "d": d} for d in (x.get("desaccords") or [])]
    persos = [{"id": k.lower(), "nom": k, "qui": "%s, %s" % (v["age"], v["cheveux"])} for k, v in noms.items()]
    titre, pages = nc.etape_recit_v2(pages, "", persos, stats)
    out = os.path.join(nc.SOURCES, chap, "narration", tag_out)
    os.makedirs(out, exist_ok=True)
    cout_total = round((a["stats"].get("cout_total") or 0) + (b["stats"].get("cout_total") or 0)
                       + stats["cout_fusion"] + stats["cout_recit"], 4)
    res = {"version": nc.VERSION, "prompt": "consensus", "sources": [tag_a, tag_b], "engine": "consensus",
           "titre": titre, "personnages": persos,
           "stats": {"noms": noms, "cout_fusion": round(stats["cout_fusion"], 4), "cout_total": cout_total,
                     "desaccords": desaccords, "total_s": max(a["stats"].get("total_s", 0), b["stats"].get("total_s", 0))},
           "pages": pages}
    json.dump(res, open(os.path.join(out, "narration.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("%s = %s + %s : %d desaccord(s), cout total %.3f $ (dont fusion+recit %.4f $)"
          % (tag_out, tag_a, tag_b, len(desaccords), cout_total, stats["cout_fusion"] + stats["cout_recit"]))


if __name__ == "__main__":
    nc.SECRET = nc._secret()
    fusion(*sys.argv[1:5])
