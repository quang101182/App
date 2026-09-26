# -*- coding: utf-8 -*-
"""Manga Studio v2.81.0 -- mode Dialogues, 3e patch serveur (ROADMAP 4-septdecies D7) : /manga/dialogues_lancer accepte
l'action « video » (dialogues.py video -> <chap>/dialogues/video/dialogues.mp4, servie par /manga/video_file existant).
Suppose patch_dialogues.py. Rejouable : python patch_dialogues_3.py <chemin du proxy>"""
import io, sys

P = sys.argv[1]
s = io.open(P, encoding="utf-8", newline="").read()
if "MANGA_DIALOGUES =" not in s:
    print("ERREUR : appliquer d'abord patch_dialogues.py"); sys.exit(1)
if 'action not in ("preparer", "voix", "video")' in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", NL), b.replace("\n", NL)
    assert s.count(a) == 1, ("ancre", s.count(a), a[:80])
    s = s.replace(a, b)


rep('''def manga_dialogues_lancer(d, action, pages=""):
    if action not in ("preparer", "voix"):''', '''def manga_dialogues_lancer(d, action, pages=""):
    if action not in ("preparer", "voix", "video"):          # v2.81.0 D7 : la video des dialogues''')
rep('''    if action == "voix" and not os.path.isfile(os.path.join(dd, "dialogues.json")):''',
    '''    if action in ("voix", "video") and not os.path.isfile(os.path.join(dd, "dialogues.json")):''')
rep('''    cmd = [MANGA_PY, MANGA_DIALOGUES, action, d] + (["--pages", pages] if pages else [])''',
    '''    cmd = [MANGA_PY, MANGA_DIALOGUES, action, d] + (["--pages", pages] if pages and action != "video" else [])''')
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("proxy patche (3)")
