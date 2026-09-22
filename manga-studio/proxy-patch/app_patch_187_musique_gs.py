# -*- coding: utf-8 -*-
"""App v1.86.0 -> v1.87.0 : « Prendre dans Generate Studio » (Quang, 22/09 05h04).
Tu generes dans Generate Studio (mode intelligent + Instrumental) ; ici un panneau liste la PLAYLIST
(les plus recentes par defaut, « Tout voir » + recherche si besoin), avec l'ecoute et un badge mesure
« voix detectee / instrumental » (analyse.json de Generate Studio). « Prendre » copie le MP3 dans la serie.
Listes : /outputs_list + /audio_meta (routes de Generate Studio, lues telles quelles). Verifie ses ancres.
"""
import shutil
p = r"D:\Download\02-Apps-Web\Repo-github\App\manga-studio\manga_studio.html"
shutil.copy(p, p + ".bak-20260922-v187")
s = open(p, encoding="utf-8").read()


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:80])
    s = s.replace(a, b)


for a, b in (("<title>Manga Studio v1.86.0</title>", "<title>Manga Studio v1.87.0</title>"),
             ('id="verBadge">v1.86.0<', 'id="verBadge">v1.87.0<'),
             ('const VERSION = "1.86.0";', 'const VERSION = "1.87.0";')):
    rep(a, b)

rep('''        <button class="btn" id="musImport" title="un fichier audio de ton PC ou de ton téléphone (mp3, wav, ogg, m4a, flac)">Importer un morceau…</button>''',
    '''        <button class="btn" id="musGs" title="un morceau de ta playlist Generate Studio (génère-le là-bas : mode intelligent + Instrumental)">🎛 Prendre dans Generate Studio</button>
        <button class="btn" id="musImport" title="un fichier audio de ton PC ou de ton téléphone (mp3, wav, ogg, m4a, flac)">Importer un morceau…</button>''')
rep('''      <p class="muted aide" id="musEtat" style="margin:6px 0 0"></p>
    </div>''',
    '''      <p class="muted aide" id="musEtat" style="margin:6px 0 0"></p>
      <div id="gsBox" class="gs-box" hidden>
        <div class="row" style="align-items:center;gap:8px">
          <b class="grow">Playlist Generate Studio</b>
          <input id="gsRech" placeholder="chercher (titre, style)…" style="width:190px" hidden>
          <button class="btn sm" id="gsTout">Tout voir</button>
          <button class="btn sm" id="gsFermer">✕</button>
        </div>
        <div id="gsListe" class="gs-liste"></div>
      </div>
    </div>''')
rep('''.trad-box,.mus-box{margin-top:10px}''',
    '''.trad-box,.mus-box{margin-top:10px}
.gs-box{margin-top:8px;padding:8px;border:1px solid var(--line,#2a2f3a);border-radius:10px}
.gs-liste{display:flex;flex-direction:column;gap:6px;margin-top:8px;max-height:420px;overflow:auto}
.gs-it{display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:6px 8px;border-radius:8px;background:rgba(255,255,255,.03)}
.gs-it .grow{min-width:150px}
.gs-badge{font-size:12px;padding:1px 7px;border-radius:9px;white-space:nowrap}
.gs-badge.voix{background:rgba(233,69,96,.18);color:#ff9aa9}.gs-badge.instr{background:rgba(80,200,120,.16);color:#8fe0a8}''')

