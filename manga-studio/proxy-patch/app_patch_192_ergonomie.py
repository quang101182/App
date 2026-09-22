# -*- coding: utf-8 -*-
"""App v1.91.0 -> v1.92.0 : ergonomie de la bibliotheque et du chapitre (Quang, 22/09 05h15).

« Le bouton rafraichir : un gros texte avant et un gros texte apres, un gros rectangle [...] pour pas grand-chose.
Ca pourrait etre beaucoup plus fin et discret [...] l'icone poubelle se retrouve completement decalee d'un vocal a
un autre selon les textes [...] definir des zones fixes [...] un rendu propre, professionnel. »
- bibliotheque : la carte « Chapitres disponibles » devient une BARRE FINE (recherche + ↻ + une ligne discrete) ;
  capture repliee par defaut ; pochettes plus petites ;
- chapitre : avertissements de capture REPLIES (« ⚠ N avertissements »), actions sur UNE ligne ;
- narrations en ZONES FIXES : titre + infos a gauche, 4 emplacements fixes a droite (▶ 🎤 🎙 🗑) ;
  un bouton absent laisse sa place vide -> 🗑 toujours au meme endroit.
Identifiants et data-attributs inchanges (bancs existants). Verifie ses ancres, sinon n'ecrit rien.
"""
import shutil
p = r"D:\Download\02-Apps-Web\Repo-github\App\manga-studio\manga_studio.html"
shutil.copy(p, p + ".bak-20260922-v192")
s = open(p, encoding="utf-8").read()


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:80])
    s = s.replace(a, b)


for a, b in (("<title>Manga Studio v1.91.0</title>", "<title>Manga Studio v1.92.0</title>"),
             ('id="verBadge">v1.91.0<', 'id="verBadge">v1.92.0<'),
             ('const VERSION = "1.91.0";', 'const VERSION = "1.92.0";')):
    rep(a, b)

# ---------- bibliotheque : barre fine a la place de la carte ----------
rep('''  <details class="card cap-box" id="capBox" open>''', '''  <details class="card cap-box" id="capBox">''')
rep('''try { if (localStorage.getItem("manga_capture_ouvert") === "0") $("capBox").open = false; } catch {}''',
    '''try { if (localStorage.getItem("manga_capture_ouvert") === "1") $("capBox").open = true; } catch {}   // v1.92 : repliee par defaut''')
rep('''  <div class="card">
    <h3>Chapitres disponibles</h3>
    <p class="muted aide" style="margin:0 0 8px">
      Remplis par <code>manga-fetch</code> (capture dans la fenêtre Edge dédiée, MangaDex ou import)
      dans <code>manga-studio/sources/</code>. Touche un chapitre pour voir ses pages.
    </p>
    <div class="row"><button class="btn" id="btnChapRefresh">Rafraîchir</button>
      <span class="muted" id="chapState"></span></div>
  </div>
  <div class="lib-recherche" id="libRechBox"><input type="search" id="libRech" autocomplete="off"
    placeholder="🔎 Rechercher : titre, autre titre (ex. Frieren), n° de chapitre ou de tome…"></div>''',
    '''  <!-- v1.92.0 : une barre fine (recherche + ↻), l'etat en une ligne discrete ; l'explication vit dans les aides ℹ️ -->
  <div class="lib-barre">
    <div class="lib-recherche" id="libRechBox"><input type="search" id="libRech" autocomplete="off"
      placeholder="🔎 Titre, autre titre (ex. Frieren), n° de chapitre ou de tome…"></div>
    <button class="btn sm lib-maj" id="btnChapRefresh" title="relire la bibliothèque (sources/)">↻</button>
  </div>
  <p class="lib-etat muted" id="chapState"></p>
  <p class="muted aide" style="margin:-4px 0 10px;font-size:12px">Remplie par la capture ci-dessus (ou MangaDex / import) dans
    <code>sources/</code>. Touche une série, puis un chapitre.</p>''')
rep('''    $("chapState").textContent = (LIB_RECH ? trouvees.length + " / " : "") + series.length + " série(s), "
      + CHAPS.length + " chapitre(s) — " + CHAPS_ROOT;''',
    '''    $("chapState").textContent = (LIB_RECH ? trouvees.length + " / " : "") + series.length + " série(s) · "
      + CHAPS.length + " chapitre(s)";
    $("chapState").title = CHAPS_ROOT;                               // le chemin disque : au survol, pas en pleine page''')
