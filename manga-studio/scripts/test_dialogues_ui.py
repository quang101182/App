# -*- coding: utf-8 -*-
"""Banc D4 + D5 (ROADMAP 4-septdecies) : le mode Dialogues DANS l'app, bout en bout, ISOLE :
 - serveur de TEST 8191 (proxy_8191.py) pointe sur une COPIE temporaire (OPM ch.6, pages 5-7 traduites) ;
 - la page servie est la COPIE patchee de manga_studio.html (interception Playwright) -- l'app en service n'est pas touchee.
Appels REELS : preparation (~0,014 $), 1 ecoute (~50 credits), voix (~450 credits).
A. fiche : ligne 🎭 Dialogues juste apres Narration, « pas encore préparé », pastille de preparation, pas de « → 🎬 »
B. portee « Des pages 5 à 7 » + Préparer -> « préparé · N répliques » (+ activite)
C. ecran de preparation : distribution (persos + narrateur), 12 repliques, CHAIR DE POULE decochee, statuts ⚪
D. reglages : vitesse d'un perso enregistree ; renommer (ancien nom = alias) ; correction de texte (orange + ↺)
E. ecoute d'une replique (audio recu) ; Generer -> « prêts », statuts ✅ ; couts : ligne ElevenLabs
F. 360 px : ni la page ni l'ecran de preparation ne debordent ; 0 erreur JS
Usage : python test_dialogues_ui.py <manga_studio.html patchee> <proxy patche>
"""
import json, os, shutil, subprocess, sys, tempfile, time, urllib.request
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
HTML, PROXY = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
VRAI = os.path.expanduser(r"~\Documents\MangaStudio-donnees\sources\one-punch-man\ch_6")
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail)[:170] if detail else ""), flush=True)


T = tempfile.mkdtemp(prefix="banc_dui_")
ch = os.path.join(T, "opm", "ch_6")
os.makedirs(os.path.join(ch, "traduction", "fr"))
tr = json.load(open(os.path.join(VRAI, "traduction", "fr", "traduction.json"), encoding="utf-8"))
tr["pages"] = [p for p in tr["pages"] if p["page"] in (5, 6, 7)]
json.dump(tr, open(os.path.join(ch, "traduction", "fr", "traduction.json"), "w", encoding="utf-8"), ensure_ascii=False)
man = json.load(open(os.path.join(VRAI, "manifest.json"), encoding="utf-8"))
for f in os.listdir(VRAI):
    if f.startswith("page_") and f.endswith(".png"):
        shutil.copy(os.path.join(VRAI, f), os.path.join(ch, f))
for p in tr["pages"]:
    shutil.copy(os.path.join(VRAI, "traduction", "fr", p["file"]), os.path.join(ch, "traduction", "fr", p["file"]))
