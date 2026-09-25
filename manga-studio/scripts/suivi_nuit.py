# -*- coding: utf-8 -*-
"""CHAINE DE TRAITEMENT des chapitres : la nuit (suivi) OU a la demande (« Tout traiter »). Manga Studio v2.4.0.

Historique : v1.98.0 (22/09 09h, etape 9) = le suivi de nuit narrait les chapitres captures. v2.4.0 (22/09 15h, etape 27,
demande Quang 15h00) : la MEME chaine sert au bouton « Tout traiter » d'une serie, sur toute la serie ou une selection,
et fait tout jusqu'a la video. Par chapitre, DANS L'ORDRE, chapitre apres chapitre (le 1er est regardable pendant que
les suivants se font) :
  1. narration  (moteur + voix du PROFIL)   -- sautee si le chapitre a deja une narration avec voix (sauf --refaire)
  2. karaoke    (option)                    -- saute si deja cale
  3. traduction (langue du profil, option)  -- sautee si deja faite, OU si le chapitre est DEJA dans cette langue
  4. « Precedemment... » (option)           -- saute s'il est a jour
  5. video      (option, file du proxy)     -- sautee si elle est a jour (meme empreinte que le proxy), pages traduites
                                               si la traduction existe
Un chapitre qui echoue n'arrete pas les autres (2 essais par etape lourde). Jamais deux passages a la fois.

REGLAGES, trois niveaux (Quang 15h03) :
  - integres ici (DEFAUT_INTEGRE) < defaut GENERAL sources/_profil_defaut.json (« en faire mes reglages par defaut »)
    < PROFIL de la serie sources/<serie>/suivi.json (nom historique garde : le proxy et l'app le lisent deja).
  - la musique n'est pas dans le profil : c'est la selection de la serie (musique/choix.json) ou celle du chapitre.
Nuit : series dont le profil a « actif », chapitres qui ont au moins une etape a faire.

Usage : python suivi_nuit.py [--serie slug] [--chapitres serie/ch_1,serie/ch_2] [--refaire] [--dry] [--declencheur X]
        --dry : affiche le PLAN (etapes a faire par chapitre + estimation), ne lance rien.
Etat : sources/_suivi/etat.json ; journal : sources/_suivi/journal.jsonl (tout, horodate).
"""
import argparse, json, os, subprocess, sys, time, urllib.request
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import precedemment as prec                                # chapitres_precedents(), chap_key()
import estimation                                          # v2.5.0 : double estimation ☁ / 🖥

VERSION = "2.6.0"
SRC = os.path.normpath(os.environ.get("MANGA_SOURCES_DIR") or os.path.join(HERE, "..", "sources"))
DIR = os.path.join(SRC, "_suivi")
ETAT, JOURNAL = os.path.join(DIR, "etat.json"), os.path.join(DIR, "journal.jsonl")
DEFAUT_F = os.path.join(SRC, "_profil_defaut.json")
PY = sys.executable.replace("pythonw.exe", "python.exe")
CREATE = getattr(subprocess, "CREATE_NO_WINDOW", 0)
# v2.5.1 (24/09, lot de Quang dans la SECONDAIRE : « video : chapitre introuvable ») : l'adresse etait en dur sur la
# principale -> la secondaire lui demandait la video d'un chapitre prive qu'elle ne voit pas. On parle a SON serveur.
PROXY = os.environ.get("MANGA_PROXY") or ("http://127.0.0.1:" + os.environ.get("MANGA_PRIVE_PORT", "8192")
                                          if os.environ.get("MANGA_ESPACE") == "prive" else "http://127.0.0.1:8190")
ETAPES = ("narration", "karaoke", "traduction", "precedemment", "video")
MOTEURS = ("kimi", "gemini")
LANGUES = ("fr", "en", "es", "de", "it", "pt", "vi")

