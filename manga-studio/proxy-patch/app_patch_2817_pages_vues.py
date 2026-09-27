# -*- coding: utf-8 -*-
"""v2.81.7 (27/09, R1-bis -- Quang 02h35 : « des pages ont ete sautees, la page 44 n'apparait pas […] meme les pages sans
dialogue doivent etre affichees, avec un petit tampon ») + R1-ter (02h38 : « aucune vision de ce que j'avais parametre, de
quelle page a quelle page ») : le lecteur des Dialogues avance PAGE PAR PAGE sur toute la portee
preparee (doc.pages_vues de dialogues.py >= 1.9.1 ; fichier plus ancien : de la 1re a la derniere page ayant une replique).
Page sans replique = page entiere + tampon « SANS DIALOGUE », ~2 s, puis la suivante. Suppose app_patch_2816. Rejouable."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v2.81.7" in s[:400]:
    print("deja applique"); sys.exit(0)
if "v2.81.6" not in s[:400]:
    print("ERREUR : appliquer d'abord app_patch_2816_lecteur_complet.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


rep("""  + '<svg id="dllSvg" preserveAspectRatio="none"></svg></div></div></div>'""",
    """  + '<svg id="dllSvg" preserveAspectRatio="none"></svg></div><div class="dlgl-tampon" id="dllTampon" hidden>SANS DIALOGUE</div></div></div>'""")
rep(""".dlgl-manq[hidden]{display:none}""", """.dlgl-manq[hidden]{display:none}
.dlgl-tampon{position:absolute;top:10px;right:10px;padding:5px 12px;border:2px solid #e5534b;color:#ff9d96;border-radius:6px;
  font:800 13px/1 system-ui,sans-serif;letter-spacing:.08em;transform:rotate(-6deg);background:rgba(7,8,11,.72);pointer-events:none}
.dlgl-tampon[hidden]{display:none}""")
rep("""  const liste = ((e.doc || {}).repliques || []).filter(x => x.lire && !(x.a_traiter && !((x.corrige || {}).qui)));
  if (!liste.length) return toast("aucune réplique à lire : prépare d'abord ce chapitre");""",
    """  const reps = ((e.doc || {}).repliques || []).filter(x => x.lire && !(x.a_traiter && !((x.corrige || {}).qui)));
  if (!reps.length) return toast("aucune réplique à lire : prépare d'abord ce chapitre");
  // v2.81.7 (R1-bis) : PAGE PAR PAGE sur toute la portee preparee ; une page sans replique a son etape (tampon)
  const ps = reps.map(x => x.page), p0 = Math.min(...ps), p1 = Math.max(...ps);
  const nums = (e.doc.pages_vues && e.doc.pages_vues.length) ? e.doc.pages_vues : Array.from({ length: p1 - p0 + 1 }, (_, k) => p0 + k);
  const trp = new Set(e.trad_pages || []), fich = e.fichiers || [];
  const imgDe = n => trp.has(n) ? "traduction/fr/page_" + String(n).padStart(3, "0") + ".png" : (fich[n - 1] || null);
  const liste = [];
  nums.forEach(n => { if (!ps.includes(n) && imgDe(n)) liste.push({ page: n, vide: true, cle: "p" + n, id: 0, img_rel: imgDe(n), texte: "", qui: "" }); });
  reps.forEach(x => liste.push(x));
  liste.sort((a, b) => a.page - b.page || (a.id || 0) - (b.id || 0));""")
rep('+ " sur " + liste.length + " sans voix à jour : "', '+ " sur " + reps.length + " sans voix à jour : "')   # le compte = REPLIQUES, pas etapes
rep("""  const manq = liste.filter(x => dllEtat(x) !== "faite").length;""",
    """  const manq = liste.filter(x => !x.vide && dllEtat(x) !== "faite").length;""")
rep("""    + (manq > 1 ? "elles s'affichent" : "elle s'affiche") + " en sous-titre, sans son.\"""",
    """    + (manq > 1 ? "elles s'affichent" : "elle s'affiche") + " en sous-titre, sans son.\"""")
rep("""  const et = DLL.etats && DLL.etats[x.cle];""", """  if (x.vide) return "vide";
  const et = DLL.etats && DLL.etats[x.cle];""")
rep("""  const ms = Math.max(1800, (x.texte || "").length * 65) / (+$("dllVit").value || 1);""",
    """  const ms = (x.vide ? 2200 : Math.max(1800, (x.texte || "").length * 65)) / (+$("dllVit").value || 1);""")
