# -*- coding: utf-8 -*-
"""Manga Studio v2.66.0 -> v2.67.0 : « Jusqu'au dernier paru » + chapitres deja presents (ROADMAP § 4-quindecies, E3 + E5 ;
maquette_dernier_paru_v1 validee par Quang le 25/09/2026 23h49). Fichier en CRLF : ancres converties.
Rejouable : python app_patch_267_dernier_paru.py <manga_studio.html>
"""
import sys

P = sys.argv[1]
s = open(P, "rb").read().decode("utf-8")
assert "\r\n" in s        # quelques lignes sont en LF seul : on ne normalise PAS le fichier, on convertit les ancres
if "v2.67.0 : dernier paru" in s:
    print("deja patche"); sys.exit(0)


def rep(a, b, n=1):
    global s
    a, b = a.replace("\n", "\r\n"), b.replace("\n", "\r\n")
    if s.count(a) != n:
        raise SystemExit("ancre %d fois (attendu %d) : %r" % (s.count(a), n, a[:80]))
    s = s.replace(a, b)


# --- version (3 endroits)
rep("<title>Manga Studio v2.66.0</title>", "<title>Manga Studio v2.67.0</title>")
rep('<span class="ver" id="verBadge">v2.66.0</span>', '<span class="ver" id="verBadge">v2.67.0</span>')
rep('const VERSION = "2.66.0";', 'const VERSION = "2.67.0";')

# --- CSS : bandeau vert « a jour »
rep(".cap-alerte.info{border-color:#2f5d8a;background:#12202e;color:#cfe6ff}",
    ".cap-alerte.info{border-color:#2f5d8a;background:#12202e;color:#cfe6ff}"
    ".cap-alerte.ok{border-color:#2f7a4f;background:#132619;color:#d6ffe6}   /* v2.67.0 : dernier paru -> a jour */")

# --- HTML : 4e puce + option du selecteur cache ; « + N » jusqu'a 300
rep('''        <button class="cap-chip" data-serie="suite">+ N suivants</button>''',
    '''        <button class="cap-chip" data-serie="suite">+ N suivants</button>
        <button class="cap-chip" data-serie="dernier" title="tous les chapitres suivants, jusqu'au dernier paru sur ce site (s'arrête seul)">Jusqu'au dernier paru</button>''')
rep('''          <option value="seul">ce chapitre seul</option></select>''',
    '''          <option value="seul">ce chapitre seul</option>
          <option value="dernier">jusqu'au dernier paru</option></select>''')
rep('''<input id="capSuite" type="number" min="1" max="50" step="1"''', '''<input id="capSuite" type="number" min="1" max="300" step="1"''')

# --- resume
rep('''               : m === "suite" ? " puis les " + (+$("capSuite").value || 1) + " suivant(s)" : " — ce chapitre seul";''',
    '''               : m === "suite" ? " puis les " + (+$("capSuite").value || 1) + " suivant(s)"
               : m === "dernier" ? " puis tous les suivants, jusqu'au dernier paru" : " — ce chapitre seul";   // v2.67.0 : dernier paru''')

# --- lancement
rep('''  const suite = modeSerie === "suite" ? Math.max(0, Math.min(50, Math.floor(+$("capSuite").value || 0))) : 0;
  const jusqua = modeSerie === "jusqua" ? $("capJusqua").value.trim().replace(",", ".") : "";
  if (jusqua && (!/^\\d{1,5}(\\.\\d{1,2})?$/.test(jusqua) || +jusqua <= +chap)){
    alert("« jusqu'au ch. » doit être un numéro plus grand que " + chap + "."); return;
  }
  const serieTxt = (jusqua ? "\\npuis les suivants jusqu'au chapitre " + jusqua
    : (suite ? "\\npuis les " + suite + " chapitre(s) suivant(s)" : ""))
    + ((jusqua || suite) && $("capEntiers").checked ? " (sans les chapitres intermédiaires)" : "");
  let force = false;
  if (deja){''',
    '''  // v2.67.0 : 300 partout (Quang 25/09 23h51) -- « + N » <= 300, « jusqu'au ch. » a 300 chapitres d'ecart au plus
  const suite = modeSerie === "suite" ? Math.max(0, Math.min(300, Math.floor(+$("capSuite").value || 0))) : 0;
  const jusqua = modeSerie === "jusqua" ? $("capJusqua").value.trim().replace(",", ".") : "";
  const dernier = modeSerie === "dernier";                                      // v2.67.0 : dernier paru
  if (jusqua && (!/^\\d{1,5}(\\.\\d{1,2})?$/.test(jusqua) || +jusqua <= +chap)){
    alert("« jusqu'au ch. » doit être un numéro plus grand que " + chap + "."); return;
  }
  if (jusqua && +jusqua - +chap > 300){
    alert("« jusqu'au ch. » : 300 chapitres d'écart au plus par capture (ici " + (+jusqua - +chap) + ").\\nCapture en deux fois, ou choisis « Jusqu'au dernier paru »."); return;
  }
  const serieTxt = (jusqua ? "\\npuis les suivants jusqu'au chapitre " + jusqua
    : (suite ? "\\npuis les " + suite + " chapitre(s) suivant(s)" : (dernier ? "\\npuis tous les suivants, jusqu'au dernier paru" : "")))
    + ((jusqua || suite || dernier) && $("capEntiers").checked ? " (sans les chapitres intermédiaires)" : "");
  let force = false;
  if (deja && (jusqua || suite || dernier)){
    // v2.67.0 (Quang 23h43 : « sans recommencer le travail ») : en SERIE, un 1er chapitre deja la se GARDE par defaut ;
    // avant, « non » a « le remplacer ? » annulait toute la serie. Les suivants deja la sont sautes par manga-fetch.
    const r = await demander({ titre: "Le ch. " + chap + " existe déjà (" + deja.pages + " pages)",
      texte: "Tu demandes aussi les suivants" + (jusqua ? " jusqu'au ch. " + jusqua : dernier ? ", jusqu'au dernier paru" : "")
        + ". Les chapitres déjà là sont gardés tels quels, jamais recapturés.",
      oui: "⏭ Le garder et continuer", autre: "♻ Le refaire", non: "Annuler" });
    if (!r) return;
    force = r === "autre";
  } else if (deja){''')
