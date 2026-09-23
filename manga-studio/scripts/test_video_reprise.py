"""Banc v2.7.0 (23/09/2026) : un telechargement de video coupe REPREND, et par le chemin direct Wi-Fi.

1. ETag + Last-Modified presents (sans eux, le gestionnaire de telechargement Android ne reprend pas).
2. Coupure simulee : 1er morceau jusqu'a la moitie, puis reprise `Range` + `If-Range: <ETag>` -> 206 ; le fichier
   recolle a le MEME SHA-256 que la video sur le disque.
3. If-Range perime (video refaite) -> 200 et le fichier ENTIER, jamais un melange.
4. Le meme telechargement par https://manga-wifi.crushrank.xyz:8723 (Caddy) : memes octets, debit mesure.
Usage : python test_video_reprise.py [chapitre=claymore/ch_1] [tag=gemini-charon]  (proxy 8190 lance)
"""
import hashlib, os, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CH = sys.argv[1] if len(sys.argv) > 1 else "claymore/ch_1"
TAG = sys.argv[2] if len(sys.argv) > 2 else "gemini-charon"
REL = CH + "/video/" + TAG + ".mp4"
DISQUE = os.path.join(HERE, "..", "sources", *REL.split("/"))
KEY = open(os.path.expanduser(r"~\Documents\ComfyUI\.studio_secret"), encoding="utf-8").read().strip()
OK = KO = 0


def check(cond, nom):
    global OK, KO
    OK, KO = (OK + 1, KO) if cond else (OK, KO + 1)
    print(("  OK  " if cond else "  KO  ") + nom, flush=True)


def get(base, entetes=None, limite=None):
    url = base + "/manga/video_file?p=" + urllib.parse.quote(REL) + "&dl=1&_k=" + urllib.parse.quote(KEY)
    r = urllib.request.urlopen(urllib.request.Request(url, headers=entetes or {}), timeout=120)
    h, lu, t = hashlib.sha256(), 0, time.time()
    while True:
        b = r.read(min(1 << 20, limite - lu) if limite else 1 << 20)
        if not b:
            break
        h.update(b); lu += len(b)
        if limite and lu >= limite:
            break
    return r.status, r.headers, h, lu, time.time() - t


taille = os.path.getsize(DISQUE)
ref = hashlib.sha256(open(DISQUE, "rb").read()).hexdigest()
print("video %s : %d Mo" % (REL, taille // 10**6))
for nom, base in (("local 8190", "http://127.0.0.1:8190"), ("direct Wi-Fi", "https://manga-wifi.crushrank.xyz:8723")):
    print("\n== " + nom)
    moitie = taille // 2
    st, hd, h1, lu1, s1 = get(base, limite=moitie)
    etag, lm = hd.get("ETag"), hd.get("Last-Modified")
    check(st == 200 and etag and lm, "200 + ETag %s + Last-Modified %s" % (etag, lm))
    st, hd, h2, lu2, s2 = get(base, {"Range": "bytes=%d-" % moitie, "If-Range": etag})
    check(st == 206 and hd.get("Content-Range") == "bytes %d-%d/%d" % (moitie, taille - 1, taille), "reprise 206 %s" % hd.get("Content-Range"))
    # recoller : relire le 1er morceau (le hash incremental ne se « concatene » pas)
    tot = hashlib.sha256()
    for plage in ("bytes=0-%d" % (moitie - 1), "bytes=%d-" % moitie):
        url = base + "/manga/video_file?p=" + urllib.parse.quote(REL) + "&dl=1&_k=" + urllib.parse.quote(KEY)
        r = urllib.request.urlopen(urllib.request.Request(url, headers={"Range": plage, "If-Range": etag}), timeout=120)
        while True:
            b = r.read(1 << 20)
            if not b:
                break
            tot.update(b)
    check(tot.hexdigest() == ref, "fichier recolle = SHA-256 du disque")
    st, hd, h3, lu3, s3 = get(base, {"Range": "bytes=%d-" % moitie, "If-Range": '"v0-0"'}, limite=None)
    check(st == 200 and lu3 == taille and h3.hexdigest() == ref, "If-Range perime -> 200 + fichier ENTIER (%d o)" % lu3)
    print("  debit : %.0f Mo/s (%d Mo en %.1f s)" % (lu3 / 1e6 / s3, lu3 // 10**6, s3))
print("\n%d/%d" % (OK, OK + KO))
sys.exit(1 if KO else 0)
