# -*- coding: utf-8 -*-
"""App v1.89.0 -> v1.90.0 : musique par SERIE ou par CHAPITRE, jusqu'a 5 morceaux enchaines au hasard (Quang 05h26-05h33).

- « Musique de ce chapitre : celle de la serie / propre a ce chapitre » ; un chapitre suit la serie d'office ;
- une LISTE a colonnes FIXES (☐ nom duree ▶ 🗑) : cocher = jouer (5 max), DECOCHER = retirer d'ici (le fichier reste),
  🗑 = supprimer de la serie ET de tous les chapitres (corbeille) — deux gestes distincts, comme demande ;
- le lecteur enchaine les coches dans un ordre ALEATOIRE, en fondu, en boucle ; la musique ne depend de rien
  d'autre (« les musiques tournent, point final ») ; 🎵 on/off du lecteur inchange.
Verifie ses ancres, sinon n'ecrit rien.
"""
import shutil
p = r"D:\Download\02-Apps-Web\Repo-github\App\manga-studio\manga_studio.html"
shutil.copy(p, p + ".bak-20260922-v190")
s = open(p, encoding="utf-8").read()


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:80])
    s = s.replace(a, b)


def rep_bloc(debut, fin, b):
    """Remplace de `debut` (inclus) jusqu'a `fin` (exclu)."""
    global s
    assert s.count(debut) == 1 and s.count(fin) >= 1, (s.count(debut), debut[:60])
    i = s.index(debut); j = s.index(fin, i)
    s = s[:i] + b + s[j:]


for a, b in (("<title>Manga Studio v1.89.0</title>", "<title>Manga Studio v1.90.0</title>"),
             ('id="verBadge">v1.89.0<', 'id="verBadge">v1.90.0<'),
             ('const VERSION = "1.89.0";', 'const VERSION = "1.90.0";')):
    rep(a, b)

# ---------- HTML ----------
rep_bloc('''      <div class="row" style="align-items:flex-end">
        <div style="width:240px"><label>🎵 Musique de la série (sous la voix)</label>''',
         '''      <div id="gsBox" class="gs-box" hidden>''',
         '''      <div class="mus-tete">
        <b>🎵 Musique sous la voix</b>
        <div class="seg" id="musMode" title="ce chapitre suit la sélection de la série, ou a la sienne">
          <button data-mode="serie">Celle de la série</button><button data-mode="propre">Propre au chapitre</button></div>
      </div>
      <div id="musListe" class="mus-liste"></div>
      <p class="muted aide" id="musEtat" style="margin:6px 0 0"></p>
      <div class="mus-actions">
        <button class="btn sm" id="musGs" title="un morceau de ta playlist Generate Studio (génère-le là-bas : mode intelligent + Instrumental)">🎛 Prendre dans Generate Studio</button>
        <button class="btn sm" id="musImport" title="un fichier audio de ton PC ou de ton téléphone (mp3, wav, ogg, m4a, flac)">Importer un fichier…</button>
        <input type="file" id="musFichier" accept="audio/*,.mp3,.wav,.ogg,.m4a,.flac" hidden>
      </div>
''')
rep('''.trad-box,.mus-box{margin-top:10px}''',
    '''.trad-box,.mus-box{margin-top:10px}
/* v1.90.0 : musique en colonnes FIXES — la case, le nom (coupe s'il est long), la duree, ▶, 🗑 toujours au meme endroit */
.mus-tete{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:6px}.mus-tete b{flex:1 1 auto;font-size:13px}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:8px;overflow:hidden}
.seg button{background:none;border:0;color:var(--dim);font:inherit;font-size:12px;padding:5px 10px;cursor:pointer}
.seg button.on{background:color-mix(in srgb, var(--accent2) 22%, transparent);color:var(--txt)}
.mus-liste{display:flex;flex-direction:column;gap:3px}
.mus-it{display:grid;grid-template-columns:22px minmax(0,1fr) 44px 32px 32px;align-items:center;gap:6px;
  padding:4px 6px;border-radius:7px;background:rgba(255,255,255,.03)}
.mus-it input{width:16px;height:16px;margin:0;accent-color:var(--accent2)}
.mus-it .nom{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-size:13px}
.mus-it .dur{font-size:12px;color:var(--dim);text-align:right;font-variant-numeric:tabular-nums}
.mus-it .btn.sm{padding:3px 0;width:32px;justify-content:center}
.mus-it.off .nom{color:var(--dim)}
.mus-actions{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}''')

