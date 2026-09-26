# -*- coding: utf-8 -*-
"""Manga Studio v2.81.0 -- LECTEUR du mode Dialogues (ROADMAP 4-septdecies D6 ; maquette_dialogues_v2 § 5). A appliquer APRES
app_patch_2810_dialogues.py. La page traduite, legerement VOILEE ; la bulle qui parle recoit un HALO qui epouse sa forme reelle
(contour calcule a la preparation ; repli : ovale doux dans la boite), dans la couleur du personnage, qui RESPIRE pendant la
voix ; pastille a son nom ; sous-titre ; ⏮ ⏯ ⏭ ; vitesse ; fin du chapitre -> chapitre suivant s'il a des voix.
Rejouable : python app_patch_2810b_lecteur.py <manga_studio.html>"""
import io, sys

P = sys.argv[1]
s = io.open(P, encoding="utf-8", newline="").read()
if "MODE « DIALOGUES »" not in s:
    print("ERREUR : appliquer d'abord app_patch_2810_dialogues.py"); sys.exit(1)
if "function dlgLecteur(" in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"


def rep(a, b, n=1):
    global s
    a, b = a.replace("\n", NL), b.replace("\n", NL)
    assert s.count(a) == n, ("ancre", s.count(a), a[:90])
    s = s.replace(a, b)


CSS = r'''
/* v2.81.0 : lecteur des Dialogues -- halo au contour reel de la bulle, couleur du personnage */
#dlgLec{position:fixed;inset:0;z-index:90;background:#07080b;display:flex;flex-direction:column}
#dlgLec[hidden]{display:none}
.dlgl-scene{flex:1;min-height:0;display:flex;align-items:center;justify-content:center;overflow:hidden;position:relative}
.dlgl-cadre{position:relative;flex:none}
.dlgl-cadre img{display:block;width:100%;height:100%;user-select:none;-webkit-user-drag:none}
.dlgl-cadre svg{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}
.dlgl-halo{transition:opacity .3s ease}.dlgl-halo.off{opacity:0}
@keyframes dlgResp{0%,100%{opacity:.55}50%{opacity:1}}
.dlgl-lueur{animation:dlgResp 2.4s ease-in-out infinite}
@media (prefers-reduced-motion:reduce){.dlgl-lueur{animation:none}}
.dlgl-sous{display:flex;align-items:baseline;gap:8px;padding:8px 14px;font-size:15px;min-height:42px;background:#0c0e13;flex-wrap:wrap}
.dlgl-sous b{white-space:nowrap}
.dlgl-barre{display:flex;align-items:center;gap:8px;padding:10px 12px;background:#0c0e13;border-top:1px solid var(--line);flex-wrap:wrap}
.dlgl-barre .bulle{background:#1f5b3a;color:#d6ffe6;border:1px solid #2f7a4f;border-radius:99px;padding:6px 12px;font-weight:600;font-size:13px;white-space:nowrap}
.dlgl-barre .btn{border-radius:99px;min-width:38px;justify-content:center}
.dlgl-barre select{width:auto;flex:none;padding:5px 6px}
'''
rep(".dlg-pastille{width:12px;height:12px;border-radius:99px;display:inline-block;flex:none}",
    ".dlg-pastille{width:12px;height:12px;border-radius:99px;display:inline-block;flex:none}" + CSS)

