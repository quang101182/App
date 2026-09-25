# -*- coding: utf-8 -*-
"""Patch du proxy 8190 : ARRETER une capture (Manga Studio v2.65.0, maquette_arret_v1 validee par Quang le 25/09/2026 22h48).

POST /manga/fetch_arret {quand}
- « apres » (capture en SERIE) : un fichier-drapeau (arret_demande.json, a cote du journal de manga-fetch) que manga-fetch >= 0.7.6
  lit ENTRE deux chapitres -- la ou il s'arrete deja quand le site n'a plus de suite. Aucun chapitre a moitie.
- « annuler » : retire le drapeau.
- « maintenant » : fin du processus (arbre entier). Le chapitre a moitie part a la CORBEILLE -- sauf s'il remplacait un ancien
  chapitre : l'ancien est alors RESTAURE par _mf_fin_remplacement, comme apres un echec.
Le BILAN (v2.50.0) dit « arretee a ta demande » et porte la reprise (chapitre + adresse) : le circuit « 🔗 Ouvrir / ▶ Reprendre »
existant sert tel quel. La ligne d'activite porte « arret: apres » tant que le drapeau est pose.
Rejouable : python patch_arret.py <chemin du proxy>.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "v2.65.0 : arret" in s:
    print("deja patche")
    sys.exit(0)


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


rep('''def _mf_fin_remplacement(reussi):''', '''def _mf_drapeau():                                   # v2.65.0 : arret -- a cote du journal de manga-fetch (DATA_DIR)
    return os.path.join(os.path.dirname(MF_EVENTS), "arret_demande.json")


def manga_fetch_arret(data):
    """v2.65.0 : arret d'une capture -- « apres » (ce chapitre), « maintenant », « annuler »."""
    quand = (data or {}).get("quand") or ""
    p, f = _FETCH["proc"], _mf_drapeau()
    en_cours = p is not None and p.poll() is None
    if quand == "annuler":
        try: os.remove(f)
        except OSError: pass
        return {"ok": True, "arret": None}
    if not en_cours:
        return {"error": "aucune capture en cours"}
    if quand == "apres":
        if not (_FETCH.get("suite") or _FETCH.get("jusqua")):
            return {"error": "capture d'un seul chapitre : utilise « Arrêter maintenant »"}
        with open(f, "w", encoding="utf-8") as fh:
            json.dump({"quand": "apres", "t": time.time()}, fh)
        return {"ok": True, "arret": "apres"}
    if quand == "maintenant":
        st = manga_fetch_status()
        _FETCH["arret_maintenant"] = str(st.get("chapitre") or _FETCH["chapitre"])
        try: os.remove(f)
        except OSError: pass
        subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try: p.wait(timeout=20)
        except Exception: pass
        return {"ok": True, "arret": "maintenant", "chapitre": _FETCH["arret_maintenant"]}
    return {"error": "quand : apres | maintenant | annuler"}


def _mf_fin_remplacement(reussi):''')
# chaque nouvelle capture repart sans arret en attente
rep('''    _FETCH.update(backup=None, dest=None, remplacement=None)''',
    '''    _FETCH.update(backup=None, dest=None, remplacement=None, arret_maintenant=None)   # v2.65.0 : arret
    try: os.remove(_mf_drapeau())
    except OSError: pass''')
# bilan : l'arret demande
rep('''        if m3: echec = m3.group(1)''', '''        if m3: echec = m3.group(1)
        demande = "arrêtée à ta demande" in arret                          # v2.65.0 : « ⏹ apres ce chapitre »
        m5 = re.search(r"arrêtée à ta demande après le ch\\. \\S+ — reprise au ch\\. (\\S+)", arret)
        if m5: echec = m5.group(1)
        am = _FETCH.get("arret_maintenant") if _FETCH.get("proc") is p else None
        if am:                                                             # « ✖ maintenant » : le processus a ete arrete
            demande = True
            commences = [meta["chapitre"]] + re.findall(r"=== Chapitre suivant : (\\S+) ===", sortie)
            faits = commences[:commences.index(am)] if am in commences else commences[:-1]
            arret = "arrêtée à ta demande pendant le ch. %s — reprise au ch. %s" % (am, am)
            tenu, echec = False, am
            part = _mf_dest(meta["titre"], am)
            if (os.path.isdir(part) and not os.path.isfile(os.path.join(part, "manifest.json"))
                    and os.path.normpath(part) != os.path.normpath(_FETCH.get("dest") or "")):
                try:
                    os.makedirs(MANGA_CORBEILLE, exist_ok=True)
                    shutil.move(part, os.path.join(MANGA_CORBEILLE, time.strftime("%Y%m%d-%H%M%S") + "_"
                                                   + os.path.relpath(part, MANGA_SOURCES).replace(os.sep, "__") + "__arret"))
                except OSError:
                    pass''')
rep('''               "faits": faits, "tenu": tenu, "reprise": reprise,''',
    '''               "faits": faits, "tenu": tenu, "reprise": reprise, "demande": bool(demande),''')
# activite : l'arret en attente
rep('''        it.update(fait=faits, total=total, etape="ch. %s" % (fs.get("chapitre") or "?"), pages=fs.get("pages"))''',
    '''        it.update(fait=faits, total=total, etape="ch. %s" % (fs.get("chapitre") or "?"), pages=fs.get("pages"))
        it["arret"] = "apres" if os.path.exists(_mf_drapeau()) else None      # v2.65.0''')
# statut : l'arret « maintenant » (le panneau de capture dit « arretee a ta demande », pas « echec »)
rep('''            "sortie": lignes[-12:], "duree_s": round(time.time() - _FETCH["debut"], 1)}''',
    '''            "sortie": lignes[-12:], "duree_s": round(time.time() - _FETCH["debut"], 1),
            "arret_demande": _FETCH.get("arret_maintenant")}                          # v2.65.0''')
rep('''            elif self.path == "/manga/fetch_capture":''', '''            elif self.path == "/manga/fetch_arret":            # Manga Studio v2.65.0
                self._json(200, manga_fetch_arret(data))
            elif self.path == "/manga/fetch_capture":''')
open(p, "w", encoding="utf-8").write(s)
print("patche")