# ---------- JS : etat, liste, selection ----------
rep_bloc('''let MUS = { items: [], choix: "" }, MUS_ON = true, MUS_VOL = 25;''',
         '''$("musImport").onclick = () => $("musFichier").click();''',
         '''let MUS = { items: [], serie_sel: [], effectif: [], chapitre: { mode: "serie", noms: [] }, max: 5 }, MUS_ON = true, MUS_VOL = 25;
try { MUS_ON = localStorage.getItem("manga_mus_on") !== "0";
      const v = localStorage.getItem("manga_mus_vol"); if (v !== null && !isNaN(+v)) MUS_VOL = +v; } catch {}
const serieDe = d => (d || "").split("/")[0];
const MUS_GAIN_MAX = 0.4, MUS_DUCK = 0.45, MUS_FONDU = 3;
const musMode = () => (MUS.chapitre || {}).mode === "propre" ? "propre" : "serie";
const musCoches = () => musMode() === "propre" ? (MUS.chapitre.noms || []) : (MUS.serie_sel || []);
async function refreshMus(){
  if (!CHAP_OPEN) return;
  MUS = await api("/manga/musiques?serie=" + encodeURIComponent(serieDe(CHAP_OPEN)) + "&d=" + encodeURIComponent(CHAP_OPEN));
  musRendre();
}
function musRendre(){
  const mode = musMode(), coches = musCoches(), plein = coches.length >= (MUS.max || 5);
  document.querySelectorAll("#musMode [data-mode]").forEach(b => b.classList.toggle("on", b.dataset.mode === mode));
  $("musMode").hidden = !MUS.items.length;
  $("musListe").innerHTML = MUS.items.map(x => {
    const on = coches.includes(x.nom);
    return '<div class="mus-it' + (on ? "" : " off") + '"><input type="checkbox" data-mus-coche="' + esc(x.nom) + '"'
      + (on ? " checked" : "") + (!on && plein ? " disabled" : "") + ' title="' + (on ? "décocher = retirer d'ici (le morceau reste dans la série)" : "cocher = jouer sous la voix") + '">'
      + '<span class="nom" title="' + esc(x.nom) + '">' + esc(x.nom) + '</span><span class="dur">' + (x.dur ? fmtT(x.dur) : "") + "</span>"
      + '<button class="btn sm" data-mus-ecoute="' + esc(x.nom) + '" title="écouter seul">' + (MUS_APERCU.dataset.nom === x.nom && !MUS_APERCU.paused ? "■" : "▶") + "</button>"
      + '<button class="btn sm danger" data-mus-suppr="' + esc(x.nom) + '" title="supprimer de la série et de tous les chapitres (corbeille)">🗑</button></div>';
  }).join("");
  $("musEtat").textContent = !MUS.items.length
    ? "Aucun morceau pour cette série. Prends-en un dans Generate Studio (instrumental) ou importe un fichier."
    : (mode === "propre" ? "Ce chapitre a sa propre sélection. " : "Sélection de la série : elle vaut pour tous les chapitres qui la suivent. ")
      + (coches.length ? coches.length + " morceau(x) coché(s) : joués au hasard, enchaînés en fondu (" + (MUS.max || 5) + " au plus)."
                       : "Rien de coché : pas de musique ici.");
}
async function musEnvoyer(mode, noms){
  const body = { serie: serieDe(CHAP_OPEN), noms };
  if (mode === "propre" || musMode() === "propre" || mode === "serie-chapitre") Object.assign(body, { d: CHAP_OPEN, mode: mode === "serie-chapitre" ? "serie" : "propre" });
  const r = await api("/manga/musique_selection", body);
  if (r.error) throw new Error(r.error);
  MUS = r; musRendre();
}
$("musMode").onclick = e => {
  const b = e.target.closest("[data-mode]"); if (!b || b.dataset.mode === musMode()) return;
  // passer en « propre » part de la selection de la serie : on ajuste au lieu de tout recocher
  (b.dataset.mode === "propre" ? musEnvoyer("propre", (MUS.serie_sel || []).slice()) : musEnvoyer("serie-chapitre", []))
    .catch(err => { log("musique : " + err.message, "e"); alert(err.message); });
};
$("musListe").onchange = e => {
  const c = e.target.closest("[data-mus-coche]"); if (!c) return;
  const nom = c.dataset.musCoche, cur = musCoches().filter(n => n !== nom);
  if (c.checked) cur.push(nom);
  musEnvoyer(musMode() === "propre" ? "propre" : "serie", cur).catch(err => { log("musique : " + err.message, "e"); alert(err.message); refreshMus(); });
};
const MUS_APERCU = new Audio();
MUS_APERCU.onplay = MUS_APERCU.onpause = MUS_APERCU.onended = () => { if (!$("musListe").hidden) musRendre(); };
$("musListe").onclick = async e => {
  const ec = e.target.closest("[data-mus-ecoute]"), su = e.target.closest("[data-mus-suppr]");
  if (ec){
    const it = MUS.items.find(x => x.nom === ec.dataset.musEcoute);
    if (!MUS_APERCU.paused && MUS_APERCU.dataset.nom === it.nom){ MUS_APERCU.pause(); return; }
    MUS_APERCU.dataset.nom = it.nom; MUS_APERCU.src = srcURL(it.fichier); MUS_APERCU.volume = 0.6;
    MUS_APERCU.play().catch(err => { if (err.name !== "AbortError") log("musique : " + err.message, "w"); });
    return;
  }
  if (!su) return;
  const nom = su.dataset.musSuppr;
  if (!confirm("Supprimer « " + nom + " » de la série ?\\n\\nIl quitte aussi TOUS les chapitres qui l'avaient choisi. Il part à la corbeille (récupérable à la main).\\n\\nPour l'enlever seulement de ce chapitre : décoche-le.")) return;
  try {
    const r = await api("/manga/musique_suppr", { serie: serieDe(CHAP_OPEN), nom });
    if (r.error) throw new Error(r.error);
    if (MUS_APERCU.dataset.nom === nom) MUS_APERCU.pause();
    log("musique supprimée de la série : " + nom); await refreshMus();
  } catch (err){ log("musique : " + err.message, "e"); alert(err.message); }
};
''')

