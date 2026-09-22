# -*- coding: utf-8 -*-
"""App v2.1.0 -> v2.1.1 : « Capturer un chapitre » en 4 ETAPES dans l'ordre (Quang 22/09 11h01 : « pas clair, la chronologie,
le lien smartphone, a quel moment je mets le nom du manga et le numero de chapitre » -- « car les champs sont apres »).
1. Ouvre la page (UN choix : 📱 lien du telephone | 🕹 piloter la fenetre | 🖥 sur le PC ; seule la facon choisie s'affiche)
2. L'onglet a capturer (choisi tout seul) · 3. Nom et n° (proposes d'apres la page : a verifier) · 4. Capturer.
Tous les identifiants existants sont gardes (aucun code de capture ne change). Verifie ses ancres, sinon n'ecrit rien.
"""
import shutil
p = r"D:\Download\02-Apps-Web\Repo-github\App\manga-studio\manga_studio.html"
s = open(p, encoding="utf-8").read()


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:80])
    s = s.replace(a, b)


L = s.split("\n")
i0 = next(i for i, l in enumerate(L) if '<summary><h3 style="display:inline">📥 Capturer un chapitre</h3></summary>' in l) + 1
i1 = next(i for i, l in enumerate(L) if 'id="capPage1"' in l) + 1
assert L[i1].strip() == "</div>", L[i1]
bloc = "\n".join(L[i0:i1 + 1])
pil = bloc[bloc.index("    <!-- v2.0.0 : TELECOMMANDE"):bloc.index("    <!-- v2.0.0 : a partir d")].rstrip("\n")
assert 'id="pilBox" hidden' in pil
NEUF = '''    <!-- v2.1.1 : 4 ETAPES dans l'ordre. Les trois facons d'ouvrir la page = UN choix ; seule la choisie s'affiche. -->
    <div class="cap-etape"><div class="cap-num">1</div><div class="cap-corps">
      <b>Ouvre la page où commencer la capture</b>
      <div class="seg cap-mode" id="capMode">
        <button data-mode="lien">📱 Lien du téléphone</button><button data-mode="pilote">🕹 Piloter la fenêtre</button><button data-mode="pc">🖥 Sur le PC</button></div>
      <div id="capModeLien" class="cap-mode-z">
        <p class="muted aide">Dans le navigateur de ton téléphone, sur la page du chapitre : <b>Partager → Manga Studio</b>. Ou colle le lien ici :</p>
        <div class="row"><input id="capLien" class="grow" inputmode="url" placeholder="lien de la page du chapitre">
          <button class="btn pri" id="btnCapLien">Ouvrir sur le PC</button></div>
      </div>
      <div id="capModePilote" class="cap-mode-z" hidden>
        <p class="muted aide">Tu vois la fenêtre de capture du PC : touche pour cliquer, glisse pour défiler, puis « ✔ Capturer cet onglet ».</p>
PILOTE
      </div>
      <div id="capModePc" class="cap-mode-z" hidden>
        <p class="muted aide">Sur le PC, ouvre le chapitre dans la <b>fenêtre de capture</b> (fenêtre Edge dédiée), puis « ↻ Onglets ».</p>
      </div>
      <div class="row cap-edge-l">
        <span id="capEdge" class="muted">fenêtre de capture : …</span>
        <button class="btn sm" id="btnCapEdge">Ouvrir la fenêtre de capture</button>
        <button class="btn sm" id="btnCapTabs">↻ Onglets</button>
        <button class="btn sm" id="btnPilote" hidden></button>
      </div>
      <p class="muted" id="capLienEtat" style="margin:4px 0 0;font-size:12px"></p>
    </div></div>
    <div class="cap-etape"><div class="cap-num">2</div><div class="cap-corps">
      <b>L'onglet à capturer</b> <span class="muted">— choisi tout seul à l'étape 1 ; change-le si besoin</span>
      <select id="capTab"></select>
    </div></div>
    <div class="cap-etape"><div class="cap-num">3</div><div class="cap-corps">
      <b>Nom du manga et n° du chapitre</b> <span class="muted">— proposés d'après la page à l'étape 1 : vérifie-les</span>
      <div class="row">
        <div class="grow"><input id="capTitre" list="capTitres" placeholder="nom du manga (ex. One Punch-Man)"></div>
        <div style="width:110px"><input id="capChap" inputmode="decimal" placeholder="n° (ex. 301)"></div>
      </div>
      <datalist id="capTitres"></datalist>
      <label class="lec-chk"><input type="checkbox" id="capPage1"> depuis la page 1 (si l'onglet est au milieu du chapitre)</label>
    </div></div>'''.replace("PILOTE", pil.replace('id="pilBox" hidden', 'id="pilBox"'))
