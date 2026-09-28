# -*- coding: utf-8 -*-
"""Banc S18 (28/09/2026, app v3.6.0) : lecteur des Dialogues, camera « case par case » -> TOUTES les cases.
Quang : « le mode case par case, dans le mode dialogue, ne se focalise que sur les dialogues […] s'il y a des cases sans dialogue,
il les saute ». Copie LEGERE d'un chapitre prepare de la principale (serveur de TEST 8191), portee elargie a une page SANS dialogue.
Controles (camera active) : chaque case de chaque page visitee UNE fois (cases muettes + cases des repliques) ; les repliques dans
LEUR ordre, chacune une fois ; une case muette est cadree (zoom) avec sa pastille « case k / N » ; pause d'une case muette ~1,2 s ;
camera coupee -> file d'avant (repliques + page sans dialogue), rallumee -> cases de nouveau ; aucune erreur JS.
Usage : python test_s18_cases_lecteur.py <html> [--largeurs 360,1280] [--chap one-punch-man/ch_5]"""
import json, os, shutil, subprocess, sys, tempfile, time, urllib.request
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
args = [x for i, x in enumerate(sys.argv[1:], 1) if not x.startswith("--") and sys.argv[i - 1] not in ("--largeurs", "--chap")]
HTML = os.path.abspath(args[0])
PROXY = os.path.expanduser(r"~\Documents\ComfyUI\_studio_llm_proxy.py")
LARGS = [int(x) for x in (sys.argv[sys.argv.index("--largeurs") + 1] if "--largeurs" in sys.argv else "360,1280").split(",")]
CH = sys.argv[sys.argv.index("--chap") + 1] if "--chap" in sys.argv else "one-punch-man/ch_5"
SRC = os.path.expanduser(r"~\Documents\MangaStudio-donnees\sources")
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail)[:190] if detail != "" else ""), flush=True)


T = tempfile.mkdtemp(prefix="s18_")
serie, chap = CH.split("/"); sd, cd = os.path.join(SRC, serie), os.path.join(SRC, serie, chap); dst = os.path.join(T, serie, chap)
os.makedirs(os.path.join(dst, "dialogues")); os.makedirs(os.path.join(dst, "traduction", "fr"))
for f in os.listdir(sd):
    if f.endswith(".json") and os.path.isfile(os.path.join(sd, f)):
        shutil.copy2(os.path.join(sd, f), os.path.join(T, serie, f))
for f in os.listdir(cd):
    if f.endswith(".json"):
        shutil.copy2(os.path.join(cd, f), os.path.join(dst, f))
doc = json.load(open(os.path.join(cd, "dialogues", "dialogues.json"), encoding="utf-8"))
ps = sorted({x["page"] for x in doc["repliques"] if x.get("lire")})
VIDE = ps[0] - 1                                         # une page SANS dialogue, ajoutee a la portee de la copie
doc["pages_vues"] = list(range(VIDE, ps[-1] + 1))
json.dump(doc, open(os.path.join(dst, "dialogues", "dialogues.json"), "w", encoding="utf-8"), ensure_ascii=False)
man = json.load(open(os.path.join(cd, "manifest.json"), encoding="utf-8"))
for n, q in enumerate(man["pages"], 1):
    f = os.path.join(dst, q["file"])
    shutil.copy2(os.path.join(cd, q["file"]), f) if n in doc["pages_vues"] else open(f, "wb").close()
tf = os.path.join(cd, "traduction", "fr")
tr = json.load(open(os.path.join(tf, "traduction.json"), encoding="utf-8"))
tr["pages"] = [p for p in tr["pages"] if p["page"] in doc["pages_vues"]]
json.dump(tr, open(os.path.join(dst, "traduction", "fr", "traduction.json"), "w", encoding="utf-8"), ensure_ascii=False)
for p in tr["pages"]:
    shutil.copy2(os.path.join(tf, p["file"]), os.path.join(dst, "traduction", "fr", p["file"]))
CASES = json.load(open(os.path.join(cd, "cases.json"), encoding="utf-8"))
print("copie :", T, "· pages", doc["pages_vues"], "(p.%d sans dialogue)" % VIDE)

