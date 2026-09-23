# -*- coding: utf-8 -*-
"""Manga Studio v2.5.3 (23/09/2026) : pages traduites montrees d'office + vignettes qui se rechargent seules.

Quang (10h26-10h28), Noritaka ch.1 traduit par un lot : « quand je regarde les pages, elles ne sont pas traduites ».
Cause mesuree : l'app affichait la VO tant que l'appareil n'avait pas choisi une langue dans « Pages affichees » --
seul le bouton 🌐 Traduire de l'app basculait la vue ; une traduction faite par un LOT (ou la nuit) restait cachee.
Desormais : une traduction terminee s'affiche d'office (la langue du telephone si elle existe, sinon la premiere),
SAUF si « VO » a ete choisie expressement sur cet appareil (memorise).
Et (capture 10h27) : des vignettes du chapitre restaient vides apres un rate de chargement, jusqu'au rafraichissement.
Desormais une vignette ratee se recharge seule (3 essais espaces), et le journal le note.
Rejouable : python app_patch_253_trad_et_vignettes.py <manga_studio.html>.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "v2.5.3 : traduction d'office" in s:
    print("deja patche"); sys.exit(0)


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


for a in ("<title>Manga Studio v2.5.2</title>", 'id="verBadge">v2.5.2</span>', 'const VERSION = "2.5.2";'):
    rep(a, a.replace("2.5.2", "2.5.3"))
rep('''try { TRAD_VUE = localStorage.getItem("manga_trad_vue") || ""; } catch {}''',
    '''try { TRAD_VUE = localStorage.getItem("manga_trad_vue") || ""; } catch {}
// v2.5.3 : traduction d'office -- la VO ne reste affichee que si elle a ete CHOISIE (sinon une traduction faite par
// un lot restait cachee : Noritaka ch.1, Quang 23/09 10h26)
let TRAD_VO_CHOISI = false; try { TRAD_VO_CHOISI = localStorage.getItem("manga_trad_vo") === "1"; } catch {}''')
rep('''  $("tradVue").value = finies.some(t => t.langue === TRAD_VUE) ? TRAD_VUE : "";''',
    '''  if (!TRAD_VO_CHOISI && finies.length && !finies.some(t => t.langue === TRAD_VUE)){
    const nav = (navigator.language || "").slice(0, 2).toLowerCase();
    TRAD_VUE = (finies.find(t => t.langue === nav) || finies[0]).langue;          // d'office, sans le memoriser
  }
  $("tradVue").value = finies.some(t => t.langue === TRAD_VUE) ? TRAD_VUE : "";''')
rep('''  TRAD_VUE = $("tradVue").value; try { localStorage.setItem("manga_trad_vue", TRAD_VUE); } catch {}''',
    '''  TRAD_VUE = $("tradVue").value; TRAD_VO_CHOISI = !TRAD_VUE;
  try { localStorage.setItem("manga_trad_vue", TRAD_VUE); localStorage.setItem("manga_trad_vo", TRAD_VO_CHOISI ? "1" : "0"); } catch {}''')
rep('''    TRAD_VUE = lg; try { localStorage.setItem("manga_trad_vue", lg); } catch {}
    await refreshTrads();''',
    '''    TRAD_VUE = lg; TRAD_VO_CHOISI = false;
    try { localStorage.setItem("manga_trad_vue", lg); localStorage.setItem("manga_trad_vo", "0"); } catch {}
    await refreshTrads();''')
rep('''    '<figure data-page="' + k + '"><img loading="lazy" src="' + pageSrc(p.path) + '" alt="page ' + (k + 1) + '">\'''',
    '''    '<figure data-page="' + k + '"><img loading="lazy" src="' + pageSrc(p.path) + '" alt="page ' + (k + 1) + '" onerror="imgReessai(this)">\'''')
rep('''function rafraichirPages(){''',
    '''// v2.5.3 : une vignette ratee (reseau du telephone, tunnel) se recharge seule -- avant, elle restait vide jusqu'au
// rafraichissement (capture Quang 23/09 10h27 : p. 9, 10, 13, 15, 16, 17, 19 vides sur Noritaka ch.1)
function imgReessai(im){
  const n = +(im.dataset.essai || 0), nom = decodeURIComponent((im.src.split("p=")[1] || "").split("&")[0]);
  if (n >= 3){ log("image toujours introuvable après 3 essais : " + nom, "w"); return; }
  im.dataset.essai = n + 1;
  if (!n) log("image ratée, nouvel essai : " + nom, "w");
  setTimeout(() => { im.src = im.src.replace(/&_r=\d+/, "") + "&_r=" + Date.now(); }, 800 * (n + 1));
}
function rafraichirPages(){''')
rep('''    const pg = CHAP_PAGE_LIST[k]; if (pg) im.src = pageSrc(pg.path);''',
    '''    const pg = CHAP_PAGE_LIST[k]; if (pg){ im.dataset.essai = 0; im.src = pageSrc(pg.path); }''')
open(p, "w", encoding="utf-8").write(s)
print("patche")
