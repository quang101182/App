# -*- coding: utf-8 -*-
"""v2.88.0 (27/09, R19 -- Quang 13h14 : « les voix privilegiees doivent etre 100 % francaises, les autres restent
optionnelles ») : dans l'ecran ✏, la liste des voix est groupee « 🇫🇷 Voix françaises » (bibliotheque ElevenLabs, en tete)
puis « Autres voix (accent anglais) ». Une voix anglophone deja attribuee a un personnage est signalee (« 🇬🇧 accent anglais :
une voix française est proposée en tête de liste ») -- jamais changee en silence (la changer = repayer ses repliques).
Serveur : patch_dialogues_10 (« fr » sur chaque voix). Serveur d'avant (sans « fr ») : liste d'avant. Suppose v2.87.0. Rejouable."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v2.88.0" in s[:400]:
    print("deja applique"); sys.exit(0)
if "v2.87.0" not in s[:400]:
    print("ERREUR : appliquer d'abord app_patch_2870_ecoute.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


rep("<title>Manga Studio v2.87.0</title>", "<title>Manga Studio v2.88.0</title>")
rep('<span class="ver" id="verBadge">v2.87.0</span>', '<span class="ver" id="verBadge">v2.88.0</span>')
rep('const VERSION = "2.87.0";', 'const VERSION = "2.88.0";   // v2.88.0 : voix francaises en tete (bibliotheque ElevenLabs), accent anglais signale (R19)')
rep("""  const optV = sel => DLG.voix.map(v => '<option value="' + esc(v.id) + '"' + (v.id === sel ? " selected" : "") + ">" + esc(v.nom + " — " + v.desc + " (" + dlgGenre(v.genre) + ")") + "</option>").join("")""",
    """  const opt1 = (v, sel) => '<option value="' + esc(v.id) + '"' + (v.id === sel ? " selected" : "") + ">" + esc(v.nom + " — " + v.desc + " (" + dlgGenre(v.genre) + ")") + "</option>";
  // v2.88.0 (R19) : voix FRANCAISES d'abord ; serveur d'avant (aucune « fr ») -> la liste d'avant
  const optV = sel => (DLG.voix.some(v => v.fr)
      ? '<optgroup label="🇫🇷 Voix françaises">' + DLG.voix.filter(v => v.fr).map(v => opt1(v, sel)).join("") + "</optgroup>"
        + '<optgroup label="Autres voix (accent anglais)">' + DLG.voix.filter(v => !v.fr).map(v => opt1(v, sel)).join("") + "</optgroup>"
      : DLG.voix.map(v => opt1(v, sel)).join(""))""")
rep("""      + '<label>Voix</label><select data-k="voix_el">' + optV(p.voix_el) + "</select>\"""",
    """      + '<label>Voix</label><select data-k="voix_el">' + optV(p.voix_el) + "</select>"
      + (DLG.voix.some(v => v.fr) && DLG.voix.some(v => v.id === p.voix_el) && !DLG.voix.some(v => v.id === p.voix_el && v.fr)
         ? '<div class="muted dlgp-accent">🇬🇧 accent anglais — une voix française est proposée en tête de liste</div>' : "")   // v2.88.0""")
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
