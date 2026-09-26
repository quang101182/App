# -*- coding: utf-8 -*-
"""Manga Studio v2.68.0 (suite) : 2 bugs signales par Quang le 26/09/2026 11h15 (Fold ferme, 476 px), captures a l'appui.
1. Pendant une generation video, l'onglet Video du chapitre « clignote en se redimensionnant en hauteur » : mesure 54 -> 16 -> 54 px
   toutes les 4 s. vidRendre() reecrit #chapVid (innerHTML) et efface l'en-tete compact (.cl-tete) que clMaj() n'y remet
   qu'au tick suivant (<= 800 ms) : le bloc replie n'affiche plus rien entre les deux. -> clMaj() juste apres la reecriture.
2. Ligne compacte « Narration » : sous 480 px les etiquettes de cout (flex:none, 280 px) poussent le chevron hors du cadre
   (476 px : 4 px dehors ; 360 px : > 100 px). -> elles peuvent se reduire et passer a la ligne.
Rejouable : python app_patch_268b_clignotement.py <manga_studio.html>
"""
import sys

P = sys.argv[1]
s = open(P, "rb").read().decode("utf-8")
if "v2.68.0 : en-tete compact remis" in s:
    print("deja patche"); sys.exit(0)


def rep(a, b):
    global s
    a, b = a.replace("\n", "\r\n"), b.replace("\n", "\r\n")
    if s.count(a) != 1:
        raise SystemExit("ancre %d fois : %r" % (s.count(a), a[:80]))
    s = s.replace(a, b)


rep('''  $("chapVid").innerHTML = ci >= 0 ? '<div class="bloc-titre">🎬 Vidéo</div>' + vidCamHtml() + vidLigne(VIDS.chapitres[ci], ci, false) : "";''',
    '''  $("chapVid").innerHTML = ci >= 0 ? '<div class="bloc-titre">🎬 Vidéo</div>' + vidCamHtml() + vidLigne(VIDS.chapitres[ci], ci, false) : "";
  clMaj();                           // v2.68.0 : en-tete compact remis TOUT DE SUITE (sinon le bloc replie clignote 54 -> 16 px)''')
rep('''  .cl-est{display:none} .cl-box.bloc-narr:not(.cl-ouv) .cl-est{display:flex;flex-wrap:wrap} }''',
    '''  .cl-est{display:none} .cl-box.bloc-narr:not(.cl-ouv) .cl-est{display:flex;flex-wrap:wrap;flex:0 1 auto;min-width:0}
  .cl-box.bloc-narr:not(.cl-ouv) .cl-est > *{max-width:100%;white-space:normal} }   /* v2.68.0 : le chevron ne sort plus du cadre */''')
open(P, "wb").write(s.encode("utf-8"))
print("patche")