JS = r'''
/* ---- v2.81.0 : le LECTEUR des Dialogues (D6) ---- */
const DLL = { d: "", doc: null, dist: null, liste: [], i: 0, W: 1, H: 1, page: null, audio: new Audio(), pause: false, t: null };
const dlgLec = document.createElement("div");
dlgLec.id = "dlgLec"; dlgLec.hidden = true;
dlgLec.innerHTML = '<div class="dlgl-scene" id="dllScene"><div class="dlgl-cadre" id="dllCadre"><img id="dllImg" alt="">'
  + '<svg id="dllSvg" preserveAspectRatio="none"></svg></div></div>'
  + '<div class="dlgl-sous" id="dllSous"></div>'
  + '<div class="dlgl-barre"><span class="bulle" id="dllPos"></span><span style="flex:1"></span>'
  + '<button class="btn sm" id="dllPrec" title="réplique précédente">⏮</button><button class="btn sm" id="dllJouer" title="lecture / pause">⏸</button>'
  + '<button class="btn sm" id="dllSuiv" title="réplique suivante">⏭</button>'
  + '<select id="dllVit" title="vitesse"><option value="0.9">0,9×</option><option value="1" selected>1,0×</option><option value="1.1">1,1×</option><option value="1.25">1,25×</option><option value="1.5">1,5×</option></select>'
  + '<button class="btn sm retour" id="dllFermer">← Fermer</button></div>';
document.body.appendChild(dlgLec);
function dllTaille(){
  const sc = $("dllScene"), r = DLL.W / DLL.H, W = sc.clientWidth - 8, H = sc.clientHeight - 8;
  let w = W, h = W / r; if (h > H){ h = H; w = H * r; }
  $("dllCadre").style.width = Math.max(10, w) + "px"; $("dllCadre").style.height = Math.max(10, h) + "px";
}
window.addEventListener("resize", () => { if (!dlgLec.hidden) dllTaille(); });
async function dlgLecteur(dir, depuis){
  const d = dir || CHAP_OPEN;
  let e;
  try { e = await api("/manga/dialogues?d=" + encodeURIComponent(d)); } catch (err) { return toast("lecteur : " + err.message); }
  const liste = ((e.doc || {}).repliques || []).filter(x => x.lire && x.voix && x.voix.fichier);
  if (!liste.length) return toast("aucune voix faite pour ce chapitre : lance « Générer les voix »");
  Object.assign(DLL, { d, doc: e.doc, dist: e.distribution || {}, liste, i: Math.max(0, Math.min(liste.length - 1, depuis || 0)), page: null, pause: false });
  DLL.audio.playbackRate = +$("dllVit").value;
  dlgLec.hidden = false; document.body.style.overflow = "hidden";
  dllMontrer();
}
function dllCouleur(qui){
  const p = ((DLL.dist.persos || []).find(x => x.nom === qui)) || (qui === "narrateur" ? DLL.dist.narrateur : null);
  return (p && p.couleur) || "#9aa6b8";
}
function dllForme(x){
  const W = DLL.W, H = DLL.H;
  if (x.contour && x.contour.length > 2) return "M" + x.contour.map(p => (p[0] * W).toFixed(1) + " " + (p[1] * H).toFixed(1)).join(" L") + " Z";
  const b = x.box, cx = (b.x + b.w / 2) * W, cy = (b.y + b.h / 2) * H, rx = b.w * W / 2 + W * 0.012, ry = b.h * H / 2 + H * 0.01;
  return "M" + (cx - rx) + " " + cy + " a" + rx + " " + ry + " 0 1 0 " + 2 * rx + " 0 a" + rx + " " + ry + " 0 1 0 " + (-2 * rx) + " 0 Z";
}
function dllHalo(x){
  const W = DLL.W, H = DLL.H, coul = dllCouleur(x.qui), f = dllForme(x), ep = Math.max(W, H) * 0.012;
  const nom = x.qui === "narrateur" ? "Narrateur" : x.qui;
  // pastille du nom au-dessus de la bulle (dans l'image)
  const xs = x.contour && x.contour.length ? x.contour.map(p => p[0]) : [x.box.x, x.box.x + x.box.w];
  const ys = x.contour && x.contour.length ? x.contour.map(p => p[1]) : [x.box.y, x.box.y + x.box.h];
  const cx = (Math.min(...xs) + Math.max(...xs)) / 2 * W, haut = Math.min(...ys) * H;
  const fs = Math.max(W, H) * 0.02, lw = nom.length * fs * 0.62 + fs * 1.4, ph = fs * 1.6;
  const px = Math.max(4, Math.min(W - lw - 4, cx - lw / 2)), py = Math.max(4, haut - ph - fs * 0.5);
  $("dllSvg").setAttribute("viewBox", "0 0 " + W + " " + H);
  $("dllSvg").innerHTML = '<defs><filter id="dllFlou" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="' + (ep * 0.7).toFixed(1) + '"/></filter>'
    + '<mask id="dllTrou"><rect width="' + W + '" height="' + H + '" fill="#fff"/><path d="' + f + '" fill="#000"/></mask></defs>'
    + '<rect width="' + W + '" height="' + H + '" fill="#05060a" opacity=".38" mask="url(#dllTrou)"/>'
    + '<g class="dlgl-halo off" id="dllG"><path d="' + f + '" fill="none" stroke="' + coul + '" stroke-width="' + (ep * 1.6).toFixed(1) + '" filter="url(#dllFlou)" class="dlgl-lueur"/>'
    + '<path d="' + f + '" fill="none" stroke="' + coul + '" stroke-width="' + (ep * 0.28).toFixed(1) + '"/>'
    + '<rect x="' + px.toFixed(1) + '" y="' + py.toFixed(1) + '" width="' + lw.toFixed(1) + '" height="' + ph.toFixed(1) + '" rx="' + (ph / 2).toFixed(1) + '" fill="' + coul + '"/>'
    + '<text x="' + (px + lw / 2).toFixed(1) + '" y="' + (py + ph * 0.7).toFixed(1) + '" font-size="' + fs.toFixed(1) + '" font-weight="700" text-anchor="middle" fill="#14080f" font-family="system-ui,sans-serif">' + esc(nom) + "</text></g>";
  requestAnimationFrame(() => { const g = $("dllG"); if (g) g.classList.remove("off"); });
}
function dllMontrer(){
  clearTimeout(DLL.t);
  const x = DLL.liste[DLL.i]; if (!x) return;
  const pages = [...new Set(DLL.liste.map(y => y.page))], c = CHAPS.find(y => y.dir === DLL.d);
  $("dllPos").textContent = (c ? "ch. " + c.chapter + " · " : "") + "p. " + x.page + " · " + (DLL.i + 1) + "/" + DLL.liste.length;
  const coul = dllCouleur(x.qui);
  $("dllSous").innerHTML = '<span class="dlg-pastille" style="background:' + esc(coul) + '"></span><b style="color:' + esc(coul) + '">'
    + esc(x.qui === "narrateur" ? "Narrateur" : x.qui) + "</b><span>" + esc(x.texte || "") + "</span>";
  const jouer = () => {
    dllHalo(x);
    DLL.audio.src = srcURL(DLL.d + "/dialogues/voix/" + x.voix.fichier);
    DLL.audio.playbackRate = +$("dllVit").value;
    if (!DLL.pause) DLL.audio.play().catch(() => {});
  };
  if (DLL.page !== x.page){
    DLL.page = x.page;
    const g = $("dllG"); if (g) g.classList.add("off");
    const img = $("dllImg");
    img.onload = () => { DLL.W = img.naturalWidth || 1; DLL.H = img.naturalHeight || 1; dllTaille(); jouer(); };
    img.src = srcURL(DLL.d + "/traduction/fr/" + x.file);
  } else jouer();
}
DLL.audio.onended = () => {
  const g = $("dllG"); if (g) g.classList.add("off");
  DLL.t = setTimeout(() => {
    if (DLL.i < DLL.liste.length - 1){ DLL.i++; return dllMontrer(); }
    dllSuite();
  }, 420);
};
async function dllSuite(){                        // fin du chapitre : le suivant, s'il a des voix (comme la visionneuse « livre »)
  const k = chapVoisin(DLL.d, 1);
  if (k < 0) return toast("fin des dialogues de la série");
  try {
    const e = await api("/manga/dialogues?d=" + encodeURIComponent(CHAPS[k].dir));
    if (((e.doc || {}).repliques || []).some(x => x.lire && x.voix)) { toast("Chapitre " + CHAPS[k].chapter); return dlgLecteur(CHAPS[k].dir, 0); }
  } catch (err) {}
  toast("fin : le ch. " + CHAPS[k].chapter + " n'a pas encore de voix");
}
$("dllPrec").onclick = () => { if (DLL.i > 0){ DLL.i--; dllMontrer(); } };
$("dllSuiv").onclick = () => { if (DLL.i < DLL.liste.length - 1){ DLL.audio.pause(); DLL.i++; dllMontrer(); } else dllSuite(); };
$("dllJouer").onclick = () => {
  DLL.pause = !DLL.pause; $("dllJouer").textContent = DLL.pause ? "▶" : "⏸";
  if (DLL.pause) DLL.audio.pause(); else DLL.audio.play().catch(() => {});
};
$("dllVit").onchange = () => { DLL.audio.playbackRate = +$("dllVit").value; };
$("dllFermer").onclick = () => { DLL.audio.pause(); clearTimeout(DLL.t); dlgLec.hidden = true; document.body.style.overflow = ""; };
document.addEventListener("keydown", e => {
  if (dlgLec.hidden) return;
  if (e.key === "Escape") $("dllFermer").click();
  else if (e.key === " "){ e.preventDefault(); $("dllJouer").click(); }
  else if (e.key === "ArrowRight") $("dllSuiv").click();
  else if (e.key === "ArrowLeft") $("dllPrec").click();
});
'''
rep("document.body.appendChild($(\"coutsModal\"));", JS + NL + "document.body.appendChild($(\"coutsModal\"));")
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("lecteur ajoute")
