# manga-fetch — sourcing de chapitres pour Manga Studio

> **v0.1.0 — 21/09/2026.** Module autonome : il remplit `sources/` avec des pages de chapitres,
> la narration (volet Manga Studio) consomme derrière. Conçu pour être intégré par une session
> Claude sans contexte supplémentaire : tout est ici.

## Les 3 canaux (et pourquoi ceux-là — tout a été mesuré le 21/09/2026)

| Canal | Commande | Ce qu'il couvre |
|---|---|---|
| **MangaDex** | `download` | Séries non licenciées (découverte). API publique, anonyme. Les titres licenciés (Bleach, DBS, OPM Murata, Claymore, Noritaka) n'y ont **0 chapitre** — mesuré. |
| **Capture** | `capture` | **TOUT lecteur web** affiché dans la fenêtre Edge dédiée. C'est le canal principal : la fenêtre navigateur EST la source (décision Quang 21/09). |
| **Import** | `import` | Images/CBZ déjà sur disque (scans de tomes possédés, etc.). |

**MANGA Plus : retiré, mesuré mort pour nous** (21/09) — le viewer web refuse même le guest token
généré par le site (« Invalid user access »), et le login n'existe que dans l'app mobile. Ne pas
y revenir sans nouvelle donnée. Le script obsolète `mangaplus_sniff_token.py` a été retiré.

## Installation

```bash
python -m venv "%LOCALAPPDATA%\manga-fetch\venv"
%LOCALAPPDATA%\manga-fetch\venv\Scripts\pip install requests playwright
```

## Usage

```bash
PY=%LOCALAPPDATA%\manga-fetch\venv\Scripts\python.exe

# Fenêtre dédiée (une fois par session PC ; profil persistant, port CDP 9223)
%PY% manga_fetch.py launch-edge

# 1. MangaDex : chercher, lister, télécharger
%PY% manga_fetch.py search "solo leveling"
%PY% manga_fetch.py chapters <manga_id> --lang fr
%PY% manga_fetch.py download <manga_id> --last 3 --lang fr

# 2. Capture : ouvrir le chapitre dans la fenêtre dédiée, puis
%PY% manga_fetch.py capture --title "Dragon Ball Super" --chapter 104

# 3. Import
%PY% manga_fetch.py import "D:\scans\bleach_t42" --title "Bleach" --chapter 367

# Contrôle d'intégrité (utilisé par le banc, utile pour l'intégration)
%PY% manga_fetch.py verify sources/<slug>/ch_104
```

## Sortie normalisée

```
sources/<slug>/ch_<num>/
    page_001.jpg, page_002.png, ...
    manifest.json    { slug, title, chapter, source, source_url, captured_at, pages[], notes[] }
```

- `pages[]` porte `bytes` (toujours) et `w`/`h` (capture uniquement).
- `notes[]` signale les pages échouées ou suspectes (< 5 Ko).
- L'extension est déduite des magic bytes, jamais de l'URL d'origine.

## Règles du chantier (à respecter par toute session qui touche ce module)

1. **`sources/` est gitignoré et le restera** : des images de chapitres sous licence ne vont
   JAMAIS dans le dépôt `App/` (public). Seul le code est versionné.
