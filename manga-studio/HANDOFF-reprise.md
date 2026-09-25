# HANDOFF — reprise de Manga Studio (après la session du 25/09/2026)

> Écrit le 25/09/2026 23h35. **Autosuffisant** : tout est ici ou dans les fichiers cités du dépôt. « Fait » = `git log`.
> **Rien n'est à reprendre d'office** : tout ce qui a été demandé est livré, commité, poussé. Ce fichier sert à repartir vite
> sur une NOUVELLE demande, sans refaire les erreurs de la session. Nature des énoncés : les versions et l'état se re-vérifient
> contre le dépôt ; les règles (dépôt public, méthode) font loi.

## 1. État au 25/09/2026 23h35

- App `manga_studio.html` **v2.66.0** · manga-fetch **0.7.6** · proxy patché (`proxy-patch/patch_lectures.py`, `patch_arret.py`).
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
| Historique git du dépôt PUBLIC contient encore d'anciens noms de la secondaire (les fichiers actuels sont propres) | seulement sur accord EXPLICITE de Quang (réécriture d'historique) |

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
- Bancs du jour : `test_reprendre_ui` 112/112, `test_choix_manga_ui` 127/127, `test_arret_capture` 14/14 (vraie capture, nettoie
  tout), `test_arret_traitement_ui` 11/11, `test_activite_ui` 64/64.

## 5. Méthode (celle de toute la session)

Maquette validée par Quang → code → banc sur l'APP RÉELLE (8190 ; 360, 476, 704, 933×700, 1280) → sabotage exigé rouge →
bancs voisins → version aux 3 endroits (`<title>`, `#verBadge`, `const VERSION`) → ROADMAP (entrée datée) → commit + push.
