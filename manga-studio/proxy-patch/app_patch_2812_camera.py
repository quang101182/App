# -*- coding: utf-8 -*-
"""Manga Studio v2.81.2 -- lecteur des Dialogues : CAMERA « suivre la case » (Quang 27/09 00h43 : « oui, c'est important »).
A appliquer apres app_patch_2811_video.py. Pendant chaque replique, un zoom doux cadre la CASE de la bulle qui parle (cases de
/manga/cases, la meme detection que la video « case par case »), elargie si besoin pour que la bulle entiere reste visible ; le
halo et le voile suivent (meme calque). Interrupteur 🎥 dans la barre, memorise sur l'appareil, ACTIF par defaut. Sans cases
pour la page (detection absente ou en cours) : page entiere.
Rejouable : python app_patch_2812_camera.py <manga_studio.html>"""
import io, sys

P = sys.argv[1]
s = io.open(P, encoding="utf-8", newline="").read()
if "dlgVidVoir" not in s:
    print("ERREUR : appliquer d'abord app_patch_2811_video.py"); sys.exit(1)
if "function dllCamera(" in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"


def rep(a, b, n=1):
    global s
    a, b = a.replace("\n", NL), b.replace("\n", NL)
    assert s.count(a) == n, ("ancre", s.count(a), a[:90])
    s = s.replace(a, b)


rep("<title>Manga Studio v2.81.1</title>", "<title>Manga Studio v2.81.2</title>")
rep('id="verBadge">v2.81.1</span>', 'id="verBadge">v2.81.2</span>')
rep('const VERSION = "2.81.1";', 'const VERSION = "2.81.2";   // v2.81.2 : lecteur des Dialogues -- camera « suivre la case »')
rep(".dlgl-cadre{position:relative;flex:none}",
    ".dlgl-cadre{position:relative;flex:none;overflow:hidden}"
    + "\n#dllZoom{position:absolute;inset:0;transform-origin:0 0}#dllZoom.anim{transition:transform .7s cubic-bezier(.4,0,.2,1)}")
rep('''dlgLec.innerHTML = '<div class="dlgl-scene" id="dllScene"><div class="dlgl-cadre" id="dllCadre"><img id="dllImg" alt="">'
  + '<svg id="dllSvg" preserveAspectRatio="none"></svg></div></div>\'''',
    '''dlgLec.innerHTML = '<div class="dlgl-scene" id="dllScene"><div class="dlgl-cadre" id="dllCadre"><div id="dllZoom"><img id="dllImg" alt="">'
  + '<svg id="dllSvg" preserveAspectRatio="none"></svg></div></div></div>\'''')
rep('''  + '<button class="btn sm" id="dllSuiv" title="réplique suivante">⏭</button>\'''',
    '''  + '<button class="btn sm" id="dllSuiv" title="réplique suivante">⏭</button>'
  + '<button class="btn sm" id="dllCam" title="caméra : suivre la case de la bulle qui parle">🎥</button>\'''')
# charger les cases a l'ouverture
rep('''  Object.assign(DLL, { d, doc: e.doc, dist: e.distribution || {}, liste, i: Math.max(0, Math.min(liste.length - 1, depuis || 0)), page: null, pause: false });''',
    '''  Object.assign(DLL, { d, doc: e.doc, dist: e.distribution || {}, liste, i: Math.max(0, Math.min(liste.length - 1, depuis || 0)), page: null, pause: false, cases: null });
  let essais = 0;                                  // detection en cours cote serveur : on redemande (4 s, ~4 min au plus)
  const cases = () => api("/manga/cases?d=" + encodeURIComponent(d)).then(j => {
    if (DLL.d !== d || !j || j.error) return;
    DLL.cases = j; dllCamera(DLL.liste[DLL.i], true);
    if (j.calcul && ++essais < 60 && !dlgLec.hidden) setTimeout(cases, 4000);
  }).catch(() => {});
  cases();
  dllCamMaj();''')
# chaque replique : la camera va sur sa case (apres le halo)
rep('''  const jouer = () => {
    dllHalo(x);''', '''  const jouer = () => {
    dllHalo(x);
    dllCamera(x, true);''')
rep('''  if (DLL.page !== x.page){
    DLL.page = x.page;''', '''  if (DLL.page !== x.page){
    DLL.page = x.page;
    $("dllZoom").classList.remove("anim"); $("dllZoom").style.transform = "";      // nouvelle page : on repart de la page entiere''')
