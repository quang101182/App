# -*- coding: utf-8 -*-
"""v2.76.0 (Quang 26/09 14h09-14h12 : « pourquoi attendre la fin ? » -> go) : la POCHETTE officielle d'un manga se pose des
que le PREMIER chapitre est capture (titre connu, dossier cree), pendant que la suite se capture. La FICHE (tomes, dates)
reste en fin de capture : elle range les chapitres par tome d'apres leur numero (v2.8.5).
Rejouable : python app_patch_276_pochette_tot.py [chemin de manga_studio.html]"""
import io, sys
P = sys.argv[1] if len(sys.argv) > 1 else r"D:\Download\02-Apps-Web\Repo-github\App\manga-studio\manga_studio.html"
s = io.open(P, encoding="utf-8", newline="").read()
if 'const VERSION = "2.76.0"' in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"
def rep(a, z):
    global s
    a, z = a.replace("\n", NL), z.replace("\n", NL)
    assert s.count(a) == 1, ("ancre", a[:70], s.count(a))
    s = s.replace(a, z)
rep("""function serieAutoDe(dir){                        // la serie qu'on VIENT de capturer (et elle seule), sans l'ouvrir
  if (dir) serieAuto(mesSeries().find(x => x.slug === serieDe(dir)));
}""", """function serieAutoDe(dir){                        // la serie qu'on VIENT de capturer (et elle seule), sans l'ouvrir
  if (dir) serieAuto(mesSeries().find(x => x.slug === serieDe(dir)));
}
// v2.76.0 : la POCHETTE des le 1er chapitre capture (le titre suffit, le dossier existe) -- un manga tout neuf, encore
// absent de la bibliotheque, compte comme « sans pochette ». La FICHE attend la fin (numeros de chapitre -> tomes).
function pochetteTot(dir, titre){
  if (!dir || (navigator.webdriver && !window.BANC_AUTO)) return;
  const slug = serieDe(dir), serie = mesSeries().find(x => x.slug === slug);
  if ((serie && serie.pochette) || POCH_DEMANDEES.has(slug)) return;
  POCH_DEMANDEES.add(slug);
  poserPochette({ slug, source: "anilist", titre: (serie && serie.title) || titre }).catch(e => log("pochette auto : " + e.message, "w"));
}""")
rep("""    bar.firstElementChild.style.width = Math.min(95, 5 + s.pages * 1.5) + "%";   // pas de total connu d'avance
    return;
  }
  clearInterval(CAP_POLL); CAP_POLL = null;""", """    bar.firstElementChild.style.width = Math.min(95, 5 + s.pages * 1.5) + "%";   // pas de total connu d'avance
    if (faits) pochetteTot(s.dossiers[0], s.titre);                                  // v2.76.0 : 1er chapitre fait
    return;
  }
  clearInterval(CAP_POLL); CAP_POLL = null;""")
rep("<title>Manga Studio v2.75.0</title>", "<title>Manga Studio v2.76.0</title>")
rep('<span class="ver" id="verBadge">v2.75.0</span>', '<span class="ver" id="verBadge">v2.76.0</span>')
rep('const VERSION = "2.75.0";', 'const VERSION = "2.76.0";')
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("v2.76.0 applique")
