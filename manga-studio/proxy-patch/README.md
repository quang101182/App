# Ce que Manga Studio ajoute au proxy Generate Studio

## Pourquoi ce dossier existe

L'app est dans ce dépôt. **Ce dont elle dépend ne l'est pas.**

Le moteur qu'elle consomme vit hors dépôt, dans `C:\Users\quang\Documents\ComfyUI\` :

| Fichier | Rôle |
|---|---|
| `_studio_llm_proxy.py` | le proxy 8190 (~60 routes) — sert l'app, relaie ComfyUI |
| `_studio_db.py` | le store SQLite partagé (`studio_content.db`) |

Ce dossier **n'est sous aucun git** (vérifié le 26/07 : `git rev-parse` échoue, et aucune copie ailleurs
sous `02-Apps-Web`). Sans les diffs ci-dessous, une réinstallation ferait tomber l'app **sans que rien
n'indique pourquoi** : le HTML serait intact, et toutes ses routes répondraient 404.

C'est le même angle mort que celui relevé la session précédente sur `App/demosaic-pipeline/`.
On le comble ici plutôt que de le signaler une deuxième fois.

## Les deux diffs

| Fichier | Contenu |
|---|---|
| `_studio_db.diff` | schéma **v3** : tables `manga_projects` / `manga_pages` / `manga_panels` + leur CRUD + `_uid()` |
| `_studio_llm_proxy.diff` | constantes `MANGA_*`, `manga_harvest()`, `manga_files()`, `_manga_safe()`, les routes `/manga/*`, le service du HTML sur `/manga` |
| `_studio_llm_proxy_crop_ref.diff` | `MANGA_CROP` + `manga_crop_ref()` + la route `POST /manga/crop_ref` — le recadrage d'une image de référence sur le visage (v1.53.0). Sans lui, l'app perd le recadrage **en silence** : elle garde l'image entière et le dit dans le journal, mais rien à l'écran n'indique qu'une brique manque |
| `_studio_llm_proxy_sources.diff` | `MANGA_SOURCES` + `manga_sources()` / `manga_source_pages()` / `_manga_src_safe()` + les routes **lecture seule** `GET /manga/sources`, `/manga/source_pages?d=`, `/manga/source_file?p=` (v1.66.0, onglet Chapitres). Sert les chapitres déposés par `manga-fetch` dans `sources/` (gitignoré, jamais versionné). `serve_manga_file` gagne un paramètre `sources=` ; aucune autre route touchée |
| `_studio_llm_proxy_narration.diff` | `MANGA_NARRATE` + `manga_narrations()` / `manga_narration()` / `manga_narrate()` / `manga_narration_note()` + `GET /manga/narrations?d=`, `GET /manga/narration?d=&tag=`, `POST /manga/narrate` (lance `scripts/narrate_chapter.py` en fond, venv kohya), `POST /manga/narration_note` (v1.67.0). `/manga/source_file` ne sert plus que images + `.mp3` sous `sources/`. Un run lance avant un redemarrage du proxy est reconnu vivant par la fraicheur de son `progress.json` (< 3 min) |
| `_studio_llm_proxy_gemini.diff` | v1.68.0 : `manga_narrate` accepte le moteur `gemini` (defaut depuis le banc de fidelite du 21/09). Une ligne. |
| `_studio_llm_proxy_capture.diff` | v1.71.0 : capture DANS l'app, en ENVELOPPANT manga-fetch (jamais modifie d'ici) : `GET /manga/fetch_tabs` (onglets de la fenetre dediee, CDP 9223), `POST /manga/fetch_edge` (launch-edge), `POST /manga/fetch_capture` (onglet DEVANT figurer dans la liste reelle -> `--tab <url>`, `--force` seulement si remplacement confirme), `GET /manga/fetch_status` (progression = lignes `[page]` d'events.log ; code 3 = reussite avec avertissements), `POST /manga/fetch_verify`. Remplacement PROTEGE : l'ancien chapitre est mis de cote (`_remplace_ch_N_<ts>`), supprime si la capture reussit, RESTAURE sinon (manga-fetch `--force` laissait des pages orphelines) |
| `_studio_llm_proxy_couts.diff` | v1.72.0 : `GET /manga/costs` = suivi des couts (somme des stats MESUREES des narration.json + bancs de fidelite ; reutilisation de lecture = tout sauf noms+lecture ; consensus = fusion seule ; date = created_at sinon mtime). Recoupe a l'identique par un calcul independant (5,332 $ le 21/09). |
| `_studio_llm_proxy_precedemment.diff` | v1.94.0 (`patch_precedemment.py`) : `GET/POST /manga/precedemment` (« Précédemment… » et rattrapage, `scripts/precedemment.py` en fond), poste de coût `precedemment` (corbeille comprise), cellule d'activité. |
| `_studio_llm_proxy_pwa.diff` | v1.95.0 (`patch_pwa.py`) : `/manga/manifest.webmanifest`, `/manga/sw.js`, `/manga/icon-*.png` PUBLICS (liste fermée, fichiers de `pwa/`, aucun secret), `/manga` → 302 `/manga/` (portée de la PWA). |
| `_studio_llm_proxy_video_prec.diff` | v1.95.1 (`patch_video_prec.py`) : réglage vidéo `precedemment` (liste blanche + raison « à refaire »), `_video_nom()` = nom lisible du fichier téléchargé (`filename*` UTF-8 + repli ASCII). |
| `_studio_llm_proxy_videos_zip.diff` | v1.97.0 (`patch_videos_zip.py`) : `GET /manga/videos_zip?serie=&d=ch_1,ch_2` = les vidéos choisies en UNE archive .zip en flux (MP4 stockés, zip64). |
| `_studio_llm_proxy_suivi.diff` | v1.98.0 (`patch_suivi.py`) : `GET/POST /manga/suivi` (réglage `sources/<série>/suivi.json`, file, estimation, dernier passage) et `POST /manga/suivi_lancer` (`scripts/suivi_nuit.py` en fond). |
| `_studio_llm_proxy_pilote.diff` | v2.0.0 (`patch_pilote.py`) : télécommande de la fenêtre de capture — `GET /manga/pilote_onglets`, `GET /manga/pilote_ecran?id=` (JPEG), `POST /manga/pilote` (clic, molette, touche, texte, url, retour, avant, recharger, activer, fermer, nouvel) ; client CDP `scripts/cdp_mini.py`. |
| `_studio_llm_proxy_suivi_moteur.diff` | v2.0.0 (`patch_suivi_moteur.py`) : le suivi choisit son moteur (kimi | gemini), estimation selon le moteur. |
| `_studio_llm_proxy_resume.diff` | v2.1.0 (`patch_resume.py`) : `GET /manga/resume` = ce que chaque chapitre (narrations avec voix, voix, karaoké, vidéo, traductions, Précédemment) et chaque série (musique, suivi) possède. |
| `_studio_llm_proxy_langue.diff` | v2.2.0 (`patch_langue.py`) : `GET /manga/langue?d=` (détection MangaDex / pages, `scripts/langue_chapitre.py`), langue dans `/manga/resume`, `/manga/traduire` refuse la langue d'origine sans `force`. |
| `_studio_llm_proxy_capture_serie.diff` | v2.3.0 (`patch_capture_serie.py`) : `POST /manga/fetch_capture` relaie `suite` (0-50) / `jusqua` à manga-fetch v0.4.0 ; `GET /manga/fetch_status` suit la série (`chapitre` = celui EN COURS, `chapitre_depart`, `dossiers`, `serie` = bilan). « Remplacer » ne vaut que pour le 1er chapitre. Testé sur 8191 (`scripts/proxy_8191.py <copie>`) puis 8190. |
| `_studio_llm_proxy_capture_entiers.diff` | v2.3.2 (`patch_capture_entiers.py`) : `entiers` (bool) sur `POST /manga/fetch_capture` → `--sans-intermediaires` (manga-fetch v0.4.1), seulement en série. |
| `_studio_llm_proxy_profil.diff` | v2.4.0 (`patch_profil.py`) : `GET /manga/suivi` + profil effectif / plan / estimation (+ « refaire »), `POST /manga/suivi` normalisé (traduction), `GET/POST /manga/profil_defaut` (⭐ / ↺), `POST /manga/suivi_lancer {lot, chapitres, refaire}`, item « lot » dans `/manga/activite`. La logique vit dans `scripts/suivi_nuit.py` (rechargé à chaud). |
| `_studio_llm_proxy_sites.diff` | v2.3.3 (`patch_sites.py`) : `GET /manga/sites` = `manga-fetch/sites.json` (liste versionnée des sites validés pour la capture). Lecture seule. |
| `_studio_llm_proxy_renommer_reessai.diff` | v2.4.2 (`patch_renommer_reessai.py`) : renommer une série réessaie 12 fois sur 6 s quand Windows refuse (fichier ouvert : miniatures servies, antivirus) — WinError 5 vu par Quang le 22/09 ; sinon message clair (le titre est déjà enregistré, refaire le renommage le termine). |
| `_studio_llm_proxy_cache_pages.diff` | v2.4.6 (`patch_cache_pages.py`) : `serve_manga_file` (pages, MP3) n'est plus « immuable par nom » : ETag (date + taille), `Cache-Control: no-cache`, 304 si inchangé. Incident Claymore 22/09 : chapitre supprimé puis recapturé = mêmes noms de pages → le navigateur montrait les 62 anciennes pages anglaises pendant 24 h. Le service worker v2.4.6 force aussi la revalidation (`cache: "no-cache"`). |
| `_studio_llm_proxy_interrompre_v2120.diff` | v2.12.0 (feuille de route 4-undecies) : `POST /manga/interrompre` -> `manga_interrompre()` charge `scripts/interruption.py` a chaud (arret propre du lot / des narrations / des traductions + bilan). Sans lui, « Interrompre et basculer » repond une erreur et le mode ne change PAS (l'app le dit). |
| `_studio_llm_proxy_vram_v2130.diff` | v2.13.0 : `GET /manga/vram` -> `manga_vram()` charge `scripts/vram_parts.py` a chaud (VRAM ventilee par moteur). Sans lui, l'app retombe sur l'ancienne barre d'une seule couleur (`/vram`). |

**Ce sont des ajouts purs.** Aucune ligne existante de Generate Studio n'est modifiée : les diffs ne
contiennent que des `+`, à l'exception de la ligne `SCHEMA_VERSION = 2` → `3` et de l'ajout de `shutil`
à la liste d'imports.

## Réappliquer

```bash
cd /c/Users/quang/Documents/ComfyUI
cp _studio_db.py _studio_db.py.bak
cp _studio_llm_proxy.py _studio_llm_proxy.py.bak
patch -p0 < .../proxy-patch/_studio_db.diff
patch -p0 < .../proxy-patch/_studio_llm_proxy.diff
python -c "import ast; ast.parse(open('_studio_db.py',encoding='utf-8').read())"
```

Puis relancer l'agent (il est idempotent, il ne touche pas au tunnel) :

```powershell
Stop-Process -Id <pid du proxy> -Force
wscript.exe "C:\Users\quang\Documents\ComfyUI\launch-generate-agent.vbs"
```

La migration de schéma est **idempotente** : `init_db()` crée les tables manquantes au boot, sans
toucher aux données existantes (vérifié le 26/07 — prompts 180, galerie 47, favoris 3 intacts après
passage en v3).

## Piège payé le 26/07

Réécrire `_studio_db.py` avec `open(p,'w')` en Python **sur Windows** convertit tout le fichier en CRLF
(il était en LF) : le diff passe de 247 à 983 lignes et devient illisible. Utiliser `newline=''`, ou
écrire en binaire. Aucun effet fonctionnel, mais ça détruit la lisibilité de toute comparaison future.

## 🔴 Le secret du gateway a été exposé — et il doit être CHANGÉ (28/07/2026)

`_studio_llm_proxy.diff` portait le `WORKER_SECRET` **en clair** dans une ligne de contexte,
dans un dépôt **public**. ⚠️ Et ce n'est pas né avec le manga : `git log --all -S` remonte au
**7 mars 2026**, sur **15 commits** — dont un du 9 mars intitulé *« security: remove tracked
secrets »*, preuve que la fuite avait déjà été traitée une fois **et qu'elle est revenue**. Cinq scripts de `scripts/`
l'avaient aussi en dur. Tout est retiré depuis le 28/07 : les scripts lisent `WORKER_SECRET`
dans l'environnement, ou `ComfyUI/.worker_secret` (hors dépôt), et s'arrêtent en le disant s'il
manque.

⚠️ **Retirer un secret d'un fichier ne le retire pas de l'historique git.** Il reste lisible
dans les commits précédents, sur un dépôt public. La seule remédiation réelle est de **changer
le secret côté gateway Cloudflare** — décision de Quang, parce que ce secret est partagé avec
d'autres applications et que le faire tourner les impacte toutes.
