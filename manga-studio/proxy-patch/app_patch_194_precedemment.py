# -*- coding: utf-8 -*-
"""App v1.93.0 -> v1.94.0 : « Precedemment... » + rattrapage (etape 7, decision Quang 22/09 08h40).

Panneau du chapitre : une ligne « 📜 Précédemment… » (fabriquer / refaire l'ouverture, ~0,013 $) et
« ⏪ Rattrapage » (les chapitres d'avant, ~0,03 $ par chapitre), etat 🟠 si une source a change.
Lecteur : case « 📜 » (memorisee par appareil, cochee par defaut) = l'ouverture joue AVANT la page 1 ;
bouton « ▶ Rattrapage puis ce chapitre ». Les pages de resume sont des pages comme les autres (voix,
sous-titres, karaoke au prorata, barre de temps), avec leur image et leur audio en chemin complet.
Ecoute a l'aveugle : jamais de resume (elle compare des narrations, rien d'autre).
Verifie ses ancres, sinon n'ecrit rien.
"""
import shutil
p = r"D:\Download\02-Apps-Web\Repo-github\App\manga-studio\manga_studio.html"
s = open(p, encoding="utf-8").read()


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:80])
    s = s.replace(a, b)


for a, b in (("<title>Manga Studio v1.93.0</title>", "<title>Manga Studio v1.94.0</title>"),
             ('id="verBadge">v1.93.0<', 'id="verBadge">v1.94.0<'),
             ('const VERSION = "1.93.0";', 'const VERSION = "1.94.0";')):
    rep(a, b)

# ---------- HTML ----------
rep('''      <div id="narrRuns" class="narr-runs"></div>''',
    '''      <div id="narrRuns" class="narr-runs"></div>
      <!-- v1.94.0 : « Precedemment... » (avant ce chapitre) et rattrapage (les chapitres d'avant) -->
      <div class="prec-box" id="precBox" hidden>
        <div class="trad-ligne"><span>📜 Précédemment…</span><span id="precOuvEtat" class="prec-etat"></span>
          <button class="btn sm" id="precOuvGen"></button></div>
        <div class="trad-ligne"><span>⏪ Rattrapage</span><span id="precRatEtat" class="prec-etat"></span>
          <button class="btn sm" id="precRatGen"></button>
          <button class="btn sm pri" id="precRatJouer" hidden title="écouter le rattrapage, puis ce chapitre enchaîne">▶ Rattrapage puis ce chapitre</button></div>
      </div>''')
rep('''    <label class="lec-chk" title="le mot prononcé s'allume"><input type="checkbox" id="lecKarOn"> karaoké</label>''',
    '''    <label class="lec-chk" title="le mot prononcé s'allume"><input type="checkbox" id="lecKarOn"> karaoké</label>
    <label class="lec-chk" id="lecPrecBox" title="« Précédemment… » avant la page 1 (s'il a été fabriqué)"><input type="checkbox" id="lecPrecOn"> 📜</label>''')
rep('''.trad-ligne{display:flex;align-items:center;gap:6px;flex-wrap:wrap}''',
    '''.trad-ligne{display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.prec-box{margin-top:10px;padding-top:8px;border-top:1px solid var(--line)}
.prec-etat{font-size:12px;color:var(--dim);flex:1;min-width:0}''')

# ---------- couts + activite ----------
rep('''  verification: "vérification", fusion: "consensus", juge: "bancs de fidélité" };''',
    '''  verification: "vérification", fusion: "consensus", juge: "bancs de fidélité", precedemment: "« Précédemment… » et rattrapages" };''')
rep('''const ACT_LBL = { narration: "Narration", traduction: "Traduction", karaoke: "Karaoké", capture: "Capture", video: "Vidéo" };''',
    '''const ACT_LBL = { narration: "Narration", traduction: "Traduction", karaoke: "Karaoké", capture: "Capture", video: "Vidéo",
                  precedemment: "Résumé" };''')
rep('''                    images: "images", son: "son", assemblage: "assemblage", attente: "en attente" };''',
    '''                    images: "images", son: "son", assemblage: "assemblage", attente: "en attente",
                    ouverture: "« Précédemment… »", rattrapage: "rattrapage" };''')
rep('''      if (x.d && x.d === CHAP_OPEN){ refreshNarrs().catch(() => {}); refreshTrads().catch(() => {}); }''',
    '''      if (x.d && x.d === CHAP_OPEN){ refreshNarrs().catch(() => {}); refreshTrads().catch(() => {}); refreshPrec().catch(() => {}); }''')
