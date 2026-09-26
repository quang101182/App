# -*- coding: utf-8 -*-
"""Manga Studio v2.68.0 -> v2.69.0 : SELECTEUR RAPIDE « Aller au … » (maquette_selecteur_chapitre_v1, retenue par Quang le
26/09/2026 11h08 ; « selecteur de chapitre, de narration et de video, pense a tous les cas » 11h10 ; ROADMAP § 4-sexdecies S1).
Un seul composant (feuille qui monte du bas : champ n° + filtres + grille), 4 contextes : chapitres (barre de navigation),
narrations (lecteur narre), videos (lecteur video), pages (visionneuse). Ouverture : glisser la barre VERS LE HAUT, toucher la
bulle / le titre, touche G (PC). Fermeture : ✕, voile, glisser vers le bas, Echap.
Rejouable : python app_patch_269_selecteur.py <manga_studio.html>
"""
import sys

P = sys.argv[1]
s = open(P, "rb").read().decode("utf-8")
assert "\r\n" in s
if "v2.69.0 : selecteur" in s:
    print("deja patche"); sys.exit(0)


def rep(a, b, n=1):
    global s
    a, b = a.replace("\n", "\r\n"), b.replace("\n", "\r\n")
    if s.count(a) != n:
        raise SystemExit("ancre %d fois (attendu %d) : %r" % (s.count(a), n, a[:80]))
    s = s.replace(a, b)


rep("<title>Manga Studio v2.68.0</title>", "<title>Manga Studio v2.69.0</title>")
rep('<span class="ver" id="verBadge">v2.68.0</span>', '<span class="ver" id="verBadge">v2.69.0</span>')
rep('const VERSION = "2.68.0";', 'const VERSION = "2.69.0";')

# ---------------------------------------------------------------- HTML (juste avant le lecteur video)
rep('''<!-- v2.68.0 : lecteur video (maquette_lecteur_video_v1, validee 26/09 11h05) -- la MEME barre que la visionneuse, en bas -->''',
'''<!-- v2.69.0 : selecteur rapide « Aller au … » (maquette_selecteur_chapitre_v1) -- chapitres, narrations, videos, pages -->
<div id="selVoile" class="sel-voile" hidden></div>
<div id="selFeuille" class="sel-feuille" role="dialog" aria-modal="true" aria-labelledby="selTitre" hidden>
  <div class="sel-poignee"></div>
  <div class="sel-tete"><b id="selTitre">Aller au chapitre</b><button class="btn sm" id="selFermer" title="fermer (Échap)">✕</button></div>
  <div class="sel-champ"><input id="selNum" inputmode="decimal" autocomplete="off" enterkeyhint="go" placeholder="n° de chapitre…">
    <button class="btn pri" id="selAller">Aller</button></div>
  <div class="sel-info" id="selInfo"></div>
  <div class="sel-filtres" id="selFiltres"></div>
  <div class="sel-grille" id="selGrille"></div>
</div>
<!-- v2.68.0 : lecteur video (maquette_lecteur_video_v1, validee 26/09 11h05) -- la MEME barre que la visionneuse, en bas -->''')

