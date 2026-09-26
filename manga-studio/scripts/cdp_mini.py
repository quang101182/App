# -*- coding: utf-8 -*-
"""Client CDP minimal, bibliotheque standard seule (Manga Studio v2.0.0, 22/09/2026, etape 17 -- telecommande).

Pourquoi pas une bibliotheque : le proxy 8190 tourne dans le venv de Generate Studio, qui n'a ni `websocket-client`
ni `websockets` (verifie le 22/09) ; y installer un paquet pour une autre app = toucher un environnement partage.
Ici : poignee de main websocket RFC 6455, trames texte masquees (client), reponses associees par id ; les
evenements CDP recus entre-temps sont ignores. Une connexion par commande groupee (rien ne reste ouvert).

Usage : with Onglet(ws_url) as o: o.cmd("Page.captureScreenshot", format="jpeg", quality=60)
"""
import base64, json, os, socket, struct, urllib.parse

_ID = [0]


class ErreurCDP(RuntimeError):
    pass


class Onglet:
    def __init__(self, ws_url, timeout=15):
        u = urllib.parse.urlparse(ws_url)
        if u.hostname not in ("127.0.0.1", "localhost"):
            raise ErreurCDP("CDP distant refuse : " + str(u.hostname))
        self.s = socket.create_connection((u.hostname, u.port or 80), timeout=timeout)
        cle = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall(("GET %s HTTP/1.1\r\nHost: %s:%d\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                        "Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n"
                        % (u.path or "/", u.hostname, u.port or 80, cle)).encode())
        tete = b""
        while b"\r\n\r\n" not in tete:
            b = self.s.recv(4096)
            if not b:
                raise ErreurCDP("poignee de main websocket coupee")
            tete += b
        if b" 101 " not in tete.split(b"\r\n", 1)[0]:
            raise ErreurCDP("poignee de main refusee : " + tete.split(b"\r\n", 1)[0].decode("latin-1"))
        self.tampon = tete.split(b"\r\n\r\n", 1)[1]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        try:
            self.s.close()
        except OSError:
            pass

    def _envoyer(self, texte):
        data = texte.encode("utf-8")
        masque = os.urandom(4)
        n = len(data)
        tete = bytes([0x81]) + (bytes([0x80 | n]) if n < 126 else
                                bytes([0x80 | 126]) + struct.pack(">H", n) if n < 65536 else
                                bytes([0x80 | 127]) + struct.pack(">Q", n))
        self.s.sendall(tete + masque + bytes(b ^ masque[i % 4] for i, b in enumerate(data)))

    def _lire(self, n):
        while len(self.tampon) < n:
            b = self.s.recv(1 << 20)
            if not b:
                raise ErreurCDP("connexion CDP coupee")
            self.tampon += b
        out, self.tampon = self.tampon[:n], self.tampon[n:]
        return out

    def _trame(self):
        """Un message complet (les fragments de continuation sont recolles)."""
        morceaux = []
        while True:
            b0, b1 = self._lire(2)
            fin, op, n = b0 & 0x80, b0 & 0x0F, b1 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._lire(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._lire(8))[0]
            masque = self._lire(4) if b1 & 0x80 else None
            data = self._lire(n)
            if masque:
                data = bytes(b ^ masque[i % 4] for i, b in enumerate(data))
            if op == 0x8:
                raise ErreurCDP("onglet ferme")
            if op == 0x9:                                   # ping -> pong
                self.s.sendall(bytes([0x8A, 0x80 | len(data)]) + b"\0\0\0\0" + data)
                continue
            morceaux.append(data)
            if fin:
                return b"".join(morceaux)

    def cmd(self, methode, **params):
        _ID[0] += 1
        mid = _ID[0]
        self._envoyer(json.dumps({"id": mid, "method": methode, "params": params}))
        while True:
            m = json.loads(self._trame().decode("utf-8", "replace"))
            if m.get("id") == mid:
                if "error" in m:
                    raise ErreurCDP("%s : %s" % (methode, (m["error"] or {}).get("message")))
                return m.get("result") or {}


# --------------------------------------------------------------------------- la telecommande
TOUCHES = {"droite": ("ArrowRight", 39), "gauche": ("ArrowLeft", 37), "haut": ("ArrowUp", 38), "bas": ("ArrowDown", 40),
           "pagebas": ("PageDown", 34), "pagehaut": ("PageUp", 33), "entree": ("Enter", 13), "echap": ("Escape", 27),
           "espace": (" ", 32), "debut": ("Home", 36), "fin": ("End", 35)}


