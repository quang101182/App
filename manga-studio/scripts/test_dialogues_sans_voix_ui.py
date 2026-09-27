# -*- coding: utf-8 -*-
"""Banc R1 (v2.81.6, Quang 27/09 02h30 : « ca ne lit que la premiere bulle quand une image en contient deux ») : le lecteur des
Dialogues ne SAUTE aucune replique. ISOLE : instance 8191 (proxy donne) sur une COPIE d'OPM ch.5 (12 voix, p.13-15) dont on
RETIRE 2 voix de la meme page ; page = le HTML donne (interception). 0 credit, rien d'ecrit dans les vraies donnees.
Usage : python test_dialogues_sans_voix_ui.py <html> <proxy>        (html = page v2.81.5 -> doit sortir ROUGE)"""
import json, os, shutil, subprocess, sys, tempfile, time, urllib.request
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
HTML, PROXY = (os.path.abspath(x) for x in sys.argv[1:3])
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
SRC = r"C:\Users\quang\Documents\MangaStudio-donnees\sources"
PAGE = open(HTML, encoding="utf-8").read()
OK, KO = [], []


def check(n, c, d=""):
    (OK if c else KO).append(n); print(("  [OK] " if c else "  [KO] ") + n + (" -- " + str(d)[:170] if d else ""), flush=True)


T = tempfile.mkdtemp(prefix="dlg_sans_voix_")
os.makedirs(os.path.join(T, "one-punch-man"))
shutil.copytree(os.path.join(SRC, "one-punch-man", "ch_5"), os.path.join(T, "one-punch-man", "ch_5"),
                ignore=shutil.ignore_patterns("video", "narration", "*.mp4"))
for f in ("serie.json", "dialogues_distribution.json", "suivi.json"):
    shutil.copy(os.path.join(SRC, "one-punch-man", f), os.path.join(T, "one-punch-man", f))
dj = os.path.join(T, "one-punch-man", "ch_5", "dialogues", "dialogues.json")
doc = json.load(open(dj, encoding="utf-8"))
p14 = [x for x in doc["repliques"] if x["page"] == 14 and x.get("lire") and x.get("voix")]
retirees = [x["cle"] for x in p14[1:3]]                          # 2 bulles de la MEME page perdent leur voix
for x in p14[1:3]:
    os.remove(os.path.join(T, "one-punch-man", "ch_5", "dialogues", "voix", x["voix"]["fichier"]))
