# -*- coding: utf-8 -*-
"""App v1.84.0 -> v1.85.0 : musique de fond PAR SERIE sous la narration (etape 13, ordre de Quang du 22/09).
Bloc « Musique de la serie » (choisir / importer / ecouter / corbeille) + dans le lecteur : interrupteur 🎵
et volume (memorises par appareil), musique qui BAISSE quand la voix parle, boucle en fondu enchaine.
Verifie ses ancres (une seule occurrence chacune), sinon s'arrete sans rien ecrire.
"""
import shutil
p = r"D:\Download\02-Apps-Web\Repo-github\App\manga-studio\manga_studio.html"
shutil.copy(p, p + ".bak-20260922-v185")
s = open(p, encoding="utf-8").read()


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:80])
    s = s.replace(a, b)


for a, b in (("<title>Manga Studio v1.84.0</title>", "<title>Manga Studio v1.85.0</title>"),
             ('id="verBadge">v1.84.0<', 'id="verBadge">v1.85.0<'),
             ('const VERSION = "1.84.0";', 'const VERSION = "1.85.0";')):
    rep(a, b)

# ---------- HTML : bloc musique sous la traduction ----------
rep('''      <p class="muted aide" id="tradEtat" style="margin:6px 0 0"></p>
    </div>''',
    '''      <p class="muted aide" id="tradEtat" style="margin:6px 0 0"></p>
    </div>
    <!-- MUSIQUE DE FOND DE LA SERIE (v1.85.0, etape 13) : sources/<serie>/musique/ -->
    <div class="narr-box mus-box">
      <div class="row" style="align-items:flex-end">
        <div style="width:240px"><label>🎵 Musique de la série (sous la voix)</label><select id="musChoix">
          <option value="">aucune</option></select></div>
        <button class="btn" id="musEcoute" title="écouter ce morceau seul">▶</button>
        <button class="btn" id="musImport" title="un fichier audio de ton PC ou de ton téléphone (mp3, wav, ogg, m4a, flac)">Importer un morceau…</button>
        <button class="btn sm danger" id="musSuppr" title="mettre ce morceau à la corbeille">🗑</button>
        <input type="file" id="musFichier" accept="audio/*,.mp3,.wav,.ogg,.m4a,.flac" hidden>
      </div>
      <p class="muted aide" id="musEtat" style="margin:6px 0 0"></p>
    </div>''')
rep('''.trad-box{margin-top:10px}''', '''.trad-box,.mus-box{margin-top:10px}
.lec-vol{width:90px;accent-color:var(--acc,#e94560)}''')

# ---------- HTML : lecteur ----------
rep('''    <label class="lec-chk"><input type="checkbox" id="lecSousOn" checked> sous-titres</label>''',
    '''    <label class="lec-chk"><input type="checkbox" id="lecSousOn" checked> sous-titres</label>
    <span class="lec-chk" id="lecMusBox" hidden><label class="lec-chk" title="musique de fond de la série"><input type="checkbox" id="lecMusOn"> 🎵</label>
      <input type="range" class="lec-vol" id="lecMusVol" min="0" max="100" step="1" title="volume de la musique"></span>''')
rep('''  <audio id="lecAudio" preload="auto"></audio>''',
    '''  <audio id="lecAudio" preload="auto"></audio>
  <audio id="lecMus1" preload="auto"></audio><audio id="lecMus2" preload="auto"></audio>''')

# ---------- JS : chargement a l'ouverture d'un chapitre ----------
rep('''  refreshTrads().catch(err => log("traductions : " + err.message, "w"));''',
    '''  refreshTrads().catch(err => log("traductions : " + err.message, "w"));
  refreshMus().catch(err => log("musique : " + err.message, "w"));''')

