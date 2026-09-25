# -*- coding: utf-8 -*-
"""Patch du proxy : BILAN PERSISTANT de chaque capture + route de lecture (Manga Studio v2.50.0, 25/09/2026).

Constat (Quang 25/09 11h19) : une capture de 40 chapitres s'est arretee au 22e (verification Cloudflare au ch.23, a 02h57)
sans AUCUN signal. Le bilan n'existait qu'en MEMOIRE du serveur (_FETCH) et dans le panneau de capture s'il etait ouvert :
une relance du serveur l'effacait. Desormais un veilleur attend la fin du processus et ecrit
<sources>/_capture_derniere.json : titre, fin, bilan « SERIE », arret, tenu (le but est-il atteint ?), et de quoi REPRENDRE
(chapitre en echec -- toujours depuis son DEBUT --, borne ou nombre restant, options, adresse de l'onglet sans jeton Cloudflare).
GET /manga/capture_derniere -> ce fichier ({} s'il n'existe pas).
Rejouable : python patch_capture_bilan.py <chemin du proxy>. Ancres verifiees ; fins de ligne du fichier conservees.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8", newline="").read()
NL = "\r\n" if "\r\n" in s else "\n"
if "_capture_derniere.json" in s:
    print("deja patche"); sys.exit(0)

# 1. le veilleur, insere juste avant manga_fetch_capture
A1 = "def manga_fetch_capture(tab_url, titre, chapitre, force=False, page1=False, suite=0, jusqua=\"\", entiers=False):" + NL
F = r'''def _mf_bilan_ecrire(p, meta):
    """Manga Studio v2.50.0 : attend la fin de la capture et ecrit son BILAN sur disque (survit a une relance du serveur)."""
    try:
        code = p.wait()
        time.sleep(0.5)
        try:
            with open(MF_RUNLOG, encoding="utf-8", errors="replace") as f: sortie = f.read()
        except OSError: sortie = ""
        evts = ""
        try:
            with open(MF_EVENTS, "rb") as f:
                f.seek(meta["offset"]); evts = f.read().decode("utf-8", "replace")
        except OSError: pass
        m = re.search(r"^S\S+RIE : .*$", sortie, re.M)
        serie = m.group(0).strip() if m else ""
        arret = serie.split(" — arrêt : ", 1)[1].strip() if " — arrêt : " in serie else ""
        faits = []
        m2 = re.match(r"^S\S+RIE : \d+ chapitre\(s\) : ([^—]+)", serie)
        if m2: faits = [x.strip() for x in m2.group(1).split(",") if x.strip()]
        premier_ko = bool(re.match(r"^S\S+RIE : arrêt", serie))
        en_serie = bool(meta["suite"] or meta["jusqua"])
        if en_serie:
            tenu = code in (0, 3) and not premier_ko and (arret.endswith(": fait") or (bool(meta["jusqua"]) and "dépasse la borne" in arret))
        else:
            tenu = code in (0, 3)
        # le chapitre a reprendre : celui qui a ECHOUE (depuis son debut), jamais le milieu d'une page
        echec = None
        m3 = re.search(r"le chapitre (\S+) a échoué", arret)
        if m3: echec = m3.group(1)
        elif premier_ko or (not en_serie and not tenu): echec = meta["chapitre"]
        url = ""
        for m4 in re.finditer(r"\[série\] chapitre suivant (\S+) onglet=(\S+)", evts):
            if m4.group(1) == echec: url = m4.group(2)
        if not url and echec == meta["chapitre"]: url = meta["tab"]
        url = re.sub(r"[?&]__cf_chl_[a-z_]+=[^&#]*", "", url).rstrip("?&")
        reprise = None
        if echec:
            reprise = {"chapitre": echec, "url": url, "page1": meta["page1"], "entiers": meta["entiers"]}
            if meta["jusqua"]: reprise["jusqua"] = meta["jusqua"]
            elif meta["suite"]: reprise["suite"] = max(0, meta["suite"] + 1 - len(faits) - 1)
        doc = {"fin": time.time(), "debut": meta["debut"], "titre": meta["titre"], "chapitre_depart": meta["chapitre"],
               "suite": meta["suite"], "jusqua": meta["jusqua"], "code": code, "serie": serie, "arret": arret,
               "faits": faits, "tenu": tenu, "reprise": reprise, "derniere_ligne": (sortie.strip().splitlines() or [""])[-1][:200]}
        tmp = os.path.join(MANGA_SOURCES, "_capture_derniere.json.tmp")
        with open(tmp, "w", encoding="utf-8") as f: json.dump(doc, f, ensure_ascii=False, indent=1)
        os.replace(tmp, os.path.join(MANGA_SOURCES, "_capture_derniere.json"))
    except Exception as e:
        print("[capture] bilan impossible :", str(e)[:200], flush=True)


def manga_capture_derniere():
    try:
        with open(os.path.join(MANGA_SOURCES, "_capture_derniere.json"), encoding="utf-8") as f: return json.load(f)
    except (OSError, ValueError): return {}


'''.replace("\n", NL)
B1 = F + A1

# 2. le veilleur demarre avec la capture
A2 = "                  debut=time.time(), titre=titre, chapitre=chapitre, suite=suite, jusqua=jusqua)" + NL + "    return {\"ok\": True}" + NL
B2 = ("                  debut=time.time(), titre=titre, chapitre=chapitre, suite=suite, jusqua=jusqua)" + NL
      + "    threading.Thread(target=_mf_bilan_ecrire, daemon=True, args=(_FETCH[\"proc\"], {    # v2.50.0 : bilan persistant" + NL
      + "        \"offset\": _FETCH[\"offset\"], \"debut\": _FETCH[\"debut\"], \"titre\": titre, \"chapitre\": chapitre, \"suite\": suite," + NL
      + "        \"jusqua\": jusqua, \"tab\": tab_url, \"page1\": bool(page1), \"entiers\": bool(entiers)})).start()" + NL
      + "    return {\"ok\": True}" + NL)

# 3. la route
A3 = "        elif self.path.split(\"?\", 1)[0] == \"/manga/fetch_status\":" + NL
B3 = ("        elif self.path.split(\"?\", 1)[0] == \"/manga/capture_derniere\":     # Manga Studio v2.50.0" + NL
      + "            self._json(200, manga_capture_derniere())" + NL + A3)

for a in (A1, A2, A3):
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
s = s.replace(A1, B1, 1).replace(A2, B2, 1).replace(A3, B3, 1)
open(p, "w", encoding="utf-8", newline="").write(s)
print("ok")
