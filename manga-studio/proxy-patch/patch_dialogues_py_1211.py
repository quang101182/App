# -*- coding: utf-8 -*-
"""dialogues.py 1.21.0 -> 1.21.1 (27/09, Quang 17h53 : « j'avais pointe un texte qui manquait, reste en anglais, et ca l'a lu
en anglais au lieu de le lire en francais ») : la regle 0 du prompt (bulle SANS texte -> lue sur l'image) disait « mot pour
mot » -- pensee pour une page deja en VF. Une bulle AJOUTEE sur une page traduite est souvent restee en VO : desormais, si le
texte lu n'est pas en francais, il est TRADUIT en francais naturel (c'est ce qui sera dit). Rejouable."""
import sys
P = sys.argv[1]
s = open(P, encoding="utf-8", newline="").read()
if 'VERSION = "1.21.1"' in s:
    print("deja applique"); sys.exit(0)
N = "\r\n" if "\r\n" in s else "\n"
def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)
rep('VERSION = "1.21.0"  #', 'VERSION = "1.21.1"  # 1.21.1 (27/09) : bulle lue sur l\'image PAS en francais -> TRADUITE (ajout reste en anglais) ;  #')
rep('''0. Si le texte d'une bulle est VIDE (page deja en francais, rien de traduit), LIS-le sur l'image et rends-le dans "texte",
   mot pour mot, casse d'origine, sans rien corriger ni ajouter.''',
    '''0. Si le texte d'une bulle est VIDE (bulle ajoutee a la main, ou page deja en francais), LIS-le sur l'image et rends-le dans
   "texte" : s'il est deja en FRANCAIS, mot pour mot, sans rien corriger ni ajouter ; s'il est dans une AUTRE langue (anglais,
   japonais...), TRADUIS-le en francais naturel et oral -- c'est ce que la voix dira, jamais la VO. Casse normale (pas tout en
   majuscules), ponctuation d'origine.''')
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok 1.21.1")
