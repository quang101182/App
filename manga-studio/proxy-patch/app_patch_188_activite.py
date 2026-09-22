# -*- coding: utf-8 -*-
"""App v1.87.0 -> v1.88.0 : cellule d'ACTIVITE dans l'en-tete (demande Quang, 22/09 05h12).

« Un bandeau dynamique d'evenements actuels [...] tant qu'il y a de l'activite en cours, ca doit etre affiche.
Quand il n'y a plus rien, il peut redevenir gris [...] ne cree pas d'effet ou le bandeau apparait et disparait
[...] la barre de VRAM prend pas mal de place [...] si j'appuie, j'ai le detail : il peut y avoir plusieurs
evenements en meme temps. »
=> une CELLULE toujours presente, de taille fixe, prise sur la largeur de la VRAM : grise « rien en cours »,
   coloree + pulsation quand ca travaille (« Narration Claymore 16/62 +1 »). Un clic ouvre un panneau
   SUPERPOSE (aucune hauteur ne bouge) : chaque tache avec sa barre, un clic = ouvrir le chapitre ; et ce qui
   vient de finir pendant la session. Source : GET /manga/activite (proxy, tous chapitres).
Verifie ses ancres, sinon n'ecrit rien.
"""
import shutil
p = r"D:\Download\02-Apps-Web\Repo-github\App\manga-studio\manga_studio.html"
shutil.copy(p, p + ".bak-20260922-v188")
s = open(p, encoding="utf-8").read()


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:80])
    s = s.replace(a, b)


for a, b in (("<title>Manga Studio v1.87.0</title>", "<title>Manga Studio v1.88.0</title>"),
             ('id="verBadge">v1.87.0<', 'id="verBadge">v1.88.0<'),
             ('const VERSION = "1.87.0";', 'const VERSION = "1.88.0";')):
    rep(a, b)

# ---------- HTML : la cellule, entre les moteurs et la VRAM ; le panneau, hors du flux ----------
rep('''    <div class="vram" title="Mémoire utilisée sur la carte graphique">''',
    '''    <!-- v1.88.0 : cellule d'ACTIVITE, TOUJOURS la (grise au repos) : aucune hauteur ne bouge jamais -->
    <button class="act" id="hdrAct" title="Ce qui travaille en ce moment (narrations, traductions, karaoké, capture)">
      <span class="act-dot"></span><span class="act-txt" id="actTxt">Rien en cours</span><span class="act-n" id="actN" hidden></span>
    </button>
    <div class="vram" title="Mémoire utilisée sur la carte graphique">''')
rep('''<nav>
  <!-- v1.80.0 : LIRE (Bibliotheque) d'abord''',
    '''<div id="actPanel" class="act-panel" hidden>
  <div class="act-h"><b>Activité</b><span class="muted aide" id="actMaj"></span><button class="btn sm" id="actFermer">✕</button></div>
  <div id="actListe"></div>
  <div id="actFinis"></div>
</div>

<nav>
  <!-- v1.80.0 : LIRE (Bibliotheque) d'abord''')

