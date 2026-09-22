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


def piloter(ws_url, action, **a):
    """Une action de l'utilisateur sur l'onglet. x, y = fractions 0..1 de la zone visible."""
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
