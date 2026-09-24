# -*- coding: utf-8 -*-
"""INTERROMPRE ce qui depend du mode « ☁ En ligne / 🖥 Sur mon PC » (feuille de route 4-undecies, 24/09/2026). v1.0.0

Quang : « si quelque chose tourne, que je ne switch pas en plein milieu […] une pop-up d'alerte, et c'est moi qui decide
si je veux interrompre ou non […] gerer les effets collateraux si je decide d'interrompre. Il faut que je sache
exactement ou j'en suis. »

Ce qui depend du mode : la NARRATION (voix) et la TRADUCTION (effacement), seules ou dans un lot (« Tout traiter » / la
nuit). Le karaoke, « Precedemment », la capture et les videos ne changent pas d'un mode a l'autre : on ne les touche pas.

interrompre() : arrete proprement (le processus de l'etape en cours, puis le lot), marque ce qui a ete coupe, et rend un
BILAN exact : chapitres finis, chapitre coupe + etape atteinte (+ analyse des pages deja payee et gardee : la reprise la
relit sans la repayer), chapitres non commences. Tout ce qui a ete paye est deja au registre des depenses.
Appele par le proxy (POST /manga/interrompre), charge a la volee.
"""
import glob, json, os, subprocess, sys, time

VERSION = "1.0.0"
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.environ.get("MANGA_SOURCES_DIR") or os.path.join(HERE, "..", "sources"))
sys.path.insert(0, HERE)
CREATE = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _suivi():
    import importlib
    return importlib.import_module("suivi_nuit")


def _lire(f):
    try:
        with open(f, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def _tuer(pid):
    """Arbre de processus (l'etape lance ses propres enfants : ffmpeg, TTS local...). True si le PID est mort ensuite."""
    if not pid:
        return True
    try:
        subprocess.run(["taskkill", "/PID", str(int(pid)), "/T", "/F"], capture_output=True, creationflags=CREATE, timeout=30)
    except Exception:
        pass
    for _ in range(20):
        if not _suivi().pid_vivant(pid):
            return True
        time.sleep(0.25)
    return False


def _marquer(pf, **kw):
    """Le progress.json d'un passage coupe dit POURQUOI il s'est arrete (sinon le proxy n'y voit qu'un « echec »)."""
    pr = _lire(pf) or {}
    pr.update(etape="interrompu", interrompu=time.strftime("%Y-%m-%dT%H:%M:%S"), **kw)
    try:
        with open(pf + ".tmp", "w", encoding="utf-8") as f:
            json.dump(pr, f, ensure_ascii=False)
        os.replace(pf + ".tmp", pf)
    except OSError:
        pass


def _passages_seuls():
    """Narrations et traductions lancees seules (hors lot) qui tournent : (type, d, cle, progress.json, pid)."""
    s, out = _suivi(), []
    for pf in glob.glob(os.path.join(SRC, "*", "*", "narration", "*", "progress.json")) \
            + glob.glob(os.path.join(SRC, "*", "*", "traduction", "*", "progress.json")):
        pr = _lire(pf) or {}
        if pr.get("etape") in ("fini", "interrompu") or pr.get("fini") or not pr.get("pid"):
            continue
        if time.time() - float(pr.get("t") or 0) > 3600 or not s.pid_vivant(pr["pid"]):
            continue
        parts = os.path.relpath(pf, SRC).replace("\\", "/").split("/")
        out.append({"type": parts[2], "d": parts[0] + "/" + parts[1], "cle": parts[3], "progress": pf,
                    "pid": pr["pid"], "etape": pr.get("etape"), "fait": pr.get("fait"), "total": pr.get("total")})
    return out


def interrompre(qui="app"):
    s = _suivi()
    bilan = {"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "lot": None, "seuls": [], "non_arretes": []}
    e = s.lire_etat()
    if e.get("etat") == "en cours" and s.pid_vivant(e.get("pid")):
        ec = e.get("en_cours") or {}
        _tuer(ec.get("pid"))                                  # l'etape d'abord (sinon elle finirait orpheline)
        if not _tuer(e.get("pid")):
            bilan["non_arretes"].append("lot PID %s" % e.get("pid"))
        finis = [x.get("num") for x in e.get("fait") or []]
        erreurs = [x.get("num") for x in e.get("erreurs") or []]
        vus = {x.get("d") for x in (e.get("fait") or []) + (e.get("erreurs") or [])}
        coupe = None
        if ec.get("d"):
            vus.add(ec["d"])
            cd = os.path.join(SRC, ec["d"])
            coupe = {"d": ec["d"], "num": ec.get("num"), "etape": ec.get("etape"), "analyse_gardee": False}
            nd = glob.glob(os.path.join(cd, "narration", "*", "progress.json"))
            for pf in nd:                                     # la narration du chapitre coupe, s'il y en avait une en route
                pr = _lire(pf) or {}
                if pr.get("etape") not in ("fini", "interrompu") and not pr.get("fini"):
                    _marquer(pf, par=qui)
                    td = os.path.dirname(pf)
                    coupe["analyse_gardee"] = s.vision_reprenable(td, cd)
                    coupe["tag"] = os.path.basename(td)             # la reprise relit l'analyse ICI, quel que soit le mode
                    coupe["etape_narration"] = pr.get("etape")
            if ec.get("etape") == "traduction":
                for pf in glob.glob(os.path.join(cd, "traduction", "*", "progress.json")):
                    pr = _lire(pf) or {}
                    if pr.get("etape") not in ("fini", "interrompu") and not pr.get("fini"):
                        _marquer(pf, par=qui)
        restants = [d for d in e.get("file") or [] if d not in vus]
        e.update(etat="interrompu", fin=time.time(), en_cours=None,
                 interruption={"t": bilan["t"], "par": qui, "coupe": coupe, "restants": restants})
        s.ecrire_etat(e)
        s.journal("interruption", par=qui, coupe=coupe, restants=restants, finis=finis, erreurs=erreurs)
        bilan["lot"] = {"serie": e.get("serie"), "refaire": bool(e.get("refaire")), "finis": finis, "erreurs": erreurs,
                        "coupe": coupe, "restants": restants,
                        "restants_num": [d.split("/")[-1][3:] for d in restants]}
    for p in _passages_seuls():
        ok = _tuer(p["pid"])
        _marquer(p["progress"], par=qui)
        (bilan["seuls"] if ok else bilan["non_arretes"]).append(
            {k: p[k] for k in ("type", "d", "cle", "etape", "fait", "total")} if ok else "%s %s PID %s" % (p["type"], p["d"], p["pid"]))
        if ok and p["type"] == "narration":
            bilan["seuls"][-1]["analyse_gardee"] = s.vision_reprenable(os.path.dirname(p["progress"]), os.path.join(SRC, p["d"]))
    return bilan


if __name__ == "__main__":
    print(json.dumps(interrompre("ligne de commande"), ensure_ascii=False, indent=1))
