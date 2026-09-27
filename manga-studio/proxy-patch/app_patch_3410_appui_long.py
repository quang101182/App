# -*- coding: utf-8 -*-
"""v3.4.1 (27/09, Quang 19h09 : « au tactile je peux creer une bulle que je ne voulais pas ; je n'ai aucun moyen de la
supprimer, seulement une croix ; un appui long serait bien ») -- verification des bulles : APPUI LONG (0,55 s, doigt
immobile) sur une pastille AJOUTEE = elle est SUPPRIMEE (↶ la rend) ; sur une bulle detectee = exclure / remettre (on ne
supprime pas ce que la detection a trouve). L'aide le dit. Suppose v3.4.0. Rejouable."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v3.4.1" in s[:900]:
    print("deja applique"); sys.exit(0)
if "v3.4.0" not in s[:1400]:
    print("ERREUR : appliquer d'abord app_patch_3400_musique_dialogues.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:80], s.count(a))
    s = s.replace(a, b)


rep("<title>Manga Studio v3.4.0</title>", "<title>Manga Studio v3.4.1</title>")
rep('<span class="ver" id="verBadge">v3.4.0</span>', '<span class="ver" id="verBadge">v3.4.1</span>')
rep('const VERSION = "3.4.0";', 'const VERSION = "3.4.1";   // v3.4.1 : verification des bulles -- appui long sur une bulle ajoutee = supprimee')
rep("""'<div class="dlv-aide" id="dlvAide">✋ <span><b>Toucher</b> = exclure · <b>glisser</b> = ordre · <b>entourer</b> = ajouter</span>""",
    """'<div class="dlv-aide" id="dlvAide">✋ <span><b>Toucher</b> = exclure · <b>glisser</b> = ordre · <b>entourer</b> = ajouter · <b>appui long</b> sur un ajout = supprimer</span>""")
rep("""  cad.addEventListener("pointerdown", e => {
    const k = e.target.closest("[data-dlv-k]"); cad.setPointerCapture(e.pointerId);
    g = { k: k ? +k.dataset.dlvK : -1, pts: [frac(e)], t: Date.now() };
  });""",
    """  cad.addEventListener("pointerdown", e => {
    const k = e.target.closest("[data-dlv-k]"); cad.setPointerCapture(e.pointerId);
    g = { k: k ? +k.dataset.dlvK : -1, pts: [frac(e)], t: Date.now() };
    if (g.k >= 0){ const g0 = g; g.lp = setTimeout(() => {                    // v3.4.1 : APPUI LONG, doigt immobile
      if (g !== g0 || g0.drag) return;
      const p = dlvPage(), it = p && p.items[g0.k]; if (!it) return;
      g = null; dlvSnap();
      if (it.ajout){ p.items.splice(g0.k, 1); p.modif++; dlvDessiner(); dlvBas(); dlvToast("🗑 bulle ajoutée supprimée · ↶ pour la remettre"); }
      else { it.exclu = !it.exclu; p.modif++; dlvDessiner(); dlvBas(); dlvToast(it.exclu ? "✕ exclue · touche-la pour la remettre" : "✓ remise"); }
      try { navigator.vibrate && navigator.vibrate(30); } catch (err) {}
    }, 550); }
  });""")
rep("""  const fin = e => {
    if (!g) return; const x = g; g = null; const p = dlvPage(); if (!p) return;""",
    """  const fin = e => {
    if (!g) return; const x = g; g = null; clearTimeout(x.lp); const p = dlvPage(); if (!p) return;   // v3.4.1 : l'appui long a deja agi -> g est vide""")
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok v3.4.1")
