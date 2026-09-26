# -*- coding: utf-8 -*-
"""v2.79.0 (Quang 26/09 16h30 : maquette_liens_video_v1, variante B) : fiche du chapitre -- le LIEN vers la video se voit.
- Narration, Traduction, Musique portent « → 🎬 » (ce qu'elles nourrissent) ;
- la ligne Video montre ses INGREDIENTS : 🎙 (narration : obligatoire), 🌐 FR/VO (pages traduites si elles existent),
  🎵 N (musique si choisie) -- vert = pret, pointille = facultatif et absent. Rien n'est bloque.
- UN seul bouton « respire » : l'etape utile suivante (Narrer -> sinon Traduire si VO non traduite -> sinon Faire la video).
  La musique ne respire jamais (pur choix). Coupe si « reduire les animations ».
Rejouable : python app_patch_279_liens_video.py [chemin de manga_studio.html]"""
import io, sys
P = sys.argv[1] if len(sys.argv) > 1 else r"D:\Download\02-Apps-Web\Repo-github\App\manga-studio\manga_studio.html"
s = io.open(P, encoding="utf-8", newline="").read()
if 'const VERSION = "2.79.0"' in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"
def rep(a, z):
    global s
    a, z = a.replace("\n", NL), z.replace("\n", NL)
    assert s.count(a) == 1, ("ancre", a[:70], s.count(a))
    s = s.replace(a, z)
# --- CSS
rep(""".cl-chev{color:var(--dim);font-size:18px;flex:none;transition:transform .15s}.cl-ouv .cl-chev{transform:rotate(90deg)}""",
""".cl-chev{color:var(--dim);font-size:18px;flex:none;transition:transform .15s}.cl-ouv .cl-chev{transform:rotate(90deg)}
/* v2.79.0 (maquette_liens_video_v1 B) : « → 🎬 » + ingredients de la video + lueur de l'etape suivante */
.cl-vers{font-size:11px;color:#e8a84a;white-space:nowrap;flex:none;opacity:.85}
.cl-ing{font-size:11px;border:1px solid var(--line);border-radius:999px;padding:1px 6px;color:var(--dim);white-space:nowrap}
.cl-ing.ok{color:#4fd28a;border-color:#2f6b4c}.cl-ing.opt{border-style:dashed}
@keyframes clLueur{0%,100%{box-shadow:0 0 0 0 rgba(255,210,90,0)}50%{box-shadow:0 0 0 3px rgba(255,210,90,.45)}}
.cl-act .btn.cl-suiv{animation:clLueur 2.2s ease-in-out infinite;outline:1px solid rgba(255,210,90,.6)}
@media (prefers-reduced-motion:reduce){.cl-act .btn.cl-suiv{animation:none}}""")
rep("""  .cl-est{display:none} .cl-box.bloc-narr:not(.cl-ouv) .cl-est{display:flex;flex-wrap:wrap;flex:0 1 auto;min-width:0}""",
"""  .cl-est{display:none} .cl-box.bloc-narr:not(.cl-ouv) .cl-est{display:flex;flex-wrap:wrap;flex:0 1 auto;min-width:0}
  .cl-box.bloc-vid > .cl-tete{flex-wrap:wrap;row-gap:4px}                                   /* v2.79.0 : ingredients en 2e ligne */
  .cl-box.bloc-vid .cl-est{display:flex;flex-wrap:wrap;order:10;flex:1 1 100%;padding-left:34px} .cl-vers{font-size:10px}
  .cl-box.bloc-narr .cl-vers{display:none}   /* v2.79.0 : a 360 px la fleche mangeait l'etat ; le lien est dit par 🎙 sur la Video */""")
