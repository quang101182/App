# -*- coding: utf-8 -*-
"""App v1.99.0 -> v2.0.0 : TELECOMMANDE de la fenetre de capture (etape 17, Quang 22/09 10h29-10h30).
Dans « Capturer un chapitre » : « 🕹 Piloter la fenetre de capture » -> onglets (toucher = basculer, ＋, ✕), ◀ ▶ ⟳ + adresse,
l'ecran de l'onglet (toucher = cliquer, glisser = defiler), ⬆ ⬇ ← → Page, texte, et « ✔ Capturer cet onglet » qui le
selectionne dans la liste de capture. Ecran rafraichi apres chaque geste et toutes les 2 s tant que le panneau est ouvert.
Verifie ses ancres, sinon n'ecrit rien.
"""
import shutil
p = r"D:\Download\02-Apps-Web\Repo-github\App\manga-studio\manga_studio.html"
s = open(p, encoding="utf-8").read()


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:80])
    s = s.replace(a, b)


for a, b in (("<title>Manga Studio v1.99.0</title>", "<title>Manga Studio v2.0.0</title>"),
             ('id="verBadge">v1.99.0<', 'id="verBadge">v2.0.0<'),
             ('const VERSION = "1.99.0";', 'const VERSION = "2.0.0";')):
    rep(a, b)

rep('''      <button class="btn sm" id="btnCapTabs">↻ Onglets</button>
    </div>''',
    '''      <button class="btn sm" id="btnCapTabs">↻ Onglets</button>
      <button class="btn sm" id="btnPilote" title="voir et piloter la fenêtre de capture depuis ici (téléphone compris)">🕹 Piloter la fenêtre</button>
    </div>
    <!-- v2.0.0 : TELECOMMANDE de la fenetre de capture (CDP 9223 relaye par le proxy) -->
    <div class="pil-box" id="pilBox" hidden>
      <div class="pil-onglets" id="pilOnglets"></div>
      <div class="pil-nav">
        <button class="btn sm" data-pil="retour" title="page précédente">◀</button>
        <button class="btn sm" data-pil="avant" title="page suivante">▶</button>
        <button class="btn sm" data-pil="recharger" title="recharger">⟳</button>
        <input id="pilUrl" inputmode="url" placeholder="adresse ou recherche">
        <button class="btn sm" id="pilAller">Aller</button>
      </div>
      <div class="pil-ecran"><img id="pilEcran" alt="écran de la fenêtre de capture"><span id="pilEtat" class="muted"></span></div>
      <div class="pil-nav">
        <button class="btn sm" data-pil-mol="-700" title="remonter">⬆</button>
        <button class="btn sm" data-pil-mol="700" title="descendre">⬇</button>
        <button class="btn sm" data-pil-t="gauche" title="flèche gauche (page précédente d'un lecteur)">←</button>
        <button class="btn sm" data-pil-t="droite" title="flèche droite (page suivante d'un lecteur)">→</button>
        <button class="btn sm" data-pil-t="pagebas" title="Page suivante">Page ⬇</button>
        <button class="btn sm" data-pil-t="entree" title="Entrée">⏎</button>
      </div>
      <div class="pil-nav">
        <input id="pilTexte" placeholder="texte à taper dans la page (après avoir touché un champ)">
        <button class="btn sm" id="pilEnvoyer">Taper</button>
        <button class="btn sm pri" id="pilChoisir" title="sélectionner cet onglet pour la capture ci-dessous">✔ Capturer cet onglet</button>
      </div>
    </div>''')
rep('''.trad-ligne{display:flex;align-items:center;gap:6px;flex-wrap:wrap}''',
    '''.trad-ligne{display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.pil-box{margin:8px 0;padding:8px;border:1px solid var(--line);border-radius:10px;background:var(--panel2)}
.pil-onglets{display:flex;gap:6px;overflow-x:auto;padding-bottom:6px}
.pil-onglets .btn{flex:none;max-width:180px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pil-onglets .btn.on{border-color:var(--accent2);color:var(--txt)}
.pil-nav{display:flex;gap:6px;align-items:center;margin:6px 0;flex-wrap:wrap}
.pil-nav input{flex:1;min-width:0}
.pil-ecran{position:relative;touch-action:none;user-select:none}
.pil-ecran img{display:block;width:100%;border-radius:6px;background:#000;min-height:120px;cursor:pointer}
.pil-ecran span{position:absolute;right:6px;bottom:6px;font-size:11px;background:#000a;padding:2px 6px;border-radius:6px}''')