# le bouton 🗑 et le menu d'avant n'existent plus
rep_bloc('''$("musSuppr").onclick = async () => {''', '''// v1.87.0 : PRENDRE DANS GENERATE STUDIO.''', '')

# ---------- JS : lecteur — jusqu'a 5 morceaux, ordre aleatoire, fondu enchaine ----------
rep('''const MP = { els: [$("lecMus1"), $("lecMus2")], cur: 0, g: 0, url: "", timer: null };''',
    '''const MP = { els: [$("lecMus1"), $("lecMus2")], cur: 0, g: 0, url: "", timer: null, liste: [], seq: [], k: 0 };
// suite des morceaux : des tours melanges, sans rejouer a la suite le meme morceau d'un tour a l'autre
function musIdx(k){
  const n = MP.liste.length;
  while (MP.seq.length <= k){
    const t = [...Array(n).keys()].sort(() => Math.random() - 0.5);
    if (n > 1 && MP.seq.length && t[0] === MP.seq[MP.seq.length - 1]) t.push(t.shift());
    MP.seq.push(...t);
  }
  return MP.seq[k];
}
function musCharge(el, k){ el.src = MP.liste[musIdx(k)]; el.dataset.k = k; }''')
rep('''  if (a.duration && a.currentTime > a.duration - MUS_FONDU && b.paused){
    b.currentTime = 0; b.play().catch(() => {}); MP.cur = 1 - MP.cur;
  }''',
    '''  // fin du morceau en cours -> le 2e lecteur (deja charge avec le SUIVANT) part, les deux se croisent MUS_FONDU s
  if (a.duration && a.currentTime > a.duration - MUS_FONDU && b.paused){
    if (+b.dataset.k !== MP.k + 1) musCharge(b, MP.k + 1);
    b.currentTime = 0; b.play().catch(() => {}); MP.cur = 1 - MP.cur; MP.k++;
  }
  // l'ancien, une fois tu, se prepare pour le morceau d'apres
  if (b.paused && b !== MP.els[MP.cur] && +b.dataset.k !== MP.k + 1 && (b.ended || b.currentTime === 0 || b.currentTime > 1)) musCharge(b, MP.k + 1);''')
rep('''function musDemarrer(){
  const url = musURL();
  $("lecMusBox").hidden = !url;
  $("lecMusOn").checked = MUS_ON; $("lecMusVol").value = MUS_VOL;
  if (url !== MP.url){
    MP.els.forEach(x => { x.pause(); if (url) x.src = url; else x.removeAttribute("src"); });
    MP.url = url; MP.cur = 0; MP.g = 0;
  }
  clearInterval(MP.timer); MP.timer = url ? setInterval(musTick, 100) : null;
}''',
    '''function musDemarrer(){
  const liste = (MUS.effectif || []).map(n => MUS.items.find(x => x.nom === n)).filter(Boolean).map(x => srcURL(x.fichier));
  const cle = liste.join("|");
  $("lecMusBox").hidden = !liste.length;
  $("lecMusOn").checked = MUS_ON; $("lecMusVol").value = MUS_VOL;
  if (cle !== MP.url){
    MP.els.forEach(x => { x.pause(); x.removeAttribute("src"); delete x.dataset.k; });
    MP.url = cle; MP.liste = liste; MP.seq = []; MP.k = 0; MP.cur = 0; MP.g = 0;
    if (liste.length){ musCharge(MP.els[0], 0); musCharge(MP.els[1], 1); }
  }
  clearInterval(MP.timer); MP.timer = liste.length ? setInterval(musTick, 100) : null;
}''')

open(p, "w", encoding="utf-8").write(s)
print("patch app v1.90.0 OK")
