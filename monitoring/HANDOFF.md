# HANDOFF — App/monitoring
Lot: R10 · 16 juillet 2026 · Codex API → prochain moteur

## Objectif courant

Porter l'acquisition publique de `index.html` v1.23.0 dans `monitoring-v2.html`, avec les mêmes chiffres, sans token et sans modifier la production.

## État actuel

- Refonte développée en parallèle dans `monitoring-v2.html`; `index.html` v1.23.0 reste la production.
- Direction visuelle validée : `D:/Download/02-Apps-Web/dashboard-refonte/MOCKUP-v0.2.html`.
- Feuille de route figée : `D:/Download/02-Apps-Web/dashboard-refonte/DASHBOARD-REFONTE-ROADMAP.md`.

## Fait vérifié

- Commit `3e43f0c` : LOT 1 / P0 Socle livré.
- `monitoring-v2.html` contient les tokens CSS validés, navigation desktop/sidebar et mobile/drawer, 7 routes par hash, `APPS[]`, `fetchApp(cfg, signal)`, et les composants `KpiTile`, `Panel`, `FunnelBar`, `ProductCard`, `Alert`, `FreshBar`.
- Fresh-bar présente sur chaque vue ; aucun endpoint réel n'est configuré ni appelé ; aucun token n'est exposé ; `index.html` est inchangé.
- Syntaxe JavaScript, contrats P0 statiques et `git diff --check` validés.

## Reste à faire

- LOT 2 / P1 Acquisition : migrer la vue acquisition token-less et prouver une stricte parité de chiffres avec la production.
- LOT 3 / P2 Home : KPI agrégés, cartes produit, funnel global et alertes après P1.
- LOT 4 / P3 Produits : SubWhisper Pro et StoryVoice, puis DictoKey en panneaux accordéon ; tokens obligatoires.
- LOT 5 / P4 Ops : Factory et Studio.
- LOT 6 / P5 Bascule : parité globale, repointage du proxy par Claude/Quang, surveillance 48 h.

## Pièges à ne pas répéter

- Ne jamais toucher `index.html` ni le proxy avant P5 : le dashboard production génère du revenu.
- Ne jamais lancer `git add -A` dans le dépôt `App` : modifications et fichiers non suivis concurrents existent dans des projets frères. Indexer uniquement les fichiers du lot.
- Respecter le mock-up validé ; toute divergence de principe doit être proposée à Quang, jamais imposée.
- Refresh manuel uniquement : pas d'auto-fetch. Garder l'isolation et les tokens pour DictoKey, SubWhisper Pro et StoryVoice.
- Avant bascule, comparer chaque chiffre v2 à la production. Vérifier le mobile réel (`scrollWidth === clientWidth`).
- Le test visuel P0 navigateur n'a pas été exécuté : l'accès local `file:` était bloqué par la politique du navigateur. Cette limitation ne valide pas le rendu PC/mobile.

## Prochaine étape unique

Exécuter LOT 2 / P1 Acquisition dans `monitoring-v2.html`, sans données protégées ni changement de production, puis vérifier la parité des chiffres avec `index.html`.

## Actions hors-code à faire par Claude

- Mémoire : consigner le LOT 1 livré et le départ du LOT 2 dans le suivi monitoring/dashboard.
- Déploiement : aucun avant P5 ; ne pas redémarrer de serveur.
- Notifications : aucune obligatoire pour cette consolidation ; envoyer une capture sur Telegram uniquement après validation visuelle demandée.
