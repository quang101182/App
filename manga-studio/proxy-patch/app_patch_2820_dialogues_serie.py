# -*- coding: utf-8 -*-
"""v2.82.0 (27/09, D10 -- maquette_dialogues_serie_v1 VALIDEE par Quang 02h28) : bouton 🎭 Dialogues dans la fiche de la SERIE
(a cote de 🎬 Videos, compteur des chapitres qui ont des dialogues ; telephone : « Site » passe dans ⋯) -> panneau « 🎭 Dialogues
de la serie » SEPARE du panneau Videos de la narration : distribution du manga, resume (prets / a mettre en voix / credits
restants), filtre « Avec dialogues » (defaut) / « Tous », une ligne par chapitre (etat, pages, credits, video, FR partiel ;
▶ Lire, ▶ Video, ⬇, 🔊 Generer, ✏), « plusieurs chapitres » (du ch. X au ch. Y : Preparer / Generer les voix). Badge 🎭 dans la
liste des chapitres. Serveur : patch_dialogues_6 (« dlg » au resume). Suppose app_patch_2818. Rejouable."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v2.82.0" in s[:400]:
    print("deja applique"); sys.exit(0)
if "v2.81.8" not in s[:400]:
    print("ERREUR : appliquer d'abord app_patch_2818_lecteur_format.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"
BS = "\\"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


# --- le bouton, et « Site » dans ⋯ sur telephone
rep("""          <button class="btn sm" id="btnVideos" title="les vidéos des chapitres de cette série"><span class="ic">🎬</span><span>Vidéos</span></button>""",
    """          <button class="btn sm" id="btnVideos" title="les vidéos des chapitres de cette série"><span class="ic">🎬</span><span>Vidéos</span></button>
          <button class="btn sm" id="btnDlgSerie" title="les dialogues (une voix par personnage) des chapitres de cette série"><span class="ic">🎭</span><span>Dialogues</span><span class="dlgs-nb" id="dlgsNb" hidden></span></button>""")
rep("""              <button role="menuitem" id="btnPochAni" title="pochette officielle de la série (AniList)">🖼 Pochette officielle</button>""",
    """              <button role="menuitem" class="menu-tel" id="btnSiteMenu" title="ouvrir le site du dernier chapitre capturé">🔗 Site</button>
              <button role="menuitem" id="btnPochAni" title="pochette officielle de la série (AniList)">🖼 Pochette officielle</button>""")

# --- le panneau (meme gabarit que le panneau Videos)
rep("""  <!-- v1.99.0 : narrations gardees DANS ce telephone (lecture PC eteint) -->""",
    """  <!-- v2.82.0 (D10, maquette_dialogues_serie_v1) : les DIALOGUES de la serie, a part des videos de la narration -->
  <div class="dlgs-box pan" id="dlgsBox" hidden>
    <div class="pan-barre"><button class="btn sm retour" id="dlgsFermer">← <span class="pan-serie"></span></button><span class="esp"></span></div>
    <div class="pan-fiche dlgs-fiche"><h3>🎭 Dialogues de la série</h3>
      <div class="muted dlgs-dist" id="dlgsDist"></div>
      <div class="dlgs-resume" id="dlgsResume"></div>
      <div class="dlgs-filtre"><button class="dlgs-f on" data-f="avec" id="dlgsFAvec">Avec dialogues</button><button class="dlgs-f" data-f="tous" id="dlgsFTous">Tous</button></div>
      <div id="dlgsListe" class="dlgs-liste"></div>
      <div class="dlgs-lot">Plusieurs chapitres : du ch. <input id="dlgsDe" inputmode="decimal"> au ch. <input id="dlgsA" inputmode="decimal">
        <button class="btn sm" id="dlgsPrep">🎭 Préparer</button><button class="btn sm" id="dlgsVoix">🔊 Générer les voix</button>
        <span class="muted">seuls les chapitres traduits en français sont traités, dans l'ordre ; quota épuisé = arrêt net, ce qui est fait est gardé</span></div>
    </div>
  </div>
  <!-- v1.99.0 : narrations gardees DANS ce telephone (lecture PC eteint) -->""")

# --- le style
rep(""".dlgl-manq[hidden]{display:none}""", """.dlgl-manq[hidden]{display:none}
.dlgs-nb{font-size:11px;border:1px solid #2d7f6c;color:#8fe6cf;border-radius:99px;padding:0 6px;margin-left:2px;line-height:16px}
.dlgs-nb[hidden]{display:none}
.menu-pan>.menu-tel{display:none}
.dlgs-fiche{border-left:4px solid #3fc7a8}
.dlgs-dist{display:flex;flex-wrap:wrap;align-items:center;gap:6px;font-size:13px}
.dlgs-resume{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}
.dlgs-filtre{display:flex;gap:6px;margin:6px 0}
.dlgs-f{font:inherit;font-size:13px;border:1px solid var(--line);border-radius:99px;padding:3px 10px;background:none;color:var(--dim);cursor:pointer}
.dlgs-f.on{border-color:#3fc7a8;color:#3fc7a8}
.dlgs-l{display:grid;grid-template-columns:110px 1fr auto;gap:10px;align-items:center;padding:9px 4px;border-top:1px solid var(--line)}
.dlgs-l .n{font:inherit;font-weight:700;background:none;border:0;color:var(--txt);text-align:left;padding:0;cursor:pointer}
.dlgs-l .e{font-size:13px;color:var(--dim);min-width:0;overflow-wrap:anywhere}.dlgs-l .e b{color:var(--txt);font-weight:600}
.dlgs-l .a{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end}
.dlgs-l.off .n{color:var(--dim)}
.dlgs-lot{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:10px;padding-top:10px;border-top:1px solid var(--line);font-size:14px}
.dlgs-lot input{width:64px}.dlgs-lot .muted{font-size:12px;flex-basis:100%}
@media (max-width:520px){ #btnSerieSite{display:none} .menu-pan>.menu-tel{display:flex}
  .dlgs-l{grid-template-columns:1fr;gap:4px}.dlgs-l .a{justify-content:flex-start} }""")

# --- le badge 🎭 de la liste des chapitres
rep("""  if ((r.trad_partiel || []).length) m.push("🌐 " + r.trad_partiel.map(x => x.toUpperCase()).join(" ") + " partiel");   // v2.81.5""",
    """  if ((r.trad_partiel || []).length) m.push("🌐 " + r.trad_partiel.map(x => x.toUpperCase()).join(" ") + " partiel");   // v2.81.5
  if (r.dlg) m.push("🎭");                                                                                   // v2.82.0 (D10)""")

# --- le compteur suit le resume et la serie ouverte ; le panneau se ferme quand on quitte la serie (comme Videos)
rep("""  try { RESUME = await api("/manga/resume"); renderLib(); } catch (e){ log("résumé : " + e.message, "w"); return; }""",
    """  try { RESUME = await api("/manga/resume"); renderLib(); dlgsNbMaj(); } catch (e){ log("résumé : " + e.message, "w"); return; }""")
rep("""  document.querySelectorAll(".pan-serie").forEach(x => { x.textContent = serie.title; });     // v2.31.0 : « ← Claymore »""",
    """  document.querySelectorAll(".pan-serie").forEach(x => { x.textContent = serie.title; });     // v2.31.0 : « ← Claymore »
  if (typeof dlgsNbMaj === "function") dlgsNbMaj();                                           // v2.82.0""")
rep("""  if (!$("vidBox").hidden) $("vidFermer").click();
  renderLib();""", """  if (!$("vidBox").hidden) $("vidFermer").click();
  if (!$("dlgsBox").hidden) $("dlgsFermer").click();                                          // v2.82.0
  renderLib();""")
rep("""  if (!$("vidBox").hidden) return { nom: "Vidéos", fermer: () => $("vidFermer").click() };""",
    """  if (!$("vidBox").hidden) return { nom: "Vidéos", fermer: () => $("vidFermer").click() };
  if (!$("dlgsBox").hidden) return { nom: "Dialogues", fermer: () => $("dlgsFermer").click() };   // v2.82.0""")

# --- la logique
rep("""new MutationObserver(() => { dlgVidBox.style.display = dlgVidBox.hidden ? "none" : "flex"; }).observe(dlgVidBox, { attributes: true, attributeFilter: ["hidden"] });""",
    """new MutationObserver(() => { dlgVidBox.style.display = dlgVidBox.hidden ? "none" : "flex"; }).observe(dlgVidBox, { attributes: true, attributeFilter: ["hidden"] });
/* ---- v2.82.0 (D10) : 🎭 Dialogues de la SERIE (maquette_dialogues_serie_v1 validee par Quang 27/09 02h28) ---- */
const DLGS = { serie: null, det: {}, chs: [], filtre: "avec", poll: null };
function dlgsNbMaj(){
  const n = CHAPS.filter(c => serieDe(c.dir) === LIB_SERIE && RESUME && (RESUME.chapitres[c.dir] || {}).dlg).length;
  $("dlgsNb").textContent = n; $("dlgsNb").hidden = !n;
}
async function dlgsCharger(serie){
  DLGS.serie = serie; clearTimeout(DLGS.poll);
  const chs = CHAPS.map((c, i) => ({ c, i })).filter(x => serieDe(x.c.dir) === serie).sort((a, b) => chapNum(a.c) - chapNum(b.c));
  if (!DLGS.chs.length || DLGS.chs[0].c.dir.split("/")[0] !== serie) $("dlgsListe").innerHTML = '<p class="muted">…</p>';
  const avec = chs.filter(x => ((RESUME && RESUME.chapitres[x.c.dir]) || {}).dlg);
  const det = await Promise.all(avec.map(async x => {
    try {
      const [e, p] = await Promise.all([api("/manga/dialogues?d=" + encodeURIComponent(x.c.dir)),
                                        api("/manga/dialogues_plan?d=" + encodeURIComponent(x.c.dir)).catch(() => null)]);
      return [x.c.dir, { e, p }];
    } catch (err) { return [x.c.dir, null]; }
  }));
  if (DLGS.serie !== serie) return;
  DLGS.det = Object.fromEntries(det); DLGS.chs = chs;
  if (!DLG.solde) await dlgSolde().catch(() => null);
  dlgsRendre();
  if (det.some(([, v]) => v && v.e && v.e.en_cours)) DLGS.poll = setTimeout(() => { if (!$("dlgsBox").hidden) dlgsCharger(serie); }, 4000);
}
function dlgsLigne(x){
  const d = x.c.dir, r = (RESUME && RESUME.chapitres[d]) || {}, dt = DLGS.det[d];
  const b = (k, t, pri) => '<button class="btn sm' + (pri ? " pri" : "") + '" data-dlgs="' + k + '" data-d="' + esc(d) + '">' + t + "</button>";
  const nom = '<button class="n" data-dlgs="ouvrir" data-d="' + esc(d) + '" title="ouvrir ce chapitre">Chapitre ' + esc(x.c.chapter) + "</button>";
  if (dt && dt.e && dt.e.doc){
    const doc = dt.e.doc, p = dt.p || {}, lues = (doc.repliques || []).filter(y => y.lire).length;
    const pv = (doc.pages_vues && doc.pages_vues.length) ? doc.pages_vues : [...new Set((doc.repliques || []).map(y => y.page))].sort((a, c) => a - c);
    const etat = dt.e.en_cours ? "⏳ en cours" : p.a_faire ? "🟠 " + (p.deja ? p.a_faire + " à faire ou refaire · " + p.deja + " prêtes" : lues + " répliques à mettre en voix")
      : "✅ prêts · " + lues + " répliques";
    const extra = pv.length ? ["p. " + dlgPlagesTxt(pv)] : [];
    if (p.a_faire) extra.push("≈ " + fmtCr(p.credits) + " crédits");
    if (p.video === "a_jour") extra.push("🎬 vidéo à jour" + (doc.video && doc.video.duree ? " (" + Math.round(doc.video.duree) + " s)" : ""));
    else if (p.video === "perimee") extra.push("🎬 vidéo à refaire");
    if ((r.trad_partiel || []).includes("fr")) extra.push("🌐 FR partiel");
    const act = (p.deja ? b("lire", "▶ Lire", !p.a_faire) : "") + (doc.video && p.video && p.video !== "absente" ? b("video", "▶ Vidéo") + b("dl", "⬇") : "")
      + (p.a_faire && !dt.e.en_cours ? b("gen", "🔊 Générer", true) : "") + b("corr", "✏");
    return '<div class="dlgs-l" data-dir="' + esc(d) + '">' + nom + '<span class="e"><b>' + esc(etat) + "</b>" + (extra.length ? " · " + esc(extra.join(" · ")) : "")
      + '</span><span class="a">' + act + "</span></div>";
  }
  const etat = r.langue === "fr" ? "déjà en VF · pas encore préparé" : (r.trad || []).includes("fr") ? "traduit · pas encore préparé"
    : (r.trad_partiel || []).includes("fr") ? "🌐 FR partiel · pas encore préparé" : "pas encore en français — les pages choisies peuvent être traduites à la préparation";
  return '<div class="dlgs-l off" data-dir="' + esc(d) + '">' + nom + '<span class="e">' + esc(etat) + '</span><span class="a">' + b("ouvrir", "Ouvrir") + "</span></div>";
}
function dlgsRendre(){
  const avec = DLGS.chs.filter(x => DLGS.det[x.c.dir] && DLGS.det[x.c.dir].e && DLGS.det[x.c.dir].e.doc);
  const pret = avec.filter(x => !(DLGS.det[x.c.dir].p || {}).a_faire).length, afaire = avec.length - pret;
  const e0 = avec.length ? DLGS.det[avec[0].c.dir].e : null, dist = ((e0 && e0.distribution) || {}).persos || [];
  $("dlgsDist").innerHTML = dist.length
    ? "Distribution du manga : " + dist.slice(0, 3).map(p => '<span class="dlg-pastille" style="background:' + esc(p.couleur || "#9aa6b8") + '"></span>' + esc(p.nom)).join(" · ")
      + (dist.length > 3 ? " · +" + (dist.length - 3) : "") + ' <button class="btn sm" data-dlgs="corr" data-d="' + esc(avec[0].c.dir) + '">✏ Régler les voix</button>'
    : "Aucun personnage pour l'instant : prépare un chapitre (ligne 🎭 du chapitre, ou « plusieurs chapitres » plus bas).";
  const s = DLG.solde && DLG.solde.ok ? DLG.solde.restants : null;
  $("dlgsResume").innerHTML = (pret ? '<span class="dlg-pill cr">' + pret + " chapitre" + (pret > 1 ? "s" : "") + " prêt" + (pret > 1 ? "s" : "") + " à lire</span>" : "")
    + (afaire ? '<span class="dlg-pill ko">' + afaire + " à mettre en voix</span>" : "")
    + '<span class="dlg-pill">' + (DLGS.chs.length - avec.length) + " non commencé" + (DLGS.chs.length - avec.length > 1 ? "s" : "") + "</span>"
    + (s !== null ? '<span class="dlg-pill cr">reste ' + fmtCr(s) + " crédits</span>" : "");
  $("dlgsFAvec").textContent = "Avec dialogues (" + avec.length + ")"; $("dlgsFTous").textContent = "Tous (" + DLGS.chs.length + ")";
  document.querySelectorAll("#dlgsBox .dlgs-f").forEach(y => y.classList.toggle("on", y.dataset.f === DLGS.filtre));
  const l = DLGS.filtre === "tous" ? DLGS.chs : avec;
  $("dlgsListe").innerHTML = l.map(dlgsLigne).join("")
    || '<p class="muted aide" style="margin:6px 0">Aucun chapitre de cette série n' + "'" + 'a encore de dialogues. « Tous » montre les chapitres à préparer.</p>';
  if (!$("dlgsDe").value && DLGS.chs.length){ $("dlgsDe").value = DLGS.chs[0].c.chapter; $("dlgsA").value = DLGS.chs[DLGS.chs.length - 1].c.chapter; }
}
async function dlgsCorriger(d){                   // ✏ : le chapitre s'ouvre, puis son ecran de correction
  const i = CHAPS.findIndex(c => c.dir === d); if (i < 0) return;
  $("dlgsBox").hidden = true;
  await openChap(i);
  for (let k = 0; k < 60 && !(DLG.d === d && DLG.e && DLG.e.doc); k++) await new Promise(r => setTimeout(r, 150));
  dlgPrepOuvrir();
}
$("btnDlgSerie").onclick = () => {
  $("dlgsBox").hidden = !$("dlgsBox").hidden;
  if (!$("dlgsBox").hidden){ $("dlgsDe").value = ""; DLGS.chs = []; dlgsCharger(LIB_SERIE).catch(e => log("dialogues de la série : " + e.message, "e"));
    $("dlgsBox").scrollIntoView({ behavior: "smooth", block: "start" }); }
};
$("dlgsFermer").onclick = () => { $("dlgsBox").hidden = true; clearTimeout(DLGS.poll); };
$("btnSiteMenu").onclick = () => $("btnSerieSite").click();
document.querySelectorAll("#dlgsBox .dlgs-f").forEach(el => el.addEventListener("click", () => { DLGS.filtre = el.dataset.f; dlgsRendre(); }));
async function dlgsLot(action){
  const de = parseFloat($("dlgsDe").value), a = parseFloat($("dlgsA").value);
  if (!(de <= a)) return toast("plage de chapitres invalide");
  if (!confirm((action === "preparer" ? "Préparer" : "Générer les voix de") + " les chapitres " + de + " à " + a + " de cette série ?""" + BS + "n" + BS + """n"
      + "Seuls les chapitres traduits en français sont traités, dans l'ordre. "
      + (action !== "preparer" ? "Si le quota ElevenLabs tombe (" + dlgSoldeTxt() + "), tout s'arrête net : ce qui est fait est gardé." : ""))) return;
  try { const r = await api("/manga/dialogues_lot", { serie: DLGS.serie, de, a, action }); if (r.error) throw new Error(r.error);
        toast("🎭 dialogues : chapitres " + de + " à " + a + " lancés"); setTimeout(() => dlgsCharger(DLGS.serie), 1500); }
  catch (err) { toast("dialogues : " + err.message); }
}
$("dlgsPrep").onclick = () => dlgsLot("preparer");
$("dlgsVoix").onclick = () => dlgsLot("voix");
document.addEventListener("click", async ev => {
  const t = ev.target.closest("#dlgsBox [data-dlgs]"); if (!t) return;
  const d = t.dataset.d, dt = DLGS.det[d] || {}, doc = (dt.e || {}).doc || {};
  const k = t.dataset.dlgs;
  if (k === "ouvrir"){ const i = CHAPS.findIndex(c => c.dir === d); if (i >= 0){ $("dlgsBox").hidden = true; openChap(i); } }
  else if (k === "lire") dlgLecteur(d, 0);
  else if (k === "corr") dlgsCorriger(d);
  else if (k === "video" && doc.video){
    const c = CHAPS.find(y => y.dir === d);
    $("dlgVidTitre").textContent = "🎭 Dialogues" + (c ? " · ch. " + c.chapter : "");
    $("dlgVidEl").src = CFG.base + "/manga/video_file?p=" + encodeURIComponent(doc.video.fichier) + "&v=" + encodeURIComponent(doc.video.t || "") + (CFG.key ? "&_k=" + encodeURIComponent(CFG.key) : "");
    dlgVidBox.hidden = false; $("dlgVidEl").play().catch(() => {});
  }
  else if (k === "dl" && doc.video){
    const a = document.createElement("a");
    a.href = CFG.base + "/manga/video_file?p=" + encodeURIComponent(doc.video.fichier) + "&dl=1&v=" + encodeURIComponent(doc.video.t || "") + (CFG.key ? "&_k=" + encodeURIComponent(CFG.key) : "");
    document.body.appendChild(a); a.click(); a.remove();
  }
  else if (k === "gen"){
    const p = dt.p || {}, c = CHAPS.find(y => y.dir === d);
    if (DLG.solde && DLG.solde.ok && p.credits > DLG.solde.restants) return toast("il faut ≈ " + fmtCr(p.credits) + " crédits, il en reste " + fmtCr(DLG.solde.restants) + " — aucun autre moteur");
    if (!confirm("Générer les " + p.a_faire + " voix manquantes du ch. " + (c ? c.chapter : "") + " (≈ " + fmtCr(p.credits) + " crédits, " + dlgSoldeTxt() + ") ?")) return;
    try { const r = await api("/manga/dialogues_lancer", { d, action: "voix" }); if (r.error) throw new Error(r.error); toast("🔊 voix lancées"); setTimeout(() => dlgsCharger(DLGS.serie), 1500); }
    catch (err) { toast("voix : " + err.message); }
  }
});""")
s = s.replace("<title>Manga Studio v2.81.8</title>", "<title>Manga Studio v2.82.0</title>", 1)
s = s.replace('id="verBadge">v2.81.8<', 'id="verBadge">v2.82.0<', 1)
s = s.replace('const VERSION = "2.81.8";', 'const VERSION = "2.82.0";   // v2.82.0 : 🎭 Dialogues de la serie (D10)', 1)
assert s.count("2.82.0") >= 4
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