rep('''  refreshNarrs().catch(err => log("narrations : " + err.message, "e"));
  $("chapDetail").scrollIntoView''',
    '''  refreshNarrs().catch(err => log("narrations : " + err.message, "e"));
  refreshPrec().catch(err => log("précédemment : " + err.message, "w"));
  $("chapDetail").scrollIntoView''')

# ---------- JS : panneau ----------
rep('''/* ----- Lecteur : une file de narrations (1 = ecoute normale ; N = ecoute a l'aveugle) ----- */''',
    '''/* ----- v1.94.0 : « Precedemment... » + rattrapage ----- */
let PREC = null, PREC_POLL = null;
const precDur = it => ((it.data || {}).items || []).reduce((a, x) => a + (x.dur || 0), 0);
function precEtatTxt(it, mode){
  if (!it || it.etat === "aucun") return mode === "ouverture" ? "pas encore fabriqué" : "pas encore fabriqué";
  if (it.etat === "en cours") return "⏳ en cours…";
  if (it.etat === "echec") return "❌ " + (it.err || "échec");
  const d = it.data || {}, nb = (d.items || []).length;
  return (it.perime ? "🟠 à refaire (" + (it.raisons || []).join(", ") + ")" : "✅")
    + " " + fmtT(precDur(it)) + (mode === "rattrapage" ? " · " + nb + " chapitre(s)" : "")
    + " · " + fmtUsd((d.stats || {}).cout_total || 0) + (d.voice ? " · " + d.voice : "");
}
async function refreshPrec(){
  if (!CHAP_OPEN) return;
  const d = CHAP_OPEN;
  const j = await api("/manga/precedemment?d=" + encodeURIComponent(d));
  if (d !== CHAP_OPEN) return;
  PREC = j;
  $("precBox").hidden = !j.possible;
  if (!j.possible){ if (PREC_POLL){ clearInterval(PREC_POLL); PREC_POLL = null; } return; }
  const o = j.modes.ouverture, r = j.modes.rattrapage, nb = j.narres;
  $("precOuvEtat").textContent = precEtatTxt(o, "ouverture");
  $("precRatEtat").textContent = precEtatTxt(r, "rattrapage");
  const lbl = (it, cout) => it.etat === "fini" ? "↻ Refaire" : "Fabriquer (~" + cout + ")";
  $("precOuvGen").textContent = lbl(o, "0,01 $"); $("precOuvGen").disabled = o.etat === "en cours";
  $("precRatGen").textContent = lbl(r, (0.035 * nb).toFixed(2).replace(".", ",") + " $");
  $("precRatGen").disabled = r.etat === "en cours";
  $("precOuvGen").title = "résumé de ~30-45 s des chapitres d'avant, lu avant la page 1 (voix choisie dans le menu Voix)";
  $("precRatGen").title = nb + " chapitre(s) précédent(s) narré(s), ~1 min chacun (voix choisie dans le menu Voix)"
    + (j.precedents > nb ? " — " + (j.precedents - nb) + " chapitre(s) sans narration, sautés" : "");
  $("precRatJouer").hidden = r.etat !== "fini";
  const encours = o.etat === "en cours" || r.etat === "en cours";
  if (encours && !PREC_POLL) PREC_POLL = setInterval(() => refreshPrec().catch(() => {}), 3000);
  if (!encours && PREC_POLL){ clearInterval(PREC_POLL); PREC_POLL = null; chargerCouts(); }
}
async function precFabriquer(mode){
  const it = PREC && PREC.modes[mode];
  if (it && it.etat === "fini" && !it.perime && !confirm("Le résumé est à jour. Le refaire quand même (nouveau texte, nouvelle voix) ?")) return;
  try {
    const r = await api("/manga/precedemment", { d: CHAP_OPEN, mode, voice: $("narrVoice").value });
    if (r.error) throw new Error(r.error);
    log("résumé lancé : " + mode + " · " + CHAP_OPEN); actRafraichir(); await refreshPrec();
  } catch (err){ log("précédemment : " + err.message, "e"); alert(err.message); }
}
$("precOuvGen").onclick = () => precFabriquer("ouverture");
$("precRatGen").onclick = () => precFabriquer("rattrapage");
$("precRatJouer").onclick = () => {
  const n = NARRS.filter(x => x.etat === "fini" && x.audio).sort((a, b) => (b.created_at || "").localeCompare(a.created_at || ""))[0];
  if (!n){ alert("Ce chapitre n'a pas encore de narration avec voix : le rattrapage se lit avant elle."); return; }
  ouvrirLecteur([n.tag], false, "rattrapage").catch(err => log("lecteur : " + err.message, "e"));
};
// Les pages d'un resume : image d'un AUTRE chapitre, audio sous precedemment/ -> chemins complets (img, aud).
function precPages(mode){
  const it = PREC && PREC.modes[mode];
  if (!it || it.etat !== "fini") return [];
  return (it.data.items || []).map(x => ({ page: "résumé", type: "histoire", prec: mode, chapitre: x.chapitre,
    img: x.img, aud: it.base + "/" + x.audio, audio: x.audio, dur: x.dur, narration: x.narration }));
}
let PREC_ON = true;
try { PREC_ON = localStorage.getItem("manga_prec") !== "0"; } catch {}
$("lecPrecOn").checked = PREC_ON;
$("lecPrecOn").onchange = () => {
  PREC_ON = $("lecPrecOn").checked; try { localStorage.setItem("manga_prec", PREC_ON ? "1" : "0"); } catch {}
  $("lecPrecOn").blur();
};

/* ----- Lecteur : une file de narrations (1 = ecoute normale ; N = ecoute a l'aveugle) ----- */''')