rep('''.lib-recherche{margin:0 0 10px}.lib-recherche input{width:100%;box-sizing:border-box}''',
    '''.lib-barre{display:flex;gap:6px;align-items:center;margin:0 0 4px}
.lib-recherche{margin:0;flex:1 1 auto;min-width:0}.lib-recherche input{width:100%;box-sizing:border-box}
.lib-maj{flex:none;width:38px;height:38px;justify-content:center;font-size:16px;padding:0}
.lib-etat{margin:0 0 10px;font-size:12px;min-height:1.2em}''')
rep('''.serie-item img{width:92px;height:132px}''',
    '''.serie-item img{width:76px;height:108px}
@media (max-width:480px){.serie-item img{width:64px;height:92px}.chap-item{padding:6px;gap:8px}}''')

# ---------- chapitre : avertissements replies, actions sur une ligne ----------
rep('''    <ul class="chap-notes" id="chapNotes" hidden></ul>
    <div class="row" style="margin:0 0 8px"><button class="btn sm" id="btnChapVerif">🔎 Vérifier (intégrité + complétude)</button>
      <span class="muted" id="chapVerif"></span></div>
    <div class="row" style="margin:0 0 8px">
      <button class="btn sm" id="btnPagesSel">☑ Sélectionner des pages</button>''',
    '''    <details class="chap-notes-box" id="chapNotesBox" hidden><summary id="chapNotesSum"></summary>
      <ul class="chap-notes" id="chapNotes" hidden></ul></details>
    <div class="chap-actions">
      <button class="btn sm" id="btnChapVerif" title="vérifier l'intégrité et la complétude du chapitre">🔎 Vérifier</button>
      <button class="btn sm" id="btnPagesSel" title="choisir des pages (supprimer, pochette)">☑ Sélection</button>''')
rep('''      <button class="btn sm danger" id="btnChapDel">🗑 Supprimer le chapitre</button>
    </div>''',
    '''      <button class="btn sm danger" id="btnChapDel" title="supprimer le chapitre (corbeille)">🗑 Chapitre</button>
    </div>
    <p class="muted" id="chapVerif" style="margin:0 0 8px;font-size:12px"></p>''')
rep('''  $("chapNotes").innerHTML = (j.notes || []).map(n => "<li>⚠ " + esc(n) + "</li>").join("");
  $("chapNotes").hidden = !(j.notes || []).length;''',
    '''  $("chapNotes").innerHTML = (j.notes || []).map(n => '<li title="' + esc(n) + '">' + esc(n) + "</li>").join("");
  $("chapNotes").hidden = !(j.notes || []).length;
  $("chapNotesBox").hidden = !(j.notes || []).length;                 // v1.92 : repliees, un clic pour les lire
  $("chapNotesSum").textContent = "⚠ " + (j.notes || []).length + " avertissement(s) de capture";''')
rep('''.chap-notes{margin:0 0 8px;padding-left:18px;color:#e6b450;font-size:13px}''',
    '''.chap-notes{margin:4px 0 0;padding-left:18px;color:#e6b450;font-size:12px}
.chap-notes li{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.chap-notes-box{margin:0 0 8px}.chap-notes-box summary{cursor:pointer;color:#e6b450;font-size:12px}
.chap-actions{display:flex;gap:6px;flex-wrap:wrap;margin:0 0 6px}''')

