# -*- coding: utf-8 -*-
"""v2.87.0 (27/09, R17 -- Quang 13h09 : « a chaque fois que je change la vitesse d'une voix, je suis oblige de la regenerer ? »,
13h10 : « oui » a la vitesse d'ECOUTE gratuite) : dans l'ecran ✏, chaque personnage a DEUX vitesses :
- « Vitesse de diction » (inchangee) : envoyee a ElevenLabs a la generation -- la changer = voix a refaire (credits) ;
- « 🎧 Vitesse d'écoute » (nouvelle, 0,7-1,5, defaut 1) : appliquee a la LECTURE (lecteur des Dialogues, ecoute d'essai) et au
  montage de la video (dialogues.py 1.14.0) ; hauteur de voix conservee ; aucune voix regeneree, aucun credit.
Lecture = vitesse generale du lecteur x ecoute du personnage qui parle. Suppose v2.86.0 (+ patch_dialogues_9 cote serveur).
Rejouable."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v2.87.0" in s[:400]:
    print("deja applique"); sys.exit(0)
if "v2.86.0" not in s[:400]:
    print("ERREUR : appliquer d'abord app_patch_2860_geste_bascule.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b, n=1):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == n, (a[:70], s.count(a))
    s = s.replace(a, b)


rep("<title>Manga Studio v2.86.0</title>", "<title>Manga Studio v2.87.0</title>")
rep('<span class="ver" id="verBadge">v2.86.0</span>', '<span class="ver" id="verBadge">v2.87.0</span>')
rep('const VERSION = "2.86.0";', 'const VERSION = "2.87.0";   // v2.87.0 : vitesse d ECOUTE par personnage, gratuite (lecture + video) (R17)')
# --- l'ecran ✏ : la 2e vitesse, sous la vitesse de diction
rep("""      + '<label>Vitesse de diction <b data-vit-v>' + Number(p.vitesse || 1.1).toFixed(2).replace(".", ",") + '</b></label><input type="range" data-k="vitesse" min="0.7" max="1.2" step="0.05" value="' + (p.vitesse || 1.1) + '" style="width:100%">'""",
    """      + '<label>Vitesse de diction <b data-vit-v>' + Number(p.vitesse || 1.1).toFixed(2).replace(".", ",") + '</b> <span class="muted">(à la génération : voix à refaire)</span></label><input type="range" data-k="vitesse" min="0.7" max="1.2" step="0.05" value="' + (p.vitesse || 1.1) + '" style="width:100%">'
      + '<label>🎧 Vitesse d\\'écoute <b data-ec-v>' + Number(p.ecoute || 1).toFixed(2).replace(".", ",") + '</b> <span class="muted">(gratuite : lecture et vidéo)</span></label><input type="range" data-k="ecoute" min="0.7" max="1.5" step="0.05" value="' + (p.ecoute || 1) + '" style="width:100%">'""")
rep("""    else m[k] = k === "vitesse" ? +e.target.value : e.target.value;""",
    """    else m[k] = k === "vitesse" || k === "ecoute" ? +e.target.value : e.target.value;   // v2.87.0 : ecoute""")
rep("""  if (e.target.dataset.k === "vitesse") e.target.closest(".dlgp-carte").querySelector("[data-vit-v]").textContent = Number(e.target.value).toFixed(2).replace(".", ",");""",
    """  if (e.target.dataset.k === "vitesse") e.target.closest(".dlgp-carte").querySelector("[data-vit-v]").textContent = Number(e.target.value).toFixed(2).replace(".", ",");
  if (e.target.dataset.k === "ecoute"){                                                   // v2.87.0 : l'essai en cours suit
    e.target.closest(".dlgp-carte").querySelector("[data-ec-v]").textContent = Number(e.target.value).toFixed(2).replace(".", ",");
    if (DLG.audio && !DLG.audio.paused) DLG.audio.playbackRate = +e.target.value;
  }""")
# --- la vitesse d'ecoute du personnage qui parle
rep("""function dlgCouleur(nom){""", """function dlgEcoute(nom){                          // v2.87.0 (R17) : vitesse d'ECOUTE (1 = telle que generee)
  const p = dlgPersos().find(x => x.nom === nom);
  return Math.max(0.7, Math.min(1.5, +((p && p.ecoute) || 1)));
}
function dlgCouleur(nom){""")
rep("""    DLL.audio.src = srcURL(DLL.d + "/dialogues/voix/" + x.voix.fichier);
    DLL.audio.playbackRate = +$("dllVit").value;""",
    """    DLL.audio.src = srcURL(DLL.d + "/dialogues/voix/" + x.voix.fichier);
    DLL.audio.playbackRate = +$("dllVit").value * dlgEcoute(x.qui);          // v2.87.0 : x la vitesse d'ecoute du personnage""")
rep("""$("dllVit").onchange = () => { DLL.audio.playbackRate = +$("dllVit").value; };""",
    """$("dllVit").onchange = () => { const x = DLL.liste && DLL.liste[DLL.i]; DLL.audio.playbackRate = +$("dllVit").value * (x ? dlgEcoute(x.qui) : 1); };""")
# --- l'ecoute d'essai (▶ d'un personnage ou d'une replique) suit aussi
rep("""    DLG.audio.src = srcURL(r.chemin); DLG.audio.play();""",
    """    DLG.audio.src = srcURL(r.chemin);
    const quiE = corps.qui || ((((DLG.e || {}).doc || {}).repliques || []).find(y => y.cle === corps.cle) || {}).qui;   // v2.87.0
    DLG.audio.playbackRate = dlgEcoute(quiE); DLG.audio.play();""")
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
