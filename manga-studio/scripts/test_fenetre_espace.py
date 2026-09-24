# -*- coding: utf-8 -*-
"""Banc S3 (compartiment secret, 24/09/2026) : la fenetre de capture de l'espace prive (CDP 9224) obeit aux memes
boutons que celle de l'espace normal (9223), par les vraies routes de l'app (/manga/pilote, /manga/fetch_edge sur 8192),
et l'autre fenetre ne bouge JAMAIS.

1. etat = la place retenue ; 2. deplacee ailleurs puis « Ranger » = retour a la place retenue ; 3. « Taille sure »
sur une fenetre trop petite = assez grande, position gardee ; 4. « Fermer » = 9224 ferme, 9223 intacte ; 5. rouverte
par l'app = a la place retenue. La fenetre normale : memes coordonnees du debut a la fin.
Fin : fenetre privee ouverte a sa place retenue (etat de Quang restaure), place retenue inchangee.
"""
import json, os, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
CONF = os.path.join(os.environ.get("LOCALAPPDATA", ""), "manga-fetch-2", "fenetre.json")
OK, KO = [], []


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail) if detail and not cond else ""), flush=True)


def post(port, chemin, corps):
    r = urllib.request.Request("http://127.0.0.1:%d%s" % (port, chemin), data=json.dumps(corps).encode(),
                               headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=60))


def page(cdp):
    try:
        l = json.load(urllib.request.urlopen("http://127.0.0.1:%d/json/list" % cdp, timeout=3))
        return next((t for t in l if t["type"] == "page"), None)
    except Exception:
        return None


def fen(port, cdp, action="fenetre_etat"):
    return post(port, "/manga/pilote", {"id": page(cdp)["id"], "action": action})


def deplacer(cdp, **b):
    import cdp_mini as c
    with c.Onglet(json.load(urllib.request.urlopen("http://127.0.0.1:%d/json/version" % cdp))["webSocketDebuggerUrl"]) as n:
        wid = n.cmd("Browser.getWindowForTarget", targetId=page(cdp)["id"])["windowId"]
        n.cmd("Browser.setWindowBounds", windowId=wid, bounds=b)


def pres(a, b, tol=12):
    return all(abs(a[k] - b[k]) <= tol for k in ("left", "top", "width", "height"))


place = json.load(open(CONF, encoding="utf-8"))["place"]
conf_avant = open(CONF, encoding="utf-8").read()
norm0 = fen(8190, 9223)["bounds"]
try:
    e = fen(8192, 9224)
    check("1. la fenetre privee est a sa place retenue", pres(e["bounds"], place), (e["bounds"], place))
    deplacer(9224, left=place["left"] - 600, top=place["top"] - 500, width=place["width"], height=place["height"])
    time.sleep(1)
    r = fen(8192, 9224, "fenetre_ranger")
    check("2. deplacee puis « Ranger » : revenue a sa place", pres(r["bounds"], place), (r["bounds"], place))
    deplacer(9224, left=place["left"], top=place["top"], width=600, height=700)
    time.sleep(1)
    t = fen(8192, 9224, "fenetre_taille")
    check("3. trop petite puis « Taille sure » : assez grande", t["assez_grande"], t["interieur"])
    check("3. ... position gardee", abs(t["bounds"]["left"] - place["left"]) <= 12 and abs(t["bounds"]["top"] - place["top"]) <= 12, t["bounds"])
    check("la fenetre normale n'a pas bouge (1-3)", pres(fen(8190, 9223)["bounds"], norm0, 2), norm0)
    f = fen(8192, 9224, "fenetre_fermer")
    time.sleep(3)
    check("4. « Fermer » : la fenetre privee est fermee", f.get("ferme") and page(9224) is None)
    check("4. ... la fenetre normale est toujours la, a sa place", page(9223) is not None and pres(fen(8190, 9223)["bounds"], norm0, 2))
finally:
    if page(9224) is None:
        post(8192, "/manga/fetch_edge", {})
        for _ in range(20):
            time.sleep(1)
            if page(9224): break
    time.sleep(2)
o = fen(8192, 9224)
check("5. rouverte par l'app : a sa place retenue", pres(o["bounds"], place), (o["bounds"], place))
check("place retenue inchangee (fichier)", open(CONF, encoding="utf-8").read() == conf_avant)
check("fenetre normale : memes coordonnees qu'au debut", pres(fen(8190, 9223)["bounds"], norm0, 2), norm0)
print("\n%d/%d" % (len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
