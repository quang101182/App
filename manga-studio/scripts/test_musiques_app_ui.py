"""Banc v2.9.0 (24/09) : « 🎵 Depuis un autre manga » -- reprendre une musique deja dans l'app, dans le profil ET le chapitre.

Serie jetable zz-essai-mus (3 pages de Solo Leveling ch.1, slug reecrit, titre « Essai Musique »). Aucune ecriture dans
une vraie serie : on verifie a la fin que les musiques de la serie SOURCE sont intactes (fichiers + choix.json).
Usage : python test_musiques_app_ui.py
"""
import hashlib, json, os, shutil, sys, time, urllib.request
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = 8190
S = "zz-essai-mus"
SRC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sources"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import banc_outils as bo
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


def api(path, body=None):
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (PORT, path), data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def empreinte_dossier(d):
    return {f: hashlib.sha1(open(os.path.join(d, f), "rb").read()).hexdigest() for f in sorted(os.listdir(d))} if os.path.isdir(d) else {}


sha = lambda f: hashlib.sha1(open(f, "rb").read()).hexdigest()
# une serie SOURCE reelle qui a des musiques (lecture seule)
source = next(s for s in sorted(os.listdir(SRC)) if not s.startswith(("_", ".", "zz-")) and os.path.isdir(os.path.join(SRC, s, "musique"))
              and any(f.lower().endswith(".mp3") for f in os.listdir(os.path.join(SRC, s, "musique"))))
avant = empreinte_dossier(os.path.join(SRC, source, "musique"))
print("serie source (lecture seule) :", source, list(avant))

bo.supprimer_serie(S)
d = os.path.join(SRC, S, "ch_1"); os.makedirs(d)
m = json.load(open(os.path.join(SRC, "claymore", "ch_1", "manifest.json"), encoding="utf-8"))   # serie stable
m.update(slug=S, title="Essai Musique", pages=m["pages"][:3])
for p in m["pages"]:
    shutil.copy2(os.path.join(SRC, "claymore", "ch_1", p["file"]), os.path.join(d, p["file"]))
