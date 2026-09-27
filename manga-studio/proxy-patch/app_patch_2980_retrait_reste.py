# -*- coding: utf-8 -*-
"""v2.98.0 (27/09, Quang 14h46 : « ca me ramene vers l'application secondaire mais avec bandeau chrome […] si je sors et
reviens je reste sur la secondaire mais avec le bandeau chrome ») : RETRAIT de « rester dans la secondaire » (v2.93-2.95),
decision de Quang 14h23 (« soit une solution fiable, soit on laisse comme ca »). Cause : un renvoi fait par la page SANS geste
de l'utilisateur n'est pas confie par Android a l'application secondaire -- il s'affiche DANS la fenetre de la principale, avec
le bandeau de Chrome (meme limite qu'au 24/09). Retires : le script de tete (renvoi) et le souvenir pose a la bascule ; le
souvenir deja pose sur un appareil est EFFACE au chargement (sinon la principale renverrait encore). Gardes : geste 📚, garde
du retour (v2.97.0), orientation, voix. Suppose v2.97.0. Rejouable."""
import re, sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v2.98.0" in s[:900]:
    print("deja applique"); sys.exit(0)
if "v2.97.0" not in s[:1400]:
    print("ERREUR : appliquer d'abord app_patch_2970_garde_geste.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


# le script de tete (du <script> qui suit le <title> jusqu'a son </script>) -> un effacement du souvenir
i = s.index("<title>Manga Studio v2.97.0</title>")
a = s.index("<script>/* v2.93.0 : RESTER", i)
b = s.index("</script>", a) + len("</script>")
s = s[:i] + "<title>Manga Studio v2.98.0</title>" + N + ("<script>/* v2.98.0 : « rester dans la secondaire » RETIRE (bandeau Chrome) -- "
     "on efface le souvenir deja pose */ try { localStorage.removeItem(\"manga_reste_secondaire\"); "
     "localStorage.removeItem(\"manga_reste_secondaire:t\"); } catch (e) {}</script>") + s[b:]
rep('<span class="ver" id="verBadge">v2.97.0</span>', '<span class="ver" id="verBadge">v2.98.0</span>')
rep('const VERSION = "2.97.0";', 'const VERSION = "2.98.0";   // v2.98.0 : retrait de « rester dans la secondaire » (bandeau Chrome sur le Fold, decision Quang)')
rep("""  try {                                                         // v2.93.0 : la principale retient la secondaire ; le retour l'efface
    if (ESPACE.nom === "normal"){ localStorage.setItem("manga_reste_secondaire", u); localStorage.removeItem("manga_reste_secondaire:t"); }
  } catch (e) {}
  location.replace(ESPACE.nom === "prive" ? u + (u.indexOf("#") >= 0 ? "&" : "#") + "retour=1" : u);""",
    """  location.replace(u);                                          // v2.98.0 : plus de souvenir (renvoi retire)""")
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