# ---------------------------------------------------------------- CSS
rep('''.vid-lecteur .menu-pan>button.on{color:#e0a030;font-weight:700}''',
'''.vid-lecteur .menu-pan>button.on{color:#e0a030;font-weight:700}
/* v2.69.0 : selecteur rapide -- une feuille qui monte du bas, au-dessus des lecteurs (80 / 90 / 95) et sous les toasts (99) */
.sel-voile{position:fixed;inset:0;background:#0009;z-index:97}.sel-voile[hidden]{display:none}
.sel-feuille{position:fixed;left:0;right:0;bottom:0;margin:0 auto;max-width:760px;height:min(78vh,640px);z-index:98;background:var(--panel);
  border-top:1px solid var(--line);border-radius:16px 16px 0 0;padding:8px 12px max(12px, env(safe-area-inset-bottom));display:flex;flex-direction:column;
  gap:8px;box-shadow:0 -10px 30px #000a;box-sizing:border-box}
.sel-feuille[hidden]{display:none}
.sel-poignee{width:40px;height:4px;border-radius:2px;background:#ffffff44;margin:0 auto 2px;flex:none}
.sel-tete{display:flex;align-items:center;gap:8px}.sel-tete b{flex:1;min-width:0;font-size:15px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sel-champ{display:flex;gap:6px}
#selNum{flex:1;min-width:0;height:42px;border-radius:10px;border:2px solid #e0a030;background:var(--bg);color:var(--txt);font-size:17px;font-weight:700;padding:0 12px;box-sizing:border-box}
#selAller{height:42px;white-space:nowrap}
.sel-info{font-size:13px;color:#e8a84a}.sel-info:empty{display:none}.sel-info .btn{margin:2px 2px 0 0}
.sel-filtres{display:flex;gap:6px;flex-wrap:wrap}.sel-filtres[hidden]{display:none}
.sel-f{font:inherit;font-size:12.5px;border:1px solid var(--line);border-radius:999px;padding:4px 10px;background:var(--panel2);color:var(--txt);cursor:pointer}
.sel-f.on{border-color:#e0a030;background:#e0a03026}
.sel-grille{flex:1;min-height:0;overflow-y:auto;display:grid;grid-template-columns:repeat(auto-fill,minmax(58px,1fr));gap:6px;align-content:start;
  padding-bottom:6px;overscroll-behavior:contain}
.sel-c{height:48px;border-radius:9px;background:var(--panel2);border:1px solid var(--line);color:var(--txt);font:inherit;font-weight:700;font-size:14px;
  display:flex;flex-direction:column;align-items:center;justify-content:center;line-height:1.1;cursor:pointer;padding:0 2px;overflow:hidden}
.sel-c small{font-size:10px;font-weight:500;color:var(--dim);white-space:nowrap}
.sel-c.lu{background:#162319}.sel-c.cour{border:2px solid #4fd28a;background:#1f5b3a;color:#d6ffe6}.sel-c.cour small{color:#b9f0cf}
.sel-c.off{opacity:.38;cursor:not-allowed}.sel-c.trou{border-style:dashed;color:var(--dim);font-weight:500}
/* la poignee rappelle le geste « glisser vers le haut » ; les barres ne font plus defiler la page (le geste est a elles) */
#navFlot,#vidBar,#lightbox .lbbar,#lecteur .lec-ctl{touch-action:none}
#vidBar,#lightbox .lbbar,#lecteur .lec-ctl{position:relative}
#navFlot::before,#vidBar::before,#lightbox .lbbar::before,#lecteur .lec-ctl::before{content:"";position:absolute;left:50%;top:-8px;width:34px;height:4px;
  margin-left:-17px;border-radius:2px;background:#ffffff38;pointer-events:none}''')

# ---------------------------------------------------------------- JS : vidOuvrir accepte une VERSION (tag)
rep('''function vidOuvrir(i){
  const c = VIDS.chapitres[i], v = c && (c.videos || [])[0];''',
'''function vidOuvrir(i, tag){                                                  // v2.69.0 : une version precise (selecteur)
  const c = VIDS.chapitres[i], v = c && ((tag && (c.videos || []).find(x => x.tag === tag)) || (c.videos || [])[0]);''')

