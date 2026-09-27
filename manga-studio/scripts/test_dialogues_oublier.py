# -*- coding: utf-8 -*-
"""Banc v2.99.1 : « 🗑 Oublier cette plage » de bout en bout, SANS toucher aux vraies donnees.
Copie LEGERE d'un chapitre prepare (json + dialogues/, sans les images) dans un dossier temporaire, serveur de TEST 8191
(proxy_8191.py sur une copie patchee du proxy), page de l'app servie telle quelle. On oublie une plage au doigt (⋯ → 🗑,
confirmation acceptee) puis l'autre ; on verifie la liste, le fichier (repliques rangees dans « oubliees », copie avant),
la video deplacee dans _oubliees (pas effacee). Nettoie tout a la fin.
Usage : python test_dialogues_oublier.py <manga_studio.html> <proxy patche> <serie/ch_N source>
"""
import json, os, shutil, subprocess, sys, tempfile, time, urllib.request
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
HTML, PROXY, CH = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2]), sys.argv[3]
SRC = os.path.expanduser(r"~\Documents\MangaStudio-donnees\sources")
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail)[:170] if detail else ""), flush=True)


T = tempfile.mkdtemp(prefix="oubli_")
serie, chap = CH.split("/")
sd, cd = os.path.join(SRC, serie), os.path.join(SRC, serie, chap)
os.makedirs(os.path.join(T, serie, chap))
for f in os.listdir(sd):                                        # fichiers de la serie (distribution, fiche...)
    if os.path.isfile(os.path.join(sd, f)) and f.endswith(".json"):
        shutil.copy2(os.path.join(sd, f), os.path.join(T, serie, f))
for f in os.listdir(cd):
    if f.endswith(".json"):
        shutil.copy2(os.path.join(cd, f), os.path.join(T, serie, chap, f))
shutil.copytree(os.path.join(cd, "dialogues"), os.path.join(T, serie, chap, "dialogues"),
                ignore=shutil.ignore_patterns("*.avant_oubli_*", "_oubliees"))
man = json.load(open(os.path.join(T, serie, chap, "manifest.json"), encoding="utf-8"))
for q in man.get("pages") or []:                                # pages factices (1 px) : le serveur liste des fichiers existants
    open(os.path.join(T, serie, chap, q["file"]), "wb").close()
DJ = os.path.join(T, serie, chap, "dialogues", "dialogues.json")
doc = json.load(open(DJ, encoding="utf-8"))
pages = sorted({x["page"] for x in doc["repliques"]})
a, b = pages[0], pages[-1]
K1 = "%d-%d" % (a, b)                                           # 2 plages : la plage des repliques + « tout » (video du chapitre)
doc.setdefault("portees", [])
if K1 not in doc["portees"]:
    doc["portees"].append(K1)
json.dump(doc, open(DJ, "w", encoding="utf-8"), ensure_ascii=False)
n_reps = len(doc["repliques"])
print("copie :", T, "· plages attendues :", K1, "+ tout" if (doc.get("video") or "tout" in (doc.get("videos") or {})) else "")

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
        ctx = br.new_context(viewport={"width": 360, "height": 780}, is_mobile=True, has_touch=True, service_workers="block")
        pg = ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("dialog", lambda d: d.accept())
        pg.route("**/*", lambda rt: rt.fulfill(status=200, content_type="text/html; charset=utf-8", body=PAGE)
                 if rt.request.method == "GET" and rt.request.url.split("#")[0].split("?")[0].rstrip("/").endswith("/manga") else rt.continue_())
        pg.goto("http://127.0.0.1:8191/manga/#k=" + KEY); pg.wait_for_timeout(2500)
        pg.evaluate("s => { localStorage.setItem('manga_onglet','tChap'); localStorage.setItem('manga_serie', s); }", serie)
        pg.reload(); pg.wait_for_timeout(3500)
        pg.evaluate("d => openChap(CHAPS.findIndex(c => c.dir === d))", CH); pg.wait_for_timeout(3000)
        pg.evaluate("() => clOuvrir('dlg')"); pg.wait_for_timeout(2500)
        titres = lambda: pg.evaluate("() => [...document.querySelectorAll('#dplListe .dpl .t')].map(x => x.textContent)")
        t0 = titres()
        check("depart : les plages sont listees (%s)" % ", ".join(t0), len(t0) >= 1, t0)
        # 1) oublier la plage des repliques
        pg.evaluate("t => [...document.querySelectorAll('#dplListe .dpl')].find(c => c.querySelector('.t').textContent === t).querySelector('[data-dpl=menu]').click()",
                    "p. %d-%d" % (a, b) if a != b else "p. %d" % a); pg.wait_for_timeout(500)
        vu = pg.evaluate("() => !!document.querySelector('.dpl-menu [data-dpl=oublier]')")
        check("⋯ propose « 🗑 Oublier cette plage »", vu)
        pg.evaluate("() => document.querySelector('.dpl-menu [data-dpl=oublier]').click()"); pg.wait_for_timeout(3500)
        t1 = titres()
        check("apres oubli : la plage a quitte la liste", ("p. %d-%d" % (a, b)) not in t1, t1)
        d1 = json.load(open(DJ, encoding="utf-8"))
        check("fichier : repliques RANGEES dans « oubliees » (rien de perdu)", len(d1.get("oubliees") or []) + len(d1["repliques"]) == n_reps and len(d1.get("oubliees") or []) > 0,
              (len(d1["repliques"]), len(d1.get("oubliees") or [])))
        check("fichier : la plage a quitte « portees »", K1 not in (d1.get("portees") or []), d1.get("portees"))
        check("copie du fichier AVANT l'oubli presente", any(".avant_oubli_" in f for f in os.listdir(os.path.dirname(DJ))))
        # 2) oublier ce qui reste (chapitre entier / video)
        if t1:
            pg.evaluate("() => document.querySelector('#dplListe .dpl [data-dpl=menu]').click()"); pg.wait_for_timeout(500)
            pg.evaluate("() => document.querySelector('.dpl-menu [data-dpl=oublier]').click()"); pg.wait_for_timeout(3500)
        t2 = titres()
        vd = os.path.join(os.path.dirname(DJ), "video")
        rangees = os.listdir(os.path.join(vd, "_oubliees")) if os.path.isdir(os.path.join(vd, "_oubliees")) else []
        check("tout oublie : liste vide, formulaire de preparation affiche", not t2 and pg.evaluate("() => !!document.querySelector('.dpl-nouv')"), t2)
        check("videos DEPLACEES dans _oubliees (pas effacees)", len(rangees) >= 1 and not [f for f in os.listdir(vd) if f.endswith(".mp4")], (rangees, os.listdir(vd)))
        pg.screenshot(path=os.path.join(HERE, "samsung_out", "dlg_oublier_360.png"))
        check("0 erreur JS", not errs, errs[:2])
        br.close()
finally:
    srv.terminate()
    try: srv.wait(10)
    except Exception: srv.kill()
    f8191 = os.path.expanduser(r"~\Documents\ComfyUI\_studio_llm_proxy_8191.py")
    if os.path.exists(f8191):
        os.remove(f8191)
    shutil.rmtree(T, ignore_errors=True)
print("\nVERDICT : %d/%d" % (len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
