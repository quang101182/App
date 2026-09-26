# -*- coding: utf-8 -*-
"""Manga Studio v2.67.2 -> v2.68.0 : LECTEUR VIDEO (maquette_lecteur_video_v1, validee par Quang le 26/09/2026 11h05 : A a H).
A barre du bas ⏮ ch. · −10 · ⏯ · +10 · ch. ⏭ + glissement = chapitre ; B toucher l'image = ⏯, deux touches gauche/droite = ∓10 s ;
C progression large + temps ; D reprise de position (serveur, action « video_pos ») ; E fin -> ch. suivant dans 5 s ;
F barre masquee apres 3 s ; G ⋯ vitesse + plein ecran ; H ecran allume (Wake Lock). Clavier PC.
Fichier en CRLF avec quelques lignes LF : ancres converties, fichier NON normalise.
Rejouable : python app_patch_268_lecteur_video.py <manga_studio.html>
"""
import sys

P = sys.argv[1]
s = open(P, "rb").read().decode("utf-8")
assert "\r\n" in s
if "v2.68.0 : lecteur video" in s:
    print("deja patche"); sys.exit(0)


def rep(a, b, n=1):
    global s
    a, b = a.replace("\n", "\r\n"), b.replace("\n", "\r\n")
    if s.count(a) != n:
        raise SystemExit("ancre %d fois (attendu %d) : %r" % (s.count(a), n, a[:80]))
    s = s.replace(a, b)


rep("<title>Manga Studio v2.67.2</title>", "<title>Manga Studio v2.68.0</title>")
rep('<span class="ver" id="verBadge">v2.67.2</span>', '<span class="ver" id="verBadge">v2.68.0</span>')
rep('const VERSION = "2.67.2";', 'const VERSION = "2.68.0";')

# ---------------------------------------------------------------- HTML
rep('''<div id="vidLecteur" class="vid-lecteur" hidden>
  <div class="vid-lec-tete"><button class="btn sm retour" id="vidLecFermer">← Fermer</button><b id="vidLecTitre"></b>
    <button class="btn sm ch-nav" id="vidLecPrev" hidden>⏮ ch.</button><button class="btn sm ch-nav" id="vidLecNext" hidden>ch. ⏭</button></div>
  <div class="vid-lec-saut" id="vidLecSaut"></div>
  <video id="vidLecVideo" controls playsinline preload="metadata"></video>
</div>''',
'''<!-- v2.68.0 : lecteur video (maquette_lecteur_video_v1, validee 26/09 11h05) -- la MEME barre que la visionneuse, en bas -->
<div id="vidLecteur" class="vid-lecteur" hidden>
  <div class="vid-lec-tete"><button class="btn sm retour" id="vidLecFermer">← Fermer</button><b id="vidLecTitre"></b>
    <div class="menu-plus" id="vidMenu"><button class="btn sm plus" aria-haspopup="menu" aria-expanded="false" title="vitesse, plein écran">⋯</button>
      <div class="menu-pan" role="menu" hidden>
        <button role="menuitem" data-vit="1">1× · vitesse normale</button><button role="menuitem" data-vit="1.25">1,25×</button>
        <button role="menuitem" data-vit="1.5">1,5×</button><hr><button role="menuitem" id="vidPlein">⛶ Plein écran</button></div></div></div>
  <div class="vid-lec-saut" id="vidLecSaut"></div>
  <div class="vid-zone" id="vidZone"><video id="vidLecVideo" playsinline preload="metadata"></video>
    <div class="vid-flash" id="vidFlash" hidden></div>
    <div class="vid-suite" id="vidSuite" hidden><div class="vid-cpt" id="vidCpt">5</div><b id="vidSuiteTxt"></b>
      <div class="vid-suite-b"><button class="btn sm" id="vidSuiteNon">Annuler</button><button class="btn pri" id="vidSuiteOui">▶ Maintenant</button></div></div>
  </div>
  <div class="vid-bas" id="vidBas">
    <div class="vid-temps"><span id="vidT">0:00</span><span id="vidD">0:00</span></div>
    <input type="range" id="vidProg" min="0" max="1000" value="0" step="1" aria-label="position dans la vidéo">
    <div class="vid-bar" id="vidBar"><button class="btn sm ch-nav" id="vidLecPrev" hidden>⏮ ch.</button>
      <button class="btn sm" id="vidM10" title="reculer de 10 s">−10</button><button class="btn sm vid-pp" id="vidPP" title="lecture / pause">⏸</button>
      <button class="btn sm" id="vidP10" title="avancer de 10 s">+10</button><button class="btn sm ch-nav" id="vidLecNext" hidden>ch. ⏭</button></div>
  </div>
</div>''')