# ---------- narrations : zones fixes ----------
rep('''.narr-run{display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:6px 8px;border:1px solid var(--line);border-radius:6px;background:var(--panel)}
.narr-run b{min-width:150px}.narr-run .grow{flex:1;min-width:160px}''',
    '''/* v1.92.0 : ZONES FIXES. A gauche le titre et UNE ligne d'infos ; a droite 4 emplacements de 34 px toujours
   dans le meme ordre (▶ 🎤 🎙 🗑) : un bouton absent laisse sa case vide, la poubelle ne bouge jamais. */
.narr-run{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:2px 10px;align-items:center;
  padding:7px 8px;border:1px solid var(--line);border-radius:7px;background:var(--panel)}
.narr-run .nr-tag{font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.narr-run .nr-info{grid-column:1;font-size:12px;color:var(--dim);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.narr-run .nr-titre{grid-column:1;font-size:12px;color:var(--dim);font-style:italic;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.narr-run .nr-act{grid-column:2;grid-row:1 / span 3;display:grid;grid-template-columns:repeat(4,34px);gap:4px}
.narr-run .nr-act .btn.sm{width:34px;height:30px;padding:0;justify-content:center}
.narr-run .nr-act i{display:block}
.narr-run .narr-pbar{grid-column:1}''')
rep('''    let info;
    if (n.etat === "fini") info = n.pages + " pages · " + (st.cout_total != null ? st.cout_total.toFixed(3) + " $ · " : "")
      + "généré en " + fmtS(st.total_s || 0) + (n.titre ? " · « " + esc(n.titre) + " »" : "")
      + (n.karaoke_en_cours ? " · ⏳ karaoké en calage…" : st.karaoke ? " · 🎤 karaoké calé" : "");
    else if (n.etat === "en cours") info = etape + " — " + (pr.fait || 0) + "/" + (pr.total || "?")
      + '<div class="narr-pbar"><div style="width:' + pct + '%"></div></div>';
    else if (n.etat === "echec") info = "échec — " + esc((n.err || "").split("\\n").filter(Boolean).slice(-1)[0] || "voir run.log");
    else info = esc(n.etat);
    return '<div class="narr-run"><b>' + (lbl[n.etat] || "") + " " + esc(n.tag) + "</b>"
      + '<span class="grow muted">' + info + "</span>"
      + (n.etat === "fini" && n.audio ? '<button class="btn sm" data-ecoute="' + i + '">▶ Écouter</button>' : "")
      + (n.etat === "fini" && n.audio && !st.karaoke && !n.karaoke_en_cours
         ? '<button class="btn sm" data-kar="' + i + '" title="cale chaque mot sur la voix (Whisper, ~0,003 $ pour 20 pages) : le mot prononcé s\\'allume dans le lecteur">🎤 Karaoké</button>' : "")
      + (n.etat === "fini" && ["kimi", "gemini", "pixtral"].includes(n.engine)
         ? '<button class="btn sm" data-revoix="' + i + '" title="même texte, lu par la voix choisie dans le menu Voix">🎙 Autre voix</button>' : "")
      + (n.etat !== "en cours" ? '<button class="btn sm danger" data-suppr-narr="' + i + '" title="supprimer cette narration">🗑</button>' : "")
      + "</div>";''',
    '''    let info, titre = "", barre = "";
    if (n.etat === "fini"){
      info = n.pages + " p. · " + (st.cout_total != null ? fmtUsd(st.cout_total) + " · " : "") + fmtS(st.total_s || 0)
        + (n.karaoke_en_cours ? " · ⏳ karaoké en calage…" : st.karaoke ? " · 🎤 karaoké calé" : "");
      titre = n.titre ? "« " + esc(n.titre) + " »" : "";
    } else if (n.etat === "en cours"){
      info = etape + " — " + (pr.fait || 0) + "/" + (pr.total || "?");
      barre = '<div class="narr-pbar"><div style="width:' + pct + '%"></div></div>';
    } else if (n.etat === "echec") info = "échec — " + esc((n.err || "").split("\\n").filter(Boolean).slice(-1)[0] || "voir run.log");
    else info = esc(n.etat);
    const vide = "<i></i>", fini = n.etat === "fini";
    return '<div class="narr-run"><span class="nr-tag" title="' + esc(n.tag) + '">' + (lbl[n.etat] || "") + " " + esc(n.tag) + "</span>"
      + '<div class="nr-act">'
      + (fini && n.audio ? '<button class="btn sm" data-ecoute="' + i + '" title="écouter">▶</button>' : vide)
      + (fini && n.audio && !st.karaoke && !n.karaoke_en_cours
         ? '<button class="btn sm" data-kar="' + i + '" title="caler le karaoké : chaque mot sur la voix (Whisper, ~0,003 $ pour 20 pages)">🎤</button>' : vide)
      + (fini && ["kimi", "gemini", "pixtral"].includes(n.engine)
         ? '<button class="btn sm" data-revoix="' + i + '" title="autre voix : même texte, lu par la voix choisie dans le menu Voix">🎙</button>' : vide)
      + (n.etat !== "en cours" ? '<button class="btn sm danger" data-suppr-narr="' + i + '" title="supprimer cette narration">🗑</button>' : vide)
      + "</div>"
      + '<span class="nr-info" title="' + esc(info.replace(/<[^>]+>/g, "")) + '">' + info + "</span>"
      + (titre ? '<span class="nr-titre" title="' + titre + '">' + titre + "</span>" : "") + barre
      + "</div>";''')

open(p, "w", encoding="utf-8").write(s)
print("patch app v1.92.0 OK")


