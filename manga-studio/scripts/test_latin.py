"""Banc v2.3.0 (23/09/2026, remontee Video Studio) : aucun nom ne disparait plus de la narration a cause d'un scan chinois.

Cas reel rejoue : OPM ch.6 p.2 (scan zh-hk) -- fiche {傑諾斯}, faits « Case 2 : 傑諾斯 lève sa main mécanique ». Avant :
le recit recopiait le nom, sans_cjk() l'effacait -> « En bas, lève sa main mécanique ». Aucun appel reseau (faux DeepSeek).
Usage : python test_latin.py
"""
import io, json, os, shutil, sys, tempfile
from contextlib import redirect_stderr, redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import narrate_chapter as nc          # noqa: E402

OK = KO = 0


def check(cond, nom):
    global OK, KO
    OK, KO = (OK + 1, KO) if cond else (OK, KO + 1)
    print(("  OK  " if cond else "  KO  ") + nom)


NOMS = {"傑諾斯": "Genos", "埼玉": "Saitama", "你說這傢伙啊": "Tu parles de ce type ?"}


class Faux:
    """Faux gateway. latin : rend la table (une 1re fois SANS « 埼玉 » si manque_une_fois) ; recit : recopie les faits."""
    def __init__(self, manque_une_fois=False, recit_cjk=False, rien=False):
        self.latin, self.manque, self.recit_cjk, self.rien = 0, manque_une_fois, recit_cjk, rien

    def __call__(self, path, body, timeout=240):
        if path.startswith("/api/gcptts"):
            import base64
            return {"audioContent": base64.b64encode(b"ID3").decode()}
        msg = body["messages"][-1]["content"]
        if "Voici des mots en caracteres" in msg:
            self.latin += 1
            mots = json.loads(msg.split("Mots : ", 1)[1])
            t = {} if self.rien else {m: NOMS.get(m, "X") for m in mots}
            if self.manque and self.latin == 1:
                t.pop("埼玉", None)
            return {"choices": [{"message": {"content": json.dumps(t, ensure_ascii=False)}, "finish_reason": "stop"}], "usage": {}}
        lot = json.loads(msg.split("\nPages :\n", 1)[1])
        pages = [{"page": x["page"], "narration": ("傑諾斯 " if self.recit_cjk else "") + x["faits"].split(" : ", 1)[-1]} for x in lot]
        return {"choices": [{"message": {"content": json.dumps({"titre": "T", "pages": pages}, ensure_ascii=False)},
                             "finish_reason": "stop"}], "usage": {}}


def vis_opm():
    return [{"page": 1, "file": "page_001.png", "type": "histoire", "presents": ["p1", "傑諾斯"],
             "faits": "Case 2 : 傑諾斯 lève sa main mécanique vers le haut.", "narration": ""},
            {"page": 2, "file": "page_002.png", "type": "histoire", "presents": ["埼玉"],
             "faits": "Case 1 : 埼玉 dit « 你說這傢伙啊 ».", "narration": ""}]


print("1. latiniser : fiche, faits, presents, resume passent en alphabet latin")
nc.post = Faux(); nc.LOGF = os.path.join(tempfile.gettempdir(), "banc_latin.jsonl")
with redirect_stderr(io.StringIO()):
    vis, resume, persos, noms, table = nc.latiniser(vis_opm(), "傑諾斯 arrive.", [{"id": "傑諾斯", "description": "cyborg"}],
                                                   {"傑諾斯": {"age": "adulte"}}, "One Punch-Man", {"cout_recit": 0.0})
