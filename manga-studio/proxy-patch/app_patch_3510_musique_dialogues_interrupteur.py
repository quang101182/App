"""app 3.5.0 -> 3.5.1 (Quang 20h54 : « il manque le switch pour dire si je veux la musique ou non […] dans les dialogues ; on avait
dit que c'etait optionnel ») : interrupteur « Musique de fond » dans le bloc 🎭 Dialogues, a cote de « Tons par replique » et
« Lire les encarts ». Reglage PROPRE aux Dialogues (DLG_MUS_ON, memorise sur l'appareil ; au 1er lancement = celui de la
narration, donc rien ne change tant qu'on n'y touche pas) : lecteur des Dialogues, video, ⚡ Tout faire et « video a refaire
(musique) » le suivent ; la narration garde le sien. Le volume reste commun. Sans morceau pour la serie : grise, dit pourquoi.
Copie, node --check, remplacement."""
import os, re, shutil, subprocess, sys

F = "D:/Download/02-Apps-Web/Repo-github/App/manga-studio/manga_studio.html"
TMP = os.path.join(os.environ.get("TEMP", "."), "manga_studio_351.html")
s = open(F, encoding="utf-8", newline="").read()
if 'const VERSION = "3.5.1"' in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n"


def rep(a, b):
    """fichier a fins de ligne MELANGEES (des blocs en LF) : CRLF d'abord, sinon LF tel quel"""
    global s
    a2, b2 = a.replace("\n", NL), b.replace("\n", NL)
    if s.count(a2) != 1:
        a2, b2 = a, b
    if s.count(a2) != 1:                                   # bloc v3.4.0 ecrit en « \r\r\n » (sans effet pour le navigateur)
        a2, b2 = a.replace("\n", "\r\r\n"), b.replace("\n", "\r\r\n")
    assert s.count(a2) == 1, (s.count(a2), a[:90])
    s = s.replace(a2, b2)


rep("<title>Manga Studio v3.5.0</title>", "<title>Manga Studio v3.5.1</title>")
rep('id="verBadge">v3.5.0</span>', 'id="verBadge">v3.5.1</span>')
rep('const VERSION = "3.5.0";', 'const VERSION = "3.5.1";   // v3.5.1 : interrupteur « Musique de fond » dans le bloc Dialogues (reglage propre aux Dialogues) ')

# reglage propre aux Dialogues, initialise sur celui de la narration
rep('''      const v = localStorage.getItem("manga_mus_vol"); if (v !== null && !isNaN(+v)) MUS_VOL = +v; } catch {}''',
    '''      const v = localStorage.getItem("manga_mus_vol"); if (v !== null && !isNaN(+v)) MUS_VOL = +v; } catch {}
let DLG_MUS_ON = MUS_ON;                          // v3.5.1 : musique des DIALOGUES, separee de la narration
try { const v = localStorage.getItem("manga_dlg_mus_on"); if (v !== null) DLG_MUS_ON = v !== "0"; } catch {}''')

# moteur : sous les Dialogues -> DLG_MUS_ON ; ailleurs -> MUS_ON
rep('''  if (!MP.url || !MUS_ON) return 0;
  if (typeof dlgLec !== "undefined" && !dlgLec.hidden){                       // v3.4.0 : sous les Dialogues
    if (DLL.pause) return 0;''',
    '''  if (!MP.url) return 0;
  if (typeof dlgLec !== "undefined" && !dlgLec.hidden){                       // v3.4.0 : sous les Dialogues
    if (DLL.pause || !DLG_MUS_ON) return 0;                                   // v3.5.1 : son propre interrupteur''')
rep('''    return MUS_VOL / 100 * MUS_GAIN_MAX * (parle ? MUS_DUCK : 1);
  }''', '''    return MUS_VOL / 100 * MUS_GAIN_MAX * (parle ? MUS_DUCK : 1);
  }
  if (!MUS_ON) return 0;''')

# video a refaire / demande de video
rep('''    const voulu = (MUS_ON ? (MUS.effectif || []) : []).slice().sort().join("|");''',
    '''    const voulu = (DLG_MUS_ON ? (MUS.effectif || []) : []).slice().sort().join("|");     // v3.5.1''')
rep('''const dlgMusiqueOpt = () => (MUS_ON && dlgMusiqueDispo() ? { musique: true, volume: MUS_VOL } : {});''',
    '''const dlgMusiqueOpt = () => (DLG_MUS_ON && dlgMusiqueDispo() ? { musique: true, volume: MUS_VOL } : {});   // v3.5.1''')

