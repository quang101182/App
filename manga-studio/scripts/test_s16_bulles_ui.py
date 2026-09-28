# -*- coding: utf-8 -*-
"""Banc S16 (28/09/2026, app v3.5.8) : l'ecran 🔍 de verification des bulles APRES la traduction, sur l'app reelle.
Vecu (chapitre de la secondaire) : Quang valide sur la detection, « Tout faire » traduit, il rouvre -> n° superposes (ses bulles
entourees + les « complements » de la traduction) et bulles qu'il avait desactivees « reactivees » (cris apparus apres).
Rejoue ICI avec SA geometrie (zones reelles, AUCUN texte ni nom) posee sur 3 pages d'un chapitre de la principale :
  p.5 = sa p.8 : 3 bulles ENTOUREES + les complements 102-104 de la traduction -> 5 pastilles, pas 8, aucune superposee
  p.6 = sa p.9 : tout exclu, puis 2 cris apparus apres -> tout reste de cote, les 2 nouveaux marques
  p.7 = sa p.11, PAS encore validee : 4 « Ngh » -> mis de cote d'office (interrupteur eteint) ; « lire les cris » les inclut
Donnees et reglages ISOLES (copie temporaire, serveur de TEST 8191), tout lancement bloque sauf la detection.
Usage : python test_s16_bulles_ui.py <html> [--proxy copie_patchee.py] [--largeurs 360,476,704,933,1280]"""
import json, os, shutil, subprocess, sys, tempfile, time, urllib.request
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
args = [x for i, x in enumerate(sys.argv[1:], 1) if not x.startswith("--") and sys.argv[i - 1] not in ("--proxy", "--largeurs")]
HTML = os.path.abspath(args[0])
PROXY = os.path.abspath(sys.argv[sys.argv.index("--proxy") + 1]) if "--proxy" in sys.argv else os.path.expanduser(r"~\Documents\ComfyUI\_studio_llm_proxy.py")
LARGS = [int(x) for x in (sys.argv[sys.argv.index("--largeurs") + 1] if "--largeurs" in sys.argv else "360,1280").split(",")]
SRC = os.path.expanduser(r"~\Documents\MangaStudio-donnees\sources")
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
CH = "one-punch-man/ch_6"
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail)[:170] if detail != "" else ""), flush=True)


G = json.loads(open(os.path.join(HERE, "test_s16_bulles.py"), encoding="utf-8").read().split("GEO = json.loads(r'''")[1].split("''')")[0])
TXT = {5: {1: "Premiere replique.", 2: "Derniere replique.", 102: "Bulle entouree A", 103: "Bulle entouree B", 104: "Bulle entouree C"},
       6: {1: "NGH !!!", 2: "AH ♡", 102: "SE-EP ♡", 103: "SE-EP ♡"},
       7: {3: "Ca continue encore.", 4: "C'etait donc si bon ?", 104: "Ngh", 105: "Ngh", 106: "Ngh", 107: "Ngh"}}
MAP = {5: "8", 6: "9", 7: "11"}

T = tempfile.mkdtemp(prefix="s16_")
serie, chap = CH.split("/")
sd, cd = os.path.join(SRC, serie), os.path.join(SRC, serie, chap)
os.makedirs(os.path.join(T, serie, chap, "traduction", "fr"))
os.makedirs(os.path.join(T, serie, chap, "dialogues"))
for f in os.listdir(sd):
    if f.endswith(".json") and os.path.isfile(os.path.join(sd, f)):
        shutil.copy2(os.path.join(sd, f), os.path.join(T, serie, f))
for f in os.listdir(cd):
    if f.endswith(".json"):
        shutil.copy2(os.path.join(cd, f), os.path.join(T, serie, chap, f))
man = json.load(open(os.path.join(cd, "manifest.json"), encoding="utf-8"))
for n, q in enumerate(man.get("pages") or [], 1):
    dst = os.path.join(T, serie, chap, q["file"])
    shutil.copy2(os.path.join(cd, q["file"]), dst) if n in (5, 6, 7, 8, 9) else open(dst, "wb").close()
