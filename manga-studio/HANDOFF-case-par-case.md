# HANDOFF — Mode vidéo « CASE PAR CASE » (écrit le 23/09/2026 à 00h10, session précédente à ~50 % de contexte)

> ✅ **LIVRÉ le 23/09/2026 vers 01h — Manga Studio v2.5.0.** Ce dossier est désormais une ARCHIVE (« fait » = `git log`).
> Réponse de Quang à la question ci-dessous : **oui, le lecteur passe aussi en case par case** (fait). Détail et verdicts : `ROADMAP.md` ligne 4-quater.
> Reste hors chantier, signalé à Quang : 4 pages traduites en FR quasi blanches (OPM ch.296 p.14 et p.18, ch.300 p.5, ch.301 p.16 — dessin perdu à la traduction, ou page de crédits) ; le banc
> `test_profil_ui.py` supprime sa série de test pendant que sa vidéo se fabrique (demande laissée en échec dans `_videos_file`) ; 3 bancs anciens dépendent de données disparues (Claymore ch.1 recapturé le 22/09, OPM ch.301).

> Autosuffisant. « Fait » = `git log`. Version de l'app au départ : **v2.4.6** (`manga_studio.html`).
> **GO de Quang donné le 23/09 à 00h06** : « tu peux attaquer les travaux jusqu'au bout […] je te laisse travailler de manière
> autonome jusqu'au bout ». Pas de rapport à chaque palier : enchaîner jusqu'à la livraison vérifiée.
> Référence feuille de route : `ROADMAP.md`, lignes **4-bis** et **4-ter** (sous l'étape 4).

## ⛔ À FAIRE EN PREMIER : une question à Quang (conflit de règles, ne PAS trancher seul)

Règle du 22/09 (étape 5, ROADMAP) : **« la vidéo doit refléter exactement ce qui est affiché »** dans le LECTEUR de l'app
(`video_chapitre.py` REJOUE `montrerPage` / `musTick` / `karTick`). Un mode case par case dans la VIDÉO seule casserait cette règle.
→ Demander : « Le lecteur de l'app passe-t-il AUSSI en case par case (recommandé : oui, même réglage, même rendu) ? »
En attendant la réponse, commencer par le moteur vidéo (étapes 1-2 ci-dessous), qui est nécessaire dans les deux cas.

## Ce que Quang a vu et décidé (démos hors app, envoyées sur Telegram le 22-23/09)

| Démo | Résultat | Avis de Quang |
|---|---|---|
| Manga classique : OPM ch.300 p.3-7 | caméra de case en case (ordre manga droite→gauche), reste assombri, double page = moitié droite puis gauche | « clairement beaucoup plus immersif… je préfère nettement » |
| Webtoon : Solo Leveling Ragnarok ch.1 p.26-30 | la case remplit la LARGEUR ; plus haute que l'écran → défilement de haut en bas ; fondu 0,3 s entre pages | « moins immersif, moins d'effet… pas mauvais » → garder le choix |

**Exigences Quang (22/09 23h58)** : l'actuel est CONSERVÉ, case par case est un mode EN PLUS ; choix **mémorisé** ; **mode par défaut**
réglable ; appliqué aux **nouveaux chapitres / nouvelles séries**, à **tous les chapitres**, au **lot** (« Tout traiter », suivi de nuit).
~~Défaut « Automatique » (cases si manga, page si webtoon)~~ → **ANNULÉ par Quang le 23/09 à 00h08** : « finalement, je me ravise même
pour les webtoons : c'est quand même plus immersif, le deuxième mode ». ⇒ **DÉFAUT = CASE PAR CASE pour TOUS les formats** ; le mode
« page entière » reste au choix (par série, ou en défaut général). Le mode cases ADAPTE sa caméra au format (manga : de case en case ;
webtoon : pleine largeur + défilement).

## Ce qui existe déjà (ne pas refaire)

- **Scripts de la démo** : `scripts/demo_case_par_case/` — `cases.py` (blocs d'encre, démo seulement), `rendu_cases.py` (caméra
  manga : aperçu page 1 s puis case par case, temps ∝ √aire, glissé 0,5 s smoothstep, zoom 1→1,035, voile 170/255 hors case),
  `bandes.py` + `rendu_webtoon.py` (webtoon : contenu hors marges plein largeur, défilement tient 12 % / défile 76 % / tient 12 %),
  `yolo_cases.py`. Vidéos de référence (NON versionnées, planches protégées) : `scripts/demo_case_par_case/videos/`.
- **Vrai détecteur de cases** : `scripts/panel_yolo.py` + `scripts/models/manga_panel_detector_fp32.pt` (YOLO26n Manga109-s, classes
  `frame` et `text`, gratuit, local). ⚠ Python avec `ultralytics` = **`C:/Users/quang/Documents/ComfyUI/.venv/Scripts/python.exe`**
  (8.4.72). Le Python global ne l'a pas. Vérifier quel Python lance `video_lot.py` (proxy) avant d'y importer YOLO.
  ⚠ Sur webtoon, YOLO trouve peu de cases (sans bordure) — inutile : la capture (manga-fetch) découpe déjà UNE case par page.
- **Réglages vidéo à 3 niveaux** : défaut intégré (`scripts/suivi_nuit.py` `DEFAUT_INTEGRE`, `reglages_video`) < défaut GÉNÉRAL
  `sources/_profil_defaut.json` < profil de série `sources/<serie>/suivi.json`. Les clés passent par une LISTE BLANCHE dans le proxy
  (`_studio_llm_proxy.py`, autour de la ligne 7869 : `"precedemment": bool(reg.get("precedemment"))`) et `suivi_nuit.py` lignes 101-110 / 244-260.

## Plan (ordre conseillé)

1. **Détection** : `scripts/cases_video.py` = cases ordonnées d'une page, avec cache `sources/<serie>/ch_N/cases.json` (empreinte =
   taille+mtime de chaque page ; recalcul si la page change — cf. incident Claymore v2.4.6 : les pages sont remplacées SOUS LE MÊME NOM).
   Manga : YOLO `frame` (ordre : rangées haut→bas, droite→gauche ; double page W>H = moitié droite puis gauche ; 1 seule case ≈ page
   = pas de caméra). Webtoon : `bandes()`. **Format** : webtoon si le chapitre porte `manifest.decoupe` (manga-fetch) OU médiane
   h/w des pages ≥ 2,5 ; sinon manga.
