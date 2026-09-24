# -*- coding: utf-8 -*-
"""Espace prive de Manga Studio (S1, 24/09/2026) : une 2e instance du serveur, qui ne voit QUE ses propres donnees.

Meme code, meme app : le module du proxy est IMPORTE (jamais execute) et seul son gestionnaire HTTP `H` est servi.
Son __main__ n'est donc jamais joue : ni watchdog des pods, ni notifications Telegram, ni file musique, ni mastering
-- tout cela reste l'affaire de l'instance normale (8190). Verifie le 24/09 : l'import du proxy ne lance aucun fil.

Donnees : MANGA_SOURCES_DIR (S0), par defaut C:/Users/quang/Documents/MangaStudio-donnees/prive -- sur C:, hors du
depot et hors de sources/. Le journal de capture de cette instance est a part lui aussi. v1.1.0 (S2) : sa base (Planche, Projet, Personnages)
et sa galerie (output) sont a part aussi ; /manga/espace repond « prive ». v1.2.0 (S3) : sa fenetre de capture (CDP 9224,
profil Edge, journaux et place a part).
L'app ouverte sur ce port parle a ce port (location.origin) et son stockage local est celui de CETTE origine.

Usage : python espace_prive.py            (port 8192, 127.0.0.1 seulement ; 8191 = banc proxy_8191.py)
        MANGA_PRIVE_PORT=... pour un autre port. Arret : Ctrl+C ou tuer le PID affiche (jamais le 8190).
"""
import importlib.util
import json
import os
import sys
from http.server import ThreadingHTTPServer

VERSION = "1.6.0"
COMFY = os.path.expanduser(r"~\Documents\ComfyUI")
PROXY = os.path.join(COMFY, "_studio_llm_proxy.py")
DONNEES = os.environ.get("MANGA_SOURCES_DIR") or os.path.expanduser(r"~\Documents\MangaStudio-donnees\prive")
PORT = int(os.environ.get("MANGA_PRIVE_PORT", "8192"))

if os.path.normcase(os.path.abspath(DONNEES)).startswith(
        os.path.normcase(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))):
    raise SystemExit("refus : les donnees de l'espace prive ne doivent pas etre dans le depot (%s)" % DONNEES)
os.makedirs(DONNEES, exist_ok=True)
os.environ["MANGA_SOURCES_DIR"] = DONNEES              # AVANT l'import : le proxy en derive tous ses chemins
os.environ["MANGA_ESPACE"] = "prive"                   # S2 : /manga/espace (l'app sait ou elle est)
os.environ["STUDIO_DB_PATH"] = os.path.join(DONNEES, "_studio_content.db")   # S2 : Planche/Projet/Personnages a part
# S2 : MEME regle d'acces que le proxy 8190 (cle exigee de TOUS, loopback compris) : a S4 un tunnel arrivera en
# local ; sans cle, le loopback serait ouvert a tout le tunnel. La cle est lue, jamais affichee.
os.environ["STUDIO_SECRET"] = open(os.path.join(COMFY, ".studio_secret"), encoding="utf-8").read().strip()
if not os.environ["STUDIO_SECRET"]:
    raise SystemExit("refus : cle vide (.studio_secret)")

# S3 : SA fenetre de capture (manga_fetch >= 0.6.5 et cdp_mini lisent ces variables ; heritees par les scripts lances).
# Profil Edge, journaux et place a part, sur C: : l'historique des sites de l'espace prive ne va jamais dans le
# profil de capture normal, et deux captures (une par espace) ne se marchent plus dessus.
LA = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
os.environ["MANGA_CAPTURE_PORT"] = os.environ.get("MANGA_CAPTURE_PORT") or "9224"
os.environ["MANGA_CAPTURE_DONNEES"] = os.path.join(LA, "manga-fetch-2")
os.environ["MANGA_CAPTURE_PROFIL"] = os.path.join(LA, "manga-fetch-edge-2")
# S5 (v1.6.0) : vue croisee -- l'autre instance (activite) et ses declarations GPU (jauge VRAM commune)
os.environ["MANGA_AUTRE_PORT"] = "8190"
os.environ["MANGA_GPU_AUTRE"] = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sources", "_gpu")
os.environ["MANGA_SITES_FILE"] = os.path.join(DONNEES, "_sites.json")   # v1.4.0 : sa liste de sites valides, hors depot
os.environ["MANGA_CAPTURE_SANS_SYNCHRO"] = "1"         # v1.3.0 : jamais de compte Microsoft ni de synchro (manga_fetch >= 0.6.6)
if os.environ["MANGA_CAPTURE_PORT"] == "9223":
    raise SystemExit("refus : 9223 est la fenetre de capture de l'espace normal")
