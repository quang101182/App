# -*- coding: utf-8 -*-
"""v2.75.0 (Quang 26/09 14h06) : la POCHETTE officielle et la FICHE (tomes, dates) d'une serie fraichement capturee se posent
SANS avoir a l'ouvrir. Regression de v2.67.1 : la fin de capture ouvrait le manga, ce qui les declenchait ; l'ouverture retiree,
elles attendaient la 1re ouverture. -> serieAuto(serie) : memes conditions qu'avant, appelee a l'ouverture ET en fin de
capture pour la serie capturee, et elle seule (= comportement d'avant v2.67.1, SANS l'ouverture).
Jamais pendant une capture (chapitre sans manifeste). Navigateur pilote (banc) : rien, sauf window.BANC_AUTO.
Rejouable : python app_patch_275_serie_auto.py [chemin de manga_studio.html]"""
import io, sys
P = sys.argv[1] if len(sys.argv) > 1 else r"D:\Download\02-Apps-Web\Repo-github\App\manga-studio\manga_studio.html"
s = io.open(P, encoding="utf-8", newline="").read()
if 'const VERSION = "2.75.0"' in s:
    print("deja applique"); sys.exit(0)
NL = "\r\n" if "\r\n" in s else "\n"
def rep(a, z):
    global s
    a, z = a.replace("\n", NL), z.replace("\n", NL)
    assert s.count(a) == 1, ("ancre", a[:70], s.count(a))
    s = s.replace(a, z)
rep("""  const captureFinie = serie.chaps.every(i => CHAPS[i].manifest);
  const majInfo = serie.info && serie.info.maj ? Date.parse(serie.info.maj.replace(" ", "T")) || 0 : 0;
  if (captureFinie && (!serie.info || dateAjout(serie) > majInfo + 60000) && !TOMES_DEMANDES.has(serie.slug)){
    TOMES_DEMANDES.add(serie.slug);
    chercherTomes(serie.slug).catch(e => log("tomes : " + e.message, "w"));
  }
  if (captureFinie && !serie.pochette && !POCH_DEMANDEES.has(serie.slug)){
    POCH_DEMANDEES.add(serie.slug);
    poserPochette({ slug: serie.slug, source: "anilist", titre: serie.title }).catch(e => log("pochette auto : " + e.message, "w"));
  }
""", """  serieAuto(serie);                                                                  // v2.75.0 : meme chose sans ouvrir
""")
rep("""const TOMES_DEMANDES = new Set(), POCH_DEMANDEES = new Set();   // v2.8.5 : une demande auto par serie et par session
""", """const TOMES_DEMANDES = new Set(), POCH_DEMANDEES = new Set();   // v2.8.5 : une demande auto par serie et par session
// v2.75.0 : fiche (tomes, dates) + pochette officielle d'une serie -- a l'ouverture, ET en fin de capture pour la serie
// capturee, sans l'ouvrir (la fin de capture n'ouvre plus le manga depuis v2.67.1 : elles attendaient l'ouverture)
function serieAuto(serie){
  if (!serie || (navigator.webdriver && !window.BANC_AUTO)) return;            // un banc n'ecrit rien dans la bibliotheque
  const captureFinie = serie.chaps.every(i => CHAPS[i].manifest);                // jamais pendant une capture
  const majInfo = serie.info && serie.info.maj ? Date.parse(serie.info.maj.replace(" ", "T")) || 0 : 0;
  if (captureFinie && (!serie.info || dateAjout(serie) > majInfo + 60000) && !TOMES_DEMANDES.has(serie.slug)){
    TOMES_DEMANDES.add(serie.slug);
    chercherTomes(serie.slug).catch(e => log("tomes : " + e.message, "w"));
  }
  if (captureFinie && !serie.pochette && !POCH_DEMANDEES.has(serie.slug)){
    POCH_DEMANDEES.add(serie.slug);
    poserPochette({ slug: serie.slug, source: "anilist", titre: serie.title }).catch(e => log("pochette auto : " + e.message, "w"));
  }
}
function serieAutoDe(dir){                        // la serie qu'on VIENT de capturer (et elle seule), sans l'ouvrir
  if (dir) serieAuto(mesSeries().find(x => x.slug === serieDe(dir)));
}
""")
rep("""    toast("capture terminée : « " + s.titre + " » est à jour dans la bibliothèque");""",
    """    toast("capture terminée : « " + s.titre + " » est à jour dans la bibliothèque");
    serieAutoDe((s.dossiers || [])[0]);                  // v2.75.0 : pochette + fiche de CETTE serie, sans l'ouvrir""")
rep("""    toast("capture terminée : « " + s.titre + " » ch. " + s.chapitre + " est dans la bibliothèque");   // v2.67.1 : plus d'ouverture auto""",
    """    toast("capture terminée : « " + s.titre + " » ch. " + s.chapitre + " est dans la bibliothèque");   // v2.67.1 : plus d'ouverture auto
    serieAutoDe(s.dossier);                              // v2.75.0 : pochette + fiche de CETTE serie, sans l'ouvrir""")
rep("<title>Manga Studio v2.74.0</title>", "<title>Manga Studio v2.75.0</title>")
rep('<span class="ver" id="verBadge">v2.74.0</span>', '<span class="ver" id="verBadge">v2.75.0</span>')
rep('const VERSION = "2.74.0";', 'const VERSION = "2.75.0";')
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("v2.75.0 applique")
