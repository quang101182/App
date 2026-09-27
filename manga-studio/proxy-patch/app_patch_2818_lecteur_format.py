# -*- coding: utf-8 -*-
"""v2.81.8 (27/09, R2 -- Quang 02h30 : « la barre de navigation en bas ne ressemble pas a toute l'application […] toutes ses
fonctions associees, meme les fonctions de swipe ») : le lecteur des Dialogues prend le SQUELETTE, les CLASSES et les GESTES du
lecteur de narration (#lecteur), fonction par fonction (constat : ROADMAP R2) :
  barre du haut « ← Fermer » bleu a gauche + titre + ⏮ ch. / ch. ⏭ (chapitres voisins AVEC dialogues) ; sous-titre .lec-sous ;
  barre de progression .lec-bar cliquable et glissable ; commandes .lec-ctl ⏮ ⏸ ⏭ + 🔊 volume general (le meme VOL_G) +
  ⚙ Reglages (vitesse, sous-titres, caméra) ; glisser la barre ←/→ (> 60 px, net) = ⏮/⏭ ; glisser vers le bas / toucher le
  titre / touche G = selecteur rapide (aller a la page) ; clavier espace, ←/→, Echap (reglages d'abord).
⏮/⏭ = la replique (l'unite des Dialogues). Suppose app_patch_2817. Rejouable."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v2.81.8" in s[:400]:
    print("deja applique"); sys.exit(0)
if "v2.81.7" not in s[:400]:
    print("ERREUR : appliquer d'abord app_patch_2817_pages_vues.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


# --- 1. le squelette du lecteur de reference
rep("""dlgLec.id = "dlgLec"; dlgLec.hidden = true;
dlgLec.innerHTML = '<div class="dlgl-scene" id="dllScene">""", """dlgLec.id = "dlgLec"; dlgLec.hidden = true; dlgLec.className = "lecteur";
dlgLec.innerHTML = '<div class="lec-top"><button class="btn sm retour" id="dllFermer">← Fermer</button>'
  + '<span class="lec-t"><b id="dllTitre"></b> <span class="muted" id="dllPos"></span></span>'
  + '<button class="btn sm ch-nav" id="dllChPrev" title="chapitre précédent (avec dialogues)">⏮ ch.</button>'
  + '<button class="btn sm ch-nav" id="dllChNext" title="chapitre suivant (avec dialogues)">ch. ⏭</button></div>'
  + '<div class="dlgl-scene" id="dllScene">""")
rep("""  + '<div class="dlgl-sous" id="dllSous"></div>'
  + '<div class="dlgl-barre"><span class="bulle" id="dllPos"></span><span style="flex:1"></span>'
  + '<button class="btn sm" id="dllPrec" title="réplique précédente">⏮</button><button class="btn sm" id="dllJouer" title="lecture / pause">⏸</button>'
  + '<button class="btn sm" id="dllSuiv" title="réplique suivante">⏭</button>'
  + '<button class="btn sm" id="dllCam" title="caméra : suivre la case de la bulle qui parle">🎥</button>'
  + '<select id="dllVit" title="vitesse"><option value="0.9">0,9×</option><option value="1" selected>1,0×</option><option value="1.1">1,1×</option><option value="1.25">1,25×</option><option value="1.5">1,5×</option></select>'
  + '<button class="btn sm retour" id="dllFermer">← Fermer</button></div>';""",
    """  + '<p class="lec-sous dll-sous" id="dllSous"></p>'
  + '<div class="lec-bar" id="dllBar" title="clique ou glisse pour te déplacer dans les dialogues"><div id="dllProg"></div><span id="dllTemps"></span></div>'
  + '<div class="lec-ctl" id="dllCtl"><button class="btn" id="dllPrec" title="réplique précédente (←)">⏮</button>'
  + '<button class="btn pri" id="dllJouer" title="lecture / pause (espace)">⏸</button><button class="btn" id="dllSuiv" title="réplique suivante (→)">⏭</button>'
  + '<label class="lec-chk" title="volume général (le même que la narration) — sur téléphone, s\\'ajoute aux touches de volume">🔊 <input type="range" class="lec-vol" id="dllVol" min="0" max="100" step="1"></label>'
  + '<button class="btn" id="dllRegBtn" aria-expanded="false" title="vitesse, sous-titres, caméra">⚙<span class="lec-reg-l"> Réglages</span></button></div>'
  + '<div class="lec-reg" id="dllReg" hidden><div class="lec-reg-t"><button class="btn sm retour" id="dllRegFermer" title="revenir à la lecture">← Lecture</button><b>⚙ Réglages des dialogues</b></div>'
  + '<label class="lec-ligne"><span>Vitesse</span><select id="dllVit" style="width:auto"><option value="0.9">0,9×</option><option value="1" selected>1×</option><option value="1.1">1,1×</option><option value="1.25">1,25×</option><option value="1.5">1,5×</option></select></label>'
  + '<label class="lec-ligne"><span>Sous-titres</span><input type="checkbox" class="bascule" id="dllSousOn" checked></label>'
  + '<label class="lec-ligne" title="la caméra cadre la case de la bulle qui parle (sinon : la page entière). Mémorisé sur cet appareil"><span>🎥 Suivre la case <small class="muted">sinon la page entière</small></span><input type="checkbox" class="bascule" id="dllCam"></label></div>';""")