# ---------------------------------------------------------------- CSS
rep('''.vid-lecteur video{flex:1;min-height:0;max-width:100%;padding-bottom:max(12px, env(safe-area-inset-bottom))}''',
'''/* v2.68.0 : lecteur video -- image au centre, barre du bas comme la visionneuse ; « calme » = barre effacee pendant la lecture */
.vid-zone{position:relative;flex:1;min-height:0;width:100%;display:flex;align-items:center;justify-content:center;overflow:hidden}
.vid-zone video{width:100%;height:100%;object-fit:contain;display:block}
.vid-flash{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);min-width:70px;height:70px;padding:0 12px;border-radius:35px;
  background:#000a;color:#fff;display:flex;align-items:center;justify-content:center;font-size:22px;font-weight:700;pointer-events:none}
.vid-flash[hidden]{display:none}.vid-flash.g{left:22%}.vid-flash.d{left:78%}
.vid-suite{position:absolute;inset:0;background:#000c;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;text-align:center;padding:16px}
.vid-suite[hidden]{display:none}
.vid-cpt{width:76px;height:76px;border-radius:50%;border:4px solid #e0a030;display:flex;align-items:center;justify-content:center;font-size:28px;font-weight:700}
.vid-suite-b{display:flex;gap:10px}
.vid-bas{width:100%;max-width:760px;padding:4px 10px max(12px, env(safe-area-inset-bottom));box-sizing:border-box;transition:opacity .25s}
.vid-temps{display:flex;justify-content:space-between;font-size:12px;color:#cfd6e3}
#vidProg{width:100%;margin:4px 0 8px;accent-color:#e0a030;height:24px}
.vid-bar{display:flex;gap:8px;align-items:center;justify-content:center;flex-wrap:wrap;touch-action:pan-y;user-select:none;-webkit-user-select:none}
.vid-bar>.btn.sm{border-radius:999px;min-width:44px;height:40px;justify-content:center;font-size:14px}
.vid-bar>.vid-pp{min-width:58px;height:46px;font-size:20px;background:#2f7a4f;border-color:#3f9a64;color:#fff}
.vid-bar.glisse-pret>.vid-pp{background:#3f9a64}
.vid-lec-tete,.vid-lec-saut{transition:opacity .25s}
.vid-lecteur.calme .vid-bas,.vid-lecteur.calme .vid-lec-tete,.vid-lecteur.calme .vid-lec-saut{opacity:0;pointer-events:none}
.vid-lecteur.calme .vid-zone::after{content:"";position:absolute;left:0;bottom:0;height:3px;width:var(--vp,0%);background:#e0a030}
.vid-lecteur .menu-pan>button.on{color:#e0a030;font-weight:700}''')

