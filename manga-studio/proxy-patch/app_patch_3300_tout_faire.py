# -*- coding: utf-8 -*-
"""v3.3.0 (27/09, Quang 17h43 « un bouton special pour tout traiter d'un coup apres avoir traite les bulles » ; 17h51 « oui go »
pour l'arret avant les voix si l'IA doute) -- « ⚡ Tout faire » : dans les etapes d'une plage des qu'il reste quelque chose
(preparation depassee, voix a faire, video absente ou a refaire) ; dans la verification des bulles, « ✓ Valider et tout
faire ». Serveur : dialogues.py 1.21.0 (« tout ») + patch_dialogues_14. Arret « doute » explique dans le bloc (✏ en lueur).
Suppose v3.2.0. Rejouable."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v3.3.0" in s[:900]:
    print("deja applique"); sys.exit(0)
if "v3.2.0" not in s[:1400]:
    print("ERREUR : appliquer d'abord app_patch_3200_prep_depassee.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:80], s.count(a))
    s = s.replace(a, b)


rep("<title>Manga Studio v3.2.0</title>", "<title>Manga Studio v3.3.0</title>")
rep('<span class="ver" id="verBadge">v3.2.0</span>', '<span class="ver" id="verBadge">v3.3.0</span>')
rep('const VERSION = "3.2.0";', 'const VERSION = "3.3.0";   // v3.3.0 : ⚡ Tout faire (repliques -> arret si doute -> voix -> video)')

# dlgLancer : « tout » (traduction demandee comme pour preparer, option sans preparation)
rep("""async function dlgLancer(action){""", """async function dlgLancer(action, opts){
  opts = opts || {};""")
rep("""      const manq = action === "preparer" ? dlgManquantes() : [];                 // v2.81.5 : traduire d'abord, sur accord""",
    """      const manq = action === "preparer" || (action === "tout" && !opts.sansPrep) ? dlgManquantes() : [];   // v2.81.5 ; v3.3.0 : « tout »""")
rep("""      const r = await api("/manga/dialogues_lancer", Object.assign({ d: CHAP_OPEN, action, pages }, manq.length ? { traduire: true } : {}));
      if (r.error) throw new Error(r.error);
      toast(action === "voix" ? "🔊 voix lancées" : "🎭 préparation lancée");""",
    """      const r = await api("/manga/dialogues_lancer", Object.assign({ d: CHAP_OPEN, action, pages }, manq.length ? { traduire: true } : {}, opts.sansPrep ? { sans_preparation: true } : {}));
      if (r.error) throw new Error(r.error);
      toast(action === "voix" ? "🔊 voix lancées" : action === "tout" ? "⚡ tout lancé : répliques, voix, vidéo (arrêt si l'IA doute)" : "🎭 préparation lancée");""")

# verification des bulles : « ✓ Valider et tout faire »
rep("""  $("dlvGo").innerHTML = der ? (DLV.nouv ? "✓ Valider et préparer<small>p. " + esc(DLV.portee)""",
    """  $("dlvGo").innerHTML = der ? (DLV.nouv ? "✓ Valider et tout faire<small>répliques · voix · vidéo · p. " + esc(DLV.portee)""")
rep("""  if (DLV.nouv){ toast("🔍 bulles vérifiées — préparation lancée"); dlgLancer("preparer"); }""",
    """  if (DLV.nouv){ toast("🔍 bulles vérifiées"); dlgLancer("tout"); }                // v3.3.0 : tout d'un coup, arret si doute""")
rep("""    if (confirm("Tes bulles ont changé : refaire la préparation de " + dplTitre(dplCle()) + " maintenant ? (≈ " + fmtUsd(0.004 * DLV.pages.length) + ")\\n\\n"
        + "Les voix dont le texte ne change pas sont gardées (aucun crédit repayé) ; les autres passeront « à refaire », la vidéo aussi.")) dlgLancer("preparer");""",
    """    if (confirm("Tes bulles ont changé : tout refaire pour " + dplTitre(dplCle()) + " maintenant ? (répliques ≈ " + fmtUsd(0.004 * DLV.pages.length) + ", puis voix, puis vidéo)\\n\\n"
        + "Les voix dont le texte ne change pas sont gardées (aucun crédit repayé). Arrêt avant les voix si l'IA a un doute ; arrêt net si le quota ElevenLabs tombe.")) dlgLancer("tout");""")

JS = r"""/* ---- v3.3.0 : ⚡ TOUT FAIRE (repliques -> arret si doute -> voix -> video) ---- */
function dplReste(k){                              // ce qu'il reste a faire sur la plage k
  const e = DLG.e || {}, p = DLG.plan || {}, x = dplInfo(k), dep = dplDepasse(k).length > 0;
  return { dep, prep: !x.reps || dep, voix: !!p.a_faire || dep, video: !x.v || x.v.etat === "perimee" || dep };
}
async function dplToutFaire(){
  const k = dplCle(), r = dplReste(k), p = DLG.plan || {}, s = DLG.solde && DLG.solde.ok ? DLG.solde.restants : null;
  if (!r.prep && !r.voix && !r.video) return toast("rien à faire : tout est à jour");
  if (!r.prep && dlgCreditsManquent()) return toast("il faut ≈ " + fmtCr(p.credits) + " crédits, il en reste " + fmtCr(s) + " — aucun autre moteur");
  const [a, b] = dplBornes(k), n = Math.max(1, Math.min(b, CHAP_PAGES || b) - a + 1);
  const lignes = [(r.prep ? "· répliques : ≈ " + fmtUsd(0.004 * n) : "· répliques : déjà à jour"),
                  "· voix : " + (r.prep ? "calculées après la préparation" : p.a_faire ? p.a_faire + " à faire (≈ " + fmtCr(p.credits) + " crédits" + (s !== null ? ", reste " + fmtCr(s) : "") + ")" : "déjà faites"),
                  "· vidéo de " + dplTitre(k)];
  if (!confirm("⚡ Tout faire pour " + dplTitre(k) + " ?\n\n" + lignes.join("\n") + "\n\nArrêt avant les voix si l'IA a un doute (✏ te le dira) ; arrêt net si le quota ElevenLabs tombe.")) return;
  dlgLancer("tout", { sansPrep: !r.prep });
}
{ const _dr4 = dplRendre; dplRendre = function(){
    _dr4.apply(this, arguments);
    const et = $("dplEtapes"); if (!et) return;
    let t = $("dplTout"); if (!t){ t = document.createElement("button"); t.id = "dplTout"; t.className = "btn sm"; t.onclick = dplToutFaire; }
    const ks = dplListe(), cle = dplCle(), connue = ks.includes(cle) && !DPL.nouv, occupe = !!((DLG.e && DLG.e.en_cours) || (DLG.lot && DLG.lot.en_cours));
    const r = connue ? dplReste(cle) : null;
    t.hidden = !connue || occupe || !(r.prep || r.voix || r.video);
    if (!t.hidden){ et.append(t); t.textContent = "⚡ Tout faire"; t.title = "répliques · voix · vidéo, avec arrêt si l'IA doute"; }
    const pr = (DLG.e || {}).progress || {};                                    // arret « doute » : dit clairement, ✏ en lueur
    if (pr.etape === "doute" && !(DLG.e || {}).en_cours){
      const el = $("dlgEtat"); if (el && !el.querySelector(".dpl-doute"))
        el.insertAdjacentHTML("beforeend", '<div class="dpl-doute" style="color:#e8a84a;margin-top:4px">⏸ arrêté avant les voix : ' + esc(pr.arret || "l'IA a un doute")
          + " — règle-le dans ✏, puis ⚡ Tout faire</div>");
      const o = $("dlgOuvrir"); if (o && !o.hidden) o.classList.add("dlg-suiv");
    }
  }; }

"""
rep("/* ---- l'ecran de preparation : distribution du MANGA + repliques du chapitre ---- */",
    JS + "/* ---- l'ecran de preparation : distribution du MANGA + repliques du chapitre ---- */")
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok v3.3.0")
