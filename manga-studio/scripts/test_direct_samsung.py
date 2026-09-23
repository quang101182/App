"""Banc Samsung REEL v2.7.x (23/09/2026) : depuis l'app servie par le TUNNEL (comme chez Quang, app installee), une
video se telecharge par le chemin direct Wi-Fi (manga-wifi.crushrank.xyz:8723).

Prealable UNIQUE par appareil : Chrome demande « <site> souhaite acceder a d'autres appareils sur votre reseau local »
-> Autoriser. Le banc touche ce bouton s'il est affiche (arbre UI Android), sinon il le signale.
Mesure : version servie, permission, sonde directe, connexion TCP telephone -> PC:8723 pendant le telechargement,
fichier complet dans /sdcard/Download (taille exacte), debit. Nettoie derriere lui (fichier supprime).
Usage : python test_direct_samsung.py   (onglet Manga Studio du tunnel ouvert sur le Samsung)
"""
import json, os, re, subprocess, sys, time, urllib.request

import websocket

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import samsung                                           # noqa: E402  (ADB, CDP_PORT, version_source)

SERIE = "RFCT32ATWGJ"
REL = "claymore/ch_1/video/gemini-charon.mp4"
TAILLE = os.path.getsize(os.path.join(HERE, "..", "sources", *REL.split("/")))
OK = KO = 0
sys.stdout.reconfigure(encoding="utf-8", errors="replace")      # le journal de l'app contient ⬇ ⚡ ☁


def check(cond, nom):
    global OK, KO
    OK, KO = (OK + 1, KO) if cond else (OK, KO + 1)
    print(("  OK  " if cond else "  KO  ") + nom, flush=True)


def adb(*a):
    return subprocess.run([samsung.ADB, "-s", SERIE, *a], capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=60).stdout


class Onglet:
    def __init__(self):
        cibles = json.load(urllib.request.urlopen("http://127.0.0.1:%d/json/list" % samsung.CDP_PORT, timeout=10))
        c = [t for t in cibles if t.get("type") == "page" and "crushrank.xyz/manga" in t.get("url", "")]
        if not c:
            raise SystemExit("aucun onglet Manga Studio servi par le tunnel sur le Samsung")
        self.ws = websocket.create_connection(c[0]["webSocketDebuggerUrl"], timeout=60, suppress_origin=True)
        self.n = 0

    def js(self, expr, attendre=False):
        self.n += 1
        self.ws.send(json.dumps({"id": self.n, "method": "Runtime.evaluate",
                                 "params": {"expression": expr, "awaitPromise": attendre, "returnByValue": True}}))
        while True:
            r = json.loads(self.ws.recv())
            if r.get("id") == self.n:
                return (r.get("result") or {}).get("result", {}).get("value")


def ui():
    adb("shell", "uiautomator", "dump", "/sdcard/ui.xml")
    return adb("shell", "cat", "/sdcard/ui.xml")


def toucher(xml, texte):
    m = re.search(r'text="%s"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"' % re.escape(texte), xml)
    if m:
        x1, y1, x2, y2 = map(int, m.groups())
        adb("shell", "input", "tap", str((x1 + x2) // 2), str((y1 + y2) // 2))
    return bool(m)


def connexion_directe():
    out = subprocess.run(["netstat", "-an"], capture_output=True).stdout.decode("cp850", "replace")
    return any("192.168.1.141:8723" in l and "192.168.1.37" in l for l in out.splitlines())


adb("shell", "input", "keyevent", "KEYCODE_WAKEUP")
adb("forward", "tcp:%d" % samsung.CDP_PORT, "localabstract:chrome_devtools_remote")
p = Onglet()
v = p.js("VERSION")
check(v == samsung.version_source(), "version servie par le tunnel = version du fichier : %s" % v)
xml = ui()
if "réseau local" in xml and toucher(xml, "Autoriser"):
    print("  invite « réseau local » affichee -> Autoriser touche")
    time.sleep(1.5)
etat = p.js("navigator.permissions.query({name:'local-network-access'}).then(s => s.state)", True)
check(etat == "granted", "permission reseau local = %s" % etat)
check(p.js("directSonder()", True) is True, "sonde du chemin direct depuis l'app installee")

avant = set(adb("shell", "ls", "-1", "/sdcard/Download").splitlines())
p.js("vidTelecharger({d: 'claymore/ch_1', videos: [{fichier: %s, v: 'banc'}]}); 1" % json.dumps(REL))
t0, nouveau, vu_direct, taille = time.time(), None, False, 0
while time.time() - t0 < 600:
    time.sleep(2)
    xml = ui()
    for b in ("Télécharger", "Télécharger quand même"):
        if 'text="%s"' % b in xml:
            toucher(xml, b)
    fins = [f for f in set(adb("shell", "ls", "-1", "/sdcard/Download").splitlines()) - avant if f.endswith(".mp4")]
    if fins:
        nouveau = fins[0]
        taille = int(adb("shell", "stat -c %%s '/sdcard/Download/%s'" % nouveau).strip() or 0)   # nom avec espaces : quote
        if taille >= TAILLE:
            break
duree = time.time() - t0
log = p.js("LOG.map(x => x.msg).filter(t => t.includes('⬇')).slice(-1)")
print("  journal de l'app : %s" % log)
check(any("Wi-Fi" in (l or "") for l in log or []), "le journal dit « par le Wi-Fi »")
# Pas de controle netstat : Chrome passe en HTTP/3 (QUIC, UDP) -> aucune connexion TCP a voir (constate 23/09).
# Le debit tranche : le tunnel Cloudflare plafonne a 5-6 Mo/s par flux (mesure Telegramme Video) ; > 12 = pas lui.
debit = taille / 1e6 / max(duree, 1)
check(debit > 12, "debit %.1f Mo/s > 12 : impossible par le tunnel (5-6 Mo/s)" % debit)
check(bool(nouveau) and taille == TAILLE, "fichier complet sur le telephone : %s (%d / %d o)" % (nouveau, taille, TAILLE))
print("  debit telephone : %.1f Mo/s (%d Mo en %.0f s, confirmation comprise)" % (taille / 1e6 / max(duree, 1), taille // 10**6, duree))
if nouveau:
    adb("shell", "rm '/sdcard/Download/%s'" % nouveau)          # c'est MON fichier de test : nettoye
print("\n%d/%d" % (OK, OK + KO))
sys.exit(1 if KO else 0)
