# -*- coding: utf-8 -*-
"""Patch du proxy : « JUSQU'AU DERNIER PARU » + securites de serie (Manga Studio v2.67.0 / manga-fetch 0.8.0,
maquette_dernier_paru_v1 validee par Quang le 25/09/2026 23h49 ; ROADMAP § 4-quindecies, etape E4).

- POST /manga/fetch_capture accepte `dernier_paru: true` -> manga-fetch `--jusqua-fin` (aucune borne, filet de 300).
- Plafonds (Quang 23h51 : « 300 partout ») : `suite` <= 300 (au lieu de 50) ; « jusqu'au ch. » : ecart <= 300.
- Ligne d'activite : en mode dernier paru, le total est INCONNU -> `fait` = chapitres captures, `total` None, `dernier_paru` true.
  ATTENTION : PAS « fin » -- le bilan a DEJA un champ `fin` (heure de fin, cle de « deja vu » de l'app).
- « Apres ce chapitre » accepte aussi le mode fin.
- Bilan : `dernier_paru`, `deja_la` (ligne « DEJA LA : » de manga-fetch 0.8.0) ; tenu (mode fin) = le site n'a plus de suite ;
  un « arret de securite … — reprise au ch. N » porte la reprise (chapitre + adresse) ; la reprise garde le mode fin.
Rejouable : python patch_dernier_paru.py <chemin du proxy>.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "v2.67.0 : dernier paru" in s:
    print("deja patche")
    sys.exit(0)


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


# --- ligne d'activite
rep('''        suite, jusqua = int(fs.get("suite") or 0), str(fs.get("jusqua") or "")
        if not (suite or jusqua):
            return it
        dep = float(fs.get("chapitre_depart"))''', '''        suite, jusqua = int(fs.get("suite") or 0), str(fs.get("jusqua") or "")
        if fs.get("dernier_paru"):                                                   # v2.67.0 : dernier paru -- total inconnu
            it.update(fait=len(fs.get("dossiers") or []), total=None, dernier_paru=True, etape="ch. %s" % (fs.get("chapitre") or "?"),
                      pages=fs.get("pages"))
            it["arret"] = "apres" if os.path.exists(_mf_drapeau()) else None
            return it
        if not (suite or jusqua):
            return it
        dep = float(fs.get("chapitre_depart"))''')

# --- « apres ce chapitre »
rep('''        if not (_FETCH.get("suite") or _FETCH.get("jusqua")):
            return {"error": "capture d'un seul chapitre : utilise « Arrêter maintenant »"}''',
    '''        if not (_FETCH.get("suite") or _FETCH.get("jusqua") or _FETCH.get("dernier_paru")):
            return {"error": "capture d'un seul chapitre : utilise « Arrêter maintenant »"}''')

# --- bilan
rep('''        premier_ko = bool(re.match(r"^S\\S+RIE : arrêt", serie))
        en_serie = bool(meta["suite"] or meta["jusqua"])
        if en_serie:
            tenu = code in (0, 3) and not premier_ko and (arret.endswith(": fait") or (bool(meta["jusqua"]) and "dépasse la borne" in arret))''',
    '''        premier_ko = bool(re.match(r"^S\\S+RIE : arrêt", serie))
        m6 = re.search(r"^DEJA LA : (.+)$", sortie, re.M)                 # v2.67.0 : dernier paru -- deja la
        deja_la = [x.strip() for x in m6.group(1).split(",") if x.strip()] if m6 else []
        en_serie = bool(meta["suite"] or meta["jusqua"] or meta.get("dernier_paru"))
        if meta.get("dernier_paru"):
            tenu = code in (0, 3) and not premier_ko and "aucun chapitre après" in arret   # MangaDex : « MangaDex : aucun… »
        elif en_serie:
            tenu = code in (0, 3) and not premier_ko and (arret.endswith(": fait") or (bool(meta["jusqua"]) and "dépasse la borne" in arret))''')
rep('''        if m5: echec = m5.group(1)
        am = _FETCH.get("arret_maintenant")''',
    '''        if m5: echec = m5.group(1)
        m7 = re.search(r"arrêt de sécurité : .* — reprise au ch\\. (\\S+)$", arret)
        if m7: echec = m7.group(1)
        am = _FETCH.get("arret_maintenant")''')
rep('''            if meta["jusqua"]: reprise["jusqua"] = meta["jusqua"]
            elif meta["suite"]:''', '''            if meta.get("dernier_paru"): reprise["dernier_paru"] = True
            elif meta["jusqua"]: reprise["jusqua"] = meta["jusqua"]
            elif meta["suite"]:''')
rep('''               "suite": meta["suite"], "jusqua": meta["jusqua"], "code": code, "serie": serie, "arret": arret,
               "faits": faits,''', '''               "suite": meta["suite"], "jusqua": meta["jusqua"], "dernier_paru": bool(meta.get("dernier_paru")), "deja_la": deja_la,
               "code": code, "serie": serie, "arret": arret,
               "faits": faits,''')

# --- lancement
rep('''def manga_fetch_capture(tab_url, titre, chapitre, force=False, page1=False, suite=0, jusqua="", entiers=False):''',
    '''def manga_fetch_capture(tab_url, titre, chapitre, force=False, page1=False, suite=0, jusqua="", entiers=False, dernier_paru=False):''')
rep('''    if not 0 <= suite <= 50:
        return {"error": "chapitres suivants : entre 0 et 50"}''', '''    if not 0 <= suite <= 300:                                          # v2.67.0 : 50 -> 300 (Quang 25/09 23h51)
        return {"error": "chapitres suivants : entre 0 et 300"}''')
rep('''    if jusqua and float(jusqua) <= float(chapitre):
        return {"error": "« jusqu'au chapitre » doit etre apres le chapitre de depart"}''',
    '''    if jusqua and float(jusqua) <= float(chapitre):
        return {"error": "« jusqu'au chapitre » doit etre apres le chapitre de depart"}
    if jusqua and float(jusqua) - float(chapitre) > 300:
        return {"error": "« jusqu'au chapitre » : 300 chapitres d'ecart au plus par capture"}
    dernier_paru = bool(dernier_paru) and not jusqua and not suite                       # v2.67.0 : dernier paru''')
rep('''    if jusqua: cmd += ["--jusqua", jusqua]                  # Manga Studio v2.3.0 : plusieurs chapitres
    elif suite: cmd += ["--suite", str(suite)]
    if entiers and (jusqua or suite): cmd.append("--sans-intermediaires")''',
    '''    if dernier_paru: cmd.append("--jusqua-fin")                      # v2.67.0 : dernier paru
    elif jusqua: cmd += ["--jusqua", jusqua]                  # Manga Studio v2.3.0 : plusieurs chapitres
    elif suite: cmd += ["--suite", str(suite)]
    if entiers and (jusqua or suite or dernier_paru): cmd.append("--sans-intermediaires")''')
rep('''                  debut=time.time(), titre=titre, chapitre=chapitre, suite=suite, jusqua=jusqua)''',
    '''                  debut=time.time(), titre=titre, chapitre=chapitre, suite=suite, jusqua=jusqua, dernier_paru=dernier_paru)''')
rep('''        "jusqua": jusqua, "tab": tab_url, "page1": bool(page1), "entiers": bool(entiers)})).start()''',
    '''        "jusqua": jusqua, "dernier_paru": dernier_paru, "tab": tab_url, "page1": bool(page1), "entiers": bool(entiers)})).start()''')

# --- statut
rep('''            "suite": _FETCH.get("suite") or 0, "jusqua": _FETCH.get("jusqua") or "",
            "sortie": lignes[-12:],''', '''            "suite": _FETCH.get("suite") or 0, "jusqua": _FETCH.get("jusqua") or "", "dernier_paru": bool(_FETCH.get("dernier_paru")),
            "sortie": lignes[-12:],''')

# --- route
rep('''                                                    str(data.get("jusqua") or ""), bool(data.get("entiers"))))''',
    '''                                                    str(data.get("jusqua") or ""), bool(data.get("entiers")),
                                                    bool(data.get("dernier_paru"))))       # v2.67.0 : dernier paru''')

open(p, "w", encoding="utf-8").write(s)
print("patche")