def taille(o):
    m = o.cmd("Page.getLayoutMetrics")
    v = m.get("cssVisualViewport") or m.get("visualViewport") or {}
    return float(v.get("clientWidth") or 1280), float(v.get("clientHeight") or 800)


def ecran(ws_url, qualite=55, largeur_max=900):
    """(jpeg, largeur CSS, hauteur CSS, url, titre). L'image est reduite a largeur_max : assez pour viser juste."""
    with Onglet(ws_url) as o:
        w, h = taille(o)
        echelle = min(1.0, largeur_max / w)
        r = o.cmd("Page.captureScreenshot", format="jpeg", quality=qualite,
                  clip={"x": 0, "y": 0, "width": w, "height": h, "scale": echelle}, captureBeyondViewport=False)
        info = o.cmd("Runtime.evaluate", expression="JSON.stringify([location.href, document.title])", returnByValue=True)
        url, titre = json.loads(((info.get("result") or {}).get("value")) or '["",""]')
        return base64.b64decode(r["data"]), w, h, url, titre


# ---------------------------------------------------------------- v2.14.0 : LA FENETRE de capture (Quang 24/09 16h15-16h22)
# « un bouton pour deplacer la fenetre a un endroit discret […] pas que tout se replace automatiquement, c'est moi qui
# declenche ces boutons, sauf a l'ouverture » + « une securite au moment ou je lance une capture : si la fenetre est trop
# petite, un message […] ou un bouton qui la remet a la bonne taille ».
# MESURE 24/09 (manga-fetch/banc_taille_fenetre.py, OPM ch.301 MangaDex en page par page) : interieur 576 px de large et
# ~774 de haut suffisent, 492 de large ou 674 de haut ECHOUENT (MangaDex n'affiche plus la page). Marge ~20 % (Quang :
# « mets-toi une marge ») -> MINIMUM 700 x 950 interieur. La PLACE par defaut = celle choisie par Quang le 24/09 16h22,
# validee en reel (MangaDex 18/18 en 33 s, webtoon 7/7 en 28 s) alors que la fenetre depasse a ~93 % sous l'ecran.
# S3 (24/09) : memes variables que manga_fetch v0.6.5 -- l'espace prive a sa fenetre de capture, sa place, son port.
FENETRE_CONF = os.path.join(os.environ.get("MANGA_CAPTURE_DONNEES") or os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "manga-fetch"), "fenetre.json")
FENETRE_DEFAUT = {"place": {"left": 2389, "top": 1344, "width": 1052, "height": 1360}, "min_interieur": [700, 950]}
CDP_NAV = "http://127.0.0.1:%d" % int(os.environ.get("MANGA_CAPTURE_PORT") or 9223)


def fenetre_conf():
    try:
        with open(FENETRE_CONF, encoding="utf-8") as f:
            c = json.load(f)
        return {"place": dict(FENETRE_DEFAUT["place"], **(c.get("place") or {})),
                "min_interieur": c.get("min_interieur") or FENETRE_DEFAUT["min_interieur"]}
    except Exception:
        return json.loads(json.dumps(FENETRE_DEFAUT))


def _navigateur():
    import urllib.request
    with urllib.request.urlopen(CDP_NAV + "/json/version", timeout=5) as r:
        return Onglet(json.load(r)["webSocketDebuggerUrl"])


