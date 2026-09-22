# -*- coding: utf-8 -*-
"""App v1.98.0 -> v1.99.0 : HORS-LIGNE dans le telephone (etape 10, decision Quang 22/09 09h00).
Une narration « 📥 gardee » = tout ce que le lecteur lit (texte, pages VO, voix, « Precedemment... ») copie dans le cache
de l'app (cle = URL sans jeton) ; pwa/sw.js v1.99.0 le sert quand le PC ne repond pas. Bibliotheque : « 📥 Gardes sur ce
telephone » (liste, taille, ▶, 🗑), visible meme PC eteint. Stockage persistant demande (navigator.storage.persist).
Verifie ses ancres, sinon n'ecrit rien.
"""
import shutil
p = r"D:\Download\02-Apps-Web\Repo-github\App\manga-studio\manga_studio.html"
s = open(p, encoding="utf-8").read()


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:80])
    s = s.replace(a, b)


for a, b in (("<title>Manga Studio v1.98.0</title>", "<title>Manga Studio v1.99.0</title>"),
             ('id="verBadge">v1.98.0<', 'id="verBadge">v1.99.0<'),
             ('const VERSION = "1.98.0";', 'const VERSION = "1.99.0";')):
    rep(a, b)

rep('''  <div id="chapList" class="chap-list"></div>''',
    '''  <!-- v1.99.0 : narrations gardees DANS ce telephone (lecture PC eteint) -->
  <div class="card hl-box" id="hlBox" hidden>
    <div class="vid-tete"><b id="hlTitre">📥 Gardés sur ce téléphone</b></div>
    <p class="muted aide" style="margin:4px 0 6px">Se lisent même PC éteint, sans réseau. Pages en VO, sans musique.</p>
    <div id="hlListe" class="vid-liste"></div>
  </div>
  <div id="chapList" class="chap-list"></div>''')
rep('''.narr-run .nr-act{grid-column:2;grid-row:1;display:grid;grid-template-columns:repeat(4,34px);gap:4px}''',
    '''.narr-run .nr-act{grid-column:2;grid-row:1;display:grid;grid-template-columns:repeat(5,34px);gap:4px}
.hl-box{margin:0 0 12px}.hl-it{display:grid;grid-template-columns:minmax(0,1fr) 32px 32px;gap:4px 6px;align-items:center;padding:6px 0;border-top:1px solid var(--line)}
.hl-it .hl-nom{font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.hl-it small{grid-column:1 / -1;color:var(--dim);font-size:11px}
.hl-it .btn.sm{width:32px;height:30px;padding:0;justify-content:center}''')
rep('''      + (n.etat !== "en cours" ? '<button class="btn sm danger" data-suppr-narr="' + i + '" title="supprimer cette narration">🗑</button>' : vide)''',
    '''      + (fini && n.audio ? '<button class="btn sm" data-hl="' + i + '" title="' + (hlGarde(CHAP_OPEN, n.tag) ? "gardé sur ce téléphone — toucher pour le retirer"
           : "garder sur ce téléphone : se lit PC éteint (~" + Math.round((n.pages || 20) * 2.2) + " Mo)") + '">' + (hlGarde(CHAP_OPEN, n.tag) ? "✅" : "📥") + "</button>" : vide)
      + (n.etat !== "en cours" ? '<button class="btn sm danger" data-suppr-narr="' + i + '" title="supprimer cette narration">🗑</button>' : vide)''')
rep('''$("narrRuns").onclick = async e => {''',
    '''$("narrRuns").onclick = async e => {
  const hb = e.target.closest("[data-hl]");
  if (hb){
    const n = NARRS[+hb.dataset.hl]; if (!n) return;
    try {
      if (hlGarde(CHAP_OPEN, n.tag)){ if (confirm("Retirer « " + n.tag + " » de ce téléphone ?")) await hlRetirer(CHAP_OPEN, n.tag); }
      else { hb.disabled = true; hb.textContent = "⏳"; await hlGarder(CHAP_OPEN, n.tag); }
    } catch (err){ log("hors-ligne : " + err.message, "e"); alert(err.message); }
    await refreshNarrs().catch(() => {}); return;
  }''')

