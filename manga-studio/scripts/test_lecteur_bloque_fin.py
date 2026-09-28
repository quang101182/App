"""Banc S15 cause B (28/09/2026) : lecteur page par page qui CALE avant la fin.

Vecu : galerie de 226 pages -> 213 capturees, capture declaree REUSSIE (code 0, 0 note). Rejoue a la main, la meme zone
avance normalement : le blocage est TRANSITOIRE (image d'une page qui ne vient pas). Or manga-fetch concluait « fin »
apres 5 essais steriles sans lire le compteur « 213 / 226 » affiche par le lecteur.

Ce banc sert un FAUX lecteur local (compteur « N / 30 », fleches, une image par page) dont l'image de la page 25
ne repond JAMAIS au 1er passage (et le lecteur ignore les fleches tant qu'elle charge) ; un rechargement la debloque.
Une VRAIE capture manga-fetch est lancee dessus (onglet ouvert par le banc dans la fenetre de capture principale,
ferme par SON id, dossier de sortie temporaire).

Attendu : 30 pages capturees, code 0. Sabotage : manga_fetch.py 0.8.9 -> 24 pages, code 0 = ROUGE.
Cas 2 (--cas bloque) : l'image ne repond jamais, meme apres rechargement -> capture signalee ECHEC (code 3),
jamais « reussie ».
Cas 3 (--cas doublons, la CAUSE PROUVEE du vecu) : pages 20-26 = copies EXACTES des pages 5-11 (la galerie reelle
repetait 214-224 = 198-208) ; aucune image ne cale. Attendu : 23 pages capturees + 7 doublons, code 0.
0.8.9 : 5 doublons d'affilee = « fin » -> 19 pages, code 0 = ROUGE.
Cas 4 (--cas bandeaux) : les 2 dernieres pages sont des bandes 800x170 (vecu : bande promotionnelle scannee en fin de
volume, 1280x246) -> 28 pages, code 0, AUCUNE fausse alerte (0.9.0 sans le comptage « hors format » : ECHEC = ROUGE).
Usage : python test_lecteur_bloque_fin.py [--fetch chemin/manga_fetch.py] [--cas cale|bloque|doublons|bandeaux]
"""
import argparse, io, json, os, shutil, subprocess, sys, tempfile, threading, time, urllib.request
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import quote

from PIL import Image, ImageDraw

ICI = os.path.dirname(os.path.abspath(__file__))
FETCH_DEFAUT = os.path.join(ICI, "..", "manga-fetch", "manga_fetch.py")
PY = os.path.join(os.environ["LOCALAPPDATA"], "manga-fetch", "venv", "Scripts", "python.exe")
PORT = os.environ.get("BANC_PORT_CDP", "9224")   # fenetre de capture : 9223 principale, 9224 secondaire
CDP = "http://127.0.0.1:" + PORT
TOTAL, CALE = 30, 25

ap = argparse.ArgumentParser()
ap.add_argument("--fetch", default=FETCH_DEFAUT)
ap.add_argument("--cas", default="cale", choices=["cale", "bloque", "doublons", "bandeaux"])
A = ap.parse_args()

ETAT = {"debloque": False}
IMGS = {}


DOUBLONS = {k: k - 15 for k in range(20, 27)} if A.cas == "doublons" else {}   # 20..26 -> 5..11


def image(n: int) -> bytes:
    n = DOUBLONS.get(n, n)
    if n not in IMGS:
        im = Image.new("RGB", (800, 170 if (A.cas == "bandeaux" and n > TOTAL - 2) else 1150), (250, 250, 245))
        d = ImageDraw.Draw(im)
        for k in range(40):                            # contenu distinct par page (> 10 Ko, empreinte unique)
            d.line([(k * 20, 0), ((k * 37 + n * 53) % 800, 1150)], fill=((n * 7) % 255, (k * 11) % 255, 90), width=3)
        d.text((40, 40), "PAGE %d" % n, fill=(0, 0, 0))
        b = io.BytesIO(); im.save(b, "PNG"); IMGS[n] = b.getvalue()
    return IMGS[n]


