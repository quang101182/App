"""Banc v2.2.0 (23/09/2026) : le recit d'un long chapitre ne peut plus finir VIDE en se disant « ok ».

Incident : Claymore ch.1 recapture en tome (180 pages) -> recit en UN appel plafonne a 8 000 tokens -> JSON illisible
-> 180 pages sans texte, 0 voix, run « ok », lot « narration ok », video refusee. 1,74 $ d'analyse sans rien a ecouter.

Aucun appel reseau : `post` est remplace par un faux DeepSeek / TTS. Usage : python test_recit_lots.py
"""
import base64, io, json, os, shutil, sys, tempfile
from contextlib import redirect_stderr, redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import narrate_chapter as nc          # noqa: E402

OK = KO = 0


def check(cond, nom):
    global OK, KO
    if cond:
        OK += 1; print("  OK  " + nom)
    else:
        KO += 1; print("  KO  " + nom)


def pages_faits(n):
    return [{"page": i, "file": "page_%03d.png" % i, "type": "histoire", "faits": "fait %d" % i, "narration": ""}
            for i in range(1, n + 1)]


class FauxDeepSeek:
    """Rend une narration pour chaque page demandee ; modes : tronque au-dela de N pages, JSON casse une fois, vide."""
    def __init__(self, tronque_au_dela=None, casse_une_fois=False, vide=False):
        self.appels, self.tailles, self.contextes = 0, [], []
        self.tronque_au_dela, self.casse, self.vide, self.reparations = tronque_au_dela, casse_une_fois, vide, 0

    def __call__(self, path, body, timeout=240):
        if path.startswith("/api/gcptts"):
            return {"audioContent": base64.b64encode(b"ID3").decode()}
        msg = body["messages"][-1]["content"]
        if body["messages"][0]["content"].startswith("Tu repares du JSON"):
            self.reparations += 1
            return {"choices": [{"message": {"content": msg.replace("<<CASSE>>", ",")}, "finish_reason": "stop"}], "usage": {}}
        self.appels += 1
        lot = json.loads(msg.split("\nPages :\n", 1)[1])
        self.tailles.append(len(lot)); self.contextes.append(msg.split("\nPages :\n", 1)[0])
        if self.tronque_au_dela and len(lot) > self.tronque_au_dela:
            return {"choices": [{"message": {"content": '{"titre":"T","pages":[{"page":1,"narr'}, "finish_reason": "length"}], "usage": {}}
        pages = [{"page": x["page"], "narration": "" if self.vide else "Recit page %d." % x["page"]} for x in lot]
        txt = json.dumps({"titre": "Titre", "pages": pages}, ensure_ascii=False)
        if self.casse:
            self.casse = False
            txt = txt.replace(",", "<<CASSE>>", 1)
        return {"choices": [{"message": {"content": txt}, "finish_reason": "stop"}], "usage": {}}


def recit(n, faux):
    nc.post = faux
    stats = dict(cout_recit=0.0, recit_s=0.0, cout_vision=0.0)
    with redirect_stderr(io.StringIO()):
        titre, pages = nc.etape_recit_v2(pages_faits(n), "", [], stats)
    return titre, pages


print("1. 180 pages -> recit par lots de %d, aucune page vide" % getattr(nc, "RECIT_LOT", 40))
f = FauxDeepSeek()
t, p = recit(180, f)
check(f.tailles == [40, 40, 40, 40, 20], "5 lots 40/40/40/40/20 (vu : %s)" % f.tailles)
check(all(x["narration"] for x in p), "180/180 pages narrees")
check("partie 1/5" in f.contextes[0] and "PAS de chute" in f.contextes[0], "lot 1 : pas de chute")
check("partie 5/5" in f.contextes[4] and "CETTE partie" in f.contextes[4], "lot 5 : la chute")
check("Recit page 40." in f.contextes[1], "lot 2 recoit la fin du lot 1 (continuite)")
check(t == "Titre", "titre repris du 1er lot")

print("2. 20 pages -> un seul appel, sans consigne de parties (comportement d'avant inchange)")
f = FauxDeepSeek()
recit(20, f)
check(f.tailles == [20] and "partie" not in f.contextes[0], "1 appel, pas de 'partie'")

print("3. reponse tronquee au-dela de 12 pages -> le lot se coupe en deux jusqu'a passer")
f = FauxDeepSeek(tronque_au_dela=12)
t, p = recit(40, f)
check(all(x["narration"] for x in p), "40/40 pages narrees malgre la troncature (lots vus : %s)" % f.tailles)

print("4. JSON mal forme -> repare, pas d'echec")
f = FauxDeepSeek(casse_une_fois=True)
t, p = recit(10, f)
check(f.reparations == 1 and all(x["narration"] for x in p), "1 reparation, 10/10 pages")

print("5. run complet dont le recit rend TOUT vide -> code 3, pas de narration.json, vision.json gardee")
tmp = tempfile.mkdtemp()
try:
    src = os.path.join(tmp, "sources"); chap = os.path.join(src, "serie", "ch_1")
    os.makedirs(os.path.join(chap, "narration", "essai"))
    json.dump({"title": "S", "chapter": "1", "pages": [{"file": "page_%03d.png" % i} for i in range(1, 11)]},
              open(os.path.join(chap, "manifest.json"), "w"))
    vision = {"resume": "", "personnages": [], "stats": {"vision_tokens_in": 1, "vision_tokens_out": 1, "cout_vision": 1.5, "vision_s": 1.0},
              "pages": pages_faits(10)}
    json.dump(vision, open(os.path.join(chap, "narration", "essai", "vision.json"), "w"))
    nc.SOURCES = src
    nc.LOGF = os.path.join(tmp, "journal.jsonl")
    nc._secret = lambda: "x"
    nc.duree_mp3 = lambda f: 1.0

    def run(faux):
        nc.post = faux
        sys.argv = ["narrate_chapter.py", "serie/ch_1", "--engine", "gemini", "--tag", "essai", "--reuse-vision", "essai"]
        out = io.StringIO()
        try:
            with redirect_stdout(out), redirect_stderr(io.StringIO()):
                nc.main()
            return 0, out.getvalue()
        except SystemExit as e:
            return e.code, out.getvalue()

    rc, out = run(FauxDeepSeek(vide=True))
    nj = os.path.join(chap, "narration", "essai", "narration.json")
    check(rc == 3, "code de sortie 3 (vu %s)" % rc)
    check(not os.path.isfile(nj), "aucun narration.json ecrit (l'app ne montre pas un faux « fini »)")
    check('"ok": false' in out, "sortie JSON ok=false")
    pr = json.load(open(os.path.join(chap, "narration", "essai", "progress.json")))
    check(pr.get("etape") == "echec" and "narration vide" in pr.get("erreur", ""), "progress.json = echec + raison")

    print("6. le nouvel essai REPREND vision.json (analyse non re-payee) et reussit")
    rc, out = run(FauxDeepSeek())
    check(rc == 0 and os.path.isfile(nj), "code 0, narration.json ecrit")
    n = json.load(open(nj, encoding="utf-8"))
    check(sum(1 for x in n["pages"] if x.get("audio")) == 10, "10/10 pages avec voix")
    check(n["stats"]["cout_vision"] == 1.5, "cout d'analyse repris, pas re-paye")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("\n%d/%d" % (OK, OK + KO))
sys.exit(1 if KO else 0)