rep("""  const r = DLL_CAM ? dllCaseDe(x) : null, cw = $("dllCadre").clientWidth, ch = $("dllCadre").clientHeight;""",
    """  const r = DLL_CAM && !x.vide ? dllCaseDe(x) : null, cw = $("dllCadre").clientWidth, ch = $("dllCadre").clientHeight;""")
rep("""  const coul = dllCouleur(x.qui);
  $("dllSous").innerHTML =""", """  const coul = dllCouleur(x.qui);
  $("dllTampon").hidden = !x.vide;
  if (x.vide) $("dllSous").innerHTML = '<span class="dlg-pill">📄 page ' + x.page + " · sans dialogue</span>"; else
  $("dllSous").innerHTML =""")
rep("""    dllHalo(x);
    dllCamera(x, true);""",
    """    if (x.vide){ $("dllSvg").innerHTML = ""; dllCamera(x, true); DLL.audio.pause(); DLL.audio.removeAttribute("src"); DLL.sil = true; return dllSilence(x); }
    dllHalo(x);
    dllCamera(x, true);""")
# --- R1-ter (Quang 02h38 : « aucune vision de ce que j'ai genere et de ce que j'avais parametre, de quelle page a quelle page »)
rep("""  if (trait) etat += " · ⚠ " + trait + " à traiter";""",
    """  if (trait) etat += " · ⚠ " + trait + " à traiter";
  const pv = dlgPagesPreparees();                                        // v2.81.7 : ce qui a ete prepare, toujours dit
  if (pv.length) etat = "p. " + dlgPlagesTxt(pv) + " (" + pv.length + " page" + (pv.length > 1 ? "s" : "") + ") · " + etat;""")
rep("""async function dlgCharger(){
  const d = CHAP_OPEN; if (!d) return;
  DLG.d = d; clearTimeout(DLG.poll);""", """function dlgPagesPreparees(){                  // v2.81.7 : portee preparee (pages_vues ; ancien fichier : pages des repliques)
  const doc = (DLG.e || {}).doc; if (!doc) return [];
  return (doc.pages_vues && doc.pages_vues.length) ? doc.pages_vues : [...new Set((doc.repliques || []).map(x => x.page))].sort((a, b) => a - b);
}
function dlgPorteeDe(e){                         // v2.81.7 : a l'ouverture d'un chapitre, la portee preparee revient dans les champs
  const pv = dlgPagesPreparees(), tot = CHAP_PAGES || 0, doc = (e || {}).doc || {};
  const pages = pv.length && tot && pv.length < tot;
  // la DERNIERE portee demandee (plusieurs portees dans un chapitre : 2-5 puis 30-35 -> 30-35, jamais « 2 a 35 »)
  const der = String(((doc.portees || []).slice(-1)[0]) || "").match(/^(\d+)(?:-(\d+))?$/);
  const bl = []; pv.forEach(n => { const l = bl[bl.length - 1]; if (l && n === l[1] + 1) l[1] = n; else bl.push([n, n]); });
  const lb = bl[bl.length - 1] || [pv[0], pv[pv.length - 1]];           // ancien fichier : le dernier bloc continu
  DLG.portee = pages ? "pages" : "chap";
  $("dlgDe").value = pages ? (der ? der[1] : lb[0]) : ""; $("dlgA").value = pages ? (der ? der[2] || der[1] : lb[1]) : "";
  document.querySelectorAll("#dlgBox .dlg-p").forEach(y => y.classList.toggle("on", y.dataset.portee === DLG.portee));
}
async function dlgCharger(){
  const d = CHAP_OPEN; if (!d) return;
  const nouveau = DLG.d !== d;
  DLG.d = d; clearTimeout(DLG.poll);""")
rep("""    DLG.e = e; DLG.lot = lot;
    DLG.plan""", """    DLG.e = e; DLG.lot = lot;
    if (nouveau) dlgPorteeDe(e);                  // v2.81.7 : jamais les champs du chapitre precedent
    DLG.plan""")
s = s.replace("<title>Manga Studio v2.81.6</title>", "<title>Manga Studio v2.81.7</title>", 1)
s = s.replace('id="verBadge">v2.81.6<', 'id="verBadge">v2.81.7<', 1)
s = s.replace('const VERSION = "2.81.6";', 'const VERSION = "2.81.7";   // v2.81.7 : lecteur des Dialogues page par page, pages sans dialogue tamponnees (R1-bis)', 1)
assert s.count("2.81.7") >= 4
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
