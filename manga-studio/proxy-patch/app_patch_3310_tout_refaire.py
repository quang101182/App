# -*- coding: utf-8 -*-
"""v3.3.1 (27/09, Quang 18h21 : « je ne vois pas le bouton de tout refaire […] c'est un peu confus ») : « ⚡ Tout faire »
disparait quand tout est a jour (normal), mais rien ne disait comment TOUT REFAIRE. Le menu ⋯ d'une plage propose desormais
« ⚡ Tout refaire (repliques → voix → video) » en tete ; « ↻ Refaire seulement les repliques » reste. Confirmation qui dit
ce qui sera repaye (dialogues.py 1.23.0 : voix gardees si texte et personnage inchanges). Suppose v3.3.0. Rejouable."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v3.3.1" in s[:900]:
    print("deja applique"); sys.exit(0)
if "v3.3.0" not in s[:1400]:
    print("ERREUR : appliquer d'abord app_patch_3300_tout_faire.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:80], s.count(a))
    s = s.replace(a, b)


rep("<title>Manga Studio v3.3.0</title>", "<title>Manga Studio v3.3.1</title>")
rep('<span class="ver" id="verBadge">v3.3.0</span>', '<span class="ver" id="verBadge">v3.3.1</span>')
rep('const VERSION = "3.3.0";', 'const VERSION = "3.3.1";   // v3.3.1 : ⋯ d une plage -> « ⚡ Tout refaire » (repliques, voix, video)')
rep("""      + '<button data-dpl="corriger" data-k="' + esc(k) + '">✏ <span>Corriger qui parle, voix, vitesses</span></button>'
      + '<button data-dpl="refaire" data-k="' + esc(k) + '">↻ <span>Refaire la préparation<small>l\\'IA relit ces pages</small></span></button>'""",
    """      + '<button data-dpl="toutrefaire" data-k="' + esc(k) + '">⚡ <span>Tout refaire<small>répliques → voix → vidéo · voix gardées si le texte ne change pas</small></span></button>'
      + '<button data-dpl="corriger" data-k="' + esc(k) + '">✏ <span>Corriger qui parle, voix, vitesses</span></button>'
      + '<button data-dpl="refaire" data-k="' + esc(k) + '">↻ <span>Refaire seulement les répliques<small>l\\'IA relit ces pages, sans voix ni vidéo</small></span></button>'""")
rep("""    else if (act === "oublier") dplOublier(k);""",
    """    else if (act === "oublier") dplOublier(k);
    else if (act === "toutrefaire"){ DPL.menu = ""; dplRendre(); const [a0, b0] = dplBornes(k), n0 = Math.max(1, Math.min(b0, CHAP_PAGES || b0) - a0 + 1);
      if (confirm("⚡ Tout refaire pour " + dplTitre(k) + " ?\\n\\n· répliques : ≈ " + fmtUsd(0.004 * n0) + "\\n· voix : seules celles dont le texte ou le personnage change sont repayées\\n· vidéo refaite"
          + "\\n\\nArrêt avant les voix si l'IA a un doute ; arrêt net si le quota ElevenLabs tombe.")) dlgLancer("tout"); }""")
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok v3.3.1")
