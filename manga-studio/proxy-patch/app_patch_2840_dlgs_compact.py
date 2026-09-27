# -*- coding: utf-8 -*-
"""v2.84.0 (27/09, R9 -- Quang 11h41 : « le petit bouton Dialogue tout en haut d'un manga : une vue plus compacte, comme le bouton
video a gauche, avec un bouton pour declencher simplement la lecture de la video, et la possibilite de deplier le detail si on le
souhaite, comme dans les chapitres ») : le panneau « 🎭 Dialogues de la serie » en lignes COMPACTES. Une ligne = « ch. N » + etat
court + gros ▶ (la video de dialogues la plus recente dans le lecteur de l'app, enchainement v2.82.4 ; sans video : les voix) +
› qui deplie la ligne complete d'avant (rien de retire). En tete : « ▶ Tout lire » (toutes les videos de dialogues de la serie,
dans l'ordre) et « ⋯ Plusieurs chapitres » (le lancement groupe, replie par defaut). Suppose v2.83.0. Rejouable."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v2.84.0" in s[:400]:
    print("deja applique"); sys.exit(0)
if "v2.83.0" not in s[:400]:
    print("ERREUR : appliquer d'abord app_patch_2830_lueur_dlg.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


rep("<title>Manga Studio v2.83.0</title>", "<title>Manga Studio v2.84.0</title>")
rep('<span class="ver" id="verBadge">v2.83.0</span>', '<span class="ver" id="verBadge">v2.84.0</span>')
rep('const VERSION = "2.83.0";', 'const VERSION = "2.84.0";   // v2.84.0 : Dialogues de la serie en lignes compactes, ▶ Tout lire (R9)')
# --- CSS
rep(""".dlgs-lot input{width:64px}.dlgs-lot .muted{font-size:12px;flex-basis:100%}""",
    """.dlgs-lot input{width:64px}.dlgs-lot .muted{font-size:12px;flex-basis:100%}
/* v2.84.0 (R9) : lignes compactes -- ch. N · etat court · ▶ · › (le detail d'avant se deplie) */
.dlgs-lot[hidden]{display:none}
.dlgs-filtre .esp{flex:1}
.dlgs-f,#dlgsTout{white-space:nowrap}.dlgs-f .l-court{display:none}
@media (max-width:520px){ .dlgs-f .l-long{display:none}.dlgs-f .l-court{display:inline} }
.dlgs-c{border-top:1px solid var(--line)}
.dlgs-t{display:grid;grid-template-columns:auto minmax(0,1fr) 44px 14px;gap:8px;align-items:center;padding:7px 4px;cursor:pointer;min-height:40px}
.dlgs-t > b{white-space:nowrap}
.dlgs-t .e{font-size:13px;color:var(--dim);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}
.dlgs-t .btn.dlgs-jouer{width:44px;height:36px;padding:0;justify-content:center;font-size:16px}
.dlgs-c .cl-chev{color:var(--dim);font-size:18px;transition:transform .15s}.dlgs-c.ouv .cl-chev{transform:rotate(90deg)}
.dlgs-c .dlgs-l{border-top:0;padding-top:0}
.dlgs-c.off .dlgs-t > b{color:var(--dim)}""")
# --- en-tete : ▶ Tout lire + ⋯ Plusieurs chapitres ; le lancement groupe replie
rep("""<button class="dlgs-f" data-f="tous" id="dlgsFTous">Tous</button></div>""",
    """<button class="dlgs-f" data-f="tous" id="dlgsFTous">Tous</button><span class="esp"></span><button class="btn sm pri" id="dlgsTout" title="toutes les vidéos de dialogues de la série, dans l'ordre">▶ Tout lire</button><button class="btn sm" id="dlgsLotBtn" aria-expanded="false" title="préparer ou générer plusieurs chapitres d'un coup">⋯</button></div>""")
rep("""<div class="dlgs-lot">Plusieurs chapitres""", """<div class="dlgs-lot" id="dlgsLot" hidden>Plusieurs chapitres""")
# --- la ligne compacte ; l'ancienne ligne devient son detail
rep("""const DLGS = { serie: null, det: {}, chs: [], filtre: "avec", poll: null };""",
    """const DLGS = { serie: null, det: {}, chs: [], filtre: "avec", poll: null, ouv: new Set() };   // v2.84.0 : ouv = lignes depliees""")
