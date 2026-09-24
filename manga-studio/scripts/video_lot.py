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
FILE = os.path.join(os.path.normpath(os.environ.get("MANGA_SOURCES_DIR") or os.path.join(HERE, "..", "sources")), "_videos_file")
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
    for essai in range(20):           # v1.99.1 : sous Windows, replace echoue (WinError 5) si le proxy LIT le fichier
        try:                          # a cet instant -- ce programme en mourait (22/09 09h54, demande bloquee)
            os.replace(tmp, f)
            return
        except PermissionError:
            time.sleep(0.25)
    os.replace(tmp, f)


LOCK = os.path.join(FILE, "_runner.lock")


def pid_vivant(pid):
    try:
        out = subprocess.run(["tasklist", "/FI", "PID eq %d" % int(pid), "/NH"], capture_output=True, text=True,
                             creationflags=CREATE, timeout=15).stdout
        return str(int(pid)) in out
    except Exception:
        return False


def prendre_verrou():
    """v1.99.1 : UN SEUL programme de file. Deux demandes a quelques ms d'ecart lancaient deux programmes (le proxy ne
    voyait pas encore le premier) qui traitaient la MEME demande -> WinError 5. Creation exclusive = atomique."""
    for _ in range(2):
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode()); os.close(fd)
            return True
        except FileExistsError:
            try:
                pid = int(open(LOCK).read().strip() or 0)
            except Exception:
                pid = 0
            if pid and pid_vivant(pid):
                return False
            try:                      # verrou d'un programme mort : on le reprend
                os.remove(LOCK)
            except OSError:
                return False
    return False


def nettoyer_orphelines():
    """Seul programme de file vivant : toute demande « en cours » est orpheline (son programme est mort).
    Sa video existe et est plus recente que la demande -> faite, on efface ; sinon -> echec, raison dite."""
    for n in os.listdir(FILE):
        if n.startswith("_") or not n.endswith(".json"):
            continue
        f = os.path.join(FILE, n)
        e = lire(f)
        if not e or e.get("etat") != "en cours" or (e.get("pid") and pid_vivant(e["pid"])):
            continue
        mp4 = os.path.join(FILE, "..", *e["d"].split("/"), "video", e["tag"] + ".mp4")
        if os.path.isfile(mp4) and os.path.getmtime(mp4) >= float(e.get("debut") or e.get("t") or 0):
            for x in (f, os.path.join(FILE, e["id"] + ".log"), f + ".tmp"):
                try:
                    os.remove(x)
                except OSError:
                    pass
        else:
            e.update(etat="echec", err="le programme de fabrication s'est arrete en route", fin=time.time())
            ecrire(f, e)


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
    if not prendre_verrou():
        return                        # un autre programme de file tourne : il prendra aussi cette demande
    try:
        nettoyer_orphelines()
        boucle()
    finally:
        try:
            os.remove(LOCK)
        except OSError:
            pass


def boucle():
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
        # 4 = chapitre avec une alerte de moderation ouverte (video_chapitre 1.98.0) : pas un echec, une ATTENTE
        e.update(etat="attente moderation" if code == 4 else "echec", fin=time.time(), code=code)
        try:
            e["err"] = open(log, encoding="utf-8", errors="replace").read()[-500:]
        except Exception:
            pass
        ecrire(f, e)


if __name__ == "__main__":
    main()
