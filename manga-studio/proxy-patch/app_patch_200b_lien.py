# -*- coding: utf-8 -*-
"""App v2.0.0 (suite) : CAPTURER A PARTIR D'UN LIEN (idee Quang 22/09 10h38).
« J'ouvre la page dans le navigateur de mon telephone, je recupere le lien, je le mets dans l'application, il s'ouvre dans
la fenetre Edge et la capture demarre. » -> champ « 🔗 Lien du chapitre » + cible du menu PARTAGER (manifest share_target) :
le lien s'ouvre dans un nouvel onglet de la fenetre de capture (ouverte au besoin), l'onglet est choisi pour la capture,
titre et numero proposes d'apres la page. Quang verifie et touche « Capturer » (pas de capture sans son accord : un
mauvais onglet a deja ete capture le 21/09 a 18h47). Verifie ses ancres, sinon n'ecrit rien.
"""
p = r"D:\Download\02-Apps-Web\Repo-github\App\manga-studio\manga_studio.html"
s = open(p, encoding="utf-8").read()


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:80])
    s = s.replace(a, b)


rep('''    <div class="row" style="margin-top:8px">
      <div class="grow"><label>Onglet à capturer</label><select id="capTab"></select></div>
    </div>''',
    '''    <!-- v2.0.0 : a partir d'un LIEN (colle, ou « Partager -> Manga Studio » depuis le navigateur du telephone) -->
    <div class="row" style="margin-top:8px">
      <div class="grow"><label>🔗 Lien du chapitre <span class="muted">(ou, dans le navigateur du téléphone : Partager → Manga Studio)</span></label>
        <input id="capLien" inputmode="url" placeholder="colle ici le lien de la page où commencer"></div>
      <button class="btn" id="btnCapLien" style="align-self:flex-end">Ouvrir sur le PC</button>
    </div>
    <p class="muted" id="capLienEtat" style="margin:4px 0 0;font-size:12px"></p>
    <div class="row" style="margin-top:8px">
      <div class="grow"><label>Onglet à capturer</label><select id="capTab"></select></div>
    </div>''')

JS = r'''
/* ----- v2.0.0 : capturer a partir d'un LIEN (colle ou partage) ----- */
const lienDe = t => { const m = /(https?:\/\/[^\s"'<>]+)/.exec(t || ""); return m ? m[1] : ""; };
function devinerTitre(titrePage){
  // « One Punch-Man - Chapter 301 - MangaDex » -> titre connu de la bibliotheque si on le retrouve, et le numero
  const t = titrePage || "", num = (/(?:chap(?:ter|itre)?|ch\.?|#)\s*(\d+(?:[.,]\d+)?)/i.exec(t) || [])[1] || "";
  const connus = [...new Set(CHAPS.map(c => c.title))].sort((a, b) => b.length - a.length);
  const connu = connus.find(x => slugTitre(t).includes(slugTitre(x)));
  const brut = t.split(/\s[-|–—]\s|\bchap(?:ter|itre)?\b|\bch\.?\s*\d/i)[0].trim();
  return { titre: connu || brut, num: num.replace(",", ".") };
}
async function capOuvrirLien(texte){
  const u = lienDe(texte) || (/^[\w-]+(\.[\w-]+)+\//.test((texte || "").trim()) ? "https://" + texte.trim() : "");
  if (!u){ $("capLienEtat").textContent = "⚠ pas de lien reconnu"; return; }
  $("capLien").value = u;
  const et = m => { $("capLienEtat").textContent = m; };
  let o = await api("/manga/pilote_onglets");
  if (!o.edge){
    et("ouverture de la fenêtre de capture sur le PC…"); await api("/manga/fetch_edge", {});
    for (let k = 0; k < 20 && !o.edge; k++){ await new Promise(r => setTimeout(r, 1000)); o = await api("/manga/pilote_onglets"); }
    if (!o.edge){ et("⚠ la fenêtre de capture ne s'ouvre pas"); return; }
  }
  if (o.capture){ et("⚠ une capture est déjà en cours"); return; }
  et("ouverture du lien dans la fenêtre de capture…");
  const r = await api("/manga/pilote", { action: "nouvel", url: u }); if (r.error) throw new Error(r.error);
  let tab = null;
  for (let k = 0; k < 20; k++){                          // la page charge (et peut rediriger) : on attend son titre
    await new Promise(res => setTimeout(res, 1000));
    tab = ((await api("/manga/pilote_onglets")).onglets || []).find(x => x.id === r.id);
    if (tab && tab.titre && !/^https?:/.test(tab.titre) && tab.url.startsWith("http")) break;
  }
  if (!tab){ et("⚠ l'onglet s'est fermé"); return; }
  await refreshCapTabs();
  const i = CAP_TABS.findIndex(t => t.url === tab.url);
  if (i >= 0){ $("capTab").value = String(i); $("capTab").dispatchEvent(new Event("change")); }
  const g = devinerTitre(tab.titre);
  if (!$("capTitre").value.trim() && g.titre) $("capTitre").value = g.titre;
  if (!$("capChap").value.trim() && g.num) $("capChap").value = g.num;
  PIL.id = r.id;
  et("✅ ouvert sur le PC et choisi : « " + tab.titre.slice(0, 70) + " » — vérifie le titre et le n°, puis Capturer"
     + " (🕹 Piloter la fenêtre pour te placer autrement)");
  $("capTitre").scrollIntoView({ behavior: "smooth", block: "center" });
}
$("btnCapLien").onclick = () => capOuvrirLien($("capLien").value).catch(e => { $("capLienEtat").textContent = "⚠ " + e.message; });
$("capLien").addEventListener("keydown", e => { if (e.key === "Enter"){ e.preventDefault(); $("btnCapLien").click(); } });
// « Partager -> Manga Studio » (manifest share_target) : /manga/?lien=…&texte=…&titre=…
function partageEntrant(){
  const q = new URLSearchParams(location.search), t = [q.get("lien"), q.get("texte"), q.get("titre")].filter(Boolean).join(" ");
  if (!t) return;
  history.replaceState(null, "", location.pathname);
  const b = document.querySelector('nav button[data-tab="tChap"]'); if (b) b.click();
  $("capBox").open = true;
  log("partage reçu : " + t.slice(0, 120));
  setTimeout(() => capOuvrirLien(t).catch(e => { $("capLienEtat").textContent = "⚠ " + e.message; }), 800);
}
'''
rep('''/* ----- v2.0.0 : TELECOMMANDE de la fenetre de capture ----- */''', JS + '''/* ----- v2.0.0 : TELECOMMANDE de la fenetre de capture ----- */''')
rep('''\nboot();\n''', '''\nboot().then(partageEntrant, partageEntrant);          // v2.0.0 : un lien partage depuis le telephone\n''')
open(p, "w", encoding="utf-8").write(s)
print("app lien OK")
