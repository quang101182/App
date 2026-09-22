# -*- coding: utf-8 -*-
"""Patch du proxy 8190 : prendre un morceau de la PLAYLIST de Generate Studio (Manga Studio v1.87.0, 22/09/2026).

POST /manga/musique_depuis_gs {serie, chemin: "gs/audio/<dossier>/audio.flac", nom}
  -> MP3 par mp3_depuis() (le MEME que la notification Telegram : cache _mp3cache/, fabrique s'il manque)
  -> copie dans sources/<serie>/musique/ par manga_musique_import (nommage, doublons, 1er = celui qui joue).
La LISTE n'a pas de route neuve : l'app lit /outputs_list + /audio_meta, comme la page de Generate Studio.
Generate Studio n'est pas touche : lecture seule de output/gs/audio/.
Rejouable : python patch_musique_gs.py <chemin du proxy>. Suppose patch_musique.py applique.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "def manga_musique_depuis_gs(" in s:
    print("deja patche")
    sys.exit(0)


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


rep('''# --- Traduction des dialogues d'un chapitre (Manga Studio v1.84.0) ---------------------''',
    '''def manga_musique_depuis_gs(data):                # Manga Studio v1.87.0
    rel = str(data.get("chemin") or "").replace("\\\\", "/").strip("/")
    if not rel.lower().startswith("gs/audio/") or "/_" in rel:
        return {"error": "ce n'est pas un morceau de la playlist"}
    root = os.path.normpath(OUT_ROOT)
    full = os.path.normpath(os.path.join(root, rel))
    if not full.startswith(root + os.sep) or not os.path.isfile(full):
        return {"error": "morceau introuvable"}
    try:
        mp3 = mp3_depuis(full)
    except Exception as e:
        return {"error": "conversion MP3 impossible : %s" % str(e)[:160]}
    with open(mp3, "rb") as f:
        b = f.read()
    nom = data.get("nom") or os.path.basename(os.path.dirname(full))
    return manga_musique_import({"serie": data.get("serie"), "nom": nom, "data": base64.b64encode(b).decode("ascii")})


# --- Traduction des dialogues d'un chapitre (Manga Studio v1.84.0) ---------------------''')

rep('''            elif self.path == "/manga/musique_import":         # Manga Studio v1.85.0''',
    '''            elif self.path == "/manga/musique_depuis_gs":      # Manga Studio v1.87.0
                self._json(200, manga_musique_depuis_gs(data))
            elif self.path == "/manga/musique_import":         # Manga Studio v1.85.0''')

open(p, "w", encoding="utf-8").write(s)
print("patch musique GS OK")
