# -*- coding: utf-8 -*-
"""v2.79.3 (Quang 26/09 18h48-19h02, Fold hors de chez lui, capture d'ecran) : le bandeau « arretee a ta demande… Reprendre »
restait alors que le bilan serveur etait « jusqu'au ch. 15 : fait » (verifie PAR Cloudflare : reponses fraiches, no-store).
Le mecanisme s'efface bien en test ; sur le telephone, AUCUNE trace : capAlerteVerifier avalait ses erreurs (catch { return; })
et le journal client n'avait plus une ligne depuis 13h19. -> (1) chaque echec est ECRIT au journal (une fois par type),
chaque effacement aussi ; (2) re-verification au RETOUR dans l'app (visibilitychange / pageshow / focus), sans attendre 60 s.
Rejouable : python app_patch_2793_bandeau_trace.py [chemin de manga_studio.html]"""
import io, sys
P = sys.argv[1] if len(sys.argv) > 1 else r"D:\Download\02-Apps-Web\Repo-github\App\manga-studio\manga_studio.html"
s = io.open(P, encoding="utf-8", newline="").read()
if 'const VERSION = "2.79.3"' in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"
def rep(a, z):
    global s
    a, z = a.replace("\n", NL), z.replace("\n", NL)
    assert s.count(a) == 1, ("ancre", a[:70], s.count(a))
    s = s.replace(a, z)
rep("""async function capAlerteVerifier(){
  let j; try { j = await api("/manga/capture_derniere"); } catch { return; }""",
"""let CAP_VERIF_ERR = "";                                  // v2.79.3 : derniere erreur ecrite (une fois par type, pas toutes les 60 s)
async function capAlerteVerifier(){
  let j; try { j = await api("/manga/capture_derniere"); }
  catch (e){ const m = "bilan de capture illisible : " + (e && e.message || e); if (m !== CAP_VERIF_ERR){ CAP_VERIF_ERR = m; log(m, "w"); } return; }
  CAP_VERIF_ERR = "";
  const avant = !!CAP_ALERTE;""")
rep("""  CAP_ALERTE = j && j.fin && (j.tenu === false || (j.dernier_paru && j.tenu)) && String(j.fin) !== vu && !enCours ? j : null;
  capAlerteRendre();
}""", """  CAP_ALERTE = j && j.fin && (j.tenu === false || (j.dernier_paru && j.tenu)) && String(j.fin) !== vu && !enCours ? j : null;
  if (avant && !CAP_ALERTE) log("bandeau de capture effacé : " + (enCours ? "une capture tourne" : "bilan à jour (" + (j && j.arret || "?") + ")"));
  capAlerteRendre();
}
// v2.79.3 : au RETOUR dans l'app (deverrouillage, retour d'une autre app) -- sans attendre le prochain tour de 60 s
(function capAlerteAuRetour(){
  let t = 0; const go = () => { if (document.hidden || Date.now() - t < 5000) return; t = Date.now(); capAlerteVerifier().catch(() => {}); };
  document.addEventListener("visibilitychange", go); addEventListener("pageshow", go); addEventListener("focus", go);
})();""")
rep("<title>Manga Studio v2.79.2</title>", "<title>Manga Studio v2.79.3</title>")
rep('<span class="ver" id="verBadge">v2.79.2</span>', '<span class="ver" id="verBadge">v2.79.3</span>')
rep('const VERSION = "2.79.2";', 'const VERSION = "2.79.3";')
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("v2.79.3 applique")
