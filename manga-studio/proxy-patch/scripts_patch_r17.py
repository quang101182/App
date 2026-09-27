# -*- coding: utf-8 -*-
"""R17 (27/09) -- dialogues.py 1.14.0 : la vitesse d'ECOUTE d'un personnage (« ecoute », 0,7-1,5, reglee dans l'ecran ✏) est
appliquee au MONTAGE de la video (ffmpeg atempo, hauteur de voix conservee) -- aucune voix regeneree, aucun credit. Elle entre
dans l'empreinte de la video SEULEMENT si elle differe de 1 : les videos existantes ne deviennent pas « a refaire » pour rien ;
une video faite avant un changement d'ecoute, elle, passe « a refaire » (gratuit). Suppose scripts_patch_r14.py.
Rejouable : python scripts_patch_r17.py <dossier scripts>"""
import os, sys

D = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
p = os.path.join(D, "dialogues.py")
s = open(p, encoding="utf-8", newline="").read()
if "def ecoute_de(" in s:
    print("deja applique"); sys.exit(0)
if 'VERSION = "1.13.0"' not in s:
    print("ERREUR : appliquer d'abord scripts_patch_r14.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


rep('VERSION = "1.13.0"', 'VERSION = "1.14.0"  # 1.14.0 (R17, 27/09) : vitesse d\'ECOUTE par personnage appliquee a la video, gratuite ;')
rep('''def empreinte_video(doc, distrib, dd, portee=""):''', '''def ecoute_de(distrib, qui):
    """1.14.0 (R17) : la vitesse d'ECOUTE du personnage (1 = telle que generee). Jamais envoyee a ElevenLabs."""
    try:
        return round(max(0.7, min(1.5, float((reglage_voix(distrib, qui) or {}).get("ecoute") or 1))), 2)
    except (TypeError, ValueError):
        return 1.0


def empreinte_video(doc, distrib, dd, portee=""):''')
rep('''    return liste, hashlib.sha1(json.dumps([[x["cle"], x["voix"]["empreinte"], x.get("texte"), couleur(x["qui"]), x["qui"]] for x in liste]).encode()).hexdigest()[:16]''',
    '''    # 1.14.0 : l'ecoute n'entre que si elle differe de 1 (les videos d'avant restent « a jour »)
    return liste, hashlib.sha1(json.dumps([[x["cle"], x["voix"]["empreinte"], x.get("texte"), couleur(x["qui"]), x["qui"]]
                                           + ([ecoute_de(distrib, x["qui"])] if ecoute_de(distrib, x["qui"]) != 1 else [])
                                           for x in liste]).encode()).hexdigest()[:16]''')
rep('''        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", os.path.join(dd, "voix", x["voix"]["fichier"]), "-af", "apad=pad_dur=0.4",''',
    '''        ec = ecoute_de(distrib, x["qui"])                     # 1.14.0 (R17) : vitesse d'ecoute, hauteur conservee
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", os.path.join(dd, "voix", x["voix"]["fichier"]),
                        "-af", ("atempo=%g," % ec if ec != 1 else "") + "apad=pad_dur=0.4",''')
open(p, "w", encoding="utf-8", newline="").write(s)
print("ok")
