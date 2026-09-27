# -*- coding: utf-8 -*-
"""Banc v2.81.5 (patch_dialogues_5) : traduction PARTIELLE tracee, cote serveur, sur une instance de TEST (8191) pointee sur
une COPIE (dossier donne) ou OPM ch.302 (VO vietnamienne) a deja les pages 2, 3, 5, 7 traduites « via dialogues ».
Paye UNE vraie page (traduction ~0,015 $ + preparation ~0,005 $). Usage : python test_trad_partielle_proxy.py <proxy patche> <sources copie>"""
import json, os, subprocess, sys, time, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
PROXY, T = (os.path.abspath(x) for x in sys.argv[1:3])
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
D = "one-punch-man/ch_302"
OK, KO = [], []
def check(n, c, d=""):
    (OK if c else KO).append(n); print(("  [OK] " if c else "  [KO] ") + n + (" -- " + str(d)[:170] if d else ""), flush=True)
def get(p):
    return json.load(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8191" + p, headers={"Authorization": "Bearer " + KEY}), timeout=30))
def post(p, b):
    return json.load(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8191" + p, data=json.dumps(b).encode(),
                     headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"}), timeout=30))
srv = subprocess.Popen([sys.executable, os.path.join(HERE, "proxy_8191.py"), PROXY], env=dict(os.environ, MANGA_SOURCES_DIR=T,
                       MANGA_DEPENSES=os.path.join(T, "_depenses_banc.jsonl")), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(60):
        try: get("/manga/el_solde"); break
        except Exception: time.sleep(1)
    e = get("/manga/dialogues?d=" + D)
    check("etat : trad_pages = pages vraiment traduites", e.get("trad_pages") == [2, 3, 5, 7], e.get("trad_pages"))
    check("etat : chapitre NON complet, pas « deja en VF »", e.get("trad_complete") is False and e.get("vf") is False, (e.get("trad_complete"), e.get("vf")))
    t = [x for x in get("/manga/traductions?d=" + D)["items"] if x["langue"] == "fr"][0]
    check("traductions : 4 / 18, via dialogues, historique", t.get("complete") is False and t.get("n") == 4 and t.get("total") == 18
          and t.get("via_dialogues") == [2, 3, 5, 7] and len(t.get("historique") or []) == 3, {k: t.get(k) for k in ("complete", "n", "total", "via_dialogues")})
    r = get("/manga/resume")["chapitres"][D]
    check("bibliotheque : FR PAS dans « trad » (complet), mais dans « trad_partiel »", r.get("trad") == [] and r.get("trad_partiel") == ["fr"], (r.get("trad"), r.get("trad_partiel")))
    r2 = post("/manga/dialogues_lancer", {"d": "one-punch-man/ch_303", "action": "preparer", "pages": "2-2"})
    check("chapitre sans traduction, SANS « traduire » : refuse", "error" in r2, r2)
    r3 = post("/manga/dialogues_lancer", {"d": D, "action": "preparer", "pages": "9-9", "traduire": "oui"})
    time.sleep(3)
    pr = (get("/manga/dialogues?d=" + D).get("progress") or {})
    # « traduire » doit etre le booleen true : une chaine ne declenche rien de paye (la page 9 n'est pas traduite)
    for _ in range(60):
        if not get("/manga/dialogues?d=" + D).get("en_cours"): break
        time.sleep(2)
    check("« traduire » non booleen : rien de traduit", 9 not in get("/manga/dialogues?d=" + D)["trad_pages"])
    r4 = post("/manga/dialogues_lancer", {"d": D, "action": "preparer", "pages": "9-9", "traduire": True})
    check("avec traduire=true : lance", r4.get("ok") is True, r4)
    vu_trad = False
    for _ in range(120):
        time.sleep(2)
        e = get("/manga/dialogues?d=" + D)
        vu_trad = vu_trad or (e.get("progress") or {}).get("etape") == "traduction"
        if not e.get("en_cours") and (e.get("progress") or {}).get("fini"): break
    check("activite : l'etape « traduction » est visible pendant le run", vu_trad)
    check("page 9 traduite puis preparee", 9 in e["trad_pages"] and any(x["page"] == 9 for x in (e.get("doc") or {}).get("repliques") or []),
          (e["trad_pages"], (e.get("progress") or {}).get("etape")))
    t = [x for x in get("/manga/traductions?d=" + D)["items"] if x["langue"] == "fr"][0]
    check("tracabilite : 5 / 18, page 9 « via dialogues », 4 passages", t["n"] == 5 and 9 in t["via_dialogues"] and len(t["historique"]) == 4, t["historique"][-1:])
    dep = [json.loads(l) for l in open(os.path.join(T, "_depenses_banc.jsonl"), encoding="utf-8")]
    tr = [x for x in dep if x["type"] == "traduction"]
    check("depense : ce passage seul (< 0,03 $), pas le cumul", tr and tr[-1]["paye"] < 0.03, tr[-1:] if tr else dep)
finally:
    srv.kill()
    try: os.remove(os.path.expanduser(r"~\Documents\ComfyUI\_studio_llm_proxy_8191.py"))
    except Exception: pass
print("VERDICT : %d OK / %d KO" % (len(OK), len(KO)))