JS = r'''/* ----- v2.0.0 : TELECOMMANDE de la fenetre de capture ----- */
const PIL = { id: null, onglets: [], timer: 0, url: "", enCours: false, objet: null };
async function pilOnglets(){
  const j = await api("/manga/pilote_onglets");
  PIL.onglets = j.onglets || [];
  if (!j.edge){ $("pilOnglets").innerHTML = '<span class="muted">fenêtre de capture fermée — « Ouvrir la fenêtre de capture »</span>'; PIL.id = null; return; }
  if (!PIL.onglets.some(o => o.id === PIL.id)) PIL.id = (PIL.onglets.find(o => o.actif) || PIL.onglets[0] || {}).id || null;
  $("pilOnglets").innerHTML = PIL.onglets.map(o => '<button class="btn sm' + (o.id === PIL.id ? " on" : "") + '" data-pil-onglet="' + esc(o.id)
      + '" title="' + esc(o.titre + " — " + o.url) + '">' + esc((o.titre || o.url).slice(0, 40)) + "</button>").join("")
    + '<button class="btn sm" data-pil-nouvel title="nouvel onglet">＋</button>'
    + (PIL.id ? '<button class="btn sm danger" data-pil-fermer title="fermer cet onglet">✕</button>' : "");
  if (j.capture) $("pilEtat").textContent = "capture en cours : pilotage suspendu";
}
async function pilEcran(){
  if ($("pilBox").hidden || !PIL.id || PIL.enCours || document.hidden) return;
  PIL.enCours = true;
  try {
    const r = await fetch(CFG.base + "/manga/pilote_ecran?id=" + encodeURIComponent(PIL.id), { headers: CFG.key ? { Authorization: "Bearer " + CFG.key } : {} });
    if (!r.ok){ $("pilEtat").textContent = "écran indisponible (" + r.status + ")"; if (r.status === 404) await pilOnglets(); return; }
    const u = decodeURIComponent(r.headers.get("X-Url") || "");
    const b = await r.blob(), url = URL.createObjectURL(b);
    $("pilEcran").src = url; if (PIL.objet) URL.revokeObjectURL(PIL.objet); PIL.objet = url;
    $("pilEcran").dataset.h = r.headers.get("X-Hauteur") || "1000";          // glisser = defiler d'autant (px CSS)
    if (u !== PIL.url){ PIL.url = u; if (document.activeElement !== $("pilUrl")) $("pilUrl").value = u; }
    $("pilEtat").textContent = decodeURIComponent(r.headers.get("X-Titre") || "").slice(0, 50);
  } catch (e){ $("pilEtat").textContent = "écran : " + e.message; }
  finally { PIL.enCours = false; }
}
function pilBoucle(){ clearInterval(PIL.timer); PIL.timer = setInterval(pilEcran, 2000); }
async function pilAction(action, extra){
  if (!PIL.id && action !== "nouvel") return;
  const r = await api("/manga/pilote", Object.assign({ id: PIL.id, action }, extra || {}));
  if (r.error) throw new Error(r.error);
  if (r.id) PIL.id = r.id;
  if (["nouvel", "fermer", "activer", "url", "retour", "avant"].includes(action)) setTimeout(() => pilOnglets().catch(() => {}), 900);
  setTimeout(pilEcran, 250); setTimeout(pilEcran, 1200);
}
const pilErr = e => { $("pilEtat").textContent = "⚠ " + e.message; log("pilotage : " + e.message, "w"); };
$("btnPilote").onclick = async () => {
  $("pilBox").hidden = !$("pilBox").hidden;
  if ($("pilBox").hidden){ clearInterval(PIL.timer); return; }
  try { await pilOnglets(); await pilEcran(); pilBoucle(); } catch (e){ pilErr(e); }
};
$("pilOnglets").onclick = e => {
  const b = e.target.closest("[data-pil-onglet],[data-pil-nouvel],[data-pil-fermer]"); if (!b) return;
  if (b.dataset.pilOnglet){ PIL.id = b.dataset.pilOnglet; pilAction("activer").catch(pilErr); pilOnglets().catch(() => {}); }
  else if (b.dataset.pilNouvel != null) pilAction("nouvel", { url: "about:blank" }).then(() => $("pilUrl").focus()).catch(pilErr);
  else if (confirm("Fermer cet onglet de la fenêtre de capture ?")) pilAction("fermer").then(() => { PIL.id = null; }).catch(pilErr);
};
document.querySelectorAll("[data-pil]").forEach(b => b.onclick = () => pilAction(b.dataset.pil).catch(pilErr));
document.querySelectorAll("[data-pil-mol]").forEach(b => b.onclick = () => pilAction("molette", { x: 0.5, y: 0.5, dy: +b.dataset.pilMol }).catch(pilErr));
document.querySelectorAll("[data-pil-t]").forEach(b => b.onclick = () => pilAction("touche", { touche: b.dataset.pilT }).catch(pilErr));
function pilAller(){
  let u = $("pilUrl").value.trim(); if (!u) return;
  if (!/^https?:\/\//.test(u) && !/^[\w-]+(\.[\w-]+)+(\/|$)/.test(u)) u = "https://www.google.com/search?q=" + encodeURIComponent(u);   // une recherche
  $("pilUrl").blur(); pilAction("url", { url: u }).catch(pilErr);
}
$("pilAller").onclick = pilAller;
$("pilUrl").addEventListener("keydown", e => { if (e.key === "Enter"){ e.preventDefault(); pilAller(); } });
$("pilEnvoyer").onclick = () => { const t = $("pilTexte").value; if (!t) return; pilAction("texte", { texte: t }).then(() => { $("pilTexte").value = ""; }).catch(pilErr); };
// ecran : toucher = cliquer a cet endroit ; glisser verticalement = defiler (le geste d'un telephone)
(function(){
  const im = $("pilEcran"); let d = null;
  im.addEventListener("pointerdown", e => { d = { x: e.clientX, y: e.clientY, t: Date.now() }; im.setPointerCapture(e.pointerId); });
  im.addEventListener("pointerup", e => {
    if (!d) return; const r = im.getBoundingClientRect(), dy = e.clientY - d.y, dx = e.clientX - d.x; const a = d; d = null;
    if (Math.abs(dy) > 25 && Math.abs(dy) > Math.abs(dx)){
      pilAction("molette", { x: (a.x - r.left) / r.width, y: (a.y - r.top) / r.height, dy: Math.round(-dy / r.height * (+im.dataset.h || 1000) * 1.5) }).catch(pilErr);
    } else if (Math.abs(dx) < 12 && Math.abs(dy) < 12){
      pilAction("clic", { x: (e.clientX - r.left) / r.width, y: (e.clientY - r.top) / r.height }).catch(pilErr);
    }
  });
  im.addEventListener("pointercancel", () => { d = null; });
})();
$("pilChoisir").onclick = async () => {
  const o = PIL.onglets.find(x => x.id === PIL.id); if (!o) return;
  await refreshCapTabs();
  const i = CAP_TABS.findIndex(t => t.url === (PIL.url || o.url));
  if (i < 0){ alert("Cet onglet n'est pas une page capturable (adresse http/https)."); return; }
  $("capTab").value = String(i); $("capTab").dispatchEvent(new Event("change"));
  toast("✔ onglet choisi pour la capture"); $("capTitre").scrollIntoView({ behavior: "smooth", block: "center" });
};

'''
rep('''/* =====================================================================
   CAPTURE (v1.71.0) -- manga-fetch enveloppe par le proxy, pilote depuis l'app
   ===================================================================== */''',
    '''/* =====================================================================
   CAPTURE (v1.71.0) -- manga-fetch enveloppe par le proxy, pilote depuis l'app
   ===================================================================== */
''' + JS)
shutil.copy(p, p + ".bak-20260922-v200")
open(p, "w", encoding="utf-8").write(s)
print("app v2.0.0 OK")
