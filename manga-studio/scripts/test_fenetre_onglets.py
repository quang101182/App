# -*- coding: utf-8 -*-
"""Banc manga-fetch 0.8.5 : la fenetre de capture rouvre SES onglets, sans onglet MangaDex d'office (Quang 27/09 21h35).
VRAI Edge, PROFIL JETABLE (dossier temporaire) et un port LIBRE (verifie) : la vraie fenetre de Quang n'est jamais touchee.
A. 1re ouverture : aucun onglet MangaDex. B. deux onglets ouverts, fermeture PROPRE (Browser.close) -> relance : les deux
reviennent, pas de MangaDex. C. fermeture FORCEE (taskkill) -> relance : les deux reviennent quand meme. D. clic alors qu'elle
est deja ouverte : ni fenetre ni onglet en plus. MUTATION : --ancien manga_fetch.py.bak-084 -> ROUGE.
Usage : python test_fenetre_onglets.py [--ancien chemin/manga_fetch.py]"""
import json, os, shutil, subprocess, sys, tempfile, time, urllib.request
import websocket

HERE = os.path.dirname(os.path.abspath(__file__))
MF = sys.argv[sys.argv.index("--ancien") + 1] if "--ancien" in sys.argv else os.path.join(HERE, "..", "manga-fetch", "manga_fetch.py")
PY = os.path.join(os.environ["LOCALAPPDATA"], "manga-fetch", "venv", "Scripts", "python.exe")
def port_libre():                      # 27/09 : 9333 etait PRIS par une autre fenetre Edge -> toujours verifier
    import socket
    k = socket.socket(); k.bind(("127.0.0.1", 0)); p = k.getsockname()[1]; k.close(); return p


PORT = port_libre()
T = tempfile.mkdtemp(prefix="banc_onglets_")
ENV = dict(os.environ, MANGA_CAPTURE_PORT=str(PORT), MANGA_CAPTURE_PROFIL=os.path.join(T, "profil"), MANGA_CAPTURE_DONNEES=os.path.join(T, "donnees"))
os.makedirs(ENV["MANGA_CAPTURE_DONNEES"])
json.dump({"place": {"left": 40, "top": 40, "width": 900, "height": 800}}, open(os.path.join(ENV["MANGA_CAPTURE_DONNEES"], "fenetre.json"), "w"))
OK, KO = [], []
A_, B_ = "https://example.com/?onglet=a", "https://example.org/?onglet=b"


def check(nom, cond, detail=""):
    (OK if cond else KO).append(nom)
    print(("  [OK] " if cond else "  [KO] ") + nom + (" -- " + str(detail)[:170] if detail else ""), flush=True)


def lancer():
    subprocess.run([PY, MF, "launch-edge"], env=ENV, capture_output=True, timeout=60)


def pages(attendre=20):
    for _ in range(attendre * 2):
        try:
            l = json.load(urllib.request.urlopen("http://127.0.0.1:%d/json/list" % PORT, timeout=2))
            p = [t["url"] for t in l if t.get("type") == "page"]
            if p:
                time.sleep(2.5)                     # laisser la restauration finir
                l = json.load(urllib.request.urlopen("http://127.0.0.1:%d/json/list" % PORT, timeout=2))
                return [t["url"] for t in l if t.get("type") == "page"]
        except Exception:
            pass
        time.sleep(0.5)
    return None


def pid_edge():
    r = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_Process -Filter \"Name='msedge.exe'\" | Where-Object { $_.CommandLine -match '%s' -and $_.CommandLine -notmatch '--type=' } | ForEach-Object { $_.ProcessId }" % os.path.basename(T)],
                       capture_output=True, text=True)
    return [int(x) for x in r.stdout.split() if x.strip().isdigit()]


def fermer(propre):
    if propre:
        ws = json.load(urllib.request.urlopen("http://127.0.0.1:%d/json/version" % PORT, timeout=3))["webSocketDebuggerUrl"]
        c = websocket.create_connection(ws, timeout=5, suppress_origin=True); c.send(json.dumps({"id": 1, "method": "Browser.close"}))
        try: c.recv()
        except Exception: pass
    else:
        for p in pid_edge():
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(p)], capture_output=True)
    for _ in range(40):
        if not pid_edge(): break
        time.sleep(0.5)
    time.sleep(1.5)


mdx = lambda l: [u for u in (l or []) if "mangadex" in u]
try:
    lancer(); p0 = pages()
    if not pid_edge():                      # garde : on ne parle JAMAIS a un autre navigateur
        raise SystemExit("ARRET : l'Edge jetable n'a pas demarre (port %d) -- rien touche" % PORT)
    check("A. 1re ouverture : fenetre ouverte, AUCUN onglet MangaDex", p0 is not None and not mdx(p0), p0)
    for u in (A_, B_):
        urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:%d/json/new?%s" % (PORT, urllib.request.quote(u, safe="")), method="PUT"), timeout=5)
    for u in list(p0 or []):                        # ne garder QUE a et b (Quang ferme ce qu'il ne veut pas)
        pass
    l = json.load(urllib.request.urlopen("http://127.0.0.1:%d/json/list" % PORT, timeout=3))
    for t in l:
        if t.get("type") == "page" and "onglet=" not in t["url"]:
            urllib.request.urlopen("http://127.0.0.1:%d/json/close/%s" % (PORT, t["id"]), timeout=3).read()
    time.sleep(6)                                  # Edge ecrit sa session quelques secondes apres un changement
    fermer(True); lancer(); p1 = pages()
    sv = os.path.join(ENV["MANGA_CAPTURE_PROFIL"], "Default", "_sessions_sauvegarde")
    check("B0. sauvegarde des onglets faite AVANT le lancement", os.path.isdir(sv) and len(os.listdir(sv)) >= 1, os.listdir(sv) if os.path.isdir(sv) else None)
    check("B. fermeture propre -> relance : SES deux onglets, pas de MangaDex", p1 is not None and any("onglet=a" in u for u in p1) and any("onglet=b" in u for u in p1) and not mdx(p1), p1)
    time.sleep(6)
    fermer(False); lancer(); p2 = pages()
    check("C. fermeture FORCEE -> relance : ses deux onglets quand meme", p2 is not None and any("onglet=a" in u for u in p2) and any("onglet=b" in u for u in p2) and not mdx(p2), p2)
    n = len(p2 or []); lancer(); time.sleep(3)
    p3 = [t["url"] for t in json.load(urllib.request.urlopen("http://127.0.0.1:%d/json/list" % PORT, timeout=3)) if t.get("type") == "page"]
    check("D. clic alors qu'elle est ouverte : aucun onglet ni fenetre en plus", len(p3) == n and not mdx(p3), (n, p3))
finally:
    try: fermer(False)
    except Exception: pass
    shutil.rmtree(T, ignore_errors=True)
print("\nVERDICT : %d/%d" % (len(OK), len(OK) + len(KO)))
sys.exit(1 if KO else 0)
