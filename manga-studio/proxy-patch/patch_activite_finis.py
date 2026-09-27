# -*- coding: utf-8 -*-
"""Manga Studio v2.85.0 (R10, 27/09 -- Quang 11h41 : « j'ai lance une preparation sur mon smartphone, j'ai la notification
« Dialogue fini », mais sur le PC il est indique « Rien en cours » ») : un JOURNAL DES FINS tenu par le serveur, commun a tous
les appareils. Avant : « en cours » venait du serveur, mais « ✓ fini » etait calcule PAR APPAREIL (ce qui tournait au tour
d'avant) -> un appareil qui n'avait pas vu la tache tourner ne la voyait jamais finir. Vrai pour TOUS les types.

A chaque calcul de /manga/activite : une tache vue en cours au calcul precedent et absente maintenant = une FIN, notee dans
<MANGA_SOURCES>/_activite_finis.json (donc une par instance, dans SES donnees ; 24 h, 50 au plus) avec t = derniere fois vue en
cours, issue = fini | arrete | quota | erreur (Dialogues : lu dans son progress ; narration / traduction / lot : arret propre
demande dans les 2 min). /manga/activite renvoie « finis » (20 plus recents). /manga/activite_autre ne les transmet PAS (les
titres de la secondaire ne passent jamais dans la principale). Rejouable : python patch_activite_finis.py <proxy>"""
import io, sys

P = sys.argv[1]
s = io.open(P, encoding="utf-8", newline="").read()
if "def _act_journaliser(" in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", NL), b.replace("\n", NL)
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


rep('''def manga_activite():
    """Tout ce qui travaille en ce moment, tous chapitres confondus (Manga Studio v1.88.0)."""''',
    '''# --- Manga Studio v2.85.0 (R10) : journal des FINS, commun a tous les appareils --------------------------------------
_ACT_VU = {}                       # cle -> (tache, derniere fois vue en cours)
_ACT_COUPE = [0.0]                 # dernier arret propre demande (manga_interrompre)
_ACT_FIN_VERROU = threading.Lock()
_ACT_FIN_ISSUE_DLG = {"arrete": "arrete", "quota": "quota", "erreur": "erreur"}


def _act_fin_cle(it):
    if it.get("type") in ("lot", "dialogues_lot"):                 # un lot = UNE tache (son « d » suit le chapitre en cours)
        return it["type"] + "|" + str(it.get("titre") or "")
    return "|".join(str(it.get(k) or "") for k in ("type", "d", "tag", "langue"))


def _act_finis_fichier():
    return os.path.join(MANGA_SOURCES, "_activite_finis.json")


def _act_finis_lire():
    try:
        with open(_act_finis_fichier(), encoding="utf-8") as f:
            j = json.load(f)
        return j if isinstance(j, list) else []
    except Exception:
        return []


def _act_journaliser(out, maintenant):
    with _ACT_FIN_VERROU:
        vus = {_act_fin_cle(it): it for it in out if it.get("etape") != "attente"}
        partis = [(k, v) for k, v in list(_ACT_VU.items()) if k not in vus]
        for k, it in vus.items():
            _ACT_VU[k] = (dict(it), maintenant)
        if not partis:
            return
        j = _act_finis_lire()
        for k, (it, t) in partis:
            _ACT_VU.pop(k, None)
            issue = "fini"
            if it.get("type") == "dialogues":
                pr = _dlg_lire(os.path.join(MANGA_SOURCES, it.get("d") or "", "dialogues", "progress.json")) or {}
                issue = _ACT_FIN_ISSUE_DLG.get(pr.get("etape"), "fini")
            elif it.get("type") in ("narration", "traduction", "lot", "dialogues_lot") and maintenant - _ACT_COUPE[0] < 120:
                issue = "arrete"
            e = {c: it.get(c) for c in ("type", "d", "titre", "chapitre", "tag", "langue", "etape") if it.get(c) not in (None, "")}
            e.update(cle=k, t=round(t, 1), vu_fini=round(maintenant, 1), issue=issue)
            j.insert(0, e)
        j = [x for x in j if maintenant - (x.get("t") or 0) < 86400][:50]
        try:
            tmp = _act_finis_fichier() + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(j, f, ensure_ascii=False)
            os.replace(tmp, _act_finis_fichier())
        except Exception:
            pass


def manga_activite():
    """Tout ce qui travaille en ce moment, tous chapitres confondus (Manga Studio v1.88.0)."""''')
rep('''            it["reste_s"] = round((total - fait) * (maintenant - t0) / (fait - f0))
    return {"items": out, "t": maintenant}''',
    '''            it["reste_s"] = round((total - fait) * (maintenant - t0) / (fait - f0))
    try:
        _act_journaliser(out, maintenant)                   # v2.85.0 (R10)
    except Exception:
        pass
    return {"items": out, "t": maintenant, "finis": _act_finis_lire()[:20]}''')
rep('''    + bilan exact. Toute la logique est dans scripts/interruption.py (recharge a chaud)."""
''', '''    + bilan exact. Toute la logique est dans scripts/interruption.py (recharge a chaud)."""
    _ACT_COUPE[0] = time.time()                             # v2.85.0 (R10) : ce qui disparait maintenant est ARRETE, pas fini
''')
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
