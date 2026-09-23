# -*- coding: utf-8 -*-
"""Manga Studio v2.5.2 (23/09/2026) : l'etat des videos se rafraichit tout seul.

Quang (09h00) : apres avoir supprime d'anciennes videos et relance la generation en case par case, un chapitre
affichait encore une video qui n'existait plus ; le bouton ↻ donnait le bon etat. Trois trous dans le code :
- ouvrir un chapitre de la MEME serie reutilisait la liste des videos en memoire (VIDS) sans la redemander ;
- la fin d'une tache (video, lot) rafraichissait narration / traduction / resume... mais jamais les videos ;
- le suivi automatique ne tournait que si une video etait deja « en cours » au dernier affichage.
Desormais : ouverture d'un chapitre = affichage immediat puis rechargement ; une tache video ou lot qui tourne
ou finit -> rechargement ; retour dans l'app -> rechargement. Et le journal dit chaque suppression / demande.
Rejouable : python app_patch_252_videos_fraiches.py <manga_studio.html>.
"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "v2.5.2 : videos fraiches" in s:
    print("deja patche"); sys.exit(0)


def rep(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit("ancre introuvable ou multiple (%d) : %r" % (s.count(a), a[:70]))
    s = s.replace(a, b)


for a in ("<title>Manga Studio v2.5.1</title>", 'id="verBadge">v2.5.1</span>', 'const VERSION = "2.5.1";'):
    rep(a, a.replace("2.5.1", "2.5.2"))
rep('''  if (VIDS.serie === serieDe(CHAP_OPEN)) vidRendre();
  else vidCharger(serieDe(CHAP_OPEN)).catch(err => log("vidéos : " + err.message, "w"));''',
    '''  if (VIDS.serie === serieDe(CHAP_OPEN)) vidRendre();                                      // tout de suite (en memoire)...
  vidCharger(serieDe(CHAP_OPEN)).catch(err => log("vidéos : " + err.message, "w"));          // v2.5.2 : videos fraiches, puis l'etat du PC''')
rep('''    if (fini) chargerResume();                            // v2.1.0 : une narration / video finie apparait sur sa carte''',
    '''    if (fini) chargerResume();                            // v2.1.0 : une narration / video finie apparait sur sa carte
    // v2.5.2 : une video (ou un lot, qui en demande) tourne ou vient de finir -> l'etat des videos est recharge
    const vidBouge = x => x.type === "video" || x.type === "lot";
    if (VIDS.serie && (items.some(vidBouge) || ACT.items.some(x => vidBouge(x) && !cles.has(actCle(x)))))
      vidCharger(VIDS.serie).catch(() => {});''')
rep('''document.addEventListener("visibilitychange", () => { if (!document.hidden){ chargerCouts(); actRafraichir(); } });''',
    '''document.addEventListener("visibilitychange", () => { if (!document.hidden){ chargerCouts(); actRafraichir();
  if (VIDS.serie) vidCharger(VIDS.serie).catch(() => {}); } });                            // v2.5.2 : retour dans l'app''')
rep('''  const r = await api("/manga/video", { entrees: liste.map(c => ({ d: c.d, tag: vidTag(c) })), reglages: reglagesLecteur() });''',
    '''  const r = await api("/manga/video", { entrees: liste.map(c => ({ d: c.d, tag: vidTag(c) })), reglages: reglagesLecteur() });
  log("vidéos demandées : " + liste.map(c => c.d).join(", ") + " (" + vidRegTxt(reglagesLecteur()) + (refaire ? ", l'ancienne à la corbeille" : "") + ")");''')
rep('''      const r = await api("/manga/video_suppr", { d: c.d, tag: c.videos[0].tag }); if (r.error) throw new Error(r.error);
      await vidCharger(VIDS.serie);''',
    '''      const r = await api("/manga/video_suppr", { d: c.d, tag: c.videos[0].tag }); if (r.error) throw new Error(r.error);
      log("vidéo supprimée (corbeille) : " + c.d + " · " + c.videos[0].tag);
      await vidCharger(VIDS.serie);''')
open(p, "w", encoding="utf-8").write(s)
print("patche")
