# -*- coding: utf-8 -*-
"""Espace prive de Manga Studio (S1, 24/09/2026) : une 2e instance du serveur, qui ne voit QUE ses propres donnees.

Meme code, meme app : le module du proxy est IMPORTE (jamais execute) et seul son gestionnaire HTTP `H` est servi.
Son __main__ n'est donc jamais joue : ni watchdog des pods, ni notifications Telegram, ni file musique, ni mastering
-- tout cela reste l'affaire de l'instance normale (8190). Verifie le 24/09 : l'import du proxy ne lance aucun fil.

Donnees : MANGA_SOURCES_DIR (S0), par defaut C:/Users/quang/Documents/MangaStudio-donnees/prive -- sur C:, hors du
depot et hors de sources/. Le journal de capture de cette instance est a part lui aussi.
L'app ouverte sur ce port parle a ce port (location.origin) et son stockage local est celui de CETTE origine.

Usage : python espace_prive.py            (port 8192, 127.0.0.1 seulement ; 8191 = banc proxy_8191.py)
        MANGA_PRIVE_PORT=... pour un autre port. Arret : Ctrl+C ou tuer le PID affiche (jamais le 8190).
"""
import importlib.util
import os
import sys
from http.server import ThreadingHTTPServer

VERSION = "1.0.0"
COMFY = os.path.expanduser(r"~\Documents\ComfyUI")
PROXY = os.path.join(COMFY, "_studio_llm_proxy.py")
DONNEES = os.environ.get("MANGA_SOURCES_DIR") or os.path.expanduser(r"~\Documents\MangaStudio-donnees\prive")
PORT = int(os.environ.get("MANGA_PRIVE_PORT", "8192"))

if os.path.normcase(os.path.abspath(DONNEES)).startswith(
        os.path.normcase(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))):
    raise SystemExit("refus : les donnees de l'espace prive ne doivent pas etre dans le depot (%s)" % DONNEES)
os.makedirs(DONNEES, exist_ok=True)
os.environ["MANGA_SOURCES_DIR"] = DONNEES              # AVANT l'import : le proxy en derive tous ses chemins

sys.path.insert(0, COMFY)                               # _studio_db et consorts
spec = importlib.util.spec_from_file_location("proxy_espace_prive", PROXY)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
if os.path.normcase(os.path.normpath(mod.MANGA_SOURCES)) != os.path.normcase(os.path.normpath(DONNEES)):
    raise SystemExit("refus : le proxy ne lit pas MANGA_SOURCES_DIR (%s)" % mod.MANGA_SOURCES)
mod.MF_RUNLOG = os.path.join(os.environ.get("LOCALAPPDATA", ""), "manga-studio", "capture_run_prive.log")

print("espace prive v%s -> http://127.0.0.1:%d/manga/ (PID %d) -- gestionnaire HTTP seul" % (VERSION, PORT, os.getpid()),
      flush=True)
ThreadingHTTPServer.request_queue_size = 128
ThreadingHTTPServer(("127.0.0.1", PORT), mod.H).serve_forever()