# ---------------------------------------------------------------- JS : ouverture
rep('''function vidOuvrir(i){
  const c = VIDS.chapitres[i], v = c && (c.videos || [])[0];
  if (!v) return;
  VID_COUR = i;
  $("vidLecTitre").textContent = c.titre + " — ch. " + c.chapitre + " · " + v.tag;
  $("vidLecVideo").src = CFG.base + "/manga/video_file?p=" + encodeURIComponent(v.fichier) + "&v=" + v.v + (CFG.key ? "&_k=" + encodeURIComponent(CFG.key) : "");
  $("vidLecteur").hidden = false; $("vidLecVideo").play().catch(() => {});
  vidNavMaj();
}''',
'''/* v2.68.0 : lecteur video -- etat, reprise de position (D), fin enchainee (E), barre qui s'efface (F), ecran allume (H) */
const VID = { cour: null, vit: 1, tap: null, calmeT: 0, suiteT: 0, envoiT: 0, wake: null, glisse: false };
const vEl = () => $("vidLecVideo");
const vidFmt = x => { x = Math.max(0, Math.floor(x || 0)); const h = Math.floor(x / 3600), m = Math.floor(x % 3600 / 60), s2 = String(x % 60).padStart(2, "0");
  return h ? h + ":" + String(m).padStart(2, "0") + ":" + s2 : m + ":" + s2; };
function vidPosSauver(){
  const v = VID.cour, e = vEl(); if (!v || !e.duration) return;
  const pos = e.currentTime, duree = e.duration; BIB.videos_pos = BIB.videos_pos || {};
  if (pos < 5 || pos > duree - 10) delete BIB.videos_pos[v.fichier];
  else BIB.videos_pos[v.fichier] = { pos, duree, t: Date.now() / 1000 };
  if (navigator.webdriver) return;                                         // un navigateur pilote (banc) n'ecrit rien
  api("/manga/bibliotheque", { action: "video_pos", slug: v.fichier.split("/")[0], fichier: v.fichier, pos, duree }).catch(() => {});
}
async function vidEveil(on){                                               // H : l'ecran ne s'eteint pas pendant la lecture
  try {
    if (on && !VID.wake && navigator.wakeLock){ VID.wake = await navigator.wakeLock.request("screen"); VID.wake.addEventListener("release", () => { VID.wake = null; }); }
    else if (!on && VID.wake){ const w = VID.wake; VID.wake = null; await w.release(); }
  } catch {}
}
function vidReveil(){                                                      // F : la barre revient, et repart dans 3 s si ca joue
  $("vidLecteur").classList.remove("calme"); clearTimeout(VID.calmeT);
  VID.calmeT = setTimeout(() => { const e = vEl(); if (!e.paused && $("vidSuite").hidden && !document.querySelector("#vidMenu .menu-pan:not([hidden])"))
    $("vidLecteur").classList.add("calme"); }, 3000);
}
function vidFlash(txt, cote){ const f = $("vidFlash"); f.textContent = txt; f.className = "vid-flash" + (cote ? " " + cote : ""); f.hidden = false;
  clearTimeout(f._t); f._t = setTimeout(() => { f.hidden = true; }, 600); }
function vidSaut(sec){ const e = vEl(); if (!e.duration) return; e.currentTime = Math.max(0, Math.min(e.duration - 0.2, e.currentTime + sec));
  vidFlash((sec < 0 ? "−" : "+") + Math.abs(sec) + " s", sec < 0 ? "g" : "d"); vidTempsMaj(); }
function vidPP(){ const e = vEl(); if (!$("vidSuite").hidden) vidSuiteStop();
  if (e.ended) { e.currentTime = 0; e.play().catch(() => {}); vidFlash("↻"); return; }
  if (e.paused){ e.play().catch(() => {}); vidFlash("▶"); } else { e.pause(); vidFlash("⏸"); } }
function vidTempsMaj(){ const e = vEl(), d = e.duration || 0;
  $("vidT").textContent = vidFmt(e.currentTime); $("vidD").textContent = vidFmt(d);
  if (!VID.glisseProg) $("vidProg").value = d ? Math.round(e.currentTime / d * 1000) : 0;
  $("vidLecteur").style.setProperty("--vp", (d ? e.currentTime / d * 100 : 0) + "%"); }
function vidSuiteStop(){ clearInterval(VID.suiteT); VID.suiteT = 0; $("vidSuite").hidden = true; }
function vidSuiteLancer(){                                                 // E : le chapitre suivant dans 5 s (Annuler / Maintenant)
  const n = vidVoisin(1); if (!n) return false;
  let k = 5; $("vidCpt").textContent = k; $("vidSuiteTxt").textContent = "ch. " + n.c.chapitre + " dans 5 s"
    + (n.trou ? " (saut : ch. " + n.trou + ")" : ""); $("vidSuite").hidden = false; vidReveil();
  VID.suiteT = setInterval(() => { k--; $("vidCpt").textContent = k; $("vidSuiteTxt").textContent = "ch. " + n.c.chapitre + " dans " + k + " s";
    if (k <= 0){ vidSuiteStop(); vidOuvrir(n.i); } }, 1000);
  return true;
}
function vidOuvrir(i){
  const c = VIDS.chapitres[i], v = c && (c.videos || [])[0];
  if (!v) return;
  if (VID.cour && !$("vidLecteur").hidden) vidPosSauver();                 // D : la position du chapitre quitte est gardee
  vidSuiteStop();
  VID_COUR = i; VID.cour = v;
  $("vidLecTitre").textContent = c.titre + " — ch. " + c.chapitre + " · " + v.tag;
  const e = vEl(), pos = ((BIB.videos_pos || {})[v.fichier] || {}).pos || 0;
  e.src = CFG.base + "/manga/video_file?p=" + encodeURIComponent(v.fichier) + "&v=" + v.v + (CFG.key ? "&_k=" + encodeURIComponent(CFG.key) : "");
  e.onloadedmetadata = () => { e.playbackRate = VID.vit; if (pos && pos < e.duration - 10){ e.currentTime = pos; toast("reprise à " + vidFmt(pos)); } vidTempsMaj(); };
  $("vidLecteur").hidden = false; e.play().catch(() => {});
  vidNavMaj(); vidReveil();
}''')

