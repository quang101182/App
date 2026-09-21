# -*- coding: utf-8 -*-
"""Banc de FIDELITE d'une narration : chaque page narree est confrontee a une reference de faits.

La reference (sources/<chap>/reference_faits.json) est ecrite A LA MAIN en lisant les pages : c'est la
seule verite du banc. Le juge (DeepSeek, texte seul, temperature 0) ne voit PAS les images : il ne fait
que comparer deux textes, ce qu'il fait bien, au lieu de relire une page, ce qui est justement le
maillon qu'on evalue.

Verdict par page : ok | mineur (embellissement sans consequence) | grave (contresens, invention qui
change l'histoire, personnage confondu, mauvais nom, action attribuee a la mauvaise personne).

Usage : python juge_narration.py claymore/ch_1 banc-k3-charon [autre-tag ...]
"""
import json, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import narrate_chapter as nc

SYS = """Tu es un correcteur de FIDELITE. On te donne, pour une page de manga, une REFERENCE (les faits reels,
etablis par un humain qui a lu la page) et la NARRATION produite par une IA pour cette page, plus la fiche
des personnages. Juge UNIQUEMENT la fidelite de la narration a la reference :
- "grave" : contresens, evenement invente qui change l'histoire, personnage confondu avec un autre, mauvais
  nom, action ou replique attribuee a la mauvaise personne, fait essentiel inverse.
- "mineur" : embellissement d'ambiance, emotion ou detail visuel ajoute SANS consequence sur l'histoire.
- "ok" : fidele (omettre un detail secondaire n'est PAS une faute ; une narration vide pour une page sans
  action est ok).
Sois strict sur les personnages : si la narration donne le nom d'un personnage a un autre, c'est grave.
Reponds UNIQUEMENT en JSON : {"verdict":"ok|mineur|grave","raison":"<une phrase>"}"""


# Style "description d'ecran" : fidele mais plat, le defaut n°1 reproche aux recaps IA (forums). Mesure
# mecanique, pas d'avis de LLM : une tournure interdite presente = une page plate.
PLAT = re.compile(r"(on voit|on aper[cç]oit|gros plan|plan large|la case|cette case|cette page|la page|"
                  r"l'image|la sc[eè]ne montre|montre (?:le|la|les|un|une)|est repr[eé]sent[eé]|appara[iî]t (?:[aà]|en|dans))",
                  re.I)


def juger(chap, tag):
    base = os.path.join(nc.SOURCES, chap)
    ref = json.load(open(os.path.join(base, "reference_faits.json"), encoding="utf-8"))
    nar = json.load(open(os.path.join(base, "narration", tag, "narration.json"), encoding="utf-8"))
    fiche = json.dumps(ref["personnages"], ensure_ascii=False)
    res, cout = [], 0.0
    for p in nar["pages"]:
        r_txt = ref["pages"].get(str(p["page"]))
        if r_txt is None:
            continue
        texte = (p.get("narration") or "").strip()
        body = {"model": "deepseek-v4-flash", "temperature": 0, "max_tokens": 400, "thinking": {"type": "disabled"},
                "messages": [{"role": "system", "content": SYS},
                             {"role": "user", "content": "Personnages : %s\nREFERENCE page %s : %s\nNARRATION : %s"
                              % (fiche, p["page"], r_txt, texte or "(vide)")}]}
        r = nc.post("/api/deepseek", body)
        cout += nc.cout("deepseek-v4-flash", r.get("usage") or {})
        try:
            v = nc.parse_json(r["choices"][0]["message"]["content"])
        except Exception as e:
            v = {"verdict": "illisible", "raison": str(e)[:100]}
        v["plat"] = sorted(set(m.lower() for m in PLAT.findall(texte)))
        res.append({"page": p["page"], **v})
    return res, cout


def main():
    nc.SECRET = nc._secret()
    chap, tags = sys.argv[1], sys.argv[2:]
    bilan = {}
    for tag in tags:
        res, cout = juger(chap, tag)
        n = {k: sum(1 for x in res if x["verdict"] == k) for k in ("ok", "mineur", "grave", "illisible")}
        n["plat"] = sum(1 for x in res if x["plat"])
        bilan[tag] = dict(n, pages=len(res), cout=round(cout, 4),
                          graves=[(x["page"], x["raison"]) for x in res if x["verdict"] == "grave"])
        out = os.path.join(nc.SOURCES, chap, "narration", tag, "fidelite.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump({"date": time.strftime("%Y-%m-%dT%H:%M:%S"), "pages": res, "bilan": bilan[tag]}, f,
                      ensure_ascii=False, indent=1)
        print("%-24s grave=%d mineur=%d ok=%d / %d | style plat=%d  (%.3f $)" % (
            tag, n["grave"], n["mineur"], n["ok"], len(res), n["plat"], cout))
        for pg, raison in bilan[tag]["graves"]:
            print("   p%-3s %s" % (pg, raison))


if __name__ == "__main__":
    main()