rep('''async function refreshNarrs(){''',
    '''// v1.85.0 : musique de fond PAR SERIE. Le volume et l'interrupteur sont memorises par appareil ;
// le morceau qui joue est memorise par serie (proxy : musique/choix.json).
// Niveau : les morceaux de Generate Studio sont mixes pour etre ecoutes SEULS (-11,4 LUFS mesures) ->
// defaut 25 % = gain 0,1 (-20 dB), et encore -7 dB quand la voix parle (ducking), remonte entre les pages.
let MUS = { items: [], choix: "" }, MUS_ON = true, MUS_VOL = 25;
try { MUS_ON = localStorage.getItem("manga_mus_on") !== "0";
      const v = localStorage.getItem("manga_mus_vol"); if (v !== null && !isNaN(+v)) MUS_VOL = +v; } catch {}
const serieDe = d => (d || "").split("/")[0];
const MUS_GAIN_MAX = 0.4, MUS_DUCK = 0.45, MUS_FONDU = 3;
const musURL = () => { const it = MUS.items.find(x => x.nom === MUS.choix); return it ? srcURL(it.fichier) : ""; };
async function refreshMus(){
  if (!CHAP_OPEN) return;
  MUS = await api("/manga/musiques?serie=" + encodeURIComponent(serieDe(CHAP_OPEN)));
  $("musChoix").innerHTML = '<option value="">aucune</option>'
    + MUS.items.map(x => '<option value="' + esc(x.nom) + '">' + esc(x.nom) + '</option>').join("");
  $("musChoix").value = MUS.choix || "";
  $("musEcoute").disabled = $("musSuppr").disabled = !MUS.choix;
  $("musEtat").textContent = !MUS.items.length
    ? "Aucun morceau pour cette série. Importe un morceau instrumental : il jouera doucement sous la voix, en boucle."
    : MUS.choix ? "Joue sous la voix de tous les chapitres de la série. Volume et 🎵 on/off : dans le lecteur."
    : "Aucune musique sous la voix pour cette série.";
}
$("musChoix").onchange = async () => {
  try {
    const r = await api("/manga/musique_choix", { serie: serieDe(CHAP_OPEN), nom: $("musChoix").value });
    if (r.error) throw new Error(r.error);
    MUS_APERCU.pause(); await refreshMus();
  } catch (e){ log("musique : " + e.message, "e"); alert(e.message); }
  $("musChoix").blur();
};
const MUS_APERCU = new Audio();
const majMusEcoute = () => { $("musEcoute").textContent = MUS_APERCU.paused ? "▶" : "■"; };
MUS_APERCU.onplay = MUS_APERCU.onpause = MUS_APERCU.onended = majMusEcoute;
$("musEcoute").onclick = () => {
  if (!MUS_APERCU.paused){ MUS_APERCU.pause(); return; }
  MUS_APERCU.src = musURL(); MUS_APERCU.volume = 0.6;
  MUS_APERCU.play().catch(e => { if (e.name !== "AbortError") log("musique : " + e.message, "w"); });
};
$("musImport").onclick = () => $("musFichier").click();
$("musFichier").onchange = () => {
  const f = $("musFichier").files[0]; $("musFichier").value = "";
  if (!f) return;
  if (f.size > 40 * 1024 * 1024){ alert("Fichier trop gros (40 Mo au plus)."); return; }
  const rd = new FileReader();
  rd.onload = async () => {
    $("musEtat").textContent = "⏳ import de « " + f.name + " »…";
    try {
      const r = await api("/manga/musique_import", { serie: serieDe(CHAP_OPEN), nom: f.name, data: rd.result });
      if (r.error) throw new Error(r.error);
      log("musique importée : " + r.nom);
      await refreshMus();
    } catch (e){ log("musique : " + e.message, "e"); alert(e.message); await refreshMus(); }
  };
  rd.readAsDataURL(f);
};
$("musSuppr").onclick = async () => {
  const nom = $("musChoix").value; if (!nom) return;
  if (!confirm("Mettre « " + nom + " » à la corbeille ?")) return;
  try {
    const r = await api("/manga/musique_suppr", { serie: serieDe(CHAP_OPEN), nom });
    if (r.error) throw new Error(r.error);
    MUS_APERCU.pause(); log("musique à la corbeille : " + nom); await refreshMus();
  } catch (e){ log("musique : " + e.message, "e"); alert(e.message); }
};

// --- lecture sous la narration : deux lecteurs pour boucler en fondu enchaine, volume suivi toutes les 100 ms
const MP = { els: [$("lecMus1"), $("lecMus2")], cur: 0, g: 0, url: "", timer: null };
function musCible(){
  if (!MP.url || !MUS_ON || $("lecteur").hidden || !LEC.playing) return 0;
  const a = $("lecAudio"), voix = a.getAttribute("src") && !a.paused && !a.ended;
  return MUS_VOL / 100 * MUS_GAIN_MAX * (voix ? MUS_DUCK : 1);
}
function musEnveloppe(el){                     // fondu d'entree et de sortie de chaque passage de la boucle
  const d = el.duration, t = el.currentTime;
  if (!d || !isFinite(d)) return 1;
  return Math.max(0, Math.min(1, t / MUS_FONDU, (d - t) / MUS_FONDU));
}
function musTick(){
  // baisse vite (0,3 s) quand la voix reprend, remonte en ~2,5 s quel que soit le volume : les 0,45 s entre
  // deux pages ne font pas pomper
  const cible = musCible();
  MP.g += Math.max(-0.02, Math.min(Math.max(0.004, cible * 0.04), cible - MP.g));
  const a = MP.els[MP.cur], b = MP.els[1 - MP.cur];
  if (MP.g <= 0.001 && cible === 0){ MP.els.forEach(x => { if (!x.paused) x.pause(); }); return; }
  if (a.paused) a.play().catch(() => {});
  // fin du passage en cours -> le 2e lecteur repart du debut, les deux se croisent pendant MUS_FONDU s
  if (a.duration && a.currentTime > a.duration - MUS_FONDU && b.paused){
    b.currentTime = 0; b.play().catch(() => {}); MP.cur = 1 - MP.cur;
  }
  MP.els.forEach(x => { x.volume = x.paused ? 0 : Math.min(1, MP.g * musEnveloppe(x)); });
}
function musDemarrer(){
  const url = musURL();
  $("lecMusBox").hidden = !url;
  $("lecMusOn").checked = MUS_ON; $("lecMusVol").value = MUS_VOL;
  if (url !== MP.url){
    MP.els.forEach(x => { x.pause(); if (url) x.src = url; else x.removeAttribute("src"); });
    MP.url = url; MP.cur = 0; MP.g = 0;
  }
  clearInterval(MP.timer); MP.timer = url ? setInterval(musTick, 100) : null;
}
function musArreter(){ clearInterval(MP.timer); MP.timer = null; MP.g = 0; MP.els.forEach(x => x.pause()); }
$("lecMusOn").onchange = () => {
  MUS_ON = $("lecMusOn").checked; try { localStorage.setItem("manga_mus_on", MUS_ON ? "1" : "0"); } catch {}
  $("lecMusOn").blur();
};
$("lecMusVol").oninput = () => {
  MUS_VOL = +$("lecMusVol").value; try { localStorage.setItem("manga_mus_vol", String(MUS_VOL)); } catch {}
};
$("lecMusVol").onchange = () => $("lecMusVol").blur();

async function refreshNarrs(){''')

rep('''  $("lecPlay").focus();                  // le clavier reste DANS le lecteur, pas sur un bouton de la page''',
    '''  $("lecPlay").focus();                  // le clavier reste DANS le lecteur, pas sur un bouton de la page
  MUS_APERCU.pause(); musDemarrer();''')
rep('''  $("lecAudio").pause(); clearTimeout(LEC.timer); $("lecteur").hidden = true; document.body.style.overflow = "";''',
    '''  $("lecAudio").pause(); clearTimeout(LEC.timer); $("lecteur").hidden = true; document.body.style.overflow = "";
  musArreter();''')

open(p, "w", encoding="utf-8").write(s)
print("patch app v1.85.0 OK")
