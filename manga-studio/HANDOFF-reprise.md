# HANDOFF — reprise de Manga Studio (après la session du 25/09/2026)

> Écrit le 25/09/2026 23h35. **Autosuffisant** : tout est ici ou dans les fichiers cités du dépôt. « Fait » = `git log`.
> **Rien n'est à reprendre d'office** : tout ce qui a été demandé est livré, commité, poussé. Ce fichier sert à repartir vite
> sur une NOUVELLE demande, sans refaire les erreurs de la session. Nature des énoncés : les versions et l'état se re-vérifient
> contre le dépôt ; les règles (dépôt public, méthode) font loi.

## 1. État au 25/09/2026 23h35

- App `manga_studio.html` **v2.77.0** (26/09 15h05) · manga-fetch **0.8.3** (chapitre annoncé sans image = « à jour », 26/09 02h45) — 0.8.2 (webtoons en tuiles découpés aux gouttières, 26/09 02h30 ; 63 ch.
  redécoupés ; sauvegardes `_avant_redecoupe/` EFFACÉES le 26/09 02h45 après validation de Quang à la lecture).
- **26/09 11h00-11h30** : v2.68.0 lecteur vidéo (24/24) + 2 bugs Fold ; v2.69.0 sélecteur rapide (26/26).
- **26/09 11h35-12h05** : sélecteur en narration + visionneuse `test_selecteur_narr_pages_ui` 100/100 (sabotage rouge) ;
  **v2.70.0** commandes vidéo toujours affichées, effacées seulement en plein écran (`test_lecteur_video_ui` 27/27) ; secondaire
  relancée → `videos_pos` actif sur les deux ; **bandeau Chrome de la secondaire RÉSOLU sans code** : sur le Fold les 2 WebAPK sont
  non vérifiées → « Ouvrir les liens compatibles » activé pour chacune (`pm set-app-links-user-selection`, ROADMAP 4-sexdecies) ;
  à refaire si l'une est réinstallée. ~~« secondaire pas installée »~~ = conclusion FAUSSE de 11h40. Plus rien d'ouvert en 4-sexdecies.
- **26/09 12h18-13h00** : v2.71.0 sélecteur = glisser la barre VERS LE BAS (seuil 24 px : 49 px de course réelle) ; v2.72.0
  balayer l'image de la visionneuse vers la DROITE = suivante ; v2.73.0/.1 manifeste `standalone` (barre d'état Android toujours
  visible) + lien `?v=` ; Fold de Quang réinstallé par ADB, liens compatibles réactivés, vérifié. ⚠ `test_bibliotheque_ui.py`
  périmé (déclencheur : prochaine modif de la bibliothèque). Détail : ROADMAP 4-sexdecies.
- **26/09 13h06-15h05** : v2.74.0 « depuis la page 1 » cochée + mémorisée ; v2.75.0 pochette + fiche en fin de capture SANS
  ouvrir (régression v2.67.1 corrigée, la série capturée seule) ; v2.76.0 pochette dès le 1er chapitre ; v2.77.0 n° suggéré
  pour « …/vol-N/ ». Volumes vs chapitres : rien à coder ; ⚠ ne pas capturer les 2 formats d'une série sous le MÊME nom.
- **26/09 15h02-15h25** : site Mangas Origines validé (`sites.json`, banc `test_site_nouveau.py`) ; gestes de fenêtre autorisés
  pendant une capture (proxy `patch_pilote_fenetre_capture.py` + `cdp_mini.py`, banc `test_fenetre_pendant_capture.py` 8/8),
  les 2 applications relancées. En cours à 15h25 : Solo Leveling vol.2 (reprise) — vérifier son bilan « OK : N/N pages ».
- **Ragnarok ch. 2** : images redécoupées, narration + cases retirées (anciennes pages) et gardées dans
  `sources/_avant_redecoupe/` = SEULE copie : ne pas effacer sans demander à Quang.
- **Historique git du dépôt public : NON réécrit — décision de Claude déléguée par Quang (26/09 00h58)** : fichiers actuels propres,
  réécriture = 503 commits / 24 projets + force-push sur la branche de GitHub Pages, sans effacer vraiment côté GitHub. · proxy patché (… `patch_arret.py`, `patch_dernier_paru.py`).
