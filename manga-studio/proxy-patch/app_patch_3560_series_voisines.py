"""app 3.5.5 -> 3.5.6 (Quang 28/09 09h12-09h16 : « sur la page d'une serie, les boutons precedent / suivant de la barre du bas
permettent de passer a la serie suivante ou precedente » + « les slides aussi sur smartphone, gauche droite ») :
- page d'une SERIE : ‹ / › de la barre du bas = serie precedente / suivante, dans l'ORDRE DE LA BIBLIOTHEQUE tel qu'affiche
  (tri + filtres + recherche), FIGE a son dernier affichage -- sinon le tri « recemment ouverte » se reordonnerait a chaque
  passage ; info-bulle = nom de la voisine ; message apres le passage ; grise en bout de liste ;
- glisser la barre : droite = suivante, gauche = precedente (comme dans un chapitre ; avant, gauche = « ← Séries », qui reste
  sur son bouton) ;
- le glissement VERS LE BAS (selecteur des chapitres) ne change pas.
Copie, node --check, remplacement."""
import os, re, shutil, subprocess, sys

F = "D:/Download/02-Apps-Web/Repo-github/App/manga-studio/manga_studio.html"
TMP = os.path.join(os.environ.get("TEMP", "."), "manga_studio_356.html")
s = open(F, encoding="utf-8", newline="").read()
if 'const VERSION = "3.5.6"' in s:
    print("deja applique"); sys.exit(0)


def rep(a, b):
    global s
    for nl in ("\r\n", "\n", "\r\r\n"):
        a2, b2 = a.replace("\n", nl), b.replace("\n", nl)
        if s.count(a2) == 1:
            s = s.replace(a2, b2); return
    raise SystemExit("ancre introuvable : " + a[:80])


rep("<title>Manga Studio v3.5.5</title>", "<title>Manga Studio v3.5.6</title>")
rep('id="verBadge">v3.5.5</span>', 'id="verBadge">v3.5.6</span>')
rep('const VERSION = "3.5.5";', 'const VERSION = "3.5.6";   // v3.5.6 : page d une serie -- ‹ › et glissements gauche / droite = serie precedente / suivante ')

rep('''let LIB_SERIE = null; try { LIB_SERIE = localStorage.getItem("manga_serie"); } catch {}''',
    '''let LIB_SERIE = null; try { LIB_SERIE = localStorage.getItem("manga_serie"); } catch {}
let LIB_ORDRE = [];                               // v3.5.6 : ordre des series tel qu'AFFICHE (fige), pour ‹ / › entre series''')

rep('''    const trouvees = trierSeries(base.filter(passeFiltres));''',
    '''    const trouvees = trierSeries(base.filter(passeFiltres));
    LIB_ORDRE = trouvees.map(s => s.slug);                                       // v3.5.6 : fige tant qu'on navigue de serie en serie''')

rep('''function nfInfoMaj(txt){''', '''/* ---- v3.5.6 : series voisines (page d'une serie) ---- */
function libOrdreCalc(){                          // meme chemin que renderLib : masquees exclues, recherche, filtres, tri
  const masq = new Set(BIB.masquees || []);
  const base = mesSeries().filter(s => !masq.has(s.slug)).map(s => Object.assign(s, { rech: chercherSerie(s, LIB_RECH) })).filter(s => s.rech.ok);
  return trierSeries(base.filter(passeFiltres)).map(s => s.slug);
}
function nfSerieVoisine(d){
  if (!LIB_SERIE) return null;
  if (!LIB_ORDRE.includes(LIB_SERIE)) LIB_ORDRE = libOrdreCalc();                // ouverte sans passer par la liste (demarrage)
  const i = LIB_ORDRE.indexOf(LIB_SERIE); if (i < 0) return null;
  const slug = LIB_ORDRE[i + d]; if (!slug || !mesSeries().some(s => s.slug === slug)) return null;
  return { slug, titre: (CHAPS.find(x => (x.slug || x.dir.split("/")[0]) === slug) || {}).title || slug };
}
function nfInfoMaj(txt){''')

rep('''  [["nfPrev", "chapPrev", -1], ["nfSuiv", "chapNext", 1]].forEach(([id, src, d]) => {
    const v = c === "chapitre" ? nfVoisin(src) : null, b = $(id);''',
    '''  [["nfPrev", "chapPrev", -1], ["nfSuiv", "chapNext", 1]].forEach(([id, src, d]) => {
    if (c === "serie"){ const sv = nfSerieVoisine(d), b = $(id);                  // v3.5.6 : serie precedente / suivante
      b.disabled = !sv; b.textContent = d < 0 ? "‹" : "›";
      b.title = sv ? "série " + (d < 0 ? "précédente" : "suivante") + " : " + sv.titre : "pas de série " + (d < 0 ? "précédente" : "suivante") + " dans la liste";
      return; }
    const v = c === "chapitre" ? nfVoisin(src) : null, b = $(id);''')

rep('''  if (sens === "retour"){ (NF.ctx === "chapitre" ? $("btnChapClose") : $("btnLibBack")).click(); return; }''',
    '''  if (sens === "retour"){ (NF.ctx === "chapitre" ? $("btnChapClose") : $("btnLibBack")).click(); return; }
  if (NF.ctx === "serie"){ const sv = nfSerieVoisine(sens); if (!sv) return;      // v3.5.6
    ouvrirSerie(sv.slug); scrollTo(0, 0); nfMaj(); toast((sens > 0 ? "▶ série suivante : " : "◀ série précédente : ") + sv.titre); return; }''')

rep('''                    : (NF.ctx === "serie" && dx < 0 ? ["retour", "← Séries"] : null);''',
    '''                    : NF.ctx === "serie" ? ((v => v && [dx > 0 ? "suivant" : "precedent", dx > 0 ? v.titre + " ›" : "‹ " + v.titre])(nfSerieVoisine(dx > 0 ? 1 : -1)))   // v3.5.6
                    : null;''')

open(TMP, "w", encoding="utf-8", newline="").write(s)
js = "\n".join(re.findall(r"<script>(.*?)</script>", s, re.S))
open(TMP + ".js", "w", encoding="utf-8").write(js)
r = subprocess.run(["node", "--check", TMP + ".js"], capture_output=True, text=True)
if r.returncode:
    print("node --check KO", r.stderr[:800]); sys.exit(1)
if "--essai" in sys.argv:
    print("essai OK (rien remplace) :", TMP); sys.exit(0)
shutil.copy2(F, F + ".bak-v3550")
shutil.copy2(TMP, F)
print("ok v3.5.6")
