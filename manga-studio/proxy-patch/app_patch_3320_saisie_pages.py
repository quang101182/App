# -*- coding: utf-8 -*-
"""v3.3.2 (27/09, Quang 18h37, PC : « des que je tape un chiffre, ca sort le focus de la cellule ») : chaque frappe dans
« de / a » d'une nouvelle plage redessinait la liste des plages (innerHTML) et DEPLACAIT les champs -> focus perdu.
Pendant la saisie, la liste n'est plus redessinee : seuls les libelles suivent. Suppose v3.3.1. Rejouable."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v3.3.2" in s[:900]:
    print("deja applique"); sys.exit(0)
if "v3.3.1" not in s[:1400]:
    print("ERREUR : appliquer d'abord app_patch_3310_tout_refaire.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"
def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:80], s.count(a))
    s = s.replace(a, b)
rep("<title>Manga Studio v3.3.1</title>", "<title>Manga Studio v3.3.2</title>")
rep('<span class="ver" id="verBadge">v3.3.1</span>', '<span class="ver" id="verBadge">v3.3.2</span>')
rep('const VERSION = "3.3.1";', 'const VERSION = "3.3.2";   // v3.3.2 : taper les pages d une nouvelle plage ne fait plus perdre le curseur')
rep('''  // AVANT de redessiner : mettre a l'abri les VRAIS boutons et champs (sinon innerHTML les detruit)
  const abri = box.querySelector('.dlg-p[data-portee="pages"]');
  if ($("dplEtapes") && L.contains($("dplEtapes"))) box.appendChild($("dplEtapes"));
  if (L.contains($("dlgDe"))){ abri.textContent = "Des pages : de "; abri.append($("dlgDe"), " à ", $("dlgA")); }
  L.innerHTML = h;
  // les VRAIS boutons et champs, deplaces (gestionnaires et regles d'avant intacts)
  const ici = $("dplEtapesIci");
  let et = $("dplEtapes"); if (!et){ et = document.createElement("div"); et.id = "dplEtapes"; et.className = "dpl-etapes"; }
  ici.replaceWith(et);
  if ($("dplChamps")) $("dplChamps").append($("dlgDe"), " à ", $("dlgA"));''',
    '''  // v3.3.2 : on TAPE dans « de / a » -> rien n'est redessine (sinon les champs bougent et perdent le curseur)
  const saisie = !connue && !!(document.activeElement && $("dplChamps") && $("dplChamps").contains(document.activeElement) && $("dplEtapes"));
  let et = $("dplEtapes");
  if (!saisie){
  // AVANT de redessiner : mettre a l'abri les VRAIS boutons et champs (sinon innerHTML les detruit)
  const abri = box.querySelector('.dlg-p[data-portee="pages"]');
  if ($("dplEtapes") && L.contains($("dplEtapes"))) box.appendChild($("dplEtapes"));
  if (L.contains($("dlgDe"))){ abri.textContent = "Des pages : de "; abri.append($("dlgDe"), " à ", $("dlgA")); }
  L.innerHTML = h;
  // les VRAIS boutons et champs, deplaces (gestionnaires et regles d'avant intacts)
  const ici = $("dplEtapesIci");
  if (!et){ et = document.createElement("div"); et.id = "dplEtapes"; et.className = "dpl-etapes"; }
  ici.replaceWith(et);
  if ($("dplChamps")) $("dplChamps").append($("dlgDe"), " à ", $("dlgA"));
  }''')
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok v3.3.2")
