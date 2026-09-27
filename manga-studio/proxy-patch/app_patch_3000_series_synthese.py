# -*- coding: utf-8 -*-
"""v3.0.0 (27/09, maquette_series_synthese_v1 validee par Quang 16h55 : « go »).
V  : 🎬 Videos de la serie = SYNTHESE (mesure avant : 5 077 px a 360 px sur une serie de 61 ch.) : resume en pastilles,
     « Generer les manquantes » en principal, les chapitres SANS narration replies en UNE ligne (voir / masquer), « › » par
     ligne = le chapitre, bloc 🎬 ouvert ; camera, reglages, cases a cocher et selection derriere « ⚙ Reglages et selection ».
     La liste, la selection, la file, le zip : le code d'avant, intact (on range l'affichage, on ne refait rien).
D  : 🎭 Dialogues de la serie = une ligne par chapitre AVEC dialogues, ses PLAGES en pastilles, ▶ (action d'avant), « › » =
     le chapitre bloc 🎭 ouvert, « ＋ plage » = idem + formulaire « Nouvelle plage » pret ; « ＋ Dialogues d'un autre
     chapitre… » ; chapitres sans dialogues replies en UNE ligne. dplListe / dplInfo generalises a n'importe quel chapitre.
VX : choix de la voix groupe Hommes / Femmes dans chaque famille, le genre du personnage EN PREMIER.
C  : couleurs par genre (memes familles que dialogues.py 1.18.0) : pastilles de la famille du genre en tete ;
     « 🎨 Couleurs selon le genre » dans ✏ (seuls les personnages de l'autre famille changent, sur confirmation).
Suppose v2.99.2. Rejouable."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v3.0.0" in s[:900]:
    print("deja applique"); sys.exit(0)
if "v2.99.2" not in s[:1400]:
    print("ERREUR : appliquer d'abord app_patch_2992_fil_doublon.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:80], s.count(a))
    s = s.replace(a, b)


rep("<title>Manga Studio v2.99.2</title>", "<title>Manga Studio v3.0.0</title>")
rep('<span class="ver" id="verBadge">v2.99.2</span>', '<span class="ver" id="verBadge">v3.0.0</span>')
rep('const VERSION = "2.99.2";', 'const VERSION = "3.0.0";   // v3.0.0 : Videos et Dialogues de la serie en SYNTHESE, voix groupees par genre, couleurs par genre')

CSS = r"""/* v3.0.0 : syntheses de serie (maquette_series_synthese_v1) */
#vidBox.vd-compact #vidReg,#vidBox.vd-compact #vidCamSerie,#vidBox.vd-compact #vidSel,#vidBox.vd-compact .lot-sel{display:none}
#vidBox .vid-it{grid-template-columns:22px minmax(0,1fr) repeat(5,32px)}
#vidBox.vd-compact .vid-it{grid-template-columns:0 minmax(0,1fr) repeat(5,32px)}#vidBox.vd-compact [data-vid-coche]{visibility:hidden;width:0}
#vidBox .vid-it.vd-plie{display:none}
.vd-resume{display:flex;flex-wrap:wrap;gap:5px;margin:4px 0 8px}
.vd-plie-l{display:flex;align-items:center;gap:8px;border:1px dashed var(--line);border-radius:8px;padding:8px;color:var(--dim);font-size:13px;margin:4px 0 0}
.vd-plie-l span{flex:1;min-width:0}.vd-plie-l small{display:block;font-size:11.5px}
#dlgsBox .dlgs-f{display:none}
.dls-pl{display:inline-block;font-size:11.5px;border:1px solid var(--line);border-radius:7px;padding:1px 6px;margin:2px 3px 0 0;white-space:nowrap}
.dls-pl.plus{color:#3fc7a8;border-style:dashed;cursor:pointer;background:none;font:inherit;font-size:11.5px}
.dls-autre{display:flex;gap:6px;align-items:center;margin:0 0 6px}.dls-autre select{flex:1;min-width:0}
.dlgp-coul .sep{width:1px;height:18px;background:var(--line);margin:0 3px}
"""
rep("#dlgPrep{position:fixed;inset:0;", CSS + "#dlgPrep{position:fixed;inset:0;")

# ---- VX : voix groupees par genre, genre du personnage en premier
rep("""function dlgOptVoix(sel, opt1){
  const fav = DLG.fav || [], sep = t => '<option disabled>──── ' + t + " ────</option>";
  const fv = fav.map(i => DLG.voix.find(v => v.id === i)).filter(Boolean), reste = DLG.voix.filter(v => !fav.includes(v.id));
  const fr = reste.filter(v => v.fr), au = reste.filter(v => !v.fr);
  return (fv.length ? sep("⭐ Mes voix préférées") + fv.map(v => opt1(v, sel)).join("") : "")
    + (fr.length ? sep("🇫🇷 Voix françaises") + fr.map(v => opt1(v, sel)).join("") + sep("Autres voix (accent anglais)") : "")
    + au.map(v => opt1(v, sel)).join("");
}""", """function dlgOptVoix(sel, opt1, genre){
  const fav = DLG.fav || [], sep = t => '<option disabled>──── ' + t + " ────</option>";
  const fv = fav.map(i => DLG.voix.find(v => v.id === i)).filter(Boolean), reste = DLG.voix.filter(v => !fav.includes(v.id));
  const fr = reste.filter(v => v.fr), au = reste.filter(v => !v.fr);
  // v3.0.0 (VX) : Hommes / Femmes dans chaque famille, le genre du personnage EN PREMIER
  const ordre = String(genre || "").toLowerCase() === "femme" ? [["female", "femmes"], ["male", "hommes"]] : [["male", "hommes"], ["female", "femmes"]];
  const grp = (l, titre) => ordre.map(([g, t]) => { const x = l.filter(v => v.genre === g); return x.length ? sep(titre + " — " + t) + x.map(v => opt1(v, sel)).join("") : ""; }).join("")
    + ((x => x.length ? sep(titre + " — autres") + x.map(v => opt1(v, sel)).join("") : "")(l.filter(v => v.genre !== "male" && v.genre !== "female")));
  return (fv.length ? sep("⭐ Mes voix préférées") + fv.map(v => opt1(v, sel)).join("") : "")
    + (fr.length ? grp(fr, "🇫🇷 Françaises") : "") + grp(au, fr.length ? "🇬🇧 Accent anglais" : "Voix");
}""")
rep("""  const optV = sel => dlgOptVoix(sel, opt1)""", """  const optV = (sel, g) => dlgOptVoix(sel, opt1, g)""")
rep("""'<label>Voix</label><div class="dlgp-ligne"><select data-k="voix_el">' + optV(p.voix_el) + "</select>\"""",
    """'<label>Voix</label><div class="dlgp-ligne"><select data-k="voix_el">' + optV(p.voix_el, p.genre) + "</select>\"""")