# --- 2. le CSS : ce que la reference a par identifiant (#lecteur ...) vaut aussi ici
rep(""".dlgl-manq[hidden]{display:none}""", """.dlgl-manq[hidden]{display:none}
#dlgLec.lecteur{z-index:90}#dlgLec .lec-t b{flex:none;max-width:none}#dlgLec .lec-t #dllPos{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}#dlgLec .dlgl-scene{flex:1;min-height:0}
#dlgLec .dll-sous b{margin-right:6px}#dlgLec .dll-sous .dlg-pastille{margin-right:6px;vertical-align:middle}
#dlgLec .lec-ctl{position:relative;touch-action:none}
#dlgLec .lec-ctl::before{content:"";position:absolute;left:50%;top:-8px;width:34px;height:4px;margin-left:-17px;border-radius:2px;background:#ffffff38;pointer-events:none}
#dllPrec,#dllJouer,#dllSuiv{width:52px;height:52px;border-radius:50%;justify-content:center;font-size:19px;padding:0}
@media (max-width:480px){ #dllPrec,#dllJouer,#dllSuiv{width:46px;height:46px}
  #dlgLec .lec-ctl{gap:5px;padding:10px 4px} #dlgLec .lec-ctl .lec-chk input.lec-vol{width:78px;flex:0 0 78px} }""")

# --- 3. titre, position, progression
rep("""  $("dllPos").textContent = (c ? "ch. " + c.chapter + " · " : "") + "p. " + x.page + " · " + (DLL.i + 1) + "/" + DLL.liste.length;""",
    """  $("dllTitre").textContent = "🎭 " + (c ? "ch. " + c.chapter : "Dialogues"); $("dllTitre").dataset.serie = c ? c.title : "";   // court : tient a 360 px
  $("dllPos").textContent = "p. " + x.page + " · " + (DLL.i + 1) + "/" + DLL.liste.length;
  dllBarre();""")
