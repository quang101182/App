# -*- coding: utf-8 -*-
"""App v1.96.0 -> v1.97.0 : telecharger un GROUPE de videos (etape 15, Quang 22/09 09h17).
Panneau Videos de la serie : selection GARDEE (elle se perdait a chaque rafraichissement, toutes les 4 s pendant une
fabrication), TOUT coche par defaut (demande Quang), « Tout » / « Rien » / plage « ch. X a Y », compte + poids ;
« ⬇ Une par une » ou « ⬇ En une archive .zip » (proxy /manga/videos_zip, en flux). Verifie ses ancres.
"""
import shutil
p = r"D:\Download\02-Apps-Web\Repo-github\App\manga-studio\manga_studio.html"
s = open(p, encoding="utf-8").read()


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:80])
    s = s.replace(a, b)


for a, b in (("<title>Manga Studio v1.96.0</title>", "<title>Manga Studio v1.97.0</title>"),
             ('id="verBadge">v1.96.0<', 'id="verBadge">v1.97.0<'),
             ('const VERSION = "1.96.0";', 'const VERSION = "1.97.0";')):
    rep(a, b)

rep('''      <button class="btn sm" id="vidDl" title="télécharger les vidéos cochées, une par une">⬇ Télécharger la sélection</button>
    </div>''',
    '''    </div>
    <!-- v1.97.0 : selection gardee, tout coche par defaut, telechargement en groupe -->
    <div class="vid-selbar">
      <button class="btn sm" id="vidTout">☑ Tout</button><button class="btn sm" id="vidRien">☐ Rien</button>
      <span class="vid-plage">ch. <input id="vidDe" inputmode="decimal" placeholder="1"> à <input id="vidA" inputmode="decimal" placeholder="…">
        <button class="btn sm" id="vidPlage" title="ne cocher que ces chapitres">Cocher</button></span>
      <span class="muted" id="vidCompte"></span>
    </div>
    <div class="vid-actions">
      <button class="btn sm" id="vidDl" title="télécharger les vidéos cochées, une par une (le téléphone peut en bloquer au-delà de quelques-unes)">⬇ Une par une</button>
      <button class="btn sm pri" id="vidZip" title="toutes les vidéos cochées dans UN fichier .zip (recommandé au-delà de 3)">⬇ En une archive .zip</button>
    </div>''')
rep('''.vid-it .narr-pbar{grid-column:2 / -1}''',
    '''.vid-it .narr-pbar{grid-column:2 / -1}
.vid-selbar{display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin:6px 0}
.vid-plage{display:inline-flex;align-items:center;gap:4px;font-size:12px;color:var(--dim)}
.vid-plage input{width:52px;padding:3px 6px;font-size:12px}
#vidCompte{font-size:12px}''')

rep('''    + (avecCase ? '<input type="checkbox" data-vid-coche="' + i + '"' + (e.cle === "sansvoix" ? " disabled" : "") + ">" : vide)''',
    '''    + (avecCase ? '<input type="checkbox" data-vid-coche="' + i + '"' + (e.cle === "sansvoix" ? " disabled" : "")
       + (vidSel().has(c.d) ? " checked" : "") + ">" : vide)''')
