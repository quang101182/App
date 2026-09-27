# -*- coding: utf-8 -*-
"""Banc v3.1.0 (R30, maquette_verif_bulles_v1) : 🔍 verifier les bulles, de bout en bout, SANS toucher aux vraies donnees.
Copies LEGERES dans un dossier temporaire (json, dialogues/, pages utiles), serveur de TEST 8191 (proxy patche), page de l'app.
Gestes REELS a la souris (pointer events) a 360 px : toucher = exclure, ↶, glisser une pastille sur une autre = ordre,
entourer = ajout, glisser la page = page suivante ; « ✓ Valider » -> fichier bulles_verifiees.json ; reouverture = etat garde ;
chapitre NON traduit : « 🔍 Verifier les bulles · gratuit » -> detection seule (dialogues.py detecter) -> pastilles.
Usage : python test_verif_bulles_ui.py <html> <proxy patche> <serie/ch traduit avec plage preparee> <serie/ch non traduit> [--704]"""
import json, os, shutil, subprocess, sys, tempfile, time, urllib.request
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
args = [x for x in sys.argv[1:] if not x.startswith("--")]
HTML, PROXY, CH, CHN = os.path.abspath(args[0]), os.path.abspath(args[1]), args[2], args[3]
LARG = 704 if "--704" in sys.argv else 360
SRC = os.path.expanduser(r"~\Documents\MangaStudio-donnees\sources")
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail)[:170] if detail else ""), flush=True)


T = tempfile.mkdtemp(prefix="verif_")


def copie(ch, pages):
    serie, chap = ch.split("/"); sd, cd = os.path.join(SRC, serie), os.path.join(SRC, serie, chap)
    os.makedirs(os.path.join(T, serie, chap), exist_ok=True)
    for f in os.listdir(sd):
        if f.endswith(".json") and os.path.isfile(os.path.join(sd, f)):
            shutil.copy2(os.path.join(sd, f), os.path.join(T, serie, f))
    for f in os.listdir(cd):
        if f.endswith(".json"):
            shutil.copy2(os.path.join(cd, f), os.path.join(T, serie, chap, f))
    if os.path.isdir(os.path.join(cd, "dialogues")):
        shutil.copytree(os.path.join(cd, "dialogues"), os.path.join(T, serie, chap, "dialogues"),
                        ignore=shutil.ignore_patterns("*.avant_oubli_*", "_oubliees", "voix", "video", "bulles_verifiees.json", "detection.json"))
    man = json.load(open(os.path.join(cd, "manifest.json"), encoding="utf-8"))
    for n, q in enumerate(man.get("pages") or [], 1):
        dst = os.path.join(T, serie, chap, q["file"])
        if n in pages:
            shutil.copy2(os.path.join(cd, q["file"]), dst)
        else:
            open(dst, "wb").close()
    tf = os.path.join(cd, "traduction", "fr")
    if os.path.isdir(tf):
        os.makedirs(os.path.join(T, serie, chap, "traduction", "fr"))
        shutil.copy2(os.path.join(tf, "traduction.json"), os.path.join(T, serie, chap, "traduction", "fr", "traduction.json"))
        for n in pages:
            f = os.path.join(tf, "page_%03d.png" % n)
            if os.path.isfile(f):
                shutil.copy2(f, os.path.join(T, serie, chap, "traduction", "fr", "page_%03d.png" % n))


