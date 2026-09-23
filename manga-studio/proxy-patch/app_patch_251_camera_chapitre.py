# -*- coding: utf-8 -*-
"""Manga Studio v2.5.1 (23/09/2026) : le choix de camera DANS le chapitre (bloc 🎬 Video) et dans le panneau 🎬 Videos.

Quang (08h51) : « quand je suis dans un chapitre, je n'ai pas le choix, case par case ou l'autre. C'est seulement le
batch qui les possede. » -> un selecteur [🎥 Case par case | Page entiere] a cote de la video. Meme reglage que la case
🎥 du lecteur et le profil : c'est le choix de la SERIE (lecteur + videos), enregistre au clic (/manga/camera).
Rejouable : python app_patch_251_camera_chapitre.py <manga_studio.html>.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "v2.5.1 : camera dans le chapitre" in s:
    print("deja patche"); sys.exit(0)


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


for a in ("<title>Manga Studio v2.5.0</title>", 'id="verBadge">v2.5.0</span>', 'const VERSION = "2.5.0";'):
    rep(a, a.replace("2.5.0", "2.5.1"))
rep('''.seg button.on{background:color-mix(in srgb, var(--accent2) 22%, transparent);color:var(--txt)}''',
    '''.seg button.on{background:color-mix(in srgb, var(--accent2) 22%, transparent);color:var(--txt)}
.vid-cam{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:4px 0 6px;font-size:12px}''')
rep('''    <p class="muted vid-reg" id="vidReg"></p>''',
    '''    <div class="vid-cam" id="vidCamSerie"></div>
    <p class="muted vid-reg" id="vidReg"></p>''')
rep('''  $("chapVid").innerHTML = ci >= 0 ? '<div class="bloc-titre">🎬 Vidéo</div>' + vidLigne(VIDS.chapitres[ci], ci, false) : "";''',
    '''  $("chapVid").innerHTML = ci >= 0 ? '<div class="bloc-titre">🎬 Vidéo</div>' + vidCamHtml() + vidLigne(VIDS.chapitres[ci], ci, false) : "";
  $("vidCamSerie").innerHTML = vidCamHtml();''')
rep('''$("vidListe").onclick = vidClic; $("chapVid").onclick = vidClic;''',
    '''// v2.5.1 : camera dans le chapitre (Quang 08h51 : « je n'ai pas le choix [...] seulement le batch »). Choix de la SERIE.
function vidCamHtml(){
  const m = camModeDe(VIDS.serie);
  return '<div class="vid-cam"><span>Caméra</span><span class="seg">'
    + [["cases", "🎥 Case par case"], ["page", "Page entière"]].map(([k, t]) =>
      '<button data-vid-cam="' + k + '"' + (k === m ? ' class="on"' : "") + ">" + t + "</button>").join("")
    + '</span><span class="muted">pour toute la série (lecteur et vidéos)</span></div>';
}
async function vidCamChoisir(e){
  const b = e.target.closest("[data-vid-cam]"); if (!b || !VIDS.serie) return false;
  const mode = b.dataset.vidCam; if (mode === camModeDe(VIDS.serie)) return true;
  try { const r = await api("/manga/camera", { serie: VIDS.serie, camera: mode }); if (r.error) throw new Error(r.error);
        CAM_SERIES[VIDS.serie] = mode; if (SUIVI && SUIVI._serie === VIDS.serie) SUIVI._rendu = false;
        toast("🎥 " + (mode === "cases" ? "case par case" : "page entière") + " — mémorisé pour la série (lecteur et vidéos)");
        vidRendre(); }
  catch (err){ log("caméra : " + err.message, "e"); alert(err.message); }
  return true;
}
$("vidListe").onclick = vidClic;
$("chapVid").onclick = async e => { if (!(await vidCamChoisir(e))) vidClic(e); };
$("vidCamSerie").onclick = vidCamChoisir;''')
rep('        toast("🎥 " + (mode === "cases" ? "case par case" : "page entière") + " — mémorisé pour la série (lecteur et vidéos)"); }\n  catch (err){ log("caméra : " + err.message, "e"); }\n};',
    '        toast("🎥 " + (mode === "cases" ? "case par case" : "page entière") + " — mémorisé pour la série (lecteur et vidéos)");\n        if (VIDS.serie === serie) vidRendre(); }                                                // v2.5.1 : le bloc 🎬 du chapitre suit\n  catch (err){ log("caméra : " + err.message, "e"); }\n};')
open(p, "w", encoding="utf-8").write(s)
print("patche")
