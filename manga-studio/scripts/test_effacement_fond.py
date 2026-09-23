"""Banc T1 (4-sexies, 23/09/2026) : l'effacement du texte d'origine ne blanchit plus un FOND de case / de page.

Images fabriquees (aucun reseau) :
  A. un petit texte sombre sur un GRAND fond clair gris (ciel, decor) -> avec ratio_max=6 : seule la boite du texte
     blanchit ; sans (Ingestion) : tout le fond est peint (comportement d'avant, garde tel quel).
  B. une VRAIE bulle fermee (trait noir, interieur blanc, texte) -> effacee comme une bulle, avec ou sans ratio_max.
Usage : python test_effacement_fond.py
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ingest_page as ip              # noqa: E402

OK = KO = 0


def check(c, nom):
    global OK, KO
    OK, KO = (OK + 1, KO) if c else (OK, KO + 1)
    print(("  OK  " if c else "  KO  ") + nom)


W, H = 800, 1200
# A : fond gris clair 215 sur la moitie haute (surface < 18 % ? non : 50 % -> on le borne a une case de 40 % x 40 %)
a = Image.new("RGB", (W, H), (40, 40, 40))
d = ImageDraw.Draw(a)
d.rectangle([60, 60, 60 + 320, 60 + 420], fill=(215, 215, 215))          # case claire : 320 x 420 = 14 % de la page
d.rectangle([180, 200, 240, 230], fill=(20, 20, 20))                     # petit texte sombre : 60 x 30
tA = {"id": 1, "x": 170 / W, "y": 190 / H, "w": 80 / W, "h": 50 / H}
# B : vraie bulle fermee
b = Image.new("RGB", (W, H), (90, 90, 90))
d = ImageDraw.Draw(b)
d.ellipse([400, 600, 700, 800], fill=(255, 255, 255), outline=(0, 0, 0), width=4)
d.rectangle([500, 680, 600, 720], fill=(10, 10, 10))
tB = {"id": 2, "x": 480 / W, "y": 660 / H, "w": 140 / W, "h": 80 / H}


def blanchi(avant, apres, zone):
    x1, y1, x2, y2 = zone
    A = np.array(avant)[y1:y2, x1:x2].astype(int); B = np.array(apres)[y1:y2, x1:x2].astype(int)
    return float(((B.min(axis=2) >= 250) & (A.min(axis=2) < 250)).mean())


print("A. petit texte sur un grand fond clair")
r6, s6 = ip.clean_bubbles(a, [dict(tA)], ratio_max=6)
r0, s0 = ip.clean_bubbles(a, [dict(tA)])
hors_boite = (60, 300, 380, 480)                                           # le fond, loin du texte
check(blanchi(a, r6, hors_boite) < 0.01, "ratio_max=6 : le fond reste intact (%.0f %% blanchi)" % (100 * blanchi(a, r6, hors_boite)))
check(s6[0]["etat"] == "fond de case -> boite seule", "etat = %s" % s6[0]["etat"])
check(blanchi(a, r6, (180, 200, 240, 230)) > 0.95, "le texte, lui, est bien efface")
check(blanchi(a, r0, hors_boite) > 0.9, "Ingestion (sans ratio_max) : comportement d'avant garde (%s)" % s0[0]["etat"])

print("B. vraie bulle fermee")
r6, s6 = ip.clean_bubbles(b, [dict(tB)], ratio_max=6)
r0, s0 = ip.clean_bubbles(b, [dict(tB)])
check(s6[0]["etat"] == "bulle" and s0[0]["etat"] == "bulle", "effacee comme une bulle, avec ou sans ratio_max (%s / %s)" % (s6[0]["etat"], s0[0]["etat"]))
check(blanchi(b, r6, (500, 680, 600, 720)) > 0.95, "le texte de la bulle est efface")
check(np.array_equal(np.array(r6), np.array(r0)), "resultat IDENTIQUE avec ou sans ratio_max")
rBok = r6

# (cas « bulle pleine de grosses lettres » : prouve sur la VRAIE page OPM ch.2 p.10, essai_t2_nr.py -- une image
# fabriquee ne reproduisait pas la poche isolee)
print("D. texte pose sur le dessin (effacement « vide ») -- T2-bis")
e = Image.new("RGB", (W, H), (150, 150, 150))
d = ImageDraw.Draw(e)
d.rectangle([300, 300, 360, 520], fill=(20, 20, 20))                                      # texte vertical sombre
d.rectangle([330, 400, 332, 402], fill=(255, 255, 255))                                   # un point blanc isole
tD = {"id": 4, "x": 295 / W, "y": 295 / H, "w": 70 / W, "h": 230 / H}
rD, sD = ip.clean_bubbles(e, [dict(tD)], ratio_max=6, couverture_min=0.5)
_, sD0 = ip.clean_bubbles(e, [dict(tD)], ratio_max=6)
check("boite" in sD[0]["etat"], "avec couverture_min : %s (sans : %s)" % (sD[0]["etat"], sD0[0]["etat"]))
check(blanchi(e, rD, (300, 300, 360, 520)) > 0.95, "le texte est efface (plus rien de pose sur du chinois)")
rB6, _ = ip.clean_bubbles(b, [dict(tB)], ratio_max=6, couverture_min=0.5)
check(np.array_equal(np.array(rB6), np.array(rBok)), "vraie bulle : resultat IDENTIQUE avec couverture_min")

print("E. personnage sur un fond clair, a cote du texte -- v1.97.0 (remontee Video Studio 24/09 : cases effacees)")
f = Image.new("RGB", (W, H), (40, 40, 40))
d = ImageDraw.Draw(f)
d.rectangle([60, 60, 60 + 300, 60 + 360], fill=(245, 245, 245))          # case claire : 11 % de la page (< 18 %)
d.rectangle([90, 90, 130, 200], fill=(20, 20, 20))                       # texte vertical sombre
d.ellipse([200, 250, 320, 400], fill=(30, 30, 30))                       # « personnage » entoure de fond clair
tE = {"id": 5, "x": 85 / W, "y": 85 / H, "w": 50 / W, "h": 120 / H}
rE, sE = ip.clean_bubbles(f, [dict(tE)], couverture_min=0.5, trous_dans_texte=True)
rE0, _ = ip.clean_bubbles(f, [dict(tE)], couverture_min=0.5)
perso = (215, 265, 305, 385)
check(blanchi(f, rE, perso) < 0.01, "le personnage reste intact (%.0f %% blanchi)" % (100 * blanchi(f, rE, perso)))
check(blanchi(f, rE, (90, 90, 130, 200)) > 0.95, "le texte, lui, est efface (%s)" % sE[0]["etat"])
check(blanchi(f, rE0, perso) > 0.9, "sans trous_dans_texte (Ingestion) : comportement d'avant garde")
rBt, _ = ip.clean_bubbles(b, [dict(tB)], couverture_min=0.5, trous_dans_texte=True)
check(np.array_equal(np.array(rBt), np.array(rBok)), "vraie bulle : resultat IDENTIQUE avec trous_dans_texte")

print("F. boite entiere geante (texte sur une photo, boite de 81 % de la page) -- v1.97.0")
g = Image.new("RGB", (W, H), (200, 200, 200))
d = ImageDraw.Draw(g)
for i in range(0, W, 16):
    d.line([(i, 0), (i, H)], fill=(20, 20, 20), width=3)                 # « photo » : ville claire rayee de noir
tF = {"id": 6, "x": 0.05, "y": 0.05, "w": 0.9, "h": 0.9}
rF, sF = ip.clean_bubbles(g, [dict(tF)], couverture_min=0.5, trous_dans_texte=True, boite_max=0.25)
_, sF0 = ip.clean_bubbles(g, [dict(tF)], couverture_min=0.5, trous_dans_texte=True)
check(sF[0]["etat"] == "trop grande -> non effacee" and np.array_equal(np.array(rF), np.array(g)),
      "boite_max=0.25 : rien n'est efface (%s ; sans : %s)" % (sF[0]["etat"], sF0[0]["etat"]))
rD2, _ = ip.clean_bubbles(e, [dict(tD)], ratio_max=6, couverture_min=0.5, trous_dans_texte=True, boite_max=0.25)
check(np.array_equal(np.array(rD2), np.array(rD)), "petite boite entiere (cas D) : inchangee par boite_max")

print("\n%d/%d" % (OK, OK + KO))
sys.exit(1 if KO else 0)
