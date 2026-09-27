# -*- coding: utf-8 -*-
"""R15-bis (27/09 12h46 -- Quang : « traduire puis preparer […] traduction des pages en erreur ») -- traduire_chapitre.py 2.3.1.
Constat (journal dialogues/run.log) : `ModuleNotFoundError: No module named 'scipy'` dans boite_lettres -- l'APP lance les
scripts avec MANGA_PY (venv kohya-trainer : numpy + cv2, PAS scipy) ; mes bancs tournaient avec le venv ComfyUI (qui a scipy).
Correctifs : (1) composantes connexes par OpenCV (present dans les DEUX interpreteurs) au lieu de scipy ; (2) un incident dans
boite_lettres ne fait plus planter la page ni le lot : la zone est ecartee comme avant, et c'est journalise. Le banc tourne
desormais avec l'interpreteur de l'APP. Suppose scripts_patch_r15.py. Rejouable : python scripts_patch_r15b.py <dossier scripts>"""
import os, sys

D = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
p = os.path.join(D, "traduire_chapitre.py")
s = open(p, encoding="utf-8", newline="").read()
if 'VERSION = "2.3.1"' in s:
    print("deja applique"); sys.exit(0)
if "def boite_lettres(" not in s:
    print("ERREUR : appliquer d'abord scripts_patch_r15.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


rep('VERSION = "2.3.0"', 'VERSION = "2.3.1"   # 2.3.1 (R15-bis) : lettres reperees par OpenCV (scipy absent de l\'interpreteur de l\'app), jamais bloquant ;')
rep('''    import numpy as np
    from scipy import ndimage
''', '''    import numpy as np
    import cv2                                                   # 2.3.1 : present dans l'interpreteur de l'APP (scipy non)
''')
rep('''    lab, _ = ndimage.label(A < sombre)
    lettres = []
    for i, sl in enumerate(ndimage.find_objects(lab)):
        if sl is None:
            continue
''', '''    n, lab, st, _ = cv2.connectedComponentsWithStats((A < sombre).astype(np.uint8), connectivity=8)
    lettres = []
    for i in range(1, n):                                        # 0 = le fond
        cx, cy, cw, ch_ = (int(v) for v in st[i][:4])
        sl = (slice(cy, cy + ch_), slice(cx, cx + cw))
''')
rep('''        voisin = A[r0:r1, c0:c1][lab[r0:r1, c0:c1] != i + 1]''',
    '''        voisin = A[r0:r1, c0:c1][lab[r0:r1, c0:c1] != i]''')
rep('''                        serre = boite_lettres(im, t)                  # 2.3.0 (R15) : resserrer sur les lettres, sinon ecarter''',
    '''                        try:
                            serre = boite_lettres(im, t)              # 2.3.0 (R15) : resserrer sur les lettres, sinon ecarter
                        except Exception as e:                        # 2.3.1 : jamais bloquant -- ecartee comme avant
                            nc.log("  page %d : lettres non reperees (%s) -> zone ecartee" % (p["num"], e))
                            serre = None''')
open(p, "w", encoding="utf-8", newline="").write(s)
print("ok")
