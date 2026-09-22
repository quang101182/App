# -*- coding: utf-8 -*-
"""SUIVI DE SERIES : la nuit, tout ce qui a ete capture est narre (Manga Studio v1.98.0, 22/09/2026, etape 9).

Decision Quang (22/09 09h00) : SANS plafond de cout. Pour chaque serie suivie (sources/<serie>/suivi.json, actif) :
  1. chaque chapitre SANS narration avec voix est narre (Kimi K3, voix de la serie), un par un, dans l'ordre ;
  2. karaoke cale sur chaque narration faite cette nuit (option, ~0,003 $) ;
  3. « Precedemment... » (ouverture) fabrique ou refait la ou il manque / est perime (option, ~0,013 $) ;
  4. video demandee a la file du proxy (option, 0 $), avec les reglages gardes dans suivi.json.
Jamais deux passages a la fois (verrou = etat.json + PID vivant). Un chapitre dont une narration tourne deja
(lancee a la main : progress.json frais) est laisse tranquille. 2 essais max par chapitre et par passage.
Etat : sources/_suivi/etat.json ; journal : sources/_suivi/journal.jsonl (tout, horodate).
Lance par la tache planifiee « MangaStudioSuiviNuit » (01:30) ou par le bouton « Lancer maintenant » (proxy).

Usage : python suivi_nuit.py [--serie slug] [--dry]      (--dry : dit ce qu'il ferait, ne lance rien)
"""
import argparse, json, os, subprocess, sys, time, urllib.request
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import precedemment as prec                                # chapitres_precedents(), narration_retenue(), chap_key()

VERSION = "1.98.0"
SRC = os.path.normpath(os.path.join(HERE, "..", "sources"))
DIR = os.path.join(SRC, "_suivi")
ETAT, JOURNAL = os.path.join(DIR, "etat.json"), os.path.join(DIR, "journal.jsonl")
PY = sys.executable.replace("pythonw.exe", "python.exe")
CREATE = getattr(subprocess, "CREATE_NO_WINDOW", 0)
PROXY = "http://127.0.0.1:8190"


def journal(ev, **kw):
    os.makedirs(DIR, exist_ok=True)
    with open(JOURNAL, "a", encoding="utf-8") as f:
        f.write(json.dumps(dict(t=datetime.now().isoformat(timespec="seconds"), ev=ev, **kw), ensure_ascii=False) + "\n")


def pid_vivant(pid):
    if not pid:
        return False
    try:
        out = subprocess.run(["tasklist", "/FI", "PID eq %d" % int(pid), "/NH"], capture_output=True, text=True,
                             creationflags=CREATE, timeout=15).stdout
        return str(int(pid)) in out
    except Exception:
        return False


def lire_etat():
    try:
        return json.load(open(ETAT, encoding="utf-8"))
    except Exception:
        return {}