JS = r'''
/* ---- v2.81.2 : camera « suivre la case » du lecteur des Dialogues ---- */
let DLL_CAM = true; try { DLL_CAM = localStorage.getItem("manga_dlg_cam") !== "0"; } catch {}
function dllCamMaj(){ $("dllCam").classList.toggle("on", DLL_CAM); $("dllCam").style.opacity = DLL_CAM ? 1 : .45;
  $("dllCam").title = DLL_CAM ? "caméra : suit la case (toucher = page entière)" : "page entière (toucher = suivre la case)"; }
$("dllCam").onclick = () => { DLL_CAM = !DLL_CAM; try { localStorage.setItem("manga_dlg_cam", DLL_CAM ? "1" : "0"); } catch {}
  dllCamMaj(); dllCamera(DLL.liste[DLL.i], true); };
function dllCaseDe(x){
  const pg = DLL.cases && DLL.cases.pages && DLL.cases.pages[x.file];
  if (!pg || !pg.cases || !pg.cases.length || !pg.W) return null;
  const b = x.box, cx = (b.x + b.w / 2) * pg.W, cy = (b.y + b.h / 2) * pg.H;
  let best = null, dmin = Infinity;
  pg.cases.forEach(c => {
    const d = Math.hypot(Math.max(c[0] - cx, 0, cx - c[2]), Math.max(c[1] - cy, 0, cy - c[3]));
    if (d < dmin){ dmin = d; best = c; }
  });
  if (!best) return null;
  // fractions de la page ; la case est elargie a la bulle entiere (une bulle deborde souvent de sa case)
  const xs = x.contour && x.contour.length ? x.contour.map(p => p[0]) : [b.x, b.x + b.w], ys = x.contour && x.contour.length ? x.contour.map(p => p[1]) : [b.y, b.y + b.h];
  const q = DLL.pastille || { x1: 1, y1: 1, x2: 0, y2: 0 };             // + la pastille du nom
  return { x1: Math.min(best[0] / pg.W, q.x1, ...xs), y1: Math.min(best[1] / pg.H, q.y1, ...ys),
           x2: Math.max(best[2] / pg.W, q.x2, ...xs), y2: Math.max(best[3] / pg.H, q.y2, ...ys) };
}
function dllCamera(x, anim){
  const z = $("dllZoom"); if (!z || !x) return;
  const r = DLL_CAM ? dllCaseDe(x) : null, cw = $("dllCadre").clientWidth, ch = $("dllCadre").clientHeight;
  z.classList.toggle("anim", !!anim);
  if (!r || !cw || !ch){ z.style.transform = ""; return; }
  const m = 0.03, x1 = Math.max(0, r.x1 - m), y1 = Math.max(0, r.y1 - m), x2 = Math.min(1, r.x2 + m), y2 = Math.min(1, r.y2 + m);
  let k = Math.min(1 / (x2 - x1), 1 / (y2 - y1));
  k = Math.max(1, Math.min(3, k));
  let tx = cw / 2 - (x1 + x2) / 2 * cw * k, ty = ch / 2 - (y1 + y2) / 2 * ch * k;
  tx = Math.min(0, Math.max(cw - cw * k, tx)); ty = Math.min(0, Math.max(ch - ch * k, ty));
  z.style.transform = "translate(" + tx.toFixed(1) + "px," + ty.toFixed(1) + "px) scale(" + k.toFixed(3) + ")";
}
window.addEventListener("resize", () => { if (!dlgLec.hidden) dllCamera(DLL.liste[DLL.i], false); });
'''
# la pastille du nom doit rester dans le cadre de la camera (vu a l'oeil 27/09 00h55 : « emme moustique » coupe a 360 px)
rep("""  const px = Math.max(4, Math.min(W - lw - 4, cx - lw / 2)), py = Math.max(4, haut - ph - fs * 0.5);""",
    """  const px = Math.max(4, Math.min(W - lw - 4, cx - lw / 2)), py = Math.max(4, haut - ph - fs * 0.5);
  DLL.pastille = { x1: px / W, y1: py / H, x2: (px + lw) / W, y2: (py + ph) / H };""")
# v2.81.2 aussi : chapitre en FRANCAIS D'ORIGINE (Quang 00h47, Solo Leveling) -- la page affichee = img_rel (page d'origine),
# plus toujours traduction/fr/
rep("""    img.src = srcURL(DLL.d + "/traduction/fr/" + x.file);""",
    """    img.src = srcURL(DLL.d + "/" + (x.img_rel || "traduction/fr/" + x.file));""")
rep("document.body.appendChild($(\"coutsModal\"));", JS + NL + "document.body.appendChild($(\"coutsModal\"));")
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("app patchee v2.81.2 (camera)")