rep('''                                      suite: jusqua ? 0 : suite, jusqua, entiers: $("capEntiers").checked });
    $("btnCapturer").disabled = true;
    $("capEtat").textContent = "capture lancée…";''',
    '''                                      suite: jusqua ? 0 : suite, jusqua, entiers: $("capEntiers").checked,
                                      dernier_paru: dernier });
    $("btnCapturer").disabled = true;
    $("capEtat").textContent = "capture lancée…";''')

# --- suivi en direct
rep('''  const enSerie = +s.suite > 0 || !!s.jusqua, faits = (s.dossiers || []).length;
  if (s.etat === "en cours"){
    const cible = s.jusqua ? " (jusqu'au ch. " + s.jusqua + ")" : (+s.suite > 0 ? " (" + (faits + 1) + " sur " + (+s.suite + 1) + ")" : "");''',
    '''  const enSerie = +s.suite > 0 || !!s.jusqua || !!s.dernier_paru, faits = (s.dossiers || []).length;
  if (s.etat === "en cours"){
    const cible = s.jusqua ? " (jusqu'au ch. " + s.jusqua + ")" : (+s.suite > 0 ? " (" + (faits + 1) + " sur " + (+s.suite + 1) + ")"
                : s.dernier_paru ? " (jusqu'au dernier paru)" : "");''')
rep('''    const tenu = /: fait$/.test(arret) || (!!s.jusqua && /dépasse la borne/.test(arret));
    $("capEtat").textContent = (tenu ? "✅ " : /arrêtée à ta demande/.test(arret) ? "⏹ " : "🟠 ") + nb + " chapitre(s) de « " + s.titre + " » : ch. " + liste
      + " (" + fmtS(s.duree_s) + ")" + (arret && !/: fait$/.test(arret) ? " — arrêt : " + arret : "");''',
    '''    const tenu = /: fait$/.test(arret) || (!!s.jusqua && /dépasse la borne/.test(arret))
      || (!!s.dernier_paru && /aucun chapitre après/.test(arret));                                  // v2.67.0
    const dl = ((s.sortie || []).map(l => /^DEJA LA : (.+)$/.exec(l)).find(Boolean) || [])[1];      // v2.67.0 : deja la
    const compte = dl ? capCompte({ faits: liste.split(",").map(x => x.trim()), deja_la: dl.split(",").map(x => x.trim()) })
                      : nb + " chapitre(s)";
    $("capEtat").textContent = (tenu ? "✅ " : /arrêtée à ta demande/.test(arret) ? "⏹ " : "🟠 ") + compte + " de « " + s.titre + " »"
      + (dl ? "" : " : ch. " + liste) + " (" + fmtS(s.duree_s) + ")"
      + (s.dernier_paru && tenu ? " — à jour" : (arret && !/: fait$/.test(arret) ? " — arrêt : " + arret : ""));''')

# --- bilan persistant (bandeau)
rep('''  CAP_ALERTE = j && j.fin && j.tenu === false && String(j.fin) !== vu && !enCours ? j : null;''',
    '''  // v2.67.0 : « jusqu'au dernier paru » TENU -> bandeau vert « a jour » (maquette ③) ; les autres modes tenus : rien, comme avant
  CAP_ALERTE = j && j.fin && (j.tenu === false || (j.dernier_paru && j.tenu)) && String(j.fin) !== vu && !enCours ? j : null;''')