# ---- C : couleurs par genre
rep("""const DLG_PAL = [""", """const DLG_PAL_H = ["#6fb8ff", "#4fd6e8", "#5fe3a1", "#ffb347", "#f5e663", "#c7a17a", "#7f8cff"];   // v3.0.0 : = dialogues.py 1.18.0
const DLG_PAL_F = ["#ff5fa2", "#e88aff", "#b58cff", "#ff7a5c", "#ff9ec7", "#f7b2ff"];
const dlgPalDe = g => ({ homme: DLG_PAL_H, femme: DLG_PAL_F })[String(g || "").toLowerCase()] || null;
function dlgPalHtml(coul, g){                     // v3.0.0 : la famille du genre d'abord, puis l'autre (tout reste choisissable)
  const f = dlgPalDe(g), a = f === DLG_PAL_F ? DLG_PAL_H : f === DLG_PAL_H ? DLG_PAL_F : null;
  const i = k => '<i class="' + (k === coul ? "on" : "") + '" style="background:' + k + '" data-coul="' + k + '"></i>';
  return f ? f.map(i).join("") + '<span class="sep"></span>' + a.map(i).join("") : DLG_PAL_H.concat(DLG_PAL_F).map(i).join("");
}
const DLG_PAL = [""")
rep("""'<label>Couleur</label><div class="dlgp-coul">' + DLG_PAL.map(k => '<i class="' + (k === coul ? "on" : "") + '" style="background:' + k + '" data-coul="' + k + '"></i>').join("") + "</div>\"""",
    """'<label>Couleur</label><div class="dlgp-coul">' + dlgPalHtml(coul, p.genre) + "</div>\"""")
rep("""    + '<button class="btn sm" id="dlgpAjout">✚ ajouter</button></span></h3><div class="dlgp-persos">';""",
    """    + '<button class="btn sm" id="dlgpAjout">✚ ajouter</button> <button class="btn sm" id="dlgpRecol" title="hommes : couleurs froides / franches ; femmes : chaudes / pastel">🎨 Couleurs selon le genre</button></span></h3><div class="dlgp-persos">';""")