L[i0:i1 + 1] = NEUF.split("\n")
s = "\n".join(L)

rep('''    <div class="row" style="margin-top:8px">
      <button class="btn pri" id="btnCapturer">📥 Capturer</button>
      <span class="muted" id="capEtat"></span>
    </div>''',
    '''    <div class="cap-etape"><div class="cap-num">4</div><div class="cap-corps">
      <div class="row"><button class="btn pri" id="btnCapturer">📥 Capturer</button><span class="muted" id="capEtat"></span></div>
    </div></div>''')
rep('''.pil-box{margin:8px 0;padding:8px;border:1px solid var(--line);border-radius:10px;background:var(--panel2)}''',
    '''.pil-box{margin:8px 0;padding:8px;border:1px solid var(--line);border-radius:10px;background:var(--panel2)}
.cap-etape{display:flex;gap:10px;margin:10px 0 0;padding-top:10px;border-top:1px solid var(--line)}
.cap-num{flex:none;width:24px;height:24px;border-radius:50%;background:var(--accent2);color:#fff;font-weight:700;display:grid;place-items:center;font-size:13px}
.cap-corps{flex:1;min-width:0;display:flex;flex-direction:column;gap:6px}.cap-corps .aide{margin:0}
.cap-mode{display:flex;flex-wrap:wrap}.cap-mode button{flex:1 1 auto}
.cap-edge-l{font-size:12px}''')
rep('''$("btnPilote").onclick = async () => {''',
    '''// v2.1.1 : UN choix de facon d'ouvrir la page (memorise ; defaut : le lien sur telephone, le PC sinon)
let CAP_MODE = null; try { CAP_MODE = localStorage.getItem("manga_cap_mode"); } catch {}
if (!["lien", "pilote", "pc"].includes(CAP_MODE)) CAP_MODE = innerWidth < 700 ? "lien" : "pc";
function capModeMaj(){
  document.querySelectorAll("#capMode [data-mode]").forEach(b => b.classList.toggle("on", b.dataset.mode === CAP_MODE));
  $("capModeLien").hidden = CAP_MODE !== "lien"; $("capModePilote").hidden = CAP_MODE !== "pilote"; $("capModePc").hidden = CAP_MODE !== "pc";
  const voir = CAP_MODE === "pilote" && $("capBox").open;
  $("pilBox").hidden = !voir;
  if (voir){ pilOnglets().then(pilEcran).then(pilBoucle).catch(pilErr); } else clearInterval(PIL.timer);
}
$("capMode").onclick = e => { const b = e.target.closest("[data-mode]"); if (!b) return;
  CAP_MODE = b.dataset.mode; try { localStorage.setItem("manga_cap_mode", CAP_MODE); } catch {} capModeMaj(); };
$("capBox").addEventListener("toggle", capModeMaj);
capModeMaj();
$("btnPilote").onclick = async () => {''')
rep('''  $("capBox").open = true;
  log("partage reçu : " + t.slice(0, 120));''',
    '''  $("capBox").open = true; CAP_MODE = "lien"; capModeMaj();
  log("partage reçu : " + t.slice(0, 120));''')
rep('''  et("✅ ouvert sur le PC et choisi : « " + tab.titre.slice(0, 70) + " » — vérifie le titre et le n°, puis Capturer"
     + " (🕹 Piloter la fenêtre pour te placer autrement)");''',
    '''  et("✅ ouvert sur le PC : « " + tab.titre.slice(0, 70) + " » — étapes 2 et 3 remplies : vérifie le nom et le n°, puis 4. Capturer"
     + " (🕹 Piloter la fenêtre pour te placer ailleurs)");''')
rep('''  toast("✔ onglet choisi pour la capture"); $("capTitre").scrollIntoView''',
    '''  toast("✔ onglet choisi (étape 2) — vérifie le nom et le n° (étape 3)"); $("capTitre").scrollIntoView''')
for a, b in (("<title>Manga Studio v2.1.0</title>", "<title>Manga Studio v2.1.1</title>"),
             ('id="verBadge">v2.1.0<', 'id="verBadge">v2.1.1<'), ('const VERSION = "2.1.0";', 'const VERSION = "2.1.1";')):
    rep(a, b)
shutil.copy(p, p + ".bak-20260922-v211")
open(p, "w", encoding="utf-8").write(s)
print("app v2.1.1 OK")