# ---------------------------------------------------------------- JS : le composant + les 4 contextes + les declencheurs
rep('''/* v2.68.0 : evenements du lecteur video */''',
'''/* ============ v2.69.0 : SELECTEUR RAPIDE « Aller au … » (maquette_selecteur_chapitre_v1, retenue par Quang 26/09 11h08) ============
   Un composant, 4 contextes (chapitres / narrations / videos / pages). Cas couverts (Quang 11h10 « pense a tous les cas ») :
   courant (vert, centre) · lu (d'apres l'historique de lecture) · numero ABSENT (pointille, non cliquable ; la recherche propose le
   plus proche) · sans narration / sans video (grise + raison) · en cours de fabrication (⏳) · video « a refaire » (🟠, lancable) ·
   plusieurs voix / versions (choix) · decimales (12,5) · serie a 1 chapitre · serie longue (grille qui defile, recherche). */
const SEL = { ctx: null, filtre: "tous", q: "", enAttente: null };
const selNumTxt = n => String(n).replace(".", ",");
function selOuvrir(ctx){
  if (!ctx) return;
  SEL.ctx = ctx; SEL.filtre = "tous"; SEL.q = ""; SEL.enAttente = null;
  $("selTitre").textContent = ctx.titre; $("selNum").value = ""; $("selAller").textContent = "Aller";
  $("selNum").placeholder = ctx.quoi === "page" ? "n° de page…" : "n° de chapitre…";
  $("selInfo").textContent = "";
  $("selFiltres").innerHTML = (ctx.filtres || []).map(f => '<button class="sel-f' + (f.k === "tous" ? " on" : "") + '" data-f="' + f.k + '">' + esc(f.t) + "</button>").join("");
  $("selFiltres").hidden = !(ctx.filtres || []).length;
  $("selVoile").hidden = $("selFeuille").hidden = false;
  selRendre();
  const c = $("selGrille").querySelector(".cour"); if (c) c.scrollIntoView({ block: "center" });
  if (!matchMedia("(pointer:coarse)").matches) setTimeout(() => $("selNum").focus(), 50);          // PC : on tape directement
}
function selFermer(){ $("selVoile").hidden = $("selFeuille").hidden = true; SEL.ctx = null; SEL.enAttente = null; }
function selVisibles(){
  const x = SEL.ctx; if (!x) return [];
  const f = (x.filtres || []).find(y => y.k === SEL.filtre), q = SEL.q.replace(",", ".");
  return x.items.filter(it => (!f || !f.test || f.test(it)) && (!q || String(it.num).startsWith(q)));
}
function selRendre(){
  $("selGrille").innerHTML = selVisibles().map(it => '<button class="sel-c' + (it.classe ? " " + it.classe : "") + '" data-k="' + esc(String(it.cle)) + '"'
    + (it.off ? ' aria-disabled="true"' : "") + ' title="' + esc(it.raison || ((SEL.ctx.quoi === "page" ? "page " : "ch. ") + it.label)) + '">' + esc(it.label)
    + (it.sous ? "<small>" + esc(it.sous) + "</small>" : "") + "</button>").join("") || '<p class="muted" style="grid-column:1/-1;margin:6px 0">Aucun résultat.</p>';
}
async function selChoisir(it){
  const x = SEL.ctx; if (!it || !x) return;
  if (it.off){ $("selInfo").textContent = "⚠ " + (it.raison || "indisponible"); return; }
  if (x.avantChoix && !it.versions){ $("selInfo").textContent = "…"; await x.avantChoix(it).catch(() => {}); $("selInfo").textContent = ""; }
  if (it.versions && !it.versions.length){ $("selInfo").textContent = "⚠ " + (it.raison || "rien à lire pour ce chapitre"); return; }
  if (it.versions && it.versions.length > 1){                                         // plusieurs voix / versions : on choisit
    SEL.enAttente = it;
    $("selInfo").innerHTML = "ch. " + esc(it.label) + " — quelle version ? " + it.versions.map((v, k) => '<button class="btn sm" data-ver="' + k + '">' + esc(v.t) + "</button>").join("");
    return;
  }
  selFermer();
  try { await x.choisir(it, (it.versions || [])[0]); } catch (e){ log("aller : " + e.message, "e"); toast("⚠ " + e.message); }
}
function selAller(){
  const x = SEL.ctx; if (!x) return;
  const q = parseFloat(SEL.q.replace(",", ".")); if (isNaN(q)) return;
  const it = x.items.find(i => i.num === q && !i.trou);
  if (it) return selChoisir(it);
  const ok = x.items.filter(i => !i.trou && !i.off), av = ok.filter(i => i.num < q).pop(), ap = ok.find(i => i.num > q);
  $("selInfo").innerHTML = "⚠ " + (x.quoi === "page" ? "page " : "ch. ") + esc(selNumTxt(q)) + " absent" + (av || ap ? " — le plus proche : "
    + [av, ap].filter(Boolean).map(i => '<button class="btn sm" data-k="' + esc(String(i.cle)) + '">' + (x.quoi === "page" ? "p. " : "ch. ") + esc(i.label) + "</button>").join("") : "");
}
function selTrous(items){                     // numeros ENTIERS absents entre deux chapitres presents : case en pointille, non cliquable
  const ent = items.filter(i => isFinite(i.num) && Number.isInteger(i.num)).map(i => i.num);
  if (ent.length < 2) return;
  const set = new Set(ent), min = Math.min(...ent), max = Math.max(...ent);
  if (max - min > 3000) return;
  for (let n = min + 1; n < max; n++) if (!set.has(n))
    items.push({ cle: "trou-" + n, num: n, label: String(n), sous: "absent", classe: "trou", trou: true, off: true, raison: "ch. " + n + " pas dans la bibliothèque" });
  items.sort((a, b) => a.num - b.num);
}
function selCtxChapitres(slug){
  const cs = CHAPS.map((c, i) => ({ c, i })).filter(x => serieDe(x.c.dir) === slug)
    .sort((a, b) => chapNum(a.c) - chapNum(b.c) || String(a.c.chapter).localeCompare(String(b.c.chapter)));
  if (!cs.length) return null;
  const L = (BIB.lectures || {})[slug], lue = L && CHAPS.find(c => c.dir === L.d), nLu = lue ? chapNum(lue) : -Infinity;
  const R = RESUME && RESUME.chapitres;
  const items = cs.map(x => {
    const r = (R && R[x.c.dir]) || {}, n = chapNum(x.c), lu = n < nLu || (!!L && L.d === x.c.dir);
    return { cle: x.c.dir, num: n, label: isFinite(n) ? selNumTxt(n) : String(x.c.chapter), i: x.i, lu,
             narr: R ? !!r.narr : null, video: R ? !!r.video : null,
             sous: (lu ? "✓" : "") + (r.narr ? "🎙" : "") + (r.video ? "🎬" : ""),
             classe: x.c.dir === CHAP_OPEN ? "cour" : lu ? "lu" : "" };
  });
  selTrous(items);
  return { titre: "Aller au chapitre — " + (cs[0].c.title || slug), quoi: "chapitre", items,
    choisir: it => openChap(it.i),
    filtres: [{ k: "tous", t: "tous (" + cs.length + ")" }, { k: "nonlus", t: "non lus", test: it => !it.trou && !it.lu },
              { k: "narr", t: "🎙 narrés", test: it => it.narr }, { k: "vid", t: "🎬 vidéo", test: it => it.video }] };
}
function selCtxNarr(){
  const x = selCtxChapitres(serieDe(CHAP_OPEN)); if (!x) return null;
  x.titre = "Narration — aller au chapitre";
  const cours = new Set(((typeof ACT !== "undefined" && ACT.items) || []).filter(a => a.type === "narration").map(a => a.d));
  x.items.forEach(it => {
    if (it.trou) return;
    if (cours.has(it.cle)){ it.off = true; it.sous = "⏳"; it.raison = "ch. " + it.label + " : narration en cours de fabrication"; it.classe += " off"; }
    else if (it.narr === false){ it.off = true; it.raison = "ch. " + it.label + " : pas de narration avec voix"; it.classe += " off"; }
  });
  x.filtres = [{ k: "tous", t: "tous" }, { k: "narr", t: "🎙 avec narration", test: it => !it.off }];
  x.avantChoix = async it => {                                // les voix sont lues a la demande (plusieurs voix = on choisit)
    const j = await api("/manga/narrations?d=" + encodeURIComponent(it.cle));
    it.versions = (j.items || []).filter(n => n.etat === "fini" && n.audio)
      .sort((a, b) => (b.created_at || "").localeCompare(a.created_at || "")).map(n => ({ t: n.voice || n.tag, n }));
    if (!it.versions.length) it.raison = "ch. " + it.label + " : pas de narration avec voix";
  };
  x.choisir = async (it, ver) => {                            // comme ⏮ / ⏭ du lecteur : on ouvre le chapitre, puis sa narration
    $("lecAudio").pause(); clearTimeout(LEC.timer);
    await openChap(it.i);
    await Promise.all([refreshPrec().catch(() => {}), refreshMus().catch(() => {})]);
    log("lecteur : aller au ch. " + it.label + " (" + ver.n.tag + ")");
    await ouvrirLecteur([ver.n.tag]);
  };
  return x;
}
function selCtxVideo(){
  const o = VIDS.chapitres.map((c, i) => ({ c, i })).sort((a, b) => vidNum(a.c) - vidNum(b.c));
  if (!o.length) return null;
  const pos = BIB.videos_pos || {};
  const items = o.map(x => {
    const vs = x.c.videos || [], enCours = (x.c.file || []).some(f => f.etat === "en cours" || f.etat === "attente"), e = vidEtat(x.c);
    const reprise = vs.find(v => pos[v.fichier]), n = vidNum(x.c);
    const it = { cle: x.c.d, num: n, label: selNumTxt(x.c.chapitre), i: x.i, video: !!vs.length,
      versions: vs.map(v => ({ t: v.tag + (pos[v.fichier] ? " · reprise " + vidFmt(pos[v.fichier].pos) : ""), v })),
      classe: x.i === VID_COUR ? "cour" : "",
      sous: vs.length ? (e && e.cle === "refaire" ? "🟠" : "🎬") + (reprise ? " " + vidFmt(pos[reprise.fichier].pos) : "") + (enCours ? "⏳" : "") : enCours ? "⏳" : "" };
    if (e && e.cle === "refaire") it.raison = "ch. " + it.label + " : vidéo à refaire (" + (e.txt || "") + ") — lisible quand même";
    if (!vs.length){ it.off = true; it.classe += " off"; it.raison = "ch. " + it.label + (enCours ? " : vidéo en cours de fabrication" : " : pas de vidéo"); }
    return it;
  });
  selTrous(items);
  return { titre: "Vidéo — aller au chapitre", quoi: "chapitre", items,
    filtres: [{ k: "tous", t: "tous" }, { k: "vid", t: "🎬 avec vidéo", test: it => it.video }, { k: "rep", t: "▶ commencées", test: it => it.video && /\\d:\\d/.test(it.sous) }],
    choisir: (it, ver) => vidOuvrir(it.i, ver && ver.v.tag) };
}
function selCtxPages(){
  if (typeof LB_LISTE === "undefined" || !LB_LISTE || !LB_LISTE.length) return null;
  const items = LB_LISTE.map((it, k) => ({ cle: "p" + k, num: k + 1, label: String(k + 1), classe: k === LB ? "cour" : "", k }));
  return { titre: "Aller à la page (" + LB_LISTE.length + ")", quoi: "page", items, filtres: [], choisir: it => lbShow(it.k) };
}
function selContexte(){
  if (!$("vidLecteur").hidden) return selCtxVideo();
  if (!$("lecteur").hidden) return LEC.aveugle ? null : selCtxNarr();          // lecture « a l'aveugle » : pas de sommaire
  if (!$("lightbox").hidden) return selCtxPages();
  const c = nfCtx();
  if (c === "chapitre") return selCtxChapitres(serieDe(CHAP_OPEN));
  if (c === "serie") return selCtxChapitres(LIB_SERIE);
  return null;
}
function selGlisserHaut(el){                  // glisser la barre VERS LE HAUT (> 50 px, net) = ouvrir ; gauche / droite gardent leur role
  if (!el) return; let x0 = null, y0 = 0;
  el.addEventListener("touchstart", e => { const t = e.touches[0]; x0 = t.clientX; y0 = t.clientY; }, { passive: true });
  el.addEventListener("touchend", e => { if (x0 === null) return; const t = e.changedTouches[0], dx = t.clientX - x0, dy = t.clientY - y0; x0 = null;
    if (dy < -50 && Math.abs(dy) > Math.abs(dx) * 1.5){ const c = selContexte(); if (c) selOuvrir(c); } }, { passive: true });
}
(function selInit(){
  $("selFermer").onclick = selFermer; $("selVoile").onclick = selFermer;
  $("selNum").addEventListener("input", () => { SEL.q = $("selNum").value.trim(); $("selInfo").textContent = ""; SEL.enAttente = null; selRendre();
    $("selAller").textContent = SEL.q ? "Aller au " + SEL.q : "Aller"; });
  $("selNum").addEventListener("keydown", e => { if (e.key === "Enter"){ e.preventDefault(); selAller(); } });
  $("selAller").onclick = selAller;
  $("selFiltres").onclick = e => { const b = e.target.closest("[data-f]"); if (!b) return; SEL.filtre = b.dataset.f;
    document.querySelectorAll("#selFiltres [data-f]").forEach(x => x.classList.toggle("on", x === b)); selRendre(); };
  $("selFeuille").addEventListener("click", e => {
    const v = e.target.closest("[data-ver]");
    if (v && SEL.enAttente){ const it = SEL.enAttente, x = SEL.ctx, ver = it.versions[+v.dataset.ver]; selFermer();
      Promise.resolve(x.choisir(it, ver)).catch(err => { log("aller : " + err.message, "e"); toast("⚠ " + err.message); }); return; }
    const b = e.target.closest("[data-k]"); if (!b || !SEL.ctx) return;
    selChoisir(SEL.ctx.items.find(i => String(i.cle) === b.dataset.k));
  });
  const f = $("selFeuille"); let y0 = null;                                    // glisser la feuille vers le bas = fermer
  f.addEventListener("touchstart", e => { y0 = e.target.closest(".sel-grille") && $("selGrille").scrollTop > 0 ? null : e.touches[0].clientY; }, { passive: true });
  f.addEventListener("touchend", e => { if (y0 === null) return; const dy = e.changedTouches[0].clientY - y0; y0 = null; if (dy > 90) selFermer(); }, { passive: true });
  document.addEventListener("keydown", e => {
    if (!$("selFeuille").hidden){ if (e.key === "Escape"){ e.preventDefault(); e.stopImmediatePropagation(); selFermer(); } return; }
    if ((e.key === "g" || e.key === "G") && !e.ctrlKey && !e.metaKey && !e.altKey && !e.target.closest("input, textarea, select, [contenteditable]")){
      const c = selContexte(); if (c){ e.preventDefault(); selOuvrir(c); } }
  }, true);
  [$("navFlot"), $("vidBar"), document.querySelector("#lightbox .lbbar"), document.querySelector("#lecteur .lec-ctl")].forEach(selGlisserHaut);
  // toucher la bulle / le titre (l'appui long de la bulle garde son role : NF.glisse bloque ce clic)
  $("nfInfo").addEventListener("click", () => { if (NF.glisse) return; const c = selContexte(); if (c) selOuvrir(c); });
  ["vidLecTitre", "lecTitre", "lbName"].forEach(id => { const el = $(id); if (!el) return; el.style.cursor = "pointer";
    el.title = "toucher : aller à… (ou glisser la barre du bas vers le haut)";
    el.addEventListener("click", ev => { ev.stopPropagation(); const c = selContexte(); if (c) selOuvrir(c); }); });
})();
/* v2.68.0 : evenements du lecteur video */''')

open(P, "wb").write(s.encode("utf-8"))
print("patche")
