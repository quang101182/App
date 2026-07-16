# HANDOFF — Dashboard Monitoring (Se7en AI)
Lot: R10 · 2026-07-16 · Claude (Opus 4.8) → prochain moteur

> Chantier : **refonte complète du dashboard monitoring** — reconstruction propre « à côté »
> (`monitoring-v2.html`), prod intact jusqu'à bascule. Codex disponible en 2e moteur exécutant
> (Quang relaie manuellement). Contrainte transverse : **économie de tokens Claude** — Claude cadre
> et valide (léger), Codex code (lourd).

## 🎯 Objectif courant
Découper puis faire implémenter par Codex `App/monitoring/monitoring-v2.html` (single-file, config-driven),
en respectant le mock-up validé, SANS toucher le prod (`App/monitoring/index.html` v1.23.0).

## 📚 Références (LIRE avant de coder — hors git, sous le parent 02-Apps-Web)
- `D:/Download/02-Apps-Web/dashboard-refonte/DASHBOARD-REFONTE-ROADMAP.md` — **feuille de route figée**
  (Règle d'or + décisions verrouillées + phasage P0→P6 + pièges). Source de vérité du chantier.
- `D:/Download/02-Apps-Web/dashboard-refonte/MOCKUP-v0.2.html` — **direction visuelle VALIDÉE** (Quang 16/07).
- Prod actuel : `App/monitoring/index.html` v1.23.0 (revenue, auth-gaté via `dash.se7enai.com` proxy-live).

## ✅ Fait (vérifié)
- Quick win **v1.23.0** (fusion onglet se7+acquisition + 3 familles nav) — déployé, testé, live.
- Audit exhaustif du dashboard (chiffré) + **palette produit validée** daltonisme.
- Mock-up v0.1 → **v0.2 VALIDÉ par Quang le 16/07** (titre « Se7en AI » recollé + fresh-bar partout + polish).
- **Feuille de route figée** (roadmap ci-dessus) + Règle d'or.
- **Découpage en lots Codex-ready** défini (voir ci-dessous). Aucune ligne de v2 encore écrite.

## ⏳ Reste à faire — LOTS (chaque lot = 1 brief autoportant relayé à Codex)
- **LOT 1 — P0 Socle** : créer `App/monitoring/monitoring-v2.html` single-file. Squelette + tokens CSS inline
  (palette : dk `#2f80d8` · swp `#ec4899` · sv `#c77d0a` · accent `#3aa0ff` · good `#22c55e`/warn `#f5b52e`/crit `#ef4444`).
  Shell nav sidebar↔drawer responsive (3 familles), routeur par hash, moteur `fetchApp(cfg, signal)` config-driven `APPS[]`,
  composants `KpiTile`/`Panel`(accordéon)/`FunnelBar`/`ProductCard`/`Alert`/`FreshBar`. Vues en placeholder.
  **DoD** : nav OK, responsive PC+mobile, **fresh-bar sur CHAQUE vue**, 0 erreur console, aucune vraie donnée branchée.
- **LOT 2 — P1 Acquisition** (token-less) : porter l'onglet fusionné v1.23.0. **DoD** : chiffres = prod.
- **LOT 3 — P2 Home** : hero KPI cross-studio + grille produits + funnel global + alertes (dépend LOT 2).
- **LOT 4 — P3 Produits** : swp + sv d'abord, DictoKey en dernier (panneaux accordéon). Token-gated.
- **LOT 5 — P4 Ops** : Factory + Studio.
- **LOT 6 — P5 Bascule** (Claude + Quang, PAS Codex) : tests parité prod↔v2, repointer proxy `se7enai-dash`, surveiller 48h.

## ⚠️ Pièges à NE PAS répéter
- **`git add -A` INTERDIT dans le repo `App`** : 5 fichiers modifiés concurrents non liés (api-gateway-pro,
  noteflow, subwhisper-pro, promoclip) + untracked (APKs, logs). TOUJOURS `git add <fichier>` un par un.
- **NE PAS casser le revenue** : prod servi jusqu'à P5. v2 développé en parallèle. Bascule = repointer proxy (réversible, 1 commit).
- **Parité AVANT bascule** : chaque vue v2 doit afficher EXACTEMENT les mêmes chiffres que le prod (Playwright côte à côte).
- **ZÉRO FREESTYLE** : respecter l'esprit du mock-up validé. Meilleure idée → la PROPOSER en texte à Quang, ne pas l'imposer.
- **Fresh-banner / pas d'auto-fetch** : refresh manuel uniquement (sinon spam réseau + coût).
- **Mobile réel** : Playwright `is_mobile=True`, vérifier `scrollWidth==clientWidth`.
- **Tokens conservés** : dk/swp/sv token-gated ; home/acquisition token-less (données publiques uniquement).
- **Codex ne fait JAMAIS** : git · mémoire · deploy · MCP. Il code le HTML, Claude/Quang gèrent le reste.

## ➡️ Prochaine étape UNIQUE
Rédiger le **brief complet du LOT 1 (P0 Socle)** pour Codex (objectif + fichiers de contexte + contraintes + DoD),
le passer à Quang qui le relaie à Codex.

## 🛠 Actions hors-code à faire par Claude (si applicable)
- **Mémoire** : à jour côté `projet-site-web-public.md` (recall) — le chantier dashboard est aussi tracé ;
  au retour d'un lot livré, noter l'avancement dans le topic monitoring/dashboard.
- **Déploiement** : AUCUN tant que P5 non atteint (prod intact). La bascule = repointer proxy `se7enai-dash`.
- **Notifications** : livrables visuels → Telegram (Quang sur Honor). Docs/roadmap → terminal (ne pas auto-push).
- **Serveurs** : rien à redémarrer pour ce chantier.
