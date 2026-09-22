# -*- coding: utf-8 -*-
"""File des videos a fabriquer (Manga Studio v1.93.0, 22/09/2026).

Une demande = UN fichier sources/_videos_file/<id>.json {id, d, tag, reglages, etat, t, ...} depose par le proxy.
Ce programme les traite une par une (la carte graphique encode une video a la fois), du plus ancien au plus recent,
et reste en vie tant qu'il en reste « en attente ». Un fichier par demande : le proxy n'ecrit QUE des demandes neuves
(ou supprime une demande encore en attente), ce programme n'ecrit que l'etat des siennes -> aucune ecriture croisee.
Survit a une relance du proxy (processus independant, PID dans _runner.json).
"""
import json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
FILE = os.path.normpath(os.path.join(HERE, "..", "sources", "_videos_file"))
SCRIPT = os.path.join(HERE, "video_chapitre.py")
CREATE = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def lire(f):
    try:
        with open(f, encoding="utf-8") as h:
            return json.load(h)
    except Exception:
        return None


def ecrire(f, e):
    tmp = f + ".tmp"
    with open(tmp, "w", encoding="utf-8") as h:
        json.dump(e, h, ensure_ascii=False)
    os.replace(tmp, f)


def en_attente():
    out = []
    for n in os.listdir(FILE):
        if n.startswith("_") or not n.endswith(".json"):
            continue
        e = lire(os.path.join(FILE, n))
        if e and e.get("etat") == "attente":
            out.append((e.get("t") or 0, n, e))
    return sorted(out)


def main():
    os.makedirs(FILE, exist_ok=True)
    while True:
        ecrire(os.path.join(FILE, "_runner.json"), {"pid": os.getpid(), "t": time.time()})
        traiter()
        try:
            os.remove(os.path.join(FILE, "_runner.json"))
        except OSError:
            pass
        if not en_attente():          # une demande deposee pendant qu'on s'arretait ? on reprend, sinon fin
            return


def traiter():
    while True:
        attente = en_attente()
        if not attente:
            return
        _, n, e = attente[0]
        f = os.path.join(FILE, n)
        e.update(etat="en cours", debut=time.time())
        ecrire(f, e)
        log = os.path.join(FILE, e["id"] + ".log")
        with open(log, "w", encoding="utf-8") as lg:
            p = subprocess.Popen([sys.executable, SCRIPT, e["d"], e["tag"], "--reglages", json.dumps(e.get("reglages") or {})],
                                 stdout=lg, stderr=lg, cwd=HERE, creationflags=CREATE)
            e["pid"] = p.pid
            ecrire(f, e)
            code = p.wait()
        if code == 0:                                          # reussie : la video et son .json font foi, la demande s'efface
            for x in (f, log):
                try:
                    os.remove(x)
                except OSError:
                    pass
            continue
        e = lire(f) or e
        e.update(etat="echec", fin=time.time(), code=code)
        try:
            e["err"] = open(log, encoding="utf-8", errors="replace").read()[-500:]
        except Exception:
            pass
        ecrire(f, e)


if __name__ == "__main__":
    main()
