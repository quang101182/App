# -*- coding: utf-8 -*-
"""Patch du proxy 8190 : renommer une serie REESSAIE sur un verrou passager (Manga Studio v2.4.2).

Quang 22/09 16h35 : « HTTP 500 /manga/serie_renommer : [WinError 5] Acces refuse » en renommant banc-webtoon. Le meme
os.rename fait a la main 1 min plus tard : OK. Windows refuse de renommer un dossier dont un fichier est OUVERT a cet
instant (le proxy qui sert les miniatures de la serie qu'on vient d'ouvrir, l'antivirus qui analyse 129 images neuves).
=> jusqu'a 12 essais sur 6 s, puis un message clair au lieu d'une erreur 500.
Rejouable : python patch_renommer_reessai.py <chemin du proxy>.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "verrou passager (v2.4.2)" in s:
    print("deja patche")
    sys.exit(0)
a = '''    if nouveau != slug:
        os.rename(sd, cible)
    return {"ok": True, "slug": nouveau, "ancien": slug, "titre": titre, "chapitres": n}'''
b = '''    if nouveau != slug:
        for _essai in range(12):                     # verrou passager (v2.4.2) : miniatures servies, antivirus
            try:
                os.rename(sd, cible)
                break
            except PermissionError:
                if _essai == 11:
                    return {"error": "Windows garde un fichier de la série ouvert (lecture des images, antivirus) : "
                                     "le titre est enregistré, réessaie le renommage dans quelques secondes."}
                time.sleep(0.5)
    return {"ok": True, "slug": nouveau, "ancien": slug, "titre": titre, "chapitres": n}'''
if s.count(a) != 1:
    raise SystemExit("ancre introuvable ou multiple (%d)" % s.count(a))
s = s.replace(a, b)
open(p, "w", encoding="utf-8").write(s)
print("ok")