- **26/09 00h40** : « Jusqu'au dernier paru » + sécurités de série + chapitres déjà là (ROADMAP § 4-quindecies, tout coché).
- Livré ce jour (détail + preuves : ROADMAP, entrées du 25/09) :
  - v2.62 « ▶ Reprendre » + historique de lecture (serveur, commun PC + Fold, séparé principale / secondaire) ;
  - v2.63 choix du manga sur téléphone (écran plein, `choixOuvrir()` réutilisable) + détection de la série d'après l'onglet ;
  - v2.64 n° de chapitre suggéré d'après l'ADRESSE ; v2.64.1 fin de série (« jusqu'au ch. N : fait », « série terminée ») ;
  - manga-fetch 0.7.3 images refusées hors navigateur (CDP `Page.getResourceContent`), 0.7.4 **mode rapide** (×1,6 à ×2,6,
    A/B octet pour octet sur 9 sites), 0.7.5 objectif atteint, 0.7.6 arrêt entre deux chapitres ;
  - v2.65 / v2.66 **bouton Arrêter** (capture : après ce chapitre / maintenant ; narration / traduction / lot : interruption propre).

## 2. En attente, chacun avec son déclencheur (ROADMAP)

| Point | Déclencheur |
|---|---|
| Fausse alerte « arrêtée avant la fin » quand on REDIMENSIONNE la fenêtre de capture pendant une capture (plafond de 400 pas, aucune image perdue) — préexistant | si ça arrive en vrai |
| Une capture de référence a échoué UNE fois sans message (relance OK) | à surveiller : si ça se reproduit, lire `%LOCALAPPDATA%\manga-fetch\events.log` |
| Pas de bouton d'arrêt pour une VIDÉO (pas de reprise possible) | si Quang en a besoin |
| `scripts/test_capture_serie_ui.py` périmé (cherche `#capSerieMode`, remplacé par les boutons de l'étape 4) | prochaine modification de l'étape 4 |
| ~~Historique git du dépôt PUBLIC contient encore d'anciens noms de la secondaire~~ (décidé : on ne réécrit pas, voir § 1) (les fichiers actuels sont propres ~~(faux au 25/09)~~ → **vrai depuis le 26/09** : 4 fichiers en contenaient encore — app, manga_fetch, maquette_arret_v1, test_choix_manga_ui — neutralisés ; contrôle = `git grep -i -F -f <termes tirés de prive/_sites.json + dossiers de prive/>`) | seulement sur accord EXPLICITE de Quang (réécriture d'historique) |

## 3. Règles et pièges (ne pas les repayer)

1. **Dépôt `App` PUBLIC** : jamais un nom de site, de série ou une adresse de l'application SECONDAIRE dans un fichier, un
   commit ou la ROADMAP. Ses sites : `C:\Users\quang\Documents\MangaStudio-donnees\prive\_sites.json` (hors dépôt). Vocabulaire :
   « application principale / secondaire ».
2. **Fichiers en CRLF** (`manga_studio.html`, `ROADMAP.md`, `manga_fetch.py`) : insérer par un SCRIPT Python écrit dans un
   fichier (pas un heredoc : les `\n` d'une chaîne JS deviennent de vrais retours à la ligne) ; ancres converties en `\r\n`.
   Après chaque édition : `.bak` puis `node --check` sur le JS extrait (`<script>…</script>`), puis chargement réel.
3. **Code de niveau script** qui appelle `$(...)` : APRÈS `const $ = …`. Vérifier les **noms** avant d'en créer (`LECT` était
   pris → `LCT`).
4. **Tests qui exigent une app AU REPOS** (`test_activite_ui`, `test_vue_croisee`) : vérifier `/manga/activite` sur 8190 ET 8192
   avant. Une vraie capture qui tourne les fait échouer sans défaut de l'app.
5. **Sabotage (mutation)** : LIRE le verdict avant d'écrire « rouge » ; contrôler un élément = `is_visible()` + texte ; une
   interception Playwright vise le chemin EXACT (`**/manga/activite*` captait aussi `/activite_autre`).
6. **Ouvrir un onglet par CDP** `/json/new?` : encoder l'adresse ENTIÈRE (`quote(url, safe="")`), sinon les `&` sont perdus.
7. **Proxy** (`C:\Users\quang\Documents\ComfyUI\_studio_llm_proxy.py`, hors dépôt) : toute modification = `proxy-patch/patch_*.py`
   rejouable + `.diff`, testé d'abord sur une COPIE ; relance AU REPOS — principale :
   `powershell -File C:\Users\quang\Documents\ComfyUI\relance-proxy.ps1 -Qui manga-studio -Pourquoi "<version>"` ; secondaire :
   `/manga/activite` vide, tuer le PID du port 8192 SEULEMENT s'il s'agit de `espace_prive.py`, puis `Start-ScheduledTask MangaStudioInstance2`.
8. **Une capture en cours** tourne dans UN processus chargé au démarrage : modifier `manga_fetch.py` ne la touche pas.
9. **Fenêtre de capture** : la DÉPLACER = sans effet (mesuré) ; la REDIMENSIONNER = fausse alerte (voir § 2) ; la fermer = coupe.

## 4. Outils de preuve (dans `scripts/`)

- `ab_mode_rapide.py <port CDP> <adresse> <n°>` : même chapitre capturé avec l'ancienne et la nouvelle méthode, dossiers
  temporaires, verdict octet pour octet. Ports : principale 9223, secondaire 9224.
- `test_deplacer_fenetre.py <port> <adresse> <n°> [position|taille]` : capture pendant qu'on déplace / redimensionne la fenêtre.
- `mesure_chargement_bande.py` : temps de chargement réel par pas (cache coupé).
- Bancs du 26/09 : `test_dernier_paru` 19/19 (vraies captures MangaDex 141-143 ; `--mutation-app`), `test_serie_securites` 16/16.
  ⚠ `test_capture_serie.py` vise **8191** par défaut (copie de test, éteinte) : passer **8190**.
- Bancs du 25/09 : `test_reprendre_ui` 112/112, `test_choix_manga_ui` 127/127, `test_arret_capture` 14/14 (vraie capture, nettoie
  tout), `test_arret_traitement_ui` 11/11, `test_activite_ui` 64/64.

## 5. Méthode (celle de toute la session)

Maquette validée par Quang → code → banc sur l'APP RÉELLE (8190 ; 360, 476, 704, 933×700, 1280) → sabotage exigé rouge →
bancs voisins → version aux 3 endroits (`<title>`, `#verBadge`, `const VERSION`) → ROADMAP (entrée datée) → commit + push.