JS = r"""/* ---- v3.0.0 (C) : « 🎨 Couleurs selon le genre » -- seuls les personnages dont la couleur est de l'AUTRE famille changent ---- */
document.addEventListener("click", async ev => {
  if (!ev.target.closest("#dlgpRecol")) return;
  const persos = dlgPersos().filter(p => !p.narrateur), prises = new Set(persos.map(p => p.couleur)), chg = [];
  persos.forEach(p => {
    const f = dlgPalDe(p.genre); if (!f || f.includes(p.couleur)) return;
    const c = f.find(k => !prises.has(k)) || f[chg.length % f.length];
    prises.add(c); chg.push({ nom: p.nom, couleur: c });
  });
  if (!chg.length) return toast("🎨 toutes les couleurs sont déjà dans la famille du genre");
  if (!confirm("Changer la couleur de " + chg.length + " personnage" + (chg.length > 1 ? "s" : "") + " ?\n\n" + chg.map(x => "· " + x.nom).join("\n")
      + "\n\nLes autres gardent la leur. Une couleur se rechoisit à la main à tout moment.")) return;
  await dlgRegler({ persos: chg });
  toast("🎨 " + chg.length + " couleur" + (chg.length > 1 ? "s" : "") + " mise" + (chg.length > 1 ? "s" : "") + " selon le genre");
});

/* ---- v3.0.0 : aller au CHAPITRE depuis un panneau de serie, bloc voulu ouvert (et « nouvelle plage » prete) ---- */
async function serVersChap(d, bloc, nouv){
  const i = CHAPS.findIndex(c => c.dir === d); if (i < 0) return;
  $("vidBox").hidden = true; $("dlgsBox").hidden = true; clearTimeout(DLGS.poll);
  await openChap(i);
  clOuvrir(bloc);
  if (bloc === "dlg"){
    // les dialogues de CE chapitre charges ET affiches (DLG.e.d) -- sinon le chargement remet le formulaire a zero
    for (let k = 0; k < 80 && !(DLG.d === d && DLG.e && DLG.e.d === d && !DLG.charge && $("dplListe")); k++) await new Promise(r => setTimeout(r, 150));
    await new Promise(r => setTimeout(r, 250));
    if (nouv){ const b = document.querySelector("#dplListe [data-dpl=nouv]"); if (b) b.click(); }
  }
  const bx = document.querySelector(bloc === "vid" ? "#chapVid" : "#dlgBox");
  if (bx) setTimeout(() => bx.scrollIntoView({ behavior: "smooth", block: "start" }), 120);
}

/* ---- v3.0.0 (V) : 🎬 Videos de la serie en SYNTHESE ---- */
const VDX = { tout: false, reglages: false };
function vdCompact(){
  const box = $("vidBox"); if (!box || !VIDS || !VIDS.chapitres) return;
  box.classList.toggle("vd-compact", !VDX.reglages);
  const es = VIDS.chapitres.map(vidEtat), n = k => es.filter(e => e.cle === k).length;
  const pretes = VIDS.chapitres.filter(c => (c.videos || []).length), o = pretes.reduce((a, c) => a + (c.videos[0].taille || 0), 0);
  let r = $("vdResume"); if (!r){ r = document.createElement("div"); r.id = "vdResume"; r.className = "vd-resume"; $("vidReg").before(r); }
  const pill = (t, cls) => '<span class="dlg-pill ' + (cls || "") + '">' + t + "</span>";
  r.innerHTML = (n("ok") ? pill("✓ " + n("ok") + " prête" + (n("ok") > 1 ? "s" : "") + " · " + fmtGo(o), "cr") : "")
    + (n("refaire") ? pill("🟠 " + n("refaire") + " à refaire", "ko") : "") + (n("cours") + n("attente") ? pill("⏳ " + (n("cours") + n("attente")) + " en cours") : "")
    + (n("echec") ? pill("❌ " + n("echec") + " en échec", "ko") : "") + (n("aucune") ? pill("⚪ " + n("aucune") + " à faire") : "")
    + (n("sansvoix") ? pill(n("sansvoix") + " sans narration") : "");
  $("vidManquantes").classList.add("pri");
  let t = $("vdReg");
  if (!t){ t = document.createElement("button"); t.id = "vdReg"; t.className = "btn sm"; box.querySelector(".lib-actions .menu-plus").before(t);
           t.onclick = () => { VDX.reglages = !VDX.reglages; vdCompact(); }; }
  t.innerHTML = VDX.reglages ? "⚙ Masquer" : '<span class="ic">⚙</span><span class="l-long">Réglages et sélection</span><span class="l-court">Réglages</span>';
  const L = $("vidListe"), lignes = [...L.querySelectorAll(":scope > .vid-it")];
  lignes.forEach(li => {
    const i = +li.dataset.vd, e = es[i]; if (!e) return;
    li.classList.toggle("vd-plie", e.cle === "sansvoix" && !VDX.tout && !VDX.reglages);
    if (!li.querySelector("[data-vd-chap]")){
      const b = document.createElement("button"); b.className = "btn sm"; b.dataset.vdChap = i; b.title = "ouvrir ce chapitre"; b.textContent = "›";
      li.insertBefore(b, li.querySelector(".vi-etat"));
    }
  });
  const ns = n("sansvoix"); let pl = $("vdPlie");
  if (ns && !VDX.reglages){
    if (!pl){ pl = document.createElement("div"); pl.id = "vdPlie"; pl.className = "vd-plie-l"; }
    L.appendChild(pl);
    pl.innerHTML = "⛔ <span>" + ns + " chapitre" + (ns > 1 ? "s" : "") + " sans narration<small>narre-les d'abord (dans le chapitre)</small></span>"
      + '<button class="dpl-lien" data-vd-tout="1">' + (VDX.tout ? "masquer" : "voir ›") + "</button>";
  } else if (pl) pl.remove();
}
{ const _dc = dlgCharger; dlgCharger = async function(){ DLG.charge = true; try { return await _dc.apply(this, arguments); } finally { DLG.charge = false; } }; }
{ const _vr = vidRendre; vidRendre = function(){ _vr.apply(this, arguments); try { vdCompact(); } catch (err) { log("vidéos synthèse : " + err.message, "w"); } }; }
document.addEventListener("click", ev => {
  const c = ev.target.closest("#vidListe [data-vd-chap]");
  if (c){ ev.stopPropagation(); const x = VIDS.chapitres[+c.dataset.vdChap]; if (x) serVersChap(x.d, "vid"); return; }
  if (ev.target.closest("#vidListe [data-vd-tout]")){ ev.stopPropagation(); VDX.tout = !VDX.tout; vdCompact(); }
}, true);

/* ---- v3.0.0 (D) : 🎭 Dialogues de la serie en SYNTHESE (plages en pastilles, vers le chapitre, nouvelle plage) ---- */
function dlgsLigneC(x){
  const d = x.c.dir, dt = DLGS.det[d], doc = dt && dt.e && dt.e.doc, p = (dt && dt.p) || {};
  const a = '<button class="btn" data-dlgs2="chap" data-d="' + esc(d) + '" title="ouvrir ce chapitre (bloc 🎭)">›</button>';
  if (!doc) return '<div class="dpl"><div class="t">ch. ' + esc(x.c.chapter) + '</div><div class="a">' + a + '</div><div class="m">pas encore préparé</div></div>';
  const tot = x.c.pages || 0, ks = dplListeDe(dt.e, p, tot), vids = dlgVideos(doc, p);
  const jouer = Object.keys(vids).length ? "video" : p.deja ? "lire" : "";
  const pls = ks.map(k => { const f = dplInfoDe(dt.e, p, k, tot);
    return '<span class="dls-pl">' + dplTitre(k) + (f.afaire ? " 🟠" : f.faites ? " ✓" : "") + (f.v ? " 🎬" + (f.v.etat === "perimee" ? " à refaire" : f.v.v.duree ? " " + Math.round(f.v.v.duree) + " s" : "") : "") + "</span>"; }).join("");
  return '<div class="dpl"><div class="t">ch. ' + esc(x.c.chapter) + (dt.e.en_cours ? ' <span class="dpl-chip">⏳ en cours</span>' : "") + '</div><div class="a">'
    + (jouer ? '<button class="btn" data-dlgs="' + jouer + '" data-d="' + esc(d) + '" title="' + (jouer === "video" ? "voir la vidéo" : "lire les voix") + '">▶</button>' : "") + a
    + '</div><div class="m">' + pls + '<button class="dls-pl plus" data-dlgs2="plage" data-d="' + esc(d) + '">＋ plage</button></div></div>';
}
function dlgsCompact(){
  const avec = DLGS.chs.filter(x => DLGS.det[x.c.dir] && DLGS.det[x.c.dir].e && DLGS.det[x.c.dir].e.doc), sans = DLGS.chs.filter(x => !avec.includes(x));
  let h = avec.length ? '<div class="dpl-st">Chapitres avec dialogues</div>' + avec.map(dlgsLigneC).join("") : "";
  h += '<button class="btn sm dpl-plus" data-dlgs2="autre">＋ Dialogues d\'un autre chapitre…</button>';
  if (DLGS.autre) h += '<div class="dls-autre"><select id="dlsAutre">' + (sans.length ? sans : DLGS.chs).map(x => '<option value="' + esc(x.c.dir) + '">ch. ' + esc(x.c.chapter) + "</option>").join("")
    + '</select><button class="btn sm pri" data-dlgs2="autreGo">Ouvrir</button></div>';
  if (sans.length) h += '<div class="vd-plie-l">· <span>' + sans.length + " chapitre" + (sans.length > 1 ? "s" : "") + " sans dialogues</span>"
    + '<button class="dpl-lien" data-dlgs2="tous">' + (DLGS.filtre === "tous" ? "masquer" : "voir ›") + "</button></div>"
    + (DLGS.filtre === "tous" ? sans.map(dlgsLigneC).join("") : "");
  $("dlgsListe").innerHTML = h;
}
{ const _dr = dlgsRendre; dlgsRendre = function(){ _dr.apply(this, arguments); try { dlgsCompact(); } catch (err) { log("dialogues série synthèse : " + err.message, "w"); } }; }
document.addEventListener("click", ev => {
  const t = ev.target.closest("#dlgsBox [data-dlgs2]"); if (!t) return;
  ev.stopPropagation();
  const k = t.dataset.dlgs2, d = t.dataset.d;
  if (k === "chap") serVersChap(d, "dlg");
  else if (k === "plage") serVersChap(d, "dlg", true);
  else if (k === "autre"){ DLGS.autre = !DLGS.autre; dlgsCompact(); }
  else if (k === "autreGo"){ const v = $("dlsAutre").value; DLGS.autre = false; serVersChap(v, "dlg", true); }
  else if (k === "tous"){ DLGS.filtre = DLGS.filtre === "tous" ? "avec" : "tous"; dlgsCompact(); }
}, true);

"""
rep("/* ---- l'ecran de preparation : distribution du MANGA + repliques du chapitre ---- */",
    JS + "/* ---- l'ecran de preparation : distribution du MANGA + repliques du chapitre ---- */")