os.makedirs(os.environ["MANGA_CAPTURE_DONNEES"], exist_ok=True)

sys.path.insert(0, COMFY)                               # _studio_db et consorts
spec = importlib.util.spec_from_file_location("proxy_espace_prive", PROXY)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
if os.path.normcase(os.path.normpath(mod.MANGA_SOURCES)) != os.path.normcase(os.path.normpath(DONNEES)):
    raise SystemExit("refus : le proxy ne lit pas MANGA_SOURCES_DIR (%s)" % mod.MANGA_SOURCES)
mod.MANGA_OUT = os.path.join(DONNEES, "_output")       # S2 : Galerie / Ingestion a part (lu a chaque requete)
os.makedirs(mod.MANGA_OUT, exist_ok=True)
print("base :", mod.studiodb.init_db(), flush=True)
if os.path.normcase(mod.studiodb.DB_PATH) != os.path.normcase(os.environ["STUDIO_DB_PATH"]):
    raise SystemExit("refus : la base n'est pas celle de l'espace prive (%s)" % mod.studiodb.DB_PATH)
if mod.STUDIO_SECRET != os.environ["STUDIO_SECRET"]:
    raise SystemExit("refus : le proxy n'a pas pris la cle")
mod.MF_RUNLOG = os.path.join(os.environ.get("LOCALAPPDATA", ""), "manga-studio", "capture_run_prive.log")
mod.MF_CDP = "http://127.0.0.1:%s" % os.environ["MANGA_CAPTURE_PORT"]          # S3
mod.MF_EVENTS = os.path.join(os.environ["MANGA_CAPTURE_DONNEES"], "events.log")   # S3 : ecrit par manga_fetch (DATA_DIR)

# S4 (v1.5.0) : acces TELEPHONE par une adresse derriere Cloudflare Access. Une requete arrivee par elle porte le jeton
# signe par Cloudflare (Cf-Access-Jwt-Assertion) : s'il est VALIDE (signature, audience, emetteur, expiration) et que
# l'e-mail est celui de Quang, la cle n'est pas exigee -- rien a saisir sur le telephone (regle apps perso).
# Reglage HORS DEPOT : <donnees>/_acces.json {"equipe": "<x>.cloudflareaccess.com", "aud": "...", "email": "...",
# "principale_url": "https://.../manga/"}. Sans ce fichier : inactif (seule la cle compte, comme sur 8190).
try:
    ACCES = json.load(open(os.path.join(DONNEES, "_acces.json"), encoding="utf-8"))
except (OSError, ValueError):
    ACCES = None
if ACCES and ACCES.get("principale_url"):
    os.environ["MANGA_AUTRE_URL"] = ACCES["principale_url"]      # l'appui long, cote telephone, ramene a la principale
_JWKS = {}


def jeton_access_valide(jeton):
    if not (ACCES and jeton):
        return False
    try:
        import jwt
        if "c" not in _JWKS:
            _JWKS["c"] = jwt.PyJWKClient("https://%s/cdn-cgi/access/certs" % ACCES["equipe"], cache_keys=True)
        cle = _JWKS["c"].get_signing_key_from_jwt(jeton).key
        p = jwt.decode(jeton, cle, algorithms=["RS256"], audience=ACCES["aud"], issuer="https://" + ACCES["equipe"])
        return (p.get("email") or "").lower() == ACCES["email"].lower()
    except Exception:
        return False


class H(mod.H):
    def _authorized(self):
        return mod.H._authorized(self) or jeton_access_valide(self.headers.get("Cf-Access-Jwt-Assertion") or "")


print("espace prive v%s -> http://127.0.0.1:%d/manga/ (PID %d) -- gestionnaire HTTP seul" % (VERSION, PORT, os.getpid()),
      flush=True)
ThreadingHTTPServer.request_queue_size = 128
ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
