# -*- coding: utf-8 -*-
"""App v2.0.1 -> v2.1.0 : ce que chaque serie et chaque chapitre POSSEDE, visible dans la bibliotheque (Quang 22/09 10h58).
Carte de chapitre : « 🎙 2 · Charon, Fenrir · 🎤 · 📜 · 🌐 FR » (le badge 🎬 ✅/🟠 existant reste) ; rien -> « pas encore narré ».
Carte de serie : « 🎙 2/3 narrés · 🎬 1 · 🎵 3 · 🌙 Gemini ». Source : GET /manga/resume (une lecture du disque),
rechargee a l'ouverture de la bibliotheque et a la fin de chaque tache. Verifie ses ancres, sinon n'ecrit rien.
"""
import shutil
p = r"D:\Download\02-Apps-Web\Repo-github\App\manga-studio\manga_studio.html"
s = open(p, encoding="utf-8").read()


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:80])
    s = s.replace(a, b)


for a, b in (("<title>Manga Studio v2.0.1</title>", "<title>Manga Studio v2.1.0</title>"),
             ('id="verBadge">v2.0.1<', 'id="verBadge">v2.1.0<'),
             ('const VERSION = "2.0.1";', 'const VERSION = "2.1.0";')):
    rep(a, b)

rep('''.chap-item small{display:block;opacity:.75;line-height:1.35;margin-top:2px}''',
    '''.chap-item small{display:block;opacity:.75;line-height:1.35;margin-top:2px}
.chap-item small.possede{opacity:1;color:var(--txt)}.chap-item small.possede.vide{opacity:.55}''')

rep('''function renderLib(){''',
    '''// v2.1.0 : ce que chaque serie / chapitre possede deja (narrations, voix, karaoke, video, musique, traduction, suivi)
let RESUME = null;
async function chargerResume(){
  try { RESUME = await api("/manga/resume"); renderLib(); } catch (e){ log("résumé : " + e.message, "w"); }
}
function possedeChap(d){
  const r = RESUME && RESUME.chapitres[d]; if (!r) return "";
  const m = [];
  if (r.narr) m.push("🎙 " + r.narr + (r.voix.length ? " · " + r.voix.join(", ") : ""));
  if (r.karaoke) m.push("🎤");
  if (r.prec) m.push("📜");
  if (r.trad.length) m.push("🌐 " + r.trad.map(x => x.toUpperCase()).join(" "));
  return m.length ? '<small class="possede" title="narrations avec voix · karaoké calé · « Précédemment… » · traductions">' + esc(m.join(" · ")) + "</small>"
                  : '<small class="possede vide">pas encore narré</small>';
}
function possedeSerie(s){
  if (!RESUME) return "";
  const cs = s.chaps.map(i => RESUME.chapitres[CHAPS[i].dir]).filter(Boolean), se = RESUME.series[s.slug] || {};
  const m = ["🎙 " + cs.filter(x => x.narr).length + "/" + s.chaps.length + " narré" + (cs.filter(x => x.narr).length > 1 ? "s" : "")];
  const v = cs.filter(x => x.video).length; if (v) m.push("🎬 " + v);
  if (se.musique) m.push("🎵 " + se.musique);
  if (se.suivi) m.push("🌙 " + (se.moteur === "gemini" ? "Gemini" : "Kimi"));
  return '<small class="possede" title="chapitres narrés · vidéos · morceaux de musique · suivi de nuit">' + esc(m.join(" · ")) + "</small>";
}
function renderLib(){''')
rep('''      + '<small>' + s.chaps.length + ' chapitre' + (s.chaps.length > 1 ? "s" : "") + ' · ' + s.pages + ' pages</small>\'''',
    '''      + '<small>' + s.chaps.length + ' chapitre' + (s.chaps.length > 1 ? "s" : "") + ' · ' + s.pages + ' pages</small>'
      + possedeSerie(s)''')
rep('''    + '<small>' + c.pages + ' pages · ' + (c.bytes / 1e6).toFixed(1) + ' Mo</small>\'''',
    '''    + possedeChap(c.dir)
    + '<small>' + c.pages + ' pages · ' + (c.bytes / 1e6).toFixed(1) + ' Mo</small>\'''')
rep('''    const fini = ACT.items.some(x => !cles.has(actCle(x)));''',
    '''    const fini = ACT.items.some(x => !cles.has(actCle(x)));
    if (fini) chargerResume();                            // v2.1.0 : une narration / video finie apparait sur sa carte''')
rep('''  CHAPS_ROOT = j.root || "sources/";
  renderLib();
}''', '''  CHAPS_ROOT = j.root || "sources/";
  renderLib();
  chargerResume();                                        // v2.1.0
}''')
shutil.copy(p, p + ".bak-20260922-v210")
open(p, "w", encoding="utf-8").write(s)
print("app v2.1.0 OK")