rep('''// --- lecture sous la narration : deux lecteurs pour boucler en fondu enchaine, volume suivi toutes les 100 ms''',
    '''// v1.87.0 : PRENDRE DANS GENERATE STUDIO. La playlist de Generate Studio = le dossier output/gs/audio/ ; on la
// lit par SES routes (/outputs_list, /audio_meta), sans rien dupliquer. Les 8 plus recentes, ou tout (+ recherche).
const GS = { tous: [], meta: {}, tout: false, N: 8 };
const gsTitre = it => it.titre || it.dossier.replace(/-\\d{6}(-\\d{6})?$/, "").replace(/-/g, " ");
const gsURL = ch => CFG.base + "/output_file?name=" + encodeURIComponent(ch) + "&mp3=1" + (CFG.key ? "&_k=" + encodeURIComponent(CFG.key) : "");
async function gsCharger(){
  const j = await api("/outputs_list");
  GS.tous = (j.files || []).filter(f => /^gs\\/audio\\/[^_/][^/]*\\/[^/]+\\.(flac|wav|mp3|ogg|m4a)$/i.test(f))
    .map(f => { const d = f.split("/")[2]; return { chemin: f, dossier: d, date: (j.dates || {})[f] || 0,
                                                    titre: (j.titres || {})[d] || "", moteurs: ((j.moteurs || {})[d] || {}).moteurs || "" }; })
    .sort((a, b) => b.date - a.date);
}
async function gsAfficher(){
  const q = GS.tout ? normRech($("gsRech").value || "") : "";
  let liste = GS.tout ? GS.tous : GS.tous.slice(0, GS.N);
  const manque = liste.filter(it => !(it.chemin in GS.meta)).map(it => it.chemin);
  if (manque.length){
    const r = await api("/audio_meta", { chemins: manque });
    Object.assign(GS.meta, r.meta || {}); manque.forEach(c => { if (!(c in GS.meta)) GS.meta[c] = {}; });
  }
  if (q) liste = liste.filter(it => normRech(gsTitre(it) + " " + ((GS.meta[it.chemin] || {}).style || "")).includes(q));
  $("gsTout").textContent = GS.tout ? "Les " + GS.N + " plus récentes" : "Tout voir (" + GS.tous.length + ")";
  $("gsRech").hidden = !GS.tout;
  $("gsListe").innerHTML = liste.map(it => {
    const m = GS.meta[it.chemin] || {}, a = m.analyse || {};
    const badge = a.voix === true ? '<span class="gs-badge voix" title="Generate Studio a mesuré une voix dans ce morceau">🎤 voix détectée</span>'
      : a.voix === false ? '<span class="gs-badge instr" title="aucune voix mesurée">🎹 instrumental</span>' : "";
    const quand = it.date ? new Date(it.date).toLocaleString("fr-FR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }) : "";
    return '<div class="gs-it"><div class="grow"><b>' + esc(gsTitre(it)) + "</b> " + badge + '<br><span class="muted aide">'
      + esc([quand, m.dur ? fmtT(m.dur) : "", it.moteurs ? "moteur " + it.moteurs : "", (m.style || "").slice(0, 60)].filter(Boolean).join(" · "))
      + '</span></div><button class="btn sm" data-gs-ecoute="' + esc(it.chemin) + '" title="écouter">▶</button>'
      + '<button class="btn sm pri" data-gs-prendre="' + esc(it.chemin) + '">Prendre</button></div>';
  }).join("") || '<p class="muted aide" style="margin:0">Aucun morceau' + (q ? " ne correspond." : " dans la playlist.") + "</p>";
}
$("musGs").onclick = async () => {
  if (!$("gsBox").hidden){ $("gsBox").hidden = true; MUS_APERCU.pause(); return; }
  $("gsBox").hidden = false; $("gsListe").innerHTML = '<p class="muted aide" style="margin:0">⏳ lecture de la playlist…</p>';
  try { await gsCharger(); await gsAfficher(); }
  catch (e){ $("gsListe").innerHTML = '<p class="muted aide" style="margin:0">❌ ' + esc(e.message) + "</p>"; log("playlist GS : " + e.message, "e"); }
};
$("gsFermer").onclick = () => { $("gsBox").hidden = true; MUS_APERCU.pause(); };
$("gsTout").onclick = () => { GS.tout = !GS.tout; gsAfficher().catch(e => log("playlist GS : " + e.message, "e")); };
$("gsRech").oninput = () => gsAfficher().catch(e => log("playlist GS : " + e.message, "e"));
$("gsListe").onclick = async e => {
  const ec = e.target.closest("[data-gs-ecoute]"), pr = e.target.closest("[data-gs-prendre]");
  if (ec){
    const url = gsURL(ec.dataset.gsEcoute);
    if (!MUS_APERCU.paused && MUS_APERCU.src === url){ MUS_APERCU.pause(); return; }
    MUS_APERCU.src = url; MUS_APERCU.volume = 0.6;
    MUS_APERCU.play().catch(err => { if (err.name !== "AbortError") log("écoute : " + err.message, "w"); });
    return;
  }
  if (!pr) return;
  const it = GS.tous.find(x => x.chemin === pr.dataset.gsPrendre), a = ((GS.meta[it.chemin] || {}).analyse) || {};
  if (a.voix === true && !confirm("Generate Studio a mesuré une VOIX dans « " + gsTitre(it) + " ». Sous la narration, elle se battra avec le narrateur.\\n\\nLa prendre quand même ?")) return;
  pr.disabled = true; pr.textContent = "⏳";
  try {
    const r = await api("/manga/musique_depuis_gs", { serie: serieDe(CHAP_OPEN), chemin: it.chemin, nom: gsTitre(it) });
    if (r.error) throw new Error(r.error);
    log("musique prise dans Generate Studio : " + r.nom); toast("« " + r.nom + " » ajouté à la série");
    await refreshMus();
    pr.textContent = "✓ prise";
  } catch (err){ pr.disabled = false; pr.textContent = "Prendre"; log("musique : " + err.message, "e"); alert(err.message); }
};

// --- lecture sous la narration : deux lecteurs pour boucler en fondu enchaine, volume suivi toutes les 100 ms''')

open(p, "w", encoding="utf-8").write(s)
print("patch app v1.87.0 OK")