json.dump(m, open(os.path.join(d, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False)
open(os.path.join(SRC, S, "pochette.jpg"), "wb").write(open(os.path.join(d, m["pages"][0]["file"]), "rb").read())   # pas d'appel AniList
md = os.path.join(SRC, S, "musique")
try:
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        pg = b.new_page(viewport={"width": 1280, "height": 900}); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto("http://127.0.0.1:%d/manga#k=%s" % (PORT, KEY)); pg.wait_for_timeout(2500)
        check("version affichee = celle du fichier", pg.inner_text("#verBadge") == "v" + bo.version_app())
        pg.click('nav button[data-tab="tChap"]'); pg.wait_for_timeout(1000)
        pg.evaluate("() => ouvrirSerie('%s')" % S); pg.wait_for_timeout(2500)

        print("1. profil de la serie (reglages du batch)")
        pg.click("#btnSuivi"); pg.wait_for_timeout(2500)          # le profil (reglages du batch)
        pg.click("#profMusApp"); pg.wait_for_timeout(4000)
        check("la boite s'ouvre sous le profil", pg.evaluate("() => $('gsBox').parentNode.id") == "profGsPlace")
        check("titre de la boite", "déjà dans l" in pg.inner_text("#gsBoxTitre"), pg.inner_text("#gsBoxTitre"))
        n1 = pg.locator("[data-app-prendre]").count()
        check("des musiques d'autres mangas sont proposees", n1 >= 1, n1)
        f1 = pg.locator("[data-app-prendre]").first.get_attribute("data-app-prendre")
        pg.locator("[data-app-prendre]").first.click(); pg.wait_for_timeout(4000)
        pris = sorted(f for f in os.listdir(md)) if os.path.isdir(md) else []
        check("copiee sous le nom de la serie", pris == ["Essai Musique 1.mp3"] or pris[:1] == ["Essai Musique 1.mp3"], pris)
        check("contenu identique a l'original", pris and sha(os.path.join(md, pris[0])) == sha(os.path.join(SRC, *f1.split("/"))))
        pg.wait_for_timeout(1000)
        check("etiquette « aussi dans » dans le profil", "aussi dans" in pg.inner_text("#profMusListe"), pg.inner_text("#profMusListe")[:120])
        check("cochee dans la selection de la serie", "Essai Musique 1" in (api("/manga/musiques?serie=" + S).get("serie_sel") or []))
        r = api("/manga/musiques_app?serie=" + S)
        check("elle n'est plus proposee ensuite", all(x["fichier"] != f1 for x in r["items"]) and len(r["items"]) == n1 - 1, len(r["items"]))
        r2 = api("/manga/musique_depuis_serie", {"serie": S, "fichier": f1})
        check("reprise en double refusee", "deja" in (r2.get("error") or ""), r2)
        r3 = api("/manga/musique_depuis_serie", {"serie": S, "fichier": "../../x/musique/a.mp3"})
        check("chemin hors de l'app refuse", bool(r3.get("error")), r3)

        print("2. fiche du chapitre")
        pg.evaluate("async () => { await openChap(CHAPS.findIndex(c => c.dir === '%s/ch_1')); }" % S); pg.wait_for_timeout(2500)
        pg.click("#musApp"); pg.wait_for_timeout(4000)
        check("la boite s'ouvre dans le chapitre", pg.evaluate("() => $('gsBox').parentNode.id") != "profGsPlace" and pg.is_visible("#gsBox"))
        n2 = pg.locator("[data-app-prendre]").count()
        check("meme liste (moins celle deja prise)", n2 == n1 - 1, (n1, n2))
        if n2:
            pg.locator("[data-app-prendre]").first.click(); pg.wait_for_timeout(4000)
            check("2e reprise = « Essai Musique 2 »", os.path.isfile(os.path.join(md, "Essai Musique 2.mp3")), sorted(os.listdir(md)))
            check("etiquette dans le chapitre", "aussi dans" in pg.inner_text("#musListe"), pg.inner_text("#musListe")[:120])
        print("2-bis. smartphone (380 px) : l'etiquette ne pousse rien hors de l'ecran (remarque Quang 24/09, v2.9.1)")
        pg.set_viewport_size({"width": 380, "height": 800}); pg.wait_for_timeout(800)
        pg.click("#gsFermer"); pg.wait_for_timeout(300)
        mesure = ("(sel) => [...document.querySelectorAll(sel)].filter(b => b.offsetParent).map(b => "
                  "Math.round(b.getBoundingClientRect().right))")
        for zone, sel in (("chapitre", "#musListe [data-mus-suppr]"), ("profil", "#profMusListe [data-pm-suppr]")):
            xs = pg.evaluate(mesure, sel)
            check("%s : poubelles dans l'ecran et alignees" % zone, xs and max(xs) <= 380 and len(set(xs)) == 1, xs)
        meme_ligne = pg.evaluate("() => [...document.querySelectorAll('#musListe .mus-it')].map(r => { const n = r.querySelector('.nom')"
                                 ".getBoundingClientRect(), t = r.querySelector('[data-mus-suppr]').getBoundingClientRect();"
                                 " return t.top < n.bottom && t.bottom > n.top; })")
        check("chapitre : poubelle sur la meme ligne que le nom", meme_ligne and all(meme_ligne), meme_ligne)
        pg.locator("#musListe").screenshot(path=os.path.join(os.environ.get("TEMP", "."), "mus_380.png"))
        check("etiquette sur sa propre ligne, sous le nom",
              pg.evaluate("() => { const a = document.querySelector('#musListe .mus-aussi'), n = a && a.parentNode;"
                          " return !!a && n.classList.contains('nom') && getComputedStyle(a).display === 'block'; }"))
        pg.set_viewport_size({"width": 1280, "height": 900}); pg.wait_for_timeout(500)
        print("3. bascule de source dans la meme boite")
        pg.click("#musGs"); pg.wait_for_timeout(3000)
        check("« Prendre dans Generate Studio » reaffiche la playlist", "Generate Studio" in pg.inner_text("#gsBoxTitre") and pg.is_visible("#gsBox"))
        check("aucune erreur JS", not errs, errs[:2])
        b.close()
finally:
    bo.supprimer_serie(S)
check("serie source INTACTE (musiques + choix.json)", empreinte_dossier(os.path.join(SRC, source, "musique")) == avant)
print("\n%d/%d" % (len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
