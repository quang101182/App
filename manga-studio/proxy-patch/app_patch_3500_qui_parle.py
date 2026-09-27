"""app 3.4.7 -> 3.5.0 (S4, maquette_qui_parle_v1 validee par Quang le 27/09 20h38) : 🎭 « Qui parle ? » PENDANT la verification
des bulles. Rangee des personnages de la serie sous la page ; toucher un personnage = pinceau (bandeau a sa couleur) ; toucher une
bulle (sa pastille OU son texte) = elle est a lui (retoucher = l'IA decidera) ; ↶ annule ; « ＋ » = nouveau personnage (nom + ♂/♀,
voix libre choisie d'office : preferee du genre, sinon francaise) ; ce que l'IA a DEJA attribue (pages preparees) s'affiche en pale,
jamais enregistre. Enregistre « qui » dans la verification (serveur patch_dialogues_16 : applique tout de suite aux repliques deja
preparees ; dialogues.py 1.27.0 : impose a la preparation). Copie, node --check, remplacement."""
import os, re, shutil, subprocess, sys

F = "D:/Download/02-Apps-Web/Repo-github/App/manga-studio/manga_studio.html"
TMP = os.path.join(os.environ.get("TEMP", "."), "manga_studio_350.html")
s = open(F, encoding="utf-8", newline="").read()
if 'const VERSION = "3.5.0"' in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", NL), b.replace("\n", NL)
    assert s.count(a) == 1, (s.count(a), a[:90])
    s = s.replace(a, b)


rep("<title>Manga Studio v3.4.7</title>", "<title>Manga Studio v3.5.0</title>")
rep('id="verBadge">v3.4.7</span>', 'id="verBadge">v3.5.0</span>')
rep('const VERSION = "3.4.7";', 'const VERSION = "3.5.0";   // v3.5.0 : 🎭 « Qui parle ? » pendant la verification des bulles (pinceau par personnage, impose a la preparation) ')

# ---- CSS
rep('''.dlv-incert span{flex:1}.dlv-incert[hidden]{display:none}''',
    '''.dlv-incert span{flex:1}.dlv-incert[hidden]{display:none}
/* v3.5.0 (S4) : 🎭 qui parle -- rangee des personnages, pinceau */
.dlv-qui{max-width:880px;width:calc(100% - 20px);margin:6px auto 0;display:flex;flex-wrap:wrap;gap:5px;align-items:center;box-sizing:border-box}
.dlv-qui[hidden]{display:none}.dlv-qlab{font-size:11.5px;color:var(--dim);margin-right:1px}
.dlv-p{display:flex;align-items:center;gap:5px;border:1.5px solid var(--line);background:var(--panel2);border-radius:99px;padding:3px 10px 3px 3px;color:var(--txt);font:inherit;font-size:13px;cursor:pointer;max-width:46%;min-width:0}
.dlv-p b{font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}
.dlv-p i{width:22px;height:22px;border-radius:50%;background:var(--c);display:grid;place-items:center;font-style:normal;font-weight:800;font-size:11px;color:#111;flex:none}
.dlv-p.on{border-color:var(--c);background:color-mix(in srgb,var(--c) 28%,#141821);box-shadow:0 0 0 2px color-mix(in srgb,var(--c) 45%,transparent)}
.dlv-p.plus{padding:3px 11px;color:var(--accent2);border-style:dashed}
.dlv-aide.pinceau{color:#fff;border-color:var(--c);background:color-mix(in srgb,var(--c) 22%,#0d0f13)}
.dlv-nouv{max-width:880px;width:calc(100% - 20px);margin:6px auto 0;display:flex;gap:6px;align-items:center;box-sizing:border-box}
.dlv-nouv[hidden]{display:none}.dlv-nouv input{flex:1;min-width:0;background:var(--bg);border:1px solid var(--line);border-radius:8px;color:var(--txt);padding:7px;font:inherit}''')

# ---- HTML : rangee + saisie d'un nouveau personnage ; aide qui mentionne les personnages
rep('''<b>entourer</b> = ajouter · <b>appui long</b> sur un ajout = supprimer</span>''',
    '''<b>entourer</b> = ajouter · <b>appui long</b> sur un ajout = supprimer · 🎭 <b>un personnage</b> puis ses bulles = qui parle</span>''')