# dplListe / dplInfo generalises a n'importe quel chapitre (le bloc du chapitre ouvert appelle les memes)
rep("""function dplBornes(k){ if (k === "tout") return [1, CHAP_PAGES || 99999];""",
    """function dplBornes(k, tot){ if (k === "tout") return [1, (tot === undefined ? CHAP_PAGES : tot) || 99999];""")
rep("""function dplListe(){                            // les plages connues du chapitre ouvert, dans l'ordre des pages
  const e = DLG.e || {}, doc = e.doc; if (!doc) return [];
  const keys = [], tot = CHAP_PAGES || 0;""",
    """function dplListe(){ return dplListeDe(DLG.e, DLG.plan, CHAP_PAGES || 0); }   // v3.0.0 : le chapitre ouvert
function dplListeDe(e, plan, tot){               // les plages connues d'UN chapitre, dans l'ordre des pages
  e = e || {}; const doc = e.doc; if (!doc) return [];
  const keys = [];""")
rep("""  const bl = []; dlgPagesPreparees().filter(n => !couvert(n)).forEach(""",
    """  const pv = (doc.pages_vues && doc.pages_vues.length) ? doc.pages_vues : [...new Set((doc.repliques || []).map(x => x.page))].sort((a, b) => a - b);
  const bl = []; pv.filter(n => !couvert(n)).forEach(""")
rep("""  Object.keys(dlgVideos(doc, DLG.plan)).forEach(k => { if (!keys.includes(k)) keys.push(k); });""",
    """  Object.keys(dlgVideos(doc, plan)).forEach(k => { if (!keys.includes(k)) keys.push(k); });""")
rep("""function dplInfo(k){
  const e = DLG.e || {}, doc = e.doc || {}, et = (DLG.plan && DLG.plan.repliques) || {}, [a, b] = dplBornes(k);""",
    """function dplInfo(k){ return dplInfoDe(DLG.e, DLG.plan, k, CHAP_PAGES || 0); }
function dplInfoDe(e, plan, k, tot){
  e = e || {}; const doc = e.doc || {}, et = (plan && plan.repliques) || {}, [a, b] = dplBornes(k, tot);""")
rep("""  const vids = dlgVideos(doc, DLG.plan);
  return { reps: reps.length,""", """  const vids = dlgVideos(doc, plan);
  return { reps: reps.length,""")
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok v3.0.0")
