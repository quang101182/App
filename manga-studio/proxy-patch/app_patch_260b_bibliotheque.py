# -*- coding: utf-8 -*-
"""Manga Studio v2.6.0 (23/09/2026), etapes B3 a B6 de la ROADMAP § 4-quinquies : BIBLIOTHEQUE PERSONNELLE.

Quang : « exclure certains mangas [...] garder ma bibliotheque propre a moi », « filtres [...] par genre », « rangement ».
- B4 MASQUER : bouton dans la barre de la serie ; section repliee « Series masquees (N) » en bas ; commun a tous les
  appareils (proxy : sources/_bibliotheque.json). Masquer ne supprime rien.
- B5 TRIER : recemment ajoutee (defaut) / recemment ouverte (commune aux appareils) / A -> Z. Memorise par appareil.
- B6 FILTRER : pastilles Genres / Public / Statut / Themes (MangaDex, en francais), avec leur nombre ; plusieurs = la serie
  doit TOUTES les avoir ; seules les pastilles qui menent a quelque chose ; filtres actifs rappeles sous la barre.
- B3 : une serie qui a sa fiche MangaDex mais pas encore ses genres est rafraichie UNE fois (au fil de la liste).
Rejouable : python app_patch_260b_bibliotheque.py <manga_studio.html>.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "v2.6.0 : BIBLIOTHEQUE PERSONNELLE" in s:
    print("deja patche"); sys.exit(0)


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


for a in ("<title>Manga Studio v2.5.3</title>", 'id="verBadge">v2.5.3</span>', 'const VERSION = "2.5.3";'):
    rep(a, a.replace("2.5.3", "2.6.0"))

# ---------------------------------------------------------------- CSS
rep('''.lib-etat{margin:0 0 10px;font-size:12px;min-height:1.2em}''',
    '''.lib-etat{margin:0 0 10px;font-size:12px;min-height:1.2em}
/* v2.6.0 : tri, filtres, series masquees */
.lib-outils{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:0 0 6px}
.lib-outils[hidden],.lib-filtres[hidden],.lib-actifs[hidden]{display:none}
.lib-outils label{display:flex;gap:6px;align-items:center;font-size:12px;color:var(--dim);margin:0}
.lib-outils select{width:auto;min-width:0;padding:5px 8px}
.lib-filtres{margin:0 0 8px;padding:10px;border:1px solid var(--line);border-radius:10px;background:var(--panel)}
.lib-groupe+.lib-groupe{margin-top:8px}
.lib-groupe>b,.lib-groupe>summary{display:block;font-size:12px;color:var(--dim);margin:0 0 5px;font-weight:600;cursor:pointer}
.pastilles{display:flex;flex-wrap:wrap;gap:6px}
.pastille{border:1px solid var(--line);background:var(--panel2);color:var(--txt);border-radius:999px;padding:6px 12px;
  font:inherit;font-size:13px;min-height:34px;cursor:pointer;display:inline-flex;align-items:center;gap:5px}
.pastille small{opacity:.65;font-size:11px}
.pastille.on{background:color-mix(in srgb, var(--accent2) 28%, transparent);border-color:var(--accent2)}
.lib-actifs{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:0 0 8px}
#libFiltresBtn.filtre-actif{border-color:var(--accent2);background:color-mix(in srgb, var(--accent2) 22%, transparent)}
.lib-masquees{margin-top:12px}.lib-masquees>summary{cursor:pointer;color:var(--dim);font-size:13px;padding:6px 0}
.masquee-ligne{display:flex;gap:6px;align-items:stretch}.masquee-ligne>.chap-item{flex:1;min-width:0;opacity:.6}
.masquee-ligne>.btn{flex:none;align-self:center}
.serie-item small.serie-genres{color:var(--dim)}''')

# ---------------------------------------------------------------- HTML
rep('''  <p class="lib-etat muted" id="chapState"></p>''',
    '''  <div class="lib-outils" id="libOutils">
    <label>Trier <select id="libTri"><option value="ajout">récemment ajoutée</option><option value="ouverte">récemment ouverte</option>
      <option value="az">A → Z</option></select></label>
    <button class="btn sm" id="libFiltresBtn" aria-expanded="false" title="filtrer par genre, public, statut, thème">⛃ Filtres</button>
  </div>
  <div class="lib-filtres" id="libFiltres" hidden></div>
  <div class="lib-actifs" id="libActifs" hidden></div>
  <p class="lib-etat muted" id="chapState"></p>''')
rep('''    <button class="btn sm" id="btnRenommer" title="changer le titre (et le dossier) de la série">✏ Renommer</button>''',
    '''    <button class="btn sm" id="btnMasquer" title="retirer cette série de ta bibliothèque, sans rien supprimer (réversible)">🙈 Masquer</button>
    <button class="btn sm" id="btnRenommer" title="changer le titre (et le dossier) de la série">✏ Renommer</button>''')

# ---------------------------------------------------------------- JS : etat, traductions, outils
rep('''let LIB_RECH = "";''',
    '''let LIB_RECH = "";
// ---------- v2.6.0 : BIBLIOTHEQUE PERSONNELLE (masquer, trier, filtrer) -- ROADMAP § 4-quinquies ----------
let BIB = { masquees: [], ouvertes: {} }, LIB_TRI = "ajout", LIB_FILTRES = new Set(), GENRES_DEMANDES = new Set(), LIB_VOIR_MASQUEES = false;
try { const t = localStorage.getItem("manga_lib_tri"); if (["ajout", "ouverte", "az"].includes(t)) LIB_TRI = t;
      LIB_FILTRES = new Set(JSON.parse(localStorage.getItem("manga_lib_filtres") || "[]")); } catch {}
const GENRE_FR = { "Action": "Action", "Adventure": "Aventure", "Boys' Love": "Boys' love", "Comedy": "Comédie", "Crime": "Policier",
  "Drama": "Drame", "Fantasy": "Fantasy", "Girls' Love": "Girls' love", "Historical": "Historique", "Horror": "Horreur", "Isekai": "Isekai",
  "Magical Girls": "Magical girls", "Mecha": "Mecha", "Medical": "Médical", "Mystery": "Mystère", "Philosophical": "Philosophique",
  "Psychological": "Psychologique", "Romance": "Romance", "Sci-Fi": "Science-fiction", "Slice of Life": "Tranche de vie",
  "Sports": "Sport", "Superhero": "Super-héros", "Thriller": "Thriller", "Tragedy": "Tragédie", "Wuxia": "Wuxia" };
const THEME_FR = { "Aliens": "Extraterrestres", "Animals": "Animaux", "Cooking": "Cuisine", "Crossdressing": "Travestissement",
  "Delinquents": "Délinquants", "Demons": "Démons", "Genderswap": "Changement de sexe", "Ghosts": "Fantômes", "Gyaru": "Gyaru",
  "Harem": "Harem", "Magic": "Magie", "Mahjong": "Mahjong", "Martial Arts": "Arts martiaux", "Military": "Militaire",
  "Monster Girls": "Monster girls", "Monsters": "Monstres", "Music": "Musique", "Ninja": "Ninja", "Office Workers": "Bureau",
  "Police": "Police", "Post-Apocalyptic": "Post-apocalyptique", "Reincarnation": "Réincarnation", "Reverse Harem": "Harem inversé",
  "Samurai": "Samouraïs", "School Life": "Vie scolaire", "Supernatural": "Surnaturel", "Survival": "Survie",
  "Time Travel": "Voyage dans le temps", "Traditional Games": "Jeux traditionnels", "Vampires": "Vampires",
  "Video Games": "Jeux vidéo", "Villainess": "Méchante", "Virtual Reality": "Réalité virtuelle", "Zombies": "Zombies" };
const PUBLIC_FR = { shounen: "shōnen", seinen: "seinen", shoujo: "shōjo", josei: "josei" };
// une etiquette = « type:valeur » : g genre, p public, s statut, t theme (valeurs MangaDex, affichees en francais)
function etiquettes(s){
  const i = s.info || {}, e = [];
  (i.genres || []).forEach(g => e.push("g:" + g)); (i.themes || []).forEach(t => e.push("t:" + t));
  if (i.public) e.push("p:" + i.public);
  if (i.statut) e.push("s:" + i.statut);
  return e;
}
function libelleEtiq(k){
  const t = k.slice(0, 1), v = k.slice(2);
  return t === "g" ? (GENRE_FR[v] || v) : t === "t" ? (THEME_FR[v] || v) : t === "p" ? (PUBLIC_FR[v] || v) : (STATUT_LBL[v] || v);
}
const dateAjout = s => Math.max(0, ...s.chaps.map(i => Date.parse(CHAPS[i].captured_at || "") || 0));
function trierSeries(l){
  const az = (a, b) => a.title.localeCompare(b.title, "fr", { sensitivity: "base", numeric: true });
  if (LIB_TRI === "az") return l.sort(az);
  if (LIB_TRI === "ouverte") return l.sort((a, b) => ((BIB.ouvertes || {})[b.slug] || 0) - ((BIB.ouvertes || {})[a.slug] || 0) || dateAjout(b) - dateAjout(a) || az(a, b));
  return l.sort((a, b) => dateAjout(b) - dateAjout(a) || az(a, b));
}
const passeFiltres = s => { const e = new Set(etiquettes(s)); return [...LIB_FILTRES].every(k => e.has(k)); };
async function bibCharger(){ try { const b = await api("/manga/bibliotheque"); if (b && !b.error) BIB = b; } catch (e){ log("bibliothèque : " + e.message, "w"); } }
function libFiltresRendre(base){
  // base = les series visibles qui correspondent a la recherche ; une pastille propose ce qu'elle DONNERAIT en plus des filtres actifs
  const dispo = new Map();
  base.filter(passeFiltres).forEach(s => etiquettes(s).forEach(k => dispo.set(k, (dispo.get(k) || 0) + 1)));
  [...LIB_FILTRES].forEach(k => { if (!dispo.has(k)) dispo.set(k, 0); });
  const pastille = k => '<button class="pastille' + (LIB_FILTRES.has(k) ? " on" : "") + '" data-filtre="' + esc(k) + '" aria-pressed="'
    + LIB_FILTRES.has(k) + '">' + esc(libelleEtiq(k)) + (LIB_FILTRES.has(k) ? "" : "<small>" + dispo.get(k) + "</small>") + "</button>";
  const groupe = (t, titre) => {
    const ks = [...dispo.keys()].filter(k => k.startsWith(t + ":")).sort((a, b) => libelleEtiq(a).localeCompare(libelleEtiq(b), "fr"));
    return ks.length ? { titre, html: '<div class="pastilles">' + ks.map(pastille).join("") + "</div>", n: ks.length } : null;
  };
  const g = [groupe("g", "Genres"), groupe("p", "Public"), groupe("s", "Statut")].filter(Boolean), th = groupe("t", "Thèmes");
  const actifTheme = [...LIB_FILTRES].some(k => k.startsWith("t:"));
  $("libFiltres").innerHTML = (g.map(x => '<div class="lib-groupe"><b>' + x.titre + "</b>" + x.html + "</div>").join("")
    + (th ? '<details class="lib-groupe"' + (actifTheme ? " open" : "") + "><summary>+ Thèmes (" + th.n + ")</summary>" + th.html + "</details>" : ""))
    || '<p class="muted" style="margin:0">Aucun genre connu pour l\\u2019instant (ils viennent de MangaDex, fiche « 📅 Tomes et dates »).</p>';
  $("libFiltresBtn").textContent = "⛃ Filtres" + (LIB_FILTRES.size ? " (" + LIB_FILTRES.size + ")" : "");
  $("libFiltresBtn").classList.toggle("filtre-actif", LIB_FILTRES.size > 0);
  $("libActifs").hidden = !LIB_FILTRES.size;
  $("libActifs").innerHTML = [...LIB_FILTRES].map(k => '<button class="pastille on" data-filtre="' + esc(k) + '" title="retirer ce filtre">'
    + esc(libelleEtiq(k)) + " ✕</button>").join("") + (LIB_FILTRES.size ? '<button class="btn sm" data-filtres-vider>Tout effacer</button>' : "");
}
function libFiltresBasculer(k){
  LIB_FILTRES.has(k) ? LIB_FILTRES.delete(k) : LIB_FILTRES.add(k);
  try { localStorage.setItem("manga_lib_filtres", JSON.stringify([...LIB_FILTRES])); } catch {}
  renderLib();
}''')

# ---------------------------------------------------------------- renderLib : la liste
rep('''  $("libRechBox").hidden = !!serie;''',
    '''  $("libRechBox").hidden = !!serie;
  $("libOutils").hidden = !!serie; if (serie){ $("libFiltres").hidden = true; $("libActifs").hidden = true; }      // v2.6.0''')
rep('''    const trouvees = series.map(s => Object.assign(s, { rech: chercherSerie(s, LIB_RECH) })).filter(s => s.rech.ok);
    $("chapList").innerHTML = trouvees.map(s =>''',
    '''    // v2.6.0 : masquees a part, puis recherche -> filtres -> tri
    const masq = new Set(BIB.masquees || []);
    const visibles = series.filter(s => !masq.has(s.slug)), cachees = series.filter(s => masq.has(s.slug));
    const base = visibles.map(s => Object.assign(s, { rech: chercherSerie(s, LIB_RECH) })).filter(s => s.rech.ok);
    libFiltresRendre(base);
    const trouvees = trierSeries(base.filter(passeFiltres));
    const cacheesTrouvees = trierSeries(cachees.map(s => Object.assign(s, { rech: chercherSerie(s, LIB_RECH) })).filter(s => s.rech.ok));
    // B3 : fiche MangaDex sans genres (fiche d'avant la v2.6.0) -> rafraichie une fois, sans bruit
    visibles.filter(s => s.info && s.info.mangadex_id && !s.info.genres && !GENRES_DEMANDES.has(s.slug)).slice(0, 1).forEach(s => {
      GENRES_DEMANDES.add(s.slug); chercherTomes(s.slug).catch(e => log("genres : " + s.slug + " : " + e.message, "w")); });
    const carte = s => (''')
rep('''      + (s.info ? '<small>' + esc(infoSerie(s.info)) + '</small>' : "")''',
    '''      + (s.info ? '<small>' + esc(infoSerie(s.info)) + '</small>' : "")
      + ((s.info && (s.info.genres || []).length) ? '<small class="serie-genres">' + esc(s.info.genres.map(g => GENRE_FR[g] || g).join(" · ")) + "</small>" : "")''')
rep('''      + (LIB_RECH && s.rech.raison ? '<small class="trouve">trouvé : ' + esc(s.rech.raison) + '</small>' : "")
      + '</span></button>').join("")
      || (LIB_RECH ? '<p class="muted aide">Aucune série ne correspond à « ' + esc(LIB_RECH) + ' ».</p>'
                   : '<p class="muted aide">Aucun chapitre dans sources/. Capture-en un ci-dessus.</p>');
    $("chapState").textContent = (LIB_RECH ? trouvees.length + " / " : "") + series.length + " série(s) · "
      + CHAPS.length + " chapitre(s)";''',
    '''      + (LIB_RECH && s.rech.raison ? '<small class="trouve">trouvé : ' + esc(s.rech.raison) + '</small>' : "")
      + '</span></button>');
    const vide = LIB_RECH || LIB_FILTRES.size
      ? '<p class="muted aide">Aucune série ' + (LIB_RECH ? "ne correspond à « " + esc(LIB_RECH) + " »" : "")
        + (LIB_RECH && LIB_FILTRES.size ? " avec " : "") + (LIB_FILTRES.size ? (LIB_RECH ? "" : "ne réunit ") + "ces filtres" : "") + "."
        + (cacheesTrouvees.length && LIB_RECH ? " " + cacheesTrouvees.length + " résultat(s) dans les séries masquées, en bas." : "") + "</p>"
      : (cachees.length ? '<p class="muted aide">Toutes tes séries sont masquées.</p>' : '<p class="muted aide">Aucun chapitre dans sources/. Capture-en un ci-dessus.</p>');
    const montrees = LIB_RECH ? cacheesTrouvees : cachees;
    $("chapList").innerHTML = (trouvees.map(carte).join("") || vide)
      + (montrees.length ? '<details class="lib-masquees" id="libMasquees"' + (LIB_VOIR_MASQUEES ? " open" : "") + "><summary>👁 Séries masquées ("
        + montrees.length + ")</summary>" + montrees.map(s => '<div class="masquee-ligne">' + carte(s)
          + '<button class="btn sm" data-afficher="' + esc(s.slug) + '" title="la remettre dans ta bibliothèque">Ré-afficher</button></div>').join("")
        + "</details>" : "");
    const filtre = LIB_RECH || LIB_FILTRES.size;
    $("chapState").textContent = (filtre ? trouvees.length + " / " : "") + visibles.length + " série(s)"
      + (cachees.length ? " · " + cachees.length + " masquée(s)" : "") + " · " + CHAPS.length + " chapitre(s)";''')
rep('''  $("libSerie").textContent = serie.title + (serie.info ? " — " + infoSerie(serie.info) : "");''',
    '''  $("libSerie").textContent = serie.title + (serie.info ? " — " + infoSerie(serie.info) : "");
  const estMasquee = (BIB.masquees || []).includes(serie.slug);                                    // v2.6.0
  $("btnMasquer").textContent = estMasquee ? "👁 Ré-afficher" : "🙈 Masquer";
  $("btnMasquer").title = estMasquee ? "la remettre dans ta bibliothèque" : "retirer cette série de ta bibliothèque, sans rien supprimer (réversible)";''')

# ---------------------------------------------------------------- chargement, ouverture, clics
rep('''  const j = await api("/manga/sources");
  CHAPS = j.items || [];''',
    '''  const [j] = await Promise.all([api("/manga/sources"), bibCharger()]);                        // v2.6.0 : + masquees / ouvertes
  CHAPS = j.items || [];''')
rep('''function ouvrirSerie(slug){
  LIB_SERIE = slug || null;''',
    '''function ouvrirSerie(slug){
  LIB_SERIE = slug || null;
  if (slug){ BIB.ouvertes = BIB.ouvertes || {}; BIB.ouvertes[slug] = Date.now() / 1000;                // v2.6.0 : tri « récemment ouverte »
    api("/manga/bibliotheque", { action: "ouverte", slug }).catch(() => {}); }''')
rep('''$("chapList").onclick = e => {
  const sv = e.target.closest("[data-serie]");''',
    '''async function bibMasquer(slug, masquer){
  const r = await api("/manga/bibliotheque", { action: masquer ? "masquer" : "afficher", slug });
  if (r.error) throw new Error(r.error);
  BIB = r;
  const t = ((seriesDe(CHAPS).find(x => x.slug === slug) || {}).title) || slug;
  log("bibliothèque : « " + t + " » " + (masquer ? "masquée" : "ré-affichée"));
  toast(masquer ? "🙈 « " + t + " » masquée — elle reste en bas, dans « Séries masquées »" : "👁 « " + t + " » de retour dans ta bibliothèque");
}
$("btnMasquer").onclick = async () => {
  const slug = LIB_SERIE; if (!slug) return;
  const masquer = !(BIB.masquees || []).includes(slug);
  try { await bibMasquer(slug, masquer); if (masquer) ouvrirSerie(null); else renderLib(); }
  catch (e){ log("bibliothèque : " + e.message, "e"); alert(e.message); }
};
$("libTri").value = LIB_TRI;
$("libTri").onchange = () => { LIB_TRI = $("libTri").value; try { localStorage.setItem("manga_lib_tri", LIB_TRI); } catch {} renderLib(); $("libTri").blur(); };
$("libFiltresBtn").onclick = () => {
  $("libFiltres").hidden = !$("libFiltres").hidden;
  $("libFiltresBtn").setAttribute("aria-expanded", String(!$("libFiltres").hidden));
};
$("libFiltres").onclick = e => { const b = e.target.closest("[data-filtre]"); if (b) libFiltresBasculer(b.dataset.filtre); };
$("libActifs").onclick = e => {
  const b = e.target.closest("[data-filtre]"); if (b){ libFiltresBasculer(b.dataset.filtre); return; }
  if (e.target.closest("[data-filtres-vider]")){ LIB_FILTRES.clear(); try { localStorage.setItem("manga_lib_filtres", "[]"); } catch {} renderLib(); }
};
$("chapList").addEventListener("toggle", e => { if (e.target.id === "libMasquees") LIB_VOIR_MASQUEES = e.target.open; }, true);
$("chapList").onclick = e => {
  const af = e.target.closest("[data-afficher]");                                                   // v2.6.0
  if (af){ bibMasquer(af.dataset.afficher, false).then(renderLib).catch(err => { log("bibliothèque : " + err.message, "e"); alert(err.message); }); return; }
  const sv = e.target.closest("[data-serie]");''')
open(p, "w", encoding="utf-8").write(s)
print("patche")
