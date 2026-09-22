# -*- coding: utf-8 -*-
"""App v2.1.1 -> v2.2.0 : la LANGUE d'origine du chapitre, affichee (Quang 22/09 12h43 : « c'est marque VO original [...]
j'aurais pu lancer une traduction francais vers francais »). « Pages affichees : VO — vietnamien » ; « ⚠ deja en francais »
a cote du choix de langue ; confirmation avant une traduction vers la meme langue (le proxy la refuse sinon) ; la langue sur
la carte du chapitre. Source : GET /manga/langue (detectee a la 1re ouverture, gardee). Verifie ses ancres.
"""
import shutil
p = r"D:\Download\02-Apps-Web\Repo-github\App\manga-studio\manga_studio.html"
s = open(p, encoding="utf-8").read()


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:80])
    s = s.replace(a, b)


for a, b in (("<title>Manga Studio v2.1.1</title>", "<title>Manga Studio v2.2.0</title>"),
             ('id="verBadge">v2.1.1<', 'id="verBadge">v2.2.0<'), ('const VERSION = "2.1.1";', 'const VERSION = "2.2.0";')):
    rep(a, b)

rep('''const LANGUE_LBL = { fr: "français", en: "anglais", es: "espagnol", de: "allemand", it: "italien", pt: "portugais", vi: "vietnamien" };''',
    '''const LANGUE_LBL = { fr: "français", en: "anglais", es: "espagnol", de: "allemand", it: "italien", pt: "portugais", vi: "vietnamien",
  ja: "japonais", zh: "chinois", ko: "coréen", ru: "russe", id: "indonésien", th: "thaï", ar: "arabe", pl: "polonais", tr: "turc" };
// v2.2.0 : la langue d'ORIGINE du chapitre ouvert (langue.json : API MangaDex, sinon lue sur 2 pages)
const LANGUE_CHAP = {};                                   // d -> {langue, methode, ...}
const METHODE_LBL = { mangadex: "donnée par MangaDex", pages: "lue sur les pages" };
async function langueChapitre(d){
  if (!d) return null;
  if (LANGUE_CHAP[d]) return LANGUE_CHAP[d];
  try { const r = await api("/manga/langue?d=" + encodeURIComponent(d)); if (r && r.langue) LANGUE_CHAP[d] = r; } catch (e){ log("langue : " + e.message, "w"); }
  return LANGUE_CHAP[d] || null;
}
function langueMaj(){
  const l = LANGUE_CHAP[CHAP_OPEN], o = $("tradVue").querySelector('option[value=""]');
  if (o) o.textContent = l ? "VO — " + (LANGUE_LBL[l.langue] || l.langue) : "VO (original)";
  $("tradVue").title = l ? "langue d'origine " + (METHODE_LBL[l.methode] || l.methode) : "";
  const meme = l && l.langue === $("tradLangue").value;
  $("tradMeme").hidden = !meme;
  if (meme) $("tradMeme").textContent = "⚠ déjà en " + (LANGUE_LBL[l.langue] || l.langue);
}''')
rep('''  $("tradVue").value = finies.some(t => t.langue === TRAD_VUE) ? TRAD_VUE : "";''',
    '''  $("tradVue").value = finies.some(t => t.langue === TRAD_VUE) ? TRAD_VUE : "";
  langueMaj();
  if (!LANGUE_CHAP[CHAP_OPEN]){ const d = CHAP_OPEN; langueChapitre(d).then(() => { if (d === CHAP_OPEN){ langueMaj(); if (RESUME && RESUME.chapitres[d] && LANGUE_CHAP[d]) { RESUME.chapitres[d].langue = LANGUE_CHAP[d].langue; } } }); }''')
rep('''  const lg = $("tradLangue").value, n = CHAP_PAGES;
  if (!confirm(''',
    '''  const lg = $("tradLangue").value, n = CHAP_PAGES, l = LANGUE_CHAP[CHAP_OPEN];
  let force = false;
  if (l && l.langue === lg){                                   // v2.2.0 : « francais -> francais »
    if (!confirm("Ce chapitre est DÉJÀ en " + (LANGUE_LBL[lg] || lg) + " (" + (METHODE_LBL[l.methode] || l.methode)
                 + ").\\n\\nLe traduire quand même vers la même langue ?")) return;
    force = true;
  }
  if (!confirm(''')
rep('''    const r = await api("/manga/traduire", { d: CHAP_OPEN, langue: lg });''',
    '''    const r = await api("/manga/traduire", { d: CHAP_OPEN, langue: lg, force });''')
# un petit avertissement a cote du choix de langue ; mise a jour quand on change de langue
i = s.index('<select id="tradLangue">')
j = s.index("</select>", i) + len("</select>")
s = s[:j] + '<span id="tradMeme" class="trad-meme" hidden></span>' + s[j:]
rep('''.trad-ligne span{font-size:12px;color:var(--dim)}''',
    '''.trad-ligne span{font-size:12px;color:var(--dim)}
.trad-ligne .trad-meme{color:#e6b450;font-weight:600}''')
rep('''$("tradVue").onchange = () => {''',
    '''$("tradLangue").addEventListener("change", langueMaj);
$("tradVue").onchange = () => {''')
# la langue sur la carte du chapitre
rep('''  const m = [];
  if (r.narr) m.push("🎙 " + r.narr + (r.voix.length ? " · " + r.voix.join(", ") : ""));''',
    '''  const m = [];
  if (r.langue) m.push("VO " + (LANGUE_LBL[r.langue] || r.langue));
  if (r.narr) m.push("🎙 " + r.narr + (r.voix.length ? " · " + r.voix.join(", ") : ""));''')
rep('''  return m.length ? '<small class="possede" title="narrations avec voix · karaoké calé · « Précédemment… » · traductions">' + esc(m.join(" · ")) + "</small>"
                  : '<small class="possede vide">pas encore narré</small>';''',
    '''  if (!r.narr) m.push("pas encore narré");
  return '<small class="possede' + (r.narr ? "" : " vide") + '" title="langue d\\'origine · narrations avec voix · karaoké calé · « Précédemment… » · traductions">'
    + esc(m.join(" · ")) + "</small>";''')
rep('''  try { RESUME = await api("/manga/resume"); renderLib(); } catch (e){ log("résumé : " + e.message, "w"); }
}''', '''  try { RESUME = await api("/manga/resume"); renderLib(); } catch (e){ log("résumé : " + e.message, "w"); return; }
  // v2.2.0 : un chapitre fraichement capture recoit sa langue tout seul (un par un ; MangaDex gratuit, sinon ~0,003 $)
  const inconnus = Object.entries(RESUME.chapitres).filter(([, r]) => !r.langue).map(([d]) => d);
  for (const d of inconnus){
    const l = await langueChapitre(d);
    if (l && RESUME.chapitres[d]){ RESUME.chapitres[d].langue = l.langue; renderLib(); }
  }
}''')
shutil.copy(p, p + ".bak-20260922-v220")
open(p, "w", encoding="utf-8").write(s)
print("app v2.2.0 OK")
