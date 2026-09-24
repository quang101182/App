# -*- coding: utf-8 -*-
"""Un script qui travaille sur la carte graphique DECLARE ce qu'il y occupe (Manga Studio v2.13.0, 24/09/2026). v1.0.0

Pourquoi : sous Windows (pilote en mode WDDM), ni nvidia-smi (« [N/A] ») ni les compteurs « GPU Process Memory »
(un processus CUDA de 1,5 Go y est INVISIBLE, mesure du 24/09) ne disent qui prend quoi. Generate Studio interroge donc
chaque moteur ; nos scripts de courte duree n'ont pas de serveur a interroger -> ils ecrivent un battement.

    import declaration_gpu; declaration_gpu.declarer("voix")      # au debut du script, une ligne

Un fil de fond ecrit toutes les 3 s sources/_gpu/<pid>.json = {nom, mo, pid, t} ; mo = torch.cuda.memory_reserved()
(ce que PyTorch a pris a la carte). Il n'initialise JAMAIS CUDA lui-meme (un script sans carte reste sans carte) et
ne fait jamais planter son hote. Le fichier disparait a la sortie ; un fichier orphelin (processus tue) est ignore
par le lecteur (vram_parts.py) des qu'il a plus de 15 s.
"""
import atexit, json, os, sys, threading, time

VERSION = "1.0.0"
DIR = os.path.join(os.path.normpath(os.environ.get("MANGA_SOURCES_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sources")), "_gpu")
PERIODE = 3.0


def _mo():
    t = sys.modules.get("torch")                      # seulement si le script a DEJA importe torch
    try:
        if t is not None and t.cuda.is_initialized():
            return int(t.cuda.memory_reserved() // (1024 * 1024))
    except Exception:
        pass
    return 0


def declarer(nom):
    f = os.path.join(DIR, "%d.json" % os.getpid())

    def ecrire():
        try:
            os.makedirs(DIR, exist_ok=True)
            with open(f + ".tmp", "w", encoding="utf-8") as h:
                json.dump({"nom": nom, "mo": _mo(), "pid": os.getpid(), "t": time.time(), "v": VERSION}, h)
            os.replace(f + ".tmp", f)
        except Exception:
            pass

    def boucle():
        while True:
            ecrire()
            time.sleep(PERIODE)

    def effacer():
        try:
            os.remove(f)
        except OSError:
            pass

    atexit.register(effacer)
    threading.Thread(target=boucle, daemon=True, name="declaration_gpu").start()
