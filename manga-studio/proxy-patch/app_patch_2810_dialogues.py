# -*- coding: utf-8 -*-
"""Manga Studio v2.81.0 -- mode « DIALOGUES » dans l'app (ROADMAP 4-septdecies D4 + D5 ; maquette_dialogues_v2 validee par
Quang le 26/09/2026 23h58). Ajoute : le bloc 🎭 Dialogues (fiche du chapitre, apres Narration), l'ecran de preparation
(distribution du MANGA + repliques par page, ecoute, corrections), la ligne ElevenLabs dans le detail des couts, les libelles
d'activite. Le lecteur (D6) est un patch a part. Rejouable : python app_patch_2810_dialogues.py <manga_studio.html>"""
import io, sys

P = sys.argv[1]
s = io.open(P, encoding="utf-8", newline="").read()
if "MODE « DIALOGUES »" in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"


def rep(a, b, n=1):
    global s
    a, b = a.replace("\n", NL), b.replace("\n", NL)
    assert s.count(a) == n, ("ancre", s.count(a), a[:90])
    s = s.replace(a, b)


# ------------------------------------------------------------------ version (3 endroits)
rep("<title>Manga Studio v2.80.0</title>", "<title>Manga Studio v2.81.0</title>")
rep('id="verBadge">v2.80.0</span>', 'id="verBadge">v2.81.0</span>')
rep('const VERSION = "2.80.0";', 'const VERSION = "2.81.0";   // v2.81.0 : mode « Dialogues » (une voix par personnage, ElevenLabs v3)')

# ------------------------------------------------------------------ CSS
CSS = r'''
/* v2.81.0 : MODE « DIALOGUES » (maquette_dialogues_v2) -- liseré vert d'eau, écran de préparation plein écran */
.narr-box.bloc-dlg{border-left:4px solid #3fc7a8}
.dlg-portee{display:flex;flex-wrap:wrap;gap:6px;margin:4px 0 8px}
.dlg-p{border:1px solid var(--line);border-radius:8px;padding:5px 9px;font-size:13px;cursor:pointer;display:inline-flex;gap:5px;align-items:center;flex-wrap:wrap}
.dlg-p.on{border-color:#3fc7a8;color:#8fe6cf}.dlg-p input{width:62px;padding:3px 5px}
.dlg-opts{display:flex;flex-wrap:wrap;gap:6px 14px;margin:2px 0 8px;font-size:13px}.dlg-opts label{display:inline-flex;gap:6px;align-items:center}
.dlg-etat{font-size:13px;color:var(--dim);margin:4px 0 8px}.dlg-etat b{color:var(--txt)}
.dlg-pill{font-size:11.5px;border:1px solid var(--line);border-radius:99px;padding:1px 7px;color:var(--dim);white-space:nowrap}
.dlg-pill.cr{border-color:#2d7f6c;color:#8fe6cf}.dlg-pill.ko{border-color:#8a3530;color:#ff9d96}
#dlgPrep{position:fixed;inset:0;z-index:85;background:var(--bg);overflow-y:auto;overscroll-behavior:contain}
#dlgPrep[hidden]{display:none}
.dlgp-haut{position:sticky;top:0;z-index:2;display:flex;align-items:center;gap:8px;flex-wrap:wrap;padding:10px 16px;background:#0c0e13ee;border-bottom:1px solid var(--line)}
.dlgp-corps{max-width:1100px;margin:0 auto;padding:10px 16px 110px}
.dlgp-corps h3{font-size:15px;margin:16px 0 6px}.dlgp-corps h3 .muted{font-weight:400;font-size:12.5px}
.dlgp-persos{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:10px}
.dlgp-carte{border:1px solid var(--line);border-top:4px solid;border-radius:12px;background:var(--panel2);padding:10px;min-width:0}
.dlgp-carte .n{display:flex;align-items:center;gap:6px}.dlgp-carte .n input{flex:1;min-width:0;font-weight:700}
.dlgp-carte label{display:block;font-size:12px;color:var(--dim);margin:7px 0 3px}
.dlgp-carte select{width:100%;min-width:0}.dlgp-ligne{display:flex;gap:6px;align-items:center}.dlgp-ligne select{flex:1}
.dlgp-fiche{font-size:12px;color:var(--dim);margin-top:2px}
.dlgp-seg{display:flex;gap:4px}.dlgp-seg button{flex:1;font-size:12.5px;padding:5px 4px}.dlgp-seg button.on{border-color:#3fc7a8;color:#8fe6cf}
.dlgp-coul{display:flex;gap:6px;flex-wrap:wrap}.dlgp-coul i{width:20px;height:20px;border-radius:99px;cursor:pointer;border:2px solid transparent;display:inline-block}
.dlgp-coul i.on{border-color:#fff}
.dlg-pastille{width:12px;height:12px;border-radius:99px;display:inline-block;flex:none}
.dlgp-page{display:flex;align-items:center;gap:10px;margin:14px 0 4px;color:var(--dim);font-size:13px}
.dlgp-page img{width:38px;height:54px;object-fit:cover;border-radius:4px;border:1px solid var(--line)}
.dlgp-rep{display:grid;grid-template-columns:24px minmax(130px,170px) 1fr minmax(110px,180px) 36px 24px;gap:8px;align-items:center;padding:6px 4px;border-bottom:1px solid var(--line)}
.dlgp-rep.off{opacity:.45}.dlgp-rep input[type=text]{width:100%;min-width:0}.dlgp-rep .txt.mod{border-color:#e0a63f}
.dlgp-rep .qui{display:flex;gap:6px;align-items:center;min-width:0}.dlgp-rep .qui select{flex:1;min-width:0}
.dlgp-rep .st{text-align:center;font-size:14px}.dlgp-rep .traiter{grid-column:2/-1;font-size:12px;color:#f0c46b}
.dlgp-rep .orig{grid-column:3/-1;font-size:11.5px;color:var(--dim)}
.dlgp-pied{position:fixed;left:0;right:0;bottom:0;z-index:3;display:flex;flex-wrap:wrap;gap:8px;align-items:center;padding:10px 16px;background:#0c0e13f2;border-top:1px solid var(--line)}
.dlgp-pied .muted{font-size:12.5px}
@media (max-width:700px){
  .dlgp-rep{grid-template-columns:24px 1fr 36px;grid-template-areas:"l q p" "l t t" "l n s";row-gap:4px}
  .dlgp-rep .c-l{grid-area:l}.dlgp-rep .qui{grid-area:q}.dlgp-rep .txt{grid-area:t}.dlgp-rep .ton{grid-area:n}.dlgp-rep .c-p{grid-area:p}.dlgp-rep .st{grid-area:s}
  .dlgp-rep .traiter,.dlgp-rep .orig{grid-column:1/-1}.dlgp-persos{grid-template-columns:1fr}}
'''
rep(".cl-box:not(.cl-ouv) > :not(.cl-tete){display:none}", ".cl-box:not(.cl-ouv) > :not(.cl-tete){display:none}" + CSS)