# reglages du lecteur des Dialogues : meme interrupteur que le bloc
rep('''  $("dllMusL").hidden = !ok; $("dllMus").checked = MUS_ON; $("dllMusVol").value = MUS_VOL; $("dllMusVol").disabled = !MUS_ON;''',
    '''  $("dllMusL").hidden = !ok; $("dllMus").checked = DLG_MUS_ON; $("dllMusVol").value = MUS_VOL; $("dllMusVol").disabled = !DLG_MUS_ON;''')
rep('''  MUS_ON = $("dllMus").checked; try { localStorage.setItem("manga_mus_on", MUS_ON ? "1" : "0"); } catch {}
  if ($("lecMusOn")) $("lecMusOn").checked = MUS_ON; $("dllMusVol").disabled = !MUS_ON; $("dllMus").blur();''',
    '''  dlgMusRegler($("dllMus").checked); $("dllMus").blur();                     // v3.5.1 : reglage des Dialogues''')
rep('''title="musique de fond de la série (mêmes réglages que la narration)"''', '''title="musique de fond de la série sous les dialogues (réglage des Dialogues, séparé de la narration)"''')

# l'interrupteur du bloc
rep('''        <label><input type="checkbox" id="dlgNarr"> Lire les encarts (narrateur)</label>''',
    '''        <label><input type="checkbox" id="dlgNarr"> Lire les encarts (narrateur)</label>
        <label id="dlgMusL"><input type="checkbox" id="dlgMus"> Musique de fond</label>''')
rep('''  ["dlgTons", "dlgNarr", "dlgEnch"].forEach(id => {                     // interrupteurs, texte a gauche''',
    '''  ["dlgTons", "dlgNarr", "dlgMus", "dlgEnch"].forEach(id => {           // interrupteurs, texte a gauche (v3.5.1 : + musique)''')
rep('''  $("dlgNarr").checked = !!(dist.narrateur && dist.narrateur.lire);''',
    '''  $("dlgNarr").checked = !!(dist.narrateur && dist.narrateur.lire);
  dlgMusBloc();                                                              // v3.5.1''')
rep('''$("dlgNarr").onchange = () => dlgRegler({ narrateur: { lire: $("dlgNarr").checked } });''',
    '''$("dlgNarr").onchange = () => dlgRegler({ narrateur: { lire: $("dlgNarr").checked } });
function dlgMusBloc(){                            // v3.5.1 : « Musique de fond » du bloc Dialogues
  const i = $("dlgMus"), sp = i.closest("label").querySelector("span"), ok = typeof MUS !== "undefined" && !!(MUS.effectif || []).length;
  i.checked = DLG_MUS_ON && ok; i.disabled = !ok;
  if (sp) sp.innerHTML = 'Musique de fond <small class="muted" style="display:block;font-size:11.5px">' + (ok ? "celle de la série, sous les voix" : "aucun morceau pour cette série") + "</small>";
}
function dlgMusRegler(on){
  DLG_MUS_ON = !!on; try { localStorage.setItem("manga_dlg_mus_on", DLG_MUS_ON ? "1" : "0"); } catch {}
  if ($("dllMus")) $("dllMus").checked = DLG_MUS_ON; if ($("dllMusVol")) $("dllMusVol").disabled = !DLG_MUS_ON;
  if ($("dlgMus")) $("dlgMus").checked = DLG_MUS_ON;
  if (typeof dlgRendre === "function" && DLG.e) dlgRendre();                // la video passe « à refaire (musique) » si besoin
}
$("dlgMus").onchange = () => { dlgMusRegler($("dlgMus").checked); toast(DLG_MUS_ON ? "🎵 musique de fond sous les dialogues" : "🔇 dialogues sans musique"); };''')

open(TMP, "w", encoding="utf-8", newline="").write(s)
js = "\n".join(re.findall(r"<script>(.*?)</script>", s, re.S))
open(TMP + ".js", "w", encoding="utf-8").write(js)
r = subprocess.run(["node", "--check", TMP + ".js"], capture_output=True, text=True)
if r.returncode:
    print("node --check KO", r.stderr[:800]); sys.exit(1)
if "--essai" in sys.argv:
    print("essai OK (rien remplace) :", TMP); sys.exit(0)
shutil.copy2(F, F + ".bak-v3500")
shutil.copy2(TMP, F)
print("ok v3.5.1")
