# -*- coding: utf-8 -*-
"""App v1.92.0 -> v1.93.0 : VIDEOS des chapitres (etape 5, valide par Quang le 22/09 06h25).

- 9:16 seul ; la video = le lecteur avec SES reglages du moment (vitesse, sous-titres, karaoke, musique + volume,
  pages VO / traduites) ;
- serie : bouton « 🎬 Videos » -> un panneau, une ligne par chapitre en ZONES FIXES : case, chapitre, etat
  (✅ a jour · 🟠 a refaire + RAISONS · ⏳ en cours · 🕓 en attente · ❌ echec · ⚪ pas de video · ⛔ pas de voix),
  puis ▶ ⬇ ↻ 🗑 toujours au meme endroit ; « Generer les manquantes », « Refaire les perimees », la selection,
  « ⬇ Telecharger la selection » (une par une : PC et telephone) ;
- la meme ligne dans le detail d'un chapitre ; un badge 🎬 sur les cartes de chapitre ;
- ↻ regenerer = l'ancienne a la corbeille puis nouvelle demande ; 🗑 = corbeille.
Verifie ses ancres, sinon n'ecrit rien.
"""
import shutil
p = r"D:\Download\02-Apps-Web\Repo-github\App\manga-studio\manga_studio.html"
shutil.copy(p, p + ".bak-20260922-v193")
s = open(p, encoding="utf-8").read()


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:80])
    s = s.replace(a, b)


for a, b in (("<title>Manga Studio v1.92.0</title>", "<title>Manga Studio v1.93.0</title>"),
             ('id="verBadge">v1.92.0<', 'id="verBadge">v1.93.0<'),
             ('const VERSION = "1.92.0";', 'const VERSION = "1.93.0";')):
    rep(a, b)

# ---------------- HTML ----------------
rep('''    <button class="btn sm danger" id="btnSerieDel">🗑 Supprimer la série</button>''',
    '''    <button class="btn sm" id="btnVideos" title="les vidéos des chapitres de cette série">🎬 Vidéos</button>
    <button class="btn sm danger" id="btnSerieDel">🗑 Supprimer la série</button>''')
rep('''  <div id="chapList" class="chap-list"></div>''',
    '''  <!-- v1.93.0 : VIDEOS de la serie (9:16, le lecteur avec ses reglages du moment) -->
  <div class="card vid-box" id="vidBox" hidden>
    <div class="vid-tete"><b>🎬 Vidéos de la série</b><button class="btn sm" id="vidFermer">✕</button></div>
    <p class="muted vid-reg" id="vidReg"></p>
    <div class="vid-actions">
      <button class="btn sm" id="vidManquantes" title="toutes les vidéos qui n'existent pas encore">Générer les manquantes</button>
      <button class="btn sm" id="vidPerimees" title="refaire les vidéos 🟠 (quelque chose a changé depuis)">Refaire les périmées</button>
      <button class="btn sm" id="vidSel" title="générer (ou refaire) les chapitres cochés">Générer la sélection</button>
      <button class="btn sm" id="vidDl" title="télécharger les vidéos cochées, une par une">⬇ Télécharger la sélection</button>
    </div>
    <div id="vidListe" class="vid-liste"></div>
  </div>
  <div id="chapList" class="chap-list"></div>''')
rep('''    <p class="muted" id="chapVerif" style="margin:0 0 8px;font-size:12px"></p>''',
    '''    <p class="muted" id="chapVerif" style="margin:0 0 8px;font-size:12px"></p>
    <div id="chapVid" class="vid-liste" style="margin:0 0 8px"></div>''')
