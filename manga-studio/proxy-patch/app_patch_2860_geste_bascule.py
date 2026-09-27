# -*- coding: utf-8 -*-
"""v2.86.0 (27/09, Quang 12h47-12h48 : « un appui long pour aller vers la secondaire et un appui normal pour revenir vers la
principale […] sauf si j'ai change d'onglet : il faut que je clique une fois [pour arriver sur la Bibliotheque], puis une
deuxieme fois pour revenir a la principale. Pour l'appui long, ca marche de la meme facon ») -- PC et telephone :
- application SECONDAIRE : un appui SIMPLE sur 📚 alors que la Bibliotheque est DEJA affichee = retour a la principale
  (meme chemin que l'appui long : sur le PC la fenetre dediee se ferme, sur le telephone l'adresse de la principale) ;
  depuis un autre onglet, le 1er appui affiche la Bibliotheque (comme avant), le 2e ramene a la principale ;
- l'appui LONG (1,2 s) ne bascule que depuis la Bibliotheque DEJA affichee (meme regle, dans les deux applications).
Seul un VRAI appui compte (event.isTrusted) : l'app « clique » elle-meme cet onglet pour y revenir (3 endroits) -- ces
clics-la ne doivent jamais faire changer d'application. Un appui sur l'onglet deja actif ne faisait que rafraichir la liste.
Suppose v2.85.0. Rejouable."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v2.86.0" in s[:400]:
    print("deja applique"); sys.exit(0)
if "v2.85.0" not in s[:400]:
    print("ERREUR : appliquer d'abord app_patch_2850_finis_communs.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


rep("<title>Manga Studio v2.85.0</title>", "<title>Manga Studio v2.86.0</title>")
rep('<span class="ver" id="verBadge">v2.85.0</span>', '<span class="ver" id="verBadge">v2.86.0</span>')
rep('const VERSION = "2.85.0";', 'const VERSION = "2.86.0";   // v2.86.0 : secondaire -> appui simple sur 📚 deja affiche = retour a la principale ; appui long depuis 📚 seulement')
rep("""  b.addEventListener("pointerdown", () => { long = false; stop();
    t = setTimeout(() => { long = true; espaceBasculer(); }, 1200); });""",
    """  b.addEventListener("pointerdown", () => { long = false; stop();
    if (!b.classList.contains("sel")) return;                    // v2.86.0 : depuis la Bibliotheque DEJA affichee seulement
    t = setTimeout(() => { long = true; espaceBasculer(); }, 1200); });""")
rep("""  b.addEventListener("click", e => { if (long){ long = false; e.stopImmediatePropagation(); e.preventDefault(); } }, true);""",
    """  b.addEventListener("click", e => {
    if (long){ long = false; e.stopImmediatePropagation(); e.preventDefault(); return; }
    // v2.86.0 : dans la SECONDAIRE, un vrai appui simple sur 📚 deja affiche = retour a la principale
    if (e.isTrusted && ESPACE.nom === "prive" && b.classList.contains("sel")){ e.stopImmediatePropagation(); e.preventDefault(); espaceBasculer(); }
  }, true);""")
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