# ------------------------------------------------------------------ HTML : le bloc, juste apres la narration
HTML = '''    <!-- DIALOGUES (v2.81.0, maquette_dialogues_v2) : une voix par personnage (ElevenLabs v3), SEPARE de la narration -->
    <div class="narr-box bloc-dlg" id="dlgBox">
      <div class="bloc-titre">🎭 Dialogues</div>
      <div class="dlg-portee">
        <span class="dlg-p on" data-portee="chap">Ce chapitre</span>
        <span class="dlg-p" data-portee="pages">Des pages : de <input type="number" id="dlgDe" min="1"> à <input type="number" id="dlgA" min="1"></span>
        <span class="dlg-p" data-portee="lot">Plusieurs chapitres : du ch. <input type="number" id="dlgLotDe" step="any"> au ch. <input type="number" id="dlgLotA" step="any"></span>
      </div>
      <div class="dlg-opts">
        <label><input type="checkbox" id="dlgTons"> Tons par réplique</label>
        <label><input type="checkbox" id="dlgNarr"> Lire les encarts (narrateur)</label>
        <label id="dlgEnchL" hidden><input type="checkbox" id="dlgEnch"> Enchaîner les voix sans relecture</label>
      </div>
      <div class="dlg-etat" id="dlgEtat"></div>
      <div class="row" style="gap:6px;flex-wrap:wrap">
        <button class="btn sm pri" id="dlgPreparer">🎭 Préparer</button>
        <button class="btn sm" id="dlgOuvrir">✏ Corriger et régler</button>
        <button class="btn sm" id="dlgVoix">🔊 Générer les voix</button>
        <button class="btn sm" id="dlgLire">▶ Lire</button>
        <button class="btn sm" id="dlgArreter" hidden>✖ Arrêter</button>
      </div>
      <p class="muted" style="font-size:12px;margin:8px 0 0">Préparer = l'IA propose qui parle, le ton et ce qu'il faut lire (quelques dixièmes de centime par page) ;
        aucune voix n'est faite avant que tu lances « Générer ». Voix : ElevenLabs, payées en crédits de ton forfait —
        quota épuisé = arrêt, aucun autre moteur.</p>
    </div>
'''
rep("    <!-- TRADUCTION DES DIALOGUES (v1.84.0, etape 11 b)", HTML + "    <!-- TRADUCTION DES DIALOGUES (v1.84.0, etape 11 b)")

# ------------------------------------------------------------------ fiche compacte : 5e ligne, apres Narration
rep('''  { k: "narr", sel: "#chapDetail .narr-box.bloc-narr", ic: "🎙", t: "Narration" },''',
    '''  { k: "narr", sel: "#chapDetail .narr-box.bloc-narr", ic: "🎙", t: "Narration" },
  { k: "dlg",  sel: "#chapDetail .narr-box.bloc-dlg",  ic: "🎭", t: "Dialogues" },          // v2.81.0 : a part de la video''')
