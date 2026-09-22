# -*- coding: utf-8 -*-
"""App v1.97.0 -> v1.98.0 : SUIVI DE SERIES (etape 9, sans plafond -- decision Quang 22/09 09h00).
Barre de la serie : « 🌙 Suivi » -> panneau : case « narrer automatiquement la nuit » (01:30), voix, options (karaoke,
« Precedemment... », video avec les reglages du lecteur), FILE des chapitres a narrer + estimation (cout, duree),
« ▶ Lancer maintenant », etat du dernier passage et son journal. Verifie ses ancres, sinon n'ecrit rien.
"""
import shutil
p = r"D:\Download\02-Apps-Web\Repo-github\App\manga-studio\manga_studio.html"
s = open(p, encoding="utf-8").read()


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:80])
    s = s.replace(a, b)


for a, b in (("<title>Manga Studio v1.97.0</title>", "<title>Manga Studio v1.98.0</title>"),
             ('id="verBadge">v1.97.0<', 'id="verBadge">v1.98.0<'),
             ('const VERSION = "1.97.0";', 'const VERSION = "1.98.0";')):
    rep(a, b)

rep('''    <button class="btn sm" id="btnVideos" title="les vidéos des chapitres de cette série">🎬 Vidéos</button>''',
    '''    <button class="btn sm" id="btnVideos" title="les vidéos des chapitres de cette série">🎬 Vidéos</button>
    <button class="btn sm" id="btnSuivi" title="narrer automatiquement, la nuit, les chapitres capturés">🌙 Suivi</button>''')
rep('''  <div class="card vid-box" id="vidBox" hidden>''',
    '''  <!-- v1.98.0 : SUIVI de la serie (scripts/suivi_nuit.py, tache planifiee 01:30) -->
  <div class="card vid-box" id="suiviBox" hidden>
    <div class="vid-tete"><b>🌙 Suivi de la série</b><button class="btn sm" id="suiviFermer">✕</button></div>
    <label class="suivi-l"><input type="checkbox" id="suiviActif"> Narrer automatiquement <b>la nuit (1 h 30)</b> les chapitres capturés et pas encore narrés</label>
    <div class="suivi-opts">
      <label>Voix <select id="suiviVoix"></select></label>
      <label><input type="checkbox" id="suiviKar" checked> karaoké</label>
      <label><input type="checkbox" id="suiviPrec" checked> « Précédemment… »</label>
      <label title="avec les réglages ACTUELS du lecteur (vitesse, sous-titres, musique, 📜)"><input type="checkbox" id="suiviVid"> vidéo</label>
    </div>
    <p class="muted suivi-file" id="suiviFile"></p>
    <div class="vid-actions"><button class="btn sm pri" id="suiviLancer">▶ Lancer maintenant</button><span class="muted" id="suiviPassage"></span></div>
    <details class="suivi-jr"><summary>Journal des passages</summary><div id="suiviJournal"></div></details>
  </div>
  <div class="card vid-box" id="vidBox" hidden>''')
rep('''.vid-selbar{display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin:6px 0}''',
    '''.vid-selbar{display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin:6px 0}
.suivi-l{display:flex;gap:8px;align-items:flex-start;margin:8px 0;font-size:13px}.suivi-l input{margin-top:3px}
.suivi-opts{display:flex;flex-wrap:wrap;gap:6px 14px;align-items:center;font-size:12px;color:var(--dim)}
.suivi-opts label{display:inline-flex;gap:5px;align-items:center}.suivi-opts select{width:auto;font-size:12px;padding:3px 6px}
.suivi-file{font-size:12px;margin:8px 0}#suiviJournal{font-size:11px;color:var(--dim);max-height:180px;overflow:auto;white-space:pre-wrap}''')