rep('''    + '<div class="dlv-incert" id="dlvIncert" hidden></div>\'''',
    '''    + '<div class="dlv-incert" id="dlvIncert" hidden></div>'
    + '<div class="dlv-qui" id="dlvQui" hidden></div>'
    + '<div class="dlv-nouv" id="dlvNouv" hidden><input id="dlvNouvNom" maxlength="40" placeholder="nom du nouveau personnage" enterkeyhint="done">'
    + '<button class="btn sm" data-dlvg="homme" title="homme">♂</button><button class="btn sm" data-dlvg="femme" title="femme">♀</button><button class="btn sm" data-dlvg="" title="annuler">✕</button></div>\'''')

# ---- etat
rep('''const DLV = { d: "", pages: [], i: 0, undo: [], seul: false, incert: new Set(), nouv: false, portee: "", aide: true };''',
    '''const DLV = { d: "", pages: [], i: 0, undo: [], seul: false, incert: new Set(), nouv: false, portee: "", aide: true, pin: "" };   // v3.5.0 : pin = pinceau (nom)''')

# ---- items : « qui » relu dans la verification enregistree
rep('''    if (aj){ absorber(aj); out.push({ id: aj.id, box: aj.box, ajout: true }); } else { const b = trouve(r); if (b){ pris.add(b); out.push(b); } } });''',
    '''    if (aj){ absorber(aj); out.push(Object.assign({ id: aj.id, box: aj.box, ajout: true }, r.qui ? { qui: r.qui } : {})); }
    else { const b = trouve(r); if (b){ pris.add(b); if (r.qui) b.qui = r.qui; out.push(b); } } });                   // v3.5.0 : qui parle''')

# ---- ouverture : pinceau range, attributions de l'IA en pale
rep('''  Object.assign(DLV, { d, pages: [], i: 0, undo: [], seul: false, incert: new Set(), portee, nouv:''',
    '''  Object.assign(DLV, { d, pages: [], i: 0, undo: [], seul: false, incert: new Set(), portee, pin: "", tous: false, nouv:''')
rep('''  DLV.pages = j.pages.map(p => Object.assign(p, { items: dlvItems(p), modif: 0 }));''',
    '''  DLV.pages = j.pages.map(p => Object.assign(p, { items: dlvItems(p), modif: 0 }));
  dlvQuiIA(); $("dlvNouv").hidden = true;''')

# ---- dessin : pastille-personnage a gauche du numero ; zone a la couleur du personnage choisi
rep('''    if (!x.ajout) h += '<rect x="' + bx + '" y="' + by + '" width="' + bw + '" height="' + bh + '" rx="' + R * 0.2 + '" fill="none" stroke="' + (x.exclu ? "#5a6070" : "#3fc7a8") + '" stroke-width="' + R * 0.1 + '" opacity=".85" pointer-events="none"/>';''',
    '''    if (!x.ajout) h += '<rect x="' + bx + '" y="' + by + '" width="' + bw + '" height="' + bh + '" rx="' + R * 0.2 + '" fill="none" stroke="' + (x.exclu ? "#5a6070" : x.qui ? dlgCouleur(x.qui) : "#3fc7a8") + '" stroke-width="' + R * (x.qui && !x.exclu ? 0.17 : 0.1) + '" opacity=".85" pointer-events="none"/>';
    const qn = x.exclu ? "" : x.qui || x.quiIA;                                // v3.5.0 : qui parle (plein = toi, pale = l'IA)
    if (qn){ const moi = !!x.qui, col = dlgCouleur(qn); let qx = cx - R * 2.05; if (qx < R) qx = cx + R * 2.05;
      h += '<g opacity="' + (moi ? 1 : 0.62) + '" pointer-events="none"><circle cx="' + qx + '" cy="' + cy + '" r="' + R * 0.92 + '" fill="' + col + '" stroke="' + (moi ? "#111" : "#fff") + '" stroke-width="' + R * 0.12 + '"'
        + (moi ? "" : ' stroke-dasharray="' + R * 0.32 + " " + R * 0.22 + '"') + '/><text x="' + qx + '" y="' + (cy + R * 0.34) + '" text-anchor="middle" font-size="' + R * 0.95 + '" font-weight="800" font-family="system-ui,sans-serif" fill="#111">' + esc(dlvInit(qn)) + "</text></g>"; }''')

