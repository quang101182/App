# -*- coding: utf-8 -*-
"""App v1.95.1 -> v1.96.0 : chapitre PRECEDENT / SUIVANT en un geste (etape 16, Quang 22/09 09h19).
Fiche du chapitre : ⏮ / ⏭ a cote du titre (ouvre le voisin de la meme serie, ordre des numeros).
Lecteur : ⏮ ch. / ch. ⏭ en haut -> enchaine la narration du voisin (la plus recente avec voix) sans sortir ;
fin de chapitre : « ▶ Chapitre suivant ». Voisin sans narration avec voix = grise, raison au survol.
Verifie ses ancres, sinon n'ecrit rien.
"""
import shutil
p = r"D:\Download\02-Apps-Web\Repo-github\App\manga-studio\manga_studio.html"
s = open(p, encoding="utf-8").read()


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:80])
    s = s.replace(a, b)


for a, b in (("<title>Manga Studio v1.95.1</title>", "<title>Manga Studio v1.96.0</title>"),
             ('id="verBadge">v1.95.1<', 'id="verBadge">v1.96.0<'),
             ('const VERSION = "1.95.1";', 'const VERSION = "1.96.0";')):
    rep(a, b)

rep('''      <h3 class="grow" id="chapTitle" style="margin:0"></h3>''',
    '''      <button class="btn sm ch-nav" id="chapPrev" hidden></button>
      <h3 class="grow" id="chapTitle" style="margin:0"></h3>
      <button class="btn sm ch-nav" id="chapNext" hidden></button>''')
rep('''    <button class="btn sm" id="lecFermer">✕ Fermer</button></div>''',
    '''    <button class="btn sm ch-nav" id="lecChPrev" title="chapitre précédent">⏮ ch.</button>
    <button class="btn sm ch-nav" id="lecChNext" title="chapitre suivant">ch. ⏭</button>
    <button class="btn sm" id="lecFermer">✕ Fermer</button></div>''')
rep('''.lec-top{display:flex;gap:10px;align-items:center;padding:8px 12px}''',
    '''.lec-top{display:flex;gap:10px;align-items:center;padding:8px 12px}
.ch-nav{white-space:nowrap;flex:none}.ch-nav:disabled{opacity:.35}
.lec-fin-suiv{margin-top:10px}''')
rep('''  $("chapTitle").textContent = c.title + " — chapitre " + c.chapter;''',
    '''  $("chapTitle").textContent = c.title + " — chapitre " + c.chapter;
  chapNavMaj();''')

rep('''/* ----- v1.94.0 : « Precedemment... » + rattrapage ----- */''',
    '''/* ----- v1.96.0 : chapitre precedent / suivant (meme serie, ordre des numeros) ----- */
const chapNum = c => { const x = parseFloat(c.chapter); return isNaN(x) ? Infinity : x; };
function chapVoisin(dir, delta){
  const l = CHAPS.map((c, i) => ({ c, i })).filter(x => serieDe(x.c.dir) === serieDe(dir))
    .sort((a, b) => chapNum(a.c) - chapNum(b.c) || String(a.c.chapter).localeCompare(String(b.c.chapter)));
  const k = l.findIndex(x => x.c.dir === dir);
  return k < 0 || k + delta < 0 || k + delta >= l.length ? -1 : l[k + delta].i;
}
async function narrAvecVoix(dir){
  const j = await api("/manga/narrations?d=" + encodeURIComponent(dir));
  return (j.items || []).filter(n => n.etat === "fini" && n.audio)
    .sort((a, b) => (b.created_at || "").localeCompare(a.created_at || ""))[0] || null;
}
function chapNavMaj(){
  [["chapPrev", -1, "⏮ "], ["chapNext", 1, " ⏭"]].forEach(([id, d, f]) => {
    const i = chapVoisin(CHAP_OPEN, d), b = $(id);
    b.hidden = i < 0; if (i < 0) return;
    b.textContent = d < 0 ? f + "ch. " + CHAPS[i].chapter : "ch. " + CHAPS[i].chapter + f;
    b.title = (d < 0 ? "chapitre précédent : " : "chapitre suivant : ") + CHAPS[i].chapter;
    b.onclick = () => openChap(i).catch(e => log("chapitre : " + e.message, "e"));
  });
}
// Lecteur : l'etat des deux boutons (un voisin sans narration avec voix ne peut pas etre lu)
async function lecNavMaj(){
  for (const [id, d] of [["lecChPrev", -1], ["lecChNext", 1]]){
    const i = chapVoisin(CHAP_OPEN, d), b = $(id);
    b.hidden = LEC.aveugle || i < 0; b.disabled = true;
    if (b.hidden) continue;
    b.title = "ch. " + CHAPS[i].chapter + " …";
    try {
      const n = await narrAvecVoix(CHAPS[i].dir);
      b.disabled = !n;
      b.title = (d < 0 ? "chapitre précédent" : "chapitre suivant") + " : ch. " + CHAPS[i].chapter
        + (n ? " (" + (n.voice || n.tag) + ")" : " — pas encore de narration avec voix");
    } catch { b.title = "ch. " + CHAPS[i].chapter + " — narrations illisibles"; }
  }
}
async function lecChapitre(delta){
  const i = chapVoisin(CHAP_OPEN, delta); if (i < 0) return;
  const n = await narrAvecVoix(CHAPS[i].dir);
  if (!n){ toast("ch. " + CHAPS[i].chapter + " : pas encore de narration avec voix"); return; }
  $("lecAudio").pause(); clearTimeout(LEC.timer);
  await openChap(i);
  await Promise.all([refreshPrec().catch(() => {}), refreshMus().catch(() => {})]);
  log("lecteur : chapitre " + (delta < 0 ? "précédent" : "suivant") + " → " + CHAPS[i].dir + " (" + n.tag + ")");
  await ouvrirLecteur([n.tag]);
}
$("lecChPrev").onclick = () => lecChapitre(-1).catch(e => log("lecteur : " + e.message, "e"));
$("lecChNext").onclick = () => lecChapitre(1).catch(e => log("lecteur : " + e.message, "e"));

/* ----- v1.94.0 : « Precedemment... » + rattrapage ----- */''')

rep('''  $("lecPrecBox").hidden = !!aveugle || !(PREC && PREC.modes.ouverture && PREC.modes.ouverture.etat === "fini");''',
    '''  $("lecPrecBox").hidden = !!aveugle || !(PREC && PREC.modes.ouverture && PREC.modes.ouverture.etat === "fini");
  lecNavMaj().catch(() => {});''')
rep('''  $("lecSous").textContent = "— Fin du chapitre —"; LEC.playing = false; $("lecPlay").textContent = "▶";''',
    '''  $("lecSous").textContent = "— Fin du chapitre —"; LEC.playing = false; $("lecPlay").textContent = "▶";
  if (!$("lecChNext").hidden && !$("lecChNext").disabled){                // v1.96.0 : enchainer
    const b = document.createElement("button"); b.className = "btn pri lec-fin-suiv";
    b.textContent = "▶ Chapitre suivant (" + $("lecChNext").title.replace(/^chapitre suivant : /, "") + ")";
    b.onclick = () => lecChapitre(1).catch(e => log("lecteur : " + e.message, "e"));
    $("lecSous").appendChild(document.createElement("br")); $("lecSous").appendChild(b);
  }''')
shutil.copy(p, p + ".bak-20260922-v196")
open(p, "w", encoding="utf-8").write(s)
print("app v1.96.0 OK")
