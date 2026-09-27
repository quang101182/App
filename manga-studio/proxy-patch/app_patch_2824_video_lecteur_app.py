# -*- coding: utf-8 -*-
"""v2.82.4 (27/09, R7 -- Quang 03h41 : « le lecteur video ne respecte pas du tout l'autre lecteur video. Il regarde comment il
est fait, il fait pareil » ; 03h44 : « si d'autres videos sont presentes dans le manga, il faudra passer a la video suivante quand
meme […] precedente et suivante ») : les videos des Dialogues s'ouvrent dans LE lecteur video de l'app (#vidLecteur : « ← Fermer »,
titre, ⋯ vitesse / plein ecran, barre de temps, −10 / ⏸ / +10, gestes, position reprise) au lieu d'un <video> aux commandes du
navigateur. ⏮ / ⏭ et l'enchainement de fin (5 s, Annuler / Maintenant) parcourent les VIDEOS DE DIALOGUES de la serie (par
chapitre, puis par portee) -- jamais celles de la narration, qui gardent leur propre liste. Suppose app_patch_2823. Rejouable."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v2.82.4" in s[:400]:
    print("deja applique"); sys.exit(0)
if "v2.82.3" not in s[:400]:
    print("ERREUR : appliquer d'abord app_patch_2823_prep_modal.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


# --- le lecteur video de l'app sait parcourir une AUTRE liste : les videos de dialogues de la serie
rep("""function vidVoisin(sens){
""", """function vidVoisin(sens){
  if (VID.dlg){ const k = VID.dlg.i + sens, L = VID.dlg.liste;                 // v2.82.4 (R7) : videos de DIALOGUES de la serie
    return k >= 0 && k < L.length ? { i: k, c: { chapitre: L[k].label }, sautes: [], trou: null } : null; }
""")
rep("""    if (k <= 0){ vidSuiteStop(); vidOuvrir(n.i); } }, 1000);""", """    if (k <= 0){ vidSuiteStop(); vidAller(n.i); } }, 1000);""")
rep("""$("vidLecPrev").onclick = () => { const v = vidVoisin(-1); if (v) vidOuvrir(v.i); };
$("vidLecNext").onclick = () => { const v = vidVoisin(1); if (v) vidOuvrir(v.i); };""",
    """$("vidLecPrev").onclick = () => { const v = vidVoisin(-1); if (v) vidAller(v.i); };
$("vidLecNext").onclick = () => { const v = vidVoisin(1); if (v) vidAller(v.i); };
function vidAller(i){ if (VID.dlg) dlgVidIdx(i); else vidOuvrir(i); }            // v2.82.4 : narration OU dialogues, chacun sa liste""")
rep("""  if (VID.cour && !$("vidLecteur").hidden) vidPosSauver();                 // D : la position du chapitre quitte est gardee""",
    """  if (VID.cour && !$("vidLecteur").hidden) vidPosSauver();                 // D : la position du chapitre quitte est gardee
  VID.dlg = null;                                                          // v2.82.4 : une video de NARRATION -> la liste de la narration""")
