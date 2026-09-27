# -*- coding: utf-8 -*-
"""v2.82.1 (27/09, R3-bis -- Quang 03h08 : « plusieurs videos sur un meme chapitre, pages 5 a 10 et 35 a 42 ? ») : 🎬 fabrique la
video de la PORTEE des champs (« Des pages : de 5 a 10 » -> dialogues_p5-10.mp4), chaque portee garde la sienne ; « Ce chapitre »
= la video du chapitre entier (comme avant). La ligne 🎭 liste TOUTES les videos (▶ ⬇, a jour / a refaire) ; ▶ Voir / ⬇ suivent
la portee des champs ; le panneau de la serie compte les videos. Une video refusee (voix manquantes) le dit AVANT de lancer.
Serveur : patch_dialogues_7 ; dialogues.py >= 1.10.0. Suppose app_patch_2820. Rejouable."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v2.82.1" in s[:400]:
    print("deja applique"); sys.exit(0)
if "v2.82.0" not in s[:400]:
    print("ERREUR : appliquer d'abord app_patch_2820_dialogues_serie.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


rep("""        <a class="btn sm" id="dlgVidDl" hidden>⬇ Télécharger</a>
      </div>""", """        <a class="btn sm" id="dlgVidDl" hidden>⬇ Télécharger</a>
      </div>
      <div class="dlg-vids" id="dlgVids" hidden></div>""")
rep(""".dlgs-nb[hidden]{display:none}""", """.dlgs-nb[hidden]{display:none}
.dlg-vids{display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin-top:8px;font-size:13px;color:var(--dim)}
.dlg-vids[hidden]{display:none}
.dlg-vids .dlg-v{display:inline-flex;align-items:center;gap:4px;border:1px solid var(--line);border-radius:99px;padding:2px 4px 2px 10px}
.dlg-vids .dlg-v.per{border-color:#8a6a2e}.dlg-vids .btn{padding:2px 8px}""")
rep("""  const v = (e.doc || {}).video, etv = p && p.video;
  $("dlgVid").disabled = occupe || !(p && p.deja);
  $("dlgVid").textContent = etv === "a_jour" ? "🎬 Refaire la vidéo" : etv === "perimee" ? "🎬 Mettre la vidéo à jour" : "🎬 Vidéo";
  $("dlgVid").classList.toggle("pri", etv === "perimee");
  $("dlgVidVoir").hidden = $("dlgVidDl").hidden = !v || etv === "absente";
  if (v) $("dlgVidDl").href = CFG.base + "/manga/video_file?p=" + encodeURIComponent(v.fichier) + "&dl=1&v=" + encodeURIComponent(v.t || "") + (CFG.key ? "&_k=" + encodeURIComponent(CFG.key) : "");""",
    """  // v2.82.1 (R3-bis) : UNE video par portee ; les boutons suivent la portee des champs
  const vids = dlgVideos(e.doc, p), k = DLG.portee === "pages" ? dlgPorteeTxt() : "tout", v = vids[k] ? vids[k].v : null, etv = vids[k] ? vids[k].etat : "absente";
  DLG.vcur = v;
  $("dlgVid").disabled = occupe || !(p && p.deja);
  $("dlgVid").textContent = (etv === "a_jour" ? "🎬 Refaire la vidéo" : etv === "perimee" ? "🎬 Mettre la vidéo à jour" : "🎬 Vidéo") + (k !== "tout" ? " p. " + k : "");
  $("dlgVid").classList.toggle("pri", etv === "perimee");
  $("dlgVidVoir").hidden = $("dlgVidDl").hidden = !v;
  if (v) $("dlgVidDl").href = dlgVidUrl(v, true);
  const ks = Object.keys(vids).sort((a, b) => (a === "tout" ? -1 : b === "tout" ? 1 : parseInt(a) - parseInt(b)));
  $("dlgVids").hidden = !ks.length;
  $("dlgVids").innerHTML = ks.length ? "🎬 Vidéos : " + ks.map(x => '<span class="dlg-v' + (vids[x].etat === "perimee" ? " per" : "") + '">'
      + (x === "tout" ? "chapitre entier" : "p. " + esc(x)) + " · " + (vids[x].etat === "perimee" ? "à refaire" : "à jour") + (vids[x].v.duree ? " · " + Math.round(vids[x].v.duree) + " s" : "")
      + ' <button class="btn sm" data-dlgv="voir" data-k="' + esc(x) + '" title="voir">▶</button><button class="btn sm" data-dlgv="dl" data-k="' + esc(x) + '" title="télécharger">⬇</button></span>').join("") : "";""")
rep("""function dlgRendre(){""", """function dlgPorteeTxt(){                       // v2.82.1 : « 5-10 » d'apres les champs (bornes au chapitre)
  const tot = CHAP_PAGES || 9999, de = Math.max(1, parseInt($("dlgDe").value) || 1), a = Math.min(tot, parseInt($("dlgA").value) || de);
  return de + "-" + Math.max(de, a);
}
function dlgVideos(doc, p){                      // v2.82.1 : {portee: {v, etat}} -- doc.videos + l'ancienne video du chapitre entier
  const out = {}, et = (p && p.videos) || {};
  Object.entries((doc || {}).videos || {}).forEach(([k, v]) => { if (et[k]) out[k] = { v, etat: et[k] }; });
  if (doc && doc.video && !out.tout && p && p.video && p.video !== "absente") out.tout = { v: doc.video, etat: p.video };
  return out;
}
const dlgVidUrl = (v, dl) => CFG.base + "/manga/video_file?p=" + encodeURIComponent(v.fichier) + (dl ? "&dl=1" : "") + "&v=" + encodeURIComponent(v.t || "") + (CFG.key ? "&_k=" + encodeURIComponent(CFG.key) : "");
function dlgVidMontrer(v, d){
  const c = CHAPS.find(y => y.dir === (d || CHAP_OPEN));
  $("dlgVidTitre").textContent = "🎭 Dialogues" + (c ? " · ch. " + c.chapter : "") + (v.portee && v.portee !== "tout" ? " · p. " + v.portee : "");
  $("dlgVidEl").src = dlgVidUrl(v, false);
  dlgVidBox.hidden = false; $("dlgVidEl").play().catch(() => {});
}
document.addEventListener("click", ev => {        // la liste des videos de la ligne 🎭
  const t = ev.target.closest("#dlgVids [data-dlgv]"); if (!t) return;
  const x = dlgVideos((DLG.e || {}).doc, DLG.plan)[t.dataset.k]; if (!x) return;
  if (t.dataset.dlgv === "voir") dlgVidMontrer(x.v);
  else { const a = document.createElement("a"); a.href = dlgVidUrl(x.v, true); document.body.appendChild(a); a.click(); a.remove(); }
});
function dlgRendre(){""")
rep("""$("dlgVid").onclick = async () => {
  const p = DLG.plan;
  if (p && p.a_faire && !confirm(p.a_faire + " réplique(s) n'ont pas encore leur voix : la vidéo ne contiendra que les voix déjà faites. Continuer ?")) return;
  try { const r = await api("/manga/dialogues_lancer", { d: CHAP_OPEN, action: "video" }); if (r.error) throw new Error(r.error); toast("🎬 vidéo des dialogues lancée"); }""",
    """$("dlgVid").onclick = async () => {
  const p = DLG.plan || {}, portee = DLG.portee === "pages" ? dlgPorteeTxt() : "";
  const [pa, pb] = portee ? portee.split("-").map(Number) : [0, 1e9];
  const manq = Object.entries(p.repliques || {}).filter(([c, v]) => ["a_faire", "a_refaire", "sans_voix", "a_traiter"].includes(v)
    && +c.split("-")[0] >= pa && +c.split("-")[0] <= pb).length;                     // v2.82.1 : la video ne saute rien -> on le dit AVANT
  if (manq) return toast(manq + " réplique" + (manq > 1 ? "s" : "") + (portee ? " de ces pages" : "") + " sans voix à jour : génère d'abord les voix (la vidéo ne saute aucune réplique)");
  try { const r = await api("/manga/dialogues_lancer", Object.assign({ d: CHAP_OPEN, action: "video" }, portee ? { pages: portee } : {}));
        if (r.error) throw new Error(r.error); toast("🎬 vidéo des dialogues lancée" + (portee ? " (p. " + portee + ")" : "")); }""")
rep("""$("dlgVidVoir").onclick = () => {
  const v = ((DLG.e || {}).doc || {}).video; if (!v) return;
  const c = CHAPS.find(y => y.dir === CHAP_OPEN);
  $("dlgVidTitre").textContent = "🎭 Dialogues" + (c ? " · ch. " + c.chapter : "");
  $("dlgVidEl").src = CFG.base + "/manga/video_file?p=" + encodeURIComponent(v.fichier) + "&v=" + encodeURIComponent(v.t || "") + (CFG.key ? "&_k=" + encodeURIComponent(CFG.key) : "");
  dlgVidBox.hidden = false; $("dlgVidEl").play().catch(() => {});
};""", """$("dlgVidVoir").onclick = () => { if (DLG.vcur) dlgVidMontrer(DLG.vcur); };      // v2.82.1 : la video de la portee des champs""")
# --- panneau de la serie : toutes les videos comptees, ▶ = la plus recente
rep("""    if (p.video === "a_jour") extra.push("🎬 vidéo à jour" + (doc.video && doc.video.duree ? " (" + Math.round(doc.video.duree) + " s)" : ""));
    else if (p.video === "perimee") extra.push("🎬 vidéo à refaire");""",
    """    const vids = Object.values(dlgVideos(doc, p)), vper = vids.filter(y => y.etat === "perimee").length;    // v2.82.1 : une par portee
    const vder = vids.map(y => y.v).sort((a, c) => String(c.t || "").localeCompare(String(a.t || "")))[0];
    if (vids.length) extra.push("🎬 " + (vids.length > 1 ? vids.length + " vidéos" : "vidéo") + (vper ? " (" + vper + " à refaire)" : " à jour")
      + (vids.length === 1 && vder.duree ? " (" + Math.round(vder.duree) + " s)" : ""));""")
rep("""    const act = (p.deja ? b("lire", "▶ Lire", !p.a_faire) : "") + (doc.video && p.video && p.video !== "absente" ? b("video", "▶ Vidéo") + b("dl", "⬇") : "")""",
    """    const act = (p.deja ? b("lire", "▶ Lire", !p.a_faire) : "") + (vids.length ? b("video", "▶ Vidéo") + b("dl", "⬇") : "")""")
rep("""  const d = t.dataset.d, dt = DLGS.det[d] || {}, doc = (dt.e || {}).doc || {};""",
    """  const d = t.dataset.d, dt = DLGS.det[d] || {}, doc = (dt.e || {}).doc || {};
  const vder = Object.values(dlgVideos(doc, dt.p)).map(y => y.v).sort((a, c) => String(c.t || "").localeCompare(String(a.t || "")))[0];   // v2.82.1""")
rep("""  else if (k === "video" && doc.video){
    const c = CHAPS.find(y => y.dir === d);
    $("dlgVidTitre").textContent = "🎭 Dialogues" + (c ? " · ch. " + c.chapter : "");
    $("dlgVidEl").src = CFG.base + "/manga/video_file?p=" + encodeURIComponent(doc.video.fichier) + "&v=" + encodeURIComponent(doc.video.t || "") + (CFG.key ? "&_k=" + encodeURIComponent(CFG.key) : "");
    dlgVidBox.hidden = false; $("dlgVidEl").play().catch(() => {});
  }
  else if (k === "dl" && doc.video){
    const a = document.createElement("a");
    a.href = CFG.base + "/manga/video_file?p=" + encodeURIComponent(doc.video.fichier) + "&dl=1&v=" + encodeURIComponent(doc.video.t || "") + (CFG.key ? "&_k=" + encodeURIComponent(CFG.key) : "");
    document.body.appendChild(a); a.click(); a.remove();
  }""", """  else if (k === "video" && vder) dlgVidMontrer(vder, d);
  else if (k === "dl" && vder){ const a = document.createElement("a"); a.href = dlgVidUrl(vder, true); document.body.appendChild(a); a.click(); a.remove(); }""")
s = s.replace("<title>Manga Studio v2.82.0</title>", "<title>Manga Studio v2.82.1</title>", 1)
s = s.replace('id="verBadge">v2.82.0<', 'id="verBadge">v2.82.1<', 1)
s = s.replace('const VERSION = "2.82.0";', 'const VERSION = "2.82.1";   // v2.82.1 : une video de dialogues par portee (R3-bis)', 1)
assert s.count("2.82.1") >= 4
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