def fenetre(ws_url, action, en_capture=False, **a):
    """etat | ranger | taille | memoriser. Rien ne bouge sans action explicite (sauf l'ouverture, cf. manga_fetch).
    v2.78 (26/09, mesure 25/09 : deplacer = sans effet, agrandir = sans perte) : en_capture = une capture tourne ->
    « ranger » refuse si la place retenue ferait passer l'interieur SOUS la taille minimale ; « fermer » refuse."""
    cible = ws_url.rstrip("/").split("/")[-1]                  # .../devtools/page/<targetId>
    conf = fenetre_conf()
    if action == "fermer" and en_capture:
        return {"error": "une capture est en cours : fermer la fenetre la couperait"}
    if action == "fermer":                                      # v2.14.1 (Quang 16h29) : fermer A DISTANCE -- ce navigateur
        with _navigateur() as n:                               # dedie (port 9223, son profil) et lui seul, jamais l'Edge de Quang
            n.cmd("Browser.close")
        return {"ok": True, "ferme": True}
    with Onglet(ws_url) as o:
        vp = json.loads(o.cmd("Runtime.evaluate", expression="JSON.stringify([innerWidth, innerHeight])",
                              returnByValue=True)["result"]["value"])
    with _navigateur() as n:
        wid = n.cmd("Browser.getWindowForTarget", targetId=cible)["windowId"]
        b = n.cmd("Browser.getWindowBounds", windowId=wid)["bounds"]
        if action in ("ranger", "taille"):
            if b.get("windowState") != "normal":
                n.cmd("Browser.setWindowBounds", windowId=wid, bounds={"windowState": "normal"})
            if action == "ranger":
                nb = dict(conf["place"])
                bw, bh = b["width"] - vp[0], b["height"] - vp[1]   # bords + barres d'Edge
                if en_capture and (nb.get("width", 0) - bw < conf["min_interieur"][0] or nb.get("height", 0) - bh < conf["min_interieur"][1]):
                    return {"error": "une capture est en cours : la place retenue est trop petite pour capturer "
                                     "(%d x %d, il faut %d x %d a l'interieur) -- « Taille sure » d'abord, ou ranger apres"
                                     % (nb.get("width", 0) - bw, nb.get("height", 0) - bh, conf["min_interieur"][0], conf["min_interieur"][1])}
            else:                                               # garde la position, grandit juste ce qu'il faut
                bw, bh = b["width"] - vp[0], b["height"] - vp[1]   # bords + barres d'Edge
                nb = {"left": b["left"], "top": b["top"], "width": max(b["width"], conf["min_interieur"][0] + bw),
                      "height": max(b["height"], conf["min_interieur"][1] + bh)}
            n.cmd("Browser.setWindowBounds", windowId=wid, bounds=nb)
            b = n.cmd("Browser.getWindowBounds", windowId=wid)["bounds"]
        elif action == "memoriser":
            conf["place"] = {k: b[k] for k in ("left", "top", "width", "height")}
            os.makedirs(os.path.dirname(FENETRE_CONF), exist_ok=True)
            with open(FENETRE_CONF, "w", encoding="utf-8") as f:
                json.dump(conf, f, ensure_ascii=False, indent=1)
    if action in ("ranger", "taille"):
        with Onglet(ws_url) as o:
            vp = json.loads(o.cmd("Runtime.evaluate", expression="JSON.stringify([innerWidth, innerHeight])",
                                  returnByValue=True)["result"]["value"])
    mw, mh = conf["min_interieur"]
    return {"ok": True, "bounds": b, "interieur": vp, "min": [mw, mh], "place": conf["place"],
            "assez_grande": vp[0] >= mw and vp[1] >= mh, "reduite": b.get("windowState") == "minimized"}


def piloter(ws_url, action, **a):
    """Une action de l'utilisateur sur l'onglet. x, y = fractions 0..1 de la zone visible."""
    if action.startswith("fenetre_"):                          # v2.14.0 : AVANT bringToFront (qui pourrait la sortir)
        return fenetre(ws_url, action[8:], **a)
    with Onglet(ws_url) as o:
        o.cmd("Page.bringToFront")
        if action in ("clic", "molette"):
            w, h = taille(o)
            x, y = max(0.0, min(1.0, float(a.get("x", 0.5)))) * w, max(0.0, min(1.0, float(a.get("y", 0.5)))) * h
            if action == "clic":
                o.cmd("Input.dispatchMouseEvent", type="mouseMoved", x=x, y=y)
                o.cmd("Input.dispatchMouseEvent", type="mousePressed", x=x, y=y, button="left", clickCount=1)
                o.cmd("Input.dispatchMouseEvent", type="mouseReleased", x=x, y=y, button="left", clickCount=1)
            else:
                o.cmd("Input.dispatchMouseEvent", type="mouseWheel", x=x, y=y, deltaX=0, deltaY=float(a.get("dy", 600)))
        elif action == "touche":
            k = TOUCHES.get(a.get("touche") or "")
            if not k:
                raise ErreurCDP("touche inconnue")
            for t in ("keyDown", "keyUp"):
                o.cmd("Input.dispatchKeyEvent", type=t, key=k[0], code=k[0] if len(k[0]) > 1 else "Space",
                      windowsVirtualKeyCode=k[1], nativeVirtualKeyCode=k[1])
        elif action == "texte":
            o.cmd("Input.insertText", text=str(a.get("texte") or "")[:500])
        elif action == "url":
            u = str(a.get("url") or "").strip()
            if not u.startswith(("http://", "https://")):
                u = "https://" + u
            if not urllib.parse.urlparse(u).hostname:
                raise ErreurCDP("adresse invalide")
            o.cmd("Page.navigate", url=u)
        elif action in ("retour", "avant", "recharger"):
            o.cmd("Runtime.evaluate", expression={"retour": "history.back()", "avant": "history.forward()",
                                                  "recharger": "location.reload()"}[action])
        else:
            raise ErreurCDP("action inconnue : " + str(action))
    return {"ok": True}
