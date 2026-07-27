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
