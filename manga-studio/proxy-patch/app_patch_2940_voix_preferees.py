# -*- coding: utf-8 -*-
"""v2.94.0 (27/09, R24 -- Quang 14h19) : dans l'ecran ✏, la liste des voix devient LISIBLE et on peut garder ses PREFEREES.
- Separations VISIBLES : lignes « ──── ⭐ Mes voix préférées ──── », « ──── 🇫🇷 Voix françaises ──── », « ──── Autres voix (accent
  anglais) ──── » (options desactivees) -- les <optgroup> de la v2.88.0 ne se voyaient pas dans le selecteur d'Android.
- ☆ a droite du choix de voix = voix PREFEREE de CETTE application (reglages.py 1.6.0) : en tete de la liste pour tous les
  personnages et tous les mangas, et choisie d'abord par la distribution automatique (dialogues.py 1.17.0).
- Narrateur : l'ecoute d'essai envoyait son nom AFFICHE (« Narrateur ») au lieu de sa cle (« narrateur ») -> « rien a dire ».
  Corrige (ecoute + ses repliques proposees en tete).
Suppose v2.93.0 + patch_reglages_favorites cote serveur. Rejouable."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v2.94.0" in s[:600]:
    print("deja applique"); sys.exit(0)
if "v2.93.0" not in s[:600]:
    print("ERREUR : appliquer d'abord app_patch_2930_rester_secondaire.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


rep("<title>Manga Studio v2.93.0</title>", "<title>Manga Studio v2.94.0</title>")
rep('<span class="ver" id="verBadge">v2.93.0</span>', '<span class="ver" id="verBadge">v2.94.0</span>')
rep('const VERSION = "2.93.0";', 'const VERSION = "2.94.0";   // v2.94.0 : voix -- separations visibles, voix PREFEREES, ecoute du narrateur reparee (R24)')
rep(""".dlgp-def{flex:none;""", """.dlgp-fav{flex:none;width:34px;height:auto;min-height:30px;padding:0;justify-content:center;opacity:.55}.dlgp-fav.on{opacity:1;color:#ffd24a;border-color:#8a6d1e}   /* v2.94.0 */
.dlgp-def{flex:none;""")
rep("""  const optV = sel => (DLG.voix.some(v => v.fr)
      ? '<optgroup label="🇫🇷 Voix françaises">' + DLG.voix.filter(v => v.fr).map(v => opt1(v, sel)).join("") + "</optgroup>"
        + '<optgroup label="Autres voix (accent anglais)">' + DLG.voix.filter(v => !v.fr).map(v => opt1(v, sel)).join("") + "</optgroup>"
      : DLG.voix.map(v => opt1(v, sel)).join(""))""",
    """  const optV = sel => dlgOptVoix(sel, opt1)                                    // v2.94.0 (R24) : separations visibles + preferees""")
rep("""      + '<label>Voix</label><select data-k="voix_el">' + optV(p.voix_el) + "</select>\"""",
    """      + '<label>Voix</label><div class="dlgp-ligne"><select data-k="voix_el">' + optV(p.voix_el) + "</select>"
      + (p.voix_el ? '<button class="btn sm dlgp-fav' + ((DLG.fav || []).includes(p.voix_el) ? " on" : "") + '" data-fav="' + esc(p.voix_el) + '" title="'
         + ((DLG.fav || []).includes(p.voix_el) ? "voix préférée (toucher pour la retirer)" : "garder cette voix dans mes préférées (en tête, choisie d'abord)") + '">'
         + ((DLG.fav || []).includes(p.voix_el) ? "★" : "☆") + "</button>" : "") + "</div>\"""")
rep("""      + '<label>Phrase à écouter</label><div class="dlgp-ligne"><select data-k="phrase">' + phrases(p.nom) + '</select>""",
    """      + '<label>Phrase à écouter</label><div class="dlgp-ligne"><select data-k="phrase">' + phrases(p.narrateur ? "narrateur" : p.nom) + '</select>""")
rep("""  if (ep !== undefined){ const p = dlgPersos()[+ep]; corps.cle = t.closest(".dlgp-carte").querySelector('[data-k="phrase"]').value; corps.qui = p.nom; }""",
    """  if (ep !== undefined){ const p = dlgPersos()[+ep]; corps.cle = t.closest(".dlgp-carte").querySelector('[data-k="phrase"]').value; corps.qui = p.narrateur ? "narrateur" : p.nom; }   // v2.94.0 : la CLE du narrateur""")
rep("""  try { DLG.defauts = (await api("/manga/reglages")).defauts || {}; } catch (e) { DLG.defauts = {}; }   // v2.89.0 (R18)""",
    """  try { const rg = await api("/manga/reglages"); DLG.defauts = rg.defauts || {}; DLG.fav = rg.voix_favorites || []; }   // v2.89.0 (R18) ; v2.94.0 : preferees
  catch (e) { DLG.defauts = {}; DLG.fav = DLG.fav || []; }""")
rep("""function dlgGenreCle(p){""", """// v2.94.0 (R24) : la liste des voix -- separations VISIBLES (lignes desactivees : Android n'affiche pas les <optgroup>)
function dlgOptVoix(sel, opt1){
  const fav = DLG.fav || [], sep = t => '<option disabled>──── ' + t + " ────</option>";
  const fv = fav.map(i => DLG.voix.find(v => v.id === i)).filter(Boolean), reste = DLG.voix.filter(v => !fav.includes(v.id));
  const fr = reste.filter(v => v.fr), au = reste.filter(v => !v.fr);
  return (fv.length ? sep("⭐ Mes voix préférées") + fv.map(v => opt1(v, sel)).join("") : "")
    + (fr.length ? sep("🇫🇷 Voix françaises") + fr.map(v => opt1(v, sel)).join("") + sep("Autres voix (accent anglais)") : "")
    + au.map(v => opt1(v, sel)).join("");
}
dlgPrep.addEventListener("click", async e => {                    // v2.94.0 : ☆ = voix preferee de CETTE application
  const t = e.target.closest("[data-fav]"); if (!t) return;
  const id = t.dataset.fav, retirer = (DLG.fav || []).includes(id), v = (DLG.voix || []).find(x => x.id === id);
  try { const r = await api("/manga/reglages", { voix_favorites: retirer ? { retirer: id } : { ajouter: id } }); if (r.error) throw new Error(r.error);
        if (!Array.isArray(r.voix_favorites)) throw new Error("serveur à relancer (réglage inconnu)");
        DLG.fav = r.voix_favorites; dlgPrepRendre();
        toast((retirer ? "☆ retirée des préférées : " : "★ voix préférée : ") + (v ? v.nom : id) + (retirer ? "" : " — en tête de liste et choisie d'abord pour les nouveaux personnages")); }
  catch (err) { toast("préférée non enregistrée : " + err.message); }
});
function dlgGenreCle(p){""")
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