# ---------------------------------------------------------------- JS : fermeture + evenements
rep('''$("vidLecFermer").onclick = () => { $("vidLecVideo").pause(); $("vidLecVideo").removeAttribute("src"); $("vidLecteur").hidden = true; };''',
'''$("vidLecFermer").onclick = () => { if (VID.glisse) return; vidPosSauver(); vidSuiteStop(); vidEveil(false);   // v2.68.0 : position gardee
  if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
  $("vidLecVideo").pause(); $("vidLecVideo").removeAttribute("src"); $("vidLecteur").hidden = true; $("vidLecteur").classList.remove("calme"); };
/* v2.68.0 : evenements du lecteur video */
(function vidLecteurInit(){
  const e = vEl(), lec = $("vidLecteur");
  e.addEventListener("play", () => { $("vidPP").textContent = "⏸"; vidEveil(true); vidReveil(); });
  e.addEventListener("pause", () => { $("vidPP").textContent = e.ended ? "↻" : "▶"; vidEveil(false); vidPosSauver(); vidReveil(); });
  e.addEventListener("timeupdate", () => { vidTempsMaj(); if (Date.now() - VID.envoiT > 10000){ VID.envoiT = Date.now(); vidPosSauver(); } });
  e.addEventListener("ended", () => { $("vidPP").textContent = "↻"; vidPosSauver(); vidEveil(false); if (!vidSuiteLancer()) vidReveil(); });
  $("vidPP").onclick = () => { if (!VID.glisse) vidPP(); };
  $("vidM10").onclick = () => { if (!VID.glisse) vidSaut(-10); };
  $("vidP10").onclick = () => { if (!VID.glisse) vidSaut(10); };
  $("vidSuiteNon").onclick = () => { vidSuiteStop(); vidReveil(); };
  $("vidSuiteOui").onclick = () => { const n = vidVoisin(1); vidSuiteStop(); if (n) vidOuvrir(n.i); };
  const pr = $("vidProg");                                                // C : la barre de progression se glisse
  pr.addEventListener("input", () => { VID.glisseProg = true; const d = e.duration || 0; if (d){ e.currentTime = pr.value / 1000 * d; $("vidT").textContent = vidFmt(e.currentTime); } vidReveil(); });
  pr.addEventListener("change", () => { VID.glisseProg = false; vidPosSauver(); });
  // B : toucher l'image = ⏯ (si la barre etait effacee : la fait revenir) ; deux touches a gauche / a droite = ∓10 s
  $("vidZone").addEventListener("click", ev => {
    if (ev.target.closest("#vidSuite")) return;
    const r = $("vidZone").getBoundingClientRect(), x = (ev.clientX - r.left) / r.width, now = Date.now();
    if (VID.tap && now - VID.tap.t < 300){ clearTimeout(VID.tap.to); VID.tap = null;
      if (x < 1 / 3) vidSaut(-10); else if (x > 2 / 3) vidSaut(10); else vidPP(); return; }
    const calme = lec.classList.contains("calme");
    VID.tap = { t: now, to: setTimeout(() => { VID.tap = null; if (calme) vidReveil(); else vidPP(); }, 280) };
  });
  ["vidBas", "vidLecSaut"].forEach(id => $(id).addEventListener("pointerdown", vidReveil));
  document.querySelector("#vidLecteur .vid-lec-tete").addEventListener("pointerdown", vidReveil);
  // A : glisser LA BARRE (pas l'image) = chapitre precedent / suivant, dans le sens des boutons (> 60 px, net) -- comme la visionneuse
  const bar = $("vidBar"); let x0 = null, y0 = 0, dx = 0, net = false;
  bar.addEventListener("touchstart", ev => { const t = ev.touches[0]; x0 = t.clientX; y0 = t.clientY; dx = 0; net = false; }, { passive: true });
  bar.addEventListener("touchmove", ev => { if (x0 === null) return; const t = ev.touches[0]; dx = t.clientX - x0;
    if (!net && Math.abs(dx) > 10 && Math.abs(dx) > Math.abs(t.clientY - y0) * 1.5) net = true;
    bar.classList.toggle("glisse-pret", net && Math.abs(dx) >= 60); }, { passive: true });
  const fin = () => { if (x0 === null) return; bar.classList.remove("glisse-pret");
    if (net && Math.abs(dx) >= 60){ const b = dx > 0 ? $("vidLecNext") : $("vidLecPrev"); if (!b.hidden){ VID.glisse = false; b.click(); } }
    x0 = null; if (net){ VID.glisse = true; setTimeout(() => { VID.glisse = false; }, 60); } };
  bar.addEventListener("touchend", fin); bar.addEventListener("touchcancel", fin);
  // G : vitesse + plein ecran
  document.querySelectorAll("#vidMenu [data-vit]").forEach(b => b.onclick = () => { VID.vit = +b.dataset.vit; e.playbackRate = VID.vit;
    document.querySelectorAll("#vidMenu [data-vit]").forEach(x => x.classList.toggle("on", x === b)); toast("vitesse " + b.textContent.split(" ")[0]); });
  $("vidPlein").onclick = async () => {
    try { if (document.fullscreenElement) await document.exitFullscreen();
          else { await lec.requestFullscreen(); try { await screen.orientation.lock("landscape"); } catch {} } } catch {} };
  document.addEventListener("visibilitychange", () => {
    if (lec.hidden) return;
    if (document.visibilityState === "hidden") vidPosSauver(); else if (!e.paused) vidEveil(true); });
  // clavier (PC) : Espace = ⏯ · ← / → = ∓10 s · Maj + ← / → = chapitre · Echap = fermer
  document.addEventListener("keydown", ev => {
    if (lec.hidden || ev.target.closest("input, textarea, select")) return;
    if (ev.key === " " || ev.key === "k"){ ev.preventDefault(); vidPP(); }
    else if (ev.key === "ArrowLeft" || ev.key === "ArrowRight"){ ev.preventDefault();
      if (ev.shiftKey){ const b = ev.key === "ArrowRight" ? $("vidLecNext") : $("vidLecPrev"); if (!b.hidden) b.click(); }
      else vidSaut(ev.key === "ArrowRight" ? 10 : -10); }
    else if (ev.key === "Escape" && !document.querySelector("#vidMenu .menu-pan:not([hidden])")) $("vidLecFermer").click();
    vidReveil();
  });
})();''')

open(P, "wb").write(s.encode("utf-8"))
print("patche")
