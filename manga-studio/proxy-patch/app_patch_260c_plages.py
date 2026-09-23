# -*- coding: utf-8 -*-
"""Manga Studio v2.6.0 (23/09/2026) : sur la carte d'une serie, les chapitres en PLAGES (« ch. 295 → 311 »).
Quang (13h26) : la liste « 295, 296, 297… » rallongeait les cartes (grille non homogene) pour une info deja donnee
(« 17 chapitres »). Les trous restent visibles (« 1 → 5, 8, 10 → 12 »), une seule ligne, coupee proprement.
Rejouable : python app_patch_260c_plages.py <manga_studio.html>.
"""
import sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "function plagesChap" in s:
    print("deja patche"); sys.exit(0)


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


rep(""".serie-item small.serie-genres{color:var(--dim)}""",
    """.serie-item small.serie-genres{color:var(--dim)}
.serie-item small.ch-plages,.serie-item small.serie-genres{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.serie-item>span{min-width:0}""")
rep("""      + '<small>ch. ' + s.chaps.map(i => esc(CHAPS[i].chapter)).join(", ") + '</small>'""",
    """      + '<small class="ch-plages" title="chapitres : ' + esc(s.chaps.map(i => CHAPS[i].chapter).join(", ")) + '">ch. ' + esc(plagesChap(s.chaps.map(i => CHAPS[i].chapter))) + '</small>'""")
rep("""const dateAjout = s =>""",
    """// v2.6.0 : « 295, 296, …, 311 » -> « 295 → 311 » ; les trous restent visibles ; un numero non entier (300.5) reste a part
function plagesChap(nums){
  const v = [...new Set(nums.map(String))].sort((a, b) => (parseFloat(a) - parseFloat(b)) || a.localeCompare(b));
  const out = []; let d = null, f = null;
  const pousse = () => { if (d !== null) out.push(d === f ? d : (parseFloat(f) - parseFloat(d) === 1 ? d + ", " + f : d + " → " + f)); };
  v.forEach(x => {
    const n = parseFloat(x), entier = /^\d+$/.test(x);
    if (entier && f !== null && /^\d+$/.test(f) && n === parseFloat(f) + 1){ f = x; return; }
    pousse(); d = x; f = x;
  });
  pousse();
  return out.join(", ");
}
const dateAjout = s =>""")
rep("""'<small class="serie-genres">' + esc(s.info.genres.map(g => GENRE_FR[g] || g).join(" · ")) + "</small>\"""",
    """'<small class="serie-genres" title="' + esc(s.info.genres.map(g => GENRE_FR[g] || g).join(" · ")) + '">' + esc(s.info.genres.map(g => GENRE_FR[g] || g).join(" · ")) + "</small>\"""")
open(p, "w", encoding="utf-8").write(s)
print("patche")