# Reglages de depart si rien n'a jamais ete choisi (repris du suivi v1.98 + du lecteur).
DEFAUT_INTEGRE = {
    "actif": False, "moteur": "kimi", "voix": "Charon", "voix_moteur": "cloud", "traduction": "",
    "karaoke": True, "precedemment": True, "video": True,
    "reglages_video": {"vitesse": 1.0, "vitesse_local": 1.0, "sous": True, "karaoke": True, "musique": True, "volume": 25,
                       "pages": "", "precedemment": True, "camera": "cases"},
}
# v2.5.0 (23/09) : camera « cases » par defaut pour TOUS les formats (decision Quang 00h08) ; « page » = zoom lent d'avant.
CAMERAS = ("cases", "page")
# Couts et durees PAR PAGE, mesures (21-22/09) : narration (suivi v1.98), traduction Claymore ch.1 (0,54 $, 459 s, 62 p.).
# v2.5.0 : les tarifs fixes (TARIF_*) sont remplaces par estimation.py, recalcule sur les passages reels.


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


def _lire_json(f):
    try:
        return json.load(open(f, encoding="utf-8"))
    except Exception:
        return None


# ------------------------------------------------------------------ reglages (3 niveaux)
def normaliser(cfg):
    """Un profil propre et complet, quoi qu'il y ait dans le fichier (valeurs inconnues -> celles par defaut)."""
    d, cfg = DEFAUT_INTEGRE, dict(cfg or {})
    rv = dict(d["reglages_video"]); rv.update({k: v for k, v in (cfg.get("reglages_video") or {}).items() if k in rv})
    if rv.get("camera") not in CAMERAS:
        rv["camera"] = d["reglages_video"]["camera"]
    voix = cfg.get("voix") if isinstance(cfg.get("voix"), str) and cfg.get("voix", "")[:1].isupper() else d["voix"]
    return {"actif": bool(cfg.get("actif", d["actif"])),
            "moteur": cfg.get("moteur") if cfg.get("moteur") in MOTEURS else d["moteur"],
            "voix": voix,
            # v2.11.0 : plus de reglage par serie -- l'interrupteur GLOBAL « En ligne / Sur mon PC » (reglages.py) decide
            "voix_moteur": "local" if __import__("reglages").sur_pc() else "cloud",
            "traduction": cfg.get("traduction") if cfg.get("traduction") in LANGUES else "",
            "karaoke": bool(cfg.get("karaoke", d["karaoke"])),
            "precedemment": bool(cfg.get("precedemment", d["precedemment"])),
            "video": bool(cfg.get("video", d["video"])),
            "reglages_video": rv}


def profil_defaut():
    return normaliser(_lire_json(DEFAUT_F) or {})


def profil(serie):
    """(profil effectif, a_son_profil) : suivi.json de la serie, sinon le defaut general."""
    propre = _lire_json(os.path.join(SRC, serie, "suivi.json"))
    if propre is None:
        return profil_defaut(), False
    base = profil_defaut()
    base.update({k: v for k, v in propre.items() if k != "reglages_video"})
    base["reglages_video"] = dict(base["reglages_video"], **(propre.get("reglages_video") or {}))
    return normaliser(base), True


# ------------------------------------------------------------------ etat d'un chapitre
def series_suivies(seule=None):
    out = []
    for s in sorted(os.listdir(SRC)):
        if s.startswith("_") or (seule and s != seule) or not os.path.isdir(os.path.join(SRC, s)):
            continue
        if not os.path.isfile(os.path.join(SRC, s, "suivi.json")):
            continue
        cfg, _ = profil(s)
        if cfg.get("actif"):
            out.append((s, cfg))
    return out


def narrations_voix(cd):
    """Narrations finies AVEC voix, la plus recente d'abord : [(tag, mtime)]."""
    nd, out = os.path.join(cd, "narration"), []
    for tag in (os.listdir(nd) if os.path.isdir(nd) else []):
        f = os.path.join(nd, tag, "narration.json")
        n = _lire_json(f)
        if n and any(p.get("audio") for p in n.get("pages") or []):
            out.append((tag, os.path.getmtime(f)))
    return sorted(out, key=lambda x: -x[1])


def a_une_voix(cd):
    return bool(narrations_voix(cd))


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
            man = _lire_json(os.path.join(cd, "manifest.json")) or {}
            out.append({"d": serie + "/" + ch, "cd": cd, "num": str(man.get("chapter") or ch[3:]),
                        "pages": len(man.get("pages") or [])})
    return sorted(out, key=lambda x: prec.chap_key(x["num"]))


