# -*- coding: utf-8 -*-
"""Banc D12 (v2.82.2) : doublons probables de personnages -- montres, JAMAIS fusionnes sans Quang. ISOLE : instance 8191 (proxy
patche 8) sur une COPIE d'OPM ch.5 ou l'on FABRIQUE deux doublons : « Cyborg blond » (= Genos, 2 repliques, autre voix) et
« Femme insecte » (= Fille-Moustique). On FUSIONNE le 1er, on REFUSE le 2e. 0 credit.
Usage : python test_dialogues_doublons_ui.py <html> <proxy>        (html = page v2.82.1 -> doit sortir ROUGE)"""
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


T = tempfile.mkdtemp(prefix="dlg_doublons_")
SD = os.path.join(T, "one-punch-man")
os.makedirs(SD)
shutil.copytree(os.path.join(SRC, "one-punch-man", "ch_5"), os.path.join(SD, "ch_5"), ignore=shutil.ignore_patterns("video", "narration", "*.mp4"))
for f in ("serie.json", "suivi.json"):
    shutil.copy(os.path.join(SRC, "one-punch-man", f), os.path.join(SD, f))
dist = json.load(open(os.path.join(SRC, "one-punch-man", "dialogues_distribution.json"), encoding="utf-8"))
genos = next(p for p in dist["persos"] if p["nom"] == "Genos")
autre_voix = next(p["voix_el"] for p in dist["persos"] if p["voix_el"] and p["voix_el"] != genos["voix_el"])
dist["persos"] += [dict(genos, nom="Cyborg blond", alias=[], voix_el=autre_voix, couleur="#6fb8ff"),
                   dict(genos, nom="Femme insecte", alias=[], genre="femme", couleur="#b58cff")]
dist["doublons"] = [{"garder": "Genos", "avec": ["Cyborg blond"], "raison": "meme cyborg, blond selon l'encrage"},
                    {"garder": "Fille-Moustique", "avec": ["Femme insecte"], "raison": "meme creature"}]
json.dump(dist, open(os.path.join(SD, "dialogues_distribution.json"), "w", encoding="utf-8"), ensure_ascii=False)
dj = os.path.join(SD, "ch_5", "dialogues", "dialogues.json")
doc = json.load(open(dj, encoding="utf-8"))
cles = [x["cle"] for x in doc["repliques"] if x.get("qui") == "Genos"][:2]
for x in doc["repliques"]:
    if x["cle"] in cles:
        x["qui"] = "Cyborg blond"
