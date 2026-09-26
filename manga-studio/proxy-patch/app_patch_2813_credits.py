# -*- coding: utf-8 -*-
"""v2.81.3 (D8, 27/09) : credits ElevenLabs du detail des couts en 3 cases titrees (comme les dollars),
au lieu de « 822 · 822 · 822 » lu comme « 3 x 822 » (Quang 01:10). Rejouable : sans effet si deja applique."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v2.81.3" in s[:400]:
    print("deja applique"); sys.exit(0)
N = "\r\n"
def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:60], s.count(a)); s = s.replace(a, b)
rep("""  return '<table class="couts-t"><tr><th>🎭 Dialogues — voix ElevenLabs</th><th class="n">crédits</th></tr>'
    + "<tr><td>aujourd'hui · ce mois · depuis le début</td><td class=\\"n\\">" + fmtCr(e.aujourdhui) + " · " + fmtCr(e.mois) + " · " + fmtCr(e.total) + "</td></tr>"
""", """  const cse = (t, v) => "<div>" + t + "<b>" + fmtCr(v) + "</b>crédits</div>";
  return '<h3 style="margin:14px 0 8px;font-size:15px">🎭 Dialogues — voix ElevenLabs</h3><div class="couts-tot">'
    + cse("aujourd'hui", e.aujourdhui) + cse("ce mois", e.mois) + cse("depuis le début", e.total) + "</div>"
    + '<table class="couts-t">'
""")
s = s.replace("<title>Manga Studio v2.81.2</title>", "<title>Manga Studio v2.81.3</title>", 1)
s = s.replace('id="verBadge">v2.81.2<', 'id="verBadge">v2.81.3<', 1)
s = s.replace('const VERSION = "2.81.2";', 'const VERSION = "2.81.3";   // v2.81.3 : credits ElevenLabs en 3 cases titrees + tarif mesure (dialogues.py 1.7.0)', 1)
assert s.count("2.81.3") >= 3
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
