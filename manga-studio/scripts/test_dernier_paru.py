# -*- coding: utf-8 -*-
"""Banc v2.67.0 / manga-fetch 0.8.0 : « JUSQU'AU DERNIER PARU » + chapitres deja la (ROADMAP § 4-quindecies, E6).
APP REELLE (8190) + vraies captures MangaDex (Frieren, francais : 141 -> 143, le 143 est le dernier paru).

A  depart 141, le 142 DEJA LA (dossier + manifeste poses par le banc) -> 141 et 143 captures, 142 saute SANS etre touche
   (date du manifeste inchangee), arret « aucun chapitre apres le 143 », tenu, bilan `dernier_paru` + `deja_la` ; pendant la
   capture : ligne d'activite « ch. fait(s) · jusqu'au dernier paru » + boutons « Apres ce chapitre » / « Maintenant ».
B  depart 142 (1er chapitre DEJA LA, sans --force = « le garder et continuer ») -> 142 et 143 sautes, rien recapture, tenu.
C  ecran : 4e puce, resume, puce grisee sur un site qui n'enchaine pas, bandeau VERT « a jour » avec « N capture(s), M deja la ».
D  proxy : « jusqu'au ch. » a plus de 300 d'ecart refuse ; « + N » accepte jusqu'a 300, refuse 301.
Mutation : --mutation-app retire le bandeau vert de l'app (copie servie ? non : fichier REEL, restaure a la fin) -> C doit rougir.
Nettoyage : serie du banc supprimee, bilan de Quang (_capture_derniere.json) remis a l'identique, onglets fermes.
"""
import json, os, shutil, sys, time, urllib.request
from urllib.parse import quote
from playwright.sync_api import sync_playwright

for f in (sys.stdout, sys.stderr):
    f.reconfigure(encoding="utf-8", errors="replace")
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
API, CDP, TITRE = "http://127.0.0.1:8190", "http://127.0.0.1:9223", "banc dernier paru"
ICI = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(ICI, "..", "sources"))
APP = os.path.normpath(os.path.join(ICI, "..", "manga_studio.html"))
BILAN = os.path.join(SRC, "_capture_derniere.json")
CH = {"141": "6e04e431-fc6b-4e38-b952-6232c72df112", "142": "58750ec8-ace6-4876-8e72-be6819106c0a",
      "143": "7568eb43-bc22-4104-ae49-7f28e392f0ad"}
MUT = "--mutation-app" in sys.argv
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail)[:300] if detail else ""))


def api(chemin, corps=None):
    rq = urllib.request.Request(API + chemin, data=json.dumps(corps).encode() if corps is not None else None,
                                headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"},
                                method="POST" if corps is not None else "GET")
    return json.load(urllib.request.urlopen(rq, timeout=30))


def onglet(ch):
    url = "https://mangadex.org/chapter/" + CH[ch]
    t = json.load(urllib.request.urlopen(urllib.request.Request(CDP + "/json/new?" + quote(url, safe=""), method="PUT")))
    for _ in range(20):
        time.sleep(2)
        for x in api("/manga/fetch_tabs")["tabs"]:
            if CH[ch] in x["url"]:
                return t["id"], x["url"]
    return t["id"], None


def attendre(cond, max_s=600):
    t0 = time.time()
    while time.time() - t0 < max_s:
        s = api("/manga/fetch_status")
        if cond(s): return s
        time.sleep(1)
    return api("/manga/fetch_status")


def bilan():
    time.sleep(2)
    return json.load(open(BILAN, encoding="utf-8"))


# ---- au repos ?
act = api("/manga/activite")["items"]
if act or api("/manga/fetch_status").get("etat") == "en cours":
    sys.exit("la principale n'est pas au repos : %s" % [x.get("type") for x in act])