rep("""function dlgsLigne(x){
  const d = x.c.dir, r = (RESUME && RESUME.chapitres[d]) || {}, dt = DLGS.det[d];""",
    """function dlgsLigne(x){                          // v2.84.0 (R9) : ch. N · etat court · ▶ · ›  (le detail = la ligne d'avant)
  const d = x.c.dir, dt = DLGS.det[d], doc = dt && dt.e && dt.e.doc, p = (dt && dt.p) || {}, ouv = DLGS.ouv.has(d);
  let court = "pas encore préparé", jouer = "";
  if (doc){
    const vids = Object.values(dlgVideos(doc, p)), vper = vids.filter(y => y.etat === "perimee").length;
    court = dt.e.en_cours ? "⏳ en cours" : p.a_faire ? "🟠 " + p.a_faire + " voix à faire" : "✅ prêts";
    if (vids.length) court += " · 🎬" + (vper ? " à refaire" : "");
    jouer = vids.length ? "video" : p.deja ? "lire" : "";
  }
  const titre = jouer === "video" ? "voir la vidéo des dialogues" : "lire les voix (pas encore de vidéo)";
  return '<div class="dlgs-c' + (ouv ? " ouv" : "") + (doc ? "" : " off") + '" data-dir="' + esc(d) + '">'
    + '<div class="dlgs-t" data-dlgs="plier" data-d="' + esc(d) + '"><b>ch. ' + esc(x.c.chapter) + '</b><span class="e">' + esc(court) + "</span>"
    + (jouer ? '<button class="btn dlgs-jouer" data-dlgs="' + jouer + '" data-d="' + esc(d) + '" title="' + titre + '">▶</button>' : "<span></span>")
    + '<span class="cl-chev">›</span></div>' + (ouv ? dlgsDetail(x) : "") + "</div>";
}
function dlgsDetail(x){
  const d = x.c.dir, r = (RESUME && RESUME.chapitres[d]) || {}, dt = DLGS.det[d];""")
rep("""  const k = t.dataset.dlgs;
  if (k === "ouvrir"){""", """  const k = t.dataset.dlgs;
  if (k === "plier"){ DLGS.ouv.has(d) ? DLGS.ouv.delete(d) : DLGS.ouv.add(d); dlgsRendre(); return; }   // v2.84.0
  if (k === "ouvrir"){""")
rep("""$("dlgsPrep").onclick = () => dlgsLot("preparer");""", """$("dlgsPrep").onclick = () => dlgsLot("preparer");
$("dlgsLotBtn").onclick = () => { const h = !$("dlgsLot").hidden; $("dlgsLot").hidden = h; $("dlgsLotBtn").setAttribute("aria-expanded", String(!h)); };   // v2.84.0
$("dlgsTout").onclick = async () => {                    // v2.84.0 : toutes les videos de dialogues de la serie, dans l'ordre
  let liste = []; try { liste = await dlgVidListe(DLGS.serie); } catch (err) {}
  if (!liste.length) return toast("aucune vidéo de dialogues dans cette série — le ▶ d'un chapitre lit ses voix");
  VID.dlg = { liste, i: 0 }; dlgVidIdx(0);
};""")
# ▶ Tout lire grise quand la serie n'a aucune video
rep("""  $("dlgsFAvec").textContent = "Avec dialogues (" + avec.length + ")";""",
    """  $("dlgsTout").disabled = !avec.some(x => Object.keys(dlgVideos(DLGS.det[x.c.dir].e.doc, DLGS.det[x.c.dir].p)).length);   // v2.84.0
  $("dlgsFAvec").innerHTML = '<span class="l-long">Avec dialogues</span><span class="l-court">Avec 🎭</span> (' + avec.length + ")";""")   # v2.84.0 : court au telephone (PAS de commentaire // : la ligne continue)
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