rep('''  $("capAlerte").classList.toggle("info", finSite || demande);
  if (!a) return;''',
    '''  const aJour = !!a && !!a.dernier_paru && !!a.tenu;                                               // v2.67.0 : dernier paru
  $("capAlerte").classList.toggle("info", (finSite || demande) && !aJour);
  $("capAlerte").classList.toggle("ok", aJour);
  if (!a) return;''')
rep('''    $("capAlerteTxt").innerHTML = fin
      ? "✅ Capture de <b>" + esc(a.titre) + "</b> : " + (a.faits || []).length + " chapitre(s) — <b>série terminée</b> : le ch. "
        + esc(dernier) + " est le dernier (marqué « " + esc(fin) + " »). Tout a été capturé."
      : "ℹ️ Capture de <b>" + esc(a.titre) + "</b> : " + (a.faits || []).length + " chapitre(s) — le site s'arrête au ch. "''',
    '''    $("capAlerteTxt").innerHTML = fin
      ? "✅ Capture de <b>" + esc(a.titre) + "</b> : " + esc(capCompte(a)) + " — <b>série terminée</b> : le ch. "
        + esc(dernier) + " est le dernier (marqué « " + esc(fin) + " »). Tout a été capturé."
      : aJour ? "✅ Capture de <b>" + esc(a.titre) + "</b> : " + esc(capCompte(a)) + " — <b>à jour</b> : le ch. " + esc(dernier)
        + " est le dernier paru sur ce site."
      : "ℹ️ Capture de <b>" + esc(a.titre) + "</b> : " + esc(capCompte(a)) + " — le site s'arrête au ch. "''')
rep('''  const but = a.jusqua ? " (objectif : ch. " + a.jusqua + ")" : (a.suite ? " sur " + (+a.suite + 1) + " demandés" : "");''',
    '''  const but = a.jusqua ? " (objectif : ch. " + a.jusqua + ")" : (a.suite ? " sur " + (+a.suite + 1) + " demandés"
            : a.dernier_paru ? " (jusqu'au dernier paru)" : "");''')
rep('''function capAlerteVue(){''',
    '''/* v2.67.0 (Quang 23h43) : « 6 capturés (1, 6 à 10), 4 déjà là (2 à 5, gardés tels quels) » -- avant, les chapitres SAUTES
   (deja presents) etaient comptes comme captures. Les suites de numeros se resument en « a a b ». */
function capPlages(l){
  const n = l.map(Number), out = []; let i = 0;
  while (i < l.length){ let j = i; while (j + 1 < l.length && n[j + 1] === n[j] + 1) j++;
    out.push(j - i >= 2 ? l[i] + " à " + l[j] : l.slice(i, j + 1).join(", ")); i = j + 1; }
  return out.join(", ");
}
function capCompte(a){
  const d = a.deja_la || [], f = (a.faits || []).filter(x => !d.includes(x));
  if (!d.length) return f.length + " chapitre(s)";
  return f.length + " capturé(s)" + (f.length ? " (" + capPlages(f) + ")" : "") + ", " + d.length + " déjà là (" + capPlages(d) + ", gardés tels quels)";
}
function capAlerteVue(){''')

# --- reprise
rep('''    const but = r.jusqua ? "jusqu'au chapitre " + r.jusqua : (r.suite ? "puis les " + r.suite + " chapitre(s) suivant(s)" : "ce chapitre seul");''',
    '''    const but = r.jusqua ? "jusqu'au chapitre " + r.jusqua : (r.suite ? "puis les " + r.suite + " chapitre(s) suivant(s)"
              : r.dernier_paru ? "puis jusqu'au dernier paru" : "ce chapitre seul");''')
rep('''                                                   suite: r.jusqua ? 0 : (r.suite || 0), jusqua: r.jusqua || "", entiers: !!r.entiers });''',
    '''                                                   suite: r.jusqua ? 0 : (r.suite || 0), jusqua: r.jusqua || "", entiers: !!r.entiers,
                                                   dernier_paru: !!r.dernier_paru });''')

# --- activite
rep('''const actProg = it => { const p = it.type === "capture" && it.total && it.pages != null ? "p. " + it.pages : "";''',
    '''const actProg = it => {
  if (it.type === "capture" && it.dernier_paru)                                                     // v2.67.0 : total inconnu
    return [it.pages != null ? "p. " + it.pages : "", (it.fait || 0) + " ch. fait(s)", "jusqu'au dernier paru"].filter(Boolean).join(" · ");
  const p = it.type === "capture" && it.total && it.pages != null ? "p. " + it.pages : "";''')
rep('''  const serie = !!x.total;
  return '<div class="act-arret">\'''',
    '''  const serie = !!x.total || !!x.dernier_paru;                                                     // v2.67.0 : dernier paru
  return '<div class="act-arret">\'''')

open(P, "wb").write(s.encode("utf-8"))
print("patche")
