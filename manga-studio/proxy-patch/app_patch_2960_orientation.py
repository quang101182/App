# -*- coding: utf-8 -*-
"""v2.96.0 (27/09, R25 -- Quang 14h19 : « on se perd vite, surtout sur smartphone […] l'interface se ressemble partout » ;
14h32 : « C » sur maquette_orientation_v1.html) : savoir OU l'on est, dans l'onglet 📚 :
- FIL D'ARIANE `#ouFil` dans la barre du haut (collant, une ligne, ellipse) : 📚 › serie › ch. N › bloc ouvert / panneau ;
  chaque etape se touche pour y remonter ; la derniere en gras ;
- BANDEAU `#ouBande` juste au-dessus de l'ecran concerne (deplace a chaque changement) (NON collant : la hauteur utile du telephone n'est pas amputee) : « ← <destination> »
  + icone + TITRE + couleur de l'ecran (serie violet, chapitre rouge, 🎭 vert d'eau, 🎬 ambre, ⚙ / 🌐 bleu).
Les retours et le fil DELEGUENT aux boutons existants (#btnChapClose, #vidFermer, #dlgsFermer, #suiviFermer, #btnLibBack,
clOuvrir) : aucun comportement nouveau. Rien a la racine ni dans les autres onglets. Suppose v2.95.0. Rejouable."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v2.96.0" in s[:700]:
    print("deja applique"); sys.exit(0)
if "v2.95.0" not in s[:700]:
    print("ERREUR : appliquer d'abord app_patch_2950_reste_filet.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


rep("<title>Manga Studio v2.95.0</title>", "<title>Manga Studio v2.96.0</title>")
rep('<span class="ver" id="verBadge">v2.95.0</span>', '<span class="ver" id="verBadge">v2.96.0</span>')
rep('const VERSION = "2.95.0";', 'const VERSION = "2.96.0";   // v2.96.0 : savoir ou l on est -- fil d Ariane + bandeau d ecran colore (R25, maquette C)')
rep("""</nav>
</div>
""", """</nav>
<div class="ou-fil" id="ouFil" hidden></div>   <!-- v2.96.0 (R25) : fil d'Ariane, collant avec la barre du haut -->
</div>
""")
rep("""<section id="tChap">
""", """<section id="tChap">
  <div class="ou-bande" id="ouBande" hidden></div>   <!-- v2.96.0 (R25) : bandeau de l'ecran, defile avec le contenu -->
