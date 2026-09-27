# -*- coding: utf-8 -*-
"""v3.1.1 (27/09, Quang 17h25-17h27, capture PC) : (1) le bloc 🎭 Dialogues passe AU-DESSUS de la Narration (« narration,
traduction, musique et video vont ensemble ; le dialogue est a part ») ; (2) bloc 🎭 REPLIE : ses deux interrupteurs restaient
affiches (regle v2.99.0 « #dlgBox .dlg-opts{display:block} » plus forte que celle des blocs replies) -> seulement ouvert ;
(3) « Tons par replique » et « Lire les encarts » cote a cote, une moitie de largeur chacun. Suppose v3.1.0."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v3.1.1" in s[:900]:
    print("deja applique"); sys.exit(0)
if "v3.1.0" not in s[:1400]:
    print("ERREUR : appliquer d'abord app_patch_3100_verif_bulles.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:80], s.count(a))
    s = s.replace(a, b)


rep("<title>Manga Studio v3.1.0</title>", "<title>Manga Studio v3.1.1</title>")
rep('<span class="ver" id="verBadge">v3.1.0</span>', '<span class="ver" id="verBadge">v3.1.1</span>')
rep('const VERSION = "3.1.0";', 'const VERSION = "3.1.1";   // v3.1.1 : Dialogues au-dessus de la narration ; bloc replie vraiment replie ; 2 interrupteurs sur une ligne')
rep('''  { k: "narr", sel: "#chapDetail .narr-box.bloc-narr", ic: "🎙", t: "Narration" },
  { k: "dlg",  sel: "#chapDetail .narr-box.bloc-dlg",  ic: "🎭", t: "Dialogues" },          // v2.81.0 : a part de la video''',
    '''  { k: "dlg",  sel: "#chapDetail .narr-box.bloc-dlg",  ic: "🎭", t: "Dialogues" },          // v2.81.0 : a part de la video ; v3.1.1 : EN TETE (Quang : « le dialogue est a part »)
  { k: "narr", sel: "#chapDetail .narr-box.bloc-narr", ic: "🎙", t: "Narration" },''')
rep("""#dlgBox .dlg-opts{display:block;margin:2px 0 4px}
#dlgBox .dlg-opts label{display:flex;align-items:center;gap:10px;padding:7px 0;border-top:1px solid var(--line);min-height:40px}""",
    """#dlgBox.cl-ouv .dlg-opts{display:grid;grid-template-columns:1fr 1fr;gap:0 14px;margin:2px 0 4px;border-top:1px solid var(--line)}   /* v3.1.1 : ouvert seulement ; 2 par ligne */
#dlgBox .dlg-opts label{display:flex;align-items:center;gap:8px;padding:7px 0;min-height:40px;min-width:0}
#dlgBox .dlg-opts label#dlgEnchL{grid-column:1 / -1;border-top:1px solid var(--line)}""")
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok v3.1.1")
