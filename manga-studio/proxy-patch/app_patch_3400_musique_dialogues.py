# -*- coding: utf-8 -*-
"""v3.4.0 (27/09, Quang 18h57 : « une musique de fond, de maniere optionnelle, pour les dialogues ? ») -- la musique de la
serie sous les Dialogues, avec les MEMES reglages que la narration (MUS_ON / MUS_VOL, communs) :
  * lecteur des Dialogues : le moteur de la narration (MP : deux lecteurs en fondu, baisse sous la voix, remontee douce)
    suit maintenant DLL.audio quand le lecteur des Dialogues est ouvert ; demarre a l'ouverture, s'arrete a la fermeture ;
  * reglages du lecteur : « 🎵 Musique » + son volume (les memes que ceux du lecteur de narration) ;
  * video / ⚡ Tout faire : le choix part au serveur (patch_dialogues_15 -> dialogues.py 1.24.0 --musique).
Suppose v3.3.2. Rejouable."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v3.4.0" in s[:900]:
    print("deja applique"); sys.exit(0)
if "v3.3.2" not in s[:1400]:
    print("ERREUR : appliquer d'abord app_patch_3320_saisie_pages.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:80], s.count(a))
    s = s.replace(a, b)


rep("<title>Manga Studio v3.3.2</title>", "<title>Manga Studio v3.4.0</title>")
rep('<span class="ver" id="verBadge">v3.3.2</span>', '<span class="ver" id="verBadge">v3.4.0</span>')
rep('const VERSION = "3.3.2";', 'const VERSION = "3.4.0";   // v3.4.0 : musique de fond de la serie sous les Dialogues (lecteur + video), memes reglages que la narration')

# le moteur de musique suit aussi le lecteur des Dialogues
rep("""function musCible(){
  if (!MP.url || !MUS_ON || $("lecteur").hidden || !LEC.playing) return 0;""",
    """function musCible(){
  if (!MP.url || !MUS_ON) return 0;
  if (typeof dlgLec !== "undefined" && !dlgLec.hidden){                       // v3.4.0 : sous les Dialogues
    if (DLL.pause) return 0;
    const v = DLL.audio, parle = v.getAttribute("src") && !v.paused && !v.ended;
    return MUS_VOL / 100 * MUS_GAIN_MAX * (parle ? MUS_DUCK : 1);
  }
  if ($("lecteur").hidden || !LEC.playing) return 0;""")
# reglages du lecteur des Dialogues : 🎵 Musique + volume (memes reglages que la narration)
rep("""<span>🎥 Suivre la case <small class="muted">sinon la page entière</small></span><input type="checkbox" class="bascule" id="dllCam"></label></div>';""",
    """<span>🎥 Suivre la case <small class="muted">sinon la page entière</small></span><input type="checkbox" class="bascule" id="dllCam"></label>'
  + '<div class="lec-ligne" id="dllMusL" hidden><label class="lec-mus-l" title="musique de fond de la série (mêmes réglages que la narration)"><span>🎵 Musique <small class="muted">celle de la série, baisse quand on parle</small></span><input type="checkbox" class="bascule" id="dllMus"></label>'
  + '<input type="range" class="lec-vol" id="dllMusVol" min="0" max="100" step="1" title="volume de la musique"></div></div>';""")
# ouverture / fermeture du lecteur des Dialogues : demarrer / arreter la musique
rep("""  dlgLec.hidden = false; document.body.style.overflow = "hidden";
  dllRegOuvrir(false); $("dllVol").value = VOL_G; DLL.audio.volume = VOL_G / 100; dllChMaj();""",
    """  dlgLec.hidden = false; document.body.style.overflow = "hidden";
  dllRegOuvrir(false); $("dllVol").value = VOL_G; DLL.audio.volume = VOL_G / 100; dllChMaj();
  dllMusMaj();                                                                 // v3.4.0 : musique de la serie""")
rep("""$("dllFermer").onclick = () => { DLL.audio.pause(); clearTimeout(DLL.t); clearTimeout(DLL.t2); dlgLec.hidden = true; document.body.style.overflow = ""; };""",
    """$("dllFermer").onclick = () => { DLL.audio.pause(); clearTimeout(DLL.t); clearTimeout(DLL.t2); dlgLec.hidden = true; document.body.style.overflow = "";
  if ($("lecteur").hidden) musArreter(); };                                    // v3.4.0""")
# video lancee depuis l'etape « 🎬 Video » : le choix de musique part avec
rep("""  try { const r = await api("/manga/dialogues_lancer", Object.assign({ d: CHAP_OPEN, action: "video" }, portee ? { pages: portee } : {}));""",
    """  try { const r = await api("/manga/dialogues_lancer", Object.assign({ d: CHAP_OPEN, action: "video" }, portee ? { pages: portee } : {}, dlgMusiqueOpt()));""")
rep("""      const r = await api("/manga/dialogues_lancer", Object.assign({ d: CHAP_OPEN, action, pages }, manq.length ? { traduire: true } : {}, opts.sansPrep ? { sans_preparation: true } : {}));""",
    """      const r = await api("/manga/dialogues_lancer", Object.assign({ d: CHAP_OPEN, action, pages }, manq.length ? { traduire: true } : {}, opts.sansPrep ? { sans_preparation: true } : {},
                                                                    action === "tout" ? dlgMusiqueOpt() : {}));   // v3.4.0""")

JS = r"""/* ---- v3.4.0 : musique de fond de la serie sous les Dialogues ---- */
const dlgMusiqueDispo = () => !!(MUS && (MUS.effectif || []).length);
const dlgMusiqueOpt = () => (MUS_ON && dlgMusiqueDispo() ? { musique: true, volume: MUS_VOL } : {});
function dllMusMaj(){
  const ok = dlgMusiqueDispo();
  $("dllMusL").hidden = !ok; $("dllMus").checked = MUS_ON; $("dllMusVol").value = MUS_VOL; $("dllMusVol").disabled = !MUS_ON;
  if (ok) musDemarrer(); else musArreter();
}
$("dllMus").onchange = () => {
  MUS_ON = $("dllMus").checked; try { localStorage.setItem("manga_mus_on", MUS_ON ? "1" : "0"); } catch {}
  if ($("lecMusOn")) $("lecMusOn").checked = MUS_ON; $("dllMusVol").disabled = !MUS_ON; $("dllMus").blur();
};
$("dllMusVol").oninput = () => {
  MUS_VOL = +$("dllMusVol").value; try { localStorage.setItem("manga_mus_vol", String(MUS_VOL)); } catch {}
  if ($("lecMusVol")) $("lecMusVol").value = MUS_VOL;
};

"""
rep("document.body.appendChild(dlgLec);", "document.body.appendChild(dlgLec);" + N + JS.replace(chr(10), N))   # APRES la creation du lecteur (ses boutons)
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok v3.4.0")
