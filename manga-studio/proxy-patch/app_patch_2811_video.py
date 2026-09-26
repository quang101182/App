# -*- coding: utf-8 -*-
"""Manga Studio v2.81.1 -- VIDEO des Dialogues dans l'app (ROADMAP 4-septdecies D7). A appliquer apres app_patch_2810_dialogues.py
et app_patch_2810b_lecteur.py. Dans la ligne Dialogues (decision 26/09 : la video des dialogues reste DANS les Dialogues, la ligne
🎬 Vidéo reste celle de la narration) : « 🎬 Vidéo » (fabriquer / refaire si perimee), « ▶ Voir », « ⬇ Télécharger ».
Rejouable : python app_patch_2811_video.py <manga_studio.html>"""
import io, sys

P = sys.argv[1]
s = io.open(P, encoding="utf-8", newline="").read()
if "function dlgLecteur(" not in s:
    print("ERREUR : appliquer d'abord app_patch_2810_dialogues.py et app_patch_2810b_lecteur.py"); sys.exit(1)
if "dlgVidVoir" in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"


def rep(a, b, n=1):
    global s
    a, b = a.replace("\n", NL), b.replace("\n", NL)
    assert s.count(a) == n, ("ancre", s.count(a), a[:90])
    s = s.replace(a, b)


rep("<title>Manga Studio v2.81.0</title>", "<title>Manga Studio v2.81.1</title>")
rep('id="verBadge">v2.81.0</span>', 'id="verBadge">v2.81.1</span>')
rep('const VERSION = "2.81.0";', 'const VERSION = "2.81.1";   // v2.81.1 : video des Dialogues (MP4) ; v2.81.0 : mode « Dialogues »')
rep('''        <button class="btn sm" id="dlgArreter" hidden>✖ Arrêter</button>''',
    '''        <button class="btn sm" id="dlgArreter" hidden>✖ Arrêter</button>
        <button class="btn sm" id="dlgVid" title="vidéo des dialogues (MP4, pour le téléphone hors ligne)">🎬 Vidéo</button>
        <button class="btn sm" id="dlgVidVoir" hidden>▶ Voir la vidéo</button>
        <a class="btn sm" id="dlgVidDl" hidden>⬇ Télécharger</a>''')
rep('''  if (e.en_cours) return { etat: (pr.etape === "voix" ? "voix en cours" : "préparation en cours")''',
    '''  if (e.en_cours) return { etat: (pr.etape === "voix" ? "voix en cours" : pr.etape === "video" ? "vidéo en cours" : "préparation en cours")''')
rep('''  $("dlgLire").disabled = !(p && p.deja);''', '''  $("dlgLire").disabled = !(p && p.deja);
  // v2.81.1 : video des dialogues
  const v = (e.doc || {}).video, etv = p && p.video;
  $("dlgVid").disabled = occupe || !(p && p.deja);
  $("dlgVid").textContent = etv === "a_jour" ? "🎬 Refaire la vidéo" : etv === "perimee" ? "🎬 Mettre la vidéo à jour" : "🎬 Vidéo";
  $("dlgVid").classList.toggle("pri", etv === "perimee");
  $("dlgVidVoir").hidden = $("dlgVidDl").hidden = !v || etv === "absente";
  if (v) $("dlgVidDl").href = CFG.base + "/manga/video_file?p=" + encodeURIComponent(v.fichier) + "&dl=1&v=" + encodeURIComponent(v.t || "") + (CFG.key ? "&_k=" + encodeURIComponent(CFG.key) : "");''')
JS = r'''
/* ---- v2.81.1 : la VIDEO des Dialogues (D7) : fabriquee par dialogues.py video, lue ici ---- */
const dlgVidBox = document.createElement("div");
dlgVidBox.id = "dlgVidBox"; dlgVidBox.hidden = true;
dlgVidBox.style.cssText = "position:fixed;inset:0;z-index:90;background:#07080b;display:flex;flex-direction:column";
dlgVidBox.innerHTML = '<video id="dlgVidEl" controls playsinline style="flex:1;min-height:0;width:100%;background:#000"></video>'
  + '<div class="dlgl-barre"><span class="bulle" id="dlgVidTitre">🎭 Dialogues</span><span style="flex:1"></span><button class="btn sm retour" id="dlgVidFermer">← Fermer</button></div>';
document.body.appendChild(dlgVidBox);
new MutationObserver(() => { dlgVidBox.style.display = dlgVidBox.hidden ? "none" : "flex"; }).observe(dlgVidBox, { attributes: true, attributeFilter: ["hidden"] });
dlgVidBox.style.display = "none";
$("dlgVid").onclick = async () => {
  const p = DLG.plan;
  if (p && p.a_faire && !confirm(p.a_faire + " réplique(s) n'ont pas encore leur voix : la vidéo ne contiendra que les voix déjà faites. Continuer ?")) return;
  try { const r = await api("/manga/dialogues_lancer", { d: CHAP_OPEN, action: "video" }); if (r.error) throw new Error(r.error); toast("🎬 vidéo des dialogues lancée"); }
  catch (err) { toast("vidéo : " + err.message); }
  setTimeout(dlgCharger, 600);
};
$("dlgVidVoir").onclick = () => {
  const v = ((DLG.e || {}).doc || {}).video; if (!v) return;
  const c = CHAPS.find(y => y.dir === CHAP_OPEN);
  $("dlgVidTitre").textContent = "🎭 Dialogues" + (c ? " · ch. " + c.chapter : "");
  $("dlgVidEl").src = CFG.base + "/manga/video_file?p=" + encodeURIComponent(v.fichier) + "&v=" + encodeURIComponent(v.t || "") + (CFG.key ? "&_k=" + encodeURIComponent(CFG.key) : "");
  dlgVidBox.hidden = false; $("dlgVidEl").play().catch(() => {});
};
$("dlgVidFermer").onclick = () => { $("dlgVidEl").pause(); dlgVidBox.hidden = true; };
'''
rep("document.body.appendChild($(\"coutsModal\"));", JS + NL + "document.body.appendChild($(\"coutsModal\"));")
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("app patchee v2.81.1")