json.dump(man, open(os.path.join(ch, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False)
srv = subprocess.Popen([sys.executable, os.path.join(HERE, "proxy_8191.py"), PROXY], env=dict(os.environ, MANGA_SOURCES_DIR=T),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
PAGE = open(HTML, encoding="utf-8").read()
try:
    for _ in range(60):
        try:
            urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8191/manga/el_solde", headers={"Authorization": "Bearer " + KEY}), timeout=5); break
        except Exception:
            time.sleep(1)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        ctx = b.new_context(viewport={"width": 1280, "height": 900})
        pg = ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("dialog", lambda d: d.accept())
        pg.route("**/*", lambda rt: rt.fulfill(status=200, content_type="text/html; charset=utf-8", body=PAGE)
                 if rt.request.method == "GET" and rt.request.url.split("#")[0].split("?")[0].rstrip("/").endswith("/manga") else rt.continue_())
        pg.goto("http://127.0.0.1:8191/manga#k=" + KEY); pg.wait_for_timeout(2500)
        pg.evaluate("() => { localStorage.setItem('manga_onglet','tChap'); localStorage.setItem('manga_serie','opm'); localStorage.setItem('manga_chap_bloc','dlg'); }")
        pg.reload(); pg.wait_for_timeout(4000)
        pg.evaluate("() => openChap(CHAPS.findIndex(c => c.dir === 'opm/ch_6'))")
        pg.wait_for_timeout(4000)
        print("=== A. fiche")
        ordre = pg.evaluate("() => [...document.querySelectorAll('#chapDetail .cl-tete')].map(h => h.dataset.cl)")
        check("A. Dialogues juste apres Narration", ordre[:2] == ["narr", "dlg"], ordre)
        etat = pg.evaluate("() => document.querySelector('.cl-tete[data-cl=dlg] .cl-etat').textContent")
        check("A. « pas encore préparé »", "pas encore préparé" in etat, etat)
        check("A. pas de « → 🎬 » sur Dialogues", not pg.evaluate("() => !!document.querySelector('.cl-tete[data-cl=dlg] .cl-vers')"))
        check("A. pastille de preparation", "préparation" in pg.evaluate("() => document.querySelector('.cl-tete[data-cl=dlg] .cl-est').textContent"))
        print("=== B. preparer p.5-7")
        pg.click('#dlgBox .dlg-p[data-portee="pages"]'); pg.fill("#dlgDe", "5"); pg.fill("#dlgA", "7")
        pg.click("#dlgPreparer")
        vu_act = False
        for _ in range(120):
            pg.wait_for_timeout(1000)
            if "Dialogues" in (pg.evaluate("() => document.getElementById('actTxt') ? actTxt.textContent : ''") or ""): vu_act = True
            et = pg.evaluate("() => document.querySelector('.cl-tete[data-cl=dlg] .cl-etat').textContent")
            if "préparé" in et and "en cours" not in et and "pas encore" not in et: break
        check("B. « préparé · N répliques à mettre en voix »", "préparé" in et and "répliques" in et, et)
        check("B. activite « Dialogues » vue pendant la preparation", vu_act)
        print("=== C. ecran de preparation")
        pg.evaluate("() => dlgPrepOuvrir()"); pg.wait_for_timeout(2500)
        n = pg.evaluate("() => [document.querySelectorAll('#dlgPrep .dlgp-carte').length, document.querySelectorAll('#dlgPrep .dlgp-rep').length, !dlgPrep.hidden]")
        check("C. ecran ouvert : persos + narrateur, 12 repliques", n[2] and n[0] >= 3 and n[1] == 12, n)
        chair = pg.evaluate("() => { const r = [...document.querySelectorAll('#dlgPrep .dlgp-rep')].find(x => x.querySelector('[data-k=texte]').value.includes('CHAIR')); return r && !r.querySelector('[data-k=lire]').checked; }")
        check("C. CHAIR DE POULE decochee", chair)
        st = pg.evaluate("() => [...document.querySelectorAll('#dlgPrep .dlgp-rep .st')].map(x => x.textContent).join('')")
        check("C. statuts ⚪ (a faire)", st.count("⚪") >= 8, st)
        print("=== D. reglages")
        pg.evaluate("() => { const r = document.querySelector('#dlgPrep .dlgp-carte[data-p=\"0\"] [data-k=vitesse]'); r.value = '0.9'; r.dispatchEvent(new Event('change', {bubbles:true})); }")
        pg.wait_for_timeout(2500)
        d0 = json.load(open(os.path.join(T, "opm", "dialogues_distribution.json"), encoding="utf-8"))
        check("D. vitesse du 1er perso enregistree (0,9)", d0["persos"][0]["vitesse"] == 0.9, d0["persos"][0].get("vitesse"))
        ancien = d0["persos"][0]["nom"]
        pg.evaluate("() => { const r = document.querySelector('#dlgPrep .dlgp-carte[data-p=\"0\"] [data-k=renomme]'); r.value = 'Perso Renommé'; r.dispatchEvent(new Event('change', {bubbles:true})); }")
        pg.wait_for_timeout(3000)
        d1 = json.load(open(os.path.join(T, "opm", "dialogues_distribution.json"), encoding="utf-8"))
        check("D. renommer : nouveau nom + ancien en alias", d1["persos"][0]["nom"] == "Perso Renommé" and ancien in d1["persos"][0]["alias"], d1["persos"][0])
        pg.evaluate("() => { const r = document.querySelector('#dlgPrep .dlgp-rep[data-cle=\"7-2\"] [data-k=texte]'); r.value = 'Tu ne pourras JAMAIS me semer.'; r.dispatchEvent(new Event('change', {bubbles:true})); }")
        pg.wait_for_timeout(3000)
        mod = pg.evaluate("() => { const r = document.querySelector('#dlgPrep .dlgp-rep[data-cle=\"7-2\"]'); return [r.querySelector('.txt').classList.contains('mod'), !!r.querySelector('[data-annuler]')]; }")
        check("D. correction : bordure orange + « ↺ revenir »", mod == [True, True], mod)
        print("=== E. ecoute + voix")
        pg.evaluate("() => document.querySelector('#dlgPrep .dlgp-rep[data-cle=\"5-2\"] [data-ecoute-r]').click()")
        for _ in range(60):
            pg.wait_for_timeout(1000)
            if pg.evaluate("() => DLG.audio.src.includes('source_file')"): break
        check("E. ecoute d'une replique : audio recu", pg.evaluate("() => DLG.audio.src.includes('source_file')"))
        pg.wait_for_timeout(2500)
        pg.evaluate("() => $('dlgpGen') && $('dlgpGen').click()")
        for _ in range(180):
            pg.wait_for_timeout(1000)
            et = pg.evaluate("() => document.querySelector('.cl-tete[data-cl=dlg] .cl-etat').textContent")
            if et.startswith("prêts"): break
        check("E. voix faites : « prêts »", et.startswith("prêts"), et)
        pg.wait_for_timeout(3000)
        st = pg.evaluate("() => [...document.querySelectorAll('#dlgPrep .dlgp-rep .st')].map(x => x.textContent).join('')")
        check("E. statuts ✅", st.count("✅") >= 9 and "⚪" not in st and "🟠" not in st, st)
        pg.evaluate("() => $('dlgpRet').click()"); pg.wait_for_timeout(500)
        pg.evaluate("() => $('hdrCost').click()"); pg.wait_for_timeout(3000)
        cout = pg.evaluate("() => $('coutsCorps').textContent")
        check("E. couts : ligne ElevenLabs en credits", "ElevenLabs" in cout and "crédits" in cout, cout[:160])
        pg.evaluate("() => $('coutsFermer').click()")
        check("0 erreur JS (1280)", not errs, errs[:3])
        print("=== F. 360 px")
        ctx2 = b.new_context(viewport={"width": 360, "height": 780}, is_mobile=True, has_touch=True)
        p2 = ctx2.new_page(); errs2 = []
        p2.on("pageerror", lambda e: errs2.append(str(e)))
        p2.route("**/*", lambda rt: rt.fulfill(status=200, content_type="text/html; charset=utf-8", body=PAGE)
                 if rt.request.method == "GET" and rt.request.url.split("#")[0].split("?")[0].rstrip("/").endswith("/manga") else rt.continue_())
        p2.goto("http://127.0.0.1:8191/manga#k=" + KEY); p2.wait_for_timeout(2500)
        p2.evaluate("() => { localStorage.setItem('manga_onglet','tChap'); localStorage.setItem('manga_serie','opm'); localStorage.setItem('manga_chap_bloc','dlg'); }")
        p2.reload(); p2.wait_for_timeout(4000)
        p2.evaluate("() => openChap(CHAPS.findIndex(c => c.dir === 'opm/ch_6'))")
        p2.wait_for_timeout(4000)
        w = p2.evaluate("() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]")
        check("F. fiche : pas de debordement a 360", w[0] <= w[1], w)
        p2.evaluate("() => dlgPrepOuvrir()"); p2.wait_for_timeout(2500)
        w2 = p2.evaluate("() => [dlgPrep.scrollWidth, dlgPrep.clientWidth, Math.max(...[...dlgPrep.querySelectorAll('*')].map(e => e.getBoundingClientRect().right))]")
        check("F. ecran de preparation : pas de debordement a 360", w2[0] <= w2[1] + 1 and w2[2] <= 361, w2)
        p2.screenshot(path=os.path.join(tempfile.gettempdir(), "dlg_prep_360.png"))
        check("0 erreur JS (360)", not errs2, errs2[:3])
        b.close()
finally:
    srv.kill()
    try:
        os.remove(os.path.expanduser(r"~\Documents\ComfyUI\_studio_llm_proxy_8191.py"))
    except OSError:
        pass
    shutil.rmtree(T, ignore_errors=True)
print("\n%d OK, %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