check(vis[0]["faits"] == "Case 2 : Genos lève sa main mécanique vers le haut.", "faits : « Genos lève… » (%s)" % vis[0]["faits"])
check(vis[0]["presents"] == ["p1", "Genos"] and vis[1]["presents"] == ["Saitama"], "presents : %s %s" % (vis[0]["presents"], vis[1]["presents"]))
check("Tu parles de ce type ?" in vis[1]["faits"], "replique chinoise traduite : %s" % vis[1]["faits"])
check(resume == "Genos arrive." and persos[0]["id"] == "Genos" and list(noms) == ["Genos"], "resume, fiche, noms : %s / %s / %s" % (resume, persos, list(noms)))
check(not any(nc.re.search(nc._RE_CJK, json.dumps(x, ensure_ascii=False)) for x in (vis, resume, persos, list(noms))), "plus AUCUN caractere CJK")

print("2. un mot oublie par le modele -> redemande une fois")
f = Faux(manque_une_fois=True); nc.post = f
with redirect_stderr(io.StringIO()):
    vis, *_ = nc.latiniser(vis_opm(), "", [], {}, "One Punch-Man", {"cout_recit": 0.0})
check(f.latin == 2 and vis[1]["presents"] == ["Saitama"], "2 appels, Saitama retrouve (%d appels)" % f.latin)

print("3. deja latin -> aucun appel (idempotent, 0 $)")
f = Faux(); nc.post = f
with redirect_stderr(io.StringIO()):
    v2, *_ = nc.latiniser([{"page": 1, "type": "histoire", "faits": "Genos lève la main.", "presents": ["Genos"]}], "", [], {}, "OPM", {})
check(f.latin == 0 and v2[0]["faits"] == "Genos lève la main.", "0 appel, texte identique")

print("4. run complet (reprise de l'analyse) : la narration garde « Genos », la voix le dit")
tmp = tempfile.mkdtemp()
try:
    src = os.path.join(tmp, "sources"); chap = os.path.join(src, "one-punch-man", "ch_6"); nd = os.path.join(chap, "narration", "essai")
    os.makedirs(nd)
    json.dump({"title": "One Punch-Man", "chapter": "6", "pages": [{"file": "page_001.png"}, {"file": "page_002.png"}]},
              open(os.path.join(chap, "manifest.json"), "w"))
    json.dump({"resume": "", "personnages": [], "pages": vis_opm(),
               "stats": {"vision_tokens_in": 1, "vision_tokens_out": 1, "cout_vision": 0.5, "vision_s": 1.0, "noms": {"傑諾斯": {}}}},
              open(os.path.join(nd, "vision.json"), "w", encoding="utf-8"), ensure_ascii=False)
    nc.SOURCES = src; nc._secret = lambda: "x"; nc.duree_mp3 = lambda f: 1.0

    def run(faux):
        nc.post = faux
        sys.argv = ["narrate_chapter.py", "one-punch-man/ch_6", "--engine", "gemini", "--tag", "essai", "--reuse-vision", "essai"]
        try:
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                nc.main()
            return 0
        except SystemExit as e:
            return e.code
    nj = os.path.join(nd, "narration.json")
    rc = run(Faux())
    n = json.load(open(nj, encoding="utf-8")) if os.path.isfile(nj) else {"pages": []}
    txt = [p["narration"] for p in n["pages"]]
    check(rc == 0 and txt and txt[0].startswith("Genos lève sa main"), "narration p.1 : %s" % (txt[:1],))
    check(not any(p.get("cjk_retires") for p in n["pages"]), "aucune page amputee (cjk_retires absent)")
    check((n.get("stats") or {}).get("latin", {}).get("傑諾斯") == "Genos", "table gardee dans les stats")

    print("5. filet : si le recit reintroduit du CJK -> ECHEC (code 3), plus d'amputation silencieuse")
    os.remove(nj)
    rc = run(Faux(recit_cjk=True))
    pr = json.load(open(os.path.join(nd, "progress.json"), encoding="utf-8"))
    check(rc == 3 and not os.path.isfile(nj) and "chinois" in pr.get("erreur", ""), "code %s, raison : %s" % (rc, pr.get("erreur", "")[:70]))
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print("\n%d/%d" % (OK, OK + KO))
sys.exit(1 if KO else 0)