json.dump(doc, open(dj, "w", encoding="utf-8"), ensure_ascii=False)
srv = subprocess.Popen([sys.executable, os.path.join(HERE, "proxy_8191.py"), PROXY], env=dict(os.environ, MANGA_SOURCES_DIR=T),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(60):
        try:
            urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8191/manga/el_solde", headers={"Authorization": "Bearer " + KEY}), timeout=5); break
        except Exception:
            time.sleep(1)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True, args=["--mute-audio"])
        ctx = b.new_context(viewport={"width": 360, "height": 780}, is_mobile=True, has_touch=True)
        pg = ctx.new_page(); errs = []; boites = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("dialog", lambda d: (boites.append(d.message), d.accept()))
        pg.route("**/*", lambda rt: rt.fulfill(status=200, content_type="text/html; charset=utf-8", body=PAGE)
                 if rt.request.method == "GET" and rt.request.url.split("#")[0].split("?")[0].rstrip("/").endswith("/manga") else rt.continue_())
        pg.goto("http://127.0.0.1:8191/manga#k=" + KEY); pg.wait_for_timeout(2500)
        pg.evaluate("() => localStorage.setItem('manga_serie','one-punch-man')"); pg.reload()
        pg.wait_for_function("() => typeof RESUME !== 'undefined' && RESUME && RESUME.chapitres", timeout=30000); pg.wait_for_timeout(800)
        pg.evaluate("() => openChap(CHAPS.findIndex(c => c.dir === 'one-punch-man/ch_5'))"); pg.wait_for_timeout(3500)
        et = pg.evaluate("() => $('dlgEtat').textContent")
        check("ligne 🎭 : « 2 doublons probables (✏) »", "2 doublons probables" in et, et)
        pg.evaluate("() => dlgPrepOuvrir()"); pg.wait_for_timeout(2000)
        ban = pg.evaluate("() => [...document.querySelectorAll('#dlgPrep .dlgp-dbl')].map(x => x.innerText.replace(/\\s+/g, ' '))")
        check("ecran ✏ : 2 bandeaux, noms + raison + 2 boutons", len(ban) == 2 and "Cyborg blond" in ban[0] and "Genos" in ban[0] and "Fusionner" in ban[0]
              and "pas les mêmes" in ban[0] and "encrage" in ban[0], ban)
        check("aucune fusion faite toute seule", json.load(open(os.path.join(SD, "dialogues_distribution.json"), encoding="utf-8"))["persos"][-2]["nom"] == "Cyborg blond")
        plan0 = pg.evaluate("() => DLG.plan && DLG.plan.a_faire")
        pg.evaluate("() => document.querySelector('#dlgPrep [data-dbl=fusion][data-i=\"0\"]').click()"); pg.wait_for_timeout(3000)
        check("fusion : confirmation qui annonce « tous les chapitres » et les voix a refaire", boites and "TOUS les chapitres" in boites[-1] and "à refaire" in boites[-1], boites[-1:])
        d2 = json.load(open(os.path.join(SD, "dialogues_distribution.json"), encoding="utf-8"))
        g = next(p for p in d2["persos"] if p["nom"] == "Genos")
        check("distribution : « Cyborg blond » retire, devenu alias de Genos", "Cyborg blond" not in [p["nom"] for p in d2["persos"]] and "Cyborg blond" in g["alias"], [p["nom"] for p in d2["persos"]])
        doc2 = json.load(open(dj, encoding="utf-8"))
        check("les 2 repliques passent a Genos dans le chapitre", all(x["qui"] == "Genos" for x in doc2["repliques"] if x["cle"] in cles))
        plan1 = pg.evaluate("() => DLG.plan && DLG.plan.a_faire")
        # ces 2 voix avaient ete faites avec la voix de GENOS : sous « Cyborg blond » (autre voix) elles etaient a refaire (2) ;
        # fusionnees dans Genos, elles retrouvent leur voix d'origine -> rien a repayer (0). Le plan suit la voix du personnage.
        check("le plan suit la voix : 2 a refaire sous le doublon, 0 une fois rendues a Genos", plan0 == 2 and plan1 == 0, (plan0, plan1))
        ban = pg.evaluate("() => [...document.querySelectorAll('#dlgPrep .dlgp-dbl')].map(x => x.innerText.replace(/\\s+/g, ' '))")
        check("il ne reste que le 2e bandeau", len(ban) == 1 and "Femme insecte" in ban[0], ban)
        pg.evaluate("() => document.querySelector('#dlgPrep [data-dbl=non]').click()"); pg.wait_for_timeout(2500)
        d3 = json.load(open(os.path.join(SD, "dialogues_distribution.json"), encoding="utf-8"))
        check("« pas les mêmes » : note, bandeau parti, rien fusionne", ["Femme insecte", "Fille-Moustique"] in d3.get("pas_doublons", [])
              and not d3.get("doublons") and "Femme insecte" in [p["nom"] for p in d3["persos"]], (d3.get("pas_doublons"), d3.get("doublons")))
        check("plus aucun bandeau", pg.evaluate("() => document.querySelectorAll('#dlgPrep .dlgp-dbl').length") == 0)
        check("pas de debordement, 0 erreur JS", not errs and not pg.evaluate("() => $('dlgPrep').scrollWidth > $('dlgPrep').clientWidth + 1"), errs)
    # et le detecteur ne repropose pas un groupe refuse (dialogues.py : « pas_doublons »)
    sys.path.insert(0, HERE)
    import dialogues as dl
    d3["doublons"] = []
    ok_ecarte = ("Femme insecte", "Fille-Moustique") in {tuple(sorted(e)) for e in d3.get("pas_doublons") or []}
    check("dialogues.py lira « pas_doublons » (groupe refuse ecarte)", ok_ecarte and "pas_doublons" in open(os.path.join(HERE, "dialogues.py"), encoding="utf-8").read())
finally:
    srv.kill()
    shutil.rmtree(T, ignore_errors=True)
    try:
        os.remove(os.path.expanduser(r"~\Documents\ComfyUI\_studio_llm_proxy_8191.py"))
    except Exception:
        pass
print("VERDICT : %d OK / %d KO" % (len(OK), len(KO)))
