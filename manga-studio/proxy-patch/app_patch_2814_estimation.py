# -*- coding: utf-8 -*-
"""v2.81.4 (27/09, Quang 01:29) : l'estimation de la PREPARATION suit la portee choisie.
Avant : 0,005 $ x TOUTES les pages du chapitre, meme pour « des pages 121 a 123 » (846 p. -> « 4,23 $ » au lieu de ~0,012 $).
Apres : pages demandees seulement, tarif mesure au D8 (0,0038 $/page -> 0,004), recalcule a la frappe ; plusieurs chapitres :
pas de chiffre invente (depend des chapitres traduits). Rejouable."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v2.81.4" in s[:400]:
    print("deja applique"); sys.exit(0)
N = "\r\n" if "\r\n" in s else "\n"
def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:60], s.count(a)); s = s.replace(a, b)
rep("""  const prep = pastille("≈ " + fmtUsd(0.005 * (CHAP_PAGES || 1)) + " préparation");""",
"""  const prep = DLG.portee === "lot" ? "" : pastille("≈ " + fmtUsd(0.004 * dlgNbPages()) + " préparation");""")
rep("""function dlgRendre(){""", """function dlgNbPages(){                    // v2.81.4 : les pages DEMANDEES, pas tout le chapitre
  const tot = CHAP_PAGES || 1;
  if (DLG.portee !== "pages") return tot;
  const de = Math.max(1, parseInt($("dlgDe").value) || 1), a = Math.min(tot, parseInt($("dlgA").value) || de);
  return Math.max(1, a - de + 1);
}
["dlgDe", "dlgA"].forEach(id => $(id).addEventListener("input", () => dlgRendre()));
function dlgRendre(){""")
s = s.replace("<title>Manga Studio v2.81.3</title>", "<title>Manga Studio v2.81.4</title>", 1)
s = s.replace('id="verBadge">v2.81.3<', 'id="verBadge">v2.81.4<', 1)
s = s.replace('const VERSION = "2.81.3";', 'const VERSION = "2.81.4";   // v2.81.4 : estimation de preparation = pages demandees', 1)
assert s.count("2.81.4") >= 4
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
