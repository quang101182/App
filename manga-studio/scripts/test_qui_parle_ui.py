# -*- coding: utf-8 -*-
"""Banc v3.5.0 (S4, maquette_qui_parle_v1 validee 27/09 20h38) : 🎭 « Qui parle ? » pendant la verification des bulles, de bout en
bout, SANS toucher aux vraies donnees ni rien payer. Copies LEGERES (json, dialogues/, pages de la plage) dans un dossier temporaire,
serveur de TEST 8191 (proxy patche fourni), VRAIS gestes souris a 360 px. Tout lancement (preparer / voix / video / tout) est bloque.
Controle : rangee des personnages de la serie ; pinceau (bandeau, .on) ; toucher la PASTILLE et toucher le TEXTE d'une bulle =
attribuee ; retoucher = rendue a l'IA ; ↶ ; le pinceau suit la page suivante ; pinceau range = toucher redevient « exclure » ;
« ＋ » nouveau personnage (♀) = cree dans la distribution AVEC une voix, pinceau sur lui ; Valider -> « qui » dans
bulles_verifiees.json ET applique tout de suite a la replique deja preparee (qui + corrige.qui) ; reouverture : garde ;
l'IA en pale (quiIA) ; aucun debordement ; 0 erreur JS.
Usage : python test_qui_parle_ui.py <html> <proxy patche> <serie/ch traduit avec plage preparee> [--704]"""
import json, os, shutil, subprocess, sys, tempfile, time, urllib.request
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
args = [x for x in sys.argv[1:] if not x.startswith("--")]
HTML, PROXY, CH = os.path.abspath(args[0]), os.path.abspath(args[1]), args[2]
LARG = 704 if "--704" in sys.argv else 360
SRC = os.path.expanduser(r"~\Documents\MangaStudio-donnees\sources")
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail)[:170] if detail else ""), flush=True)


T = tempfile.mkdtemp(prefix="quiparle_")


def copie(ch, pages):
    serie, chap = ch.split("/"); sd, cd = os.path.join(SRC, serie), os.path.join(SRC, serie, chap)
    os.makedirs(os.path.join(T, serie, chap), exist_ok=True)
    for f in os.listdir(sd):
        if f.endswith(".json") and os.path.isfile(os.path.join(sd, f)):
            shutil.copy2(os.path.join(sd, f), os.path.join(T, serie, f))
    for f in os.listdir(cd):
        if f.endswith(".json"):
            shutil.copy2(os.path.join(cd, f), os.path.join(T, serie, chap, f))
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
    os.makedirs(os.path.join(T, serie, chap, "traduction", "fr"))
    shutil.copy2(os.path.join(tf, "traduction.json"), os.path.join(T, serie, chap, "traduction", "fr", "traduction.json"))
    for n in pages:
        f = os.path.join(tf, "page_%03d.png" % n)
        if os.path.isfile(f):
            shutil.copy2(f, os.path.join(T, serie, chap, "traduction", "fr", "page_%03d.png" % n))