def a_narrer(serie):
    """(compatibilite v1.98, lu par le proxy) chapitres sans narration avec voix, sans narration en cours."""
    return [c for c in chapitres(serie) if not a_une_voix(c["cd"]) and not narration_en_cours(c["cd"])]


def tag_profil(cfg):
    return "%s-%s" % (cfg["moteur"], cfg["voix"].lower().replace("@", "-ton").replace(".", "")) + ("-local" if cfg.get("voix_moteur") == "local" else "")   # S7


def tag_retenu(cd, cfg):
    """La narration qui sert au karaoke et a la video : celle du profil si elle existe, sinon la plus recente."""
    nv = [t for t, _m in narrations_voix(cd)]
    return tag_profil(cfg) if tag_profil(cfg) in nv else (nv[0] if nv else None)


def karaoke_manque(cd, tag):
    n = _lire_json(os.path.join(cd, "narration", tag, "narration.json")) or {}
    return any(p.get("audio") and (p.get("narration") or "").strip() and not p.get("mots") for p in n.get("pages") or [])


def langue_du_chapitre(c, detecter=True):
    """Langue d'origine (langue.json) ; detectee a la demande (~0,0025 $) si elle manque. None = inconnue."""
    j = _lire_json(os.path.join(c["cd"], "langue.json"))
    if j and j.get("langue"):
        return j["langue"]
    if not detecter:
        return None
    try:
        import langue_chapitre
        return (langue_chapitre.detecter(c["d"]) or {}).get("langue")
    except BaseException as e:                     # detecter() leve SystemExit sur chapitre introuvable
        journal("langue", d=c["d"], err=str(e)[:200])
        return None


def traduction_faite(cd, lg):
    return os.path.isfile(os.path.join(cd, "traduction", lg, "traduction.json"))


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


def musique_effective(c):
    """Les morceaux qui accompagneront la video (meme regle que le proxy : propre au chapitre, sinon la serie)."""
    ch = _lire_json(os.path.join(c["cd"], "musique.json")) or {}
    if ch.get("mode") == "propre":
        return list(ch.get("noms") or [])
    sj = _lire_json(os.path.join(SRC, c["d"].split("/")[0], "musique", "choix.json")) or {}
    if isinstance(sj.get("serie"), list):
        return list(sj["serie"])
    return [sj["nom"]] if sj.get("nom") else []


def reglages_video_voulus(c, cfg, tag=""):
    # v2.6.0 (Quang 25/09) : la voix LOCALE parle plus vite -> sa propre vitesse ; la video ne recoit que « vitesse »
    rv = dict(cfg["reglages_video"])
    vl = rv.pop("vitesse_local", None)
    if str(tag).endswith("-local") and vl:
        rv["vitesse"] = vl
    lg = cfg.get("traduction") or ""
    rv["pages"] = lg if lg and traduction_faite(c["cd"], lg) else ""
    return rv


def video_a_faire(c, tag, cfg):
    """None = a jour ; sinon la raison. Meme empreinte que le proxy (video_chapitre.empreinte)."""
    info = _lire_json(os.path.join(c["cd"], "video", tag + ".json"))
    if not info or not os.path.isfile(os.path.join(c["cd"], "video", tag + ".mp4")):
        return "pas encore de vidéo"
    voulu, fait = reglages_video_voulus(c, cfg, tag), info.get("reglages") or {}
    for k in ("vitesse", "sous", "karaoke", "musique", "volume", "pages", "precedemment"):
        if (voulu.get(k) or "") != (fait.get(k) or ""):
            return "réglage changé (%s)" % k
    if (voulu.get("camera") or "page") != (fait.get("camera") or "page"):      # v2.5.0 : une video d'avant = « page »
        return "réglage changé (caméra : %s)" % ("case par case" if voulu.get("camera") == "cases" else "page entière")
    if voulu.get("musique") and musique_effective(c) != (fait.get("musique_noms") or []):
        return "la sélection de musique a changé"
    try:
        import video_chapitre
        cur, old = video_chapitre.empreinte(c["d"], tag, fait), info.get("empreinte") or {}
    except Exception as e:
        return "empreinte illisible (%s)" % str(e)[:60]
    for k, v in cur.items():
        if k == "reglages" or (k == "karaoke" and not (fait.get("sous") and fait.get("karaoke"))):
            continue
        if old.get(k) != v:
            return "le moteur vidéo a été amélioré" if k == "moteur" else "%s a changé" % k      # v1.97.0
    return None