# --- etat de la video : ses ingredients
rep("""    return { etat: e ? e.textContent : "narre d'abord ce chapitre", est: "",""",
"""    return { etat: e ? e.textContent : "narre d'abord ce chapitre", est: clIngredients(),""")
rep("""function clMaj(){
  if (!$("chapDetail") || $("chapDetail").hidden) return;""",
"""// v2.79.0 : ce que la VIDEO va utiliser -- 🎙 narration (obligatoire), 🌐 pages traduites (sinon VO), 🎵 musique (si choisie)
function clTradOk(){
  const l = LANGUE_CHAP[CHAP_OPEN], cible = $("tradLangue").value, r = RESUME && RESUME.chapitres[CHAP_OPEN];
  return !!((l && l.langue === cible) || (r && (r.trad || []).includes(cible)));
}
function clIngredients(){
  const n = document.querySelectorAll("#narrRuns [data-ecoute]").length, nb = document.querySelectorAll("#musListe input:checked").length;
  const cible = ($("tradLangue").value || "fr").toUpperCase(), ok = clTradOk();
  const p = (cls, txt, t) => '<span class="cl-ing ' + cls + '" title="' + t + '">' + txt + "</span>";
  return p(n ? "ok" : "", n ? "🎙" : "🎙 à faire", n ? "narration prête" : "la vidéo a besoin d'une narration")
       + p(ok ? "ok" : "opt", "🌐 " + (ok ? cible : "VO"), ok ? "pages en " + cible : "pas traduit : les pages de la vidéo seront en VO (facultatif)")
       + p(nb ? "ok" : "opt", "🎵 " + (nb || "—"), nb ? nb + " morceau(x) dans la vidéo" : "sans musique (facultatif)");
}
// l'etape utile SUIVANTE (une seule) : narrer -> traduire (si VO non traduite) -> faire la video. Jamais la musique.
function clSuivante(){
  if (document.querySelector("#narrRuns .narr-pbar")) return "";                         // une narration tourne
  if (!document.querySelectorAll("#narrRuns [data-ecoute]").length) return "narr";
  if (!clTradOk() && !/en cours|\d+\s*\/\s*\d+/i.test($("tradEtat").textContent || "")) return "trad";
  if (!$("chapVid").querySelector("[data-vid-voir]") && $("chapVid").querySelector("[data-vid-gen]")) return "vid";
  return "";
}
function clMaj(){
  if (!$("chapDetail") || $("chapDetail").hidden) return;""")
rep("""      h.innerHTML = '<span class="cl-ic">' + b.ic + '</span><span class="cl-t">' + b.t + '</span><span class="cl-etat"></span>'
        + '<span class="cl-est"></span><span class="cl-act"></span><span class="cl-chev">›</span>';""",
"""      h.innerHTML = '<span class="cl-ic">' + b.ic + '</span><span class="cl-t">' + b.t + '</span><span class="cl-etat"></span>'
        + (b.k !== "vid" ? '<span class="cl-vers" title="utilisé par la vidéo">→ 🎬</span>' : "")          // v2.79.0
        + '<span class="cl-est"></span><span class="cl-act"></span><span class="cl-chev">›</span>';""")
rep("""    if (q(".cl-act").innerHTML !== e.act) q(".cl-act").innerHTML = e.act;
  });""", """    if (q(".cl-act").innerHTML !== e.act) q(".cl-act").innerHTML = e.act;
  });
  const suiv = clSuivante();                                                            // v2.79.0 : une seule lueur
  document.querySelectorAll("#chapDetail .cl-tete").forEach(h => {
    const b = h.querySelector(".cl-act .btn:not([disabled]):not([data-cl-ecoute])");
    h.querySelectorAll(".cl-act .btn.cl-suiv").forEach(x => { if (x !== b || h.dataset.cl !== suiv) x.classList.remove("cl-suiv"); });
    if (b && h.dataset.cl === suiv) b.classList.add("cl-suiv");
  });""")
rep("<title>Manga Studio v2.78.0</title>", "<title>Manga Studio v2.79.0</title>")
rep('<span class="ver" id="verBadge">v2.78.0</span>', '<span class="ver" id="verBadge">v2.79.0</span>')
rep('const VERSION = "2.78.0";', 'const VERSION = "2.79.0";')
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("v2.79.0 applique")