doc = json.load(open(os.path.join(SRC, CH, "dialogues", "dialogues.json"), encoding="utf-8"))
pp = sorted({x["page"] for x in doc["repliques"]}); A, B = pp[0], pp[-1]
copie(CH, set(range(A, B + 1))); copie(CHN, {1, 2, 3})
print("copie :", T, "· plage", A, "-", B)
PAGE = open(HTML, encoding="utf-8").read()
srv = subprocess.Popen([sys.executable, os.path.join(HERE, "proxy_8191.py"), PROXY], env=dict(os.environ, MANGA_SOURCES_DIR=T),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
VF = os.path.join(T, CH, "dialogues", "bulles_verifiees.json")
try:
    for _ in range(60):
        try:
            urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8191/manga/el_solde", headers={"Authorization": "Bearer " + KEY}), timeout=5); break
        except Exception:
            time.sleep(1)
    with sync_playwright() as p:
        br = p.chromium.launch(channel="msedge", headless=True)
        ctx = br.new_context(viewport={"width": LARG, "height": 800}, is_mobile=LARG < 800, has_touch=False, service_workers="block")
        pg = ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("dialog", lambda d: d.dismiss() if ("Tout" in d.message or "tout refaire" in d.message or "Refaire" in d.message) else d.accept())   # jamais de lancement payant
        pg.route("**/*", lambda rt: rt.fulfill(status=200, content_type="text/html; charset=utf-8", body=PAGE)
                 if rt.request.method == "GET" and rt.request.url.split("#")[0].split("?")[0].rstrip("/").endswith("/manga") else
                 (rt.fulfill(status=200, body='{"ok":true}', content_type="application/json") if rt.request.method != "GET" and "dialogues_lancer" in rt.request.url
                  and '"detecter"' not in (rt.request.post_data or "") else rt.continue_()))   # 27/09 : TOUT lancement bloque sauf la detection (gratuite)
        def ouvrir(ch):
            pg.goto("http://127.0.0.1:8191/manga/#k=" + KEY); pg.wait_for_timeout(2500)
            pg.evaluate("s => { localStorage.setItem('manga_onglet','tChap'); localStorage.setItem('manga_serie', s); localStorage.setItem('manga_dlv_aide','1'); }", ch.split("/")[0])
            pg.reload(); pg.wait_for_timeout(3500)
            pg.evaluate("d => openChap(CHAPS.findIndex(c => c.dir === d))", ch); pg.wait_for_timeout(3000)
            pg.evaluate("() => clOuvrir('dlg')"); pg.wait_for_timeout(2500)
        pts = lambda: pg.evaluate("""() => [...document.querySelectorAll('#dlvSvg [data-dlv-k]')].map(g => { const r = g.querySelector('circle').getBoundingClientRect();
                                      return { x: r.left + r.width / 2, y: r.top + r.height / 2, t: g.textContent }; })""")
        # ---- 1. chapitre traduit, plage connue
        ouvrir(CH)
        pg.evaluate("k => { const c = [...document.querySelectorAll('#dplListe .dpl')].find(x => x.querySelector('.t').textContent === k); if (c) c.click(); }", "p. %d-%d" % (A, B) if A != B else "p. %d" % A)
        pg.wait_for_timeout(800)
        e = pg.evaluate("() => { const b = document.getElementById('dplBulles'); return { vis: !!(b && b.offsetParent), txt: b && b.textContent, premier: b && b.parentNode.firstElementChild === b }; }")
        check("etape « 🔍 Bulles » en tete des etapes de la plage", e["vis"] and e["premier"] and "Bulles" in e["txt"], e)
        pg.evaluate("() => $('dplBulles').click()"); pg.wait_for_timeout(3500)
        api = pg.evaluate("async ([d, p]) => (await api('/manga/dialogues_bulles?d=' + encodeURIComponent(d) + '&pages=' + p)).pages[0].bulles.length", [CH, "%d-%d" % (A, B)])
        P0 = pts()
        check("ecran ouvert sur la 1re page, une pastille par bulle (%d), numerotees 1..n" % len(P0), pg.evaluate("() => !$('dlvBox').hidden") and len(P0) == api
              and [x["t"] for x in P0] == [str(i + 1) for i in range(len(P0))], [x["t"] for x in P0])
        check("aide des 3 gestes affichee", pg.evaluate("() => !$('dlvAide').hidden && /entourer/.test($('dlvAide').textContent)"))
        check("gros bouton = « Page suivante › »", "Page suivante" in pg.evaluate("() => $('dlvGo').textContent"))
        if len(P0) >= 2:
            pg.mouse.click(P0[1]["x"], P0[1]["y"]); pg.wait_for_timeout(300)
            check("toucher une pastille = exclue (✕), numerotation recalculee", [x["t"] for x in pts()][1] == "✕", [x["t"] for x in pts()])
            pg.evaluate("() => $('dlvAnnuler').click()"); pg.wait_for_timeout(300)
            check("↶ remet la pastille", [x["t"] for x in pts()] == [x["t"] for x in P0])
            ids0 = pg.evaluate("() => dlvPage().items.map(x => x.id)")
            a_, b_ = P0[-1], P0[0]
            pg.mouse.move(a_["x"], a_["y"]); pg.mouse.down();
            for k in range(1, 11): pg.mouse.move(a_["x"] + (b_["x"] - a_["x"]) * k / 10, a_["y"] + (b_["y"] - a_["y"]) * k / 10); pg.wait_for_timeout(15)
            pg.mouse.up(); pg.wait_for_timeout(300)
            ids1 = pg.evaluate("() => dlvPage().items.map(x => x.id)")
            check("glisser la derniere pastille sur la 1re = elle passe en tete", ids1[0] == ids0[-1] and len(ids1) == len(ids0), (ids0, ids1))
        cad = pg.evaluate("() => { const r = $('dlvCadre').getBoundingClientRect(); return { x: r.left, y: r.top, w: r.width, h: r.height }; }")
        import math
        cx, cy, rr = cad["x"] + cad["w"] * 0.5, cad["y"] + cad["h"] * 0.93, min(cad["w"], cad["h"]) * 0.05
        pg.mouse.move(cx + rr, cy); pg.mouse.down()
        for k in range(1, 25): pg.mouse.move(cx + rr * math.cos(k / 24 * 6.28), cy + rr * 0.7 * math.sin(k / 24 * 6.28)); pg.wait_for_timeout(10)
        pg.mouse.up(); pg.wait_for_timeout(300)
        aj = pg.evaluate("() => dlvPage().items.filter(x => x.ajout).length")
        check("entourer au doigt = une bulle ajoutee (pastille jaune)", aj == 1, aj)
        k_aj = pg.evaluate("() => dlvPage().items.findIndex(x => x.ajout)")
        pa = [x for x in pts()][k_aj]
        pg.mouse.move(pa["x"], pa["y"]); pg.mouse.down(); pg.wait_for_timeout(900); pg.mouse.up(); pg.wait_for_timeout(300)
        check("appui long sur la bulle ajoutee = SUPPRIMEE", pg.evaluate("() => dlvPage().items.filter(x => x.ajout).length") == 0)
        pg.evaluate("() => $('dlvAnnuler').click()"); pg.wait_for_timeout(300)
        check("↶ rend la bulle supprimee", pg.evaluate("() => dlvPage().items.filter(x => x.ajout).length") == 1)
        n_ex = pg.evaluate("() => dlvPage().items.filter(x => x.exclu).length"); p1 = [x for x in pts()][0]
        pg.mouse.move(p1["x"], p1["y"]); pg.mouse.down(); pg.wait_for_timeout(900); pg.mouse.up(); pg.wait_for_timeout(300)
        check("appui long sur une bulle DETECTEE = exclue (pas supprimee)", pg.evaluate("() => dlvPage().items.filter(x => x.exclu).length") == n_ex + 1 and pg.evaluate("() => dlvPage().items.length") == len(P0) + 1)
        pg.evaluate("() => $('dlvAnnuler').click()"); pg.wait_for_timeout(300)
        t0 = pg.evaluate("() => $('dlvTitre').textContent")
        pg.mouse.move(cad["x"] + cad["w"] * 0.85, cad["y"] + cad["h"] * 0.5); pg.mouse.down()
        for k in range(1, 11): pg.mouse.move(cad["x"] + cad["w"] * (0.85 - 0.07 * k), cad["y"] + cad["h"] * 0.5); pg.wait_for_timeout(10)
        pg.mouse.up(); pg.wait_for_timeout(1200)
        t1 = pg.evaluate("() => $('dlvTitre').textContent")
        check("glisser la page vers la gauche = page suivante", ("p. %d" % A) in t0 and ("p. %d" % (A + 1)) in t1 if B > A else True, (t0, t1))
        for _ in range(10):
            if "Valider" in pg.evaluate("() => $('dlvGo').textContent"): break
            pg.evaluate("() => $('dlvGo').click()"); pg.wait_for_timeout(900)
        check("derniere page : « ✓ Valider » (plage deja preparee : rien de paye)", pg.evaluate("() => /✓ Valider/.test($('dlvGo').textContent) && !/préparer/.test($('dlvGo').textContent)"))
        pg.screenshot(path=os.path.join(HERE, "samsung_out", "verif_%d.png" % LARG))
        pg.evaluate("() => $('dlvGo').click()"); pg.wait_for_timeout(1500)
        vf = json.load(open(VF, encoding="utf-8")) if os.path.isfile(VF) else {}
        pg13 = (vf.get("pages") or {}).get(str(A)) or {}
        check("fichier ecrit : toutes les pages de la plage", sorted(int(k) for k in (vf.get("pages") or {})) == list(range(A, B + 1)), list((vf.get("pages") or {}).keys()))
        check("fichier : 1 ajout + ordre avec la derniere en tete (p.%d)" % A, len(pg13.get("ajouts") or []) == 1 and (len(P0) < 2 or pg13["ordre"][0]["id"] == ids0[-1]), pg13.get("ordre", [])[:2])
        check("apres validation : etape « ✓ Bulles » verte", pg.evaluate("() => { const b = $('dplBulles'); return /✓ Bulles/.test(b.textContent) && b.classList.contains('dpl-fait'); }"))
        pg.evaluate("() => $('dplBulles').click()"); pg.wait_for_timeout(3000)
        r = pg.evaluate("() => ({ aj: dlvPage().items.filter(x => x.ajout).length, first: dlvPage().items[0].id })")
        check("reouverture : ajout et ordre gardes", r["aj"] == 1 and (len(P0) < 2 or r["first"] == ids0[-1]), r)
        pg.evaluate("() => $('dlvFermer').click()"); pg.wait_for_timeout(400)
        # ---- 2. chapitre NON traduit : detection seule
        ouvrir(CHN)
        f = pg.evaluate("() => { const v = $('dplVerif'), p = $('dlgPreparer'); return { v: !!(v && v.offsetParent), vt: v && v.textContent, lien: p.classList.contains('dpl-sansverif'), pt: p.textContent }; }")
        check("nouvelle plage : « 🔍 Verifier les bulles · gratuit » en principal, « preparer sans verifier » en lien", f["v"] and "gratuit" in f["vt"] and f["lien"] and "sans vérifier" in f["pt"], f)
        pg.evaluate("() => { const l = document.querySelector('[data-dpl=pages]'); if (l) l.click(); }"); pg.wait_for_timeout(500)
        pg.evaluate("() => { $('dlgDe').value = 1; $('dlgA').value = 3; $('dlgDe').dispatchEvent(new Event('input')); }"); pg.wait_for_timeout(400)
        pg.evaluate("() => $('dplVerif').click()"); pg.wait_for_timeout(1500)
        att = pg.evaluate("() => $('dlvAttente').textContent")
        for _ in range(40):
            if pg.evaluate("() => $('dlvAttente').hidden"): break
            pg.wait_for_timeout(1000)
        n3 = []
        for _ in range(3):
            n3.append(len(pts())); pg.evaluate("() => $('dlvSuiv').click()"); pg.wait_for_timeout(900)
        check("detection seule lancee (message « gratuit »), puis pastilles sur les pages non traduites", "gratuit" in att and sum(n3) > 0, (att, n3))
        check("detection.json ecrit (gratuit, sur le PC)", os.path.isfile(os.path.join(T, CHN, "dialogues", "detection.json")))
        check("nouvelle plage : derniere page = « ✓ Valider et tout faire »", "tout faire" in pg.evaluate("() => $('dlvGo').textContent"))
        check("aucun debordement horizontal", not pg.evaluate("() => document.documentElement.scrollWidth > document.documentElement.clientWidth"))
        check("0 erreur JS", not errs, errs[:2])
        br.close()
finally:
    srv.terminate()
    try: srv.wait(10)
    except Exception: srv.kill()
    subprocess.run(["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -match 'dialogues.py' -and $_.ParentProcessId -eq %d } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" % srv.pid], capture_output=True)
    f8191 = os.path.expanduser(r"~\Documents\ComfyUI\_studio_llm_proxy_8191.py")
    if os.path.exists(f8191):
        os.remove(f8191)
    shutil.rmtree(T, ignore_errors=True)
print("\nVERDICT : %d/%d" % (len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
