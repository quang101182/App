# -*- coding: utf-8 -*-
"""Patch du proxy 8190 : musique PAR SERIE + PAR CHAPITRE, jusqu'a 5 morceaux enchaines (Manga Studio v1.90.0, 22/09/2026).

Demandes de Quang (05h26-05h32) :
- la musique se definit pour tout le manga OU par chapitre ; un chapitre reprend d'office celle de la serie ;
- jusqu'a 5 morceaux, lus dans un ordre aleatoire et enchaines (un chapitre de 62 p. ~ 12 min = 4-6 morceaux) ;
- DEUX suppressions differentes : l'enlever d'un chapitre (decocher) / la supprimer de la base (corbeille) ;
- un morceau rapatrie prend le NOM DU MANGA, numerote 1, 2, 3... sans jamais REUTILISER un numero supprime
  (un compteur est garde : « Claymore 3 » supprime ne renait jamais sous un autre son).
Stockage : sources/<serie>/musique/choix.json {"serie": [noms], "compteur": N}  (ancien format {"nom": X} relu)
           sources/<serie>/<chapitre>/musique.json {"mode": "serie"|"propre", "noms": [...]}
Routes : GET /manga/musiques?serie=&d=  ·  POST /manga/musique_selection {serie, d?, mode?, noms}
         (import / suppr / choix / depuis_gs gardent leurs routes, avec le nouveau comportement).
Remplace le bloc manga_musiques ... manga_musique_suppr. Rejouable. Suppose patch_musique(_gs).py appliques.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "def manga_musique_selection(" in s:
    print("deja patche")
    sys.exit(0)

debut, fin = "def manga_musiques(serie):\n", "def manga_musique_depuis_gs(data):"
if s.count(debut) != 1 or s.count(fin) != 1 or s.index(debut) > s.index(fin):
    raise SystemExit("ancres du bloc musique introuvables")
NOUVEAU = '''MUS_MAX = 5                                      # v1.90.0 : jusqu'a 5 morceaux enchaines par chapitre
_MUS_DUR = {}                                    # (chemin, taille, mtime) -> duree (ffprobe une seule fois)


def _mus_titre(serie):
    """Titre AFFICHE de la serie (manifest de ses chapitres, mis a jour au renommage), sinon le dossier."""
    sd, _ = _mus_dir(serie)
    for ch in sorted(os.listdir(sd)) if sd else []:
        try:
            with open(os.path.join(sd, ch, "manifest.json"), encoding="utf-8") as f:
                t = (json.load(f).get("title") or "").strip()
            if t:
                return _mus_nom(t) or serie
        except Exception:
            continue
    return serie


def _mus_etat(md):
    try:
        with open(os.path.join(md, "choix.json"), encoding="utf-8") as f:
            e = json.load(f)
    except Exception:
        e = {}
    if "serie" not in e:                         # ancien format (v1.85) : {"nom": X}
        e = {"serie": [e["nom"]] if e.get("nom") else [], "compteur": 0}
    return e


def _mus_etat_ecrit(md, e):
    os.makedirs(md, exist_ok=True)
    tmp = os.path.join(md, "choix.json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(e, f, ensure_ascii=False)
    os.replace(tmp, os.path.join(md, "choix.json"))


def _mus_chap(serie, d):
    """Dossier du chapitre, s'il appartient bien a cette serie."""
    d = (d or "").strip("/")
    if not d or d.split("/")[0] != (serie or "").strip("/"):
        return None
    full = _manga_src_safe(d)
    return full if full and os.path.isfile(os.path.join(full, "manifest.json")) else None


def _mus_chap_lit(cd):
    try:
        with open(os.path.join(cd, "musique.json"), encoding="utf-8") as f:
            c = json.load(f)
        return {"mode": "propre" if c.get("mode") == "propre" else "serie", "noms": list(c.get("noms") or [])}
    except Exception:
        return {"mode": "serie", "noms": []}


def manga_musiques(serie, d=""):
    sd, md = _mus_dir(serie)
    if not sd:
        return None
    items = []
    if os.path.isdir(md):
        for f in sorted(os.listdir(md), key=str.lower):
            if f.lower().endswith(_MUS_EXT):
                full = os.path.join(md, f)
                st = os.stat(full)
                cle = (full, st.st_size, int(st.st_mtime))
                if cle not in _MUS_DUR:
                    _MUS_DUR[cle] = _duree_s(full)
                items.append({"nom": os.path.splitext(f)[0], "fichier": serie.strip("/") + "/musique/" + f,
                              "taille": st.st_size, "dur": round(_MUS_DUR[cle] or 0, 1)})
    noms = {x["nom"] for x in items}
    sel = [n for n in _mus_etat(md)["serie"] if n in noms][:MUS_MAX]
    r = {"items": items, "serie_sel": sel, "max": MUS_MAX}
    cd = _mus_chap(serie, d)
    if cd:
        c = _mus_chap_lit(cd)
        c["noms"] = [n for n in c["noms"] if n in noms][:MUS_MAX]
        r["chapitre"] = c
        r["effectif"] = c["noms"] if c["mode"] == "propre" else sel
    else:
        r["effectif"] = sel
    r["choix"] = r["effectif"][0] if r["effectif"] else ""      # compat v1.85 (un seul morceau)
    return r