PAGE = open(HTML, encoding="utf-8").read()
srv = subprocess.Popen([sys.executable, os.path.join(HERE, "proxy_8191.py"), PROXY], env=dict(os.environ, MANGA_SOURCES_DIR=T),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(60):
        try:
            urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8191/manga/el_solde", headers={"Authorization": "Bearer " + KEY}), timeout=5); break
        except Exception:
            time.sleep(1)
    with sync_playwright() as p:
        br = p.chromium.launch(channel="msedge", headless=True)
        for LARG in LARGS:
            print("=== largeur %d" % LARG)
            ctx = br.new_context(viewport={"width": LARG, "height": 800 if LARG < 800 else 900}, is_mobile=LARG < 800, service_workers="block")
            pg = ctx.new_page(); errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.on("dialog", lambda d: d.dismiss())
            pg.route("**/*", lambda rt: rt.fulfill(status=200, content_type="text/html; charset=utf-8", body=PAGE)
                     if rt.request.method == "GET" and rt.request.url.split("#")[0].split("?")[0].rstrip("/").endswith("/manga") else
                     (rt.fulfill(status=200, body='{"ok":true}', content_type="application/json") if rt.request.method != "GET" else rt.continue_()))
            pg.goto("http://127.0.0.1:8191/manga/#k=" + KEY); pg.wait_for_timeout(2500)
            pg.evaluate("s => { localStorage.setItem('manga_onglet','tChap'); localStorage.setItem('manga_serie', s); localStorage.setItem('manga_dlg_cam','1'); }", serie)
            pg.reload(); pg.wait_for_timeout(3500)
            pg.evaluate("d => openChap(CHAPS.findIndex(c => c.dir === d))", CH); pg.wait_for_timeout(2500)
            pg.evaluate("d => { dlgLecteur(d, 0); }", CH)
            for _ in range(40):
                pg.wait_for_timeout(500)
                if pg.evaluate("() => !!(DLL.cases && DLL.liste.some(x => x.muette))"): break
            pg.evaluate("() => { DLL.pause = true; DLL.audio.pause(); clearTimeout(DLL.t); clearTimeout(DLL.t2); }")
            L = pg.evaluate("""() => DLL.liste.map(x => ({ page: x.page, m: !!x.muette, v: !!x.vide, k: x.muette ? x.k : null, nk: x.nk || null,
                                  cle: x.cle, c: (x.muette || x.vide) ? null : (() => { if (typeof dllPageCases !== 'function') return null; const pgc = dllPageCases(x.page, x.file); return pgc ? dllIdxCase(x, pgc) : null; })() }))""")
            B = pg.evaluate("() => (DLL.base || DLL.liste).filter(x => !x.vide).map(x => x.cle)")
            check("repliques jouees dans LEUR ordre, chacune une fois", [x["cle"] for x in L if not x["m"] and not x["v"]] == B, len(B))
            ok_pages, detail = True, []
            for n in doc["pages_vues"]:
                fic = man["pages"][n - 1]["file"]
                e = CASES["pages"].get(fic) or {}
                N = len(e.get("cases") or [])
                if N < 2:
                    continue
                vues = [x["k"] if x["m"] else x["c"] for x in L if x["page"] == n and not x["v"]]
                if sorted(set(vues)) != list(range(N)) or len([x for x in L if x["page"] == n and x["m"]]) != len({k for k in range(N)} - {x["c"] for x in L if x["page"] == n and not x["m"] and not x["v"]}):
                    ok_pages = False; detail.append((n, N, vues))
            check("camera active : chaque case de chaque page visitee (muettes + cases des repliques)", ok_pages, detail[:2])
            check("la page sans dialogue (p.%d) = ses cases une a une, plus de page entiere" % VIDE,
                  any(x["m"] for x in L if x["page"] == VIDE) and not any(x["v"] for x in L if x["page"] == VIDE), [x for x in L if x["page"] == VIDE][:3])
            i = next((i for i, x in enumerate(L) if x["m"] and x["page"] != VIDE), next((i for i, x in enumerate(L) if x["m"]), 0))
            pg.evaluate("i => { DLL.pause = false; DLL.i = i; dllMontrer(); }", i); pg.wait_for_timeout(700)
            st = pg.evaluate("() => ({ t: $('dllZoom').style.transform, sous: $('dllSous').textContent, pos: $('dllPos').textContent, i: DLL.i })")
            check("case muette cadree par la camera (zoom)", "scale(" in st["t"] and "scale(1.000)" not in st["t"], st["t"])
            check("case muette : « case k / N · sans dialogue »", "case " in st["sous"] and "sans dialogue" in st["sous"], st["sous"])
            t0 = time.time()
            for _ in range(40):
                pg.wait_for_timeout(100)
                if pg.evaluate("() => DLL.i") != i: break
            dt = time.time() - t0
            vit = pg.evaluate("() => +$('dllVit').value || 1")
            check("case muette : courte pause (~1,2 s / vitesse %.2g) puis la suite" % vit, 0.9 / vit <= dt + 0.7 <= 2.6 / vit, round(dt + 0.7, 2))
            pg.evaluate("() => { DLL.pause = true; DLL.audio.pause(); clearTimeout(DLL.t); clearTimeout(DLL.t2); }")
            pg.evaluate("() => { $('dllCam').checked = false; $('dllCam').onchange(); }"); pg.wait_for_timeout(500)
            off = pg.evaluate("() => ({ m: DLL.liste.filter(x => x.muette).length, same: !!DLL.base && DLL.liste.length === DLL.base.length && DLL.liste.every((x, k) => x === DLL.base[k]), cam: localStorage.getItem('manga_dlg_cam') })")
            check("camera coupee : file d'avant (aucune case muette, page sans dialogue entiere)", off["m"] == 0 and off["same"], off)
            pg.evaluate("() => { $('dllCam').checked = true; $('dllCam').onchange(); }"); pg.wait_for_timeout(500)
            check("camera rallumee : cases muettes de retour", pg.evaluate("() => DLL.liste.some(x => x.muette)"))
            deb = pg.evaluate("() => document.documentElement.scrollWidth > innerWidth + 1")
            check("aucun defilement horizontal", not deb)
            check("aucune erreur JavaScript", not errs, errs[:2])
            pg.evaluate("() => { DLL.pause = true; DLL.audio.pause(); clearTimeout(DLL.t); clearTimeout(DLL.t2); }")
            ctx.close()
        br.close()
finally:
    srv.terminate()
    try:
        srv.wait(10)
    except Exception:
        srv.kill()
    shutil.rmtree(T, ignore_errors=True)
print("\nVERDICT %s : %d/%d" % ("VERT" if not KO else "ROUGE", len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