rep('''        + (b.k !== "vid" ? '<span class="cl-vers" title="utilisé par la vidéo">→ 🎬</span>' : "")          // v2.79.0''',
    '''        + (b.k !== "vid" && b.k !== "dlg" ? '<span class="cl-vers" title="utilisé par la vidéo">→ 🎬</span>' : "")   // v2.79.0 ; v2.81.0 : pas les Dialogues''')
rep('''function clEtat(k){
  if (k === "narr"){''', '''function clEtat(k){
  if (k === "dlg") return dlgEtat();                                        // v2.81.0
  if (k === "narr"){''')

# ------------------------------------------------------------------ ouverture d'un chapitre
rep('''  refreshNarrs().catch(err => log("narrations : " + err.message, "e"));''',
    '''  refreshNarrs().catch(err => log("narrations : " + err.message, "e"));
  dlgCharger();                                                              // v2.81.0 : mode Dialogues''')

# ------------------------------------------------------------------ activite, lancements, couts
rep('''                  precedemment: "Résumé", lot: "⚙ Traitement", essai: "🧪 Essai" };''',
    '''                  precedemment: "Résumé", lot: "⚙ Traitement", essai: "🧪 Essai",
                  dialogues: "🎭 Dialogues", dialogues_lot: "🎭 Dialogues (plusieurs chapitres)" };   // v2.81.0''')
rep('''const ACT_ETAPE = { noms: "repérage des personnages",''', '''const ACT_ETAPE = { preparation: "préparation (qui parle, ton)", noms: "repérage des personnages",''')
rep('''                            "/manga/precedemment", "/manga/ingest"]);''',
    '''                            "/manga/precedemment", "/manga/ingest", "/manga/dialogues_lancer", "/manga/dialogues_lot"]);''')
rep('''  verification: "vérification", fusion: "consensus", juge: "bancs de fidélité", precedemment: "« Précédemment… » et rattrapages" };''',
    '''  verification: "vérification", fusion: "consensus", juge: "bancs de fidélité", precedemment: "« Précédemment… » et rattrapages",
  dialogues: "🎭 dialogues (préparation)" };''')
rep('''    + '<table class="couts-t"><tr><th>Par moteur</th><th class="n">coût</th></tr>\'''',
    '''    + dlgCoutsEl(c)                                                            // v2.81.0 : ElevenLabs, en crédits
    + '<table class="couts-t"><tr><th>Par moteur</th><th class="n">coût</th></tr>\'''')