def video_en_file(d):
    fd = os.path.join(SRC, "_videos_file")
    for f in (os.listdir(fd) if os.path.isdir(fd) else []):
        if f.endswith(".json") and not f.startswith("_"):
            e = _lire_json(os.path.join(fd, f)) or {}
            if e.get("d") == d and e.get("etat") in ("attente", "en cours"):
                return True
    return False


# ------------------------------------------------------------------ PLAN (ce que ferait la chaine)
def plan_chapitre(c, cfg, refaire=False, avant_narres=False, detecter_langue=False):
    """Pour chaque etape : "faire" | "fait" | "non" (pas demandee / sans objet) + le pourquoi.
    avant_narres : un chapitre PRECEDENT de ce lot va etre narre (le « Precedemment » sera alors a faire)."""
    et, pourquoi = {}, {}
    tag = tag_retenu(c["cd"], cfg)
    narrer = refaire or tag is None
    et["narration"] = "faire" if narrer else "fait"
    tag_final = tag_profil(cfg) if narrer else tag
    if not cfg["karaoke"]:
        et["karaoke"] = "non"
    else:
        et["karaoke"] = "faire" if narrer or refaire or karaoke_manque(c["cd"], tag_final) else "fait"
    lg = cfg.get("traduction") or ""
    if not lg:
        et["traduction"] = "non"
    else:
        orig = langue_du_chapitre(c, detecter=detecter_langue)
        if orig == lg:
            et["traduction"], pourquoi["traduction"] = "non", "déjà en " + lg
        else:
            et["traduction"] = "faire" if refaire or not traduction_faite(c["cd"], lg) else "fait"
    if not cfg["precedemment"]:
        et["precedemment"] = "non"
    else:
        precedents = [x for x in prec.chapitres_precedents(os.path.dirname(c["cd"]), c["num"])]
        if not precedents:
            et["precedemment"], pourquoi["precedemment"] = "non", "premier chapitre"
        elif refaire or avant_narres or ouverture_a_faire(c):
            et["precedemment"] = "faire"
        else:
            et["precedemment"] = "fait" if os.path.isfile(os.path.join(c["cd"], "precedemment", "ouverture.json")) else "non"
    if not cfg["video"]:
        et["video"] = "non"
    elif video_en_file(c["d"]):
        et["video"], pourquoi["video"] = "fait", "déjà dans la file"
    elif narrer or refaire or any(et[k] == "faire" for k in ("karaoke", "traduction", "precedemment")):
        et["video"] = "faire"
    else:
        r = video_a_faire(c, tag_final, cfg)
        et["video"] = "faire" if r else "fait"
        if r:
            pourquoi["video"] = r
    n = c["pages"]
    # v2.5.0 (4-undecies) : les DEUX estimations (☁ en ligne / 🖥 sur le PC), recalculees sur les passages reels
    # (estimation.py) ; « cout » / « minutes » = celles du mode actif, comme avant pour qui ne lit que celles-la.
    estim = estimation.chapitre(n, {k for k, v in et.items() if v == "faire"}, cfg["moteur"])
    actif = estim["pc" if cfg.get("voix_moteur") == "local" else "cloud"]
    return {"d": c["d"], "num": c["num"], "pages": n, "tag": tag_final, "etapes": et, "pourquoi": pourquoi,
            "a_faire": any(v == "faire" for v in et.values()), "cout": round(actif["usd"], 3), "minutes": actif["min"],
            "estim": estim}


def plan_serie(serie, chapitres_voulus=None, refaire=False, cfg=None, detecter_langue=False):
    """Le plan d'une serie (tous ses chapitres, ou ceux demandes), dans l'ordre des chapitres."""
    cfg = cfg or profil(serie)[0]
    out, narre_avant = [], False
    for c in chapitres(serie):
        if chapitres_voulus is not None and c["d"] not in chapitres_voulus:
            continue
        p = plan_chapitre(c, cfg, refaire, narre_avant, detecter_langue)
        if narration_en_cours(c["cd"]):
            p["etapes"] = {k: "fait" for k in ETAPES}; p["a_faire"] = False; p["pourquoi"] = {"narration": "narration en cours"}
        out.append(p)
        narre_avant = narre_avant or (p["etapes"]["narration"] == "faire")
    return out