tr = json.load(open(os.path.join(cd, "traduction", "fr", "traduction.json"), encoding="utf-8"))
tr["pages"] = [p for p in tr["pages"] if p["page"] in (5, 6, 7)]
for p in tr["pages"]:
    p["bulles"] = [dict(b, trad=TXT[p["page"]][b["id"]], lue=True) for b in G[MAP[p["page"]]]["bulles"]]
    shutil.copy2(os.path.join(cd, "traduction", "fr", p["file"]), os.path.join(T, serie, chap, "traduction", "fr", p["file"]))
json.dump(tr, open(os.path.join(T, serie, chap, "traduction", "fr", "traduction.json"), "w", encoding="utf-8"), ensure_ascii=False)
VF = os.path.join(T, serie, chap, "dialogues", "bulles_verifiees.json")
# S17 (v3.5.9) : p.8 en DETECTION SEULE, texte lu sur la page (dialogues.py detecter 1.30.0) -> les cris de cote des l'ouverture
LU8 = [("SQUISH S", {"x": 0.1, "y": 0.1, "w": 0.06, "h": 0.05}), ("SuCK", {"x": 0.5, "y": 0.2, "w": 0.05, "h": 0.1}),
       ("Show me your miserable face.", {"x": 0.3, "y": 0.5, "w": 0.12, "h": 0.1}), ("", {"x": 0.7, "y": 0.7, "w": 0.05, "h": 0.12})]
json.dump({"pages": {"8": {"file": man["pages"][7]["file"], "bulles": [{"id": i + 1, "box": b, "lu": t} for i, (t, b) in enumerate(LU8)]}}},
          open(os.path.join(T, serie, chap, "dialogues", "detection.json"), "w", encoding="utf-8"))
json.dump({"pages": {"5": G["8"]["verif"], "6": G["9"]["verif"]}}, open(VF, "w", encoding="utf-8"))
REG = os.path.join(T, "_reglages.json")
for f in ("_reglages.json",):
    if os.path.exists(os.path.join(SRC, f)):
        r0 = json.load(open(os.path.join(SRC, f), encoding="utf-8")); r0.pop("petits_cris", None)
        json.dump(r0, open(REG, "w", encoding="utf-8"))
