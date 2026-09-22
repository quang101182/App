# -*- coding: utf-8 -*-
"""Instance de TEST du proxy sur 8191 : n'importe QUE le gestionnaire HTTP d'une copie patchee.

Jamais une 2e instance complete : le __main__ du proxy lance le watchdog des pods, les notifications
Telegram, la file musique... ici, rien de tout ca (le module est importe, pas execute).
Usage :
    python proxy_8191.py <copie_patchee.py>
La copie est posee a cote du vrai proxy (C:/Users/quang/Documents/ComfyUI/) le temps du test, parce que
le proxy calcule ses chemins depuis son propre emplacement et importe _studio_db de ce dossier.
Arret : Ctrl+C, ou tuer le PID affiche (jamais le 8190). ⚠ Un process TUE ne passe pas par le finally :
supprimer alors a la main ~/Documents/ComfyUI/_studio_llm_proxy_8191.py (constate le 22/09).
"""
import importlib.util
import os
import shutil
import sys
from http.server import ThreadingHTTPServer

COMFY = os.path.expanduser(r"~\Documents\ComfyUI")
source = os.path.abspath(sys.argv[1])
copie = os.path.join(COMFY, "_studio_llm_proxy_8191.py")
if os.path.normcase(source) != os.path.normcase(copie):
    shutil.copyfile(source, copie)
sys.path.insert(0, COMFY)
spec = importlib.util.spec_from_file_location("proxy_8191", copie)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
print("proxy de TEST -> http://127.0.0.1:8191 (PID %d) -- gestionnaire HTTP seul" % os.getpid(), flush=True)
try:
    ThreadingHTTPServer(("127.0.0.1", 8191), mod.H).serve_forever()
finally:
    try:
        os.remove(copie)
    except OSError:
        pass
