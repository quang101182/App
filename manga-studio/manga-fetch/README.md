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
4. **Journal** : chaque action s'ajoute à `%LOCALAPPDATA%\manga-fetch\fetch.log` (jsonl, horodaté).
5. La capture est **chapitre par chapitre, à la main de Quang** : pas de crawl automatique de
   séries ni de contournement de protections — c'est la ligne tenue depuis le début du chantier.

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