JS = r'''/* ----- v1.99.0 : HORS-LIGNE (dans ce telephone) ----- */
const HL_CACHE = "manga-horsligne-v1";
const hlCle = u => { const x = new URL(u, location.href); x.searchParams.delete("_k"); return x.toString(); };
// L'index vit DANS le cache, avec les fichiers : localStorage n'est ecrit sur disque qu'avec retard sur Android
// (mesure sur le Samsung le 22/09 : app fermee juste apres « garder » -> 36 fichiers gardes, index PERDU).
const HL_IDX_CLE = () => hlCle(location.origin + "/manga/__index_horsligne.json");
let HL_IDX = (() => { try { return JSON.parse(localStorage.getItem("manga_hl") || "[]"); } catch { return []; } })();
const hlIndex = () => HL_IDX.slice();
async function hlSauveIndex(l){
  HL_IDX = l.slice();
  try { localStorage.setItem("manga_hl", JSON.stringify(l)); } catch {}
  try { await (await caches.open(HL_CACHE)).put(HL_IDX_CLE(), new Response(JSON.stringify(l), { headers: { "Content-Type": "application/json" } })); } catch {}
}
async function hlChargerIndex(){
  try {
    const r = await (await caches.open(HL_CACHE)).match(HL_IDX_CLE());
    if (r){ HL_IDX = await r.json(); try { localStorage.setItem("manga_hl", JSON.stringify(HL_IDX)); } catch {} }
    else if (HL_IDX.length) await hlSauveIndex(HL_IDX);       // ancien index (localStorage seul) : recopie
  } catch {}
  hlRendre();
}
const hlGarde = (d, tag) => hlIndex().some(x => x.d === d && x.tag === tag);
async function hlGarder(d, tag){
  if (!("caches" in window)) throw new Error("ce navigateur ne sait pas garder de fichiers");
  try { if (navigator.storage && navigator.storage.persist) await navigator.storage.persist(); } catch {}
  const n = await api("/manga/narration?d=" + encodeURIComponent(d) + "&tag=" + encodeURIComponent(tag));
  const urls = [CFG.base + "/manga/narration?d=" + encodeURIComponent(d) + "&tag=" + encodeURIComponent(tag)];
  (n.pages || []).filter(p => p.type === "histoire" || p.audio).forEach(p => {
    if (p.file) urls.push(srcURL(d + "/" + p.file));
    if (p.audio) urls.push(srcURL(n.base + "/" + p.audio));
  });
  let prec = null;
  try { prec = await api("/manga/precedemment?d=" + encodeURIComponent(d)); } catch {}
  if (prec){
    urls.push(CFG.base + "/manga/precedemment?d=" + encodeURIComponent(d));
    Object.values(prec.modes || {}).filter(m => m.etat === "fini").forEach(m => (m.data.items || []).forEach(x => {
      if (x.img) urls.push(srcURL(x.img)); if (x.audio) urls.push(srcURL(m.base + "/" + x.audio)); }));
  }
  const c = await caches.open(HL_CACHE), o = { headers: CFG.key ? { Authorization: "Bearer " + CFG.key } : {} };
  let octets = 0, k = 0;
  for (const u of urls){
    const r = await fetch(u, o);
    if (!r.ok) throw new Error("HTTP " + r.status + " en gardant " + u.split("?")[0].split("/").pop());
    const b = await r.blob(); octets += b.size;
    await c.put(hlCle(u), new Response(b, { headers: { "Content-Type": r.headers.get("Content-Type") || "application/octet-stream" } }));
    if (++k % 5 === 0) toast("📥 " + k + "/" + urls.length);
  }
  const c0 = CHAPS.find(x => x.dir === d) || {};
  const l = hlIndex().filter(x => !(x.d === d && x.tag === tag));
  l.push({ d, tag, titre: n.title || c0.title || d.split("/")[0], chapitre: String(n.chapter || c0.chapter || ""), voix: n.voice || "",
           pages: (n.pages || []).length, octets, urls: urls.map(hlCle), quand: new Date().toLocaleString("sv-SE").slice(0, 16) });   // heure LOCALE (toISOString = UTC)
  await hlSauveIndex(l); hlRendre();
  log("hors-ligne : " + d + " · " + tag + " gardé (" + urls.length + " fichiers, " + fmtGo(octets) + ")");
  toast("📥 gardé sur ce téléphone : " + fmtGo(octets));
}
async function hlRetirer(d, tag){
  const e = hlIndex().find(x => x.d === d && x.tag === tag); if (!e) return;
  const autres = new Set(hlIndex().filter(x => x !== e && !(x.d === d && x.tag === tag)).flatMap(x => x.urls || []));
  const c = await caches.open(HL_CACHE);
  for (const u of e.urls || []) if (!autres.has(u)) await c.delete(u);     // un « Precedemment » partage reste
  await hlSauveIndex(hlIndex().filter(x => !(x.d === d && x.tag === tag))); hlRendre();
  log("hors-ligne : " + d + " · " + tag + " retiré");
}
function hlRendre(){
  const l = hlIndex().sort((a, b) => (a.titre + a.chapitre.padStart(5, "0")).localeCompare(b.titre + b.chapitre.padStart(5, "0")));
  $("hlBox").hidden = !l.length;
  $("hlTitre").textContent = "📥 Gardés sur ce téléphone (" + l.length + " · " + fmtGo(l.reduce((a, x) => a + (x.octets || 0), 0)) + ")";
  $("hlListe").innerHTML = l.map((x, i) => '<div class="hl-it"><span class="hl-nom">' + esc(x.titre) + " — ch. " + esc(x.chapitre) + "</span>"
    + '<button class="btn sm" data-hl-lire="' + i + '" title="lire (même PC éteint)">▶</button>'
    + '<button class="btn sm danger" data-hl-suppr="' + i + '" title="retirer de ce téléphone">🗑</button>'
    + "<small>" + esc(x.voix || x.tag) + " · " + x.pages + " p. · " + fmtGo(x.octets || 0) + " · gardé le " + esc(x.quand.replace("T", " ")) + "</small></div>").join("");
  $("hlListe").onclick = async ev => {
    const b = ev.target.closest("[data-hl-lire],[data-hl-suppr]"); if (!b) return;
    const x = l[+(b.dataset.hlLire ?? b.dataset.hlSuppr)]; if (!x) return;
    if (b.dataset.hlSuppr != null){ if (confirm("Retirer « " + x.titre + " ch. " + x.chapitre + " » de ce téléphone ?")) await hlRetirer(x.d, x.tag); return; }
    hlLire(x).catch(err => { log("hors-ligne : " + err.message, "e"); alert(err.message); });
  };
}
// Lecture d'une narration gardee : le lecteur ordinaire, ses requetes servies par le service worker si le PC dort.
async function hlLire(x){
  CHAP_OPEN = x.d; CHAP_PAGE_LIST = []; TRADS = []; MUS.effectif = [];
  try { PREC = await api("/manga/precedemment?d=" + encodeURIComponent(x.d)); } catch { PREC = null; }
  await ouvrirLecteur([x.tag]);
}
hlRendre(); hlChargerIndex();

/* ----- Lecteur : une file de narrations (1 = ecoute normale ; N = ecoute a l'aveugle) ----- */'''
rep('''/* ----- Lecteur : une file de narrations (1 = ecoute normale ; N = ecoute a l'aveugle) ----- */''', JS)
shutil.copy(p, p + ".bak-20260922-v199")
open(p, "w", encoding="utf-8").write(s)
print("app v1.99.0 OK")