def ecrire_etat(e):
    os.makedirs(DIR, exist_ok=True)
    tmp = ETAT + ".tmp"
    json.dump(e, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.replace(tmp, ETAT)


def series_suivies(seule=None):
    out = []
    for s in sorted(os.listdir(SRC)):
        f = os.path.join(SRC, s, "suivi.json")
        if s.startswith("_") or (seule and s != seule) or not os.path.isfile(f):
            continue
        try:
            cfg = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        if cfg.get("actif"):
            out.append((s, cfg))
    return out


def a_une_voix(cd):
    nd = os.path.join(cd, "narration")
    for tag in (os.listdir(nd) if os.path.isdir(nd) else []):
        f = os.path.join(nd, tag, "narration.json")
        try:
            if any(p.get("audio") for p in json.load(open(f, encoding="utf-8")).get("pages") or []):
                return True
        except Exception:
            pass
    return False


def narration_en_cours(cd):
    nd = os.path.join(cd, "narration")
    for tag in (os.listdir(nd) if os.path.isdir(nd) else []):
        pr = os.path.join(nd, tag, "progress.json")
        if os.path.isfile(pr) and not os.path.isfile(os.path.join(nd, tag, "narration.json")) \
                and time.time() - os.path.getmtime(pr) < 180:
            return tag
    return None


def chapitres(serie):
    sd, out = os.path.join(SRC, serie), []
    for ch in os.listdir(sd):
        cd = os.path.join(sd, ch)
        if ch.startswith("ch_") and os.path.isfile(os.path.join(cd, "manifest.json")):
            try:
                man = json.load(open(os.path.join(cd, "manifest.json"), encoding="utf-8"))
            except Exception:
                man = {}
            out.append({"d": serie + "/" + ch, "cd": cd, "num": str(man.get("chapter") or ch[3:]),
                        "pages": len(man.get("pages") or [])})
    return sorted(out, key=lambda x: prec.chap_key(x["num"]))


def a_narrer(serie):
    """La file : chapitres sans narration avec voix, sans narration en cours."""
    return [c for c in chapitres(serie) if not a_une_voix(c["cd"]) and not narration_en_cours(c["cd"])]


def ouverture_a_faire(c):
    """Le « Precedemment... » de ce chapitre manque ou est perime (meme regle que le proxy)."""
    pv = prec.chapitres_precedents(os.path.dirname(c["cd"]), c["num"])
    utiles = [x for x in pv if x["narr"]][-3:]
    if not utiles:
        return False
    f = os.path.join(c["cd"], "precedemment", "ouverture.json")
    if not os.path.isfile(f):
        return True
    try:
        src = {x.get("ch"): (x.get("tag"), x.get("created_at")) for x in json.load(open(f, encoding="utf-8")).get("sources") or []}
    except Exception:
        return True
    return any(src.get(x["ch"]) != (x["narr"][2], x["narr"][1]) for x in utiles)


def lancer(cmd, log, etat, etape):
    etat["en_cours"] = dict(etat.get("en_cours") or {}, etape=etape, depuis=time.time())
    ecrire_etat(etat)
    with open(log, "w", encoding="utf-8") as lg:
        p = subprocess.Popen(cmd, stdout=lg, stderr=lg, cwd=HERE, creationflags=CREATE,
                             env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        etat["en_cours"]["pid"] = p.pid; ecrire_etat(etat)
        return p.wait()


def demander_video(d, tag, reglages):
    try:
        k = open(os.path.join(os.path.expanduser("~"), "Documents", "ComfyUI", ".studio_secret"), encoding="utf-8").read().strip()
        req = urllib.request.Request(PROXY + "/manga/video", data=json.dumps({"entrees": [{"d": d, "tag": tag}], "reglages": reglages}).encode(),
                                     headers={"Authorization": "Bearer " + k, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except Exception as e:
        return {"error": str(e)[:200]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--serie", default="")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--declencheur", default="manuel")
    a = ap.parse_args()
    old = lire_etat()
    if not a.dry and old.get("etat") == "en cours" and pid_vivant(old.get("pid")):
        journal("refus", raison="un passage tourne deja", pid=old.get("pid"))
        print("un passage tourne deja (PID %s)" % old.get("pid"))
        return 2
    suivies = series_suivies(a.serie or None)
    plan = [(s, cfg, a_narrer(s)) for s, cfg in suivies]
    if a.dry:
        for s, cfg, file in plan:
            print("%s : %d a narrer %s (voix %s)" % (s, len(file), [c["num"] for c in file], cfg.get("voix")))
        return 0
    if not any(f for _s, _c, f in plan):
        # une nuit sans rien a narrer n'efface pas l'etat du dernier VRAI passage (ce que l'app affiche)
        journal("rien", declencheur=a.declencheur, series=[s for s, _c, _f in plan])
        return 0
    etat = {"version": VERSION, "etat": "en cours", "pid": os.getpid(), "debut": time.time(), "declencheur": a.declencheur,
            "fait": [], "erreurs": [], "en_cours": None,
            "file": [c["d"] for _s, _c, f in plan for c in f]}
    ecrire_etat(etat)
    journal("debut", declencheur=a.declencheur, series=[s for s, _c, _f in plan], file=etat["file"])
    try:
        for s, cfg, file in plan:
            voix = cfg.get("voix") or "Charon"
            moteur = cfg.get("moteur") or "kimi"
            tag = "%s-%s" % (moteur, voix.lower())
            faits = []
            for c in file:
                if narration_en_cours(c["cd"]) or a_une_voix(c["cd"]):        # quelqu'un l'a fait entre-temps
                    continue
                etat["en_cours"] = {"d": c["d"], "num": c["num"], "pages": c["pages"]}
                ok = False
                for essai in (1, 2):
                    td = os.path.join(c["cd"], "narration", tag)
                    os.makedirs(td, exist_ok=True)
                    try: os.remove(os.path.join(td, "progress.json"))
                    except OSError: pass
                    t0 = time.time()
                    rc = lancer([PY, os.path.join(HERE, "narrate_chapter.py"), c["d"], "--engine", moteur, "--voice", voix, "--tag", tag],
                                os.path.join(td, "run.log"), etat, "narration")
                    ok = rc == 0 and os.path.isfile(os.path.join(td, "narration.json"))
                    journal("narration", d=c["d"], tag=tag, essai=essai, rc=rc, ok=ok, s=round(time.time() - t0))
                    if ok:
                        break
                if not ok:
                    etat["erreurs"].append({"d": c["d"], "etape": "narration", "t": time.time()}); ecrire_etat(etat)
                    continue
                faits.append(c)
                etat["fait"].append({"d": c["d"], "tag": tag, "t": time.time()}); ecrire_etat(etat)
                if cfg.get("karaoke", True):
                    rc = lancer([PY, os.path.join(HERE, "karaoke_mots.py"), c["d"], tag], os.path.join(td, "karaoke.log"), etat, "karaoke")
                    journal("karaoke", d=c["d"], tag=tag, rc=rc)
            if cfg.get("precedemment", True):
                for c in chapitres(s):
                    if a_une_voix(c["cd"]) and ouverture_a_faire(c):
                        etat["en_cours"] = {"d": c["d"], "num": c["num"]}
                        os.makedirs(os.path.join(c["cd"], "precedemment"), exist_ok=True)
                        rc = lancer([PY, os.path.join(HERE, "precedemment.py"), c["d"], "--mode", "ouverture", "--voice", voix],
                                    os.path.join(c["cd"], "precedemment", "ouverture.log"), etat, "precedemment")
                        journal("precedemment", d=c["d"], rc=rc)
            if cfg.get("video") and faits:
                for c in faits:
                    r = demander_video(c["d"], tag, cfg.get("reglages_video") or {})
                    journal("video", d=c["d"], reponse=r)
        etat.update(etat="fini", fin=time.time(), en_cours=None)
    except Exception as e:
        etat.update(etat="echec", fin=time.time(), err=str(e)[:300])
        journal("echec", err=str(e)[:300])
        raise
    finally:
        ecrire_etat(etat)
        journal("fin", etat=etat["etat"], fait=len(etat["fait"]), erreurs=len(etat["erreurs"]), s=round(time.time() - etat["debut"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