LECTEUR = """<!doctype html><meta charset=utf-8><title>faux lecteur</title>
<style>body{margin:0;background:#222;color:#eee;font:16px sans-serif;text-align:center}img{height:92vh}</style>
<div class=sn><span id=cur>1</span> / <span>%(T)d</span></div><img id=img>
<script>
let n = +(location.hash.slice(1) || 1), charge = false;
function montre(k) { n = k; charge = true; document.getElementById('cur').textContent = k;
  history.replaceState(null, '', '#' + k);
  const i = document.getElementById('img'); i.onload = () => { charge = false; };
  i.src = '/img/' + k + '.png'; }
document.addEventListener('keydown', e => { if (e.key === 'ArrowRight' && !charge && n < %(T)d) montre(n + 1); });
document.getElementById('img').addEventListener('click', () => { if (!charge && n < %(T)d) montre(n + 1); });
montre(n);
</script>""" % {"T": TOTAL}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        p = self.path.split("?")[0]
        if p == "/lecteur":
            b = LECTEUR.encode("utf-8"); t = "text/html; charset=utf-8"
            if not ETAT.get("vu_lecteur"):
                ETAT["vu_lecteur"] = True
            else:
                ETAT["debloque"] = A.cas == "cale"      # un RECHARGEMENT debloque l'image qui calait (cas « cale »)
        elif p.startswith("/img/"):
            n = int(p[5:].split(".")[0])
            if n == CALE and not ETAT["debloque"] and A.cas not in ("doublons", "bandeaux"):
                time.sleep(60)                          # ne repond pas (noeud d'images lent / perdu)
                return
            b = image(n); t = "image/png"
        else:
            self.send_response(404); self.end_headers(); return
        self.send_response(200); self.send_header("Content-Type", t)
        self.send_header("Cache-Control", "no-store"); self.send_header("Content-Length", str(len(b)))
        self.end_headers(); self.wfile.write(b)


srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
srv.daemon_threads = True
threading.Thread(target=srv.serve_forever, daemon=True).start()
url = "http://127.0.0.1:%d/lecteur#1" % srv.server_port
out = tempfile.mkdtemp(prefix="banc_bloque_")
tab = json.load(urllib.request.urlopen(urllib.request.Request(CDP + "/json/new?" + quote(url, safe=""), method="PUT")))
ok = 0; ko = 0


def verif(cond, msg):
    global ok, ko
    print(("OK  " if cond else "KO  ") + msg)
    if cond: ok += 1
    else: ko += 1


try:
    time.sleep(2)
    env = dict(os.environ, MANGA_CAPTURE_PORT=PORT, PYTHONIOENCODING="utf-8")
    r = subprocess.run([PY, A.fetch, "capture", "--tab", "127.0.0.1:%d/lecteur" % srv.server_port,
                        "--title", "banc lecteur bloque", "--chapter", "1", "--out", out, "--force"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=600)
    print(r.stdout[-1500:])
    if r.stderr.strip():
        print("stderr:", r.stderr[-800:])
    mans = [os.path.join(d, "manifest.json") for d, _, fs in os.walk(out) if "manifest.json" in fs]
    man = json.load(open(mans[0], encoding="utf-8")) if mans else {"pages": [], "notes": []}
    n = len(man["pages"])
    if A.cas == "cale":
        verif(n == TOTAL, "cas cale : %d pages capturées sur %d annoncées" % (n, TOTAL))
        verif(r.returncode == 0, "cas cale : code %d (0 attendu : rien n'est perdu)" % r.returncode)
        verif(not any("ECHEC" in x for x in man.get("notes", [])), "cas cale : aucune note ECHEC")
    elif A.cas == "bandeaux":
        verif(n == TOTAL - 2, "cas bandeaux : %d pages capturées (attendu %d, les 2 bandeaux ignorés)" % (n, TOTAL - 2))
        verif(r.returncode == 0, "cas bandeaux : code %d (0 attendu : aucune fausse alerte)" % r.returncode)
        verif(not any("ECHEC" in x for x in man.get("notes", [])), "cas bandeaux : aucune note ECHEC")
    elif A.cas == "doublons":
        attendu = TOTAL - len(DOUBLONS)
        verif(n == attendu, "cas doublons : %d pages capturées (attendu %d = %d annoncées - %d en double)"
              % (n, attendu, TOTAL, len(DOUBLONS)))
        verif(r.returncode == 0, "cas doublons : code %d (0 attendu : rien de perdu)" % r.returncode)
        verif(not any("ECHEC" in x for x in man.get("notes", [])), "cas doublons : aucune note ECHEC")
    else:
        verif(n == CALE - 1, "cas bloqué : %d pages (les %d avant le blocage)" % (n, CALE - 1))
        echec = [x for x in man.get("notes", []) if "ECHEC" in x]
        verif(r.returncode == 3 and bool(echec), "cas bloqué : capture signalée en échec (code %d, notes %s)"
              % (r.returncode, echec[:1]))
        verif(any(("%d" % TOTAL) in x for x in echec), "cas bloqué : la note cite le total annoncé (%d)" % TOTAL)
finally:
    try:
        urllib.request.urlopen(CDP + "/json/close/" + tab["id"])
    except Exception:
        pass
    srv.shutdown()
    shutil.rmtree(out, ignore_errors=True)

print("\nVERDICT %s : %d/%d" % ("VERT" if ko == 0 else "ROUGE", ok, ok + ko))
sys.exit(0 if ko == 0 else 1)
