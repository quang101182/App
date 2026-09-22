# -*- coding: utf-8 -*-
"""Patch du proxy 8190 : renommer une serie = DOSSIER D'ABORD, avec reessais (Manga Studio v2.4.2).

Quang 22/09 16h35 : « HTTP 500 /manga/serie_renommer : [WinError 5] Acces refuse » (banc-webtoon -> « a »). Le meme
os.rename fait a la main 1 min plus tard : OK -- un fichier de la serie etait OUVERT a cet instant (miniatures servies,
antivirus sur 129 images neuves). PIRE : le titre etait deja ecrit dans les manifestes AVANT le renommage du dossier
-> serie incoherente (dossier banc-webtoon, slug « a ») que l'app ne pouvait plus SUPPRIMER (« introuvable », 16h39).
=> 1. le dossier est renomme EN PREMIER, jusqu'a 12 essais sur 6 s ; s'il refuse, RIEN n'a change (message clair) ;
   2. seulement ensuite, les manifestes / narrations / serie.json du dossier renomme.
Rejouable (code d'origine OU premiere version de ce patch) : python patch_renommer_reessai.py <chemin du proxy>.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "dossier d'abord (v2.4.2)" in s:
    print("deja patche")
    sys.exit(0)

FIN_ORIGINE = '''    if nouveau != slug:
        os.rename(sd, cible)
    return {"ok": True, "slug": nouveau, "ancien": slug, "titre": titre, "chapitres": n}'''
FIN_V1 = '''    if nouveau != slug:
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
FIN = '''    return {"ok": True, "slug": nouveau, "ancien": slug, "titre": titre, "chapitres": n}'''
if s.count(FIN_V1) == 1:
    s = s.replace(FIN_V1, FIN)
elif s.count(FIN_ORIGINE) == 1:
    s = s.replace(FIN_ORIGINE, FIN)
else:
    raise SystemExit("fin de manga_serie_renommer introuvable")

APRES = '''        return {"error": "une autre serie porte deja ce nom de dossier (%s)" % nouveau}
    n = 0'''
if s.count(APRES) != 1:
    raise SystemExit("ancre « une autre serie » introuvable (%d)" % s.count(APRES))
s = s.replace(APRES, '''        return {"error": "une autre serie porte deja ce nom de dossier (%s)" % nouveau}
    if nouveau != slug:                              # dossier d'abord (v2.4.2) : s'il refuse, RIEN n'est change
        for _essai in range(12):                     # verrou passager : miniatures servies, antivirus
            try:
                os.rename(sd, cible)
                break
            except PermissionError:
                if _essai == 11:
                    return {"error": "Windows garde un fichier de la série ouvert (lecture des images, antivirus) : "
                                     "rien n'a été changé, réessaie dans quelques secondes."}
                time.sleep(0.5)
        sd = cible
    n = 0''')
open(p, "w", encoding="utf-8").write(s)
print("ok")