rep('''<div id="lightbox" hidden>''',
    '''<div id="vidLecteur" class="vid-lecteur" hidden>
  <div class="vid-lec-tete"><b id="vidLecTitre"></b><button class="btn sm" id="vidLecFermer">✕ Fermer</button></div>
  <video id="vidLecVideo" controls playsinline preload="metadata"></video>
</div>
<div id="lightbox" hidden>''')
rep('''.trad-box,.mus-box{margin-top:10px}''',
    '''.trad-box,.mus-box{margin-top:10px}
/* v1.93.0 : videos — une ligne = zones FIXES (case, chapitre, etat, puis ▶ ⬇ ↻ 🗑 toujours au meme endroit) */
.vid-box{margin:0 0 12px}.vid-tete{display:flex;align-items:center;gap:8px}.vid-tete b{flex:1}
.vid-reg{font-size:12px;margin:4px 0 8px}
.vid-actions{display:flex;gap:6px;flex-wrap:wrap;margin:0 0 8px}
.vid-liste{display:flex;flex-direction:column;gap:4px}
.vid-it{display:grid;grid-template-columns:22px minmax(0,1fr) repeat(4,32px);gap:4px 6px;align-items:center;
  padding:6px 8px;border:1px solid var(--line);border-radius:7px;background:var(--panel)}
.vid-it input{width:16px;height:16px;margin:0;accent-color:var(--accent2)}
.vid-it .vi-nom{font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.vid-it .vi-etat{grid-column:2 / -1;font-size:12px;color:var(--dim)}
.vid-it .vi-etat.ko{color:#e6b450}
.vid-it .btn.sm{width:32px;height:30px;padding:0;justify-content:center}
.vid-it i{display:block}
.vid-it .narr-pbar{grid-column:2 / -1}
.vid-badge{font-size:11px;margin-left:4px}
.vid-lecteur{position:fixed;inset:0;z-index:95;background:#000;display:flex;flex-direction:column;align-items:center}
.vid-lecteur[hidden]{display:none}
.vid-lec-tete{display:flex;gap:8px;align-items:center;width:100%;max-width:760px;padding:8px 10px;box-sizing:border-box}
.vid-lec-tete b{flex:1;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.vid-lecteur video{flex:1;min-height:0;max-width:100%;padding-bottom:max(12px, env(safe-area-inset-bottom))}''')

# ---------------- activite ----------------
rep('''const ACT_LBL = { narration: "Narration", traduction: "Traduction", karaoke: "Karaoké", capture: "Capture" };''',
    '''const ACT_LBL = { narration: "Narration", traduction: "Traduction", karaoke: "Karaoké", capture: "Capture", video: "Vidéo" };''')
rep('''                    recit: "écriture du récit", voix: "synthèse vocale" };''',
    '''                    recit: "écriture du récit", voix: "synthèse vocale",
                    images: "images", son: "son", assemblage: "assemblage", attente: "en attente" };''')