# ---------- 2e passe (vue sur capture 360 px) : infos de narration en pleine largeur, traduction compacte ----------
s = open(p, encoding="utf-8").read()
rep('''.narr-run .nr-info{grid-column:1;font-size:12px;''', '''.narr-run .nr-info{grid-column:1 / -1;font-size:12px;''')
rep('''.narr-run .nr-titre{grid-column:1;font-size:12px;''', '''.narr-run .nr-titre{grid-column:1 / -1;font-size:12px;''')
rep('''.narr-run .nr-act{grid-column:2;grid-row:1 / span 3;display:grid;''', '''.narr-run .nr-act{grid-column:2;grid-row:1;display:grid;''')
rep('''.narr-run .narr-pbar{grid-column:1}''', '''.narr-run .narr-pbar{grid-column:1 / -1}
/* traduction : etiquettes EN LIGNE, deux petites rangees au lieu d'une colonne de blocs */
.trad-ligne{display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.trad-ligne+.trad-ligne{margin-top:6px}
.trad-ligne span{font-size:12px;color:var(--dim)}
.trad-ligne select{width:auto;min-width:0;padding:5px 8px}''')
rep('''      <div class="row" style="align-items:flex-end">
        <div style="width:150px"><label>🌐 Traduire en</label><select id="tradLangue">
          <option value="fr">français</option><option value="en">anglais</option><option value="es">espagnol</option>
          <option value="de">allemand</option><option value="it">italien</option><option value="pt">portugais</option>
          <option value="vi">vietnamien</option></select></div>
        <button class="btn" id="btnTraduire" title="efface le texte des bulles et y pose la traduction (onomatopées laissées telles quelles)">Traduire les dialogues</button>
        <div style="width:150px"><label>Afficher les pages</label><select id="tradVue"><option value="">VO (original)</option></select></div>
      </div>''',
    '''      <div class="trad-ligne"><span>🌐 Traduire les dialogues en</span><select id="tradLangue">
          <option value="fr">français</option><option value="en">anglais</option><option value="es">espagnol</option>
          <option value="de">allemand</option><option value="it">italien</option><option value="pt">portugais</option>
          <option value="vi">vietnamien</option></select>
        <button class="btn sm" id="btnTraduire" title="efface le texte des bulles et y pose la traduction (onomatopées laissées telles quelles)">Traduire</button></div>
      <div class="trad-ligne"><span>Pages affichées</span><select id="tradVue"><option value="">VO (original)</option></select></div>''')
open(p, "w", encoding="utf-8").write(s)
print("2e passe OK")


# ---------- 3e passe (banc test_ergonomie_ui a 360 px) : boutons du chapitre sur une ligne, noms entiers ----------
s = open(p, encoding="utf-8").read()
rep('''.chap-actions{display:flex;gap:6px;flex-wrap:wrap;margin:0 0 6px}''',
    '''.chap-actions{display:flex;gap:6px;flex-wrap:wrap;margin:0 0 6px}
@media (max-width:480px){
  .chap-actions{gap:4px}.chap-actions .btn.sm{padding:5px 7px;font-size:12px}
  /* telephone : le NOM prend toute la ligne du haut, les 4 cases fixes passent a droite de la ligne d'infos
     (toujours la meme colonne -> 🗑 reste aligne) */
  .narr-run{grid-template-areas:"tag tag" "info act" "titre titre" "barre barre"}
  .narr-run .nr-tag{grid-area:tag}.narr-run .nr-act{grid-area:act;grid-row:auto;grid-column:auto}
  .narr-run .nr-info{grid-area:info}.narr-run .nr-titre{grid-area:titre}.narr-run .narr-pbar{grid-area:barre}
}''')
open(p, "w", encoding="utf-8").write(s)
print("3e passe OK")


# ---------- 4e passe (vu sur capture 360 px, que le banc n'avait pas vu) : la regle telephone etait ECRASEE ----------
# par la regle generale placee plus bas (meme specificite) -> le nom passait SOUS les boutons. On monte la specificite.
s = open(p, encoding="utf-8").read()
rep('''  .narr-run{grid-template-areas:"tag tag" "info act" "titre titre" "barre barre"}
  .narr-run .nr-tag{grid-area:tag}.narr-run .nr-act{grid-area:act;grid-row:auto;grid-column:auto}
  .narr-run .nr-info{grid-area:info}.narr-run .nr-titre{grid-area:titre}.narr-run .narr-pbar{grid-area:barre}''',
    '''  .narr-runs .narr-run{grid-template-areas:"tag tag" "info act" "titre titre" "barre barre"}
  .narr-runs .narr-run .nr-tag{grid-area:tag}.narr-runs .narr-run .nr-act{grid-area:act}
  .narr-runs .narr-run .nr-info{grid-area:info}.narr-runs .narr-run .nr-titre{grid-area:titre}
  .narr-runs .narr-run .narr-pbar{grid-area:barre}''')
open(p, "w", encoding="utf-8").write(s)
print("4e passe OK")