2. **Moteur vidéo** `scripts/video_chapitre.py` : nouveau réglage **`camera` = "page" | "cases"** (défaut **"cases"**, décision Quang 23/09 00h08 ; l'adaptation manga/webtoon est INTERNE au mode cases).
   GARDER le pipeline actuel (ASS pour les sous-titres/karaoké = taille auto sur texte long, mixage audio, NVENC) : seul
   `clip_page()` change pour une page en mode cases → clip rendu image par image (PIL `Image.transform(EXTENT)` comme la démo, ou
   filtre ffmpeg `crop` animé). La DURÉE d'une page ne change pas (voix/vitesse + 0,45 s, muette 2,5 s) → audio et karaoké identiques.
   **Empreinte** (`empreinte()`, clé `reglages`) : n'y inclure `camera` QUE si ≠ "page" (comme `precedemment`), sinon toutes les
   vidéos existantes passeraient « à refaire ». Nom de fichier lisible (proxy `_video_nom`) : ajouter « cases » si mode cases.
3. **Proxy** (patch rejouable `proxy-patch/patch_camera.py` + `.diff`, sur le modèle de `patch_cache_pages.py`) : `camera` dans la
   liste blanche des réglages + raison « à refaire » (« le mode de caméra a changé »). Tester sur **8191** (`scripts/proxy_8191.py
   <copie>`) PUIS 8190 via `powershell -File C:/Users/quang/Documents/ComfyUI/relance-proxy.ps1 -Qui manga-studio -Pourquoi "..."`.
   ⚠ Le proxy est partagé avec Generate Studio : relire le fichier juste avant de patcher, `.bak` d'abord.
4. **suivi_nuit.py** : `camera` dans `reglages_video` (3 niveaux) + `reglages_video_voulus` / `video_a_faire` (comparaison des clés).
5. **App** `manga_studio.html` (v2.5.0) : sélecteur « Caméra : Case par case / Page entière » partout où les réglages
   vidéo se choisissent (fabrication d'une vidéo, profil de série, défaut général ⭐) ; + le LECTEUR si Quang dit oui (question en tête).
   `node --check` sur le JS après édition (règle : une apostrophe = tous les boutons morts). Version bumpée aux 3 endroits
   (`<title>`, `#verBadge`, `const VERSION`).

## Définition de « fini » (tout vérifié soi-même, jamais « teste de ton côté »)

- Vidéo réelle en mode cases sur un chapitre manga ET un webtoon, contrôlée à l'œil (images extraites, réduites ≤ 1800 px avant lecture).
- Vidéo en mode "page" **identique** à avant (même empreinte → pas « à refaire ») — mutation : casser la condition, exiger du rouge.
- Défaut « case par case » + forçage par série + défaut général : mémorisés après relance du proxy ; « Tout traiter » et le suivi de
  nuit respectent le mode (banc sur une série de TEST cachée `sources/_essai-.../`, jamais la bibliothèque de Quang).
- Bancs existants toujours verts (`scripts/test_video_ui.py <port>`, `test_profil_ui.py`, `test_chaine.py`…).
- ⛔ **Bibliothèque de Quang intouchable** (demande explicite 22/09) : tout essai dans un dossier `sources/_xxx` (ignoré par l'app,
  le suivi et la file vidéo), copié depuis ses séries, supprimé après ; ne supprimer QUE ce qu'on a créé.
- Livraison sur le téléphone de Quang = Telegram (chat `5867229613`, bot `JARVIS_TELEGRAM_BOT_TOKEN` dans `jarvis/.env`) ; ⚠ envoyer
  via Python `requests` (curl sous Windows casse les accents de la légende : « strings must be encoded in UTF-8 »).

## Pièges déjà payés (22-23/09)

- `video_chapitre.py --sortie x.mp4` écrit QUAND MÊME `<tag>.progress.json` dans `sources/<chap>/video/` → travailler sur une copie.
- Démo manga : détection par blocs d'encre = 2 cases fusionnées (OPM p.6) et bandes absurdes sur double page → YOLO pour le vrai.
- Sous-titres dessinés à la main = débordement sur les pages à longue narration → garder l'ASS de l'app.
- Limite assumée : le temps passé sur une case suit sa TAILLE, pas la phrase dite (caler sur la parole = autre étape, non demandée).

## Hors de ce chantier (ne pas mélanger)

Prospection auteurs (`ETUDE-outil-auteurs.md`, point prévu jeudi 24/09 au soir) ; mesure « taille des images envoyées » (déjà réduite
à 1000 px depuis le 21/09 — rien à gagner, sauf les doubles pages 3840 px dont les bulles deviennent minuscules : à signaler seulement).
