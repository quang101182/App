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
print("\n%d/%d" % (OK, OK + KO))
sys.exit(1 if KO else 0)
