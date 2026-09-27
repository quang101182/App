# -*- coding: utf-8 -*-
"""R18 phase 2 (27/09) -- reglages.py 1.5.0 : les curseurs de lecture ont aussi une valeur PAR DEFAUT par instance :
vit_cloud / vit_local (vitesse des narrations, voix en ligne / sur le PC), vol_g (volume general), mus_vol (musique),
dll_vit (lecteur des Dialogues), vid_vit (lecteur video). Recharge a chaud par le serveur (aucune relance).
Suppose scripts_patch_r18.py. Rejouable : python scripts_patch_r18b.py <dossier scripts>"""
import os, sys

D = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
p = os.path.join(D, "reglages.py")
s = open(p, encoding="utf-8", newline="").read()
if '"vid_vit"' in s:
    print("deja applique"); sys.exit(0)
if 'VERSION = "1.4.0"' not in s:
    print("ERREUR : appliquer d'abord scripts_patch_r18.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"
a = '''                  "voix_h_ecoute": (0.7, 1.5), "voix_f_ecoute": (0.7, 1.5), "voix_n_ecoute": (0.7, 1.5)}'''.replace("\n", N)
b = '''                  "voix_h_ecoute": (0.7, 1.5), "voix_f_ecoute": (0.7, 1.5), "voix_n_ecoute": (0.7, 1.5),
                  # v1.5.0 (R18 phase 2) : les curseurs de lecture de l'app
                  "vit_cloud": (0.5, 2), "vit_local": (0.5, 2), "vol_g": (0, 100), "mus_vol": (0, 100),
                  "dll_vit": (0.5, 2), "vid_vit": (0.5, 2)}'''.replace("\n", N)
assert s.count(a) == 1
s = s.replace(a, b).replace('VERSION = "1.4.0"', 'VERSION = "1.5.0"   # 1.5.0 (R18 phase 2) : defauts des curseurs de lecture ;', 1)
open(p, "w", encoding="utf-8", newline="").write(s)
print("ok")
