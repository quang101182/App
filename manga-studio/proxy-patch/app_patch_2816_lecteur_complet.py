# -*- coding: utf-8 -*-
"""v2.81.6 (27/09, R1 -- Quang 02h30 : « ca ne lit que la premiere bulle quand une image en contient deux ») : le lecteur des
Dialogues ne SAUTE PLUS aucune replique. Avant : filtre « lire && voix », les repliques sans voix disparaissaient en silence
(ch. de Quang : 5 jouees sur 36). Apres : toutes les repliques lues ; voix a jour (etat du plan, la meme definition que la
video) = audio ; sinon halo + sous-titre + « voix à faire », duree de lecture tiree du texte ; a l'ouverture, un bandeau
« N répliques sans voix · 🔊 Générer (≈ crédits) ». Rejouable."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v2.81.6" in s[:400]:
    print("deja applique"); sys.exit(0)
N = "\r\n" if "\r\n" in s else "\n"
BS = "\\"      # une barre oblique inverse litterale pour les \n des chaines JS


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


rep("""  + '<div class="dlgl-sous" id="dllSous"></div>'""",
    """  + '<div class="dlgl-manq" id="dllManq" hidden></div>'
  + '<div class="dlgl-sous" id="dllSous"></div>'""")
rep(""".dlgl-sous b{white-space:nowrap}""", """.dlgl-sous b{white-space:nowrap}
.dlgl-manq{display:flex;align-items:center;gap:8px;flex-wrap:wrap;padding:6px 14px;font-size:13px;background:#2a2112;color:#f0c46b;border-top:1px solid #5a4520}
.dlgl-manq[hidden]{display:none}""")
rep("""  let e;
  try { e = await api("/manga/dialogues?d=" + encodeURIComponent(d)); } catch (err) { return toast("lecteur : " + err.message); }
  const liste = ((e.doc || {}).repliques || []).filter(x => x.lire && x.voix && x.voix.fichier);
  if (!liste.length) return toast("aucune voix faite pour ce chapitre : lance « Générer les voix »");
  Object.assign(DLL, { d, doc: e.doc, dist: e.distribution || {}, liste, i: Math.max(0, Math.min(liste.length - 1, depuis || 0)), page: null, pause: false, cases: null });""",
"""  let e, plan = null;
  try { [e, plan] = await Promise.all([api("/manga/dialogues?d=" + encodeURIComponent(d)),
                                       api("/manga/dialogues_plan?d=" + encodeURIComponent(d)).catch(() => null)]); }
  catch (err) { return toast("lecteur : " + err.message); }
  // v2.81.6 (R1) : TOUTES les repliques lues -- une replique sans voix n'est plus sautee en silence
  const liste = ((e.doc || {}).repliques || []).filter(x => x.lire && !(x.a_traiter && !((x.corrige || {}).qui)));
  if (!liste.length) return toast("aucune réplique à lire : prépare d'abord ce chapitre");
  const etats = (plan && plan.repliques) || {};
  Object.assign(DLL, { d, doc: e.doc, dist: e.distribution || {}, liste, i: Math.max(0, Math.min(liste.length - 1, depuis || 0)), page: null, pause: false, cases: null,
                       etats, avecPlan: !!(plan && plan.repliques) });
  const manq = liste.filter(x => dllEtat(x) !== "faite").length;
  $("dllManq").hidden = !manq;
  if (manq) $("dllManq").innerHTML = "⚠ " + manq + " réplique" + (manq > 1 ? "s" : "") + " sur " + liste.length + " sans voix à jour : "
    + (manq > 1 ? "elles s'affichent" : "elle s'affiche") + " en sous-titre, sans son."
    + ' <button class="btn sm" id="dllGen">🔊 Générer' + (plan && plan.credits ? " (≈ " + fmtCr(plan.credits) + " crédits)" : "") + "</button>";""")
rep("""function dllCouleur(qui){""", """function dllEtat(x){                            // v2.81.6 : l'etat du plan (meme definition que la video) ; sans plan : fichier present
  const et = DLL.etats && DLL.etats[x.cle];
  return et || (!DLL.avecPlan && x.voix && x.voix.fichier ? "faite" : "a_faire");
}
function dllSilence(x){                          // replique sans voix : on la laisse LIRE (duree tiree du texte), puis on enchaine
  clearTimeout(DLL.t2);
  if (DLL.pause) return;
  const ms = Math.max(1800, (x.texte || "").length * 65) / (+$("dllVit").value || 1);
  DLL.t2 = setTimeout(dllApres, ms);
}
function dllApres(){
  const g = $("dllG"); if (g) g.classList.add("off");
  DLL.t = setTimeout(() => {
    if (DLL.i < DLL.liste.length - 1){ DLL.i++; return dllMontrer(); }
    dllSuite();
  }, 420);
}
function dllCouleur(qui){""")
rep("""function dllMontrer(){
  clearTimeout(DLL.t);""", """function dllMontrer(){
  clearTimeout(DLL.t); clearTimeout(DLL.t2);""")
rep("""    + esc(x.qui === "narrateur" ? "Narrateur" : x.qui) + "</b><span>" + esc(x.texte || "") + "</span>";""",
    """    + esc(x.qui === "narrateur" ? "Narrateur" : x.qui) + "</b><span>" + esc(x.texte || "") + "</span>"
    + (dllEtat(x) === "faite" ? "" : ' <span class="dlg-pill ko" title="pas de voix à jour pour cette réplique : lance « 🔊 Générer »">'
       + (dllEtat(x) === "a_refaire" ? "voix à refaire" : "voix à faire") + "</span>");""")
rep("""    DLL.audio.src = srcURL(DLL.d + "/dialogues/voix/" + x.voix.fichier);
    DLL.audio.playbackRate = +$("dllVit").value;
    if (!DLL.pause) DLL.audio.play().catch(() => {});""",
    """    if (dllEtat(x) !== "faite"){ DLL.audio.pause(); DLL.audio.removeAttribute("src"); DLL.sil = true; return dllSilence(x); }
    DLL.sil = false;
    DLL.audio.src = srcURL(DLL.d + "/dialogues/voix/" + x.voix.fichier);
    DLL.audio.playbackRate = +$("dllVit").value;
    if (!DLL.pause) DLL.audio.play().catch(() => {});""")
rep("""DLL.audio.onended = () => {
  const g = $("dllG"); if (g) g.classList.add("off");
  DLL.t = setTimeout(() => {
    if (DLL.i < DLL.liste.length - 1){ DLL.i++; return dllMontrer(); }
    dllSuite();
  }, 420);
};""", """DLL.audio.onended = dllApres;""")
rep("""    if (((e.doc || {}).repliques || []).some(x => x.lire && x.voix)) { toast("Chapitre " + CHAPS[k].chapter); return dlgLecteur(CHAPS[k].dir, 0); }""",
    """    if (((e.doc || {}).repliques || []).some(x => x.lire)) { toast("Chapitre " + CHAPS[k].chapter); return dlgLecteur(CHAPS[k].dir, 0); }""")
rep("""  if (DLL.pause) DLL.audio.pause(); else DLL.audio.play().catch(() => {});
};""", """  if (DLL.sil){ if (DLL.pause) clearTimeout(DLL.t2); else dllSilence(DLL.liste[DLL.i]); return; }   // v2.81.6
  if (DLL.pause) DLL.audio.pause(); else DLL.audio.play().catch(() => {});
};
document.addEventListener("click", async ev => {                 // v2.81.6 : bandeau « sans voix » -> generer, sur accord
  if (!ev.target.closest("#dllGen")) return;
  if (!confirm("Générer les voix manquantes de ce chapitre ?""" + BS + "n" + BS + """nLe lecteur continue ; rouvre-le quand c'est fini pour les entendre.")) return;
  try { const r = await api("/manga/dialogues_lancer", { d: DLL.d, action: "voix" }); if (r.error) throw new Error(r.error); toast("🔊 voix lancées"); }
  catch (err) { toast("voix : " + err.message); }
});""")
rep("""$("dllFermer").onclick = () => { DLL.audio.pause(); clearTimeout(DLL.t);""",
    """$("dllFermer").onclick = () => { DLL.audio.pause(); clearTimeout(DLL.t); clearTimeout(DLL.t2);""")
s = s.replace("<title>Manga Studio v2.81.5</title>", "<title>Manga Studio v2.81.6</title>", 1)
s = s.replace('id="verBadge">v2.81.5<', 'id="verBadge">v2.81.6<', 1)
s = s.replace('const VERSION = "2.81.5";', 'const VERSION = "2.81.6";   // v2.81.6 : le lecteur des Dialogues ne saute plus aucune replique (R1)', 1)
assert s.count("2.81.6") >= 4
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