serie = os.path.join(SRC, "banc-dernier-paru")
assert not os.path.exists(serie), "la serie du banc existe deja : a nettoyer d'abord"
sauve = open(BILAN, "rb").read() if os.path.exists(BILAN) else None
app_orig = open(APP, "rb").read() if MUT else None
tabs = []
try:
    if MUT:
        s = app_orig.decode("utf-8")
        a = "(j.tenu === false || (j.dernier_paru && j.tenu))"
        assert s.count(a) == 1
        open(APP, "wb").write(s.replace(a, "(j.tenu === false)").encode("utf-8"))
        print("MUTATION : bandeau vert « à jour » retiré de l'app")
    # le 142 « deja la » : dossier + manifeste poses par le banc
    d142 = os.path.join(serie, "ch_142"); os.makedirs(d142)
    for i in (1, 2):
        open(os.path.join(d142, "page_%03d.png" % i), "wb").write(b"\x89PNG banc 142 page %d" % i)
    json.dump({"title": TITRE, "chapter": "142", "pages": [{"file": "page_001.png"}, {"file": "page_002.png"}],
               "captured_at": "2026-01-01T00:00:00", "source": "banc"}, open(os.path.join(d142, "manifest.json"), "w"))
    m142 = os.path.getmtime(os.path.join(d142, "manifest.json"))

    print("=== D. plafonds (proxy) ===")
    tid, url141 = onglet("141"); tabs.append(tid)
    check("onglet 141 ouvert dans la fenêtre de capture", bool(url141))
    r = api("/manga/fetch_capture", {"tab": url141, "title": TITRE, "chapter": "141", "jusqua": "442"})
    check("« jusqu'au ch. » 141 → 442 (301 d'écart) refusé", "300" in (r.get("error") or ""), r)
    r = api("/manga/fetch_capture", {"tab": url141, "title": TITRE, "chapter": "141", "suite": 301})
    check("« + N » = 301 refusé", "300" in (r.get("error") or ""), r)

    print("=== A. dernier paru depuis 141, 142 déjà là ===")
    r = api("/manga/fetch_capture", {"tab": url141, "title": TITRE, "chapter": "141", "page1": True, "dernier_paru": True})
    check("A : capture lancée", r.get("ok"), r)
    s = attendre(lambda s: s.get("etat") == "en cours" and (s.get("pages") or 0) >= 1, 180)
    check("A : statut dernier_paru", s.get("dernier_paru") is True, {k: s.get(k) for k in ("etat", "dernier_paru", "jusqua")})
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        pg = b.new_page(viewport={"width": 360, "height": 780}, is_mobile=True, has_touch=True)
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(API + "/manga#k=" + KEY); pg.wait_for_timeout(4000)
        pg.evaluate("() => { actRafraichir(); $('actPanel').hidden = false; }"); pg.wait_for_timeout(1500); pg.evaluate("() => actRendre()")
        ligne = pg.evaluate("() => (document.querySelector('#actListe') || {}).innerText || ''")
        btn = pg.evaluate("() => [...document.querySelectorAll('#actListe [data-arret]')].map(b => b.dataset.arret)")
        check("écran : activité « ch. fait(s) · jusqu'au dernier paru »", "jusqu'au dernier paru" in ligne and "ch. fait(s)" in ligne, ligne[:200])
        check("écran : « Après ce chapitre » + « Maintenant » (série au total inconnu)", btn == ["apres", "maintenant"], btn)
        s = attendre(lambda s: s.get("etat") != "en cours", 900)
        bi = bilan()
        check("A : faits 141, 142, 143 ; déjà là = 142", bi.get("faits") == ["141", "142", "143"] and bi.get("deja_la") == ["142"],
              [bi.get("faits"), bi.get("deja_la"), bi.get("arret")])
        check("A : arrêt « aucun chapitre après le 143 sur ce site », tenu, dernier_paru, sans reprise",
              "aucun chapitre après le 143" in bi.get("arret", "") and bi.get("tenu") is True
              and bi.get("dernier_paru") is True and not bi.get("reprise"), bi.get("arret"))
        check("A : 142 NON touché (manifeste du banc, même date)",
              os.path.getmtime(os.path.join(d142, "manifest.json")) == m142 and sorted(os.listdir(d142)) == ["manifest.json", "page_001.png", "page_002.png"])
        n141 = len([f for f in os.listdir(os.path.join(serie, "ch_141")) if f.endswith((".png", ".jpg", ".webp"))]) if os.path.isdir(os.path.join(serie, "ch_141")) else 0
        n143 = len([f for f in os.listdir(os.path.join(serie, "ch_143")) if f.endswith((".png", ".jpg", ".webp"))]) if os.path.isdir(os.path.join(serie, "ch_143")) else 0
        check("A : 141 (22 p.) et 143 (22 p.) capturés", n141 == 22 and n143 == 22, [n141, n143])

        print("=== C. écran ===")
        pg.evaluate("() => { try { localStorage.removeItem('manga_cap_vu'); } catch {} }"); pg.reload(); pg.wait_for_timeout(5000)
        pg.evaluate("() => capAlerteVerifier()"); pg.wait_for_timeout(1500)
        ban = pg.evaluate("() => [!$('capAlerte').hidden, $('capAlerte').classList.contains('ok'), $('capAlerte').classList.contains('info'), $('capAlerteTxt').textContent, $('capAlerteReprendre').hidden, $('actErr').hidden]")
        check("écran : bandeau VERT « à jour : le ch. 143 est le dernier paru », « 2 capturé(s) (141, 143), 1 déjà là (142 …) », sans reprise ni ❌",
              ban[0] and ban[1] and not ban[2] and "à jour" in ban[3] and "le ch. 143 est le dernier paru" in ban[3]
              and "2 capturé(s) (141, 143), 1 déjà là (142, gardés tels quels)" in ban[3] and ban[4] and ban[5], ban)
        pg.evaluate("() => capAlerteVue()")
        # etape 4 : puce, resume, site qui n'enchaine pas
        pg.evaluate("""() => { CAP_TABS = [{ url: %s, title: 'banc' }]; $('capTab').innerHTML = '<option value="0">banc</option>';
                               $('capTab').value = '0'; $('capTitre').value = 'Banc'; $('capChap').value = '141'; capEnchMaj();
                               document.querySelector('#capChips [data-serie=dernier]').click(); }""" % json.dumps(url141))
        e4 = pg.evaluate("() => [[...document.querySelectorAll('#capChips .cap-chip')].map(b => b.textContent.trim() + (b.classList.contains('on') ? '*' : '') + (b.disabled ? '(x)' : '')), $('capResume').textContent]")
        check("écran : 4 puces, « Jusqu'au dernier paru » active", e4[0] == ["Ce chapitre seul", "Jusqu'au ch. …", "+ N suivants", "Jusqu'au dernier paru*"], e4[0])
        check("écran : résumé « puis tous les suivants, jusqu'au dernier paru »", "puis tous les suivants, jusqu'au dernier paru" in e4[1], e4[1])
        pg.evaluate("""() => { CAP_TABS = [{ url: 'https://exemple.invalid/lecteur?id=abc', title: 'x' }]; capEnchMaj(); }""")
        e5 = pg.evaluate("() => [document.querySelector('#capChips [data-serie=dernier]').disabled, $('capSerieMode').value, $('capEnch').textContent]")
        check("écran : site qui n'enchaîne pas → puce grisée, mode « seul »", e5[0] is True and e5[1] == "seul" and "⛔" in e5[2], e5)
        larg = {}
        for w in (360, 476, 704, 933, 1280):
            pg.set_viewport_size({"width": w, "height": 800}); pg.wait_for_timeout(300)
            larg[w] = pg.evaluate("() => [document.documentElement.scrollWidth <= innerWidth, (() => { const c = $('capChips').getBoundingClientRect(); return c.right <= innerWidth + 1; })()]")
        check("écran : aucun débordement 360 / 476 / 704 / 933 / 1280", all(all(v) for v in larg.values()), larg)
        check("aucune erreur JS", not errs, errs[:3])
        b.close()

    if not MUT:
        print("=== B. départ sur un chapitre DÉJÀ LÀ (« le garder et continuer ») ===")
        tid, url142 = onglet("142"); tabs.append(tid)
        m143 = os.path.getmtime(os.path.join(serie, "ch_143", "manifest.json"))
        r = api("/manga/fetch_capture", {"tab": url142, "title": TITRE, "chapter": "142", "page1": True, "dernier_paru": True, "force": False})
        check("B : capture lancée sans --force", r.get("ok"), r)
        attendre(lambda s: s.get("etat") != "en cours", 400)
        bi = bilan()
        check("B : 142 et 143 sautés (déjà là), aucun recapturé, tenu",
              bi.get("faits") == ["142", "143"] and bi.get("deja_la") == ["142", "143"] and bi.get("tenu") is True
              and os.path.getmtime(os.path.join(d142, "manifest.json")) == m142
              and os.path.getmtime(os.path.join(serie, "ch_143", "manifest.json")) == m143, [bi.get("faits"), bi.get("deja_la"), bi.get("arret")])
finally:
    if MUT and app_orig is not None:
        open(APP, "wb").write(app_orig); print("app restaurée")
    for t in tabs:
        try: urllib.request.urlopen(CDP + "/json/close/" + t)
        except Exception: pass
    shutil.rmtree(serie, ignore_errors=True)
    if sauve is not None: open(BILAN, "wb").write(sauve)
    elif os.path.exists(BILAN): os.remove(BILAN)
    print("nettoyage : série du banc supprimée, bilan de Quang " + ("restauré" if sauve is not None else "absent au départ"))

print("\nVERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