# ---- barre du bas : rangee + compte des attributions
rep('''function dlvBas(){
  const L = dlvListe(), p = dlvPage(),''', '''function dlvBas(){
  dlvQuiRendre();                                                            // v3.5.0
  const L = dlvListe(), p = dlvPage(),''')
rep('''    : "Page suivante ›<small>" + actifs + " bulle" + (actifs > 1 ? "s" : "") + (p && p.modif ? " · " + p.modif + " modifiée" + (p.modif > 1 ? "s" : "") : "") + "</small>";''',
    '''    : "Page suivante ›<small>" + actifs + " bulle" + (actifs > 1 ? "s" : "") + (p && p.modif ? " · " + p.modif + " modifiée" + (p.modif > 1 ? "s" : "") : "")
      + ((n => n ? " · 🎭 " + n : "")(p ? p.items.filter(y => y.qui && !y.exclu).length : 0)) + "</small>";''')

# ---- enregistrement : « qui » part avec l'ordre et les ajouts ; attributions appliquees tout de suite (serveur)
rep('''  DLV.pages.forEach(p => { pages[p.page] = { ordre: p.items.filter(x => !x.exclu).map(x => ({ id: x.id, box: x.box })),''',
    '''  const avecQui = x => Object.assign({ id: x.id, box: x.box }, x.qui ? { qui: x.qui } : {});                // v3.5.0
  DLV.pages.forEach(p => { pages[p.page] = { ordre: p.items.filter(x => !x.exclu).map(avecQui),''')
rep('''                                             ajouts: p.items.filter(x => x.ajout && !x.exclu).map(x => ({ id: x.id, box: x.box })) }; });''',
    '''                                             ajouts: p.items.filter(x => x.ajout && !x.exclu).map(avecQui) }; });''')
rep('''  try { const r = await api("/manga/dialogues_verif", { d: DLV.d, pages }); if (r.error) throw new Error(r.error); }''',
    '''  DLV.nq = 0;
  try { const r = await api("/manga/dialogues_verif", { d: DLV.d, pages }); if (r.error) throw new Error(r.error); DLV.nq = r.qui_appliques || 0; }''')
rep('''  else { toast("🔍 bulles vérifiées et gardées"); dlgRendre(); }''',
    '''  else if (DLV.nq){ toast("🎭 " + DLV.nq + " réplique" + (DLV.nq > 1 ? "s" : "") + " attribuée" + (DLV.nq > 1 ? "s" : "") + " — leurs voix sont à refaire (🔊)"); dlgCharger(); }   // v3.5.0
  else { toast("🔍 bulles vérifiées et gardées"); dlgRendre(); }''')

# ---- toucher en mode pinceau : attribuer (pastille OU texte de la bulle)
rep('''    if (x.k >= 0 && !x.drag){ dlvSnap(); const it = p.items[x.k]; it.exclu = !it.exclu; p.modif++; dlvDessiner(); dlvBas();''',
    '''    if (DLV.pin && !x.drag){                                                 // v3.5.0 : pinceau -> la bulle touchee est a lui
      let k = x.k;
      if (k < 0 && Math.hypot(f.px - d0.px, f.py - d0.py) < 10){ const img = $("dlvImg"), W = img.naturalWidth || 1000, H = img.naturalHeight || 1400, R = +$("dlvSvg").dataset.r || 20;
        k = p.items.findIndex(it => f.x * W >= it.box.x * W - R * 0.5 && f.x * W <= (it.box.x + it.box.w) * W + R * 0.5 && f.y * H >= it.box.y * H - R * 0.5 && f.y * H <= (it.box.y + it.box.h) * H + R * 0.5); }
      if (k >= 0){ dlvSnap(); const it = p.items[k], deja = it.qui === DLV.pin; it.exclu = false; it.qui = deja ? "" : DLV.pin; p.modif++; dlvDessiner(); dlvBas();
        return dlvToast(deja ? "bulle " + (p.items.filter(y => !y.exclu).indexOf(it) + 1) + " : l'IA décidera" : "🎭 bulle " + (p.items.filter(y => !y.exclu).indexOf(it) + 1) + " : " + dlvNomAff(DLV.pin)); }
    }
    if (x.k >= 0 && !x.drag){ dlvSnap(); const it = p.items[x.k]; it.exclu = !it.exclu; p.modif++; dlvDessiner(); dlvBas();''')

