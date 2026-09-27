# -*- coding: utf-8 -*-
"""Manga Studio v3.4.0 -- 15e patch serveur (27/09, musique de fond des Dialogues) : /manga/dialogues_lancer accepte
« musique » (bool) + « volume » (0-100) pour video / tout -> dialogues.py 1.24.0 --musique '{"noms": <musique EFFECTIVE du
chapitre (manga_musiques : celle de la serie ou la sienne)>, "volume": v}'. Sans musique ou sans morceau : rien ne change.
Suppose patch_dialogues_14. Rejouable."""
import io, sys

P = sys.argv[1]
s = io.open(P, encoding="utf-8", newline="").read()
if "def _dlg_musique_arg(" in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", NL), b.replace("\n", NL)
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %s" % (s.count(a), a[:70]))
    s = s.replace(a, b)


rep('''def manga_dialogues_lancer(d, action, pages="", traduire=False, sans_prep=False):''',
    '''def _dlg_musique_arg(d, volume):
    """v3.4.0 : la musique EFFECTIVE du chapitre (serie ou la sienne) -> argument --musique, ou [] s'il n'y en a pas."""
    try:
        m = manga_musiques(d.split("/")[0], d) or {}
        noms = [n for n in (m.get("effectif") or []) if isinstance(n, str)]
        v = max(0, min(100, int(float(volume if volume is not None else 25))))
    except Exception:
        return []
    return ["--musique", json.dumps({"noms": noms, "volume": v}, ensure_ascii=False)] if noms else []


def manga_dialogues_lancer(d, action, pages="", traduire=False, sans_prep=False, musique=False, volume=None):''')
rep('''+ (["--traduire"] if traduire and action in ("preparer", "tout") else []) + (["--sans-preparation"] if sans_prep and action == "tout" else [])''',
    '''+ (["--traduire"] if traduire and action in ("preparer", "tout") else []) + (["--sans-preparation"] if sans_prep and action == "tout" else []) \\
          + (_dlg_musique_arg(d, volume) if musique and action in ("video", "tout") else [])   # v3.4.0''')
rep('''                                                       data.get("sans_preparation") is True))   # v3.3.0''',
    '''                                                       data.get("sans_preparation") is True,   # v3.3.0
                                                       data.get("musique") is True, data.get("volume")))   # v3.4.0''')
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