rep('''const vidCoches = () => [...document.querySelectorAll("#vidListe [data-vid-coche]:checked")].map(x => VIDS.chapitres[+x.dataset.vidCoche]);''',
    '''// v1.97.0 : la selection est un ETAT (par serie), plus la lecture des cases : un rafraichissement ne la perd plus.
// Par defaut TOUT est coche (Quang 09h17). Les chapitres ajoutes ensuite a la serie arrivent coches aussi.
const VID_SEL = {};
function vidSel(){
  const k = VIDS.serie || "";
  if (!VID_SEL[k]) VID_SEL[k] = { set: new Set(), vus: new Set() };
  const e = VID_SEL[k];
  VIDS.chapitres.forEach(c => { if (!e.vus.has(c.d)){ e.vus.add(c.d); e.set.add(c.d); } });
  return e.set;
}
const vidCoches = () => VIDS.chapitres.filter(c => vidSel().has(c.d));
const fmtGo = o => o >= 1e9 ? (o / 1e9).toFixed(2).replace(".", ",") + " Go" : Math.round(o / 1e6) + " Mo";
function vidCompte(){
  const l = vidCoches(), av = l.filter(c => (c.videos || []).length);
  const o = av.reduce((a, c) => a + (c.videos[0].taille || 0), 0);
  $("vidCompte").textContent = l.length + " coché(s) · " + av.length + " vidéo(s) prête(s) · " + fmtGo(o);
  $("vidDl").disabled = $("vidZip").disabled = !av.length;
}''')
rep('''  $("vidListe").innerHTML = VIDS.chapitres.map((c, i) => vidLigne(c, i, true)).join("") || '<p class="muted aide" style="margin:0">Aucun chapitre.</p>';''',
    '''  $("vidListe").innerHTML = VIDS.chapitres.map((c, i) => vidLigne(c, i, true)).join("") || '<p class="muted aide" style="margin:0">Aucun chapitre.</p>';
  vidCompte();''')
rep('''function vidVoixChange(e){
  const sel = e.target.closest("[data-vid-voix]"); if (!sel) return;''',
    '''function vidVoixChange(e){
  const cb = e.target.closest("[data-vid-coche]");
  if (cb){ const c = VIDS.chapitres[+cb.dataset.vidCoche]; if (c){ cb.checked ? vidSel().add(c.d) : vidSel().delete(c.d); vidCompte(); } return; }
  const sel = e.target.closest("[data-vid-voix]"); if (!sel) return;''')
rep('''$("vidDl").onclick = async () => {                     // une par une, 1,5 s d'ecart : PC et telephone acceptent''',
    '''$("vidTout").onclick = () => { VIDS.chapitres.forEach(c => vidSel().add(c.d)); vidRendre(); };
$("vidRien").onclick = () => { vidSel().clear(); vidRendre(); };
$("vidPlage").onclick = () => {
  const de = parseFloat(($("vidDe").value || "").replace(",", ".")), a = parseFloat(($("vidA").value || "").replace(",", "."));
  const lo = isNaN(de) ? -Infinity : de, hi = isNaN(a) ? Infinity : a;
  vidSel().clear();
  VIDS.chapitres.forEach(c => { const n = parseFloat(c.chapitre); if (!isNaN(n) && n >= lo && n <= hi) vidSel().add(c.d); });
  vidRendre(); toast(vidCoches().length + " chapitre(s) coché(s)");
};
$("vidZip").onclick = () => {
  const l = vidCoches().filter(c => (c.videos || []).length);
  if (!l.length){ toast("aucune vidéo prête parmi les chapitres cochés"); return; }
  const o = l.reduce((a, c) => a + (c.videos[0].taille || 0), 0);
  if (o > 2e9 && !confirm("L'archive fera " + fmtGo(o) + " (" + l.length + " vidéos). La télécharger ?")) return;
  const a = document.createElement("a");
  a.href = CFG.base + "/manga/videos_zip?serie=" + encodeURIComponent(VIDS.serie) + "&d=" + encodeURIComponent(l.map(c => c.d.split("/").pop()).join(","))
    + (CFG.key ? "&_k=" + encodeURIComponent(CFG.key) : "");
  a.download = ""; document.body.appendChild(a); a.click(); a.remove();
  log("archive demandée : " + l.length + " vidéo(s), " + fmtGo(o));
};
$("vidDl").onclick = async () => {                     // une par une, 1,5 s d'ecart : PC et telephone acceptent''')
shutil.copy(p, p + ".bak-20260922-v197")
open(p, "w", encoding="utf-8").write(s)
print("app v1.97.0 OK")
