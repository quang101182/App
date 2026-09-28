"""app 3.5.6 -> 3.5.7 (Quang 28/09 16h53 : FAVORIS « pour les avoir en debut de liste, en priorite ; simple et rapide ; principale
et secondaire ») : ☆ / ★ sur chaque carte de serie (coin haut-droit) et a cote du titre de la page de la serie ; les favoris passent
EN TETE de la liste, le tri choisi s'applique a l'interieur de chaque groupe (et donc aussi a ‹ › entre series). Enregistre cote
serveur (patch_bibliotheque_favoris : fichier de bibliotheque de l'instance -> separe principale / secondaire, commun aux appareils).
Serveur pas encore relance : l'etoile revient en arriere et le dit. Copie, node --check, remplacement."""
import os, re, shutil, subprocess, sys

F = "D:/Download/02-Apps-Web/Repo-github/App/manga-studio/manga_studio.html"
TMP = os.path.join(os.environ.get("TEMP", "."), "manga_studio_357.html")
s = open(F, encoding="utf-8", newline="").read()
if 'const VERSION = "3.5.7"' in s:
    print("deja applique"); sys.exit(0)


def rep(a, b):
    global s
    for nl in ("\r\n", "\n", "\r\r\n"):
        a2, b2 = a.replace("\n", nl), b.replace("\n", nl)
        if s.count(a2) == 1:
            s = s.replace(a2, b2); return
    raise SystemExit("ancre introuvable : " + a[:80])


rep("<title>Manga Studio v3.5.6</title>", "<title>Manga Studio v3.5.7</title>")
rep('id="verBadge">v3.5.6</span>', 'id="verBadge">v3.5.7</span>')
rep('const VERSION = "3.5.6";', 'const VERSION = "3.5.7";   // v3.5.7 : favoris -- ☆ sur les series, les favorites en tete de liste ')

rep('''.serie-item>span{min-width:0}''', '''.serie-item>span{min-width:0}
/* v3.5.7 : favoris */
.serie-item{position:relative}
.fav-c{position:absolute;top:4px;right:6px;font-size:20px;line-height:1;padding:4px;color:var(--dim);opacity:.55;cursor:pointer;user-select:none}
.fav-c.on{color:#f5c542;opacity:1;text-shadow:0 0 6px rgba(245,197,66,.45)}
.serie-item>span{padding-right:26px}
.lib-titre-l{display:flex;align-items:center;gap:6px;min-width:0}.lib-titre-l h3{min-width:0}
.fav-b{flex:none;background:none;border:0;font-size:22px;line-height:1;padding:2px 4px;color:var(--dim);cursor:pointer}
.fav-b.on{color:#f5c542;text-shadow:0 0 6px rgba(245,197,66,.45)}''')

rep('''        <h3 id="libSerie"></h3><div class="lib-meta muted" id="libMeta"></div>''',
    '''        <div class="lib-titre-l"><h3 id="libSerie"></h3><button class="fav-b" id="libFav" title="mettre en favori (en tête de liste)" aria-pressed="false">☆</button></div><div class="lib-meta muted" id="libMeta"></div>''')

# tri : favoris en tete, le tri choisi a l'interieur
rep('''function trierSeries(l){''', '''function trierSeries(l){                          // v3.5.7 : les FAVORIS en tete, le tri choisi dans chaque groupe
  const fav = new Set(BIB.favoris || []), r = trierSeriesBase(l);
  return r.filter(s => fav.has(s.slug)).concat(r.filter(s => !fav.has(s.slug)));
}
function trierSeriesBase(l){''')

# etoile sur la carte
rep('''      + '<span><b>' + esc(s.title) + '</b>'
      + '<small>' + s.chaps.length + ' chapitre' ''',
    '''      + '<span class="fav-c' + ((BIB.favoris || []).includes(s.slug) ? " on" : "") + '" data-fav="' + esc(s.slug) + '" role="button" title="'
      + ((BIB.favoris || []).includes(s.slug) ? "retirer des favoris" : "mettre en favori (en tête de liste)") + '">' + ((BIB.favoris || []).includes(s.slug) ? "★" : "☆") + "</span>"   // v3.5.7
      + '<span><b>' + esc(s.title) + '</b>'
      + '<small>' + s.chaps.length + ' chapitre' ''')

rep('''$("chapList").onclick = e => {
  const af = e.target.closest("[data-afficher]");''', '''$("chapList").onclick = e => {
  const fv = e.target.closest("[data-fav]"); if (fv){ bibFavori(fv.dataset.fav); return; }          // v3.5.7 : l'etoile, pas la serie
  const af = e.target.closest("[data-afficher]");''')

rep('''$("btnLibBack").onclick = () => ouvrirSerie(null);''', '''$("btnLibBack").onclick = () => ouvrirSerie(null);
/* ---- v3.5.7 : FAVORIS ---- */
async function bibFavori(slug){
  if (!slug) return;
  const avant = (BIB.favoris || []).slice(), on = !avant.includes(slug);
  BIB.favoris = on ? avant.concat([slug]) : avant.filter(x => x !== slug);                   // tout de suite, sans attendre
  renderLib(); if (typeof nfMaj === "function") nfMaj();
  try {
    const r = await api("/manga/bibliotheque", { slug, action: on ? "favori" : "pas_favori" });
    if (r.error) throw new Error(/action inconnue/.test(r.error) ? "serveur à relancer (favoris pas encore connus)" : r.error);
    if (!Array.isArray(r.favoris)) throw new Error("serveur à relancer (favoris pas encore connus)");
    BIB.favoris = r.favoris;
    const t = (CHAPS.find(x => (x.slug || x.dir.split("/")[0]) === slug) || {}).title || slug;
    toast(on ? "★ « " + t + " » en favori — en tête de liste" : "☆ « " + t + " » retirée des favoris");
  } catch (err) { BIB.favoris = avant;
    toast("favori non enregistré : " + (/action inconnue/.test(err.message) ? "serveur de cette application à relancer (favoris pas encore connus)" : err.message)); }
  renderLib(); if (typeof nfMaj === "function") nfMaj();
}
function libFavMaj(){
  const b = $("libFav"); if (!b) return; const on = !!LIB_SERIE && (BIB.favoris || []).includes(LIB_SERIE);
  b.textContent = on ? "★" : "☆"; b.classList.toggle("on", on); b.setAttribute("aria-pressed", on);
  b.title = on ? "retirer des favoris" : "mettre en favori (en tête de liste)";
}
$("libFav").onclick = () => bibFavori(LIB_SERIE);
{ const _rl = renderLib; renderLib = function(){ _rl.apply(this, arguments); libFavMaj(); }; }''')

open(TMP, "w", encoding="utf-8", newline="").write(s)
js = "\n".join(re.findall(r"<script>(.*?)</script>", s, re.S))
open(TMP + ".js", "w", encoding="utf-8").write(js)
r = subprocess.run(["node", "--check", TMP + ".js"], capture_output=True, text=True)
if r.returncode:
    print("node --check KO", r.stderr[:800]); sys.exit(1)
if "--essai" in sys.argv:
    print("essai OK (rien remplace) :", TMP); sys.exit(0)
shutil.copy2(F, F + ".bak-v3560")
shutil.copy2(TMP, F)
print("ok v3.5.7")