2. **Aucun secret** : ce module n'a pas de token (MangaDex est anonyme, la capture utilise la
   session de la fenêtre dédiée, l'import est local). Le jour où un canal en exigerait un, il vit
   dans `%LOCALAPPDATA%\manga-fetch\`, jamais ici.
3. **La fenêtre dédiée** (`%LOCALAPPDATA%\manga-fetch-edge`, port 9223) est séparée du navigateur
   de Quang. On la tue par user-data-dir, **jamais** en masse (`taskkill /IM msedge.exe` interdit).
3-bis. **La fenêtre dédiée doit rester AFFICHÉE** (même derrière d'autres fenêtres), jamais réduite : mesuré le 22/09,
   réduite la capture réussit mais la fenêtre RÉAPPARAÎT (l'onglet est mis au premier plan, sinon Edge le freine) et
   l'écran du pilotage met 1 à 2 min. Quang : solution fiable ou rien — pas de fenêtre hors écran ni autre bricolage.
3-ter. **Taille et place (mesuré le 24/09, v0.6.4)** : sous ~**576 × 774 px intérieurs** (MangaDex, page par page) le site
   n'affiche plus la page → « aucune image détectée ». Minimum retenu avec marge : **700 × 950** (contrôle avant chaque
   capture dans l'app, bouton « Taille sûre »). La fenêtre s'OUVRE à la place choisie par Quang (sur le côté, ~93 % sous
   l'écran) : capture normale (MangaDex 18/18 en 33 s, webtoon 7/7 en 28 s) — partiellement hors écran ≠ réduite.
   Place : `%LOCALAPPDATA%\manga-fetchenetre.json` (boutons « Ranger » / « Retenir » de l'app). Banc :
   `banc_taille_fenetre.py`. ⚠ Raijin Scans renvoie vers son Discord (constaté 24/09) : site fermé.
4. **Journal** : chaque action s'ajoute à `%LOCALAPPDATA%\manga-fetch\fetch.log` (jsonl, horodaté).
5. ~~La capture est **chapitre par chapitre, à la main de Quang** : pas de crawl automatique de
   séries ni de contournement de protections — c'est la ligne tenue depuis le début du chantier.~~
   → **levée par Quang le 22/09/2026** (*« elle a sauté depuis longtemps […] je l'utilise à titre
   privé, c'est mon problème »*) : v0.4.0 capture plusieurs chapitres d'affilée (§ ci-dessous).
   Usage privé : ne pas la réintroduire, ne pas rouvrir la question.

## Capture de plusieurs chapitres (v0.4.0, 22/09/2026)

`capture ... --chapter N --suite K` (les K suivants, ~~50~~ **300** max depuis 0.8.0) ou `--jusqua Y` (jusqu'au ch. Y inclus),
ou **`--jusqua-fin`** (0.8.0 : jusqu'au dernier chapitre paru sur le site — voir plus bas).
Après chaque chapitre, `chapitre_suivant()` amène **le même onglet** au suivant, site par site :

| Site | Enchaînement (vérifié en réel le 22/09) | Comment |
|---|---|---|
| **MangaDex** | ✅ OPM 302→304 (19/19/18 p.), 305→308, 310→311 | API publique `/manga/<id>/aggregate`, **dans la langue du chapitre lu** (le lecteur passe aussi seul au suivant, mais on ne s'y fie pas) |
| **MANGA Plus** | ✅ Claymore #002→#003 (39+39 p., contenus distincts) | aucun passage automatique, et le bouton « To Chapter #00x » ne réagit pas à un clic scripté → page de la série `/titles/<id>`, clic sur le chapitre, puis réouverture de son adresse (le lecteur se recharge juste après le clic) |
| **Sites à adresses `…/chapter-N/`** (WordPress « Madara » : raijin-scans.fr…) | ✅ Solo Leveling: Ragnarok VF ch.1→2 (v0.5.1) | les liens « chapter-N / chapitre-N » de la SÉRIE présents sur la page du chapitre (liste des chapitres) |
| autre | ❌ arrêt « non pris en charge » | — |

- Suivant = le plus petit numéro > au courant. **Un trou arrête la série** (« le chapitre 5 n'est pas
  disponible sur ce site ») sauf si `--jusqua` le couvre ; la borne dépassée arrête aussi, en le disant.
- ⚠ **MANGA Plus liste des chapitres qui ne s'ouvrent pas sur le web** : Claymore #004 est affiché
  gratuit mais son lecteur reste à « 1 / 0 » (API 200, zéro page ; #002 → 42). Détecté en 30 s à
  l'ouverture → arrêt avec la raison, au lieu d'un échec au bout de 2 min 30.
- Seul le 1er chapitre peut être remplacé (`--force`) ; un suivant déjà présent est **gardé** et la série continue.
- Bilan en fin de sortie : `SÉRIE : 3 chapitre(s) : 302, 303, 304 — arrêt : <raison>` ; code 3 si la
  demande n'a pas été tenue jusqu'au bout.
- Bancs : `scripts/test_capture_serie.py [port]` **27/27** (mutation « saute un chapitre » → 14/20 rouge),
  `scripts/test_capture_serie_ui.py [port]` **13/13** ; non-régression `test_manga_fetch.py` **9/9**.

## « Jusqu'au dernier paru » + sécurités de série (v0.8.0, 26/09/2026)

`--jusqua-fin` : aucune borne ; la série s'arrête quand le site n'a plus de suite (« aucun chapitre après le N », code 0 =
demande tenue) ou sur le « Final » du dernier chapitre (« série terminée », 0.7.5). Sécurités (le plafond de 50 a disparu) :

| Risque | Sécurité |
|---|---|
| tourner en rond | le suivant doit être **strictement plus grand** (sinon « arrêt de sécurité … retour en arrière ») |
| le site ressert le chapitre précédent | ≥ 80 % d'images **identiques** (sha1) au précédent → le chapitre est **mis de côté** (`_doublon_ch_N_<t>`, jamais effacé), arrêt, reprise au ch. N |
| un lien « suivant » qui part ailleurs | saut de **plus de 10** numéros (mode fin seulement) → arrêt, reprise au ch. proposé |
| solliciter le site trop vite | **pause de 3 s** entre deux chapitres (tous modes, chapitres sautés compris) |
| dernier filet | **300 chapitres** par lancement (tous modes), puis arrêt avec reprise |

Tous ces arrêts s'écrivent « arrêt de sécurité : <raison> — reprise au ch. N » (lu par le proxy pour la reprise) et dans
`events.log` (catégorie `sécurité`). Un chapitre **déjà là** est sauté sans être recapturé et listé à part :
ligne `DEJA LA : 2, 3` avant le bilan `SÉRIE`. Bancs : `scripts/test_serie_securites.py` **16/16** (mutation 15/16),
`scripts/test_dernier_paru.py` **19/19** (vraies captures MangaDex, mutation de l'app rouge).

## Webtoons (manhwa) : découpage automatique des bandes (v0.5.0, 22/09/2026)

Un webtoon arrive en BANDES de 800 × ~10 000 px (*Solo Leveling: Ragnarok* ch.1, MangaDex, 26 bandes). Telles
quelles, elles sont inexploitables en aval : un modèle de lecture les réduit à ~160 px de large, la détection des
bulles et la vidéo 9:16 aussi. ⇒ après chaque capture, `decouper_bandes()` coupe toute image > 3× plus haute que large
(`python manga_fetch.py decouper <dossier>` pour un chapitre déjà là ; idempotent). Bandes **recollées** d'abord (l'éditeur
coupe n'importe où), coupe dans une ligne **strictement** unie (écart ≤ 24 sur toute la largeur — la v1 ignorait 2 % des
pixels et coupait À TRAVERS des encadrés), gouttière la plus proche de 1,5× la largeur. Originaux dans `originaux/`.
Mesuré : 26 bandes → **129 pages** en 13 s, 5 coupes hors gouttière, **aucune dans du texte** (contrôle visuel des coupes) ;
narration Gemini de 12 pages : récit fidèle aux encadrés, 0,26 $. ⚠ **Traduction** : les encadrés de webtoon sont en
TEXTE BLANC SUR FOND NOIR → le relettrage (fait pour texte noir sur bulle blanche) les laisse en VO (ROADMAP § 28).
v0.5.1 : **avatars des commentaires** exclus (raijin-scans : 5 « pages » = avatars 736×1288 affichés en 50 px) — une page
est AFFICHÉE ≥ 180 px de large et hors zone de commentaires ; test « le bloc défile-t-il » fait dans les DEUX sens (un
onglet resté tout en bas faisait écarter le vrai bloc → « aucune image »). Raijin ch.2 : 12 coupes hors gouttière,
toutes dans du dessin (contrôle visuel).
v0.4.2 : le lecteur MangaDex en bande marquait `<body>` comme « bloc défilant » (overflow:auto) alors que c'est la fenêtre
qui défile → 2 pages sur 26 ; body/html ignorés et un bloc n'est retenu que s'il défile VRAIMENT.
⚠ Deux onglets sur la MÊME adresse : `--tab` prend le premier (ici celui de Quang, figé) — viser une adresse distincte.

## Lecteurs reconnus (v0.3.0, 21/09/2026)

| Affichage | Détection | Avance | Extraction |
|---|---|---|---|
| **Page par page** (MangaDex) | document ≈ hauteur d'écran, aucun bloc défilant | flèche → ; si rien : **clic à droite, puis à gauche** (sens japonais, MANGA Plus) — le côté qui marche est gardé | `fetch` du blob / `requests` |
| **Bande verticale dans la page** | document > 2,5 écrans | défilement de la fenêtre | idem |
| **Bande verticale dans un BLOC** (MANGA Plus vertical) | plus grand élément `overflow:auto/scroll` > 2,5× sa hauteur | défilement de CE bloc | `fetch` interdit (CSP) → **canvas** = pleine résolution, sans l'écran |

- Mesuré : BORUTO -TWO BLUE VORTEX- #001 (MANGA Plus vertical) **1 page → 52/52** en pleine
  résolution ; OPM 301 (MangaDex) **19/19** et Claymore 1 (MANGA Plus) **62/62**, inchangés.
- ⛔ **Capture de moins de 3 pages = ÉCHEC** (code 2, dossier retiré) : v0.2 déclarait
  « terminée pages=1 » quand le lecteur n'avançait pas.
- ⚠️ Avant v0.3.0, MANGA Plus était extrait par **capture d'écran** : taille d'affichage ET
  **barres du lecteur incrustées** en haut et en bas des pages (vu par Quang). Le screenshot reste
  le dernier recours, barres flottantes masquées pendant la prise. Claymore ch.1 (capturé avant, en
  affichage page par page) a été vérifié : 801×1200, **aucune barre** — seul le mode vertical les incrustait.

## Banc

```bash
%PY% test_manga_fetch.py
```

Test réel de bout en bout (download + capture du même chapitre MangaDex, contrôle croisé des
comptes de pages, mutation pour vérifier que `verify` crie) — verdict chiffré en sortie.
