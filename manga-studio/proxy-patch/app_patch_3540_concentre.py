"""app 3.5.3 -> 3.5.4 (S5, feuille de route du 27/09 soir ; constat : 26 repliques sur 30 donnees au meme personnage) : controle
GRATUIT apres la preparation. Sur la plage choisie, si l'IA (repliques NON corrigees par Quang, lues, hors narrateur / inconnu, 6 au
moins) a mis >= 80 % sur UN personnage alors que la serie en compte plusieurs -> bandeau « ⚠ N repliques sur T donnees a X » avec
« 🔍 vérifier qui parle » (ouvre la verification des bulles : pinceau v3.5.0) et « c’est normal » (plus rien pour cette plage,
memorise sur l'appareil). Copie, node --check, remplacement."""
import os, re, shutil, subprocess, sys

F = "D:/Download/02-Apps-Web/Repo-github/App/manga-studio/manga_studio.html"
TMP = os.path.join(os.environ.get("TEMP", "."), "manga_studio_354.html")
s = open(F, encoding="utf-8", newline="").read()
if 'const VERSION = "3.5.4"' in s:
    print("deja applique"); sys.exit(0)


def rep(a, b):
    global s
    for nl in ("\r\n", "\n", "\r\r\n"):
        a2, b2 = a.replace("\n", nl), b.replace("\n", nl)
        if s.count(a2) == 1:
            s = s.replace(a2, b2); return
    raise SystemExit("ancre introuvable : " + a[:80])


rep("<title>Manga Studio v3.5.3</title>", "<title>Manga Studio v3.5.4</title>")
rep('id="verBadge">v3.5.3</span>', 'id="verBadge">v3.5.4</span>')
rep('const VERSION = "3.5.3";', 'const VERSION = "3.5.4";   // v3.5.4 : alerte gratuite « presque tout au meme personnage » apres la preparation (S5) ')

rep('''/* ---- l'ecran de preparation : distribution du MANGA + repliques du chapitre ---- */''',
    '''/* ---- v3.5.4 (S5) : « presque tout au meme personnage » -- controle GRATUIT apres la preparation ---- */
function dplConcentre(k){
  const e = DLG.e || {}, doc = e.doc, persos = ((e.distribution || {}).persos || []).length;
  if (!doc || !k || k === "lot" || persos < 2) return null;
  let vus = []; try { vus = JSON.parse(localStorage.getItem("manga_dlg_normal") || "[]"); } catch (err) {}
  if (vus.includes(CHAP_OPEN + "|" + k)) return null;
  const [a, b] = dplBornes(k);
  const rs = (doc.repliques || []).filter(x => x.page >= a && x.page <= b && x.lire && x.qui && x.qui !== "narrateur" && x.qui !== "inconnu" && !(x.corrige || {}).qui);
  if (rs.length < 6) return null;
  const n = {}; rs.forEach(x => { n[x.qui] = (n[x.qui] || 0) + 1; });
  const [qui, c] = Object.entries(n).sort((u, w) => w[1] - u[1])[0];
  return c / rs.length >= 0.8 ? { qui, n: c, t: rs.length } : null;
}
{ const _dr5 = dplRendre; dplRendre = function(){
    _dr5.apply(this, arguments);
    const cle = dplCle(), el = $("dlgEtat"), occupe = !!((DLG.e && DLG.e.en_cours) || (DLG.lot && DLG.lot.en_cours));
    if (!el || occupe || DPL.nouv || !dplListe().includes(cle) || el.querySelector(".dpl-s5")) return;
    const r = dplConcentre(cle); if (!r) return;
    el.insertAdjacentHTML("beforeend", '<div class="dpl-s5" style="margin-top:6px;padding:7px 9px;border:1px solid #6b5520;background:#2a2310;color:#f3dca0;border-radius:8px;font-size:12.5px">'
      + "⚠ " + r.n + " répliques sur " + r.t + " données à « " + esc(r.qui) + " » par l’IA"
      + '<div style="display:flex;gap:12px;margin-top:4px;flex-wrap:wrap"><button class="dpl-lien" data-s5="voir">🔍 vérifier qui parle ›</button>'
      + '<button class="dpl-lien" data-s5="ok" style="color:var(--dim)">c’est normal</button></div></div>');
  }; }
document.addEventListener("click", e => {
  const b = e.target.closest("[data-s5]"); if (!b) return;
  if (b.dataset.s5 === "voir"){ const bb = $("dplBulles"); if (bb) bb.click(); return; }
  let vus = []; try { vus = JSON.parse(localStorage.getItem("manga_dlg_normal") || "[]"); } catch (err) {}
  vus.push(CHAP_OPEN + "|" + dplCle()); try { localStorage.setItem("manga_dlg_normal", JSON.stringify(vus.slice(-300))); } catch (err) {}
  const d = b.closest(".dpl-s5"); if (d) d.remove(); toast("d’accord : plus d’alerte pour cette plage");
});

/* ---- l'ecran de preparation : distribution du MANGA + repliques du chapitre ---- */''')

open(TMP, "w", encoding="utf-8", newline="").write(s)
js = "\n".join(re.findall(r"<script>(.*?)</script>", s, re.S))
open(TMP + ".js", "w", encoding="utf-8").write(js)
r = subprocess.run(["node", "--check", TMP + ".js"], capture_output=True, text=True)
if r.returncode:
    print("node --check KO", r.stderr[:800]); sys.exit(1)
if "--essai" in sys.argv:
    print("essai OK (rien remplace) :", TMP); sys.exit(0)
shutil.copy2(F, F + ".bak-v3530")
shutil.copy2(TMP, F)
print("ok v3.5.4")