print("copie :", T)

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
            json.dump({"pages": {"5": G["8"]["verif"], "6": G["9"]["verif"]}}, open(VF, "w", encoding="utf-8"))
            ctx = br.new_context(viewport={"width": LARG, "height": 800}, is_mobile=LARG < 800, has_touch=False, service_workers="block")
            pg = ctx.new_page(); errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.on("dialog", lambda d: d.dismiss() if ("Tout" in d.message or "tout refaire" in d.message or "Refaire" in d.message) else d.accept())
            pg.route("**/*", lambda rt: rt.fulfill(status=200, content_type="text/html; charset=utf-8", body=PAGE)
                     if rt.request.method == "GET" and rt.request.url.split("#")[0].split("?")[0].rstrip("/").endswith("/manga") else
                     (rt.fulfill(status=200, body='{"ok":true}', content_type="application/json") if rt.request.method != "GET" and "dialogues_lancer" in rt.request.url
                      and '"detecter"' not in (rt.request.post_data or "") else rt.continue_()))
            pg.goto("http://127.0.0.1:8191/manga/#k=" + KEY); pg.wait_for_timeout(2500)
            pg.evaluate("s => { localStorage.setItem('manga_onglet','tChap'); localStorage.setItem('manga_serie', s); localStorage.setItem('manga_dlv_aide','0'); }", serie)
            pg.reload(); pg.wait_for_timeout(3500)
            pg.evaluate("d => openChap(CHAPS.findIndex(c => c.dir === d))", CH); pg.wait_for_timeout(2500)
            pg.evaluate("() => dlvOuvrir('5-8')"); pg.wait_for_timeout(4000)
            etat = lambda: pg.evaluate("""() => { const p = dlvPage(), R = +$('dlvSvg').dataset.r;
                const c = [...document.querySelectorAll('#dlvSvg [data-dlv-k] circle')].map(e => [+e.getAttribute('cx'), +e.getAttribute('cy')]);
                let sup = 0; c.forEach((a, i) => c.forEach((b, j) => { if (j > i && Math.hypot(a[0] - b[0], a[1] - b[1]) < R) sup++; }));
                return { page: p.page, items: p.items.map(x => ({ id: x.id, ex: !!x.exclu, nouv: !!x.nouv, cri: !!x.cri, aj: !!x.ajout })),
                         t: [...document.querySelectorAll('#dlvSvg [data-dlv-k]')].map(g => g.textContent), sup,
                         barre: !$('dlvCris') || $('dlvCris').hidden ? '' : $('dlvCris').textContent, deb: document.documentElement.scrollWidth > innerWidth + 1 }; }""")
            e5 = etat()
            check("p.5 (sa p.8) : 5 pastilles, pas 8 (entourees = complements)", e5["page"] == 5 and len(e5["t"]) == 5, e5["t"])
            check("p.5 : numerotees 1..5, aucune n'est de cote", e5["t"] == ["1", "2", "3", "4", "5"], e5["t"])
            check("p.5 : aucune pastille superposee", e5["sup"] == 0, e5["sup"])
            check("p.5 : pas de barre d'info (rien de mis de cote)", e5["barre"] == "", e5["barre"])
            pg.evaluate("() => dlvAller(1)"); pg.wait_for_timeout(700)
            e6 = etat()
            check("p.6 (sa p.9) : tout reste de cote (4 ✕, rien de reactive)", e6["t"] == ["✕"] * 4, e6["t"])
            check("p.6 : les 2 cris apparus apres sont marques « nouveaux »", sorted(x["id"] for x in e6["items"] if x["nouv"]) == [102, 103], e6["items"])
            check("p.6 : barre « 🆕 2 apparues apres ta validation »", "🆕 2" in e6["barre"] and "apparues" in e6["barre"], e6["barre"])
            pg.evaluate("() => dlvAller(2)"); pg.wait_for_timeout(700)
            e7 = etat()
            check("p.7 (non validee) : 4 « Ngh » mis de cote, 2 vraies repliques numerotees", sorted(e7["t"]) == sorted(["1", "2", "✕", "✕", "✕", "✕"])
                  and sorted(x["id"] for x in e7["items"] if x["cri"] and x["ex"]) == [104, 105, 106, 107], (e7["t"], e7["items"]))
            check("p.7 : barre « 🔇 4 petits cris » + bouton « lire les cris »", "🔇 4" in e7["barre"] and "lire les cris" in e7["barre"], e7["barre"])
            check("aucun defilement horizontal", not e7["deb"])
            vis = pg.evaluate("() => { const b = $('dlvCrisBtn'), r = b && b.getBoundingClientRect(); return !!(r && r.width > 0 && r.right <= innerWidth + 1 && r.bottom <= innerHeight); }")
            check("bouton « lire les cris » visible a l'ecran", vis)
            pg.evaluate("() => $('dlvCrisBtn') && $('dlvCrisBtn').click()"); pg.wait_for_timeout(1200)
            e7b = etat(); reg = json.load(open(REG, encoding="utf-8")) if os.path.exists(REG) else {}
            check("« lire les cris » : reglage enregistre POUR CETTE application (petits_cris = vrai)", reg.get("petits_cris") is True, reg)
            check("« lire les cris » : les 6 bulles de p.7 numerotees", sorted(e7b["t"]) == ["1", "2", "3", "4", "5", "6"], e7b["t"])
            check("« lire les cris » : p.6 VALIDEE intouchee", pg.evaluate("() => DLV.pages[1].items.filter(x => x.exclu).length") == 4)
            pg.evaluate("() => $('dlvCrisBtn') && $('dlvCrisBtn').click()"); pg.wait_for_timeout(1200)
            e7c = etat(); reg = json.load(open(REG, encoding="utf-8")) if os.path.exists(REG) else {}
            check("« ne plus lire les cris » : retour a 4 de cote, reglage faux", e7c["t"].count("✕") == 4 and reg.get("petits_cris") is False, (e7c["t"], reg.get("petits_cris")))
            P = pg.evaluate("""() => [...document.querySelectorAll('#dlvSvg [data-dlv-k]')].map(g => { const r = g.querySelector('circle').getBoundingClientRect();
                                  return { x: r.left + r.width / 2, y: r.top + r.height / 2, t: g.textContent }; })""")
            k = next(i for i, x in enumerate(P) if x["t"] == "✕")
            pg.mouse.click(P[k]["x"], P[k]["y"]); pg.wait_for_timeout(400)
            e7d = etat()
            check("toucher un cri de cote = inclus (3 numerotees)", e7d["t"].count("✕") == 3, e7d["t"])
            pg.evaluate("() => dlvAller(3)"); pg.wait_for_timeout(900)
            e8 = etat()
            check("p.8 (detection seule, texte lu) : « SQUISH S » et « SuCK » de cote, la phrase et l'illisible numerotees",
                  e8["page"] == 8 and sorted(e8["t"]) == ["1", "2", "✕", "✕"] and sorted(x["id"] for x in e8["items"] if x["cri"]) == [1, 2], (e8["t"], e8["items"]))
            check("p.8 : barre « 🔇 2 petits cris »", "🔇 2" in e8["barre"], e8["barre"])
            pg.evaluate("() => $('dlvGo').click()"); pg.wait_for_timeout(2500)
            v = json.load(open(VF, encoding="utf-8"))["pages"]
            check("✓ Valider : p.6 enregistree avec les 2 nouveaux en EXCLUES", sorted(x["id"] for x in v["6"]["exclues"]) == [1, 2, 102, 103], v["6"]["exclues"])
            check("✓ Valider : p.7 = 3 de cote en exclues, 3 dans l'ordre", len(v["7"]["exclues"]) == 3 and len(v["7"]["ordre"]) == 3, v["7"])
            check("✓ Valider : p.8 = ses 2 cris en exclues", sorted(x["id"] for x in v.get("8", {}).get("exclues", [])) == [1, 2], v.get("8"))
            check("✓ Valider : p.5 = 5 dans l'ordre, dont ses 3 entourees", len(v["5"]["ordre"]) == 5 and len(v["5"]["ajouts"]) == 3, v["5"])
            if LARG == LARGS[0]:                          # S17 : page detectee AVANT la lecture -> re-detection reelle a l'ouverture
                dj = os.path.join(T, serie, chap, "dialogues", "detection.json"); dd = json.load(open(dj, encoding="utf-8"))
                dd["pages"]["9"] = {"file": man["pages"][8]["file"], "bulles": [{"id": 1, "box": {"x": 0.2, "y": 0.2, "w": 0.1, "h": 0.1}}]}
                json.dump(dd, open(dj, "w", encoding="utf-8"))
                pg.evaluate("() => { $('dlvBox').hidden = true; }")
                pg.evaluate("() => dlvOuvrir('9-9')")
                for _ in range(60):
                    pg.wait_for_timeout(1500)
                    if pg.evaluate("() => !!(DLV.pages[0] && DLV.pages[0].lu === true && $('dlvAttente').hidden)"): break
                d9 = json.load(open(dj, encoding="utf-8"))["pages"]["9"]["bulles"]
                check("page detectee sans lecture -> re-detection a l'ouverture : chaque zone porte « lu »", d9 and all("lu" in b for b in d9), len(d9))
                check("... et l'ecran l'affiche avec le texte lu", pg.evaluate("() => DLV.pages[0].lu === true && DLV.pages[0].bulles.some(b => b.texte)"))
            check("aucune erreur JavaScript", not errs, errs[:2])
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