# ---------------- JS ----------------
rep('''async function refreshNarrs(){''',
    '''// ---------- v1.93.0 : VIDEOS ----------
// La video = le lecteur avec SES reglages du moment : on les envoie tels quels, la video les garde (tracabilite).
function reglagesLecteur(){
  return { vitesse: +$("lecVit").value, sous: $("lecSousOn").checked, karaoke: KAR_ON, musique: MUS_ON, volume: MUS_VOL, pages: TRAD_VUE || "" };
}
const vidRegTxt = r => [String(r.vitesse).replace(".", ",") + "×", r.sous ? (r.karaoke ? "sous-titres karaoké" : "sous-titres") : "sans sous-titres",
  r.musique ? "musique " + r.volume + " %" : "sans musique", r.pages ? "pages " + r.pages : "pages VO"].join(" · ");
let VIDS = { serie: null, chapitres: [] }, VID_POLL = null;
// en plus des raisons du proxy (fichiers) : les reglages du lecteur ont-ils change depuis la video ?
function vidReglagesDiff(v){
  const cur = reglagesLecteur(), r = v.reglages || {}, d = [];
  if (+r.vitesse !== +cur.vitesse) d.push("vitesse");
  if (!!r.sous !== !!cur.sous || (cur.sous && !!r.karaoke !== !!cur.karaoke)) d.push("sous-titres");
  if (!!r.musique !== !!cur.musique || (cur.musique && +r.volume !== +cur.volume)) d.push("musique");
  if ((r.pages || "") !== (cur.pages || "") && !(r.pages === "" && cur.pages)) d.push("pages VO / traduites");
  return d.length ? ["réglages du lecteur différents (" + d.join(", ") + ")"] : [];
}
function vidEtat(c){
  const f = (c.file || [])[0], v = (c.videos || [])[0];
  if (f && f.etat === "en cours"){ const pr = f.progress || {};
    return { cle: "cours", txt: "⏳ fabrication — " + (ACT_ETAPE[pr.etape] || pr.etape || "démarrage") + (pr.total ? " " + pr.fait + "/" + pr.total : ""),
             pct: pr.total ? Math.round(100 * pr.fait / pr.total) : 0 }; }
  if (f && f.etat === "attente") return { cle: "attente", txt: "🕓 en attente", id: f.id };
  if (f && f.etat === "echec") return { cle: "echec", txt: "❌ échec — " + ((f.err || "").trim().split("\\n").slice(-1)[0] || "voir le journal"), id: f.id, ko: true };
  if (v){ const r = v.raisons || [], note = vidReglagesDiff(v);
    // 🟠 = le CHAPITRE a change (narration, voix, pages, traduction, karaoke, musique). Les reglages du lecteur sont
    // propres a chaque appareil : une difference n'est qu'une NOTE (sinon tout serait 🟠 sur un autre telephone).
    const info = (v.duree_s ? fmtT(v.duree_s) + " · " : "") + (v.taille / 1e6).toFixed(0) + " Mo · " + (v.tag || "")
      + (note.length ? " · ℹ️ " + note[0] : "");
    return r.length ? { cle: "refaire", txt: "🟠 à refaire : " + r.join(" ; ") + " · " + info, ko: true, v }
                    : { cle: "ok", txt: "✅ à jour · " + info, v }; }
  if (!(c.narrations || []).length) return { cle: "sansvoix", txt: "⛔ pas de narration avec voix : narre d'abord ce chapitre" };
  return { cle: "aucune", txt: "⚪ pas de vidéo (narration " + c.narrations[0].tag + ")" };
}
function vidLigne(c, i, avecCase){
  const e = vidEtat(c), v = e.v, vide = "<i></i>";
  return '<div class="vid-it" data-vd="' + i + '">'
    + (avecCase ? '<input type="checkbox" data-vid-coche="' + i + '"' + (e.cle === "sansvoix" ? " disabled" : "") + ">" : vide)
    + '<span class="vi-nom" title="' + esc(c.titre) + '">Chapitre ' + esc(c.chapitre) + "</span>"      // la serie est deja le contexte : le N° d'abord
    + (v ? '<button class="btn sm" data-vid-voir="' + i + '" title="regarder">▶</button>' : vide)
    + (v ? '<button class="btn sm" data-vid-dl="' + i + '" title="télécharger">⬇</button>' : vide)
    + (e.cle === "attente" || e.cle === "echec" ? '<button class="btn sm" data-vid-annule="' + i + '" title="retirer de la file">✕</button>'
       : e.cle !== "sansvoix" && e.cle !== "cours" ? '<button class="btn sm" data-vid-gen="' + i + '" title="' + (v ? "régénérer (l'ancienne part à la corbeille)" : "générer la vidéo") + '">' + (v ? "↻" : "🎬") + "</button>" : vide)
    + (v ? '<button class="btn sm danger" data-vid-suppr="' + i + '" title="supprimer la vidéo (corbeille)">🗑</button>' : vide)
    + '<span class="vi-etat' + (e.ko ? " ko" : "") + '" title="' + esc(e.txt) + '">' + esc(e.txt) + "</span>"
    + (e.cle === "cours" ? '<div class="narr-pbar"><div style="width:' + e.pct + '%"></div></div>' : "") + "</div>";
}
async function vidCharger(serie){
  if (!serie) return;
  VIDS = Object.assign(await api("/manga/videos?serie=" + encodeURIComponent(serie)), { serie });
  vidRendre();
}
function vidRendre(){
  $("vidReg").textContent = "Réglages utilisés = ceux du lecteur maintenant : " + vidRegTxt(reglagesLecteur()) + ". Format 9:16.";
  $("vidListe").innerHTML = VIDS.chapitres.map((c, i) => vidLigne(c, i, true)).join("") || '<p class="muted aide" style="margin:0">Aucun chapitre.</p>';
  const ci = VIDS.chapitres.findIndex(c => c.d === CHAP_OPEN);
  $("chapVid").innerHTML = ci >= 0 ? vidLigne(VIDS.chapitres[ci], ci, false) : "";
  document.querySelectorAll("#chapList [data-chap]").forEach(b => {         // badge sur les cartes de chapitre
    const c = VIDS.chapitres.find(x => x.d === (CHAPS[+b.dataset.chap] || {}).dir); let s = b.querySelector(".vid-badge");
    const e = c && vidEtat(c), t = e && { ok: "🎬 ✅", refaire: "🎬 🟠", cours: "🎬 ⏳", attente: "🎬 🕓", echec: "🎬 ❌" }[e.cle];
    if (!t){ if (s) s.remove(); return; }
    if (!s){ s = document.createElement("span"); s.className = "vid-badge"; (b.querySelector("b") || b).appendChild(s); }
    s.textContent = t; s.title = e.txt;
  });
  const vivant = VIDS.chapitres.some(c => (c.file || []).some(f => f.etat === "en cours" || f.etat === "attente"));
  clearTimeout(VID_POLL);
  if (vivant) VID_POLL = setTimeout(() => vidCharger(VIDS.serie).catch(e => log("vidéos : " + e.message, "w")), 4000);
}
async function vidDemander(liste, refaire){
  if (!liste.length){ toast("rien à générer"); return; }
  for (const c of liste) if (refaire && (c.videos || [])[0]) await api("/manga/video_suppr", { d: c.d, tag: c.videos[0].tag });
  const r = await api("/manga/video", { entrees: liste.map(c => ({ d: c.d })), reglages: reglagesLecteur() });
  if (r.error) throw new Error(r.error);
  toast("🎬 " + r.ajoutees.length + " vidéo(s) en file" + (r.refusees.length ? " · " + r.refusees.length + " refusée(s)" : ""));
  if (r.refusees.length) log("vidéos refusées : " + r.refusees.map(x => x.d + " (" + x.raison + ")").join(", "), "w");
  await vidCharger(VIDS.serie); actRafraichir();
}
function vidTelecharger(c){
  const v = (c.videos || [])[0]; if (!v) return;
  const a = document.createElement("a");
  a.href = CFG.base + "/manga/video_file?p=" + encodeURIComponent(v.fichier) + "&dl=1&v=" + v.v + (CFG.key ? "&_k=" + encodeURIComponent(CFG.key) : "");
  a.download = ""; document.body.appendChild(a); a.click(); a.remove();
}
const vidCoches = () => [...document.querySelectorAll("#vidListe [data-vid-coche]:checked")].map(x => VIDS.chapitres[+x.dataset.vidCoche]);
async function vidClic(e){
  const b = e.target.closest("[data-vid-voir],[data-vid-dl],[data-vid-gen],[data-vid-suppr],[data-vid-annule]"); if (!b) return;
  const c = VIDS.chapitres[+(b.dataset.vidVoir ?? b.dataset.vidDl ?? b.dataset.vidGen ?? b.dataset.vidSuppr ?? b.dataset.vidAnnule)];
  if (!c) return;
  try {
    if (b.dataset.vidVoir != null){
      const v = c.videos[0];
      $("vidLecTitre").textContent = c.titre + " — ch. " + c.chapitre + " · " + v.tag;
      $("vidLecVideo").src = CFG.base + "/manga/video_file?p=" + encodeURIComponent(v.fichier) + "&v=" + v.v + (CFG.key ? "&_k=" + encodeURIComponent(CFG.key) : "");
      $("vidLecteur").hidden = false; $("vidLecVideo").play().catch(() => {});
    } else if (b.dataset.vidDl != null) vidTelecharger(c);
    else if (b.dataset.vidGen != null){
      const v = (c.videos || [])[0];
      if (v && !confirm("Régénérer la vidéo de ce chapitre avec les réglages actuels du lecteur ?\\n\\n" + vidRegTxt(reglagesLecteur()) + "\\n\\nL'ancienne part à la corbeille.")) return;
      await vidDemander([c], !!v);
    } else if (b.dataset.vidSuppr != null){
      if (!confirm("Supprimer la vidéo de « " + c.titre + " ch. " + c.chapitre + " » ? (corbeille)")) return;
      const r = await api("/manga/video_suppr", { d: c.d, tag: c.videos[0].tag }); if (r.error) throw new Error(r.error);
      await vidCharger(VIDS.serie);
    } else if (b.dataset.vidAnnule != null){
      const r = await api("/manga/video_annule", { id: vidEtat(c).id }); if (r.error) throw new Error(r.error);
      await vidCharger(VIDS.serie); actRafraichir();
    }
  } catch (err){ log("vidéo : " + err.message, "e"); alert(err.message); }
}
$("vidListe").onclick = vidClic; $("chapVid").onclick = vidClic;
$("btnVideos").onclick = () => { $("vidBox").hidden = !$("vidBox").hidden; if (!$("vidBox").hidden) vidCharger(LIB_SERIE).catch(e => log("vidéos : " + e.message, "e")); };
$("vidFermer").onclick = () => { $("vidBox").hidden = true; };
$("vidManquantes").onclick = () => vidDemander(VIDS.chapitres.filter(c => vidEtat(c).cle === "aucune"), false).catch(e => alert(e.message));
$("vidPerimees").onclick = () => {
  const l = VIDS.chapitres.filter(c => vidEtat(c).cle === "refaire");
  if (l.length && !confirm("Refaire " + l.length + " vidéo(s) périmée(s) ? Les anciennes partent à la corbeille.")) return;
  vidDemander(l, true).catch(e => alert(e.message));
};
$("vidSel").onclick = () => { const l = vidCoches().filter(c => vidEtat(c).cle !== "cours" && vidEtat(c).cle !== "attente");
  if (l.some(c => (c.videos || []).length) && !confirm("Certaines vidéos cochées existent déjà : les refaire (les anciennes partent à la corbeille) ?")) return;
  vidDemander(l, true).catch(e => alert(e.message)); };
$("vidDl").onclick = async () => {                     // une par une, 1,5 s d'ecart : PC et telephone acceptent
  const l = vidCoches().filter(c => (c.videos || []).length);
  if (!l.length){ toast("coche des chapitres qui ont une vidéo"); return; }
  for (const c of l){ vidTelecharger(c); await new Promise(r => setTimeout(r, 1500)); }
};
$("vidLecFermer").onclick = () => { $("vidLecVideo").pause(); $("vidLecVideo").removeAttribute("src"); $("vidLecteur").hidden = true; };

async function refreshNarrs(){''')
rep('''  $("chapState").textContent = serie.title + " : " + serie.chaps.length + " chapitre(s)";''',
    '''  $("chapState").textContent = serie.title + " : " + serie.chaps.length + " chapitre(s)";
  vidCharger(serie.slug).catch(e => log("vidéos : " + e.message, "w"));        // v1.93.0 : badges + panneau''')
rep('''  refreshMus().catch(err => log("musique : " + err.message, "w"));''',
    '''  refreshMus().catch(err => log("musique : " + err.message, "w"));
  if (VIDS.serie === serieDe(CHAP_OPEN)) vidRendre();
  else vidCharger(serieDe(CHAP_OPEN)).catch(err => log("vidéos : " + err.message, "w"));''')

open(p, "w", encoding="utf-8").write(s)
print("patch app v1.93.0 OK")
