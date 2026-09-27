# -*- coding: utf-8 -*-
"""Manga Studio v3.2.0 -- 13e patch serveur (27/09, Quang 17h43) : /manga/dialogues renvoie AUSSI le contenu de la
verification des bulles (« verif » : {page: {ordre, exclues, ajouts, t}}) pour que l'app detecte une preparation DEPASSEE
(bulles retouchees apres coup) et propose de la refaire. Suppose patch_dialogues_12. Rejouable."""
import io, sys

P = sys.argv[1]
s = io.open(P, encoding="utf-8", newline="").read()
if '"verif": ((_dlg_lire(' in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"
a = '''            "verif_pages": sorted(int(k) for k in (((_dlg_lire(os.path.join(dd, "bulles_verifiees.json")) or {}).get("pages")) or {}))}   # v3.1.0 (R30)'''
b = '''            "verif_pages": sorted(int(k) for k in (((_dlg_lire(os.path.join(dd, "bulles_verifiees.json")) or {}).get("pages")) or {})),   # v3.1.0 (R30)
            "verif": ((_dlg_lire(os.path.join(dd, "bulles_verifiees.json")) or {}).get("pages")) or {}}   # v3.2.0 : preparation depassee ?'''
if s.count(a) != 1:
    raise SystemExit("ancre introuvable (%d) -- patch_dialogues_12 applique ?" % s.count(a))
s = s.replace(a, b)
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
