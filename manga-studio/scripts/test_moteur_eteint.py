# -*- coding: utf-8 -*-
"""Banc v2.46.0 : MOTEUR LOCAL ETEINT -- l'app ne doit produire AUCUNE reponse en erreur, et les references des
personnages (fichiers du disque) doivent s'afficher quand meme. APP REELLE, 1280 px puis 360 px.

Avant v2.46.0 (mesure 25/09, un chapitre ouvert 60 s) : 10 reponses 502 -- sondes /comfy/system_stats, listes LoRA /
checkpoints, et les images de reference demandees au moteur (/comfy/view) -> invisibles moteur eteint.
Lecture seule : toute requete POST vers /manga/ autre que les lectures d'etat fait echouer le banc.
Le banc REFUSE de conclure si le moteur est allume (il ne mesurerait rien).
Usage : python test_moteur_eteint.py [port] [serie]
"""
import json, os, sys, urllib.request
from playwright.sync_api import sync_playwright

KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
PORT = sys.argv[1] if len(sys.argv) > 1 else "8190"
SERIE = sys.argv[2] if len(sys.argv) > 2 else "claymore"
BASE = "http://127.0.0.1:%s" % PORT
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail else ""))


def get(chemin, cle=True):
    rq = urllib.request.Request(BASE + chemin, headers={"Authorization": "Bearer " + KEY} if cle else {})
    try:
        with urllib.request.urlopen(rq, timeout=10) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


st, corps = get("/manga/comfy_up")
etat = json.loads(corps or b"{}") if st == 200 else {}
check("sonde /manga/comfy_up : 200", st == 200, st)
if etat.get("up"):
    print("\nMOTEUR ALLUME : ce banc mesure le cas « éteint », il ne conclut pas."); sys.exit(2)
check("sonde : moteur éteint vu comme tel", etat == {"up": False}, etat)
# confinement de la lecture disque (la cle est exigee, aucune sortie du dossier)
check("comfy_file sans clé → 401", get("/manga/comfy_file?filename=x.png&type=input", cle=False)[0] == 401)
for q, att in (("filename=..%2F_studio_llm_proxy.py&type=input", 400), ("filename=_studio_llm_proxy.py&type=input&subfolder=..", 403),
               ("filename=win.ini&type=input&subfolder=C:%2Fwindows", 403), ("filename=a.png&type=bogus", 400)):
    check("comfy_file refuse « %s » (%d)" % (q, att), get("/manga/comfy_file?" + q)[0] == att, get("/manga/comfy_file?" + q)[0])

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w, h in ((1280, 900), (360, 780)):
        print("=== %d px" % w)
        c = b.new_context(viewport={"width": w, "height": h}, has_touch=(w < 400), is_mobile=(w < 400))
        pg = c.new_page()
        mauvais, errs, ecrit = [], [], []
        pg.on("response", lambda r: mauvais.append("%d %s" % (r.status, r.url.split("?")[0].replace(BASE, ""))) if r.status >= 400 else None)
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("request", lambda r: ecrit.append(r.url) if r.method == "POST" and "/manga/" in r.url else None)
        pg.goto(BASE + "/manga#k=" + KEY); pg.wait_for_timeout(2500)
        pg.evaluate("s => { localStorage.setItem('manga_onglet','tChap'); localStorage.setItem('manga_serie', s); }", SERIE)
        pg.reload(); pg.wait_for_timeout(3500)
        check("version = VERSION du code", pg.inner_text("#verBadge").strip() == "v" + pg.evaluate("() => VERSION"))
        check("témoin moteur : éteint", "off" in pg.get_attribute("#dComfy", "class"))
        pg.click("#chapList [data-chap] >> nth=1"); pg.wait_for_selector("#chapDetail:not([hidden])", timeout=15000)
        pg.wait_for_timeout(2000)
        imgs = []
        for tab in ("tPerso", "tPlate", "tProj", "tGal", "tSet"):
            pg.evaluate("t => document.querySelector('nav button[data-tab=\"' + t + '\"]').click()", tab)   # 360 px : onglets rares caches
            pg.wait_for_timeout(2500)
            imgs += pg.evaluate("""() => [...document.querySelectorAll('img')].filter(i => /comfy/.test(i.src))
                                     .map(i => [i.src.split('?')[0].replace(location.origin, ''), i.complete, i.naturalWidth])""")
        # une sonde periodique du moteur passe (toutes les 15 s) : elle ne doit pas etre en erreur non plus
        pg.wait_for_timeout(16000)
        refs = [x for x in imgs if x[0].endswith("/manga/comfy_file")]
        check("images de ComfyUI lues sur le disque (plus aucune par /comfy/view)", not any(x[0].startswith("/comfy/") for x in imgs),
              sorted({x[0] for x in imgs}))
        check("au moins une référence de personnage vue", len(refs) > 0, len(refs))
        check("toutes les références s'affichent (largeur > 0)", refs and all(x[1] and x[2] > 0 for x in refs),
              [x for x in refs if not x[2]][:3])
        check("AUCUNE réponse en erreur, moteur éteint", not mauvais, mauvais[:8])
        check("aucune erreur JS", not errs, errs[:3])
        check("rien écrit (lecture seule)", not [u for u in ecrit if not any(k in u for k in ("activite", "costs"))], ecrit[:3])
        c.close()
    b.close()

print("\nVERDICT : %d OK / %d KO" % (len(OK), len(KO)))
sys.exit(1 if KO else 0)
