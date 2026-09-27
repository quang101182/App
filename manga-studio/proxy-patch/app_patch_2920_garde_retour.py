# -*- coding: utf-8 -*-
"""v2.92.0 (27/09, Quang 14h07 : « pour le retour, oui, tu peux rajouter le refaire retour pour quitter la secondaire, si
jamais je fais ca par accident ») : journal du Fold (14h03) -- la secondaire est une application a part ; le geste retour sur
son ecran racine la FERME et Android reaffiche la principale. Desormais, dans l'application SECONDAIRE seulement : une entree
d'historique de GARDE ; le 1er retour qui atteint la racine affiche « ↩ refais retour pour quitter » et laisse 2,5 s ; un 2e
retour dans ce delai = sortie normale (Android). Passe ce delai, la garde se rearme. Cohabite avec l'ecran « choix du manga »
(son entree {choix} se ferme d'abord, comme avant). Principale : inchangee. Suppose v2.91.0. Rejouable."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v2.92.0" in s[:400]:
    print("deja applique"); sys.exit(0)
if "v2.91.0" not in s[:400]:
    print("ERREUR : appliquer d'abord app_patch_2910_defauts_curseurs.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


rep("<title>Manga Studio v2.91.0</title>", "<title>Manga Studio v2.92.0</title>")
rep('<span class="ver" id="verBadge">v2.91.0</span>', '<span class="ver" id="verBadge">v2.92.0</span>')
rep('const VERSION = "2.91.0";', 'const VERSION = "2.92.0";   // v2.92.0 : secondaire -- « refais retour pour quitter » (le geste retour ne la ferme plus par accident)')
rep("""  if (ESPACE.nom === "prive"){ DIRECT.ok = false; espDiscretion(); voixRemplir(); }""",
    """  if (ESPACE.nom === "prive"){ DIRECT.ok = false; espDiscretion(); voixRemplir(); espGardeRetour(); }   // v2.92.0""")
rep("""let ESP_DISCRETION = false;""", """/* v2.92.0 : secondaire -- un retour accidentel a la racine ne la ferme plus (1er = avertissement, 2e dans les 2,5 s = sortie) */
const GARDE = { arme: false, t: 0, minuteur: 0 };
function espGardeArmer(){ try { if (!(history.state && history.state.garde)) history.pushState({ garde: 1 }, ""); GARDE.arme = true; } catch (e) {} }
function espGardeRetour(){
  if (GARDE.pret) return; GARDE.pret = true;
  espGardeArmer();
  addEventListener("popstate", e => {
    if (e.state && (e.state.garde || e.state.choix)) return;          // on revient sur la garde (ex. choix du manga ferme) : rien
    if (!$("choix").hidden) return;                                   // l'ecran « choix » gere son propre retour
    GARDE.arme = false; GARDE.t = Date.now();
    toast("↩ refais retour pour quitter l'application secondaire");
    clearTimeout(GARDE.minuteur);
    GARDE.minuteur = setTimeout(() => { if (!GARDE.arme) espGardeArmer(); }, 2500);   // pas de 2e retour : la garde revient
  });
}
let ESP_DISCRETION = false;""")
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
