# -*- coding: utf-8 -*-
"""Fenetre dediee de l'espace prive sur le PC (S3, 24/09/2026) : ouvrir / fermer / ranger / retenir / etat.

Pourquoi : sans elle, l'appui long ouvrait l'espace prive DANS l'onglet Edge habituel de Quang -> son historique et
son cache gardaient l'adresse. Ici : fenetre Edge --app, PROFIL A PART (historique, cache et stockage isoles), port
de pilotage 9225 (loopback seul), ouverte a SA place (retenue par « Retenir », sinon la place par defaut, discrete).
Appele par le proxy (route /manga/espace_fenetre) -- jamais pour une demande venue du telephone (le proxy refuse).

Usage : python fenetre_espace.py ouvrir|fermer|ranger|retenir|etat      -> une ligne JSON sur la sortie
"""
import json, os, subprocess, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import cdp_mini as c

VERSION = "1.1.0"
PORT_CDP = 9225
PORT_APP = int(os.environ.get("MANGA_PRIVE_PORT", "8192"))
LA = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
PROFIL = os.path.join(LA, "EdgeApps", "MangaStudio-2")          # nom neutre, sur C:
CONF = os.path.join(LA, "manga-studio", "fenetre-2.json")
DEFAUT = {"left": 2389, "top": 1344, "width": 1100, "height": 1300}   # comme la capture : surtout sous l'ecran
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()


def place():
    try:
        return dict(DEFAUT, **json.load(open(CONF, encoding="utf-8")).get("place", {}))
    except Exception:
        return dict(DEFAUT)


def navigateur():
    try:
        v = json.load(urllib.request.urlopen("http://127.0.0.1:%d/json/version" % PORT_CDP, timeout=2))
        return c.Onglet(v["webSocketDebuggerUrl"])
    except Exception:
        return None


def page_id():
    l = json.load(urllib.request.urlopen("http://127.0.0.1:%d/json/list" % PORT_CDP, timeout=3))
    return next(t["id"] for t in l if t["type"] == "page")


def bornes(n):
    wid = n.cmd("Browser.getWindowForTarget", targetId=page_id())["windowId"]
    return wid, n.cmd("Browser.getWindowBounds", windowId=wid)["bounds"]



def profil_sans_synchro(profil):
    """S3 (24/09) : un profil Edge qui ne se connecte PAS au compte Microsoft et ne synchronise RIEN (sinon son
    historique remonterait sur les autres appareils de Quang : constate, Edge le proposait d'office). A appeler
    navigateur ferme ; complete par --disable-sync. Verifie le 24/09 : edge://settings/profiles/sync -> « Pas en
    cours de synchronisation »."""
    f = os.path.join(profil, "Default", "Preferences")
    os.makedirs(os.path.dirname(f), exist_ok=True)
    try:
        p = json.load(open(f, encoding="utf-8"))
    except Exception:
        p = {}
    p.setdefault("signin", {}).update(allowed=False, allowed_on_next_startup=False)
    p.setdefault("sync", {}).update(requested=False)
    p["sync"].pop("has_setup_completed", None); p["sync"].pop("keep_everything_synced", None)
    json.dump(p, open(f, "w", encoding="utf-8"))


def ouvrir():
    n = navigateur()
    if n:                                                        # deja ouverte : la ramener (depliee), rien d'autre
        with n:
            wid, b = bornes(n)
            if b.get("windowState") == "minimized":
                n.cmd("Browser.setWindowBounds", windowId=wid, bounds={"windowState": "normal"})
        with c.Onglet("ws://127.0.0.1:%d/devtools/page/%s" % (PORT_CDP, page_id())) as o:
            o.cmd("Page.bringToFront")
        return {"ok": True, "deja": True}
    edge = next(p for p in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe") if os.path.exists(p))
    os.makedirs(PROFIL, exist_ok=True)
    profil_sans_synchro(PROFIL)
    p = place()
    subprocess.Popen([edge, "--app=http://127.0.0.1:%d/manga/#k=%s" % (PORT_APP, KEY), "--user-data-dir=" + PROFIL, "--disable-sync",
                      "--remote-debugging-port=%d" % PORT_CDP, "--remote-allow-origins=http://127.0.0.1:%d" % PORT_CDP,
                      "--no-first-run", "--no-default-browser-check", "--disable-features=Translate",
                      "--window-position=%d,%d" % (p["left"], p["top"]), "--window-size=%d,%d" % (p["width"], p["height"])],
                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    for _ in range(40):
        time.sleep(0.25)
        if navigateur():
            return {"ok": True, "ouverte": True, "place": p}
    return {"error": "la fenetre ne repond pas"}


def main(action):
    if action == "ouvrir":
        return ouvrir()
    n = navigateur()
    if not n:
        return {"ok": True, "ouverte": False}
    with n:
        if action == "fermer":
            n.cmd("Browser.close")
            return {"ok": True, "ferme": True}
        wid, b = bornes(n)
        if action == "ranger":
            n.cmd("Browser.setWindowBounds", windowId=wid, bounds={"windowState": "normal"})
            n.cmd("Browser.setWindowBounds", windowId=wid, bounds=place())
            wid, b = bornes(n)
        elif action == "retenir":
            os.makedirs(os.path.dirname(CONF), exist_ok=True)
            json.dump({"place": {k: b[k] for k in ("left", "top", "width", "height")}}, open(CONF, "w", encoding="utf-8"))
        return {"ok": True, "ouverte": True, "bounds": b, "place": place()}


if __name__ == "__main__":
    a = sys.argv[1] if len(sys.argv) > 1 else "etat"
    if a not in ("ouvrir", "fermer", "ranger", "retenir", "etat"):
        print(json.dumps({"error": "action inconnue"})); sys.exit(1)
    try:
        print(json.dumps(main(a)))
    except Exception as e:
        print(json.dumps({"error": str(e)[:200]}))
