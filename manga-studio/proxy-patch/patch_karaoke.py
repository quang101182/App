# -*- coding: utf-8 -*-
"""Patch du proxy 8190 : karaoke d'une narration (Manga Studio v1.86.0, 22/09/2026, etape 2-bis).

POST /manga/karaoke {d, tag} -> lance scripts/karaoke_mots.py EN FOND (temps de chaque mot -> narration.json) ;
/manga/narrations expose karaoke_en_cours par narration (le resultat, lui, est dans stats.karaoke).
Rejouable : python patch_karaoke.py <chemin du proxy>. Suppose patch_musique.py applique.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "def manga_karaoke(" in s:
    print("deja patche")
    sys.exit(0)


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


rep('''# --- Musique de fond par serie (Manga Studio v1.85.0) -----------------------------------''',
    '''# --- Karaoke d'une narration (Manga Studio v1.86.0) ------------------------------------
MANGA_KARAOKE = os.path.join(MANGA_ROOT, "scripts", "karaoke_mots.py")
_KAR_JOBS = {}                                   # (chapitre, tag) -> Popen


def _kar_vivant(d, tag):
    p = _KAR_JOBS.get((d.strip("/"), tag))
    return bool(p and p.poll() is None)


def manga_karaoke(d, tag):
    td = _narr_dir(d, tag)
    if not tag or not td or not os.path.isfile(os.path.join(td, "narration.json")):
        return {"error": "narration introuvable"}
    if not os.path.isfile(MANGA_PY) or not os.path.isfile(MANGA_KARAOKE):
        return {"error": "venv kohya ou karaoke_mots.py introuvable"}
    if _narr_job_vivant(d, tag):
        return {"error": "la narration n'est pas finie"}
    if _kar_vivant(d, tag):
        return {"error": "le karaoke est deja en cours"}
    lg = open(os.path.join(td, "karaoke.log"), "w", encoding="utf-8")
    _KAR_JOBS[(d.strip("/"), tag)] = subprocess.Popen(
        [MANGA_PY, MANGA_KARAOKE, d.strip("/"), tag], stdout=lg, stderr=lg,
        cwd=os.path.dirname(MANGA_KARAOKE), creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return {"ok": True}


# --- Musique de fond par serie (Manga Studio v1.85.0) -----------------------------------''')

rep('''            it = {"tag": tag, "etat": "vide", "running": _narr_job_vivant(d, tag)}''',
    '''            it = {"tag": tag, "etat": "vide", "running": _narr_job_vivant(d, tag),
                  "karaoke_en_cours": _kar_vivant(d, tag)}                 # v1.86.0''')

rep('''            elif self.path == "/manga/musique_import":         # Manga Studio v1.85.0''',
    '''            elif self.path == "/manga/karaoke":                # Manga Studio v1.86.0
                self._json(200, manga_karaoke(data.get("d") or "", data.get("tag") or ""))
            elif self.path == "/manga/musique_import":         # Manga Studio v1.85.0''')

open(p, "w", encoding="utf-8").write(s)
print("patch karaoke OK")
