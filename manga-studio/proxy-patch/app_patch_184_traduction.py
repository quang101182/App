import shutil
p = r"D:\Download\02-Apps-Web\Repo-github\App\manga-studio\manga_studio.html"
shutil.copy(p, p + ".bak-20260922-v184")
s = open(p, encoding="utf-8").read()


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:80])
    s = s.replace(a, b)


for a, b in (("<title>Manga Studio v1.83.0</title>", "<title>Manga Studio v1.84.0</title>"),
             ('id="verBadge">v1.83.0<', 'id="verBadge">v1.84.0<'),
             ('const VERSION = "1.83.0";', 'const VERSION = "1.84.0";')):
    rep(a, b)

# ---------- HTML : bloc traduction, sous la narration ----------
rep('''      <div id="narrRuns" class="narr-runs"></div>''',
    '''      <div id="narrRuns" class="narr-runs"></div>
    </div>
    <!-- TRADUCTION DES DIALOGUES (v1.84.0, etape 11 b) : scripts/traduire_chapitre.py via le proxy -->
    <div class="narr-box trad-box">
      <div class="row" style="align-items:flex-end">
        <div style="width:150px"><label>🌐 Traduire en</label><select id="tradLangue">
          <option value="fr">français</option><option value="en">anglais</option><option value="es">espagnol</option>
          <option value="de">allemand</option><option value="it">italien</option><option value="pt">portugais</option>
          <option value="vi">vietnamien</option></select></div>
        <button class="btn" id="btnTraduire" title="efface le texte des bulles et y pose la traduction (onomatopées laissées telles quelles)">Traduire les dialogues</button>
        <div style="width:150px"><label>Afficher les pages</label><select id="tradVue"><option value="">VO (original)</option></select></div>
      </div>
      <p class="muted aide" id="tradEtat" style="margin:6px 0 0"></p>''')
rep('''.narr-essais{margin-top:4px}''',
    '''.trad-box{margin-top:10px}
.narr-essais{margin-top:4px}''')

# ---------- JS : pages VO / traduites ----------
rep('''const srcURL = p =>''',
    '''// v1.84.0 : une page s'affiche en VO ou dans la langue choisie (si ce chapitre a ete traduit)
let TRADS = [], TRAD_VUE = "", TRAD_POLL = null;
try { TRAD_VUE = localStorage.getItem("manga_trad_vue") || ""; } catch {}
function tradMap(){ const t = TRADS.find(x => x.langue === TRAD_VUE && x.etat === "fini"); return t ? t.pages || {} : null; }
function pageSrc(chemin){
  const m = tradMap(), f = (chemin || "").split("/").pop();
  return srcURL(m && m[f] ? m[f] : chemin);
}
const srcURL = p =>''')
rep('''    '<figure data-page="' + k + '"><img loading="lazy" src="' + srcURL(p.path) + '" alt="page ' + (k + 1) + '">\'''',
    '''    '<figure data-page="' + k + '"><img loading="lazy" src="' + pageSrc(p.path) + '" alt="page ' + (k + 1) + '">\'''')
rep('''    ouvrirVisionneuse(j.pages.map((pg, k) => ({ url: srcURL(pg.path), nom: "p. " + (k + 1) })), +f.dataset.page);''',
    '''    ouvrirVisionneuse(j.pages.map((pg, k) => ({ url: pageSrc(pg.path), nom: "p. " + (k + 1) })), +f.dataset.page);''')
rep('''  img.src = srcURL(CHAP_OPEN + "/" + p.file);''', '''  img.src = pageSrc(CHAP_OPEN + "/" + p.file);''')
rep('''  if (suivant) (new Image()).src = srcURL(CHAP_OPEN + "/" + suivant.file);''',
    '''  if (suivant) (new Image()).src = pageSrc(CHAP_OPEN + "/" + suivant.file);''')