# ------------------------------------------------------------------ execution
def lancer(cmd, log, etat, etape):
    etat["en_cours"] = dict(etat.get("en_cours") or {}, etape=etape, depuis=time.time())
    ecrire_etat(etat)
    os.makedirs(os.path.dirname(log), exist_ok=True)
    with open(log, "a", encoding="utf-8") as lg:          # AJOUT : un 2e essai n'efface plus la cause du 1er
        lg.write("\n===== %s · %s (chaine) =====\n" % (datetime.now().isoformat(timespec="seconds"), etape)); lg.flush()
        p = subprocess.Popen(cmd, stdout=lg, stderr=lg, cwd=HERE, creationflags=CREATE,
                             env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        etat["en_cours"]["pid"] = p.pid; ecrire_etat(etat)
        return p.wait()


def derniere_ligne(log):
    try:
        return [x for x in open(log, encoding="utf-8", errors="replace").read().splitlines() if x.strip()][-1][:300]
    except Exception:
        return ""


def demander_video(d, tag, reglages):
    try:
        k = open(os.path.join(os.path.expanduser("~"), "Documents", "ComfyUI", ".studio_secret"), encoding="utf-8").read().strip()
        req = urllib.request.Request(PROXY + "/manga/video", data=json.dumps({"entrees": [{"d": d, "tag": tag}], "reglages": reglages}).encode(),
                                     headers={"Authorization": "Bearer " + k, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except Exception as e:
        return {"error": str(e)[:200]}


def vision_reprenable(td, cd):
    """v2.4.1 : l'analyse des pages (vision.json, ~90 % du cout d'une narration) d'un run precedent est reprise
    si elle est posterieure a la capture (manifest.json) : 23/09, Claymore ch.1 = 1,74 $ d'analyse perdus par un
    echec du recit, et le 2e essai l'aurait RE-payee."""
    v, m = os.path.join(td, "vision.json"), os.path.join(cd, "manifest.json")
    try:
        return os.path.getmtime(v) >= os.path.getmtime(m) and bool((_lire_json(v) or {}).get("pages"))
    except OSError:
        return False


def _vision_depuis(td, t):
    try:
        return bool(t) and os.path.getmtime(os.path.join(td, "vision.json")) >= float(t)
    except OSError:
        return False


def traiter_chapitre(c, cfg, refaire, etat, avant_narres, reprise_de=None):
    """La chaine d'UN chapitre. Retourne (ok, {etape: resultat})."""
    # v2.5.0 (4-undecies) : le mode « ☁ / 🖥 » est RELU a chaque chapitre, pour la voix comme pour l'effacement. Avant,
    # la voix restait celle du LANCEMENT du lot (profil lu une fois) pendant que l'effacement suivait l'interrupteur :
    # basculer en plein lot aurait melange voix en ligne + effacement local. Ce qui tourne finit dans son mode ; les
    # chapitres suivants prennent le nouveau.
    cfg = dict(cfg, voix_moteur="local" if __import__("reglages").sur_pc() else "cloud")
    p = plan_chapitre(c, cfg, refaire, avant_narres, detecter_langue=True)
    et, res = p["etapes"], {}
    etat["en_cours"] = {"d": c["d"], "num": c["num"], "pages": c["pages"], "etapes": et, "mode": "pc" if cfg["voix_moteur"] == "local" else "cloud"}
    tag = p["tag"]
    td = os.path.join(c["cd"], "narration", tag)
    # 1. narration
    if et["narration"] == "faire":
        ok, err = False, ""
        for essai in (1, 2):
            os.makedirs(td, exist_ok=True)
            try: os.remove(os.path.join(td, "progress.json"))
            except OSError: pass
            t0 = time.time()
            # v2.5.0 : un chapitre COUPE par une interruption reprend son analyse deja payee, meme en « refaire » et meme
            # si le mode a change entre-temps (l'analyse est la meme en ☁ et en 🖥 ; seul le dossier -local differe)
            src = (reprise_de or {}).get("tag") if (reprise_de or {}).get("d") == c["d"] else None
            sd = os.path.join(c["cd"], "narration", src) if src else td
            coupe_ici = bool(src) and _vision_depuis(sd, reprise_de.get("debut")) and vision_reprenable(sd, c["cd"])
            reprise = coupe_ici or ((essai > 1 or not refaire) and vision_reprenable(td, c["cd"]))
            rc = lancer([PY, os.path.join(HERE, "narrate_chapter.py"), c["d"], "--engine", cfg["moteur"], "--voice", cfg["voix"], "--tag", tag,
                         "--tts", cfg.get("voix_moteur") or "cloud"]
                        + (["--reuse-vision", src if coupe_ici else tag] if reprise else []),
                        os.path.join(td, "run.log"), etat, "narration")
            n = _lire_json(os.path.join(td, "narration.json"))
            ok = rc == 0 and bool(n) and (not refaire or os.path.getmtime(os.path.join(td, "narration.json")) >= t0 - 1)
            err = "" if ok else derniere_ligne(os.path.join(td, "run.log"))
            journal("narration", d=c["d"], tag=tag, essai=essai, rc=rc, ok=ok, s=round(time.time() - t0), err=err,
                    analyse_reprise=reprise)
            if ok:
                break
        res["narration"] = "ok" if ok else "echec : " + err
        if not ok:
            return False, res                                # sans narration, rien d'autre n'a de sens
    # 2. karaoke
    if et["karaoke"] == "faire":
        rc = lancer([PY, os.path.join(HERE, "karaoke_mots.py"), c["d"], tag] + (["--force"] if refaire else []),
                    os.path.join(td, "karaoke.log"), etat, "karaoke")
        res["karaoke"] = "ok" if rc == 0 else "echec : " + derniere_ligne(os.path.join(td, "karaoke.log"))
        journal("karaoke", d=c["d"], tag=tag, rc=rc)
    # 3. traduction
    lg = cfg.get("traduction") or ""
    if et["traduction"] == "faire":
        tdir = os.path.join(c["cd"], "traduction", lg)
        ok = False
        for essai in (1, 2):
            t0 = time.time()
            rc = lancer([PY, os.path.join(HERE, "traduire_chapitre.py"), c["d"], "--langue", lg, "--engine", "gemini"]
                        + (["--effacement", "local"] if __import__("reglages").sur_pc() else []),
                        os.path.join(tdir, "run.log"), etat, "traduction")
            ok = rc == 0 and traduction_faite(c["cd"], lg)
            journal("traduction", d=c["d"], langue=lg, essai=essai, rc=rc, ok=ok, s=round(time.time() - t0))
            if ok:
                break
        res["traduction"] = "ok" if ok else "echec : " + derniere_ligne(os.path.join(tdir, "run.log"))
    elif p["pourquoi"].get("traduction"):
        res["traduction"] = "sautée : " + p["pourquoi"]["traduction"]
    # 4. « Precedemment... » (verifie A CET INSTANT : les chapitres d'avant viennent peut-etre d'etre narres)
    if et["precedemment"] == "faire" and (refaire or ouverture_a_faire(c)):
        os.makedirs(os.path.join(c["cd"], "precedemment"), exist_ok=True)
        rc = lancer([PY, os.path.join(HERE, "precedemment.py"), c["d"], "--mode", "ouverture", "--voice", cfg["voix"]],
                    os.path.join(c["cd"], "precedemment", "ouverture.log"), etat, "precedemment")
        res["precedemment"] = "ok" if rc == 0 else "echec"
        journal("precedemment", d=c["d"], rc=rc)
    # 5. video (la file du proxy la fabrique ; on la demande, on n'attend pas)
    if et["video"] == "faire":
        etat["en_cours"]["etape"] = "video"; ecrire_etat(etat)
        r = demander_video(c["d"], tag, reglages_video_voulus(c, cfg, tag))
        ok = bool(r.get("ajoutees")) or any("file" in (x.get("raison") or "") for x in r.get("refusees") or [])
        res["video"] = "demandée" if ok else "echec : " + (r.get("error") or "; ".join(x.get("raison", "") for x in r.get("refusees") or []))
        journal("video", d=c["d"], tag=tag, reponse=r)
    return not any(str(v).startswith("echec") for v in res.values()), res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--serie", default="")
    ap.add_argument("--chapitres", default="", help="serie/ch_1,serie/ch_2 (defaut : tous ceux qui ont une etape a faire)")
    ap.add_argument("--refaire", action="store_true", help="refaire meme ce qui est deja fait")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--declencheur", default="manuel")
    a = ap.parse_args()
    for flux in (sys.stdout, sys.stderr):
        if flux and hasattr(flux, "reconfigure"):
            flux.reconfigure(encoding="utf-8", errors="replace")
    old = lire_etat()
    if not a.dry and old.get("etat") == "en cours" and pid_vivant(old.get("pid")):
        journal("refus", raison="un passage tourne deja", pid=old.get("pid"))
        print("un passage tourne deja (PID %s)" % old.get("pid"))
        return 2
    voulus = [x.strip() for x in a.chapitres.split(",") if x.strip()] or None
    if voulus or a.declencheur == "lot":
        # A LA DEMANDE : la serie donnee, meme si elle n'est pas suivie la nuit
        if not a.serie:
            print("--serie obligatoire pour un lot"); return 1
        cfg = profil(a.serie)[0]
        cibles = [(a.serie, cfg)]
    else:
        cibles = series_suivies(a.serie or None)             # LA NUIT : les series « actif »
    plan = []
    for s, cfg in cibles:
        pl = plan_serie(s, voulus, a.refaire, cfg)
        plan.append((s, cfg, [p for p in pl if p["a_faire"]]))
    if a.dry:
        for s, cfg, pl in plan:
            print("%s (%s-%s, traduction %s) : %d chapitre(s), ~%.2f $, ~%d min" % (
                s, cfg["moteur"], cfg["voix"], cfg["traduction"] or "aucune", len(pl),
                sum(p["cout"] for p in pl), sum(p["minutes"] for p in pl)))
            for p in pl:
                print("  ch.%-6s %s %s" % (p["num"], " ".join("%s=%s" % (k[:4], v) for k, v in p["etapes"].items()),
                                            p["pourquoi"] or ""))
        return 0
    if not any(pl for _s, _c, pl in plan):
        journal("rien", declencheur=a.declencheur, series=[s for s, _c, _p in plan])
        print("rien a faire")
        return 0
    # v2.5.0 : reprise apres une interruption (interruption.py) -> le chapitre coupe ne repaie pas son analyse
    reprise_de = dict((old.get("interruption") or {}).get("coupe") or {}, debut=old.get("debut")) if old.get("etat") == "interrompu" else None
    etat = {"version": VERSION, "etat": "en cours", "pid": os.getpid(), "debut": time.time(), "declencheur": a.declencheur,
            "serie": a.serie or None, "refaire": a.refaire, "fait": [], "erreurs": [], "en_cours": None,
            "file": [p["d"] for _s, _c, pl in plan for p in pl],
            "estimation": {"cout": round(sum(p["cout"] for _s, _c, pl in plan for p in pl), 2),
                           "minutes": round(sum(p["minutes"] for _s, _c, pl in plan for p in pl))}}
    ecrire_etat(etat)
    journal("debut", declencheur=a.declencheur, series=[s for s, _c, _p in plan], file=etat["file"], refaire=a.refaire)
    try:
        for s, cfg, pl in plan:
            narre_avant = False
            tous = {c["d"]: c for c in chapitres(s)}
            for p in pl:
                c = tous.get(p["d"])
                if not c or narration_en_cours(c["cd"]):
                    continue
                t0 = time.time()
                ok, res = traiter_chapitre(c, cfg, a.refaire, etat, narre_avant, reprise_de)
                narre_avant = narre_avant or res.get("narration") == "ok"
                ligne = {"d": c["d"], "num": c["num"], "res": res, "s": round(time.time() - t0), "t": time.time()}
                (etat["fait"] if ok else etat["erreurs"]).append(ligne)
                etat["en_cours"] = None; ecrire_etat(etat)
                journal("chapitre", ok=ok, **{k: v for k, v in ligne.items() if k != "t"})   # « t » = l'horodatage du journal
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
