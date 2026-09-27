# -*- coding: utf-8 -*-
"""dialogues.py 1.22.1 -> 1.23.0 (27/09, constat reel noritaka ch.1 p.5-6 : refaire la preparation a repaye 19 voix sur 23,
291 credits, alors que les textes n'avaient pas change) : l'IA redecide le TON de chaque replique a chaque preparation, et le
ton entre dans l'empreinte de la voix. Desormais : texte ET personnage inchanges -> l'ANCIEN ton est garde (voix conservee) ;
une correction de ton par Quang prime toujours. Rejouable."""
import sys
P = sys.argv[1]
s = open(P, encoding="utf-8", newline="").read()
if 'VERSION = "1.23.0"' in s:
    print("deja applique"); sys.exit(0)
N = "\r\n" if "\r\n" in s else "\n"
def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)
rep('VERSION = "1.22.1"  #', 'VERSION = "1.23.0"  # 1.23.0 (27/09) : texte et personnage inchanges -> ANCIEN ton garde (la voix n\'est pas repayee) ;  #')
rep('''            neuf.update({k: v for k, v in corr.items() if k in ("texte", "qui", "ton", "lire")})   # les corrections gagnent''',
    '''            neuf.update({k: v for k, v in corr.items() if k in ("texte", "qui", "ton", "lire")})   # les corrections gagnent
            if (vieux and "ton" not in corr and vieux.get("ton") is not None and vieux.get("qui") == neuf["qui"]
                    and (vieux.get("texte") or "").strip() == (neuf.get("texte") or "").strip()):
                neuf["ton"] = vieux["ton"]                   # 1.23.0 : meme texte, meme personnage -> meme ton -> meme voix''')
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok 1.23.0")