# ---------- JS : lecteur ----------
rep('''async function ouvrirLecteur(tags, aveugle){
  LEC.file = tags; LEC.iFile = 0; LEC.aveugle = !!aveugle; LEC.notes = {};''',
    '''async function ouvrirLecteur(tags, aveugle, avant){
  LEC.file = tags; LEC.iFile = 0; LEC.aveugle = !!aveugle; LEC.notes = {};
  LEC.avant = aveugle ? null : (avant || (PREC_ON ? "ouverture" : null));      // v1.94.0 : resume en tete
  $("lecPrecBox").hidden = !!aveugle || !(PREC && PREC.modes.ouverture && PREC.modes.ouverture.etat === "fini");''')
rep('''  if (LEC.n.pages.length < avant) log("lecteur : " + (avant - LEC.n.pages.length) + " page(s) supprimée(s) depuis la narration, sautée(s)");''',
    '''  if (LEC.n.pages.length < avant) log("lecteur : " + (avant - LEC.n.pages.length) + " page(s) supprimée(s) depuis la narration, sautée(s)");
  const pre = LEC.iFile === 0 && LEC.avant ? precPages(LEC.avant) : [];
  if (pre.length){ LEC.n.pages = pre.concat(LEC.n.pages); log("lecteur : " + LEC.avant + " en tête (" + pre.length + " page(s) de résumé)"); }''')
rep('''  img.src = pageSrc(CHAP_OPEN + "/" + p.file);''',
    '''  img.src = p.img ? srcURL(p.img) : pageSrc(CHAP_OPEN + "/" + p.file);''')
rep('''  $("lecInfo").textContent = (LEC.aveugle ? "" : (n.title || "") + " ch. " + (n.chapter || "") + " · ")
    + "page " + p.page + " (" + (LEC.i + 1) + "/" + n.pages.length + ")";''',
    '''  $("lecInfo").textContent = p.prec ? (p.prec === "ouverture" ? "Précédemment…" : "Rattrapage · ch. " + p.chapitre)
      + " (" + (LEC.i + 1) + "/" + n.pages.length + ")"
    : (LEC.aveugle ? "" : (n.title || "") + " ch. " + (n.chapter || "") + " · ")
    + "page " + p.page + " (" + (LEC.i + 1) + "/" + n.pages.length + ")";''')
rep('''  if (suivant) (new Image()).src = pageSrc(CHAP_OPEN + "/" + suivant.file);        // prechargement''',
    '''  if (suivant) (new Image()).src = suivant.img ? srcURL(suivant.img) : pageSrc(CHAP_OPEN + "/" + suivant.file);   // prechargement''')
rep('''    a.src = srcURL(n.base + "/" + p.audio); a.playbackRate = +$("lecVit").value;''',
    '''    a.src = srcURL(p.aud || n.base + "/" + p.audio); a.playbackRate = +$("lecVit").value;''')

shutil.copy(p, p + ".bak-20260922-v194")
open(p, "w", encoding="utf-8").write(s)
print("app v1.94.0 OK")
