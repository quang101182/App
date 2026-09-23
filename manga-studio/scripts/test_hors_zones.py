"""Banc T2 (4-sexies, 23/09/2026) : les textes « hors zones » de Gemini deviennent des zones de complement, sans
onomatopees, sans texte vide, sans boite absurde, et JAMAIS par-dessus une bulle detectee. Aucun reseau."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import traduire_chapitre as tc
OK = KO = 0
def check(c, n):
    global OK, KO
    OK, KO = (OK + 1, KO) if c else (OK, KO + 1); print(("  OK  " if c else "  KO  ") + n)
bulle = {"id": 3, "x": 0.50, "y": 0.10, "w": 0.20, "h": 0.15}
hors = [{"texte": "然而現在", "type": "narration", "trad": "Pourtant, aujourd'hui…", "box": [50, 60, 400, 140]},     # encadre vertical : garde
        {"texte": "轟", "type": "onomatopee", "trad": "", "box": [500, 500, 600, 600]},                          # onomatopee : ecartee
        {"texte": "你", "type": "dialogue", "trad": "  ", "box": [700, 100, 750, 200]},                           # sans traduction : ecarte
        {"texte": "x", "type": "dialogue", "trad": "Toi !", "box": [120, 520, 200, 650]},                         # sur la bulle 3 : ecarte
        {"texte": "y", "type": "dialogue", "trad": "Oui", "box": [10, 10, 12, 12]},                               # boite minuscule : ecartee
        {"texte": "z", "type": "dialogue", "trad": "Non", "box": "n'importe"}]                                    # boite illisible : ecartee
z = tc.zones_hors(hors, [bulle])
check(len(z) == 1, "1 seule zone gardee sur 6 (%d)" % len(z))
check(z and z[0]["hors_zone"] and z[0]["complement"] and z[0]["id"] > 3, "zone marquee complement + hors_zone, id neuf")
check(z and abs(z[0]["x"] - (0.06 - 0.08 * 0.08)) < 1e-6 and abs(z[0]["y"] - (0.05 - 0.08 * 0.35)) < 1e-6, "boite ymin/xmin milliemes -> fractions, marge 8 %")
check(z and z[0]["_h"]["trad"].startswith("Pourtant"), "la traduction suit la zone")
check(tc.zones_hors([], [bulle]) == [], "rien -> rien")
print("\n%d/%d" % (OK, OK + KO)); sys.exit(1 if KO else 0)
