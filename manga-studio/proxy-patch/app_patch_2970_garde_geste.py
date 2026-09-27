# -*- coding: utf-8 -*-
"""v2.97.0 (27/09, Quang 14h36 : « un seul geste m'a fait sortir de l'application ») -- journal du Fold 14:35:49 :
`CoreBackPreview … SameTaskWebApkActivity: Setting back callback null` = Chrome n'a declare AUCUN retour interne : il a juge
la garde (posee au CHARGEMENT, sans geste de l'utilisateur) ignorable, et Android a ferme l'application. (Onglet de navigateur
du Samsung : garde respectee -- le cas de l'application installee differe.) Desormais la garde est posee PENDANT un geste de
Quang (premier toucher / touche), et reposee au toucher suivant apres un avertissement : une entree creee pendant un geste de
l'utilisateur n'est pas ignoree. Le reamorcage par minuterie (sans geste, donc ignore) est retire. Suppose v2.96.0. Rejouable."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v2.97.0" in s[:700]:
    print("deja applique"); sys.exit(0)
if "v2.96.0" not in s[:700]:
    print("ERREUR : appliquer d'abord app_patch_2960_orientation.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


rep("<title>Manga Studio v2.96.0</title>", "<title>Manga Studio v2.97.0</title>")
rep('<span class="ver" id="verBadge">v2.96.0</span>', '<span class="ver" id="verBadge">v2.97.0</span>')
rep('const VERSION = "2.96.0";', 'const VERSION = "2.97.0";   // v2.97.0 : garde du retour posee PENDANT un geste (Chrome ignorait celle du chargement)')
rep("""  if (GARDE.pret) return; GARDE.pret = true;
  espGardeArmer();""", """  if (GARDE.pret) return; GARDE.pret = true;
  // v2.97.0 : posee PENDANT un geste (toucher / touche) -- posee au chargement, Chrome la jugeait ignorable (journal du Fold)
  const auGeste = () => { if (!GARDE.arme && Date.now() - GARDE.t > 2500) espGardeArmer(); };
  addEventListener("pointerdown", auGeste, true); addEventListener("keydown", auGeste, true);""")
rep("""    if (!$("choix").hidden) return;                                   // l'ecran « choix » gere son propre retour
    GARDE.arme = false; GARDE.t = Date.now();
    toast("↩ refais retour pour quitter l'application secondaire");""", """    if (!$("choix").hidden) return;                                   // l'ecran « choix » gere son propre retour
    GARDE.arme = false; GARDE.t = Date.now();
    toast("↩ refais retour pour quitter l'application secondaire");""")
rep("""  });
}
setTimeout(() => { if (window.__resteEchec""", """  }, true);                                                            // v2.97.0 : AVANT l'ecran « choix » (il se ferme)
}
setTimeout(() => { if (window.__resteEchec""")
rep("""    clearTimeout(GARDE.minuteur);
    GARDE.minuteur = setTimeout(() => { if (!GARDE.arme) espGardeArmer(); }, 2500);   // pas de 2e retour : la garde revient""",
    """    // v2.97.0 : reposee au PROCHAIN geste (apres 2,5 s) -- une minuterie, sans geste, serait ignoree par Chrome""")
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
