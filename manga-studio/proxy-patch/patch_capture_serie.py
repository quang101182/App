# -*- coding: utf-8 -*-
"""Patch du proxy 8190 : CAPTURE DE PLUSIEURS CHAPITRES (Manga Studio v2.3.0, etape 18).

Quang (22/09 10h43) : « definir le nombre de chapitres a capturer a partir de celui ou je suis, ou du ch. X au ch. Y ».
manga-fetch v0.4.0 porte l'enchainement (--suite N / --jusqua Y, verifie site par site : MangaDex par l'API,
MANGA Plus par la page de la serie). Ici, le proxy :
- relaie `suite` (0-50) et `jusqua` a POST /manga/fetch_capture ;
- suit la serie dans GET /manga/fetch_status : chapitre EN COURS (ligne « === Chapitre suivant : X === »),
  pages du chapitre en cours (depuis son dernier « [capture] demarrage »), `dossiers` = tous les chapitres
  ecrits, `serie` = la ligne de bilan « SERIE : ... ».
- « remplacer » (--force) ne vaut que pour le 1er chapitre : manga-fetch n'ecrase jamais les suivants.
Rejouable : python patch_capture_serie.py <chemin du proxy>.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if '"serie": serie' in s:
    print("deja patche")
    sys.exit(0)


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


rep('''def manga_fetch_capture(tab_url, titre, chapitre, force=False, page1=False):''',
    '''def manga_fetch_capture(tab_url, titre, chapitre, force=False, page1=False, suite=0, jusqua=""):''')

rep('''    if not re.match(r"^\\d{1,5}(\\.\\d{1,2})?$", chapitre or ""):
        return {"error": "numero de chapitre invalide"}
    onglets = manga_fetch_tabs()''',
    '''    if not re.match(r"^\\d{1,5}(\\.\\d{1,2})?$", chapitre or ""):
        return {"error": "numero de chapitre invalide"}
    try:
        suite = int(suite or 0)
    except (TypeError, ValueError):
        return {"error": "nombre de chapitres suivants invalide"}
    if not 0 <= suite <= 50:
        return {"error": "chapitres suivants : entre 0 et 50"}
    jusqua = str(jusqua or "").strip().replace(",", ".")
    if jusqua and not re.match(r"^\\d{1,5}(\\.\\d{1,2})?$", jusqua):
        return {"error": "« jusqu'au chapitre » invalide"}
    if jusqua and float(jusqua) <= float(chapitre):
        return {"error": "« jusqu'au chapitre » doit etre apres le chapitre de depart"}
    onglets = manga_fetch_tabs()''')

rep('''    if page1: cmd.append("--page-1")
    os.makedirs(os.path.dirname(MF_RUNLOG), exist_ok=True)''',
    '''    if page1: cmd.append("--page-1")
    if jusqua: cmd += ["--jusqua", jusqua]                  # Manga Studio v2.3.0 : plusieurs chapitres
    elif suite: cmd += ["--suite", str(suite)]
    os.makedirs(os.path.dirname(MF_RUNLOG), exist_ok=True)''')

rep('''                  debut=time.time(), titre=titre, chapitre=chapitre)
    return {"ok": True}''',
    '''                  debut=time.time(), titre=titre, chapitre=chapitre, suite=suite, jusqua=jusqua)
    return {"ok": True}''')

rep('''    pages, derniere = 0, ""
    try:
        with open(MF_EVENTS, "rb") as f:
            f.seek(_FETCH["offset"])
            for ligne in f.read().decode("utf-8", "replace").splitlines():
                if "[page]" in ligne: pages += 1
                if ligne.strip(): derniere = ligne.strip()[20:160]
    except OSError: pass
    dossier = None
    m = re.search(r"OK : \\d+(?:/\\d+)? pages -> (.+)", sortie)
    if m:
        full = os.path.normpath(m.group(1).strip())
        root = os.path.normpath(MANGA_SOURCES)
        if full.startswith(root + os.sep):
            dossier = full[len(root) + 1:].replace(os.sep, "/")
    lignes = [l for l in sortie.splitlines() if l.strip()]
    remplacement = None
    if code is not None and _FETCH.get("backup"):
        remplacement = _mf_fin_remplacement(code in (0, 3) and bool(dossier))
        _FETCH["remplacement"] = remplacement''',
    '''    pages, derniere = 0, ""
    try:
        with open(MF_EVENTS, "rb") as f:
            f.seek(_FETCH["offset"])
            for ligne in f.read().decode("utf-8", "replace").splitlines():
                if "[capture] d" in ligne and "marrage" in ligne: pages = 0   # v2.3.0 : pages du chapitre EN COURS
                if "[page]" in ligne: pages += 1
                if ligne.strip(): derniere = ligne.strip()[20:160]
    except OSError: pass
    dossiers = []
    root = os.path.normpath(MANGA_SOURCES)
    for m in re.finditer(r"OK : \\d+(?:/\\d+)? pages -> (.+)", sortie):
        full = os.path.normpath(m.group(1).strip())
        if full.startswith(root + os.sep):
            dossiers.append(full[len(root) + 1:].replace(os.sep, "/"))
    dossier = dossiers[-1] if dossiers else None
    chap_cours = _FETCH["chapitre"]
    for m in re.finditer(r"=== Chapitre suivant : (\\S+) ===", sortie):
        chap_cours = m.group(1)
    m = re.search(r"^S\\S+RIE : .*$", sortie, re.M)
    serie = m.group(0).strip() if m else None
    lignes = [l for l in sortie.splitlines() if l.strip()]
    remplacement = None
    if code is not None and _FETCH.get("backup"):
        dest1 = _FETCH.get("dest")
        remplacement = _mf_fin_remplacement(code in (0, 3) and bool(dest1)
                                            and os.path.isfile(os.path.join(dest1, "manifest.json")))
        _FETCH["remplacement"] = remplacement''')

rep('''            "titre": _FETCH["titre"], "chapitre": _FETCH["chapitre"], "pages": pages, "derniere": derniere,
            "dossier": dossier, "sortie": lignes[-12:], "duree_s": round(time.time() - _FETCH["debut"], 1)}''',
    '''            "titre": _FETCH["titre"], "chapitre": chap_cours, "chapitre_depart": _FETCH["chapitre"],
            "pages": pages, "derniere": derniere, "dossier": dossier, "dossiers": dossiers, "serie": serie,
            "suite": _FETCH.get("suite") or 0, "jusqua": _FETCH.get("jusqua") or "",
            "sortie": lignes[-12:], "duree_s": round(time.time() - _FETCH["debut"], 1)}''')

rep('''                                                    str(data.get("chapter") or ""), bool(data.get("force")),
                                                    bool(data.get("page1"))))''',
    '''                                                    str(data.get("chapter") or ""), bool(data.get("force")),
                                                    bool(data.get("page1")), data.get("suite") or 0,
                                                    str(data.get("jusqua") or "")))''')

open(p, "w", encoding="utf-8").write(s)
print("ok")