# ---------- CSS ----------
rep('''.vram{display:flex;align-items:center;gap:6px;font-size:11px;color:var(--dim);
  flex:1 1 150px;min-width:120px}''',
    '''.vram{display:flex;align-items:center;gap:6px;font-size:11px;color:var(--dim);
  flex:1 1 70px;min-width:60px}
/* v1.88.0 : cellule d'activite. Meme hauteur qu'une pastille moteur, largeur prise sur la VRAM. */
.act{display:flex;align-items:center;gap:6px;padding:3px 9px;border-radius:99px;cursor:pointer;
  border:1px solid var(--line);background:var(--panel);font:inherit;font-size:11px;color:var(--dim);
  flex:1 1 110px;min-width:0;max-width:260px}
.act .act-dot{width:8px;height:8px;border-radius:50%;background:#444;flex:none}
.act .act-txt{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}
.act .act-n{flex:none;font-weight:700;color:var(--txt)}
.act.on{border-color:var(--accent2);color:var(--txt)}
.act.on .act-dot{animation:actPulse 1.2s infinite}
.act.fini .act-dot{background:var(--ok)}
@keyframes actPulse{0%,100%{background:var(--accent2)}50%{background:#1d3a44}}
.act-panel{position:fixed;z-index:70;top:52px;right:max(8px,calc(50vw - 380px));width:min(420px,calc(100vw - 16px));
  max-height:70vh;overflow:auto;background:var(--panel);border:1px solid var(--line);border-radius:12px;
  box-shadow:0 10px 30px #000b;padding:10px}
.act-panel[hidden]{display:none}
.act-h{display:flex;align-items:center;gap:8px;margin-bottom:8px}.act-h b{flex:1}
.act-it{display:block;width:100%;text-align:left;font:inherit;color:var(--txt);background:var(--panel2);
  border:1px solid var(--line);border-radius:9px;padding:8px 10px;margin-bottom:6px;cursor:pointer}
.act-it .muted{font-size:12px}
.act-bar{height:5px;border-radius:99px;background:var(--bg,#0b0d11);margin-top:6px;overflow:hidden}
.act-bar i{display:block;height:100%;background:var(--accent2);transition:width .5s}
.act-finis-t{font-size:12px;color:var(--dim);margin:10px 0 4px}''')
rep('''@media(max-width:700px){
  main{padding:10px}''',
    '''@media(max-width:480px){
  .vram>span:first-child{display:none}          /* v1.88.0 : le mot « VRAM » cede sa place a la cellule d'activite */
  .vram{flex:1 1 60px;min-width:56px}
  .act{flex:1 1 80px}
}
@media(max-width:700px){
  main{padding:10px}''')

