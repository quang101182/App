"""Manga Studio — chemin direct (v2.7.0, 23/09/2026) : cree l'enregistrement DNS du Wi-Fi de la maison.

manga-wifi.crushrank.xyz -> 192.168.1.141 (adresse Wi-Fi du PC), A public NON proxie : resolu partout, joignable
seulement depuis le Wi-Fi de la maison. Meme recette que Telegramme Video (tgv-wifi, 13/09/2026).
Le jeton Cloudflare est LU dans llm-cli/.env (CF_API_TOKEN), jamais ecrit ici. Rejouable : ne cree rien si l'enregistrement
existe deja avec la bonne adresse ; le corrige s'il pointe ailleurs (--corriger).
Usage : python dns_direct.py [--corriger]
"""
import json, os, sys, urllib.request

NOM, ZONE, IP = "manga-wifi.crushrank.xyz", "crushrank.xyz", "192.168.1.141"
ENV = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "llm-cli", ".env"))


def jeton():
    for l in open(ENV, encoding="utf-8"):
        if l.strip().startswith("CF_API_TOKEN"):
            return l.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("CF_API_TOKEN absent de " + ENV)


def cf(methode, chemin, corps=None):
    req = urllib.request.Request("https://api.cloudflare.com/client/v4" + chemin, method=methode,
                                 data=json.dumps(corps).encode() if corps else None,
                                 headers={"Authorization": "Bearer " + jeton(), "Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=30))
    if not r.get("success"):
        raise SystemExit("Cloudflare : %s" % r.get("errors"))
    return r["result"]


zone = cf("GET", "/zones?name=" + ZONE)[0]["id"]
ex = cf("GET", "/zones/%s/dns_records?name=%s" % (zone, NOM))
if ex and ex[0]["content"] == IP and ex[0]["type"] == "A" and not ex[0]["proxied"]:
    print("deja en place : %s -> %s (non proxie)" % (NOM, IP))
elif ex and "--corriger" not in sys.argv:
    raise SystemExit("existe mais differe : %s -> %s (proxied=%s) ; relancer avec --corriger" % (NOM, ex[0]["content"], ex[0]["proxied"]))
elif ex:
    cf("PUT", "/zones/%s/dns_records/%s" % (zone, ex[0]["id"]), {"type": "A", "name": NOM, "content": IP, "proxied": False, "ttl": 300,
                                                                "comment": "Manga Studio chemin direct Wi-Fi (v2.7.0)"})
    print("corrige : %s -> %s" % (NOM, IP))
else:
    cf("POST", "/zones/%s/dns_records" % zone, {"type": "A", "name": NOM, "content": IP, "proxied": False, "ttl": 300,
                                               "comment": "Manga Studio chemin direct Wi-Fi (v2.7.0)"})
    print("cree : %s -> %s (non proxie)" % (NOM, IP))
