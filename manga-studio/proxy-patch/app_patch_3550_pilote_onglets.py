"""app 3.5.4 -> 3.5.5 (Quang 27/09 21h55-21h58 : télécommande de la fenêtre de capture « déroutante » -- on ne sait pas fermer un
onglet, et toucher un onglet le fait passer en première position ; « je veux la totalité […] principale et secondaire ») :
- onglets affichés dans l'ORDRE DU PC (serveur patch_pilote_ordre : barre d'onglets lue par l'accessibilité Windows, sinon
  ordre stable) -- toucher un onglet ne le déplace plus ;
- un ✕ sur CHAQUE onglet ; fermeture avec 5 s pour ANNULER (plus de confirmation) ;
- l'onglet choisi reste visible dans la rangée (défilement automatique).
Copie, node --check, remplacement."""
import os, re, shutil, subprocess, sys

F = "D:/Download/02-Apps-Web/Repo-github/App/manga-studio/manga_studio.html"
TMP = os.path.join(os.environ.get("TEMP", "."), "manga_studio_355.html")
s = open(F, encoding="utf-8", newline="").read()
if 'const VERSION = "3.5.5"' in s:
    print("deja applique"); sys.exit(0)


def rep(a, b):
    global s
    for nl in ("\r\n", "\n", "\r\r\n"):
        a2, b2 = a.replace("\n", nl), b.replace("\n", nl)
        if s.count(a2) == 1:
            s = s.replace(a2, b2); return
    raise SystemExit("ancre introuvable : " + a[:80])


rep("<title>Manga Studio v3.5.4</title>", "<title>Manga Studio v3.5.5</title>")
rep('id="verBadge">v3.5.4</span>', 'id="verBadge">v3.5.5</span>')
rep('const VERSION = "3.5.4";', 'const VERSION = "3.5.5";   // v3.5.5 : télécommande -- onglets dans l ordre du PC, ✕ sur chaque onglet avec annulation ')

rep('''.pil-onglets .btn.on{border-color:var(--accent2);color:var(--txt)}''',
    '''.pil-onglets .btn.on{border-color:var(--accent2);color:var(--txt)}
/* v3.5.5 : un onglet = une pastille (titre + ✕) */
.pil-o{flex:none;display:inline-flex;align-items:stretch;border:1px solid var(--line);border-radius:8px;background:var(--panel2);max-width:210px}
.pil-o.on{border-color:var(--accent2);box-shadow:0 0 0 1px var(--accent2)}
.pil-o .pil-t{flex:1;min-width:0;background:none;border:0;color:var(--dim);font:inherit;font-size:13px;padding:6px 4px 6px 9px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;cursor:pointer;text-align:left}
.pil-o.on .pil-t{color:var(--txt)}
.pil-o .pil-x{flex:none;background:none;border:0;border-left:1px solid var(--line);color:var(--dim);font:inherit;font-size:13px;padding:0 9px;cursor:pointer;min-width:34px}
.pil-o .pil-x:hover{color:#ff9d96}
.pil-annul{display:inline-flex;align-items:center;gap:6px;font-size:12.5px;color:var(--dim);margin-right:10px}
.pil-annul-l{margin:2px 0 6px}.pil-annul-l[hidden]{display:none}''')

rep('''const PIL = { id: null, onglets: [], timer: 0, url: "", enCours: false, objet: null };''',
    '''const PIL = { id: null, onglets: [], timer: 0, url: "", enCours: false, objet: null, fermes: {}, vu: "" };   // v3.5.5 : fermes = {id: minuterie}''')

