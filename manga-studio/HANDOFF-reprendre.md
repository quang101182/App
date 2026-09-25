# HANDOFF — « Reprendre » + historique de lecture (Manga Studio)

> Écrit le 25/09/2026 14h45, fin d'une longue session (v2.45.0 → v2.61.0, tout commité et poussé).
> **Autosuffisant** : tout ce qu'il faut est ici ou dans les fichiers cités du dépôt. « Fait » = `git log` (relire avant de coder).
> Nature des énoncés : les DÉCISIONS ci-dessous sont des intentions validées par Quang (elles font loi) ; l'état du code se
> re-vérifie contre le dépôt.

## 1. Ce que Quang veut (idée du 25/09 14h37, décisions 14h41)

- Un bouton **« ▶ ch. N »** tout à gauche de la **barre de navigation du bas** (à gauche de la bulle verte « où je suis »).
  - Dans un manga (liste de ses chapitres OU un chapitre ouvert) : le **dernier chapitre ouvert dans CE manga**. Toucher =
    y aller, **à la page où il s'était arrêté**. Dynamique : 1, puis 24, puis 2… (le dernier OUVERT, pas le plus avancé).
  - Hors d'un manga (bibliothèque, autres onglets) : **grisé** (jamais masqué — règle d'interface de Quang).
  - Téléphone (≤ 480 px) : « ▶24 » ; PC / Fold déplié : « ▶ ch. 24 ». Couleur **ambrée** (≠ vert de la bulle, ≠ bleu du retour).
- **Appui long** sur ce bouton (même mécanique que l'appui long de la bulle, v2.57.0 : 0,6 s immobile, remplissage, vibration)
  = une **fenêtre « 🕘 Reprendre »** : une ligne par manga (pochette, nom, « il y a 2 h · sur le Fold », « ch. 24 · p. 12 »),
  la plus récente en haut ; toucher une ligne = y aller ; fermer par « ← Fermer » (barre du bas, `nfPanneau()`), le bouton de
  la fenêtre, ou Échap. Ergonomique, rapide.
- **Page retenue EN SILENCE** (tranché par Claude à la demande de Quang) : le bouton n'affiche que le chapitre ; il ramène à la
  page ; l'historique montre « ch. 24 · p. 12 ».
- **Historique COMMUN au PC et au téléphone** (stocké côté SERVEUR), mais **séparé entre l'application principale et la
  secondaire** (compartiment secret : la principale ne doit rien voir de la secondaire — `MANGA_SOURCES_DIR` de chaque
  instance, cf. ROADMAP § 4-quaterdecies).
- Maquette validée sur le principe : **`maquette_reprendre_v1.html`** (dans ce dossier). ⚠ Point à confirmer avec Quang avant
  de coder : dans un chapitre DÉJÀ ouvert, « ▶ » montre-t-il le chapitre d'avant (retour d'un geste) ou reste-t-il sur celui-ci ?

## 2. Où brancher (lu dans le code le 25/09, v2.61.0 — re-vérifier)

- Barre du bas : `<nav class="nav-flot" id="navFlot">` (HTML près de `<div id="toast">`) ; JS `nfMaj()`, `nfCtx()`,
  `nfPanneau()`, `nfAller()`, bloc « v2.53.0 : NAVIGATION FLOTTANTE » (placé APRÈS `const $` — ⚠ voir piège 1).
- Bulle verte + appui long : `#nfInfo`, `nfInfoMaj()`, `nfAppuiLong()` / `nfTraiter()` (v2.57.0) — réutiliser la mécanique.
- Ouvrir un manga : `ouvrirSerie(slug)` ; ouvrir un chapitre : `openChap(i)` (index dans `CHAPS`, `CHAPS[i].dir` =
  « serie/ch_N ») ; chapitre ouvert : `CHAP_OPEN`. Pages : `#chapPages figure[data-page]`.
- Stockage serveur : le fichier `sources/_bibliotheque.json` (par application) porte déjà `masquees` et `ouvertes`
  (`POST /manga/bibliotheque {action:"ouverte", slug}`) → y ajouter un champ `lectures: {slug: {d, page, t, appareil}}`
  avec une action `lecture`. ⚠ Le proxy n'est PAS dans ce dépôt : `C:\Users\quang\Documents\ComfyUI\_studio_llm_proxy.py`.
  Toute modification = un script `proxy-patch/patch_*.py` rejouable + le `.diff`, puis relance **au repos** :
  principale `powershell -File C:\Users\quang\Documents\ComfyUI\relance-proxy.ps1 -Qui manga-studio -Pourquoi "<version>"` ;
  secondaire : vérifier `/manga/activite` vide ET `/manga/fetch_status` ≠ « en cours », tuer le PID qui écoute 8192 SEULEMENT
  s'il s'agit de `espace_prive.py`, puis `Start-ScheduledTask MangaStudioInstance2`.
- ⚠ Les bancs Playwright ne doivent pas écrire l'historique (comme `ouverte` : garde `navigator.webdriver`, v2.48.0).

## 3. Pièges payés dans cette session (ne pas les repayer)

1. **Zone morte de `$`** : tout code de NIVEAU SCRIPT qui appelle `$(...)` doit être APRÈS `const $ = …` (~ligne 2465), sinon
   TOUT le script meurt (deux fois le 25/09). `node --check` ne le voit pas → après chaque édition : sauvegarde `.bak`,
   `node --check` sur le JS extrait, PUIS chargement réel (`typeof $` === "function" sur 8190 et 8192), restauration si échec.
2. **Fichiers en CRLF** : `manga_studio.html`, `ROADMAP.md`, les scripts Python du projet. Un script d'insertion doit
   convertir ses ancres (`\n` → `\r\n`). Un heredoc bash avec `\\n` dans du Python casse les ancres → utiliser l'outil d'édition.
3. **Débordement latéral** : un élément qui dépasse un instant de côté fait agrandir la zone d'affichage en mode téléphone
   (la barre partait sous l'écran) → `html,body{overflow-x:clip}` est en place ; ne pas le retirer.
4. **Largeurs à tester** : 360, 476 (Fold fermé), 704 / 933 (Fold déplié), 1280. Pas seulement 360 / 1280.
5. **Blocs du chapitre repliés par défaut** (v2.60.0) : un banc qui touche un réglage doit d'abord `clOuvrir('narr'|'vid'|'trad'|'mus')`.

## 4. Méthode (celle de toute la session)

Maquette validée ✅ → code → **banc Playwright sur l'app réelle** (8190, 1280 + 360 + Fold, POST bloqués sauf lectures) →
**mutation** (saboter, exiger du rouge, restaurer) → non-régression des bancs voisins (`scripts/test_nav_flot_ui.py`,
`test_appui_long_ui.py`, `test_replier_ui.py`, `test_chapitre_compact_ui.py`, `test_retour_visionneuse_ui.py`) → version
bumpée aux 3 endroits (`<title>`, `#verBadge`, `const VERSION`) → ROADMAP (entrée datée) → commit + push. Prochaine version : **v2.62.0**.

## 5. Autres points ouverts (non urgents, avec leur déclencheur)

- ROADMAP : 🟠 relance du serveur pendant une capture → pas de bilan pour celle-là (déclencheur : si ça arrive).
- ROADMAP : `ouvertes` garde 5 slugs de bancs anciens (sans effet visible).
