# -*- coding: utf-8 -*-
"""R14 (27/09) -- dialogues.py 1.13.0 : les Dialogues lisent aussi les textes que la traduction a « ecartes » POUR L'IMAGE.

Constat mesure (chapitre webtoon de la secondaire) : la traduction ecarte un texte hors bulles quand l'effacer risquerait
d'abimer le dessin (« zone trop grande pour une boite entiere », « ne tiendrait pas ») -- a raison : un essai qui les
effacait quand meme (fond clair a >= 70 %) a BLANCHI des morceaux de cases (p.43, p.47 ; controle visuel 27/09, abandonne).
Mais ce texte-la est juste : seule sa POSE sur l'image est risquee. Les Dialogues (voix) n'ont besoin que du texte : ils les
lisent donc desormais. Restent exclus : « moins de 2 lettres » (« ...! », rien a dire). Suppose scripts_patch_r12_r13.py.
Rejouable : python scripts_patch_r14.py <dossier scripts>"""
import os, sys

D = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
p = os.path.join(D, "dialogues.py")
s = open(p, encoding="utf-8", newline="").read()
if "def ecarte_pour_image(" in s:
    print("deja applique"); sys.exit(0)
if 'VERSION = "1.12.0"' not in s:
    print("ERREUR : appliquer d'abord scripts_patch_r12_r13.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


rep('VERSION = "1.12.0"', 'VERSION = "1.13.0"  # 1.13.0 (R14, 27/09) : les textes ecartes POUR L\'IMAGE (zone trop grande...) sont lus ;')
rep('''def source_bulles(chap_dir, plage=""):''', '''def ecarte_pour_image(b):
    """1.13.0 (R14) : texte ecarte par la traduction pour PROTEGER LE DESSIN (sa pose sur l'image), pas parce qu'il est faux
    -> les Dialogues le lisent. « moins de 2 lettres » (« ...! ») reste exclu."""
    return bool(b.get("ecarte")) and not str(b.get("ecarte")).startswith("moins de 2")


def source_bulles(chap_dir, plage=""):''')
rep('''            p["_bulles"] = sorted([b for b in p["bulles"] if b["type"] in ("dialogue", "narration") and not b.get("ecarte")''',
    '''            p["_bulles"] = sorted([b for b in p["bulles"] if b["type"] in ("dialogue", "narration") and (not b.get("ecarte") or ecarte_pour_image(b))''')
open(p, "w", encoding="utf-8", newline="").write(s)
print("ok")