# ------------------------------------------------------------------ JS du mode
JS = r'''
/* ============ v2.81.0 : MODE « DIALOGUES » (maquette_dialogues_v2 ; ROADMAP 4-septdecies) ============
   Une voix par personnage (ElevenLabs v3), SEPARE de la narration : ses fichiers (<chap>/dialogues/, <serie>/dialogues_distribution.json),
   ses routes (/manga/dialogues*), son lecteur. Decisions de Quang : toujours lu en francais ; distribution = celle du MANGA ;
   corrections a la main avant/apres ; AUCUN moteur de secours (quota ElevenLabs epuise = arret, credits affiches). */
const DLG = { d: "", e: null, plan: null, solde: null, voix: null, lot: null, poll: null, portee: "chap", audio: new Audio() };
const DLG_EXPR = ["retenue", "naturelle", "expressive"];
const DLG_PAL = ["#ff5fa2", "#ffb347", "#6fb8ff", "#b58cff", "#5fe3a1", "#ff7a5c", "#f5e663", "#4fd6e8", "#e88aff", "#c7a17a"];
const fmtCr = n => Number(n || 0).toLocaleString("fr-FR");
async function dlgSolde(force){
  try { DLG.solde = await api("/manga/el_solde" + (force ? "?force=1" : "")); } catch (e) { DLG.solde = null; }
  return DLG.solde;
}
function dlgCoutsEl(c){
  const e = c && c.elevenlabs; if (!e) return "";
  const s = DLG.solde && DLG.solde.ok ? DLG.solde : null;
  return '<table class="couts-t"><tr><th>🎭 Dialogues — voix ElevenLabs</th><th class="n">crédits</th></tr>'
    + "<tr><td>aujourd'hui · ce mois · depuis le début</td><td class=\"n\">" + fmtCr(e.aujourdhui) + " · " + fmtCr(e.mois) + " · " + fmtCr(e.total) + "</td></tr>"
    + (s ? "<tr><td>restants sur ton forfait" + (s.renouvellement ? " (renouvellement le " + new Date(s.renouvellement * 1000).toLocaleDateString("fr-FR") + ")" : "")
         + '</td><td class="n">' + fmtCr(s.restants) + " / " + fmtCr(s.limite) + "</td></tr>" : "")
    + '<tr><td colspan="2" class="muted" style="font-size:12px">en crédits, pas en dollars : c\'est ton forfait ElevenLabs qui les paie</td></tr></table>';
}
async function dlgCharger(){
  const d = CHAP_OPEN; if (!d) return;
  DLG.d = d; clearTimeout(DLG.poll);
  try {
    const [e, lot] = await Promise.all([api("/manga/dialogues?d=" + encodeURIComponent(d)),
                                        api("/manga/dialogues_lot?serie=" + encodeURIComponent(serieDe(d))).catch(() => null)]);
    if (DLG.d !== d) return;
    DLG.e = e; DLG.lot = lot;
    DLG.plan = e.doc ? await api("/manga/dialogues_plan?d=" + encodeURIComponent(d)).catch(() => null) : null;
    if (!DLG.solde || (e.progress && e.progress.fini)) await dlgSolde(!!(e.progress && e.progress.fini));
  } catch (err) { log("dialogues : " + err.message, "w"); }
  dlgRendre();
  if (!$("dlgPrep").hidden) dlgPrepRendre();
  if ((DLG.e && DLG.e.en_cours) || (DLG.lot && DLG.lot.en_cours)) DLG.poll = setTimeout(dlgCharger, 2500);
}
function dlgCreditsManquent(){
  const p = DLG.plan, s = DLG.solde;
  return !!(p && s && s.ok && p.credits > s.restants);
}
function dlgEtat(){
  const e = DLG.e, p = DLG.plan, pr = (e && e.progress) || {}, lot = DLG.lot && DLG.lot.lot;
  const pastille = (t, cls) => '<span class="dlg-pill ' + (cls || "") + '">' + t + "</span>";
  const solde = DLG.solde && DLG.solde.ok ? " · reste " + fmtCr(DLG.solde.restants) : "";
  if (!e) return { etat: "…", est: "", act: "" };
  if (DLG.lot && DLG.lot.en_cours && lot){
    const ch = lot.chapitres || [];
    return { etat: "plusieurs chapitres en cours · " + ch.filter(x => x.etat === "fait").length + "/" + ch.filter(x => x.etat !== "non traduit").length
             + (lot.en_cours ? " · " + lot.en_cours.split("/").pop().replace("ch_", "ch. ") : ""), est: "",
             act: '<button class="btn sm" data-dlg="arreter">✖ Arrêter</button>' };
  }
  if (e.en_cours) return { etat: (pr.etape === "voix" ? "voix en cours" : "préparation en cours") + (pr.total ? " · " + (pr.fait || 0) + "/" + pr.total : "")
                           + (pr.credits ? " · " + fmtCr(pr.credits) + " crédits" : ""), est: "",
                           act: '<button class="btn sm" data-dlg="arreter">✖ Arrêter</button>' };
  if (!e.traduit) return { etat: "traduis d'abord ce chapitre en français", est: "", act: "" };
  const prep = pastille("≈ " + fmtUsd(0.005 * (CHAP_PAGES || 1)) + " préparation");
  if (!e.doc) return { etat: "pas encore préparé", est: prep, act: '<button class="btn sm pri" data-dlg="preparer">🎭 Préparer</button>' };
  const lues = p ? Object.values(p.repliques).filter(x => x !== "non_lue").length : 0;
  const trait = p ? Object.values(p.repliques).filter(x => x === "a_traiter").length : 0;
  let etat;
  if (pr.etape === "quota") etat = "quota ElevenLabs épuisé · " + (p ? p.deja : 0) + " voix sur " + (p ? p.deja + p.a_faire : "?");
  else if (p && p.a_faire) etat = p.deja ? p.a_faire + " à faire ou refaire · " + p.deja + " prêtes" : "préparé · " + p.a_faire + " répliques à mettre en voix";
  else etat = "prêts · " + lues + " répliques";
  if (trait) etat += " · ⚠ " + trait + " à traiter";
  const est = p && p.a_faire ? pastille("≈ " + fmtCr(p.credits) + " crédits" + solde, dlgCreditsManquent() ? "ko" : "cr") : "";
  const act = (p && p.a_faire ? '<button class="btn sm' + (dlgCreditsManquent() ? '" disabled' : ' pri"') + ' data-dlg="voix">🔊 Générer</button>' : "")
    + '<button class="btn sm" data-dlg="ouvrir">✏</button>'
    + (p && p.deja ? '<button class="btn sm' + (p.a_faire ? "" : " pri") + '" data-dlg="lire">▶ Lire</button>' : "");
  return { etat, est, act };
}
function dlgRendre(){
  const e = DLG.e || {}, dist = e.distribution || {}, p = DLG.plan, pr = e.progress || {};
  const x = dlgEtat();
  $("dlgEtat").innerHTML = "<b>" + esc(x.etat) + "</b> " + x.est
    + (pr.etape === "quota" || dlgCreditsManquent() ? '<br><span style="color:#ff9d96">Aucun autre moteur n\'est utilisé. Recharge des crédits sur ElevenLabs, ou attends le renouvellement de ton forfait.</span>' : "")
    + (pr.etape === "arrete" ? "<br>" + esc(pr.arret || "arrêté") + " — les voix déjà faites sont gardées." : "");
  $("dlgTons").checked = dist.tons !== false;
  $("dlgNarr").checked = !!(dist.narrateur && dist.narrateur.lire);
  const occupe = !!(e.en_cours || (DLG.lot && DLG.lot.en_cours));
  $("dlgArreter").hidden = !occupe;
  $("dlgPreparer").disabled = occupe || !e.traduit && DLG.portee !== "lot";
  $("dlgVoix").disabled = occupe || (DLG.portee !== "lot" && (!p || !p.a_faire || dlgCreditsManquent()));
  $("dlgOuvrir").disabled = !e.doc;
  $("dlgLire").disabled = !(p && p.deja);
  $("dlgEnchL").hidden = DLG.portee !== "lot";
  if (!$("dlgLotDe").value){ const c = CHAPS.find(y => y.dir === CHAP_OPEN); if (c){ $("dlgLotDe").value = c.chapter; $("dlgLotA").value = c.chapter; } }
  if (typeof clMaj === "function") clMaj();
}
document.querySelectorAll("#dlgBox .dlg-p").forEach(el => el.addEventListener("click", e => {
  DLG.portee = el.dataset.portee;
  document.querySelectorAll("#dlgBox .dlg-p").forEach(y => y.classList.toggle("on", y === el));
  dlgRendre();
}));
async function dlgRegler(corps){
  try {
    const r = await api("/manga/dialogues_distribution", Object.assign({ serie: serieDe(CHAP_OPEN) }, corps));
    if (r.error) throw new Error(r.error);
    if (DLG.e) DLG.e.distribution = r.distribution;
    if (r.renommes && Object.keys(r.renommes).length) toast("renommé : " + Object.entries(r.renommes).map(([a, b]) => a + " → " + b).join(", "));
  } catch (err) { toast("réglage non enregistré : " + err.message); }
  dlgCharger();
}
$("dlgTons").onchange = () => dlgRegler({ tons: $("dlgTons").checked });
$("dlgNarr").onchange = () => dlgRegler({ narrateur: { lire: $("dlgNarr").checked } });
async function dlgLancer(action){
  try {
    if (DLG.portee === "lot"){
      const de = parseFloat($("dlgLotDe").value), a = parseFloat($("dlgLotA").value);
      if (!(de <= a)) return toast("plage de chapitres invalide");
      const act = action === "preparer" && $("dlgEnch").checked ? "tout" : action;
      if (!confirm((act === "preparer" ? "Préparer" : act === "voix" ? "Générer les voix de" : "Préparer puis mettre en voix")
                   + " les chapitres " + de + " à " + a + " de cette série ?\n\nSeuls les chapitres traduits en français sont traités, dans l'ordre. "
                   + (act !== "preparer" ? "Si le quota ElevenLabs tombe (" + dlgSoldeTxt() + "), tout s'arrête net : ce qui est fait est gardé." : "")))
        return;
      const r = await api("/manga/dialogues_lot", { serie: serieDe(CHAP_OPEN), de, a, action: act });
      if (r.error) throw new Error(r.error);
      toast("🎭 dialogues : chapitres " + de + " à " + a + " lancés");
    } else {
      const pages = DLG.portee === "pages" ? (($("dlgDe").value || "1") + "-" + ($("dlgA").value || $("dlgDe").value || "1")) : "";
      if (action === "voix" && dlgCreditsManquent()) return toast("il faut ≈ " + fmtCr(DLG.plan.credits) + " crédits, il en reste " + fmtCr(DLG.solde.restants) + " — aucun autre moteur");
      const r = await api("/manga/dialogues_lancer", { d: CHAP_OPEN, action, pages });
      if (r.error) throw new Error(r.error);
      toast(action === "voix" ? "🔊 voix lancées" : "🎭 préparation lancée");
    }
    setTimeout(dlgCharger, 600);
  } catch (err) { toast("dialogues : " + err.message); }
}
function dlgSoldeTxt(){ const s = DLG.solde; return s && s.ok ? fmtCr(s.restants) + " crédits restants" : "solde inconnu"; }
async function dlgArreter(){
  try {
    if (DLG.lot && DLG.lot.en_cours) await api("/manga/dialogues_lot_arreter", { serie: serieDe(CHAP_OPEN) });
    else await api("/manga/dialogues_arreter", { d: CHAP_OPEN });
    toast("arrêté — ce qui est fait est gardé");
  } catch (err) { toast("arrêt : " + err.message); }
  setTimeout(dlgCharger, 500);
}
$("dlgPreparer").onclick = () => dlgLancer("preparer");
$("dlgVoix").onclick = () => dlgLancer("voix");
$("dlgArreter").onclick = dlgArreter;
$("dlgOuvrir").onclick = () => dlgPrepOuvrir();
$("dlgLire").onclick = () => (typeof dlgLecteur === "function" ? dlgLecteur() : toast("lecteur : prochaine étape"));
document.addEventListener("click", e => {
  const b = e.target.closest("[data-dlg]"); if (!b) return;
  e.stopPropagation();
  ({ preparer: () => dlgLancer("preparer"), voix: () => dlgLancer("voix"), arreter: dlgArreter, ouvrir: () => dlgPrepOuvrir(),
     lire: () => $("dlgLire").click() }[b.dataset.dlg] || (() => {}))();
}, true);

/* ---- l'ecran de preparation : distribution du MANGA + repliques du chapitre ---- */
const dlgPrep = document.createElement("div");
dlgPrep.id = "dlgPrep"; dlgPrep.hidden = true;
dlgPrep.innerHTML = '<div class="dlgp-haut"><button class="btn sm retour" id="dlgpRet">← Chapitre</button><b id="dlgpTitre">🎭 Dialogues</b>'
  + '<span style="flex:1"></span><span class="dlg-pill cr" id="dlgpSolde"></span></div><div class="dlgp-corps" id="dlgpCorps"></div>'
  + '<div class="dlgp-pied" id="dlgpPied"></div>';
document.body.appendChild(dlgPrep);
$("dlgpRet").onclick = () => { dlgPrep.hidden = true; document.body.style.overflow = ""; dlgCharger(); };
document.addEventListener("keydown", e => { if (e.key === "Escape" && !dlgPrep.hidden) $("dlgpRet").click(); });
async function dlgPrepOuvrir(){
  if (!DLG.e || !DLG.e.doc) return toast("prépare d'abord ce chapitre");
  if (!DLG.voix){ try { DLG.voix = ((await api("/manga/el_voix")).voix || []); } catch (e) { DLG.voix = []; } }
  dlgPrep.hidden = false; document.body.style.overflow = "hidden";
  dlgPrepRendre();
}
const dlgGenre = g => g === "female" ? "femme" : g === "male" ? "homme" : g || "?";
function dlgPersos(){
  const dist = (DLG.e && DLG.e.distribution) || { persos: [] };
  return (dist.persos || []).concat([Object.assign({ nom: "narrateur", narrateur: true }, dist.narrateur || {})]);
}
function dlgCouleur(nom){
  const p = dlgPersos().find(x => x.nom === nom);
  return (p && p.couleur) || "#8b93a7";
}
function dlgPrepRendre(){
  const e = DLG.e, doc = e && e.doc; if (!doc) return;
  const plan = (DLG.plan && DLG.plan.repliques) || {}, persos = dlgPersos(), c = CHAPS.find(y => y.dir === CHAP_OPEN);
  $("dlgpTitre").textContent = "🎭 Dialogues · " + (c ? c.title + " — ch. " + c.chapter : CHAP_OPEN);
  $("dlgpSolde").textContent = "ElevenLabs : " + dlgSoldeTxt();
  const lignes = doc.repliques || [];
  const optV = sel => DLG.voix.map(v => '<option value="' + esc(v.id) + '"' + (v.id === sel ? " selected" : "") + ">" + esc(v.nom + " — " + v.desc + " (" + dlgGenre(v.genre) + ")") + "</option>").join("")
    + (sel && !DLG.voix.some(v => v.id === sel) ? '<option value="' + esc(sel) + '" selected>' + esc(sel) + "</option>" : "") + (sel ? "" : '<option value="" selected>— à choisir —</option>');
  const phrases = nom => {
    const l = lignes.filter(x => /[\p{L}\p{N}]/u.test(x.texte || "")), a = l.filter(x => x.qui === nom).sort((u, v) => v.texte.length - u.texte.length), b = l.filter(x => x.qui !== nom);
    const o = x => '<option value="' + esc(x.cle) + '">' + esc((x.texte || "").slice(0, 70)) + "</option>";
    return (a.length ? '<optgroup label="Ses répliques">' + a.map(o).join("") + "</optgroup>" : "") + (b.length ? '<optgroup label="Autres phrases">' + b.map(o).join("") + "</optgroup>" : "");
  };
  let h = '<h3>Distribution du manga <span class="muted">— vaut pour <b>tous les chapitres</b> de la série · ' + (persos.length - 1) + ' personnage(s) · '
    + '<button class="btn sm" id="dlgpAjout">✚ ajouter</button></span></h3><div class="dlgp-persos">';
  persos.forEach((p, i) => {
    const coul = p.couleur || "#8b93a7";
    h += '<div class="dlgp-carte" data-p="' + i + '" style="border-top-color:' + esc(coul) + '"><div class="n"><span class="dlg-pastille" style="background:' + esc(coul) + '"></span>'
      + (p.narrateur ? "<b>Narrateur</b>" : '<input type="text" data-k="renomme" value="' + esc(p.nom) + '" title="renommer (l\'ancien nom reste reconnu)">')
      + "</div>" + (p.narrateur ? '<div class="dlgp-fiche">encarts de récit · ' + (p.lire ? "lus" : "<b>non lus</b> (case « Lire les encarts » du bloc)") + "</div>"
      : '<div class="dlgp-fiche">' + esc([p.genre, p.age, p.fiche].filter(Boolean).join(" · ")) + (p.alias && p.alias.length ? " · aussi : " + esc(p.alias.join(", ")) : "") + "</div>")
      + '<label>Voix</label><select data-k="voix_el">' + optV(p.voix_el) + "</select>"
      + '<label>Phrase à écouter</label><div class="dlgp-ligne"><select data-k="phrase">' + phrases(p.nom) + '</select><button class="btn sm" data-ecoute-p="' + i + '">▶</button></div>'
      + "<label>Expressivité</label><div class=\"dlgp-seg\">" + DLG_EXPR.map((t, k) => '<button class="btn sm' + ((p.expressivite ?? 1) === k ? " on" : "") + '" data-expr="' + k + '">' + t + "</button>").join("") + "</div>"
      + '<label>Vitesse de diction <b data-vit-v>' + Number(p.vitesse || 1.1).toFixed(2).replace(".", ",") + '</b></label><input type="range" data-k="vitesse" min="0.7" max="1.2" step="0.05" value="' + (p.vitesse || 1.1) + '" style="width:100%">'
      + (p.narrateur ? "" : '<label>Couleur</label><div class="dlgp-coul">' + DLG_PAL.map(k => '<i class="' + (k === coul ? "on" : "") + '" style="background:' + k + '" data-coul="' + k + '"></i>').join("") + "</div>")
      + "</div>";
  });
  h += "</div>";
  const aFaire = DLG.plan ? DLG.plan.a_faire : 0;
  h += '<h3>Répliques <span class="muted">(' + lignes.length + ' · ✅ voix faite · ⚪ à faire · 🟠 à refaire · ⚠ à traiter / sans voix)</span></h3>';
  const optQ = sel => persos.map(p => '<option' + (p.nom === sel ? " selected" : "") + ">" + esc(p.nom) + "</option>").join("") + '<option' + (sel === "inconnu" ? " selected" : "") + ">inconnu</option>";
  const ST = { faite: "✅", a_faire: "⚪", a_refaire: "🟠", sans_voix: "⚠", a_traiter: "⚠", non_lue: "·" };
  let page = null;
  lignes.forEach(x => {
    if (x.page !== page){
      page = x.page;
      const pg = (CHAP_PAGE_LIST || [])[page - 1];
      h += '<div class="dlgp-page">' + (pg ? '<img loading="lazy" src="' + pageSrc(pg.path) + '" alt="">' : "") + "Page " + page + "</div>";
    }
    const mod = (x.texte || "") !== (x.texte_origine || "");
    h += '<div class="dlgp-rep' + (x.lire ? "" : " off") + '" data-cle="' + esc(x.cle) + '">'
      + '<input type="checkbox" class="c-l" data-k="lire"' + (x.lire ? " checked" : "") + ' title="lire cette réplique">'
      + '<span class="qui"><span class="dlg-pastille" style="background:' + esc(dlgCouleur(x.qui)) + '"></span><select data-k="qui">' + optQ(x.qui) + "</select></span>"
      + '<input type="text" class="txt' + (mod ? " mod" : "") + '" data-k="texte" value="' + esc(x.texte || "") + '">'
      + '<input type="text" class="ton" data-k="ton" value="' + esc(x.ton || "") + '" placeholder="ton"' + ((e.distribution || {}).tons === false ? " disabled title=\"tons coupés\"" : "") + ">"
      + '<button class="btn sm c-p" data-ecoute-r="' + esc(x.cle) + '"' + (x.lire ? "" : " disabled") + ">▶</button>"
      + '<span class="st" title="' + esc(plan[x.cle] || "") + '">' + (ST[plan[x.cle]] || "·") + "</span>"
      + (x.a_traiter ? '<span class="traiter">⚠ page refusée par la modération : choisis toi-même qui parle, la réplique redeviendra lisible</span>' : "")
      + (mod ? '<span class="orig">d\'origine : « ' + esc(x.texte_origine || "") + ' » <a href="#" data-annuler="' + esc(x.cle) + '">↺ revenir</a></span>' : "")
      + "</div>";
  });
  $("dlgpCorps").innerHTML = h;
  const manque = dlgCreditsManquent();
  $("dlgpPied").innerHTML = e.en_cours ? '<b>' + esc(dlgEtat().etat) + '</b><button class="btn sm" data-dlg="arreter">✖ Arrêter</button>'
    : (aFaire ? '<button class="btn' + (manque ? '" disabled' : ' pri"') + ' id="dlgpGen">🔊 Générer les voix manquantes · ' + aFaire + '</button>'
       + '<span class="dlg-pill ' + (manque ? "ko" : "cr") + '">≈ ' + fmtCr(DLG.plan.credits) + " crédits · " + (DLG.solde && DLG.solde.ok ? "il en restera " + fmtCr(Math.max(0, DLG.solde.restants - DLG.plan.credits)) : "solde inconnu") + "</span>"
       + (manque ? '<span class="muted" style="color:#ff9d96">quota insuffisant — aucun autre moteur</span>' : "")
       : '<span class="muted">Toutes les voix sont à jour.</span>')
    + '<span style="flex:1"></span><button class="btn sm" id="dlgpLire"' + (DLG.plan && DLG.plan.deja ? "" : " disabled") + ">▶ Lire</button>";
  if ($("dlgpGen")) $("dlgpGen").onclick = () => { DLG.portee = "chap"; dlgLancer("voix"); };
  if ($("dlgpLire")) $("dlgpLire").onclick = () => $("dlgLire").click();
  if ($("dlgpAjout")) $("dlgpAjout").onclick = async () => {
    const nom = (prompt("Nom du personnage à ajouter :") || "").trim(); if (!nom) return;
    const g = (prompt("Homme ou femme ? (h / f)") || "").trim().toLowerCase();
    await dlgRegler({ ajouter: { nom, genre: g.startsWith("f") ? "femme" : g.startsWith("h") ? "homme" : "?" } });
  };
}
// reglages d'un personnage : enregistres a chaque changement (distribution du MANGA)
dlgPrep.addEventListener("change", async e => {
  const carte = e.target.closest(".dlgp-carte"), rep_ = e.target.closest(".dlgp-rep");
  if (carte){
    const p = dlgPersos()[+carte.dataset.p], k = e.target.dataset.k; if (!p || !k || k === "phrase") return;
    const m = { nom: p.nom };
    if (k === "renomme"){ const v = e.target.value.trim(); if (!v || v === p.nom) return; m.renomme = v; }
    else m[k] = k === "vitesse" ? +e.target.value : e.target.value;
    return dlgRegler(p.narrateur ? { narrateur: m } : { persos: [m] });
  }
  if (rep_){
    const k = e.target.dataset.k; if (!k) return;
    const corr = { cle: rep_.dataset.cle }; corr[k] = k === "lire" ? e.target.checked : e.target.value;
    try { const r = await api("/manga/dialogues_maj", { d: CHAP_OPEN, corrections: [corr] }); if (r.error) throw new Error(r.error); }
    catch (err) { toast("correction non enregistrée : " + err.message); }
    dlgCharger();
  }
});
dlgPrep.addEventListener("input", e => {
  if (e.target.dataset.k === "vitesse") e.target.closest(".dlgp-carte").querySelector("[data-vit-v]").textContent = Number(e.target.value).toFixed(2).replace(".", ",");
});
dlgPrep.addEventListener("click", async e => {
  const t = e.target;
  if (t.dataset.expr !== undefined){ const p = dlgPersos()[+t.closest(".dlgp-carte").dataset.p]; const m = { nom: p.nom, expressivite: +t.dataset.expr };
    return dlgRegler(p.narrateur ? { narrateur: m } : { persos: [m] }); }
  if (t.dataset.coul){ const p = dlgPersos()[+t.closest(".dlgp-carte").dataset.p]; return dlgRegler({ persos: [{ nom: p.nom, couleur: t.dataset.coul }] }); }
  if (t.dataset.annuler){ e.preventDefault();
    try { await api("/manga/dialogues_maj", { d: CHAP_OPEN, corrections: [{ cle: t.dataset.annuler, annuler: true }] }); } catch (err) { toast(err.message); }
    return dlgCharger(); }
  const ep = t.dataset.ecouteP, er = t.dataset.ecouteR;
  if (ep === undefined && er === undefined) return;
  const corps = { d: CHAP_OPEN };
  if (ep !== undefined){ const p = dlgPersos()[+ep]; corps.cle = t.closest(".dlgp-carte").querySelector('[data-k="phrase"]').value; corps.qui = p.nom; }
  else corps.cle = er;
  if (!corps.cle) return toast("aucune phrase à écouter");
  t.disabled = true; const avant = t.textContent; t.textContent = "…";
  try {
    const r = await api("/manga/dialogues_ecouter", corps);
    if (r.error) throw new Error(r.error);
    DLG.audio.src = srcURL(r.chemin); DLG.audio.play();
    if (r.credits) { toast("écoute : " + fmtCr(r.credits) + " crédits" + (r.definitive ? " (gardée comme voix de la réplique)" : "")); dlgSolde(true).then(() => dlgCharger()); }
  } catch (err) { toast("écoute : " + err.message); }
  finally { t.disabled = false; t.textContent = avant; }
});
'''
rep("document.body.appendChild($(\"coutsModal\"));", JS + NL + "document.body.appendChild($(\"coutsModal\"));")

io.open(P, "w", encoding="utf-8", newline="").write(s)
print("app patchee v2.81.0")