JS = r'''// ---------- v1.98.0 : SUIVI ----------
let SUIVI = null, SUIVI_POLL = null;
const SUIVI_EV = { debut: "début du passage", narration: "narration", karaoke: "karaoké", precedemment: "« Précédemment… »",
                   video: "vidéo demandée", fin: "fin du passage", refus: "refusé", echec: "échec" };
function suiviRendre(){
  const j = SUIVI, c = j.config || {}, f = j.file || [], ps = j.passage || {};
  $("suiviVoix").innerHTML = VOIX.map(v => '<option value="' + v[0] + '">' + esc(v[1]) + "</option>").join("");
  let v = c.voix; if (!v) try { v = localStorage.getItem("manga_voix_" + LIB_SERIE); } catch {}
  $("suiviVoix").value = VOIX.some(x => x[0] === v) ? v : VOIX[0][0];
  $("suiviActif").checked = !!c.actif; $("suiviKar").checked = c.karaoke !== false;
  $("suiviPrec").checked = c.precedemment !== false; $("suiviVid").checked = !!c.video;
  $("suiviFile").textContent = f.length
    ? f.length + " chapitre(s) à narrer : ch. " + f.map(x => x.num).join(", ") + " — ≈ " + fmtUsd(j.estimation.cout)
      + " et ≈ " + fmtS(j.estimation.minutes * 60) + " (Kimi K3, sans plafond)"
    : "Rien à narrer : tous les chapitres capturés ont une narration avec voix.";
  const en = ps.en_cours;
  const ETP = { narration: "narration", karaoke: "karaoké", precedemment: "« Précédemment… »" };
  $("suiviPassage").textContent = ps.vivant ? "⏳ en cours" + (en ? " — ch. " + (en.num || en.d) + " · " + (ETP[en.etape] || en.etape || "") : "")
    : ps.etat === "fini" ? "dernier passage : ✅ " + new Date(ps.fin * 1000).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" })
      + " · " + (ps.fait || []).length + " narré(s)" + ((ps.erreurs || []).length ? " · ❌ " + ps.erreurs.length : "")
    : ps.etat === "interrompu" ? "⚠ dernier passage interrompu" : ps.etat === "echec" ? "❌ " + (ps.err || "échec") : "jamais lancé";
  $("suiviLancer").disabled = !!ps.vivant || !f.length;
  $("suiviJournal").textContent = (j.journal || []).slice().reverse().map(x => x.t.replace("T", " ").slice(5, 16) + "  "
    + (SUIVI_EV[x.ev] || x.ev) + (x.d ? " · " + x.d.split("/").pop().replace("ch_", "ch. ") : "")
    + (x.ok === false || (x.rc != null && x.rc !== 0) ? " ❌" : x.ok || x.rc === 0 ? " ✅" : "") + (x.s ? " (" + fmtS(x.s) + ")" : "")).join("\n") || "—";
  clearTimeout(SUIVI_POLL);
  if (ps.vivant && !$("suiviBox").hidden) SUIVI_POLL = setTimeout(() => suiviCharger().catch(() => {}), 5000);
}
async function suiviCharger(){ if (!LIB_SERIE) return; SUIVI = await api("/manga/suivi?serie=" + encodeURIComponent(LIB_SERIE)); suiviRendre(); }
async function suiviSauver(){
  const r = await api("/manga/suivi", { serie: LIB_SERIE, actif: $("suiviActif").checked, voix: $("suiviVoix").value,
    karaoke: $("suiviKar").checked, precedemment: $("suiviPrec").checked, video: $("suiviVid").checked, reglages_video: reglagesLecteur() });
  if (r.error) throw new Error(r.error);
  toast($("suiviActif").checked ? "🌙 suivi activé : narration la nuit" : "suivi désactivé"); await suiviCharger();
}
["suiviActif", "suiviVoix", "suiviKar", "suiviPrec", "suiviVid"].forEach(id => $(id).onchange = () => suiviSauver().catch(e => alert(e.message)));
$("btnSuivi").onclick = () => { $("suiviBox").hidden = !$("suiviBox").hidden; if (!$("suiviBox").hidden) suiviCharger().catch(e => log("suivi : " + e.message, "e")); };
$("suiviFermer").onclick = () => { $("suiviBox").hidden = true; clearTimeout(SUIVI_POLL); };
$("suiviLancer").onclick = async () => {
  const j = SUIVI || {}, f = j.file || [];
  if (!confirm("Narrer maintenant " + f.length + " chapitre(s) (≈ " + fmtUsd((j.estimation || {}).cout || 0) + ", ≈ "
               + fmtS(((j.estimation || {}).minutes || 0) * 60) + ") avec la voix " + $("suiviVoix").value + " ?")) return;
  try {
    await suiviSauver();
    const r = await api("/manga/suivi_lancer", { serie: LIB_SERIE }); if (r.error) throw new Error(r.error);
    log("suivi lancé : " + LIB_SERIE); setTimeout(() => { suiviCharger().catch(() => {}); actRafraichir(); }, 2500);
  } catch (e){ alert(e.message); }
};
'''
rep('''$("btnVideos").onclick = () =>''', JS + '''$("btnVideos").onclick = () =>''')
shutil.copy(p, p + ".bak-20260922-v198")
open(p, "w", encoding="utf-8").write(s)
print("app v1.98.0 OK")
