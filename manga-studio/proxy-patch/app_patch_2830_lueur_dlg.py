# -*- coding: utf-8 -*-
"""v2.83.0 (27/09, R8 -- Quang 11h41 : « un minimum d'interaction visuelle pour savoir a quelle etape on en est […] apres la
preparation, le bouton Generer les voix pourrait scintiller, comme le bouton Narration ») : la LUEUR de l'etape suivante (meme
animation que `cl-suiv`) dans les Dialogues. UNE etape a la fois : ✏ Corriger (s'il reste « ⚠ a traiter » ou un doublon probable :
on corrige AVANT de payer des voix) -> 🔊 Generer -> ▶ Lire (tant que les voix pretes n'ont pas ete ecoutees sur cet appareil)
-> 🎬 Video (absente ou a refaire pour la portee). Rien tant que le chapitre n'a jamais ete prepare (pas de concurrence avec la
Narration), rien pendant un traitement. Ou : en-tete replie du bloc, boutons du bloc, pied de l'ecran ✏. Suppose v2.82.4. Rejouable."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v2.83.0" in s[:400]:
    print("deja applique"); sys.exit(0)
if "v2.82.4" not in s[:400]:
    print("ERREUR : appliquer d'abord app_patch_2824_video_lecteur_app.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


rep("<title>Manga Studio v2.82.4</title>", "<title>Manga Studio v2.83.0</title>")
rep('<span class="ver" id="verBadge">v2.82.4</span>', '<span class="ver" id="verBadge">v2.83.0</span>')
rep('const VERSION = "2.82.4";', 'const VERSION = "2.83.0";   // v2.83.0 : lueur de l etape suivante des Dialogues (R8)')
rep("""@media (prefers-reduced-motion:reduce){.cl-act .btn.cl-suiv{animation:none}}""",
    """@media (prefers-reduced-motion:reduce){.cl-act .btn.cl-suiv{animation:none}}
/* v2.83.0 (R8) : la meme lueur pour l'etape suivante des Dialogues (bloc, en-tete replie, pied de l'ecran ✏) */
.btn.dlg-suiv{animation:clLueur 2.2s ease-in-out infinite;outline:1px solid rgba(255,210,90,.6)}
@media (prefers-reduced-motion:reduce){.btn.dlg-suiv{animation:none}}""")
# --- l'etape suivante + la pose de la lueur
rep("""function dlgPlagesTxt(ns){""", """// v2.83.0 (R8) : l'etape suivante des Dialogues du chapitre ouvert -- "" = rien ne brille
const dlgLuCle = d => "manga_dlg_lu:" + d;
function dlgSuivante(){
  const e = DLG.e, p = DLG.plan;
  if (!e || !e.doc || DLG.d !== CHAP_OPEN || e.en_cours || (DLG.lot && DLG.lot.en_cours)) return "";   // jamais prepare / occupe
  const trait = p ? Object.values(p.repliques || {}).filter(x => x === "a_traiter").length : 0;
  if (trait || dlgDoublons().length) return "ouvrir";                        // corriger AVANT de payer des voix
  if (p && p.a_faire) return dlgCreditsManquent() ? "" : "voix";
  if (!p || !p.deja) return "";
  let lu = 0; try { lu = +localStorage.getItem(dlgLuCle(DLG.d)) || 0; } catch (err) {}
  if (lu < p.deja) return "lire";                                            // des voix pretes pas encore ecoutees ici
  const vids = dlgVideos(e.doc, p), k = DLG.portee === "pages" ? dlgPorteeTxt() : "tout";
  return !vids[k] || vids[k].etat === "perimee" ? "video" : "";
}
function dlgLueur(){
  const suiv = dlgSuivante();
  const cible = { ouvrir: ["#dlgOuvrir", ".cl-tete[data-cl=dlg] [data-dlg=ouvrir]"],
                  voix: ["#dlgVoix", ".cl-tete[data-cl=dlg] [data-dlg=voix]", "#dlgpGen"],
                  lire: ["#dlgLire", ".cl-tete[data-cl=dlg] [data-dlg=lire]", "#dlgpLire"],
                  video: ["#dlgVid"] }[suiv] || [];
  const on = new Set(cible.map(q => document.querySelector(q)).filter(b => b && !b.disabled));
  document.querySelectorAll(".btn.dlg-suiv").forEach(b => { if (!on.has(b)) b.classList.remove("dlg-suiv"); });
  on.forEach(b => b.classList.add("dlg-suiv"));
  return suiv;
}
function dlgMarquerLu(){ try { if (DLG.d && DLG.plan) localStorage.setItem(dlgLuCle(DLG.d), String(DLG.plan.deja || 0)); } catch (err) {} }
function dlgPlagesTxt(ns){""")
# posee apres chaque rendu du bloc (clMaj tourne toutes les 800 ms) et du pied de l'ecran ✏
rep("""    if (b && h.dataset.cl === suiv) b.classList.add("cl-suiv");
  });
}""", """    if (b && h.dataset.cl === suiv) b.classList.add("cl-suiv");
  });
  if (typeof dlgLueur === "function") dlgLueur();                                      // v2.83.0 (R8)
}""")
rep("""  if ($("dlgpLire")) $("dlgpLire").onclick = () => $("dlgLire").click();""",
    """  if ($("dlgpLire")) $("dlgpLire").onclick = () => $("dlgLire").click();
  dlgLueur();                                                                            // v2.83.0 (R8)""")
# ▶ Lire (bloc, en-tete, pied ✏ : tous passent par #dlgLire) = les voix pretes sont ecoutees
rep("""$("dlgLire").onclick = () => (typeof dlgLecteur === "function" ? dlgLecteur() : toast("lecteur : prochaine étape"));""",
    """$("dlgLire").onclick = () => { dlgMarquerLu(); return typeof dlgLecteur === "function" ? dlgLecteur() : toast("lecteur : prochaine étape"); };   // v2.83.0 : lu""")
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