# ---------- JS ----------
rep('''async function refreshNarrs(){''',
    '''/* ---------- v1.88.0 : ACTIVITE (cellule d'en-tete + panneau) ---------- */
const ACT = { items: [], finis: [], timer: null, cles: new Set(), maj: 0 };
const ACT_LBL = { narration: "Narration", traduction: "Traduction", karaoke: "Karaoké", capture: "Capture" };
const ACT_ETAPE = { noms: "repérage des personnages", vision: "lecture des pages", verification: "vérification",
                    recit: "écriture du récit", voix: "synthèse vocale" };
const actCle = it => [it.type, it.d || it.titre, it.tag || it.langue || ""].join("|");
const actNom = it => (it.titre || "?") + (it.chapitre ? " ch." + it.chapitre : "");
const actFini = it => it.type === "karaoke" ? " fini" : " finie";
const actProg = it => it.total ? it.fait + "/" + it.total : (it.fait != null ? it.fait + " p." : "");
function actRendre(){
  const n = ACT.items.length, b = $("hdrAct");
  b.classList.toggle("on", n > 0);
  b.classList.toggle("fini", !n && ACT.finis.length > 0 && Date.now() - ACT.finis[0].t < 10 * 60 * 1000);
  const it = ACT.items[0];
  $("actTxt").textContent = it ? ACT_LBL[it.type] + " " + actNom(it) + " " + actProg(it)
    : b.classList.contains("fini") ? "✓ " + ACT_LBL[ACT.finis[0].type] + actFini(ACT.finis[0]) : "Rien en cours";
  $("actN").hidden = n < 2; $("actN").textContent = "+" + (n - 1);
  b.title = n ? n + " tâche(s) en cours — touche pour le détail" : "Rien ne travaille en ce moment";
  if ($("actPanel").hidden) return;
  $("actMaj").textContent = ACT.maj ? "mis à jour " + new Date(ACT.maj).toLocaleTimeString("fr-FR") : "";
  $("actListe").innerHTML = ACT.items.map((x, i) => {
    const pct = x.total ? Math.round(100 * (x.fait || 0) / x.total) : 0;
    const detail = [x.tag || (x.langue ? "→ " + x.langue : ""), ACT_ETAPE[x.etape] || x.etape || "", actProg(x)].filter(Boolean).join(" · ");
    return '<button class="act-it" data-act="' + i + '"><b>' + esc(ACT_LBL[x.type] || x.type) + "</b> — " + esc(actNom(x))
      + '<br><span class="muted">' + esc(detail) + "</span>"
      + (x.total ? '<div class="act-bar"><i style="width:' + pct + '%"></i></div>' : "") + "</button>";
  }).join("") || '<p class="muted aide" style="margin:0">Rien ne travaille en ce moment.</p>';
  $("actFinis").innerHTML = ACT.finis.length ? '<div class="act-finis-t">Terminé pendant cette session</div>'
    + ACT.finis.slice(0, 8).map((x, i) => '<button class="act-it" data-fini="' + i + '">✅ ' + esc(ACT_LBL[x.type] || x.type) + " — "
      + esc(actNom(x)) + (x.tag ? ' <span class="muted">· ' + esc(x.tag) + "</span>" : "") + ' <span class="muted">· '
      + new Date(x.t).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" }) + "</span></button>").join("") : "";
}
async function actRafraichir(){
  try {
    const j = await api("/manga/activite");
    const items = j.items || [], cles = new Set(items.map(actCle));
    // ce qui tournait au tour d'avant et ne tourne plus = FINI (on le garde pour la session)
    ACT.items.filter(x => !cles.has(actCle(x))).forEach(x => {
      ACT.finis.unshift(Object.assign({}, x, { t: Date.now() }));
      toast("✅ " + (ACT_LBL[x.type] || x.type) + actFini(x) + " : " + actNom(x));
      if (x.d && x.d === CHAP_OPEN){ refreshNarrs().catch(() => {}); refreshTrads().catch(() => {}); }
    });
    ACT.items = items; ACT.maj = Date.now();
  } catch (e){ /* proxy injoignable : le temoin dedie le dit deja, la cellule garde son dernier etat */ }
  actRendre();
  clearTimeout(ACT.timer);
  ACT.timer = setTimeout(actRafraichir, ACT.items.length ? 4000 : 15000);   // vif quand ca travaille, calme sinon
}
async function actOuvrirChapitre(d){
  if (!d) return;
  $("actPanel").hidden = true;
  document.querySelector('nav button[data-tab="tChap"]').click();
  if (!CHAPS.length) await refreshChaps();
  const i = CHAPS.findIndex(c => c.dir === d);
  if (i >= 0) await openChap(i);
}
$("hdrAct").onclick = () => {
  // juste SOUS l'en-tete, quelle que soit sa hauteur (1 ligne sur PC, 3 sur un telephone de 360 px)
  $("actPanel").style.top = Math.round(document.querySelector("header").getBoundingClientRect().bottom + 6) + "px";
  $("actPanel").hidden = !$("actPanel").hidden; actRendre(); if (!$("actPanel").hidden) actRafraichir();
};
$("actFermer").onclick = () => { $("actPanel").hidden = true; };
$("actPanel").onclick = e => {
  const a = e.target.closest("[data-act]"), f = e.target.closest("[data-fini]");
  if (a) actOuvrirChapitre(ACT.items[+a.dataset.act].d).catch(err => log("activité : " + err.message, "e"));
  if (f) actOuvrirChapitre(ACT.finis[+f.dataset.fini].d).catch(err => log("activité : " + err.message, "e"));
};
document.addEventListener("keydown", e => { if (e.key === "Escape" && !$("actPanel").hidden) $("actPanel").hidden = true; });
setTimeout(actRafraichir, 1500);

async function refreshNarrs(){''')

open(p, "w", encoding="utf-8").write(s)
print("patch app v1.88.0 OK")
