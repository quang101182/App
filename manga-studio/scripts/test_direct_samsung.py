"""Banc Samsung REEL v2.7.0 (23/09/2026) : depuis la page servie par le TUNNEL (comme chez Quang), une video se
telecharge par le chemin direct Wi-Fi (manga-wifi.crushrank.xyz:8723), apres l'invite Chrome « reseau local ».

Mesure : version servie, worker installe NEUF (URL versionnee), invite reseau local (touchee « Autoriser »), sonde
directe = vrai, connexion TCP du telephone vers 192.168.1.141:8723 pendant le telechargement, fichier complet
dans /sdcard/Download (taille exacte), debit. Nettoie derriere lui (le fichier telecharge est supprime).
Usage : python test_direct_samsung.py
"""
import json, os, re, subprocess, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import samsung                                           # noqa: E402

TUNNEL = "https://generate-agent-a1a1df54.crushrank.xyz/manga/"
REL = "claymore/ch_1/video/gemini-charon.mp4"
TAILLE = os.path.getsize(os.path.join(HERE, "..", "sources", *REL.split("/")))
OK = KO = 0


def check(cond, nom):
    global OK, KO
    OK, KO = (OK + 1, KO) if cond else (OK, KO + 1)
    print(("  OK  " if cond else "  KO  ") + nom, flush=True)


def adb(*a):
    return subprocess.run([samsung.ADB, "-s", "RFCT32ATWGJ", *a], capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=60).stdout


adb("shell", "input keyevent KEYCODE_WAKEUP")
adb("forward", "tcp:%d" % samsung.CDP_PORT, "localabstract:chrome_devtools_remote")
avant = set(adb("shell", "ls /sdcard/Download").split())
url = TUNNEL + "#k=" + urllib.parse.quote(samsung.secret())
onglets = json.load(urllib.request.urlopen("http://127.0.0.1:%d/json/list" % samsung.CDP_PORT, timeout=10))
if not any("crushrank.xyz/manga" in t.get("url", "") and t.get("type") == "page" for t in onglets):
    adb("shell", "am", "start", "-n", "com.android.chrome/com.google.android.apps.chrome.Main", "-a", "android.intent.action.VIEW", "-d", "'" + url + "'")   # Chrome Android refuse /json/new
time.sleep(8)
samsung.Phone.calibrate = lambda self, tries=5: None      # aucun tap dans la page ici (plein ecran WebAPK : y_off < 0)
p = samsung.Phone(url_contains="crushrank.xyz/manga", open_if_missing=False)
v = p.js("VERSION")
check(v == samsung.version_source() == "2.7.0", "version servie par le tunnel : %s" % v)
time.sleep(4)
sw = p.js("navigator.serviceWorker.getRegistrations().then(rs => rs.map(r => (r.active || r.waiting || r.installing || {}).scriptURL))", await_promise=True)
check(any(s and s.endswith("/manga/sw.js?v=2.7.0") for s in sw or []), "worker installe neuf : %s" % sw)

# L'invite « reseau local » (interface Chrome native) : on la cherche dans l'arbre UI et on touche Autoriser.
invite = None
for _ in range(10):
    xml = p.ui_dump()
    if re.search(r"r[ée]seau local|local network|appareils", xml, re.I):
        invite = xml
        break
    p.js("directSonder()", await_promise=True)
    time.sleep(1.5)
if invite:
    txt = re.findall(r'text="([^"]*(?:r[ée]seau|network|appareils)[^"]*)"', invite, re.I)
    print("  invite vue : %s" % txt[:2])
    p.ui_tap("Autoriser") if "Autoriser" in invite else p.ui_tap("Allow")
    time.sleep(1.5)
etat = p.js("navigator.permissions.query({name:'local-network-access'}).then(s => s.state).catch(e => 'inconnu:' + e.message)", await_promise=True)
print("  permission reseau local : %s (invite %s)" % (etat, "vue et acceptee" if invite else "non vue"))
ok = p.js("directSonder()", await_promise=True)
check(ok is True, "sonde du chemin direct depuis le telephone = %s" % ok)

# Telechargement par le VRAI code de l'app (baseTelechargement + lien), sur la video Claymore ch.1.
p.js("vidTelecharger({d: 'claymore/ch_1', videos: [{fichier: %s, v: 'banc'}]})" % json.dumps(REL), await_promise=True)
t0, nouveau, vu_direct, taille, precedent = time.time(), None, False, 0, (0, time.time())
while time.time() - t0 < 600:
    time.sleep(3)
    if not vu_direct and "192.168.1.141:8723" in subprocess.run(["netstat", "-an"], capture_output=True, text=True).stdout.replace("  ", " "):
        vu_direct = any("192.168.1.141:8723" in l and "192.168.1.37" in l for l in subprocess.run(["netstat", "-an"], capture_output=True, text=True).stdout.splitlines())
    xml = p.ui_dump()
    if re.search(r'text="T[ée]l[ée]charger"', xml):              # Chrome demande parfois de confirmer
        p.ui_tap("Télécharger")
    fichiers = set(adb("shell", "ls /sdcard/Download").split()) - avant
    fins = [f for f in fichiers if f.endswith(".mp4")]
    if fins:
        nouveau = fins[0]
        taille = int((adb("shell", "stat -c %s '/sdcard/Download/" + nouveau + "'").strip() or "0"))
        if taille >= TAILLE:
            break
duree = time.time() - t0
log = p.js("LOG.map(x => x.msg).filter(t => t.includes('⬇') || t.includes('chemin direct')).slice(-3)")
print("  journal de l'app : %s" % log)
check(any("Wi-Fi" in (l or "") for l in log or []), "le journal dit « par le Wi-Fi »")
check(vu_direct, "connexion TCP telephone 192.168.1.37 -> PC 192.168.1.141:8723 vue pendant le telechargement")
check(nouveau and taille == TAILLE, "fichier complet sur le telephone : %s (%d / %d o)" % (nouveau, taille, TAILLE))
print("  debit telephone : %.1f Mo/s (%d Mo en %.0f s, confirmation comprise)" % (taille / 1e6 / duree, taille // 10**6, duree))
if nouveau:
    adb("shell", "rm '/sdcard/Download/" + nouveau + "'")          # c'est MON fichier de test : nettoye
p.screenshot("direct_samsung_fin")
print("\n%d/%d" % (OK, OK + KO))
sys.exit(1 if KO else 0)
