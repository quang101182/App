# -*- coding: utf-8 -*-
"""ESSAI (24/09/2026) : combien pese la « reflexion » de Gemini 3.6 Flash dans nos appels, et peut-on la baisser ?

Constat du code (narrate_chapter v2.7.0) : aucun appel Gemini ne fixe thinkingConfig -> reflexion par defaut, facturee
au prix de la SORTIE (3,75 $/M). Cet essai pose la MEME question des noms (Q_NOMS, une page par appel) sur N pages,
avec reflexion par defaut puis reduite, et compare jetons, cout, et les noms trouves. Ne modifie pas l'app.
Usage : python essai_reflexion_gemini.py <chapitre> <p1,p2,...> [niveaux=defaut,low,minimal]
"""
import base64, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import narrate_chapter as nc
nc.SECRET = nc._secret()

chap, pages = sys.argv[1], [int(x) for x in sys.argv[2].split(",")]
niveaux = (sys.argv[3] if len(sys.argv) > 3 else "defaut,low,minimal").split(",")
cd = os.path.join(nc.SOURCES if hasattr(nc, "SOURCES") else os.path.join(HERE, "..", "sources"), chap)
man = json.load(open(os.path.join(cd, "manifest.json"), encoding="utf-8"))
path = nc.ENGINES["gemini"][0]
res = {}
for niv in niveaux:
    tot = {"in": 0, "out": 0, "think": 0, "usd": 0.0, "s": 0.0, "noms": {}}
    for num in pages:
        p = man["pages"][num - 1]
        img = base64.b64encode(nc.page_jpeg(os.path.join(cd, p["file"]))).decode()
        gc = {"maxOutputTokens": 4000, "responseMimeType": "application/json"}
        if niv != "defaut":
            gc["thinkingConfig"] = {"thinkingLevel": niv}
        t0 = time.time()
        r = nc.post(path, {"systemInstruction": {"parts": [{"text": "Reponds uniquement en JSON."}]},
                           "contents": [{"role": "user", "parts": [{"text": nc.Q_NOMS},
                                                                   {"inline_data": {"mime_type": "image/jpeg", "data": img}}]}],
                           "generationConfig": gc})
        tot["s"] += time.time() - t0
        if r.get("error"):
            print(niv, "ERREUR", json.dumps(r["error"])[:300]); break
        um = r.get("usageMetadata") or {}
        i, o, th = um.get("promptTokenCount", 0), um.get("candidatesTokenCount", 0), um.get("thoughtsTokenCount", 0)
        tot["in"] += i; tot["out"] += o; tot["think"] += th
        tot["usd"] += nc.cout("gemini-3.6-flash", {"prompt_tokens": i, "completion_tokens": o + th})
        txt = "".join(x.get("text", "") for x in ((r.get("candidates") or [{}])[0].get("content") or {}).get("parts", []))
        try:
            tot["noms"][num] = sorted((x.get("nom") or "").strip() + "/" + (x.get("porteur_age") or "")
                                      for x in nc.parse_json(txt).get("noms") or [])
        except Exception:
            tot["noms"][num] = ["ILLISIBLE"]
    res[niv] = tot
    print("%-8s in=%6d out=%5d reflexion=%6d  %.4f $  %.0f s" % (niv, tot["in"], tot["out"], tot["think"], tot["usd"], tot["s"]), flush=True)
print("\nNoms par page :")
for num in pages:
    print("  p.%-3d " % num + " | ".join("%s: %s" % (n, ", ".join(res[n]["noms"].get(num, []))) for n in res))
json.dump(res, open(os.path.join(HERE, "essai_reflexion_gemini.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