def manga_musique_import(data):
    sd, md = _mus_dir(data.get("serie"))
    if not sd:
        return {"error": "serie introuvable"}
    try:
        b = base64.b64decode((data.get("data") or "").split(",")[-1])
    except Exception:
        return {"error": "fichier illisible"}
    ext = _mus_ext(b[:16])
    if not ext or len(b) < 10000:
        return {"error": "ce n'est pas un fichier audio (mp3, wav, ogg, m4a, flac)"}
    os.makedirs(md, exist_ok=True)
    e = _mus_etat(md)
    titre = _mus_titre(data.get("serie"))
    # « Titre N » : N = au-dela du plus grand numero EXISTANT et du compteur (jamais un numero supprime reutilise)
    pris = [int(m.group(1)) for m in (re.match(re.escape(titre) + r" (\\d+)$", os.path.splitext(f)[0])
                                       for f in os.listdir(md)) if m]
    k = max([e.get("compteur") or 0] + pris) + 1
    while any(os.path.isfile(os.path.join(md, "%s %d%s" % (titre, k, x))) for x in _MUS_EXT):
        k += 1
    nom = "%s %d" % (titre, k)
    with open(os.path.join(md, nom + ext), "wb") as f:
        f.write(b)
    e["compteur"] = k
    if len(e["serie"]) < MUS_MAX:                # il rejoint la selection de la serie tant qu'il y a de la place
        e["serie"].append(nom)
    _mus_etat_ecrit(md, e)
    return {"ok": True, "nom": nom}


def manga_musique_selection(data):
    sd, md = _mus_dir(data.get("serie"))
    if not sd:
        return {"error": "serie introuvable"}
    r = manga_musiques(data.get("serie"))
    existants = {x["nom"] for x in r["items"]}
    noms = [n for n in dict.fromkeys(data.get("noms") or [])]
    if any(n not in existants for n in noms):
        return {"error": "morceau introuvable"}
    if len(noms) > MUS_MAX:
        return {"error": "%d morceaux au plus" % MUS_MAX}
    if data.get("d"):
        cd = _mus_chap(data.get("serie"), data.get("d"))
        if not cd:
            return {"error": "chapitre introuvable"}
        mode = "propre" if data.get("mode") == "propre" else "serie"
        with open(os.path.join(cd, "musique.json"), "w", encoding="utf-8") as f:
            json.dump({"mode": mode, "noms": noms}, f, ensure_ascii=False)
    else:
        e = _mus_etat(md)
        e["serie"] = noms
        _mus_etat_ecrit(md, e)
    return dict(manga_musiques(data.get("serie"), data.get("d") or ""), ok=True)


def manga_musique_choix(data):                   # compat v1.85 : un seul morceau pour la serie
    return manga_musique_selection({"serie": data.get("serie"), "noms": [data["nom"]] if data.get("nom") else []})


def manga_musique_suppr(data):
    """Supprimer de la BASE : corbeille + retire de la selection de la serie ET de tous ses chapitres."""
    sd, md = _mus_dir(data.get("serie"))
    if not sd:
        return {"error": "serie introuvable"}
    nom = data.get("nom")
    it = [x for x in manga_musiques(data.get("serie"))["items"] if x["nom"] == nom]
    if not it:
        return {"error": "morceau introuvable"}
    f = os.path.basename(it[0]["fichier"])
    os.makedirs(MANGA_CORBEILLE, exist_ok=True)
    dest = os.path.join(MANGA_CORBEILLE, time.strftime("%Y%m%d-%H%M%S") + "_" + data["serie"].strip("/") + "__musique__" + f)
    shutil.move(os.path.join(md, f), dest)
    e = _mus_etat(md)
    e["serie"] = [n for n in e["serie"] if n != nom]
    _mus_etat_ecrit(md, e)
    for ch in os.listdir(sd):
        mj = os.path.join(sd, ch, "musique.json")
        if os.path.isfile(mj):
            c = _mus_chap_lit(os.path.join(sd, ch))
            if nom in c["noms"]:
                c["noms"] = [n for n in c["noms"] if n != nom]
                with open(mj, "w", encoding="utf-8") as fh:
                    json.dump(c, fh, ensure_ascii=False)
    return {"ok": True, "corbeille": os.path.relpath(dest, MANGA_SOURCES)}


'''
i, j = s.index(debut), s.index(fin)
s = s[:i] + NOUVEAU + s[j:]


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


rep('''            _r = manga_musiques((parse_qs(urlparse(self.path).query).get("serie") or [""])[0])''',
    '''            _q = parse_qs(urlparse(self.path).query)
            _r = manga_musiques((_q.get("serie") or [""])[0], (_q.get("d") or [""])[0])''')
rep('''            elif self.path == "/manga/musique_choix":''',
    '''            elif self.path == "/manga/musique_selection":      # Manga Studio v1.90.0
                self._json(200, manga_musique_selection(data))
            elif self.path == "/manga/musique_choix":''')
open(p, "w", encoding="utf-8").write(s)
print("patch musique selection OK")