rep("""function dllCouleur(qui){""", """function dllBarre(f){                           // v2.81.8 : progression = etape courante (+ avancee de sa voix)
  const n = DLL.liste.length || 1, a = DLL.audio;
  const dans = f !== undefined ? 0 : (!DLL.sil && a.duration ? Math.min(1, a.currentTime / a.duration) : 0);
  const fr = f !== undefined ? f : (DLL.i + dans) / n;
  $("dllProg").style.width = (Math.max(0, Math.min(1, fr)) * 100).toFixed(2) + "%";
  $("dllTemps").textContent = "réplique " + Math.min(n, Math.floor(fr * n) + 1) + " / " + n;
}
function dllCouleur(qui){""")
rep("""DLL.audio.onended = dllApres;""", """DLL.audio.onended = dllApres;
DLL.audio.addEventListener("timeupdate", () => { if (!dlgLec.hidden) dllBarre(); });
(function dllBarreGeste(){                        // cliquer / glisser la barre = aller a cette etape (comme #lecBar)
  const bar = $("dllBar"); let actif = false;
  const frac = e => { const r = bar.getBoundingClientRect(); return Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)); };
  const aller = f => { const n = DLL.liste.length; if (!n) return; DLL.audio.pause(); DLL.i = Math.min(n - 1, Math.floor(f * n)); dllMontrer(); };
  bar.addEventListener("pointerdown", e => { if (!DLL.liste.length) return; actif = true; bar.setPointerCapture(e.pointerId); dllBarre(frac(e)); });
  bar.addEventListener("pointermove", e => { if (actif) dllBarre(frac(e)); });
  bar.addEventListener("pointerup", e => { if (!actif) return; actif = false; aller(frac(e)); });
  bar.addEventListener("pointercancel", () => { actif = false; dllBarre(); });
})();
(function dllGlisser(){                           // glisser la barre des commandes ←/→ (> 60 px, net) = ⏮/⏭, comme la reference
  const bar = $("dllCtl"); let x0 = null, y0 = 0, dx = 0, net = false;
  bar.addEventListener("touchstart", e => { if (e.target.closest("input, select, .lec-reg")) { x0 = null; return; }
    const t = e.touches[0]; x0 = t.clientX; y0 = t.clientY; dx = 0; net = false; }, { passive: true });
  bar.addEventListener("touchmove", e => { if (x0 === null) return; const t = e.touches[0]; dx = t.clientX - x0;
    if (!net && Math.abs(dx) > 10 && Math.abs(dx) > Math.abs(t.clientY - y0) * 1.5) net = true; }, { passive: true });
  const fin = () => { if (x0 === null) return; x0 = null; if (net && Math.abs(dx) >= 60) (dx > 0 ? $("dllSuiv") : $("dllPrec")).click(); };
  bar.addEventListener("touchend", fin); bar.addEventListener("touchcancel", fin);
  selGlisserHaut(bar);                            // vers le bas = selecteur rapide
  $("dllTitre").style.cursor = "pointer"; $("dllTitre").title = "toucher : aller à une page (ou glisser la barre du bas vers le bas)";
  $("dllTitre").addEventListener("click", ev => { ev.stopPropagation(); const c = selContexte(); if (c) selOuvrir(c); });
})();
function selCtxDlg(){                             // v2.81.8 : le selecteur rapide du lecteur des Dialogues = les pages de la portee
  const pages = [...new Set(DLL.liste.map(x => x.page))];
  const cour = (DLL.liste[DLL.i] || {}).page;
  const items = pages.map(n => ({ cle: "p" + n, num: n, label: String(n), classe: n === cour ? "cour" : "",
                                  sous: DLL.liste.some(x => x.page === n && x.vide) ? "·" : "" }));
  return { titre: "Dialogues — aller à la page", quoi: "page", items, filtres: [],
           choisir: it => { DLL.audio.pause(); DLL.i = DLL.liste.findIndex(x => x.page === it.num); dllMontrer(); } };
}
async function dllVoisin(delta){                  // ⏮ ch. / ch. ⏭ : le chapitre voisin qui A des dialogues
  let d = DLL.d;
  for (let n = 0; n < 400; n++){
    const k = chapVoisin(d, delta); if (k < 0) return null;
    d = CHAPS[k].dir;
    if (!RESUME || !RESUME.chapitres[d] || RESUME.chapitres[d].dlg) return d;
  }
  return null;
}
async function dllChMaj(){
  for (const [id, dl] of [["dllChPrev", -1], ["dllChNext", 1]]){
    const d = await dllVoisin(dl); const b = $(id);
    b.disabled = !d; b.dataset.d = d || ""; b.title = d ? "chapitre " + (dl < 0 ? "précédent" : "suivant") + " : " + (CHAPS.find(c => c.dir === d) || {}).chapter : "aucun chapitre " + (dl < 0 ? "précédent" : "suivant") + " avec dialogues";
  }
}
["dllChPrev", "dllChNext"].forEach(id => { $(id).onclick = () => { const d = $(id).dataset.d; if (!d) return; DLL.audio.pause(); clearTimeout(DLL.t); clearTimeout(DLL.t2); dlgLecteur(d, 0); }; });
function dllRegOuvrir(on){
  if (on) dlgLec.style.setProperty("--lec-bas", Math.round(dlgLec.getBoundingClientRect().bottom - $("dllCtl").getBoundingClientRect().top + 6) + "px");
  $("dllReg").hidden = !on; $("dllRegBtn").setAttribute("aria-expanded", on ? "true" : "false");
}
$("dllRegBtn").onclick = () => dllRegOuvrir($("dllReg").hidden);
$("dllRegFermer").onclick = () => dllRegOuvrir(false);
$("dllSousOn").onchange = () => { $("dllSous").style.visibility = $("dllSousOn").checked ? "" : "hidden"; };
$("dllVol").value = typeof VOL_G === "number" ? VOL_G : 100; DLL.audio.volume = (+$("dllVol").value) / 100;
$("dllVol").oninput = () => { VOL_G = +$("dllVol").value; DLL.audio.volume = VOL_G / 100; if ($("lecVolG")) $("lecVolG").value = VOL_G;
  try { localStorage.setItem("manga_vol_g", String(VOL_G)); } catch {} };""")