""")
rep(""".topbar{position:sticky;top:0;z-index:50;background:#0d0f13ee;backdrop-filter:blur(8px)}""",
    """.topbar{position:sticky;top:0;z-index:50;background:#0d0f13ee;backdrop-filter:blur(8px)}
/* v2.96.0 (R25, maquette_orientation_v1 C) : fil d'Ariane + bandeau d'ecran */
.ou-fil{display:flex;align-items:center;gap:2px;padding:3px 10px;border-top:1px solid var(--line);font-size:12.5px;white-space:nowrap;overflow:hidden}
.ou-fil[hidden],.ou-bande[hidden]{display:none}
.ou-fil button{font:inherit;background:none;border:0;color:var(--dim);padding:3px 6px;border-radius:7px;cursor:pointer;min-width:0;overflow:hidden;text-overflow:ellipsis;flex:0 1 auto}
.ou-fil button:hover{background:var(--panel2);color:var(--txt)}
.ou-fil i{color:#3b4254;font-style:normal;flex:none}
.ou-fil .ici{color:var(--txt);font-weight:700;background:var(--panel2);flex:none;max-width:60%}
.ou-bande{display:flex;align-items:center;gap:10px;padding:8px 10px;margin:0 0 10px;border:1px solid var(--line);border-left:5px solid var(--ouc,#8b93a7);border-radius:12px;
  background:linear-gradient(90deg,color-mix(in srgb,var(--ouc,#8b93a7) 22%,transparent),color-mix(in srgb,var(--ouc,#8b93a7) 3%,transparent))}
.ou-bande .ou-ic{font-size:20px;flex:none}.ou-bande .ou-t{font-weight:800;font-size:15px;letter-spacing:.3px;text-transform:uppercase;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ou-bande .btn.retour{flex:none;max-width:48%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}""")
rep("""let CL_OUVERT = ""; try { CL_OUVERT = localStorage.getItem("manga_chap_bloc") || ""; } catch {}""",
    """let CL_OUVERT = ""; try { CL_OUVERT = localStorage.getItem("manga_chap_bloc") || ""; } catch {}
/* ---- v2.96.0 (R25) : OU suis-je ? -- fil d'Ariane (barre du haut) + bandeau d'ecran (couleur, titre, retour qui nomme sa destination) ---- */
const OU_COUL = { serie: "#b58cff", chap: "#e84a5f", narr: "#e84a5f", dlg: "#3fc7a8", trad: "#4a9ee8", mus: "#b58cff", vid: "#e8a84a", prof: "#4a9ee8" };
const ouVis = id => { const e = document.getElementById(id); return !!(e && !e.hidden && e.offsetParent !== null); };
function ouEtat(){
  const sel = document.querySelector("nav button.sel");
  if (!sel || sel.dataset.tab !== "tChap") return null;
  const titre = ((document.getElementById("libSerie") || {}).textContent || "").trim();
  if (ouVis("chapDetail")){
    const c = CHAPS.find(y => y.dir === CHAP_OPEN) || {}, st = c.title || titre, b = CL.find(x => x.k === CL_OUVERT);
    const fil = [{ t: "📚", go: "racine" }, { t: st, go: "serie" }, { t: "ch. " + (c.chapter || "?"), go: b ? "chapitre" : "" }];
    if (b) fil.push({ t: b.ic + " " + b.t });
    return { fil, ic: b ? b.ic : "📖", titre: b ? b.t : "Chapitre " + (c.chapter || ""), coul: b ? OU_COUL[b.k] : OU_COUL.chap, ret: "← " + st, retId: "btnChapClose", cible: "chapDetail" };
  }
  for (const [id, ic, t, k, ret] of [["vidBox", "🎬", "Vidéos de la série", "vid", "vidFermer"], ["dlgsBox", "🎭", "Dialogues de la série", "dlg", "dlgsFermer"],
                                     ["suiviBox", "⚙", "Profil et traitement", "prof", "suiviFermer"]])
    if (ouVis(id)) return { fil: [{ t: "📚", go: "racine" }, { t: titre, go: "serie" }, { t: ic + " " + t }], ic, titre: t, coul: OU_COUL[k], ret: "← " + titre, retId: ret, cible: id };
  if (ouVis("libNav")) return { fil: [{ t: "📚", go: "racine" }, { t: titre }], ic: "📚", titre, coul: OU_COUL.serie, ret: "← Toutes les séries", retId: "btnLibBack", cible: "libNav" };
  return null;
}
let OU_DERNIER = "";
function ouMaj(){
  let e = null; try { e = ouEtat(); } catch (err) {}
  const cle = JSON.stringify(e); if (cle === OU_DERNIER) return; OU_DERNIER = cle;
  const fil = document.getElementById("ouFil"), bande = document.getElementById("ouBande"); if (!fil || !bande) return;
  fil.hidden = bande.hidden = !e; if (!e) return;
  fil.innerHTML = e.fil.map((x, i) => (i ? "<i>›</i>" : "") + '<button type="button"' + (i === e.fil.length - 1 ? ' class="ici"' : "")
    + (x.go ? ' data-ou-go="' + x.go + '"' : "") + ' title="' + esc(x.t) + '">' + esc(x.t) + "</button>").join("");
  const cib = document.getElementById(e.cible);                // le bandeau se place JUSTE au-dessus de l'ecran concerne
  if (cib && cib.parentNode && bande.nextElementSibling !== cib) cib.parentNode.insertBefore(bande, cib);
  bande.style.setProperty("--ouc", e.coul);
  bande.innerHTML = '<button type="button" class="btn sm retour" data-ou-ret="' + e.retId + '">' + esc(e.ret) + '</button><span class="ou-ic">' + e.ic
    + '</span><span class="ou-t">' + esc(e.titre) + "</span>";
}
function ouCliquer(id){ const b = document.getElementById(id); if (b && b.offsetParent !== null) b.click(); }
document.addEventListener("click", e => {
  const r = e.target.closest("[data-ou-ret]"), g = e.target.closest("[data-ou-go]");
  if (r){ ouCliquer(r.dataset.ouRet); setTimeout(ouMaj, 60); return; }
  if (g){
    const go = g.dataset.ouGo;
    if (go === "chapitre"){ clOuvrir(""); }
    else {                                                   // serie / racine : on referme ce qui est ouvert au-dessus
      ["btnChapClose", "vidFermer", "dlgsFermer", "suiviFermer"].forEach(ouCliquer);
      if (go === "racine") setTimeout(() => ouCliquer("btnLibBack"), 80);
    }
    setTimeout(ouMaj, 150); return;
  }
  setTimeout(ouMaj, 60);
});
setInterval(ouMaj, 700);""")
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
