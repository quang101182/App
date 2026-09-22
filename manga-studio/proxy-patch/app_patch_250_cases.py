# -*- coding: utf-8 -*-
"""Manga Studio v2.5.0 (23/09/2026) : camera « case par case » dans le LECTEUR, le profil de serie et les videos.

Decision Quang : mode par defaut pour tous les formats, « page entiere » au choix ; le lecteur fait comme la video
(« oui, lecteur aussi », 23/09). La regle est scripts/cases_video.py ; camPlan / camPose en sont le miroir JS.
Rejouable : python app_patch_250_cases.py <manga_studio.html>.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "v2.5.0 : CAMERA" in s:
    print("deja patche")
    sys.exit(0)


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


for a in ("<title>Manga Studio v2.4.6</title>", 'id="verBadge">v2.4.6</span>', 'const VERSION = "2.4.6";'):
    rep(a, a.replace("2.4.6", "2.5.0"))

# ---------------------------------------------------------------- CSS
rep('''@keyframes lecKb2{from{transform:scale(1.07) translateY(1.5%)}to{transform:scale(1)}}''',
    '''@keyframes lecKb2{from{transform:scale(1.07) translateY(1.5%)}to{transform:scale(1)}}
/* v2.5.0 : camera « case par case » -- l'image a sa taille naturelle, la camera la deplace (translate + scale) */
.lec-scene{position:relative}
.lec-scene img.cam{position:absolute;left:0;top:0;max-width:none;max-height:none;transform-origin:0 0;will-change:transform}
.lec-scene img.fondu{animation:lecFondu .3s linear}
@keyframes lecFondu{from{opacity:0}to{opacity:1}}
.lec-voile{position:absolute;left:0;top:0;pointer-events:none}
.lec-voile[hidden]{display:none}''')

# ---------------------------------------------------------------- HTML
rep('''  <div class="lec-scene"><img id="lecImg" alt=""></div>''',
    '''  <div class="lec-scene"><img id="lecImg" alt=""><div class="lec-voile" id="lecVoile" hidden></div></div>''')
rep('''    <label class="lec-chk" title="le mot prononcé s'allume"><input type="checkbox" id="lecKarOn"> karaoké</label>''',
    '''    <label class="lec-chk" title="le mot prononcé s'allume"><input type="checkbox" id="lecKarOn"> karaoké</label>
    <label class="lec-chk" title="la caméra passe de case en case (sinon : la page entière). Mémorisé pour la série : lecteur ET vidéos"><input type="checkbox" id="lecCamOn" checked> 🎥 cases</label>''')
rep('''      <label><input type="checkbox" id="suiviVid"> fabriquer</label>''',
    '''      <label><input type="checkbox" id="suiviVid"> fabriquer</label>
      <label title="lecteur ET vidéos de cette série : la caméra passe de case en case, ou montre la page entière">caméra <select id="profCam"><option value="cases">case par case</option><option value="page">page entière</option></select></label>''')

# ---------------------------------------------------------------- etapes d'activite
rep('''                    images: "images", son: "son", assemblage: "assemblage", attente: "en attente",''',
    '''                    images: "images", son: "son", assemblage: "assemblage", attente: "en attente", cases: "détection des cases",''')

# ---------------------------------------------------------------- reglages video
rep('''           precedemment: (() => { try { return PREC_ON; } catch { return true; } })() };''',
    '''           precedemment: (() => { try { return PREC_ON; } catch { return true; } })(),
           camera: camModeDe(VIDS.serie || serieDe(CHAP_OPEN)) };                          // v2.5.0''')
rep('''function reglagesLecteur(){''',
    '''// v2.5.0 : la camera de chaque serie (profil ; « cases » par defaut). Declare ICI : reglagesLecteur s'en sert.
const CAM_SERIES = {};
function camModeDe(serie){ return CAM_SERIES[serie] === "page" ? "page" : "cases"; }
function reglagesLecteur(){''')
rep('''  .concat(r.precedemment ? ["📜 précédemment"] : []).join(" · ");''',
    '''  .concat(r.precedemment ? ["📜 précédemment"] : []).concat([r.camera === "cases" ? "🎥 case par case" : "page entière"]).join(" · ");''')
rep('''  if (!!r.precedemment !== !!cur.precedemment) d.push("« Précédemment… »");''',
    '''  if (!!r.precedemment !== !!cur.precedemment) d.push("« Précédemment… »");
  if ((r.camera || "page") !== (cur.camera || "page")) d.push("caméra");                  // v2.5.0 : une video d'avant = page''')
rep('''  VIDS = Object.assign(await api("/manga/videos?serie=" + encodeURIComponent(serie)), { serie });''',
    '''  VIDS = Object.assign(await api("/manga/videos?serie=" + encodeURIComponent(serie)), { serie });
  if (VIDS.camera) CAM_SERIES[serie] = VIDS.camera;                                         // v2.5.0''')

# ---------------------------------------------------------------- profil de serie
rep('''  $("profVol").value = rv.volume != null ? rv.volume : 25;''',
    '''  $("profVol").value = rv.volume != null ? rv.volume : 25;
  $("profCam").value = rv.camera === "page" ? "page" : "cases";                             // v2.5.0
  if (LIB_SERIE) CAM_SERIES[LIB_SERIE] = $("profCam").value;''')
rep('''                             musique: $("profMusOn").checked, volume: +$("profVol").value, pages: "", precedemment: $("suiviPrec").checked } };''',
    '''                             musique: $("profMusOn").checked, volume: +$("profVol").value, pages: "", precedemment: $("suiviPrec").checked,
                             camera: $("profCam").value } };''')
rep('''["suiviMoteur", "suiviVoix", "profTrad", "suiviKar", "suiviPrec", "suiviVid", "profVit", "profSous", "profMusOn", "profVol"]''',
    '''["suiviMoteur", "suiviVoix", "profTrad", "suiviKar", "suiviPrec", "suiviVid", "profVit", "profSous", "profMusOn", "profVol", "profCam"]''')
rep('''    + (d.traduction ? " · traduction " + (LANGUE_NOM[d.traduction] || d.traduction) : "") + (d.video ? " · vidéo" : "");''',
    '''    + (d.traduction ? " · traduction " + (LANGUE_NOM[d.traduction] || d.traduction) : "") + (d.video ? " · vidéo" : "")
    + ((d.reglages_video || {}).camera === "page" ? " · page entière" : " · case par case");''')
rep('''                c.video ? "vidéo" + (c.reglages_video.musique ?''',
    '''                c.video ? "vidéo " + (c.reglages_video.camera === "page" ? "page entière" : "case par case") + (c.reglages_video.musique ?''')

# ---------------------------------------------------------------- hors-ligne : les cases partent avec la narration
rep('''  let prec = null;
  try { prec = await api("/manga/precedemment?d=" + encodeURIComponent(d)); } catch {}''',
    '''  try { const cs = await api("/manga/cases?d=" + encodeURIComponent(d));                     // v2.5.0
        if (cs && !cs.calcul && !cs.error) urls.push(CFG.base + "/manga/cases?d=" + encodeURIComponent(d)); } catch {}
  let prec = null;
  try { prec = await api("/manga/precedemment?d=" + encodeURIComponent(d)); } catch {}''')

# ---------------------------------------------------------------- lecteur
rep('''  log("lecteur : " + (LEC.aveugle ? "aveugle " + LETTRES[LEC.iFile] : tag) + " (" + LEC.n.pages.length + " pages)");
  montrerPage();''',
    '''  log("lecteur : " + (LEC.aveugle ? "aveugle " + LETTRES[LEC.iFile] : tag) + " (" + LEC.n.pages.length + " pages)");
  await camCharger(CHAP_OPEN).catch(e => log("caméra : " + e.message, "w"));             // v2.5.0
  montrerPage();''')
rep('''  img.style.setProperty("--kb", Math.max(4, (p.dur || 3) / (+$("lecVit").value) + 1) + "s");
  img.classList.add(LEC.i % 2 ? "kb2" : "kb");''',
    '''  img.style.setProperty("--kb", Math.max(4, (p.dur || 3) / (+$("lecVit").value) + 1) + "s");
  if (!camPage(p)) img.classList.add(LEC.i % 2 ? "kb2" : "kb");                            // v2.5.0 : sinon la camera''')
rep('''$("lecAudio").onended = () => { if (LEC.playing) LEC.timer = setTimeout(pageSuivante, 450); };''',
    '''$("lecAudio").onended = () => { CAM.finAudio = performance.now(); if (LEC.playing) LEC.timer = setTimeout(pageSuivante, 450); };
$("lecAudio").addEventListener("play", () => { CAM.finAudio = 0; });                        // v2.5.0 : relu apres la fin
$("lecAudio").addEventListener("seeked", () => { if (!$("lecAudio").ended) CAM.finAudio = 0; });''')
rep('''$("lecKarOn").onchange = () => {''',
    '''// ---------- v2.5.0 : CAMERA « case par case » (decision Quang 22-23/09 : defaut pour tous les formats) ----------
// MIROIR de scripts/cases_video.py (plan / pose) : la video et le lecteur font le MEME trajet -> a garder identique.
// Les cases viennent du proxy (/manga/cases : cache par chapitre, detection YOLO lancee s'il en manque). Tant qu'une
// page n'a pas ses cases (ou pour le « Precedemment... »), le lecteur montre la page entiere avec le zoom lent.
const CAM = { d: null, data: null, raf: 0, finAudio: 0, debut: 0, essai: null, n: 0 };
const CAM_APERCU = 0.10, CAM_GLISSE = 0.5, CAM_ZOOM = 1.035, CAM_PAD = 0.035, CAM_VOILE = 170 / 255;
function camCadre(b, A, pad){
  if (pad == null) pad = CAM_PAD;
  let [x0, y0, x1, y1] = b, w = x1 - x0, h = y1 - y0;
  x0 -= w * pad; x1 += w * pad; y0 -= h * pad; y1 += h * pad; w = x1 - x0; h = y1 - y0;
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
  if (w / h < A) w = h * A; else h = w / A;
  return [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2];
}
const camLisse = u => { u = Math.min(1, Math.max(0, u)); return u * u * (3 - 2 * u); };
const camMel = (a, b, u) => a.map((x, i) => x + (b[i] - x) * u);
function camZoome(r, k){
  const cx = (r[0] + r[2]) / 2, cy = (r[1] + r[3]) / 2, w = (r[2] - r[0]) / k, h = (r[3] - r[1]) / k;
  return [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2];
}
function camPlan(e, fmt, A, T){
  const W = e.W, H = e.H, bs = e.cases || [], page = camCadre([0, 0, W, H], A, 0);
  if (fmt === "webtoon"){
    const b = bs[0] || [0, 0, W, H], hv = W / A;
    if (b[3] - b[1] > hv * 1.02) return { type: "defile", T, de: [0, b[1], W, b[1] + hv], vers: [0, b[3] - hv, W, b[3]], case: b };
    return { type: "fixe", T, r: camCadre(b, A, 0.02), z: 1.04, case: b };
  }
  if (bs.length <= 1) return { type: "fixe", T, r: page, z: 1.06, case: null };
  const t0 = Math.min(1, CAM_APERCU * T), aires = bs.map(b => Math.sqrt((b[2] - b[0]) * (b[3] - b[1])));
  const tot = aires.reduce((a, b) => a + b, 0);
  let t = t0;
  const segs = bs.map((b, i) => { const d = (T - t0) * aires[i] / tot, sg = { a: t, b: t + d, r: camCadre(b, A), case: b }; t += d; return sg; });
  return { type: "cases", T, page, apercu: t0, segs };
}
function camPose(pl, t){
  const T = pl.T;
  if (pl.type === "defile") return [camMel(pl.de, pl.vers, camLisse((t / T - 0.12) / 0.76)), pl.case, 1];
  if (pl.type === "fixe") return [camZoome(pl.r, 1 + (pl.z - 1) * Math.min(1, Math.max(0, t / T))), pl.case, pl.case ? 1 : 0];
  if (t < pl.apercu) return [pl.page, null, 0];
  const segs = pl.segs; let k = 0;
  while (k < segs.length - 1 && t >= segs[k].b) k++;
  const sg = segs[k], u = Math.min(1, Math.max(0, (t - sg.a) / Math.max(0.01, sg.b - sg.a)));
  const r = camZoome(sg.r, 1 + (CAM_ZOOM - 1) * u), g = Math.min(CAM_GLISSE, (sg.b - sg.a) / 2);
  if (t - sg.a < g){
    const e = camLisse((t - sg.a) / g);
    if (k === 0) return [camMel(pl.page, r, e), sg.case, e];
    const pr = segs[k - 1];
    return [camMel(camZoome(pr.r, CAM_ZOOM), r, e), camMel(pr.case, sg.case, e), 1];
  }
  return [r, sg.case, 1];
}
async function camCharger(d){
  clearTimeout(CAM.essai);
  if (CAM.d !== d){ CAM.d = d; CAM.data = null; CAM.n = 0; }
  const j = await api("/manga/cases?d=" + encodeURIComponent(d));
  if (!j || j.error || CAM.d !== d) return;
  CAM.data = j; CAM_SERIES[serieDe(d)] = j.camera === "page" ? "page" : "cases";
  $("lecCamOn").checked = camModeDe(serieDe(d)) === "cases";
  // detection en cours : on redemande (au plus ~4 min), la page en cours passe en mode cases des qu'elle est prete
  if (j.calcul && ++CAM.n < 60) CAM.essai = setTimeout(() => {
    if ($("lecteur").hidden || CAM.d !== d) return;
    camCharger(d).then(() => { const p = LEC.n && LEC.n.pages[LEC.i]; if (p && !$("lecImg").classList.contains("cam") && camEntree(p)) montrerPageCam(p); })
      .catch(() => {});
  }, 4000);
  if (j.calcul && CAM.n === 1) log("caméra : détection des cases en cours pour " + d + " (" + j.manquantes + " page(s))");
  if (j.echec) log("caméra : la détection des cases a échoué (voir sources/_suivi/cases.log) : page entière", "w");
}
function camEntree(p){
  if (!p || p.prec || p.img || !CAM.data || CAM.d !== CHAP_OPEN || camModeDe(serieDe(CHAP_OPEN)) !== "cases") return null;
  return (CAM.data.pages || {})[p.file] || null;
}
// true = la camera prend la page ; false = page entiere (zoom lent kb/kb2, comme avant)
function camPage(p){
  cancelAnimationFrame(CAM.raf);
  const img = $("lecImg"), e = camEntree(p);
  CAM.debut = performance.now(); CAM.finAudio = 0;
  if (!e){
    img.classList.remove("cam", "fondu"); img.style.width = img.style.height = img.style.transform = "";
    $("lecVoile").hidden = true; return false;
  }
  img.classList.remove("kb", "kb2"); img.classList.add("cam");
  if (CAM.data.format === "webtoon" && LEC.i > 0){ img.classList.remove("fondu"); void img.offsetWidth; img.classList.add("fondu"); }
  camTick(); return true;
}
function montrerPageCam(p){                // bascule en cours de page, sans relancer la voix
  const img = $("lecImg");
  img.classList.remove("kb", "kb2"); void img.offsetWidth;
  const d = performance.now() - CAM.debut, fa = CAM.finAudio;
  if (!camPage(p)) img.classList.add(LEC.i % 2 ? "kb2" : "kb");
  CAM.debut = performance.now() - d; CAM.finAudio = fa;
}
// l'instant t de la page et sa duree T, dans le temps de la VIDEO (voix / vitesse + 0,45 s ; muette 2,5 s)
function camTemps(p){
  const v = +$("lecVit").value || 1, a = $("lecAudio");
  if (!p.audio) return [(performance.now() - CAM.debut) / 1000, 2.5];
  const voix = (p.dur || 3) / v;
  if (CAM.finAudio) return [voix + (performance.now() - CAM.finAudio) / 1000, voix + 0.45];
  return [(a.currentTime || 0) / v, voix + 0.45];
}
function camTick(){
  cancelAnimationFrame(CAM.raf);
  if ($("lecteur").hidden || !LEC.n) return;
  const p = LEC.n.pages[LEC.i], e = camEntree(p), img = $("lecImg");
  if (!e || !img.classList.contains("cam")) return;
  const sc = img.parentElement, sw = sc.clientWidth, sh = sc.clientHeight;
  if (sw > 0 && sh > 0){
    const pret = img.complete && img.naturalWidth, nw = pret ? img.naturalWidth : e.W, nh = pret ? img.naturalHeight : e.H;
    const sx = nw / e.W, sy = nh / e.H;          // page traduite : meme dessin, autre taille
    const ee = sx === 1 && sy === 1 ? e : { W: nw, H: nh, cases: (e.cases || []).map(b => [b[0] * sx, b[1] * sy, b[2] * sx, b[3] * sy]) };
    const [t, T] = camTemps(p), [cam, cs, a] = camPose(camPlan(ee, CAM.data.format, sw / sh, T), t);
    const k = sw / (cam[2] - cam[0]);
    img.style.width = nw + "px"; img.style.height = nh + "px";
    img.style.transform = "translate(" + (-cam[0] * k).toFixed(1) + "px," + (-cam[1] * k).toFixed(1) + "px) scale(" + k.toFixed(5) + ")";
    const vl = $("lecVoile");
    if (cs && a > 0){
      vl.hidden = false;
      vl.style.left = ((cs[0] - cam[0]) * k).toFixed(1) + "px"; vl.style.top = ((cs[1] - cam[1]) * k).toFixed(1) + "px";
      vl.style.width = ((cs[2] - cs[0]) * k).toFixed(1) + "px"; vl.style.height = ((cs[3] - cs[1]) * k).toFixed(1) + "px";
      vl.style.boxShadow = "0 0 0 200vmax rgba(5,6,8," + (CAM_VOILE * a).toFixed(3) + ")";
    } else vl.hidden = true;
  }
  CAM.raf = requestAnimationFrame(camTick);
}
$("lecCamOn").onchange = async () => {
  const serie = serieDe(CHAP_OPEN), mode = $("lecCamOn").checked ? "cases" : "page";
  $("lecCamOn").blur();
  CAM_SERIES[serie] = mode;
  const p = LEC.n && LEC.n.pages[LEC.i];
  if (mode === "cases" && !CAM.data) await camCharger(CHAP_OPEN).catch(() => {});
  if (p) montrerPageCam(p);
  try { const r = await api("/manga/camera", { serie, camera: mode }); if (r.error) throw new Error(r.error);
        toast("🎥 " + (mode === "cases" ? "case par case" : "page entière") + " — mémorisé pour la série (lecteur et vidéos)"); }
  catch (err){ log("caméra : " + err.message, "e"); }
};
window.addEventListener("resize", () => { if (!$("lecteur").hidden) camTick(); });
$("lecKarOn").onchange = () => {''')
open(p, "w", encoding="utf-8").write(s)
print("patche")