rep('''  CHAP_PAGES = j.pages.length; narrEstim(); reprendreVoix();''',
    '''  CHAP_PAGES = j.pages.length; narrEstim(); reprendreVoix();
  refreshTrads().catch(err => log("traductions : " + err.message, "w"));''')
rep('''async function refreshNarrs(){''',
    '''const LANGUE_LBL = { fr: "français", en: "anglais", es: "espagnol", de: "allemand", it: "italien", pt: "portugais", vi: "vietnamien" };
function rafraichirPages(){
  document.querySelectorAll("#chapPages figure img").forEach((im, k) => {
    const pg = CHAP_PAGE_LIST[k]; if (pg) im.src = pageSrc(pg.path);
  });
}
async function refreshTrads(){
  if (!CHAP_OPEN) return;
  const j = await api("/manga/traductions?d=" + encodeURIComponent(CHAP_OPEN));
  TRADS = j.items || [];
  const finies = TRADS.filter(t => t.etat === "fini");
  $("tradVue").innerHTML = '<option value="">VO (original)</option>'
    + finies.map(t => '<option value="' + t.langue + '">' + esc(LANGUE_LBL[t.langue] || t.langue) + '</option>').join("");
  $("tradVue").value = finies.some(t => t.langue === TRAD_VUE) ? TRAD_VUE : "";
  const enCours = TRADS.find(t => t.etat === "en cours");
  const f = finies.find(t => t.langue === $("tradVue").value) || finies[0];
  $("tradEtat").innerHTML = enCours
      ? "⏳ traduction en " + esc(LANGUE_LBL[enCours.langue] || enCours.langue) + " — page " + ((enCours.progress || {}).fait || 0)
        + "/" + ((enCours.progress || {}).total || "?")
      : f && f.stats ? "✅ " + esc(LANGUE_LBL[f.langue] || f.langue) + " : " + f.stats.traduites + " bulle(s) traduite(s), "
        + f.stats.onomatopees + " onomatopée(s) laissée(s) · " + fmtUsd(f.stats.cout) + " · " + fmtS(f.stats.s || 0)
      : (TRADS.find(t => t.etat === "echec") ? "❌ la dernière traduction a échoué" : "Pas encore traduit. Les onomatopées restent telles quelles.");
  $("btnTraduire").disabled = !!enCours;
  rafraichirPages();
  if (enCours && !TRAD_POLL) TRAD_POLL = setInterval(() => refreshTrads().catch(e => log("traductions : " + e.message, "w")), 4000);
  if (!enCours && TRAD_POLL){ clearInterval(TRAD_POLL); TRAD_POLL = null; chargerCouts(); }
}
$("tradVue").onchange = () => {
  TRAD_VUE = $("tradVue").value; try { localStorage.setItem("manga_trad_vue", TRAD_VUE); } catch {}
  rafraichirPages(); $("tradVue").blur();
};
$("btnTraduire").onclick = async () => {
  const lg = $("tradLangue").value, n = CHAP_PAGES;
  if (!confirm("Traduire les dialogues des " + n + " pages en " + (LANGUE_LBL[lg] || lg) + " ?\\n\\nCoût ≈ "
               + (n * 0.016).toFixed(2) + " $ (mesuré 0,016 $/page), ~" + fmtS(n * 14) + ". Les pages VO ne sont pas modifiées.")) return;
  try {
    const r = await api("/manga/traduire", { d: CHAP_OPEN, langue: lg });
    if (r.error) throw new Error(r.error);
    log("traduction lancée : " + CHAP_OPEN + " → " + lg);
    TRAD_VUE = lg; try { localStorage.setItem("manga_trad_vue", lg); } catch {}
    await refreshTrads();
  } catch (e){ log("traduction : " + e.message, "e"); alert(e.message); }
};
async function refreshNarrs(){''')

open(p, "w", encoding="utf-8").write(s)
print("patch app v1.84.0 OK")
