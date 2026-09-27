# -*- coding: utf-8 -*-
"""v2.93.0 (27/09, Quang 14h08 : « si je suis dans la secondaire, je reste dedans tant que je n'ai pas fait la manipulation,
tant que je n'ai pas appuye sur Bibliotheque ») -- TELEPHONE (les deux raccourcis sont deux applications, journal du Fold 14h03) :
- la principale RETIENT qu'on est passe a la secondaire (appui long, chemin du telephone) ;
- tant qu'on n'est pas revenu par 📚 (ou la panique Echap), l'ouvrir -- par son icone -- renvoie AUSSITOT dans la secondaire
  (des le tout debut du chargement, page masquee : pas de flash), sans limite de temps ;
- revenir par 📚 depuis la secondaire passe « #retour=1 » a la principale : elle oublie, et reste la principale ;
- filet : si la principale se recharge < 20 s apres une redirection (secondaire injoignable), elle ne boucle pas : elle reste
  ouverte et le dit.
PC : la secondaire vit dans sa fenetre dediee -- rien ne change (le souvenir n'est pose QUE par le chemin du telephone).
Suppose v2.92.0. Rejouable."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v2.93.0" in s[:400]:
    print("deja applique"); sys.exit(0)
if "v2.92.0" not in s[:400]:
    print("ERREUR : appliquer d'abord app_patch_2920_garde_retour.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


rep("<title>Manga Studio v2.92.0</title>", """<title>Manga Studio v2.93.0</title>
<script>/* v2.93.0 : RESTER dans la secondaire tant qu'on n'est pas revenu par 📚 (le plus tot possible : pas de flash) */
(function(){ try {
  var K = "manga_reste_secondaire";
  if (/[#&]retour=1/.test(location.hash)){ localStorage.removeItem(K);
    history.replaceState(null, "", location.pathname + location.search + location.hash.replace(/[#&]retour=1/, "").replace(/^&/, "#")); return; }
  function aller(){
    var u = localStorage.getItem(K);
    if (!u || u.indexOf(location.host) >= 0) return;
    var t = +(localStorage.getItem(K + ":t") || 0);
    if (Date.now() - t < 20000){ window.__resteEchec = true; return; }      // recharge juste apres une redirection : injoignable
    localStorage.setItem(K + ":t", String(Date.now()));
    document.documentElement.style.visibility = "hidden";
    setTimeout(function(){ document.documentElement.style.visibility = ""; }, 3000);   // jamais une page vide derriere
    location.replace(u);
  }
  aller();
  // application installee : la principale revient au premier plan SANS se recharger (icone touchee) -> meme regle
  document.addEventListener("visibilitychange", function(){ if (!document.hidden) try { aller(); } catch (e) {} });
} catch (e) {} })();
</script>""")
rep('<span class="ver" id="verBadge">v2.92.0</span>', '<span class="ver" id="verBadge">v2.93.0</span>')
rep('const VERSION = "2.92.0";', 'const VERSION = "2.93.0";   // v2.93.0 : on RESTE dans la secondaire tant qu on n est pas revenu par 📚 (telephone)')
rep("""  const u = espaceAutreURL(); if (u) location.replace(u);      // repli : pas de fenetre dediee (ou telephone) -- v2.90.0 : replace, pas d'historique""",
    """  const u = espaceAutreURL(); if (!u) return;                  // repli : pas de fenetre dediee (ou telephone) -- v2.90.0 : replace
  try {                                                         // v2.93.0 : la principale retient la secondaire ; le retour l'efface
    if (ESPACE.nom === "normal"){ localStorage.setItem("manga_reste_secondaire", u); localStorage.removeItem("manga_reste_secondaire:t"); }
  } catch (e) {}
  location.replace(ESPACE.nom === "prive" ? u + (u.indexOf("#") >= 0 ? "&" : "#") + "retour=1" : u);""")
# appui long robuste (Quang 14h09 : « je n'arrive plus a aller vers la secondaire […] ca n'a pas marche au bout de deux, trois
# essais ») : journal du Fold = onglet 📚 BIEN affiche ; aucune trace des essais rates (rien n'etait journalise). Cause la plus
# probable : un leger glissement du doigt -> le navigateur prend le geste (pointercancel) et annule le minuteur. Desormais :
# le bouton interdit au navigateur de prendre le geste (touch-action:none), et chaque appui long ANNULE est journalise (cause).
rep("""  b.addEventListener("pointerdown", () => { long = false; stop();
    if (!b.classList.contains("sel")) return;                    // v2.86.0 : depuis la Bibliotheque DEJA affichee seulement
    t = setTimeout(() => { long = true; espaceBasculer(); }, 1200); });
  ["pointerup", "pointerleave", "pointercancel"].forEach(ev => b.addEventListener(ev, stop));""",
    """  b.style.touchAction = "none"; b.style.webkitTouchCallout = "none"; b.style.userSelect = "none";   // v2.93.0 : le doigt reste a nous
  let t0 = 0;
  b.addEventListener("pointerdown", () => { long = false; stop();
    if (!b.classList.contains("sel")) return;                    // v2.86.0 : depuis la Bibliotheque DEJA affichee seulement
    t0 = Date.now(); t = setTimeout(() => { t = null; long = true; log("appui long : bascule d'application"); espaceBasculer(); }, 1200); });
  ["pointerup", "pointerleave", "pointercancel"].forEach(ev => b.addEventListener(ev, () => {
    if (t && Date.now() - t0 > 300) log("appui long annulé (" + ev + " à " + ((Date.now() - t0) / 1000).toFixed(1).replace(".", ",") + " s)");   // v2.93.0
    stop(); }));""")
rep("""let ESP_DISCRETION = false;""", """setTimeout(() => { if (window.__resteEchec && typeof toast === "function")        // v2.93.0 : filet, pas de boucle
  toast("application secondaire injoignable — tu es dans la principale (appui long sur 📚 pour réessayer)"); }, 1500);
let ESP_DISCRETION = false;""")
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
