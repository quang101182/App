"""Banc MODERATION (feuille de route 4-decies, 24/09/2026) -- hors ligne, aucun appel paye, aucune vraie alerte touchee.

Refus SIMULES (Gemini natif SAFETY, Kimi content_filter, HTTP 400 « high risk », refus en toutes lettres) :
  1. reconnus par moderation.py ;
  2. l'analyse (etape_vision_v2) CONTINUE : lot refuse repris page par page, seule la page fautive est mise de cote,
     et il n'y a JAMAIS de nouvel essai paye sur un refus ;
  3. le recit isole la page refusee ;
  4. registre d'alertes (fichier jetable) : ajout, regroupement, etats ;
  5. video_chapitre refuse (code 4) un chapitre avec une alerte ouverte, l'accepte avec --malgre-alertes ;
  6. registre des depenses : une narration qui reutilise une analyse n'inscrit pas l'analyse recopiee.
Usage : python test_moderation.py
"""
import io, json, os, subprocess, sys, tempfile, urllib.error
HERE = os.path.dirname(os.path.abspath(__file__))
TMP = tempfile.mkdtemp(prefix="banc_moderation_")
os.environ["MANGA_ALERTES"] = os.path.join(TMP, "alertes.json")
os.environ["MANGA_DEPENSES"] = os.path.join(TMP, "depenses.jsonl")
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import moderation as mod
import narrate_chapter as nc
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


print("1. reconnaissance")
check("Gemini finishReason SAFETY", bool(mod.refus_gemini({"candidates": [{"finishReason": "SAFETY"}]})))
check("Gemini blockReason", bool(mod.refus_gemini({"promptFeedback": {"blockReason": "PROHIBITED_CONTENT"}})))
check("Gemini reponse normale = pas un refus", mod.refus_gemini({"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": "{}"}]}}]}) is None)
check("Kimi content_filter", bool(mod.refus_openai({"choices": [{"finish_reason": "content_filter"}]})))
check("HTTP 400 high risk", bool(mod.refus_http(400, '{"error":{"message":"The request was rejected because it was considered high risk"}}')))
check("HTTP 400 ordinaire = pas un refus", mod.refus_http(400, '{"error":"max_tokens too large"}') is None)
check("refus en toutes lettres", bool(mod.refus_texte("I'm sorry, but I can't help with that.")))
check("JSON normal = pas un refus", mod.refus_texte('{"pages": []}') is None)

print("2. l'analyse continue (Gemini refuse la page 2)")
appels = []


def faux_post(path, body, timeout=240):
    textes = " ".join(p.get("text", "") for c in body.get("contents", []) for p in c.get("parts", []))
    nums = [int(x) for x in __import__("re").findall(r"PAGE (\d+)", textes)]
    appels.append(nums)
    if 2 in nums:
        return {"candidates": [{"finishReason": "SAFETY"}], "usageMetadata": {"promptTokenCount": 10}}
    j = {"pages": [{"page": n, "type": "histoire", "faits": "faits de la page %d" % n, "presents": []} for n in nums],
         "resume": "r", "nouveaux": []}
    return {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": json.dumps(j)}]}}],
            "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5}}


nc.post = faux_post
nc.page_jpeg = lambda path, largeur=1000: b"\xff\xd8\xff"           # pas d'image reelle
nc.progres = lambda *a, **k: None
pages = [{"num": n, "file": "page_%03d.png" % n} for n in (1, 2, 3, 4)]
stats = dict(vision_tokens_in=0, vision_tokens_out=0, cout_vision=0.0, vision_s=0.0)
sortie, resume, persos = nc.etape_vision_v2(TMP, pages, "gemini", 2, stats)
types = {p["page"]: p["type"] for p in sortie}
check("4 pages en sortie, dans l'ordre", [p["page"] for p in sortie] == [1, 2, 3, 4], [p["page"] for p in sortie])
check("seule la page 2 est mise de cote", types == {1: "histoire", 2: "moderation", 3: "histoire", 4: "histoire"}, types)
check("motif garde sur la page", "Gemini" in (next(p for p in sortie if p["page"] == 2).get("moderation") or ""))
check("aucun nouvel essai paye sur un refus (appels : [1,2] [1] [2] [3,4])", appels == [[1, 2], [1], [2], [3, 4]], appels)
check("stats.moderation = page 2", [m["page"] for m in stats.get("moderation", [])] == [2])

print("3. le recit isole la page refusee (DeepSeek refuse la page 3)")


def faux_recit(lot, persos_, stats_, contexte):
    if any(x["page"] == 3 for x in lot):
        raise mod.Refus("deepseek", "requete refusee (HTTP 400) : Content Exists Risk")
    return {"titre": "T", "pages": [{"page": x["page"], "narration": "narration %d" % x["page"]} for x in lot]}


nc._appel_recit_v2 = faux_recit
st2 = {}
j = nc._recit_lot([{"page": n, "type": "histoire", "faits": "f"} for n in (1, 2, 3, 4)], [], st2, "")
nar = {p["page"]: p["narration"] for p in j["pages"]}
check("pages 1, 2, 4 racontees, 3 vide", nar == {1: "narration 1", 2: "narration 2", 3: "", 4: "narration 4"}, nar)
check("stats.moderation = page 3 (recit)", [(m["page"], m["etape"]) for m in st2.get("moderation", [])] == [(3, "recit")])

print("4. registre d'alertes (fichier jetable)")
a1 = mod.ajouter_alerte("zz-serie/ch_1", "narration", [2], "gemini", "motif A")
a2 = mod.ajouter_alerte("zz-serie/ch_1", "narration", [5], "gemini", "motif B")
check("meme chapitre + meme etape = UNE alerte, pages cumulees", a1 == a2 and mod.ouvertes_pour("zz-serie/ch_1")[0]["pages"] == [2, 5])
mod.ajouter_alerte("zz-serie/ch_1", "traduction", [7], "gemini", "motif C")
check("autre etape = autre alerte", len(mod.ouvertes_pour("zz-serie/ch_1")) == 2)
check("le vrai registre n'est pas touche", mod.ALERTES.startswith(TMP))

print("5. la video attend (code 4)")
env = dict(os.environ, PYTHONIOENCODING="utf-8")
r = subprocess.run([sys.executable, os.path.join(HERE, "video_chapitre.py"), "zz-serie/ch_1", "tagx"], capture_output=True,
                   text=True, env=env, encoding="utf-8", errors="replace")
check("video refusee : code 4 + message", r.returncode == 4 and "VIDEO EN ATTENTE" in r.stdout, (r.returncode, r.stdout[-120:]))
n = mod.changer_etat([a["id"] for a in mod.ouvertes_pour("zz-serie/ch_1")], "ignoree")
r = subprocess.run([sys.executable, os.path.join(HERE, "video_chapitre.py"), "zz-serie/ch_1", "tagx"], capture_output=True,
                   text=True, env=env, encoding="utf-8", errors="replace")
check("alertes ignorees : la video n'attend plus (echoue plus loin, chapitre inexistant)", r.returncode != 4 and "VIDEO EN ATTENTE" not in r.stdout,
      (n, r.returncode))

print("6. registre des depenses")
import depenses as dep
dep.noter("narration", "zz/ch_1", "t", "gemini", 0.2 - 0.12, reuse="autre")
check("ligne ecrite dans le fichier jetable", dep.REGISTRE.startswith(TMP) and abs(dep.lire()[-1]["paye"] - 0.08) < 1e-9)

print("\n%d/%d" % (len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