# ---- fonctions : rangee, pinceau, nouveau personnage, attributions de l'IA
rep('''function dlvToast(t){''', '''/* ---- v3.5.0 (S4) : 🎭 QUI PARLE, pendant la verification ---- */
const dlvInit = n => n === "narrateur" ? "N" : ((String(n || "").trim()[0]) || "?").toUpperCase();
const dlvNomAff = n => n === "narrateur" ? "Narrateur" : n;
function dlvQuiIA(){                              // ce que l'IA a DEJA attribue (pages preparees) : affiche en pale, jamais enregistre
  const reps = (((DLG.e || {}).doc || {}).repliques || []).filter(x => x.box);
  DLV.pages.forEach(p => { const rs = reps.filter(x => x.page === p.page);
    p.items.forEach(it => { const x = rs.find(y => y.id === it.id && dlvIou(y.box, it.box) >= 0.2) || rs.find(y => dlvIou(y.box, it.box) >= 0.5);
      it.quiIA = x && x.qui && x.qui !== "inconnu" ? x.qui : ""; }); });
}
function dlvQuiRendre(){
  const el = $("dlvQui"), a = $("dlvAide"), dist = DLG.e && DLG.e.distribution;
  el.hidden = !dist;
  if (dist){
    const ps = dlgPersos();
    if (DLV.pin && !ps.some(p => p.nom === DLV.pin)) DLV.pin = "";
    // compact : d'abord ceux qui parlent DEJA dans ce chapitre (les plus frequents), 5 au plus ; « 👥 +N » deplie les autres
    const cpt = {};
    ((((DLG.e || {}).doc || {}).repliques) || []).forEach(x => { if (x.qui && x.qui !== "inconnu") cpt[x.qui] = (cpt[x.qui] || 0) + 1; });
    DLV.pages.forEach(p => p.items.forEach(it => { if (it.qui) cpt[it.qui] = (cpt[it.qui] || 0) + 100; }));
    let vis = ps.filter(p => cpt[p.nom]).sort((u, w) => cpt[w.nom] - cpt[u.nom]);
    if (!vis.length) vis = ps.filter(p => !p.narrateur);
    vis = vis.slice(0, 5);
    const pinP = ps.find(p => p.nom === DLV.pin); if (pinP && !vis.includes(pinP)) vis.unshift(pinP);
    const montres = DLV.tous ? ps : vis, autres = ps.length - vis.length;
    el.innerHTML = '<span class="dlv-qlab">🎭 Qui parle ?</span>' + montres.map(p => '<button class="dlv-p' + (DLV.pin === p.nom ? " on" : "") + '" style="--c:' + esc(p.couleur || "#8b93a7")
      + '" data-dlvp="' + esc(p.nom) + '" title="' + esc(dlvNomAff(p.nom)) + ' : puis touche ses bulles"><i>' + esc(dlvInit(p.nom)) + "</i><b>" + esc(dlvNomAff(p.nom)) + "</b></button>").join("")
      + (DLV.tous ? '<button class="dlv-p plus" data-dlvp="tous" title="seulement ceux du chapitre">‹ moins</button>'
                  : autres > 0 ? '<button class="dlv-p plus" data-dlvp="tous" title="les autres personnages de la série">👥 +' + autres + "</button>" : "")
      + '<button class="dlv-p plus" data-dlvp="+" title="nouveau personnage">＋</button>'
      + (DLV.pin ? '<button class="dlv-p" style="--c:#555" data-dlvp="x" title="ranger le pinceau">✕</button>' : "");
  }
  const sp = a.querySelector("span"); if (!a.dataset.txt) a.dataset.txt = sp.innerHTML;
  if (DLV.pin){ a.hidden = false; a.classList.add("pinceau"); a.style.setProperty("--c", dlgCouleur(DLV.pin));
    sp.innerHTML = "🖌 <b>" + esc(dlvNomAff(DLV.pin)) + "</b> — touche ses bulles · retouche « " + esc(dlvNomAff(DLV.pin)) + " » pour ranger le pinceau"; }
  else if (a.classList.contains("pinceau")){ a.classList.remove("pinceau"); sp.innerHTML = a.dataset.txt; a.hidden = !DLV.aide; }
}
function dlvPinceau(nom){
  const avant = $("dlvScene").clientHeight;
  DLV.pin = nom || ""; dlvQuiRendre();
  if ($("dlvScene").clientHeight !== avant){ dlvTaille(); } dlvDessiner();
  if (DLV.pin) dlvToast("🖌 " + dlvNomAff(DLV.pin) + " — touche ses bulles");
}
$("dlvQui").addEventListener("click", e => {
  const b = e.target.closest("[data-dlvp]"); if (!b) return; const v = b.dataset.dlvp;
  if (v === "+"){ $("dlvNouv").hidden = false; dlvTaille(); dlvDessiner(); $("dlvNouvNom").focus(); return; }
  if (v === "tous"){ DLV.tous = !DLV.tous; dlvQuiRendre(); dlvTaille(); dlvDessiner(); return; }
  DLV.tous = false; dlvPinceau(v === "x" || DLV.pin === v ? "" : v); dlvTaille(); dlvDessiner();
});
function dlvVoixLibre(genre){                     // voix d'office : preferee du genre, sinon francaise du genre, jamais deja prise
  const g = genre === "femme" ? "female" : "male", prises = new Set(dlgPersos().map(p => p.voix_el)), l = DLG.voix || [], ok = v => v && v.genre === g && !prises.has(v.id);
  const v = (DLG.fav || []).map(i => l.find(x => x.id === i)).find(ok) || l.find(x => x.fr && ok(x)) || l.find(ok);
  return v ? v.id : null;
}
async function dlvNouveau(genre){
  const nom = $("dlvNouvNom").value.trim().slice(0, 40);
  if (!genre){ $("dlvNouv").hidden = true; $("dlvNouvNom").value = ""; dlvTaille(); dlvDessiner(); return; }
  if (!nom){ $("dlvNouvNom").focus(); return dlvToast("écris d'abord son nom"); }
  if (/^(narrateur|inconnu)$/i.test(nom)) return dlvToast("« " + nom + " » est réservé");
  const deja = dlgPersos().find(p => p.nom.toLowerCase() === nom.toLowerCase());
  if (!deja){
    try {
      if (!DLG.voix){ try { DLG.voix = ((await api("/manga/el_voix")).voix || []); } catch (err) { DLG.voix = []; } }
      const gk = genre === "femme" ? "f" : "h", df = DLG.defauts || {}, aj = { nom, genre };
      const vx = dlvVoixLibre(genre); if (vx) aj.voix_el = vx;
      if (df["voix_" + gk + "_vitesse"] != null) aj.vitesse = df["voix_" + gk + "_vitesse"];
      if (df["voix_" + gk + "_ecoute"] != null) aj.ecoute = df["voix_" + gk + "_ecoute"];
      const r = await api("/manga/dialogues_distribution", { serie: serieDe(DLV.d), ajouter: aj });
      if (r.error) throw new Error(r.error);
      if (DLG.e) DLG.e.distribution = r.distribution;
    } catch (err) { return dlvToast("⚠ personnage non créé : " + err.message); }
  }
  $("dlvNouvNom").value = ""; $("dlvNouv").hidden = true;
  dlvPinceau(deja ? deja.nom : nom); dlvTaille(); dlvDessiner();
}
$("dlvNouv").addEventListener("click", e => { const b = e.target.closest("[data-dlvg]"); if (b) dlvNouveau(b.dataset.dlvg); });
$("dlvNouvNom").addEventListener("keydown", e => { if (e.key === "Escape") dlvNouveau(""); });
function dlvToast(t){''')

open(TMP, "w", encoding="utf-8", newline="").write(s)
js = "\n".join(re.findall(r"<script>(.*?)</script>", s, re.S))
open(TMP + ".js", "w", encoding="utf-8").write(js)
r = subprocess.run(["node", "--check", TMP + ".js"], capture_output=True, text=True)
if r.returncode:
    print("node --check KO", r.stderr[:800]); sys.exit(1)
if "--essai" in sys.argv:
    print("essai OK (rien remplace) :", TMP); sys.exit(0)
shutil.copy2(F, F + ".bak-v3470")
shutil.copy2(TMP, F)
print("ok v3.5.0")