# --- les videos des dialogues : la liste de la serie, puis LE lecteur de l'app
rep("""function dlgVidMontrer(v, d){
  const c = CHAPS.find(y => y.dir === (d || CHAP_OPEN));
  $("dlgVidTitre").textContent = "🎭 Dialogues" + (c ? " · ch. " + c.chapter : "") + (v.portee && v.portee !== "tout" ? " · p. " + v.portee : "");
  $("dlgVidEl").src = dlgVidUrl(v, false);
  dlgVidBox.hidden = false; $("dlgVidEl").play().catch(() => {});
}""", """async function dlgVidListe(serie){               // v2.82.4 : toutes les videos de DIALOGUES de la serie, par chapitre puis par portee
  const out = [];
  const chs = CHAPS.filter(c => serieDe(c.dir) === serie && RESUME && (RESUME.chapitres[c.dir] || {}).dlg).sort((a, b) => chapNum(a) - chapNum(b));
  for (const c of chs){
    let e, p;
    try { [e, p] = await Promise.all([api("/manga/dialogues?d=" + encodeURIComponent(c.dir)), api("/manga/dialogues_plan?d=" + encodeURIComponent(c.dir)).catch(() => null)]); }
    catch (err) { continue; }
    const vids = dlgVideos((e || {}).doc, p);
    Object.keys(vids).sort((a, b) => (a === "tout" ? -1 : b === "tout" ? 1 : parseInt(a) - parseInt(b)))
      .forEach(k => out.push({ d: c.dir, v: vids[k].v, label: c.chapter + (k === "tout" ? "" : " · p. " + k) }));
  }
  return out;
}
async function dlgVidMontrer(v, d){              // v2.82.4 (R7) : LE lecteur video de l'app (#vidLecteur), pas un autre
  const dir = d || CHAP_OPEN;
  let liste = [];
  try { liste = await dlgVidListe(serieDe(dir)); } catch (err) {}
  let i = liste.findIndex(x => x.v.fichier === v.fichier);
  if (i < 0){ const c = CHAPS.find(y => y.dir === dir); liste = [{ d: dir, v, label: (c ? c.chapter : "") + (v.portee && v.portee !== "tout" ? " · p. " + v.portee : "") }]; i = 0; }
  VID.dlg = { liste, i };
  dlgVidIdx(i);
}
function dlgVidIdx(i){
  const x = VID.dlg && VID.dlg.liste[i]; if (!x) return;
  if (VID.cour && !$("vidLecteur").hidden) vidPosSauver();
  vidSuiteStop();
  VID.dlg.i = i; VID_COUR = -1;
  if (document.activeElement && document.activeElement.blur) document.activeElement.blur();   // un champ reste derriere : les touches vont au lecteur
  const v = x.v, c = CHAPS.find(y => y.dir === x.d);
  VID.cour = { fichier: v.fichier, tag: "dialogues", v: v.t || "" };
  $("vidLecTitre").textContent = "🎭 " + (c ? c.title + " — ch. " + c.chapter : "Dialogues") + (v.portee && v.portee !== "tout" ? " · p. " + v.portee : "");
  const e = vEl(), pos = (((typeof BIB !== "undefined" && BIB.videos_pos) || {})[v.fichier] || {}).pos || 0;
  e.src = dlgVidUrl(v, false);
  e.onloadedmetadata = () => { e.playbackRate = VID.vit; if (pos && pos < e.duration - 10){ e.currentTime = pos; toast("reprise à " + vidFmt(pos)); } vidTempsMaj(); };
  $("vidLecteur").hidden = false; e.play().catch(() => {});
  vidNavMaj(); vidReveil();
}""")
rep("""  $("vidSuiteOui").onclick = () => { const n = vidVoisin(1); vidSuiteStop(); if (n) vidOuvrir(n.i); };""",
    """  $("vidSuiteOui").onclick = () => { const n = vidVoisin(1); vidSuiteStop(); if (n) vidAller(n.i); };""")
rep("""  if (!$("vidLecteur").hidden) return selCtxVideo();""",
    """  if (!$("vidLecteur").hidden && VID.dlg) return { titre: "Dialogues — aller à la vidéo", quoi: "vidéo", filtres: [],   // v2.82.4
      items: VID.dlg.liste.map((x, k) => ({ cle: "v" + k, num: k + 1, label: x.label, classe: k === VID.dlg.i ? "cour" : "", k })),
      choisir: it => dlgVidIdx(it.k) };
  if (!$("vidLecteur").hidden) return selCtxVideo();""")
s = s.replace("<title>Manga Studio v2.82.3</title>", "<title>Manga Studio v2.82.4</title>", 1)
s = s.replace('id="verBadge">v2.82.3<', 'id="verBadge">v2.82.4<', 1)
s = s.replace('const VERSION = "2.82.3";', 'const VERSION = "2.82.4";   // v2.82.4 : les videos des Dialogues dans le lecteur video de l app, precedente / suivante (R7)', 1)
assert s.count("2.82.4") >= 4
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
