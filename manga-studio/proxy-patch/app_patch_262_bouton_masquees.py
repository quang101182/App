# -*- coding: utf-8 -*-
"""Manga Studio v2.6.2 (23/09/2026) : les series masquees derriere un BOUTON a droite de « Filtres », plus en bas de liste.
Quang (13h52) : « le bouton serie masquee, je ne le mettrai pas en bas a la suite comme ca [...] a cote du bouton filtre
a droite ». « 👁 Masquees (N) » (seulement s'il y en a) bascule la liste sur les series masquees, chacune avec
« Re-afficher » ; un 2e toucher revient a la bibliotheque. Rejouable : python app_patch_262_bouton_masquees.py <html>.
"""
import sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if 'id="libMasqueesBtn"' in s:
    print("deja patche"); sys.exit(0)


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


for a in ("<title>Manga Studio v2.6.1</title>", 'id="verBadge">v2.6.1</span>', 'const VERSION = "2.6.1";'):
    rep(a, a.replace("2.6.1", "2.6.2"))
rep('''    <button class="btn sm" id="libFiltresBtn" aria-expanded="false" title="filtrer par genre, public, statut, thème">⛃ Filtres</button>''',
    '''    <button class="btn sm" id="libFiltresBtn" aria-expanded="false" title="filtrer par genre, public, statut, thème">⛃ Filtres</button>
    <button class="btn sm" id="libMasqueesBtn" aria-pressed="false" hidden title="voir les séries retirées de ta bibliothèque (rien n'est supprimé)">👁 Masquées</button>''')
rep('''#libFiltresBtn.filtre-actif{''', '''#libMasqueesBtn[hidden]{display:none}
#libMasqueesBtn.filtre-actif,#libFiltresBtn.filtre-actif{''')
rep('''        + (cacheesTrouvees.length && LIB_RECH ? " " + cacheesTrouvees.length + " résultat(s) dans les séries masquées, en bas." : "") + "</p>"''',
    '''        + (cacheesTrouvees.length && LIB_RECH ? " " + cacheesTrouvees.length + " résultat(s) dans les séries masquées (bouton « 👁 Masquées »)." : "") + "</p>"''')
rep('''    const montrees = LIB_RECH ? cacheesTrouvees : cachees;
    $("chapList").innerHTML = (trouvees.map(carte).join("") || vide)
      + (montrees.length ? '<details class="lib-masquees" id="libMasquees"' + (LIB_VOIR_MASQUEES ? " open" : "") + "><summary>👁 Séries masquées ("
        + montrees.length + ")</summary>" + montrees.map(s => '<div class="masquee-ligne">' + carte(s)
          + '<button class="btn sm" data-afficher="' + esc(s.slug) + '" title="la remettre dans ta bibliothèque">Ré-afficher</button></div>').join("")
        + "</details>" : "");''',
    '''    const montrees = LIB_RECH ? cacheesTrouvees : cachees;
    // v2.6.2 : les masquees derriere le bouton « 👁 Masquees (N) » (a droite de Filtres), plus en bas de liste
    if (!cachees.length) LIB_VOIR_MASQUEES = false;
    $("libMasqueesBtn").hidden = !cachees.length;
    $("libMasqueesBtn").textContent = LIB_VOIR_MASQUEES ? "← Ma bibliothèque" : "👁 Masquées (" + cachees.length + ")";
    $("libMasqueesBtn").classList.toggle("filtre-actif", LIB_VOIR_MASQUEES);
    $("libMasqueesBtn").setAttribute("aria-pressed", String(LIB_VOIR_MASQUEES));
    $("chapList").innerHTML = LIB_VOIR_MASQUEES
      ? (montrees.map(s => '<div class="masquee-ligne">' + carte(s)
          + '<button class="btn sm" data-afficher="' + esc(s.slug) + '" title="la remettre dans ta bibliothèque">Ré-afficher</button></div>').join("")
         || '<p class="muted aide">Aucune série masquée ne correspond.</p>')
      : (trouvees.map(carte).join("") || vide);''')
rep('''$("chapList").addEventListener("toggle", e => { if (e.target.id === "libMasquees") LIB_VOIR_MASQUEES = e.target.open; }, true);''',
    '''$("libMasqueesBtn").onclick = () => { LIB_VOIR_MASQUEES = !LIB_VOIR_MASQUEES; renderLib(); $("libMasqueesBtn").blur(); };''')
rep("""— elle reste en bas, dans « Séries masquées »""", """— retrouve-la avec le bouton « 👁 Masquées »""")
open(p, "w", encoding="utf-8").write(s)
print("patche")
