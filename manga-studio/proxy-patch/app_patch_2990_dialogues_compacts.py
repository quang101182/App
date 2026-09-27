# -*- coding: utf-8 -*-
"""v2.99.0 (27/09, maquette_dialogues_compact_v1 validee par Quang 15h34 : « c'est bon ») -- Dialogues plus compacts, dans
l'esprit du reste de l'app. SEULS le bloc 🎭 du chapitre et l'ecran ✏ changent (Quang 15h15 : « n'altère surtout pas le reste »).
A  : bloc 🎭 = liste « Dialogues de ce chapitre » (une carte par PLAGE de pages : doc.portees + pages preparees non couvertes +
     videos ; etat voix / video / repliques ; ▶ lit depuis la plage ; ⋯ voir / telecharger / corriger / refaire), sous la plage
     choisie ses etapes en UNE rangee ; « ＋ Nouvelle plage de pages » = petit formulaire ; options en interrupteurs.
     Les VRAIS boutons (#dlgPreparer, #dlgOuvrir, #dlgVoix, #dlgVid, #dlgArreter) et champs (#dlgDe, #dlgA) sont DEPLACES, pas
     recrees : leurs regles (actif / grise, lueur de l'etape suivante, credits) et leurs gestionnaires restent ceux d'avant.
A3 : « Oublier cette plage » NON fait (demande une route serveur : question posee a Quang).
B  : ecran ✏ = un personnage par LIGNE (couleur, nom, voix, expressivite, vitesse, ▶) ; toucher = ses reglages (la carte
     d'avant, intacte) depliee, un seul a la fois.
Suppose v2.98.1. Rejouable."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v2.99.0" in s[:900]:
    print("deja applique"); sys.exit(0)
if "v2.98.1" not in s[:1400]:
    print("ERREUR : appliquer d'abord app_patch_2981_camera_pages.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


rep("<title>Manga Studio v2.98.1</title>", "<title>Manga Studio v2.99.0</title>")
rep('<span class="ver" id="verBadge">v2.98.1</span>', '<span class="ver" id="verBadge">v2.99.0</span>')
rep('const VERSION = "2.98.1";', 'const VERSION = "2.99.0";   // v2.99.0 : Dialogues compacts -- plages de pages du chapitre, nouvelle plage, ecran ✏ en lignes')

CSS = r"""/* v2.99.0 : Dialogues compacts (maquette_dialogues_compact_v1) */
#dlgBox .dlg-portee,#dlgBox>.row,#dlgBox .dlg-vids,#dlgBox>p.muted{display:none}
#dlgBox.dpl-lot .dlg-portee{display:flex}#dlgBox.dpl-lot .dlg-portee .dlg-p:not([data-portee=lot]){display:none}
.dpl-st{font-size:11px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:var(--dim);margin:2px 0 6px}
.dpl{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:2px 8px;align-items:center;border:1px solid var(--line);border-radius:8px;padding:7px 8px;margin:0 0 6px;background:var(--panel);cursor:pointer}
.dpl.sel{border-color:#3fc7a8;box-shadow:inset 3px 0 0 #3fc7a8}
.dpl .t{font-weight:700;font-size:14px}.dpl .m{font-size:12px;color:var(--dim);grid-column:1;min-width:0}
.dpl .a{grid-row:1/3;grid-column:2;display:flex;gap:4px}.dpl .a .btn{width:34px;height:32px;padding:0;justify-content:center}
.dpl-chip{display:inline-block;font-size:11px;border-radius:9px;padding:0 7px;border:1px solid var(--line);margin:0 3px 2px 0;white-space:nowrap}
.dpl-chip.ok{color:var(--ok);border-color:#3fbf7f66}.dpl-chip.warn{color:var(--warn);border-color:#e0a63f66}
.dpl-etapes{display:flex;gap:3px;margin:0 0 8px;flex-wrap:wrap}.dpl-etapes>*{flex:1 1 auto;min-width:0;padding:7px 4px;font-size:12px;justify-content:center;text-align:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.dpl-etapes>[hidden],.dpl-menu [hidden]{display:none !important}
.dpl-nouv .dpl-etapes>*{white-space:normal;overflow:visible}
.dpl-etapes .dpl-fait{color:var(--ok);border:1px solid var(--line);border-radius:8px;display:flex;align-items:center}
.dpl-plus{width:100%;text-align:left;border-style:dashed !important;color:#3fc7a8;background:transparent !important;margin:0 0 6px}
.dpl-nouv{border:1px solid #3fc7a8;border-radius:8px;padding:8px;margin:0 0 6px;background:var(--panel)}
.dpl-nouv .lab{font-size:12px;color:var(--dim);margin:0 0 4px;display:flex;align-items:center}
.dpl-nouv .lab span{flex:1}.dpl-ch{display:flex;gap:6px;align-items:center;margin:0 0 8px}.dpl-ch input{width:70px}
.dpl-lien{font-size:12px;color:var(--accent2);background:none;border:0;padding:0;cursor:pointer}
.dpl-menu{border:1px solid var(--line);border-radius:8px;background:var(--panel);margin:-2px 0 8px}
.dpl-menu button{display:flex;gap:10px;width:100%;text-align:left;background:none;border:0;border-top:1px solid var(--line);color:var(--txt);padding:9px 10px;font:inherit;font-size:13px;cursor:pointer}
.dpl-menu button:first-child{border-top:0}.dpl-menu small{display:block;color:var(--dim);font-size:11.5px}
#dlgBox .dlg-opts{display:block;margin:2px 0 4px}
#dlgBox .dlg-opts label{display:flex;align-items:center;gap:10px;padding:7px 0;border-top:1px solid var(--line);min-height:40px}
#dlgBox .dlg-opts label>span{flex:1}#dlgBox .dlg-opts label[hidden]{display:none}
.dpl-aide{font-size:11.5px;color:var(--dim);margin:6px 0 0}
.dlgp-res{display:flex;align-items:center;gap:8px;cursor:pointer;min-height:36px}
.dlgp-res .nm{flex:1;min-width:0;font-weight:700}.dlgp-res .nm small{display:block;font-weight:400;color:var(--dim);font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.dlgp-res .btn{width:34px;height:32px;padding:0;justify-content:center;flex:none}
.dlgp-carte.ferme>:not(.dlgp-res){display:none}.dlgp-carte.ferme{padding:6px 10px;border-top-width:1px}
.dlgp-carte:not(.ferme) .dlgp-res{border-bottom:1px solid var(--line);padding-bottom:6px;margin-bottom:4px}
.dlgp-persos{gap:6px}.dlgp-carte:not(.ferme)>.n .dlg-pastille{display:none}
"""
rep("#dlgPrep{position:fixed;inset:0;", CSS + "#dlgPrep{position:fixed;inset:0;")

JS = r"""/* ---- v2.99.0 : Dialogues compacts (maquette_dialogues_compact_v1, validee 27/09) -- A : plages de pages du chapitre ---- */
const DPL = { nouv: false, menu: "" };
function dplBornes(k){ if (k === "tout") return [1, CHAP_PAGES || 99999]; const m = String(k).match(/^(\d+)(?:-(\d+))?$/); return m ? [+m[1], +(m[2] || m[1])] : [0, -1]; }
function dplListe(){                            // les plages connues du chapitre ouvert, dans l'ordre des pages
  const e = DLG.e || {}, doc = e.doc; if (!doc) return [];
  const keys = [], tot = CHAP_PAGES || 0;
  (doc.portees || []).forEach(k => { k = String(k || ""); if (/^\d+(-\d+)?$/.test(k) && !keys.includes(k)) keys.push(k); });
  const couvert = n => keys.some(k => { const [a, b] = dplBornes(k); return n >= a && n <= b; });
  const bl = []; dlgPagesPreparees().filter(n => !couvert(n)).forEach(n => { const l = bl[bl.length - 1]; if (l && n === l[1] + 1) l[1] = n; else bl.push([n, n]); });
  bl.forEach(([a, b]) => { const k = tot && a === 1 && b >= tot ? "tout" : a + "-" + b; if (!keys.includes(k)) keys.push(k); });
  Object.keys(dlgVideos(doc, DLG.plan)).forEach(k => { if (!keys.includes(k)) keys.push(k); });
  return keys.sort((u, v) => (u === "tout" ? -1 : v === "tout" ? 1 : dplBornes(u)[0] - dplBornes(v)[0]));
}
function dplInfo(k){
  const e = DLG.e || {}, doc = e.doc || {}, et = (DLG.plan && DLG.plan.repliques) || {}, [a, b] = dplBornes(k);
  const reps = (doc.repliques || []).filter(x => x.lire && x.page >= a && x.page <= b);
  const n = s => reps.filter(x => s.includes(et[x.cle])).length;
  const vids = dlgVideos(doc, DLG.plan);
  return { reps: reps.length, faites: n(["faite"]), afaire: n(["a_faire", "a_refaire", "sans_voix"]), trait: n(["a_traiter"]), v: vids[k] || null, a, b };
}
const dplTitre = k => k === "tout" ? "Chapitre entier" : (([a, b]) => a === b ? "p. " + a : "p. " + a + "-" + b)(dplBornes(k));
const dplCle = () => DLG.portee === "lot" ? "lot" : DLG.portee === "chap" ? "tout" : dlgPorteeTxt();
function dplChoisir(k){
  DPL.nouv = false; DPL.menu = "";
  if (k === "tout"){ DLG.portee = "chap"; $("dlgDe").value = ""; $("dlgA").value = ""; }
  else { const [a, b] = dplBornes(k); DLG.portee = "pages"; $("dlgDe").value = a; $("dlgA").value = b; }
  document.querySelectorAll("#dlgBox .dlg-p").forEach(y => y.classList.toggle("on", y.dataset.portee === DLG.portee));
  dlgRendre();
}
function dplInstaller(){
  if ($("dplListe")) return;
  const box = $("dlgBox"), t = box.querySelector(".bloc-titre");
  t.insertAdjacentHTML("afterend", '<div id="dplListe"></div>');
  box.insertAdjacentHTML("beforeend", '<p class="dpl-aide">ⓘ Préparer ≈ ' + fmtUsd(0.004) + ' / page · voix en crédits ElevenLabs, aucune avant « Voix » · quota épuisé = arrêt.</p>');
  ["dlgTons", "dlgNarr", "dlgEnch"].forEach(id => {                     // interrupteurs, texte a gauche
    const i = $(id), l = i.closest("label"); i.classList.add("bascule");
    const sp = document.createElement("span"); [...l.childNodes].filter(n => n !== i).forEach(n => sp.appendChild(n)); l.appendChild(sp); l.appendChild(i);
  });
  $("dlgNarr").closest("label").querySelector("span").innerHTML = 'Lire les encarts <small class="muted" style="display:block;font-size:11.5px">voix du narrateur</small>';
  // « ✓ Vidéo » deja a jour : toucher = la VOIR (la refaire passe par ⋯)
  $("dlgVid").addEventListener("click", ev => { if ($("dlgVid").dataset.dpl === "voir" && DLG.vcur){ ev.stopImmediatePropagation(); dlgVidMontrer(DLG.vcur); } }, true);
  box.addEventListener("click", ev => {
    const c = ev.target.closest("[data-dpl]"); if (!c || !box.contains(c)) return;
    const k = c.dataset.k, act = c.dataset.dpl;
    if (act === "carte"){ if (dplCle() !== k || DPL.nouv) dplChoisir(k); return; }
    ev.stopPropagation();
    if (act === "lire"){ if (dplCle() !== k) dplChoisir(k); dplLire(k); }
    else if (act === "menu"){ if (dplCle() !== k) dplChoisir(k); DPL.menu = DPL.menu === k ? "" : k; dplRendre(); }
    else if (act === "voir"){ const x = dplInfo(k); if (x.v) dlgVidMontrer(x.v.v); }
    else if (act === "dl"){ const x = dplInfo(k); if (x.v){ const a = document.createElement("a"); a.href = dlgVidUrl(x.v.v, true); document.body.appendChild(a); a.click(); a.remove(); } }
    else if (act === "corriger"){ DPL.menu = ""; dlgPrepOuvrir(); }
    else if (act === "refaire"){ DPL.menu = ""; dplRendre(); if (confirm("Refaire la préparation de " + dplTitre(k) + " ?\n\nL'IA relit ces pages (≈ " + fmtUsd(0.004 * (dplBornes(k)[1] - dplBornes(k)[0] + 1)) + ").")) dlgLancer("preparer"); }
    else if (act === "nouv"){
      const ks = dplListe(), fin = ks.filter(x => x !== "tout").reduce((m, x) => Math.max(m, dplBornes(x)[1]), 0), tot = CHAP_PAGES || 0;
      DPL.nouv = true; DPL.menu = ""; DLG.portee = "pages"; $("dlgDe").value = tot && fin >= tot ? 1 : Math.min(tot || fin + 1, fin + 1); $("dlgA").value = tot || "";
      document.querySelectorAll("#dlgBox .dlg-p").forEach(y => y.classList.toggle("on", y.dataset.portee === "pages"));
      dlgRendre(); setTimeout(() => $("dlgDe").focus(), 50);
    }
    else if (act === "annuler"){ const ks = dplListe(); DPL.nouv = false; if (ks.length) dplChoisir(ks[ks.length - 1]); else { DLG.portee = "chap"; dlgRendre(); } }
    else if (act === "chap" || act === "pages" || act === "lot"){
      DLG.portee = act; if (act === "pages" && !$("dlgDe").value) $("dlgDe").value = 1;
      document.querySelectorAll("#dlgBox .dlg-p").forEach(y => y.classList.toggle("on", y.dataset.portee === act));
      dlgRendre();
    }
  });
}
async function dplLire(k){                       // ▶ d'une plage : le lecteur des Dialogues, a la 1re replique de la plage
  dlgMarquerLu();
  await dlgLecteur();
  const [a] = dplBornes(k), i = DLL.liste.findIndex(x => x.page >= a);
  if (i > 0 && !dlgLec.hidden){ DLL.i = i; dllMontrer(); }
}
function dplRendre(){
  dplInstaller();
  const box = $("dlgBox"), L = $("dplListe"), e = DLG.e || {}, ks = dplListe(), cle = dplCle(), connue = ks.includes(cle) && !DPL.nouv;
  box.classList.toggle("dpl-lot", DLG.portee === "lot");
  let h = ks.length ? '<div class="dpl-st">Dialogues de ce chapitre</div>' : "";
  ks.forEach(k => {
    const x = dplInfo(k), sel = connue && k === cle;
    const ch = (x.afaire ? '<span class="dpl-chip warn">' + x.afaire + " voix à faire</span>" : x.faites ? '<span class="dpl-chip ok">✓ voix</span>' : "")
      + (x.trait ? '<span class="dpl-chip warn">⚠ ' + x.trait + " à traiter</span>" : "")
      + (x.v ? '<span class="dpl-chip ' + (x.v.etat === "perimee" ? "warn" : "ok") + '">🎬 ' + (x.v.etat === "perimee" ? "à refaire" : x.v.v.duree ? Math.round(x.v.v.duree) + " s" : "prête") + "</span>" : "");
    h += '<div class="dpl' + (sel ? " sel" : "") + '" data-dpl="carte" data-k="' + esc(k) + '"><div class="t">' + dplTitre(k) + '</div><div class="a">'
      + '<button class="btn" data-dpl="lire" data-k="' + esc(k) + '" title="lire les dialogues de ' + esc(dplTitre(k)) + '"' + (x.reps ? "" : " disabled") + ">▶</button>"
      + '<button class="btn" data-dpl="menu" data-k="' + esc(k) + '" title="plus">⋯</button></div>'
      + '<div class="m">' + ch + x.reps + " réplique" + (x.reps > 1 ? "s" : "") + "</div></div>";
    if (sel) h += '<div id="dplEtapesIci"></div>';
    if (DPL.menu === k) h += '<div class="dpl-menu">'
      + (x.v ? '<button data-dpl="voir" data-k="' + esc(k) + '">▶ <span>Voir la vidéo</span></button><button data-dpl="dl" data-k="' + esc(k) + '">⬇ <span>Télécharger la vidéo</span></button>' : "")
      + '<button data-dpl="corriger" data-k="' + esc(k) + '">✏ <span>Corriger qui parle, voix, vitesses</span></button>'
      + '<button data-dpl="refaire" data-k="' + esc(k) + '">↻ <span>Refaire la préparation<small>l\'IA relit ces pages</small></span></button></div>';
  });
  if (!connue){
    const lot = DLG.portee === "lot", chap = DLG.portee === "chap";
    h += '<div class="dpl-nouv"><div class="lab"><span>' + (lot ? "Plusieurs chapitres" : ks.length ? "Nouvelle plage — " + (chap ? "chapitre entier" : "pages") : chap ? "Tout le chapitre" : "Pages")
      + "</span>" + (ks.length ? '<button class="btn sm" data-dpl="annuler" title="annuler">✕</button>' : "") + "</div>"
      + (lot || chap ? "" : '<div class="dpl-ch" id="dplChamps"></div>') + '<div id="dplEtapesIci"></div>'
      + '<div>' + [chap ? "" : '<button class="dpl-lien" data-dpl="chap">chapitre entier</button>', DLG.portee === "pages" ? "" : '<button class="dpl-lien" data-dpl="pages">des pages…</button>',
                   lot ? "" : '<button class="dpl-lien" data-dpl="lot">plusieurs chapitres…</button>'].filter(Boolean).join(" · ") + "</div></div>";
  } else h += '<button class="btn sm dpl-plus" data-dpl="nouv">＋ Nouvelle plage de pages</button>';
  // AVANT de redessiner : mettre a l'abri les VRAIS boutons et champs (sinon innerHTML les detruit)
  const abri = box.querySelector('.dlg-p[data-portee="pages"]');
  if ($("dplEtapes") && L.contains($("dplEtapes"))) box.appendChild($("dplEtapes"));
  if (L.contains($("dlgDe"))){ abri.textContent = "Des pages : de "; abri.append($("dlgDe"), " à ", $("dlgA")); }
  L.innerHTML = h;
  // les VRAIS boutons et champs, deplaces (gestionnaires et regles d'avant intacts)
  const ici = $("dplEtapesIci");
  let et = $("dplEtapes"); if (!et){ et = document.createElement("div"); et.id = "dplEtapes"; et.className = "dpl-etapes"; }
  ici.replaceWith(et);
  if ($("dplChamps")) $("dplChamps").append($("dlgDe"), " à ", $("dlgA"));
  $("dlgA").placeholder = CHAP_PAGES ? String(CHAP_PAGES) : "";
  const x = connue ? dplInfo(cle) : null, prep = !!(x && x.reps);
  let fait = $("dplPrepFait"); if (!fait){ fait = document.createElement("span"); fait.id = "dplPrepFait"; fait.className = "dpl-fait"; fait.textContent = "✓ Préparé"; }
  et.append(fait, $("dlgPreparer"), $("dlgOuvrir"), $("dlgVoix"), $("dlgVid"), $("dlgArreter"));
  fait.hidden = !prep; $("dlgPreparer").hidden = prep;
  $("dlgOuvrir").hidden = $("dlgVid").hidden = !connue || DLG.portee === "lot"; $("dlgVoix").hidden = !connue && DLG.portee !== "lot";
  if (connue){
    const p = DLG.plan || {};
    $("dlgOuvrir").textContent = "✏ Régler";
    $("dlgVoix").textContent = p.a_faire ? "🔊 Voix (" + p.a_faire + ")" : x.faites ? "✓ Voix" : "🔊 Voix";
    const vv = x.v && x.v.etat !== "perimee";
    $("dlgVid").textContent = vv ? "✓ Vidéo" : x.v ? "🎬 Mettre à jour" : "🎬 Vidéo";
    $("dlgVid").dataset.dpl = vv ? "voir" : "";
    $("dlgVid").classList.toggle("dpl-fait", !!vv);
  } else if (!$("dlgPreparer").hidden && DLG.portee !== "lot"){
    const n = dlgNbPages(), manq = dlgManquantes().length;
    $("dlgPreparer").textContent = (manq ? "🌐 Traduire puis préparer" : "🎭 Préparer") + (DLG.portee === "pages" ? " " + dplTitre(dlgPorteeTxt()) : "")
      + " · ≈ " + fmtUsd(0.004 * n + (manq ? dlgTarifTrad() * manq : 0));
  }
  $("dlgPreparer").classList.toggle("pri", !prep);
  if (typeof dlgLueur === "function") dlgLueur();
}
{ const _rendre = dlgRendre; dlgRendre = function(){ _rendre.apply(this, arguments); try { dplRendre(); } catch (err) { log("dialogues compacts : " + err.message, "w"); } }; }
{ const _porteeDe = dlgPorteeDe; dlgPorteeDe = function(){ DPL.nouv = false; DPL.menu = ""; return _porteeDe.apply(this, arguments); }; }

/* ---- v2.99.0 : B -- ecran ✏ : un personnage par LIGNE, reglages depliés un seul a la fois ---- */
DLG.ppOuv = null;
function dppCompact(){
  const persos = dlgPersos(), fr = (DLG.voix || []).some(v => v.fr);
  document.querySelectorAll("#dlgpCorps .dlgp-carte").forEach(c => {
    const i = +c.dataset.p, p = persos[i]; if (!p || c.querySelector(".dlgp-res")) return;
    const nom = p.narrateur ? "Narrateur" : p.nom, coul = p.couleur || "#8b93a7", v = (DLG.voix || []).find(x => x.id === p.voix_el);
    const vt = p.voix_el ? (fr ? (v && v.fr ? "🇫🇷 " : "🇬🇧 ") : "") + (v ? v.nom : p.voix_el) + " · " + DLG_EXPR[p.expressivite ?? 1] + " · " + Number(p.vitesse || 1.1).toFixed(2).replace(".", ",") + "×" : "⚠ voix à choisir";
    c.insertAdjacentHTML("afterbegin", '<div class="dlgp-res" data-pp="1"><span class="dlg-pastille" style="background:' + esc(coul) + '"></span><div class="nm">' + esc(nom)
      + "<small>" + esc(vt) + '</small></div><button class="btn sm" data-pp-ecoute="1" title="écouter sa voix">▶</button><button class="btn sm" data-pp-tog="1" title="réglages">▾</button></div>');
    c.dataset.nom = nom;
  });
  dppAppliquer();
}
function dppAppliquer(){
  document.querySelectorAll("#dlgpCorps .dlgp-carte").forEach(c => {
    const ouv = DLG.ppOuv === c.dataset.nom; c.classList.toggle("ferme", !ouv);
    const t = c.querySelector("[data-pp-tog]"); if (t) t.textContent = ouv ? "▴" : "▾";
  });
}
document.addEventListener("click", ev => {
  const r = ev.target.closest("#dlgpCorps .dlgp-res"); if (!r) return;
  const c = r.closest(".dlgp-carte");
  if (ev.target.closest("[data-pp-ecoute]")){ const b = c.querySelector("[data-ecoute-p]"); if (b) b.click(); return; }
  DLG.ppOuv = DLG.ppOuv === c.dataset.nom ? null : c.dataset.nom; dppAppliquer();
});
{ const _prep = dlgPrepRendre; dlgPrepRendre = function(){ const r = _prep.apply(this, arguments); try { dppCompact(); } catch (err) { log("✏ compact : " + err.message, "w"); } return r; }; }

"""
rep("/* ---- l'ecran de preparation : distribution du MANGA + repliques du chapitre ---- */",
    JS + "/* ---- l'ecran de preparation : distribution du MANGA + repliques du chapitre ---- */")
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok v2.99.0")
