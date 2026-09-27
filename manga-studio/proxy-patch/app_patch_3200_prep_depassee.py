# -*- coding: utf-8 -*-
"""v3.2.0 (27/09, Quang 17h43 : « j'ai retravaille les bulles, mais a aucun moment ca ne me propose de refaire la preparation,
les voix et la video ») -- PREPARATION DEPASSEE : l'app compare la verification des bulles (patch_dialogues_13) a la
preparation (ordre des repliques, bulles exclues encore presentes, bulles ajoutees absentes) ; en cas d'ecart : pastille
« 🟠 bulles modifiees » sur la plage, l'etape « ✓ Prepare » redevient « ↻ Preparer » (lueur) ; et en VALIDANT des bulles
modifiees d'une plage deja preparee, l'app PROPOSE de refaire la preparation tout de suite. La suite se recale seule :
dialogues.py 1.20.0 retire les repliques des bulles exclues, les voix dont le texte change passent « a refaire », celles
inchangees sont gardees, la video passe « a refaire » (empreinte). Suppose v3.1.1. Rejouable."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v3.2.0" in s[:900]:
    print("deja applique"); sys.exit(0)
if "v3.1.1" not in s[:1400]:
    print("ERREUR : appliquer d'abord app_patch_3110_dialogues_en_tete.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:80], s.count(a))
    s = s.replace(a, b)


rep("<title>Manga Studio v3.1.1</title>", "<title>Manga Studio v3.2.0</title>")
rep('<span class="ver" id="verBadge">v3.1.1</span>', '<span class="ver" id="verBadge">v3.2.0</span>')
rep('const VERSION = "3.1.1";', 'const VERSION = "3.2.0";   // v3.2.0 : bulles retouchees apres coup -> la preparation est dite depassee et proposee a refaire')

# en validant des bulles MODIFIEES d'une plage deja preparee : proposer de refaire tout de suite
rep("""  if (DLV.nouv){ toast("🔍 bulles vérifiées — préparation lancée"); dlgLancer("preparer"); }
  else { toast("🔍 bulles vérifiées et gardées" + (DLV.pages.some(p => p.modif) ? " — ⋯ › Refaire la préparation pour les appliquer" : "")); dlgRendre(); }""",
    """  if (DLG.e){ DLG.e.verif = Object.assign({}, DLG.e.verif || {}); Object.entries(pages).forEach(([k, v]) => { DLG.e.verif[k] = v; }); }   // v3.2.0
  if (DLV.nouv){ toast("🔍 bulles vérifiées — préparation lancée"); dlgLancer("preparer"); }
  else if (DLV.pages.some(p => p.modif) && dplDepasse(dplCle()).length){          // v3.2.0 : proposer de refaire TOUT DE SUITE
    dlgRendre();
    if (confirm("Tes bulles ont changé : refaire la préparation de " + dplTitre(dplCle()) + " maintenant ? (≈ " + fmtUsd(0.004 * DLV.pages.length) + ")\\n\\n"
        + "Les voix dont le texte ne change pas sont gardées (aucun crédit repayé) ; les autres passeront « à refaire », la vidéo aussi.")) dlgLancer("preparer");
    else toast("🟠 préparation à refaire — étape « ↻ Préparer » de la plage");
  }
  else { toast("🔍 bulles vérifiées et gardées"); dlgRendre(); }""")

JS = r"""/* ---- v3.2.0 : preparation DEPASSEE (bulles retouchees apres coup) ---- */
function dplDepasse(k){                           // pages de la plage dont la preparation ne suit plus la verification
  const e = DLG.e || {}, doc = e.doc, vf = e.verif || {}; if (!doc || !k || k === "lot") return [];
  const [a, b] = dplBornes(k), out = [];
  Object.keys(vf).map(Number).filter(n => n >= a && n <= b).forEach(n => {
    const v = vf[n] || {}, reps = (doc.repliques || []).filter(x => x.page === n).sort((x, y) => (x.ordre ?? x.id) - (y.ordre ?? y.id));
    const ids = reps.map(x => x.id), dans = new Set(ids), ov = (v.ordre || []).map(r => r.id), ovs = new Set(ov);
    const sv = ov.filter(i => dans.has(i)), sd = ids.filter(i => ovs.has(i));
    if (sv.join() !== sd.join() || (v.exclues || []).some(r => dans.has(r.id)) || (v.ajouts || []).some(r => !dans.has(r.id))) out.push(n);
  });
  return out;
}
{ const _dr3 = dplRendre; dplRendre = function(){
    _dr3.apply(this, arguments);
    const ks = dplListe(), cle = dplCle(), connue = ks.includes(cle) && !DPL.nouv;
    ks.forEach(k => { if (!dplDepasse(k).length) return;                      // pastille sur la carte de la plage
      const c = [...document.querySelectorAll("#dplListe .dpl")].find(x => x.dataset.k === k), m = c && c.querySelector(".m");
      if (m && !m.querySelector(".dpl-dep")) m.insertAdjacentHTML("afterbegin", '<span class="dpl-chip warn dpl-dep">🟠 bulles modifiées</span>'); });
    if (!connue) return;
    const dep = dplDepasse(cle), pr = $("dlgPreparer"), fait = $("dplPrepFait");
    if (dep.length && pr && fait){
      fait.hidden = true; pr.hidden = false; pr.classList.add("pri", "dlg-suiv"); pr.classList.remove("dpl-sansverif");
      pr.textContent = "↻ Préparer"; pr.title = "les bulles des p. " + dlgPlagesTxt(dep) + " ont changé depuis la préparation";
    } else if (pr) pr.classList.remove("dlg-suiv");
  }; }

"""
rep("/* ---- l'ecran de preparation : distribution du MANGA + repliques du chapitre ---- */",
    JS + "/* ---- l'ecran de preparation : distribution du MANGA + repliques du chapitre ---- */")
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok v3.2.0")