# --- 4. la camera devient une bascule des reglages
rep("""function dllCamMaj(){ $("dllCam").classList.toggle("on", DLL_CAM); $("dllCam").style.opacity = DLL_CAM ? 1 : .45;
  $("dllCam").title = DLL_CAM ? "caméra : suit la case (toucher = page entière)" : "page entière (toucher = suivre la case)"; }
$("dllCam").onclick = () => { DLL_CAM = !DLL_CAM; try { localStorage.setItem("manga_dlg_cam", DLL_CAM ? "1" : "0"); } catch {}
  dllCamMaj(); dllCamera(DLL.liste[DLL.i], true); };""",
    """function dllCamMaj(){ $("dllCam").checked = DLL_CAM; }
$("dllCam").onchange = () => { DLL_CAM = $("dllCam").checked; try { localStorage.setItem("manga_dlg_cam", DLL_CAM ? "1" : "0"); } catch {}
  dllCamera(DLL.liste[DLL.i], true); };""")

# --- 5. ouverture : titre, voisins, volume partage ; fermeture : reglages ; clavier : Echap ferme d'abord les reglages
rep("""  dlgLec.hidden = false; document.body.style.overflow = "hidden";
  dllMontrer();""", """  dlgLec.hidden = false; document.body.style.overflow = "hidden";
  dllRegOuvrir(false); $("dllVol").value = VOL_G; DLL.audio.volume = VOL_G / 100; dllChMaj();
  dllMontrer();""")
rep("""  if (e.key === "Escape") $("dllFermer").click();
  else if (e.key === " "){ e.preventDefault(); $("dllJouer").click(); }""",
    """  if (e.target.tagName === "TEXTAREA" || (e.target.tagName === "INPUT" && e.target.type !== "checkbox" && e.target.type !== "range")) return;
  if (/^(Arrow|Escape| )/.test(e.key) && (e.target.tagName === "SELECT" || e.target.type === "range")) e.target.blur();
  if (e.key === "Escape"){ if (!$("dllReg").hidden) dllRegOuvrir(false); else $("dllFermer").click(); }
  else if (e.key === " "){ e.preventDefault(); $("dllJouer").click(); }""")
rep("""  if (!$("lecteur").hidden) return LEC.aveugle ? null : selCtxNarr();          // lecture « a l'aveugle » : pas de sommaire""",
    """  if (typeof dlgLec !== "undefined" && !dlgLec.hidden) return selCtxDlg();   // v2.81.8 : le lecteur des Dialogues
  if (!$("lecteur").hidden) return LEC.aveugle ? null : selCtxNarr();          // lecture « a l'aveugle » : pas de sommaire""")
s = s.replace("<title>Manga Studio v2.81.7</title>", "<title>Manga Studio v2.81.8</title>", 1)
s = s.replace('id="verBadge">v2.81.7<', 'id="verBadge">v2.81.8<', 1)
s = s.replace('const VERSION = "2.81.7";', 'const VERSION = "2.81.8";   // v2.81.8 : lecteur des Dialogues au format de l\'app (barre, reglages, gestes) (R2)', 1)
assert s.count("2.81.8") >= 4
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