doc = json.load(open(os.path.join(SRC, CH, "dialogues", "dialogues.json"), encoding="utf-8"))
pp = sorted({x["page"] for x in doc["repliques"]}); A, B = pp[0], pp[-1]
copie(CH, set(range(A, B + 1)))
print("copie :", T, "· plage", A, "-", B)
PAGE = open(HTML, encoding="utf-8").read()
srv = subprocess.Popen([sys.executable, os.path.join(HERE, "proxy_8191.py"), PROXY], env=dict(os.environ, MANGA_SOURCES_DIR=T),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
VF = os.path.join(T, CH, "dialogues", "bulles_verifiees.json")
DJ = os.path.join(T, CH, "dialogues", "dialogues.json")
DIST = os.path.join(T, CH.split("/")[0], "dialogues_distribution.json")
NOUVEAU = "Témoin banc"
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
        pg.on("dialog", lambda d: d.dismiss())                                  # aucune confirmation acceptee : jamais de lancement
        pg.route("**/*", lambda rt: rt.fulfill(status=200, content_type="text/html; charset=utf-8", body=PAGE)
                 if rt.request.method == "GET" and rt.request.url.split("#")[0].split("?")[0].rstrip("/").endswith("/manga") else
                 (rt.fulfill(status=200, body='{"ok":true}', content_type="application/json") if rt.request.method != "GET" and "dialogues_lancer" in rt.request.url
                  else rt.continue_()))                                          # TOUT lancement bloque
        pg.goto("http://127.0.0.1:8191/manga/#k=" + KEY); pg.wait_for_timeout(2500)
        pg.evaluate("s => { localStorage.setItem('manga_onglet','tChap'); localStorage.setItem('manga_serie', s); localStorage.setItem('manga_dlv_aide','1'); }", CH.split("/")[0])
        pg.reload(); pg.wait_for_timeout(3500)
        pg.evaluate("d => openChap(CHAPS.findIndex(c => c.dir === d))", CH); pg.wait_for_timeout(3000)
        pg.evaluate("() => clOuvrir('dlg')"); pg.wait_for_timeout(2500)
        pg.evaluate("k => { const c = [...document.querySelectorAll('#dplListe .dpl')].find(x => x.querySelector('.t').textContent === k); if (c) c.click(); }", "p. %d-%d" % (A, B) if A != B else "p. %d" % A)
        pg.wait_for_timeout(800)
        pg.evaluate("() => $('dplBulles').click()"); pg.wait_for_timeout(3500)
        pts = lambda: pg.evaluate("""() => [...document.querySelectorAll('#dlvSvg [data-dlv-k]')].map(g => { const r = g.querySelector('circle').getBoundingClientRect();
                                      return { x: r.left + r.width / 2, y: r.top + r.height / 2, t: g.textContent }; })""")
        items = lambda: pg.evaluate("() => dlvPage().items.map(x => ({ id: x.id, qui: x.qui || '', ia: x.quiIA || '', ex: !!x.exclu }))")
        persos = pg.evaluate("() => dlgPersos().map(p => p.nom)")
        chips = pg.evaluate("() => [...document.querySelectorAll('#dlvQui [data-dlvp]')].map(b => b.dataset.dlvp)")
        parlent = pg.evaluate("() => [...new Set((DLG.e.doc.repliques || []).map(x => x.qui).filter(q => q && q !== 'inconnu'))]")
        check("rangee COMPACTE : ceux qui parlent deja dans le chapitre (5 max), « 👥 +N », ＋", pg.evaluate("() => !$('dlvQui').hidden")
              and set(chips[:-2]) <= set(parlent) and 0 < len(chips) - 2 <= 5 and chips[-2:] == ["tous", "+"], (parlent, chips))
        pg.click('#dlvQui [data-dlvp="tous"]'); pg.wait_for_timeout(300)
        tous = pg.evaluate("() => [...document.querySelectorAll('#dlvQui [data-dlvp]')].map(b => b.dataset.dlvp)")
        check("« 👥 » deplie TOUTE la distribution (narrateur compris), « ‹ moins » la replie", tous[:len(persos)] == persos, tous)
        pg.click('#dlvQui [data-dlvp="tous"]'); pg.wait_for_timeout(300)
        persos = chips[:-2]
        check("l'IA en pale : attributions deja faites lues (quiIA)", any(x["ia"] for x in items()), items())
        heros = persos[0]
        pg.click('#dlvQui [data-dlvp="%s"]' % heros.replace('"', '\\"')); pg.wait_for_timeout(300)
        a = pg.evaluate("() => ({ on: !!document.querySelector('#dlvQui .dlv-p.on'), pin: DLV.pin, aide: $('dlvAide').classList.contains('pinceau') && !$('dlvAide').hidden, t: $('dlvAide').textContent })")
        check("toucher un personnage = pinceau (bouton actif + bandeau a sa couleur)", a["on"] and a["pin"] == heros and a["aide"] and heros in a["t"], a)
        P = pts()
        pg.mouse.click(P[0]["x"], P[0]["y"]); pg.wait_for_timeout(300)
        check("pinceau : toucher la PASTILLE 1 = bulle a lui", items()[0]["qui"] == heros and not items()[0]["ex"], items()[0])
        c2 = pg.evaluate("() => { const it = dlvPage().items[1], r = $('dlvCadre').getBoundingClientRect(); return it ? { x: r.left + (it.box.x + it.box.w / 2) * r.width, y: r.top + (it.box.y + it.box.h / 2) * r.height } : null; }")
        if c2:
            pg.mouse.click(c2["x"], c2["y"]); pg.wait_for_timeout(300)
            check("pinceau : toucher le TEXTE de la bulle 2 = a lui aussi", items()[1]["qui"] == heros, items()[1])
        n_init = pg.evaluate("() => document.querySelectorAll('#dlvSvg g[opacity=\"1\"] text').length")
        check("dessin : une pastille-personnage PLEINE par bulle attribuee", n_init == sum(1 for x in items() if x["qui"]), n_init)
        check("bas : compte des attributions (🎭)", "🎭" in pg.evaluate("() => $('dlvGo').textContent"), pg.evaluate("() => $('dlvGo').textContent"))
        pg.mouse.click(P[0]["x"], P[0]["y"]); pg.wait_for_timeout(300)
        check("retoucher la bulle 1 avec le meme pinceau = rendue a l'IA", items()[0]["qui"] == "", pg.evaluate("() => $('dlvToast').textContent"))
        pg.evaluate("() => $('dlvAnnuler').click()"); pg.wait_for_timeout(300)
        check("↶ = l'attribution revient", items()[0]["qui"] == heros)
        titre0 = pg.evaluate("() => $('dlvTitre').textContent")
        if B > A:
            pg.evaluate("() => $('dlvSuiv').click()"); pg.wait_for_timeout(1200)
            check("le pinceau SUIT la page suivante", pg.evaluate("() => DLV.pin") == heros and pg.evaluate("() => $('dlvTitre').textContent") != titre0)
            pg.evaluate("() => $('dlvPrec').click()"); pg.wait_for_timeout(1200)
        pg.click('#dlvQui [data-dlvp="%s"]' % heros.replace('"', '\\"')); pg.wait_for_timeout(300)
        check("retoucher le personnage = pinceau range (aide d'origine)", pg.evaluate("() => DLV.pin") == "" and "exclure" in pg.evaluate("() => $('dlvAide').textContent"))
        P = pts(); pg.mouse.click(P[-1]["x"], P[-1]["y"]); pg.wait_for_timeout(300)
        check("sans pinceau, toucher une pastille = EXCLURE (comme avant)", items()[-1]["ex"], items()[-1])
        pg.evaluate("() => $('dlvAnnuler').click()"); pg.wait_for_timeout(300)
        # nouveau personnage
        pg.click('#dlvQui [data-dlvp="+"]'); pg.wait_for_timeout(300)
        check("＋ = saisie du nom visible", pg.evaluate("() => !$('dlvNouv').hidden"))
        pg.fill("#dlvNouvNom", NOUVEAU); pg.click('#dlvNouv [data-dlvg="femme"]'); pg.wait_for_timeout(2500)
        dist = json.load(open(DIST, encoding="utf-8"))
        np_ = next((q for q in dist["persos"] if q["nom"] == NOUVEAU), None)
        check("nouveau personnage cree dans la distribution (femme) AVEC une voix", bool(np_) and np_.get("genre") == "femme" and bool(np_.get("voix_el")), np_)
        check("… et le pinceau est sur lui, saisie refermee", pg.evaluate("() => DLV.pin") == NOUVEAU and pg.evaluate("() => $('dlvNouv').hidden"))
        P = pts(); pg.mouse.click(P[-1]["x"], P[-1]["y"]); pg.wait_for_timeout(300)
        ref = items()
        check("bulle derniere -> nouveau personnage", ref[-1]["qui"] == NOUVEAU, ref[-1])
        # valider
        for _ in range(10):
            if "Valider" in pg.evaluate("() => $('dlvGo').textContent"): break
            pg.evaluate("() => $('dlvGo').click()"); pg.wait_for_timeout(900)
        pg.evaluate("() => $('dlvGo').click()"); pg.wait_for_timeout(2500)
        vf = json.load(open(VF, encoding="utf-8"))
        o = (vf["pages"].get(str(A)) or {}).get("ordre") or []
        quis = {r["id"]: r.get("qui") for r in o}
        check("verification enregistree : « qui » sur les bulles attribuees (p.%d)" % A, quis.get(ref[0]["id"]) == heros and quis.get(ref[-1]["id"]) == NOUVEAU, quis)
        dj = json.load(open(DJ, encoding="utf-8"))
        rp = {x["id"]: x for x in dj["repliques"] if x["page"] == A}
        x0, xn = rp.get(ref[0]["id"]) or {}, rp.get(ref[-1]["id"]) or {}
        check("applique TOUT DE SUITE aux repliques deja preparees (qui + corrige.qui)", x0.get("qui") == heros and (x0.get("corrige") or {}).get("qui") == heros
              and xn.get("qui") == NOUVEAU and (xn.get("corrige") or {}).get("qui") == NOUVEAU, (x0.get("qui"), x0.get("corrige"), xn.get("qui")))
        pg.wait_for_timeout(1500)
        pg.evaluate("() => $('dplBulles').click()"); pg.wait_for_timeout(3500)
        r2 = items()
        check("reouverture : attributions gardees", r2[0]["qui"] == heros and r2[-1]["qui"] == NOUVEAU, r2)
        pg.screenshot(path=os.path.join(HERE, "samsung_out", "qui_parle_%d.png" % LARG))
        check("aucun debordement horizontal (page + rangee)", not pg.evaluate("() => document.documentElement.scrollWidth > document.documentElement.clientWidth || $('dlvQui').scrollWidth > $('dlvQui').clientWidth + 1"))
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