doc["pages_vues"] = [12, 13, 14, 15, 16]              # R1-bis : p.12 et p.16 sans replique preparee -> etapes « sans dialogue »
json.dump(doc, open(dj, "w", encoding="utf-8"), ensure_ascii=False)
lues = [x for x in doc["repliques"] if x.get("lire")]
print("copie :", T, "| lues", len(lues), "| voix retirees", retirees)
srv = subprocess.Popen([sys.executable, os.path.join(HERE, "proxy_8191.py"), PROXY], env=dict(os.environ, MANGA_SOURCES_DIR=T),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(60):
        try:
            urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8191/manga/el_solde", headers={"Authorization": "Bearer " + KEY}), timeout=5); break
        except Exception:
            time.sleep(1)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True, args=["--autoplay-policy=no-user-gesture-required", "--mute-audio"])
        for w, h in ((1280, 900), (360, 780)):
            print("=== %d px" % w)
            ctx = b.new_context(viewport={"width": w, "height": h}, is_mobile=w < 500, has_touch=w < 500)
            pg = ctx.new_page(); errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.route("**/*", lambda rt: rt.fulfill(status=200, content_type="text/html; charset=utf-8", body=PAGE)
                     if rt.request.method == "GET" and rt.request.url.split("#")[0].split("?")[0].rstrip("/").endswith("/manga") else rt.continue_())
            pg.goto("http://127.0.0.1:8191/manga#k=" + KEY); pg.wait_for_timeout(2500)
            pg.evaluate("() => localStorage.setItem('manga_serie','one-punch-man')"); pg.reload(); pg.wait_for_timeout(3500)
            pg.evaluate("() => openChap(CHAPS.findIndex(c => c.dir === 'one-punch-man/ch_5'))"); pg.wait_for_timeout(3000)
            et = pg.evaluate("() => $('dlgEtat').textContent")
            check("R1-ter : la ligne dit la portee preparee « p. 12-16 (5 pages) »", "p. 12-16 (5 pages)" in et, et)
            check("R1-ter : champs restaures (des pages 12 a 16)", pg.evaluate("() => DLG.portee + ' ' + $('dlgDe').value + '-' + $('dlgA').value") == "pages 12-16",
                  pg.evaluate("() => DLG.portee + ' ' + $('dlgDe').value + '-' + $('dlgA').value"))
            pg.evaluate("() => dlgLecteur()"); pg.wait_for_timeout(2500)
            n = pg.evaluate("() => DLL.liste.filter(x => !x.vide).length")
            check("toutes les repliques lues sont dans le lecteur (%d)" % len(lues), n == len(lues), n)
            v = pg.evaluate("() => DLL.liste.filter(x => x.vide).map(x => x.page)")
            check("R1-bis : pages sans dialogue presentes (12, 16)", v == [12, 16], v)
            pg.evaluate("() => { DLL.i = 0; dllMontrer(); }"); pg.wait_for_timeout(1500)
            check("R1-bis : p.12 affichee avec le tampon « SANS DIALOGUE »", pg.evaluate("() => DLL.liste[DLL.i].page === 12 && !$('dllTampon').hidden && $('dllImg').naturalWidth > 0")
                  and "sans dialogue" in pg.evaluate("() => $('dllSous').textContent"))
            t0 = time.time()
            while time.time() - t0 < 8 and pg.evaluate("() => DLL.i") == 0:
                pg.wait_for_timeout(300)
            check("R1-bis : elle enchaine seule sur la p.13, tampon retire", pg.evaluate("() => DLL.liste[DLL.i].page") == 13 and pg.evaluate("() => $('dllTampon').hidden"))
            bandeau = pg.evaluate("() => { const b = document.getElementById('dllManq'); return b && !b.hidden ? b.textContent : '' }")
            check("bandeau « 2 répliques sans voix » + bouton Générer", "2 répliques" in bandeau and "Générer" in bandeau, bandeau)
            k = pg.evaluate("c => DLL.liste.findIndex(x => x.cle === c)", retirees[0])
            pg.evaluate("k => { DLL.i = k; dllMontrer(); }", k); pg.wait_for_timeout(1200)
            sous = pg.evaluate("() => $('dllSous').textContent")
            check("replique sans voix : sous-titre + « voix à faire / à refaire », pas de son", ("voix à faire" in sous or "voix à refaire" in sous) and pg.evaluate("() => DLL.audio.paused"), sous[:90])
            halo = pg.evaluate("() => !!document.querySelector('#dllSvg path')")
            check("replique sans voix : halo dessine sur sa bulle", halo)
            t0 = time.time()
            while time.time() - t0 < 20 and pg.evaluate("() => DLL.i") <= k + 1:
                pg.wait_for_timeout(300)
            check("elle ENCHAINE seule (2 sans voix, puis la suivante)", pg.evaluate("() => DLL.i") >= k + 2, pg.evaluate("() => DLL.i"))
            pg.evaluate("() => { DLL.i = 1; dllMontrer(); }"); pg.wait_for_timeout(1500)
            check("replique AVEC voix : son lance, pas de pastille", not pg.evaluate("() => DLL.audio.paused") and "voix à" not in pg.evaluate("() => $('dllSous').textContent"))
            deux = pg.evaluate("""() => { const e = { doc: { pages_vues: [2, 3, 4, 5, 30, 31, 32, 33, 34, 35], portees: ["2-5", "30-35"], repliques: [] } };
                const sauve = DLG.e; DLG.e = e; dlgPorteeDe(e); const r = [$('dlgDe').value + '-' + $('dlgA').value, dlgPlagesTxt(dlgPagesPreparees())];
                DLG.e = sauve; return r; }""")
            check("2 portees dans un chapitre (2-5 puis 30-35) : champs = la DERNIERE, etat = « 2-5, 30-35 »", deux == ["30-35", "2-5, 30-35"], deux)
            check("0 erreur JS", not errs, errs)
            ctx.close()
finally:
    srv.kill()
    shutil.rmtree(T, ignore_errors=True)
    try:
        os.remove(os.path.expanduser(r"~\Documents\ComfyUI\_studio_llm_proxy_8191.py"))
    except Exception:
        pass
print("VERDICT : %d OK / %d KO" % (len(OK), len(KO)))
