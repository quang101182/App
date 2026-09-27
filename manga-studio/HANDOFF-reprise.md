# HANDOFF — reprise de Manga Studio (après la session du 25/09/2026)

> Écrit le 25/09/2026 23h35. **Autosuffisant** : tout est ici ou dans les fichiers cités du dépôt. « Fait » = `git log`.
> **Rien n'est à reprendre d'office** : tout ce qui a été demandé est livré, commité, poussé. Ce fichier sert à repartir vite
> sur une NOUVELLE demande, sans refaire les erreurs de la session. Nature des énoncés : les versions et l'état se re-vérifient
> contre le dépôt ; les règles (dépôt public, méthode) font loi.

## 1. État au 25/09/2026 23h35

- App `manga_studio.html` **v2.82.4** (27/09 03h55 ; R6 écran ✏ au gabarit des fenêtres ; R7 vidéos des Dialogues dans le lecteur vidéo de l'app, précédente / suivante). **Feuille de route de la nuit = ROADMAP § 4-septdecies « Feuille de route de la nuit du 27/09 » (R1 → R5), À SUIVRE DANS L'ORDRE** : R1 ✅ lecteur sans trou (v2.81.7), R2 ✅ format du lecteur (v2.81.8), R3 ✅ D10 (v2.82.0), R3-bis ✅ (une vidéo par portée, v2.82.1), **R4 = PROCHAINE (D12 doublons)**, R5 (D9 clôture). Avant : v2.81.5 à 02h15 (traduire seulement les pages des Dialogues, tracées — ROADMAP D11) ; v2.81.4 à 01h35 : D8 fait sur le Samsung : tarif ElevenLabs v3 réel 0,28 crédit/car., estimation de préparation = pages demandées : ROADMAP § 4-septdecies) · manga-fetch **0.8.4** (chapitre annoncé sans image = « à jour », 26/09 02h45) — 0.8.2 (webtoons en tuiles découpés aux gouttières, 26/09 02h30 ; 63 ch.
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
  les 2 applications relancées. Solo Leveling vol.2 → 15 capturés (912 p. pour le vol.2, 0 vide).
- **26/09 16h20-19h05** : v2.78.0 ordre de la fiche ; v2.79.0 liens Traduction / Musique → Vidéo + lueur (maquette B) ;
  v2.79.1 fiche à 360 px ; v2.79.2 suivi de capture unique ; v2.79.3 bandeau tracé. **Ouvert** : bandeau périmé sur le Fold
  (cause non prouvée ; déclencheur = s'il résiste après rechargement en v2.79.3 → lire le journal client du Fold).
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
| **🎭 Dialogues — caméra « suivre la case » dans le lecteur** (Quang 27/09 00h43 : « c'est important ») : zoom doux sur la case de la bulle qui parle (cases de `/manga/cases`), interrupteur 🎥 mémorisé, défaut ACTIF. Patch app `app_patch_2812_camera.py` | ✅ FAIT v2.81.2 (27/09 00h57) |
| **🎭 Dialogues — D8 appareil réel** | ✅ FAIT 27/09 01h35 (v2.81.3-.4, ROADMAP D8) |
| **🎭 Dialogues — D10 bouton 🎭 dans la fiche de la SÉRIE** (Quang 01h24 : retrouver ce qui existe, sans mélanger avec 🎬 Vidéos ; choix délégué → bouton séparé + panneau « Dialogues de la série ») | **PROCHAINE ÉTAPE** : maquette à faire valider par Quang, puis code |
| Solo Leveling ch.9 (VF) : préparation d'une portée de pages jamais faite en vrai | au 1er usage de Quang, ou pendant D10 |
| Vidéo de dialogues : son empreinte ne compte pas les pages SANS dialogue (`pages_vues`) → élargir une portée sans nouvelle réplique ne la marque pas « à refaire » | si Quang le remarque, ou prochaine modification de `empreinte_video()` |
| Chapitre de Quang sur la secondaire (préparé p.44-65, 4 noms fusionnés à la main) : 34 voix à générer (≈ 377 crédits) | décision de Quang (bouton 🔊 Générer) |
| **Relancer la SECONDAIRE** : elle n'a pas `patch_dialogues_5` (traduction partielle tracée ; l'app y retombe sur l'ancien comportement, sans rien supposer) | ✅ FAIT 27/09 02h17 (~~capture en cours~~ : constat NON revérifié, finie depuis — Quang 02h16) |
| `test_dialogues_largeurs_reel.py` : 1 KO en 5 passages (150 contrôles), non identifié (capture pendant le fondu du halo ?) | s'il revient : relancer avec affichage du contrôle en échec avant toute hypothèse |
| **🎭 Dialogues — relancer la SECONDAIRE au repos** (elle n'a pas les routes Dialogues : patchs proxy 1-3 appliqués au fichier, instance 8192 pas relancée) : `/manga/activite` vide sur 8192, tuer le PID de `espace_prive.py` SEULEMENT, puis `Start-ScheduledTask MangaStudioInstance2` | ✅ FAIT 27/09 00h55 (les deux instances ont les 4 patchs) |
| **🎭 Dialogues — D9 clôture** (ROADMAP § 4-septdecies : constats, versions ; mémoire ; commit) | après D10 |
| Fausse alerte « arrêtée avant la fin » quand on REDIMENSIONNE la fenêtre de capture pendant une capture (plafond de 400 pas, aucune image perdue) — préexistant | si ça arrive en vrai |
| Une capture de référence a échoué UNE fois sans message (relance OK) | à surveiller : si ça se reproduit, lire `%LOCALAPPDATA%\manga-fetch\events.log` |
| Pas de bouton d'arrêt pour une VIDÉO (pas de reprise possible) | si Quang en a besoin |
| `scripts/test_capture_serie_ui.py` périmé (cherche `#capSerieMode`, remplacé par les boutons de l'étape 4) | prochaine modification de l'étape 4 |
| ~~Historique git du dépôt PUBLIC contient encore d'anciens noms de la secondaire~~ (décidé : on ne réécrit pas, voir § 1) (les fichiers actuels sont propres ~~(faux au 25/09)~~ → **vrai depuis le 26/09** : 4 fichiers en contenaient encore — app, manga_fetch, maquette_arret_v1, test_choix_manga_ui — neutralisés ; contrôle = `git grep -i -F -f <termes tirés de prive/_sites.json + dossiers de prive/>`) | seulement sur accord EXPLICITE de Quang (réécriture d'historique) |

## 3. Règles et pièges (ne pas les repayer)

- **27/09 12h21-13h20 — textes restés en anglais / pages sans dialogue** (ROADMAP R12-R15, feuille de route du 27/09 jour) : cause mesurée = la traduction SAUTAIT toute page où le détecteur local ne trouve aucune bulle (15/29 pages du chapitre webtoon ; 206 pages sur 24 chapitres des 2 instances) + écartait les grands encadrés. Livré : `traduire_chapitre.py` 2.3.0 (aucune page sautée, `lue` par page, zone resserrée sur les lettres), `dialogues.py` 1.13.0 (lit les textes écartés pour l'image), serveur `patch_trad_lues` DÉPLOYÉ (Quang : « partout ») → ces chapitres sont « traduits en partie » et l'app repropose les pages jamais lues, coût annoncé. Rien corrigé à la main : c'est à Quang de relancer « 🌐 Traduire puis préparer » (≈ 0,04 $ pour les 15 pages du chapitre).
- **27/09 11h45-12h20 — app v2.85.0** (ROADMAP « Feuille de route du 27/09 (jour) », R8 → R11 tout coché) : v2.83.0 lueur de l'étape suivante des Dialogues ; v2.84.0 panneau 🎭 de la série compact (▶ vidéo, › détail, ▶ Tout lire, ⋯ plusieurs chapitres) ; v2.85.0 « ✓ fini » COMMUN à tous les appareils (journal serveur `_activite_finis.json` par instance, `patch_activite_finis.py` appliqué, 2 instances relancées) + fin des Dialogues par étape. Bancs : lueur 14/14, série 142/142, fins communes 11/11, Samsung 8/8. Onglets restés ouverts sur une version antérieure (PC, Fold) : les RECHARGER pour avoir la v2.85.0.
- **27/09 11h10 — fenêtres Edge au démarrage** : Windows (« Redémarrer mes applications », RestartApps=1) rouvrait à la connexion la fenêtre de capture laissée ouverte (signature `--restart` dans sa ligne de commande). Tâche planifiée **MangaStudioFermerFenetres** (ouverture de session) → `scripts/fermer_fenetres_demarrage.py` v1.0.0 : ferme pendant 4 min les SEULES fenêtres Edge des 3 profils Manga Studio portant `--restart` (CDP, sinon taskkill du PID). Réglage Windows NON modifié (vaut pour toutes les apps). Journal : `%LOCALAPPDATA%\manga-studioermeture_demarrage.log`. Vérifié : relance simulée fermée en < 3 s, ouverture par l'app conservée ; les 3 fenêtres s'ouvrent dans le coin (place retenue : principale 2213,1277 ; secondaire 2387,1344 ; espace privé 2389,1344). ⚠ Non vérifié sur un VRAI redémarrage (déclencheur : prochain démarrage du PC → lire le journal).
0. **Nuit du 27/09 (payés)** : (a) un patch Python écrit par `cat <<EOF` casse les `
` des chaînes JS et les guillemets → écrire
   les patchs avec l'outil d'écriture, un `BS = "\\"` pour les `
` JS, et vérifier `node --check` + « rejeu = fichier identique » ;
   (b) `ROADMAP.md` est en **LF** (pas CRLF) ; (c) un banc qui lit `RESUME` doit l'ATTENDRE (`wait_for_function`) ; (d) ne pas
   effacer les copies de banc (`scratchpad/src_partiel/…`) tant qu'un banc s'en sert ; (e) le lecteur des Dialogues = mêmes
   classes que `#lecteur` : toute règle CSS ciblée `#lecteur …` / `#lecPrev` doit avoir son pendant `#dlgLec …` / `#dllPrec`.


1. **Dépôt `App` PUBLIC** : jamais un nom de site, de série ou une adresse de l'application SECONDAIRE dans un fichier, un
   commit ou la ROADMAP. Ses sites : `C:\Users\quang\Documents\MangaStudio-donnees\prive\_sites.json` (hors dépôt). Vocabulaire :
   « application principale / secondaire ».
2. **Fichiers en CRLF** (`manga_studio.html`, `manga_fetch.py` ; ~~`ROADMAP.md`~~ = LF, constaté 27/09 : tester `
` in s avant) : insérer par un SCRIPT Python écrit dans un
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
