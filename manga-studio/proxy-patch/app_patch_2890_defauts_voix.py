# -*- coding: utf-8 -*-
"""v2.89.0 (27/09, R18 phase 1 -- Quang 13h13 : « voix d'homme […] 1 trop lent, voire 1,10 […] j'aimerais un bouton pour
indiquer que c'est la valeur par defaut que je souhaite desormais […] tu separes ces valeurs entre la principale et la
secondaire ») : dans l'ecran ✏, un bouton « ⭐ » a droite de « Vitesse de diction » et de « 🎧 Vitesse d'écoute » :
- enregistre la valeur comme DEFAUT des personnages du meme genre (homme / femme / narrateur) de CETTE application
  (reglages.py 1.4.0 : _reglages.json de l'instance) -- les nouveaux personnages la recoivent (dialogues.py 1.16.0) ;
- propose ensuite de l'appliquer aux autres personnages de ce genre DANS CE MANGA (confirmation : la diction = voix a refaire,
  credits ; l'ecoute = gratuit) ;
- « ⭐ » plein quand la valeur affichee EST le defaut. Genre inconnu : pas de bouton (jamais devine).
Suppose v2.88.0 + patch_reglages_defauts cote serveur. Rejouable."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v2.89.0" in s[:400]:
    print("deja applique"); sys.exit(0)
if "v2.88.0" not in s[:400]:
    print("ERREUR : appliquer d'abord app_patch_2880_voix_fr.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


rep("<title>Manga Studio v2.88.0</title>", "<title>Manga Studio v2.89.0</title>")
rep('<span class="ver" id="verBadge">v2.88.0</span>', '<span class="ver" id="verBadge">v2.89.0</span>')
rep('const VERSION = "2.88.0";', 'const VERSION = "2.89.0";   // v2.89.0 : ⭐ vitesses par defaut des voix, par genre et par application (R18)')
rep(""".dlgp-carte select{width:100%;min-width:0}""", """.dlgp-carte select{width:100%;min-width:0}
.dlgp-def{flex:none;width:34px;height:30px;padding:0;justify-content:center;opacity:.55}.dlgp-def.on{opacity:1;color:#ffd24a;border-color:#8a6d1e}   /* v2.89.0 */""")
rep("""<input type="range" data-k="vitesse" min="0.7" max="1.2" step="0.05" value="' + (p.vitesse || 1.1) + '" style="width:100%">'""",
    """<div class="dlgp-ligne"><input type="range" data-k="vitesse" min="0.7" max="1.2" step="0.05" value="' + (p.vitesse || 1.1) + '" style="flex:1">' + dlgDefBtn(p, "vitesse") + "</div>\"""")
rep("""<input type="range" data-k="ecoute" min="0.7" max="1.5" step="0.05" value="' + (p.ecoute || 1) + '" style="width:100%">'""",
    """<div class="dlgp-ligne"><input type="range" data-k="ecoute" min="0.7" max="1.5" step="0.05" value="' + (p.ecoute || 1) + '" style="flex:1">' + dlgDefBtn(p, "ecoute") + "</div>\"""")
rep("""function dlgEcoute(nom){""", """// v2.89.0 (R18) : les valeurs par defaut des voix, par genre -- celles de CETTE application (reglages de l'instance)
const DLG_DEF_LIB = { h: "hommes", f: "femmes", n: "narrateur" };
function dlgGenreCle(p){
  if (p.narrateur) return "n";
  const g = (p.genre || "").toLowerCase();
  if (g === "homme" || g === "male") return "h";
  if (g === "femme" || g === "female") return "f";
  const v = (DLG.voix || []).find(x => x.id === p.voix_el);                   // genre inconnu : celui de sa voix, sinon rien
  return v && v.genre === "male" ? "h" : v && v.genre === "female" ? "f" : "";
}
function dlgDefBtn(p, k){
  const g = dlgGenreCle(p); if (!g) return "";
  const d = (DLG.defauts || {})["voix_" + g + "_" + k], val = +(p[k] || (k === "ecoute" ? 1 : 1.1));
  const on = d != null && Math.abs(d - val) < 0.001;
  return '<button class="btn sm dlgp-def' + (on ? " on" : "") + '" data-defaut="' + k + '" title="' + (on ? "c'est la valeur par défaut des " : "en faire la valeur par défaut des ")
    + DLG_DEF_LIB[g] + (d != null && !on ? " (aujourd'hui " + String(d).replace(".", ",") + ")" : "") + '">' + (on ? "★" : "☆") + "</button>";
}
dlgPrep.addEventListener("click", async e => {
  const t = e.target.closest("[data-defaut]"); if (!t) return;
  const carte = t.closest(".dlgp-carte"), p = dlgPersos()[+carte.dataset.p], k = t.dataset.defaut, g = dlgGenreCle(p);
  if (!p || !g) return;
  const val = +carte.querySelector('input[data-k="' + k + '"]').value, lib = DLG_DEF_LIB[g], app = ESPACE.nom === "prive" ? "secondaire" : "principale";
  try {
    const r = await api("/manga/reglages", { defauts: { ["voix_" + g + "_" + k]: val } });
    if (r.error) throw new Error(r.error);
    if (!r.defauts) throw new Error("serveur à relancer (réglage inconnu)");
    DLG.defauts = r.defauts;
  } catch (err) { return toast("par défaut non enregistré : " + err.message); }
  toast("★ " + (k === "vitesse" ? "diction" : "écoute") + " " + String(val).replace(".", ",") + " : par défaut pour les " + lib + " (application " + app + ")");
  const autres = dlgPersos().filter(q => q !== p && dlgGenreCle(q) === g && Math.abs(+(q[k] || (k === "ecoute" ? 1 : 1.1)) - val) > 0.001);
  if (g !== "n" && autres.length && confirm("Appliquer aussi " + String(val).replace(".", ",") + " aux " + autres.length + " autres " + lib + " de ce manga ?\\n\\n"
      + autres.map(q => "· " + q.nom).join("\\n") + "\\n\\n" + (k === "vitesse" ? "⚠ Vitesse de diction : leurs voix déjà faites seront à refaire (crédits)." : "Gratuit : aucune voix n'est refaite.")))
    await dlgRegler({ persos: autres.map(q => ({ nom: q.nom, [k]: val })) });
  else dlgPrepRendre();
});
function dlgEcoute(nom){""")
rep("""  dlgPrep.hidden = false; document.body.style.overflow = "hidden";
  dlgPrepRendre();""", """  try { DLG.defauts = (await api("/manga/reglages")).defauts || {}; } catch (e) { DLG.defauts = {}; }   // v2.89.0 (R18)
  dlgPrep.hidden = false; document.body.style.overflow = "hidden";
  dlgPrepRendre();""")
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
