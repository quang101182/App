# -*- coding: utf-8 -*-
"""Patch du proxy 8190 : « ignorer les chapitres intermediaires (x.5) » pendant une capture en serie (Manga Studio v2.3.2).

Quang (22/09 14h47) : pas de 298.5 entre 298 et 299. POST /manga/fetch_capture accepte `entiers` (bool) et le relaie
a manga-fetch v0.4.1 (--sans-intermediaires). Suppose patch_capture_serie.py deja applique.
Rejouable : python patch_capture_entiers.py <chemin du proxy>.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "--sans-intermediaires" in s:
    print("deja patche")
    sys.exit(0)


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


rep('''def manga_fetch_capture(tab_url, titre, chapitre, force=False, page1=False, suite=0, jusqua=""):''',
    '''def manga_fetch_capture(tab_url, titre, chapitre, force=False, page1=False, suite=0, jusqua="", entiers=False):''')
rep('''    elif suite: cmd += ["--suite", str(suite)]''',
    '''    elif suite: cmd += ["--suite", str(suite)]
    if entiers and (jusqua or suite): cmd.append("--sans-intermediaires")   # v2.3.2 : pas de x.5''')
rep('''                                                    bool(data.get("page1")), data.get("suite") or 0,
                                                    str(data.get("jusqua") or "")))''',
    '''                                                    bool(data.get("page1")), data.get("suite") or 0,
                                                    str(data.get("jusqua") or ""), bool(data.get("entiers"))))''')
open(p, "w", encoding="utf-8").write(s)
print("ok")