rep('''  if (!PIL.onglets.some(o => o.id === PIL.id)) PIL.id = (PIL.onglets.find(o => o.actif) || PIL.onglets[0] || {}).id || null;
  $("pilOnglets").innerHTML = PIL.onglets.map(o => '<button class="btn sm' + (o.id === PIL.id ? " on" : "") + '" data-pil-onglet="' + esc(o.id)
      + '" title="' + esc(o.titre + " — " + o.url) + '">' + esc((o.titre || o.url).slice(0, 40)) + "</button>").join("")
    + '<button class="btn sm" data-pil-nouvel title="nouvel onglet">＋</button>'
    + (PIL.id ? '<button class="btn sm danger" data-pil-fermer title="fermer cet onglet">✕</button>' : "");''',
    '''  const vis = PIL.onglets.filter(o => !PIL.fermes[o.id]);                      // v3.5.5 : en cours de fermeture = masqué
  if (!vis.some(o => o.id === PIL.id)) PIL.id = (vis.find(o => o.actif) || vis[0] || {}).id || null;
  const annul = Object.keys(PIL.fermes).map(id => { const o = PIL.onglets.find(x => x.id === id) || {};
    return '<span class="pil-annul">🗑 « ' + esc((o.titre || o.url || "onglet").slice(0, 22)) + ' » fermé · <button class="dpl-lien" data-pil-annul="' + esc(id) + '">Annuler</button></span>'; }).join("");
  $("pilOnglets").innerHTML = vis.map(o => '<span class="pil-o' + (o.id === PIL.id ? " on" : "") + '"><button class="pil-t" data-pil-onglet="' + esc(o.id)
      + '" title="' + esc(o.titre + " — " + o.url) + '">' + esc((o.titre || o.url).slice(0, 40)) + '</button><button class="pil-x" data-pil-x="' + esc(o.id)
      + '" title="fermer cet onglet (5 s pour annuler)" aria-label="fermer l’onglet">✕</button></span>').join("")
    + '<button class="btn sm" data-pil-nouvel title="nouvel onglet">＋</button>';
  let al = $("pilAnnul"); if (!al){ al = document.createElement("div"); al.id = "pilAnnul"; al.className = "pil-annul-l"; $("pilOnglets").after(al);
    al.addEventListener("click", e => $("pilOnglets").onclick(e)); }        // meme gestionnaire que la rangee
  al.innerHTML = annul; al.hidden = !annul;                                    // hors de la rangee qui defile : toujours VISIBLE
  if (PIL.vu !== PIL.id){ PIL.vu = PIL.id; const on = $("pilOnglets").querySelector(".pil-o.on"); if (on) on.scrollIntoView({ inline: "nearest", block: "nearest" }); }''')

rep('''  const b = e.target.closest("[data-pil-onglet],[data-pil-nouvel],[data-pil-fermer]"); if (!b) return;
  if (b.dataset.pilOnglet){''',
    '''  const b = e.target.closest("[data-pil-onglet],[data-pil-nouvel],[data-pil-fermer],[data-pil-x],[data-pil-annul]"); if (!b) return;
  if (b.dataset.pilX){ pilFermerOnglet(b.dataset.pilX); return; }                  // v3.5.5
  if (b.dataset.pilAnnul){ clearTimeout(PIL.fermes[b.dataset.pilAnnul]); delete PIL.fermes[b.dataset.pilAnnul]; pilOnglets().catch(() => {}); toast("↶ onglet gardé"); return; }
  if (b.dataset.pilOnglet){''')

rep('''document.querySelectorAll("[data-pil]").forEach(b => b.onclick = () => pilAction(b.dataset.pil).catch(pilErr));''',
    '''document.querySelectorAll("[data-pil]").forEach(b => b.onclick = () => pilAction(b.dataset.pil).catch(pilErr));
function pilFermerOnglet(id){                     // v3.5.5 : masqué tout de suite, VRAIMENT fermé après 5 s sauf « Annuler »
  if (PIL.fermes[id]) return;
  PIL.fermes[id] = setTimeout(async () => {
    try { const r = await api("/manga/pilote", { id, action: "fermer" }); if (r.error) throw new Error(r.error); }
    catch (err) { toast("onglet non fermé : " + err.message); }
    delete PIL.fermes[id]; if (PIL.id === id) PIL.id = null;
    pilOnglets().catch(() => {});
  }, 5000);
  pilOnglets().catch(() => {});
}''')

rep('''function pilBoucle(){ clearInterval(PIL.timer); PIL.timer = setInterval(pilEcran, 2000); }''',
    '''function pilBoucle(){ clearInterval(PIL.timer); let n = 0;                    // v3.5.5 : + onglets relus toutes les 6 s (ordre du PC)
  PIL.timer = setInterval(() => { pilEcran(); if (++n % 3 === 0 && !document.hidden && !$("pilBox").hidden) pilOnglets().catch(() => {}); }, 2000); }''')

open(TMP, "w", encoding="utf-8", newline="").write(s)
js = "\n".join(re.findall(r"<script>(.*?)</script>", s, re.S))
open(TMP + ".js", "w", encoding="utf-8").write(js)
r = subprocess.run(["node", "--check", TMP + ".js"], capture_output=True, text=True)
if r.returncode:
    print("node --check KO", r.stderr[:800]); sys.exit(1)
if "--essai" in sys.argv:
    print("essai OK (rien remplace) :", TMP); sys.exit(0)
shutil.copy2(F, F + ".bak-v3540")
shutil.copy2(TMP, F)
print("ok v3.5.5")
