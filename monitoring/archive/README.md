# Archive — dashboard monitoring v1

## `index-v1.23.0.html`

L'**ancien dashboard monitoring** (v1.23.0, dernier commit fonctionnel `1546c70`), servi sur
`dash.se7enai.com` jusqu'à la **bascule P5 du 16/07/2026**. Depuis, la racine sert
`monitoring-v2.html` (refonte complète, 7 vues portées, parités prouvées vue par vue).

**Archivé le 18/07/2026**, après les 48 h de surveillance prévues par la roadmap — au cours
desquelles une régression a été trouvée et corrigée (P3b2b, le détail par appareil au clic).

## ⚠ Ce fichier est TOUJOURS le filet de rollback — il a juste changé d'URL

Le worker `se7enai-dash` relaie **n'importe quel chemin** vers github.io (seul `/` est réécrit
vers la v2). L'archivage ne l'a donc pas débranché :

| Avant le 18/07 | Depuis le 18/07 |
|---|---|
| `dash.se7enai.com/index.html` | `dash.se7enai.com/archive/index-v1.23.0.html` |

Les tokens y sont **toujours injectés** par le worker (c'est du HTML) → la page est pleinement
fonctionnelle, pas une coquille morte.

## Rollback complet (repointer la racine sur la v1)

`se7enai-hub/dash-worker/src/inject.js` l.22 — remplacer `"/monitoring-v2.html"` par
`"/archive/index-v1.23.0.html"` puis :

```bash
cd D:/Download/02-Apps-Web/se7enai-hub/dash-worker
export CLOUDFLARE_API_TOKEN="cfut_..."   # token « claude-factory », cf _quickref.md
npx wrangler deploy --config ./wrangler.toml
```

⚠ Toujours `--config ./wrangler.toml` (2 incidents de worker déployé au mauvais endroit).
Le worker **n'est pas versionné** (`se7enai-hub` n'est pas un dépôt git) — un `.bak` horodaté
`src/inject.js.bak-pre-p5-*` sert de filet.

## Bugs connus de cette v1 — corrigés en v2, jamais dans ce fichier

Si un rollback est déclenché, ces défauts **reviennent** :

- **Perf TikTok mensongère** : « 82 226 vues » sous le libellé « boostées exclues » alors que le
  filtre ne les exclut pas → **81,5 % des vues affichées sont achetées**.
- **Filtre premium DictoKey** : `getDeviceCategory()` oublie `tier === 'premium'` en KV → 16 pills
  au lieu de 18, et ces appareils disparaissent si on décoche « free ».
- **Fuite Chart.js** (`window._cLatency` jamais détruit), **fetch sans `signal`** (jusqu'à 50
  requêtes en vol), **`J+N` faux d'un jour**, **backlog Studio filtré au tiers**.
- **Rétention « 0 % » en rouge** sur des cohortes d'une seule personne.
- **`0 %` de conversion du bandeau bulle** — un chiffre qui ne mesurait rien (le param était
  `(not set)`, cf `putBoolean` droppé par Firebase côté app).

Détail complet : `../HANDOFF.md` et `dashboard-refonte/DASHBOARD-REFONTE-ROADMAP.md` §8.
