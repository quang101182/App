# -*- coding: utf-8 -*-
"""v2.95.0 (27/09, Quang 14h23 : « ca a marche une premiere fois, mais depuis cela ne fonctionne plus ») -- journal du Fold :
chaque echec = icone de la principale touchee MOINS DE 20 s apres un renvoi reussi (14:22:27 -> 30, 33 ; 43 -> 50). Cause =
MON filet anti-boucle de la v2.93.0 (« rechargee < 20 s apres une redirection = secondaire injoignable »), qui se declenchait
aussi quand la principale revient simplement au PREMIER PLAN (application installee : pas de rechargement, donc AUCUNE boucle
possible). Desormais : le filet ne vaut QUE pour un vrai rechargement de page ; au retour au premier plan, le renvoi se fait
toujours. + la principale se masque des qu'elle passe en arriere-plan tant qu'elle doit renvoyer (plus d'apercu de 2-3 s
avant le renvoi), et se reaffiche seule au bout de 3 s si rien ne se passe. Suppose v2.94.0. Rejouable."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "manga_studio.html"
s = open(P, encoding="utf-8", newline="").read()
if "v2.95.0" in s[:600]:
    print("deja applique"); sys.exit(0)
if "v2.94.0" not in s[:600]:
    print("ERREUR : appliquer d'abord app_patch_2940_voix_preferees.py"); sys.exit(1)
N = "\r\n" if "\r\n" in s else "\n"


def rep(a, b):
    global s
    a, b = a.replace("\n", N), b.replace("\n", N)
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


rep("<title>Manga Studio v2.94.0</title>", "<title>Manga Studio v2.95.0</title>")
rep('<span class="ver" id="verBadge">v2.94.0</span>', '<span class="ver" id="verBadge">v2.95.0</span>')
rep('const VERSION = "2.94.0";', 'const VERSION = "2.95.0";   // v2.95.0 : le renvoi vers la secondaire marche a chaque retour au premier plan (filet reserve aux rechargements)')
rep("""  function aller(){
    var u = localStorage.getItem(K);
    if (!u || u.indexOf(location.host) >= 0) return;
    var t = +(localStorage.getItem(K + ":t") || 0);
    if (Date.now() - t < 20000){ window.__resteEchec = true; return; }      // recharge juste apres une redirection : injoignable
    localStorage.setItem(K + ":t", String(Date.now()));""",
    """  function aller(premierPlan){
    var u = localStorage.getItem(K);
    if (!u || u.indexOf(location.host) >= 0) return;
    var t = +(localStorage.getItem(K + ":t") || 0);
    // v2.95.0 : le filet anti-boucle ne vaut QUE pour un vrai RECHARGEMENT (retour au premier plan = aucune boucle possible)
    if (!premierPlan && Date.now() - t < 20000){ window.__resteEchec = true; return; }
    localStorage.setItem(K + ":t", String(Date.now()));""")
rep("""  document.addEventListener("visibilitychange", function(){ if (!document.hidden) try { aller(); } catch (e) {} });""",
    """  document.addEventListener("visibilitychange", function(){ try {
    if (document.hidden){ if (localStorage.getItem(K)) document.documentElement.style.visibility = "hidden"; return; }   // v2.95.0 : pas d'apercu
    aller(true);
    setTimeout(function(){ document.documentElement.style.visibility = ""; }, 3000);
  } catch (e) {} });""")
open(P, "w", encoding="utf-8", newline="").write(s)
print("ok")
