# -*- coding: utf-8 -*-
"""App v1.85.0 -> v1.86.0 : sous-titres KARAOKE dans le lecteur (etape 2-bis, ordre de Quang du 22/09).
Le mot prononce s'allume. Temps des mots = pages[].mots (scripts/karaoke_mots.py, bouton « 🎤 Karaoke » par
narration) ; tant qu'une narration n'est pas calee : repli au prorata de la longueur des mots (roadmap).
Case « karaoke » a cote de « sous-titres », memorisee par appareil. Verifie ses ancres, sinon n'ecrit rien.
"""
import shutil
p = r"D:\Download\02-Apps-Web\Repo-github\App\manga-studio\manga_studio.html"
shutil.copy(p, p + ".bak-20260922-v186")
s = open(p, encoding="utf-8").read()


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:80])
    s = s.replace(a, b)


for a, b in (("<title>Manga Studio v1.85.0</title>", "<title>Manga Studio v1.86.0</title>"),
             ('id="verBadge">v1.85.0<', 'id="verBadge">v1.86.0<'),
             ('const VERSION = "1.85.0";', 'const VERSION = "1.86.0";')):
    rep(a, b)

# ---------- HTML + CSS ----------
rep('''    <label class="lec-chk"><input type="checkbox" id="lecSousOn" checked> sous-titres</label>''',
    '''    <label class="lec-chk"><input type="checkbox" id="lecSousOn" checked> sous-titres</label>
    <label class="lec-chk" title="le mot prononcé s'allume"><input type="checkbox" id="lecKarOn"> karaoké</label>''')
rep('''.trad-box,.mus-box{margin-top:10px}''',
    '''.trad-box,.mus-box{margin-top:10px}
.lec-sous .km{opacity:.5;transition:opacity .12s,color .12s}
.lec-sous .km.dit{opacity:1}
.lec-sous .km.on{opacity:1;color:#ffd700;text-shadow:0 0 10px rgba(255,215,0,.35)}''')

# ---------- JS : sous-titre de la page (texte simple ou mots) ----------
rep('''  $("lecSous").textContent = $("lecSousOn").checked ? (p.narration || "") : "";
  $("lecInfo").textContent =''',
    '''  sousTitre(p);
  $("lecInfo").textContent =''')
rep('''$("lecSousOn").onchange = () => {
  const p = LEC.n && LEC.n.pages[LEC.i];
  $("lecSous").textContent = $("lecSousOn").checked && p ? (p.narration || "") : "";
  $("lecSousOn").blur();
};''',
    '''$("lecSousOn").onchange = () => {
  const p = LEC.n && LEC.n.pages[LEC.i];
  if (p) sousTitre(p);
  $("lecSousOn").blur();
};
// v1.86.0 : KARAOKE. Un <span> par mot de narration.split() ; le mot dont le debut est passe s'allume.
// Temps : p.mots (Whisper recale, un couple par mot) ; sinon repli au prorata de la longueur des mots.
let KAR_ON = true, KAR = { spans: [], t: [], k: -1, raf: 0 };
try { KAR_ON = localStorage.getItem("manga_kar") !== "0"; } catch {}
$("lecKarOn").checked = KAR_ON;
function tempsMots(p){
  const toks = (p.narration || "").split(/\\s+/).filter(Boolean);
  if (Array.isArray(p.mots) && p.mots.length === toks.length) return p.mots.map(m => m[0]);
  const poids = toks.map(t => t.length + 1), tot = poids.reduce((a, b) => a + b, 0) || 1, dur = p.dur || 3;
  let c = 0; return poids.map(w => { const t = c / tot * dur; c += w; return t; });
}
function sousTitre(p){
  cancelAnimationFrame(KAR.raf); KAR.spans = []; KAR.k = -1;
  const el = $("lecSous");
  if (!$("lecSousOn").checked){ el.textContent = ""; return; }
  if (!KAR_ON || !p.audio){ el.textContent = p.narration || ""; return; }
  const toks = (p.narration || "").split(/\\s+/).filter(Boolean);
  el.innerHTML = toks.map(t => '<span class="km">' + esc(t) + "</span>").join(" ");
  KAR.spans = [...el.querySelectorAll(".km")]; KAR.t = tempsMots(p);
  karTick();
}
function karTick(){
  if ($("lecteur").hidden || !KAR.spans.length) return;
  const t = $("lecAudio").currentTime || 0;
  let k = -1; while (k + 1 < KAR.t.length && KAR.t[k + 1] <= t + 0.05) k++;
  if (k !== KAR.k){
    KAR.spans.forEach((s, i) => { s.classList.toggle("dit", i < k); s.classList.toggle("on", i === k); });
    KAR.k = k;
  }
  KAR.raf = requestAnimationFrame(karTick);
}
$("lecKarOn").onchange = () => {
  KAR_ON = $("lecKarOn").checked; try { localStorage.setItem("manga_kar", KAR_ON ? "1" : "0"); } catch {}
  const p = LEC.n && LEC.n.pages[LEC.i];
  if (p) sousTitre(p);
  $("lecKarOn").blur();
};''')

# ---------- JS : bouton « 🎤 Karaoke » par narration ----------
rep('''    if (n.etat === "fini") info = n.pages + " pages · " + (st.cout_total != null ? st.cout_total.toFixed(3) + " $ · " : "")
      + "généré en " + fmtS(st.total_s || 0) + (n.titre ? " · « " + esc(n.titre) + " »" : "");''',
    '''    if (n.etat === "fini") info = n.pages + " pages · " + (st.cout_total != null ? st.cout_total.toFixed(3) + " $ · " : "")
      + "généré en " + fmtS(st.total_s || 0) + (n.titre ? " · « " + esc(n.titre) + " »" : "")
      + (n.karaoke_en_cours ? " · ⏳ karaoké en calage…" : st.karaoke ? " · 🎤 karaoké calé" : "");''')
rep('''      + (n.etat === "fini" && ["kimi", "gemini", "pixtral"].includes(n.engine)''',
    '''      + (n.etat === "fini" && n.audio && !st.karaoke && !n.karaoke_en_cours
         ? '<button class="btn sm" data-kar="' + i + '" title="cale chaque mot sur la voix (Whisper, ~0,003 $ pour 20 pages) : le mot prononcé s\\'allume dans le lecteur">🎤 Karaoké</button>' : "")
      + (n.etat === "fini" && ["kimi", "gemini", "pixtral"].includes(n.engine)''')
rep('''  const encours = NARRS.some(n => n.etat === "en cours");''',
    '''  const encours = NARRS.some(n => n.etat === "en cours" || n.karaoke_en_cours);''')
rep('''$("narrRuns").onclick = async e => {
  const rv = e.target.closest("[data-revoix]");''',
    '''$("narrRuns").onclick = async e => {
  const kb = e.target.closest("[data-kar]");
  if (kb){
    const n = NARRS[+kb.dataset.kar];
    try {
      const r = await api("/manga/karaoke", { d: CHAP_OPEN, tag: n.tag });
      if (r.error) throw new Error(r.error);
      log("karaoké lancé : " + n.tag); await refreshNarrs();
    } catch (err){ log("karaoké : " + err.message, "e"); alert(err.message); }
    return;
  }
  const rv = e.target.closest("[data-revoix]");''')

open(p, "w", encoding="utf-8").write(s)
print("patch app v1.86.0 OK")
