# -*- coding: utf-8 -*-
"""v3.1.0 (27/09, maquette_verif_bulles_v1 validee par Quang 17h17 : « ok c bon ») -- 🔍 VERIFIER LES BULLES avant de
preparer (mode Dialogues). Ecran calque sur le lecteur des Dialogues (← Fermer, gros boutons ronds en bas). Pastilles
numerotees AUTOMATIQUEMENT page par page ; trois gestes sans mode : toucher = exclure / reinclure, glisser une pastille sur
une autre = ordre (renumerotation seule), entourer au doigt = ajouter (rectangle englobant) ; glisser la page = page
suivante / precedente ; ↶ = annuler. « ⚠ seulement les pages a regarder » : pages ou deux tris sont en desaccord.
Pages pas encore traduites : detection SEULE (gratuite, dialogues.py 1.19.0). « ✓ Valider » enregistre (patch_dialogues_12) ;
nouvelle plage = « ✓ Valider et preparer ». Entrees : etape « 🔍 Bulles » du bloc 🎭 (verte si toute la plage est
verifiee) et « 🔍 Verifier les bulles · gratuit » du formulaire « Nouvelle plage ». Le lecteur suit l'ordre verifie.
Suppose v3.0.0. Rejouable."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v3.1.0" in s[:900]:
    print("deja applique"); sys.exit(0)
if "v3.0.0" not in s[:1400]:
    print("ERREUR : appliquer d'abord app_patch_3000_series_synthese.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:80], s.count(a))
    s = s.replace(a, b)


rep("<title>Manga Studio v3.0.0</title>", "<title>Manga Studio v3.1.0</title>")
rep('<span class="ver" id="verBadge">v3.0.0</span>', '<span class="ver" id="verBadge">v3.1.0</span>')
rep('const VERSION = "3.0.0";', 'const VERSION = "3.1.0";   // v3.1.0 : 🔍 verifier les bulles avant de preparer (Dialogues) -- numerotation, exclure, ordre, entourer')

CSS = r"""/* v3.1.0 : 🔍 verification des bulles (maquette_verif_bulles_v1) */
#dlvBox{position:fixed;inset:0;z-index:86;background:var(--bg);display:flex;flex-direction:column}#dlvBox[hidden]{display:none}
.dlv-haut{display:flex;align-items:center;gap:8px;padding:10px 12px;max-width:900px;width:100%;margin:0 auto;box-sizing:border-box}
.dlv-haut b{flex:1;min-width:0;font-size:15px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.dlv-haut small{color:var(--dim);font-weight:400}
.dlv-aide{margin:0 auto 6px;max-width:880px;width:calc(100% - 20px);font-size:12.5px;color:#cfe;background:#10261f;border:1px solid #2d7f6c;border-radius:10px;padding:6px 10px;display:flex;gap:8px;align-items:center;box-sizing:border-box}
.dlv-aide span{flex:1}.dlv-aide[hidden]{display:none}
.dlv-scene{flex:1;min-height:0;display:flex;align-items:center;justify-content:center;padding:0 8px;position:relative}
.dlv-cadre{position:relative;touch-action:none;user-select:none;-webkit-user-select:none}
.dlv-cadre img{display:block;width:100%;height:100%;pointer-events:none}
.dlv-cadre svg{position:absolute;inset:0;width:100%;height:100%;overflow:visible}
.dlv-attente{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:var(--dim);font-size:14px;text-align:center;padding:20px}
.dlv-attente[hidden]{display:none}
.dlv-incert{max-width:880px;width:calc(100% - 20px);margin:6px auto 0;font-size:12.5px;color:var(--warn);display:flex;gap:8px;align-items:center;box-sizing:border-box}
.dlv-incert span{flex:1}.dlv-incert[hidden]{display:none}
.dlv-bas{display:flex;align-items:center;gap:10px;padding:10px 14px max(14px, env(safe-area-inset-bottom));background:#0c0e13;border-top:1px solid var(--line);margin-top:6px}
.dlv-bas>*{flex:none}.dlv-in{display:flex;gap:10px;align-items:center;max-width:880px;width:100%;margin:0 auto}
.dlv-rond{width:52px;height:52px;border-radius:50%;background:#1b2130;border:1px solid var(--line);color:var(--txt);font-size:18px;display:grid;place-items:center;cursor:pointer;flex:none}
.dlv-rond:disabled{opacity:.32;cursor:default}
.dlv-go{flex:1;min-width:0;height:52px;border-radius:99px;background:#3fc7a8;color:#062a22;font-weight:800;border:0;font-size:15px;cursor:pointer;line-height:1.15}
.dlv-go small{display:block;font-weight:600;font-size:11.5px;opacity:.8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.dlv-go:disabled{opacity:.5}
.dlv-toast{position:absolute;left:50%;transform:translateX(-50%);bottom:92px;background:#1f2533f0;border:1px solid var(--line);border-radius:99px;padding:7px 14px;font-size:13px;white-space:nowrap;z-index:2;pointer-events:none}
.dlv-toast[hidden]{display:none}
.dpl-sansverif{background:none !important;border:0 !important;color:var(--accent2) !important;font-size:12px !important;padding:2px 0 !important;flex:0 0 100% !important;text-align:left !important;justify-content:flex-start !important;font-weight:400 !important}
#dplVerif{flex:1 1 100%}
"""
rep("#dlgPrep{position:fixed;inset:0;", CSS + "#dlgPrep{position:fixed;inset:0;")

# le lecteur suit l'ordre verifie (dialogues.py 1.19.0 ecrit « ordre » ; sinon le n° de detection, comme avant)
rep("""  liste.sort((a, b) => a.page - b.page || (a.id || 0) - (b.id || 0));""",
    """  const rg = x => x.vide ? -1 : (x.ordre ?? x.id ?? 0);                   // v3.1.0 (R30) : l'ordre verifie par Quang
  liste.sort((a, b) => a.page - b.page || rg(a) - rg(b));""")

JS = r"""/* ---- v3.1.0 (R30) : 🔍 VERIFIER LES BULLES avant de preparer ---- */
const DLV = { d: "", pages: [], i: 0, undo: [], seul: false, incert: new Set(), nouv: false, portee: "", aide: true };
try { DLV.aide = localStorage.getItem("manga_dlv_aide") !== "0"; } catch (e) {}
(() => {
  const b = document.createElement("div"); b.id = "dlvBox"; b.hidden = true;
  b.innerHTML = '<div class="dlv-haut"><button class="btn sm retour" id="dlvFermer">← Fermer</button><b id="dlvTitre">🔍</b>'
    + '<button class="btn sm" id="dlvAnnuler" title="annuler le dernier geste">↶</button></div>'
    + '<div class="dlv-aide" id="dlvAide">✋ <span><b>Toucher</b> = exclure · <b>glisser</b> = ordre · <b>entourer</b> = ajouter</span><button class="dpl-lien" id="dlvAideOk">OK</button></div>'
    + '<div class="dlv-scene" id="dlvScene"><div class="dlv-cadre" id="dlvCadre"><img id="dlvImg" alt=""><svg id="dlvSvg"></svg></div>'
    + '<div class="dlv-attente" id="dlvAttente" hidden></div><div class="dlv-toast" id="dlvToast" hidden></div></div>'
    + '<div class="dlv-incert" id="dlvIncert" hidden></div>'
    + '<div class="dlv-bas"><div class="dlv-in"><button class="dlv-rond" id="dlvPrec" title="page précédente">⏮</button>'
    + '<button class="dlv-go" id="dlvGo"></button><button class="dlv-rond" id="dlvSuiv" title="page suivante">⏭</button></div></div>';
  document.body.appendChild(b);
})();
const dlvIou = (a, b) => { const x1 = Math.max(a.x, b.x), y1 = Math.max(a.y, b.y), x2 = Math.min(a.x + a.w, b.x + b.w), y2 = Math.min(a.y + a.h, b.y + b.h);
  const i = Math.max(0, x2 - x1) * Math.max(0, y2 - y1), u = a.w * a.h + b.w * b.h - i; return u > 0 ? i / u : 0; };
function dlvItems(p){                             // bulles de la page + verification deja enregistree -> [{id, box, ajout, exclu}]
  const bl = p.bulles.map(b => ({ id: b.id, box: b.box, texte: b.texte || "" })), v = p.verif;
  if (!v) return bl;
  const pris = new Set(), trouve = r => { let best = null, bi = 0; bl.forEach(b => { if (pris.has(b)) return; const x = dlvIou(r.box, b.box); if (x > bi){ bi = x; best = b; } }); return bi >= 0.5 ? best : null; };
  const out = [];
  (v.ordre || []).forEach(r => { const aj = (v.ajouts || []).find(z => z.id === r.id && dlvIou(z.box, r.box) >= 0.5);
    if (aj) out.push({ id: aj.id, box: aj.box, ajout: true }); else { const b = trouve(r); if (b){ pris.add(b); out.push(b); } } });
  (v.exclues || []).forEach(r => { const b = trouve(r); if (b){ pris.add(b); out.push(Object.assign(b, { exclu: true })); } });
  bl.forEach(b => { if (!pris.has(b)) out.push(b); });
  (v.ajouts || []).forEach(z => { if (!out.some(o => o.ajout && o.id === z.id)) out.push({ id: z.id, box: z.box, ajout: true }); });
  return out;
}
function dlvOrdreCases(items, pg){               // meme tri « case par case » que scripts/mesure_ordre_cases.py
  const W = pg.W, H = pg.H, rs = [];
  [...pg.cases].sort((a, b) => a[1] - b[1]).forEach(c => {
    const h = c[3] - c[1], r = rs.find(r => Math.min(r.y2, c[3]) - Math.max(r.y1, c[1]) > 0.5 * Math.min(h, r.y2 - r.y1));
    if (r){ r.cs.push(c); r.y1 = Math.min(r.y1, c[1]); r.y2 = Math.max(r.y2, c[3]); } else rs.push({ y1: c[1], y2: c[3], cs: [c] });
  });
  const oc = rs.sort((a, b) => a.y1 - b.y1).flatMap(r => r.cs.sort((a, b) => b[2] - a[2]));
  const cas = b => { const cx = (b.box.x + b.box.w / 2) * W, cy = (b.box.y + b.box.h / 2) * H; let bi = 999, dm = Infinity;
    oc.forEach((c, i) => { const d = Math.max(c[0] - cx, 0, cx - c[2]) ** 2 + Math.max(c[1] - cy, 0, cy - c[3]) ** 2; if (d < dm){ dm = d; bi = i; } }); return bi; };
  return [...items].sort((a, b) => cas(a) - cas(b) || Math.round(a.box.y / 0.06) - Math.round(b.box.y / 0.06) || (b.box.x + b.box.w) - (a.box.x + a.box.w)).map(b => b.id);
}
async function dlvOuvrir(portee){
  const d = CHAP_OPEN; if (!d) return;
  Object.assign(DLV, { d, pages: [], i: 0, undo: [], seul: false, incert: new Set(), portee, nouv: !dplListe().includes(portee === "1-" + CHAP_PAGES ? "tout" : portee) || DPL.nouv });
  $("dlvBox").hidden = false; document.body.style.overflow = "hidden";
  $("dlvAide").hidden = !DLV.aide;
  dlvAttente("chargement des bulles…");
  let j = await api("/manga/dialogues_bulles?d=" + encodeURIComponent(d) + "&pages=" + encodeURIComponent(portee)).catch(e => ({ error: e.message }));
  if (j.error) return dlvAttente("⚠ " + j.error);
  if (j.pages.some(p => !p.source)){                                         // pages pas encore traduites : detection seule, gratuite
    dlvAttente("🔍 détection des bulles… (gratuit, sur le PC)");
    const r = await api("/manga/dialogues_lancer", { d, action: "detecter", pages: portee }).catch(e => ({ error: e.message }));
    if (r.error && !/déjà en cours/.test(r.error)) return dlvAttente("⚠ détection : " + r.error);
    for (let k = 0; k < 90; k++){
      await new Promise(x => setTimeout(x, 1500)); if ($("dlvBox").hidden || DLV.d !== d) return;
      j = await api("/manga/dialogues_bulles?d=" + encodeURIComponent(d) + "&pages=" + encodeURIComponent(portee)).catch(() => j);
      if (!j.en_cours && !j.pages.some(p => !p.source)) break;
    }
  }
  DLV.pages = j.pages.map(p => Object.assign(p, { items: dlvItems(p), modif: 0 }));
  try {                                                                      // pages « a regarder » : deux tris en desaccord
    const cs = await api("/manga/cases?d=" + encodeURIComponent(d)), fich = (DLG.e && DLG.e.fichiers) || [];
    if (cs && cs.pages) DLV.pages.forEach(p => { const pg = cs.pages[fich[p.page - 1]]; const it = p.items.filter(x => !x.ajout);
      if (pg && pg.cases && pg.cases.length && pg.W && it.length >= 2 && dlvOrdreCases(it, pg).join() !== [...it].sort((a, b) => a.id - b.id).map(x => x.id).join()) DLV.incert.add(p.page); });
  } catch (e) {}
  dlvAttente("");
  dlvAller(0);
}
function dlvAttente(t){ $("dlvAttente").hidden = !t; $("dlvAttente").textContent = t || ""; $("dlvCadre").style.visibility = t ? "hidden" : ""; if (t){ $("dlvGo").disabled = true; $("dlvIncert").hidden = true; } }
const dlvListe = () => DLV.seul ? DLV.pages.filter(p => DLV.incert.has(p.page)) : DLV.pages;
function dlvAller(i){
  const L = dlvListe(); if (!L.length) return;
  DLV.i = Math.max(0, Math.min(L.length - 1, i));
  const p = L[DLV.i], c = CHAPS.find(y => y.dir === DLV.d);
  $("dlvTitre").innerHTML = "🔍 ch. " + esc(c ? c.chapter : "?") + " <small>p. " + p.page + " · " + (DLV.i + 1) + "/" + L.length + (DLV.seul ? " à regarder" : "") + "</small>";
  const img = $("dlvImg");
  img.onload = () => { dlvTaille(); dlvDessiner(); };
  img.src = srcURL(DLV.d + "/" + p.img);
  if (img.complete && img.naturalWidth){ dlvTaille(); dlvDessiner(); }
  dlvBas();
}
function dlvTaille(){
  const img = $("dlvImg"), sc = $("dlvScene"), r = (img.naturalWidth || 3) / (img.naturalHeight || 4), W = sc.clientWidth - 16, H = sc.clientHeight - 8;
  let w = W, h = W / r; if (h > H){ h = H; w = H * r; }
  $("dlvCadre").style.width = Math.max(10, w) + "px"; $("dlvCadre").style.height = Math.max(10, h) + "px";
}
window.addEventListener("resize", () => { if (!$("dlvBox").hidden){ dlvTaille(); dlvDessiner(); } });
function dlvPage(){ return dlvListe()[DLV.i]; }
function dlvDessiner(extra){
  const p = dlvPage(); if (!p) return;
  const img = $("dlvImg"), W = img.naturalWidth || 1000, H = img.naturalHeight || 1400, R = Math.max(W, H) * 0.021, svg = $("dlvSvg");
  svg.setAttribute("viewBox", "0 0 " + W + " " + H);
  let n = 0, h = "";
  if (!p.items.length) h += '<text x="' + W / 2 + '" y="' + H / 2 + '" text-anchor="middle" font-size="' + R * 1.2 + '" fill="#e8a84a" stroke="#000" stroke-width="' + R * 0.12 + '" paint-order="stroke">aucune bulle détectée — entoure-en une si besoin</text>';
  p.items.forEach((x, k) => {
    const cx = (x.box.x + x.box.w) * W - R * 0.4, cy = x.box.y * H + R * 0.4, num = x.exclu ? "✕" : String(++n);
    if (x.ajout) h += '<rect x="' + x.box.x * W + '" y="' + x.box.y * H + '" width="' + x.box.w * W + '" height="' + x.box.h * H + '" fill="none" stroke="#3fc7a8" stroke-width="' + R * 0.15 + '" stroke-dasharray="' + R * 0.5 + " " + R * 0.35 + '"/>';
    h += '<g data-dlv-k="' + k + '" style="cursor:grab"><circle cx="' + cx + '" cy="' + cy + '" r="' + R + '" fill="' + (x.exclu ? "#5a6070" : x.ajout ? "#e8c35a" : "#3fc7a8") + '" stroke="#062a22" stroke-width="' + R * 0.14 + '"/>'
      + '<text x="' + cx + '" y="' + (cy + R * 0.36) + '" text-anchor="middle" font-size="' + R * (num.length > 1 ? 0.92 : 1.05) + '" font-weight="800" font-family="system-ui,sans-serif" fill="' + (x.exclu ? "#ddd" : "#062a22") + '">' + num + "</text></g>";
  });
  svg.innerHTML = h + (extra || "");
  svg.dataset.r = R;
}
function dlvBas(){
  const L = dlvListe(), p = dlvPage(), der = DLV.i >= L.length - 1, ajouts = DLV.pages.reduce((s, q) => s + q.items.filter(x => x.ajout).length, 0);
  const modifs = DLV.pages.reduce((s, q) => s + q.modif, 0), actifs = p ? p.items.filter(x => !x.exclu).length : 0;
  $("dlvPrec").disabled = DLV.i <= 0; $("dlvSuiv").disabled = der; $("dlvGo").disabled = false;
  const nb = DLV.pages.length, cout = fmtUsd(0.004 * nb);
  $("dlvGo").innerHTML = der ? (DLV.nouv ? "✓ Valider et préparer<small>p. " + esc(DLV.portee) + (ajouts ? " · " + ajouts + " ajoutée" + (ajouts > 1 ? "s" : "") : "") + " · ≈ " + cout + "</small>"
                                         : "✓ Valider<small>" + (modifs ? modifs + " changement" + (modifs > 1 ? "s" : "") + " · gardé pour la prochaine préparation" : "rien à changer") + "</small>")
    : "Page suivante ›<small>" + actifs + " bulle" + (actifs > 1 ? "s" : "") + (p && p.modif ? " · " + p.modif + " modifiée" + (p.modif > 1 ? "s" : "") : "") + "</small>";
  const ni = DLV.incert.size;
  $("dlvIncert").hidden = !ni || nb < 2;
  $("dlvIncert").innerHTML = "⚠ <span>ordre incertain sur " + ni + " page" + (ni > 1 ? "s" : "") + " sur " + nb + "</span>"
    + '<button class="dpl-lien" id="dlvSeul">' + (DLV.seul ? "toutes les pages" : "seulement celles-là ›") + "</button>";
}
function dlvToast(t){ const e = $("dlvToast"); e.textContent = t; e.hidden = false; clearTimeout(DLV.tt); DLV.tt = setTimeout(() => { e.hidden = true; }, 2200); }
function dlvSnap(){ const p = dlvPage(); DLV.undo.push({ page: p.page, items: JSON.stringify(p.items), modif: p.modif }); if (DLV.undo.length > 60) DLV.undo.shift(); }
$("dlvAnnuler").onclick = () => {
  const u = DLV.undo.pop(); if (!u) return dlvToast("rien à annuler");
  const p = DLV.pages.find(q => q.page === u.page); p.items = JSON.parse(u.items); p.modif = u.modif;
  const L = dlvListe(), i = L.indexOf(p); if (i >= 0 && i !== DLV.i) dlvAller(i); else { dlvDessiner(); dlvBas(); }
  dlvToast("↶ annulé");
};
$("dlvAideOk").onclick = () => { DLV.aide = false; $("dlvAide").hidden = true; try { localStorage.setItem("manga_dlv_aide", "0"); } catch (e) {} setTimeout(() => { dlvTaille(); dlvDessiner(); }, 30); };
$("dlvFermer").onclick = () => {
  if (DLV.pages.some(q => q.modif) && !confirm("Fermer sans enregistrer tes changements ?")) return;
  $("dlvBox").hidden = true; document.body.style.overflow = "";
};
$("dlvPrec").onclick = () => dlvAller(DLV.i - 1);
$("dlvSuiv").onclick = () => dlvAller(DLV.i + 1);
$("dlvBox").addEventListener("click", e => { if (e.target.closest("#dlvSeul")){ DLV.seul = !DLV.seul; dlvAller(0); } });
$("dlvGo").onclick = async () => {
  const L = dlvListe();
  if (DLV.i < L.length - 1) return dlvAller(DLV.i + 1);
  const pages = {};
  DLV.pages.forEach(p => { pages[p.page] = { ordre: p.items.filter(x => !x.exclu).map(x => ({ id: x.id, box: x.box })),
                                             exclues: p.items.filter(x => x.exclu && !x.ajout).map(x => ({ id: x.id, box: x.box })),
                                             ajouts: p.items.filter(x => x.ajout && !x.exclu).map(x => ({ id: x.id, box: x.box })) }; });
  $("dlvGo").disabled = true;
  try { const r = await api("/manga/dialogues_verif", { d: DLV.d, pages }); if (r.error) throw new Error(r.error); }
  catch (err) { $("dlvGo").disabled = false; return dlvToast("⚠ non enregistré : " + err.message); }
  $("dlvBox").hidden = true; document.body.style.overflow = "";
  if (DLG.e) DLG.e.verif_pages = [...new Set([...(DLG.e.verif_pages || []), ...DLV.pages.map(p => p.page)])];
  if (DLV.nouv){ toast("🔍 bulles vérifiées — préparation lancée"); dlgLancer("preparer"); }
  else { toast("🔍 bulles vérifiées et gardées" + (DLV.pages.some(p => p.modif) ? " — ⋯ › Refaire la préparation pour les appliquer" : "")); dlgRendre(); }
};
/* gestes : toucher / glisser une pastille, entourer, glisser la page */
(() => {
  const cad = $("dlvCadre"); let g = null;
  const frac = e => { const r = cad.getBoundingClientRect(); return { x: (e.clientX - r.left) / r.width, y: (e.clientY - r.top) / r.height, px: e.clientX, py: e.clientY }; };
  cad.addEventListener("pointerdown", e => {
    const k = e.target.closest("[data-dlv-k]"); cad.setPointerCapture(e.pointerId);
    g = { k: k ? +k.dataset.dlvK : -1, pts: [frac(e)], t: Date.now() };
  });
  cad.addEventListener("pointermove", e => {
    if (!g) return; const f = frac(e); g.pts.push(f);
    const img = $("dlvImg"), W = img.naturalWidth || 1000, H = img.naturalHeight || 1400, R = +$("dlvSvg").dataset.r || 20;
    if (g.k >= 0){ const d0 = g.pts[0], mv = Math.hypot(f.px - d0.px, f.py - d0.py); if (mv > 8){ g.drag = true;
        dlvDessiner('<circle cx="' + f.x * W + '" cy="' + f.y * H + '" r="' + R * 1.15 + '" fill="#e8c35a" stroke="#3a2a00" stroke-width="' + R * 0.14 + '" opacity=".9"/>'); } }
    else if (g.pts.length > 2) dlvDessiner('<polyline points="' + g.pts.map(q => q.x * W + "," + q.y * H).join(" ") + '" fill="none" stroke="#e8c35a" stroke-width="' + R * 0.2 + '" stroke-linecap="round" stroke-linejoin="round"/>');
  });
  const fin = e => {
    if (!g) return; const x = g; g = null; const p = dlvPage(); if (!p) return;
    const f = x.pts[x.pts.length - 1], d0 = x.pts[0], cad2 = cad.getBoundingClientRect();
    if (x.k >= 0 && !x.drag){ dlvSnap(); const it = p.items[x.k]; it.exclu = !it.exclu; p.modif++; dlvDessiner(); dlvBas();
      return dlvToast(it.exclu ? "✕ exclue · touche-la pour la remettre" : "✓ remise"); }
    if (x.k >= 0 && x.drag){
      const img = $("dlvImg"), R = (+$("dlvSvg").dataset.r || 20) / (img.naturalWidth || 1000);
      let cible = -1, dm = Infinity;
      p.items.forEach((it, k) => { if (k === x.k) return; const cx = it.box.x + it.box.w - R * 0.4, cy = (it.box.y * (img.naturalHeight || 1400) / (img.naturalWidth || 1000)) + R * 0.4;
        const d = Math.hypot(cx - f.x, cy - f.y * (img.naturalHeight || 1400) / (img.naturalWidth || 1000)); if (d < dm){ dm = d; cible = k; } });
      if (cible < 0 || dm > R * 3){ dlvDessiner(); return; }
      dlvSnap(); const [it] = p.items.splice(x.k, 1); const c2 = cible > x.k ? cible - 1 : cible; p.items.splice(c2, 0, it); p.modif++;
      dlvDessiner(); dlvBas(); return dlvToast("↕ ordre changé");
    }
    const xs = x.pts.map(q => q.x), ys = x.pts.map(q => q.y), bx = { x: Math.min(...xs), y: Math.min(...ys), w: Math.max(...xs) - Math.min(...xs), h: Math.max(...ys) - Math.min(...ys) };
    const dxp = f.px - d0.px, dyp = f.py - d0.py, ferme = Math.hypot(f.px - d0.px, f.py - d0.py) < 0.45 * Math.max(bx.w * cad2.width, bx.h * cad2.height);
    if (Math.abs(dxp) > 0.22 * cad2.width && Math.abs(dyp) < 0.15 * cad2.height && !ferme){ dlvDessiner(); return dlvAller(DLV.i + (dxp < 0 ? 1 : -1)); }
    if (bx.w > 0.025 && bx.h > 0.015 && x.pts.length > 5){
      bx.x = Math.max(0, bx.x); bx.y = Math.max(0, bx.y); bx.w = Math.min(1 - bx.x, bx.w); bx.h = Math.min(1 - bx.y, bx.h);
      const deja = p.items.find(it => !it.exclu && dlvIou(it.box, bx) >= 0.5); if (deja){ dlvDessiner(); return dlvToast("cette bulle est déjà comptée"); }
      dlvSnap();
      const id = 900 + DLV.pages.reduce((s, q) => s + q.items.filter(y => y.ajout).length, 0) + p.page * 0;
      const nid = Math.max(900, ...p.items.filter(y => y.ajout).map(y => y.id + 1)) + (id - id);
      // place de lecture : apres la bulle la plus proche situee AVANT (plus haut, ou meme hauteur et plus a droite)
      const cy = bx.y + bx.h / 2, cx = bx.x + bx.w / 2; let pos = 0;
      p.items.forEach((it, k) => { const iy = it.box.y + it.box.h / 2, ix = it.box.x + it.box.w / 2; if (iy < cy - 0.03 || (Math.abs(iy - cy) <= 0.03 && ix > cx)) pos = k + 1; });
      p.items.splice(pos, 0, { id: nid, box: { x: +bx.x.toFixed(4), y: +bx.y.toFixed(4), w: +bx.w.toFixed(4), h: +bx.h.toFixed(4) }, ajout: true }); p.modif++;
      dlvDessiner(); dlvBas(); return dlvToast("＋ bulle ajoutée (" + (p.items.filter(y => !y.exclu).indexOf(p.items[pos]) + 1) + ") · lue à la préparation");
    }
    dlvDessiner();
  };
  cad.addEventListener("pointerup", fin); cad.addEventListener("pointercancel", () => { g = null; dlvDessiner(); });
})();
/* entrees : etape « 🔍 Bulles » (plage connue) et « 🔍 Verifier les bulles · gratuit » (nouvelle plage) */
function dlvPortee(){ return DLG.portee === "chap" ? "1-" + (CHAP_PAGES || 1) : dlgPorteeTxt(); }
function dlvVerifiee(k){ const [a, b] = dplBornes(k), vp = new Set((DLG.e && DLG.e.verif_pages) || []); if (!vp.size) return false; for (let n = a; n <= Math.min(b, CHAP_PAGES || b); n++) if (!vp.has(n)) return false; return true; }
{ const _dr2 = dplRendre; dplRendre = function(){
    _dr2.apply(this, arguments);
    const et = $("dplEtapes"); if (!et) return;
    let bb = $("dplBulles"); if (!bb){ bb = document.createElement("button"); bb.id = "dplBulles"; bb.className = "btn sm"; bb.onclick = () => dlvOuvrir(dlvPortee()); }
    let vb = $("dplVerif"); if (!vb){ vb = document.createElement("button"); vb.id = "dplVerif"; vb.className = "btn sm pri"; vb.onclick = () => dlvOuvrir(dlvPortee()); }
    const ks = dplListe(), cle = dplCle(), connue = ks.includes(cle) && !DPL.nouv, lot = DLG.portee === "lot";
    const occupe = !!((DLG.e && DLG.e.en_cours) || (DLG.lot && DLG.lot.en_cours));
    if (connue){ et.prepend(bb); bb.hidden = false; vb.hidden = true; const ok = dlvVerifiee(cle); bb.textContent = ok ? "✓ Bulles" : "🔍 Bulles"; bb.classList.toggle("dpl-fait", ok); bb.disabled = occupe;
                 $("dlgPreparer").classList.remove("dpl-sansverif"); }
    else if (!lot){ et.prepend(vb); vb.hidden = false; bb.hidden = true; vb.disabled = occupe;
                 vb.innerHTML = '🔍 Vérifier les bulles <span style="font-weight:400;font-size:12px">· gratuit</span>';
                 const pr = $("dlgPreparer"); if (!pr.hidden){ pr.classList.add("dpl-sansverif"); pr.classList.remove("pri", "dlg-suiv");
                   pr.textContent = "préparer" + (DLG.portee === "pages" ? " " + dplTitre(dlgPorteeTxt()) : "") + " sans vérifier (" + ((pr.textContent.match(/≈ [^)]+$/) || [""])[0] || "") + ")"; et.append(pr); } }
    else { bb.hidden = vb.hidden = true; $("dlgPreparer").classList.remove("dpl-sansverif"); }
  }; }

"""
rep("/* ---- l'ecran de preparation : distribution du MANGA + repliques du chapitre ---- */",
    JS + "/* ---- l'ecran de preparation : distribution du MANGA + repliques du chapitre ---- */")
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok v3.1.0")
