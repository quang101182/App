# HANDOFF — App/monitoring
Lot: R9 · 16 juillet 2026 · Claude (Opus 4.8) → Codex (gpt-5.6-terra) pour P1, puis retour Claude

## Objectif courant

Refonte du dashboard monitoring « reconstruire à côté » : porter chaque vue de la prod `index.html` v1.23.0 vers `monitoring-v2.html` (config-driven, tokenisé, responsive), **sans toucher la prod**, en migrant onglet par onglet, bascule seulement à parité de chiffres vérifiée.

**Étape immédiate = LOT 2 / P1 Acquisition** : brancher la vue Acquisition (token-less, données publiques) dans `monitoring-v2.html`, chiffres STRICTEMENT identiques à la prod.

## Références figées

- Mock-up de direction VALIDÉ : `D:/Download/02-Apps-Web/dashboard-refonte/MOCKUP-v0.2.html`.
- Feuille de route mère : `D:/Download/02-Apps-Web/dashboard-refonte/DASHBOARD-REFONTE-ROADMAP.md` (§3 = phasage P0→P6).
- **Brief P1 détaillé (auto-suffisant, pour Codex) : `D:/Download/02-Apps-Web/dashboard-refonte/BRIEF-CODEX-P1-acquisition.md`** ← à lire et exécuter.

## Ce qui est fait (vérifié)

- **LOT 1 / P0 Socle** livré (`monitoring-v2.html` v2.0.0-P0.1). Socle Codex (`3e43f0c`) + fix bloquant Claude (shadowing `refresh` dans `route()` → `forceRefresh`).
  - Config `APPS[]`, nav desktop/sidebar + mobile/drawer, routeur par hash (7 vues), `fetchApp(cfg, signal)`, composants `KpiTile`/`Panel`/`FunnelBar`/`ProductCard`/`Alert`/`FreshBar`, tokens CSS palette validée.
  - Fresh-bar présente sur chaque vue ; aucun endpoint réel branché ; aucun token exposé ; `index.html` inchangé.
  - ✅ **Preuve runtime** (Playwright + `python -m http.server`, PAS `file:`) : home + 7 vues à froid rendues, **0 erreur console** PC(1280) ET mobile(384), fresh-bar=1/vue, `scrollWidth==clientWidth`.
- **P1 — préparation** (Claude, 16/07) : logique Acquisition prod extraite et **vérifiée ligne à ligne** contre `index.html` (lignes 2000-2114) → endpoints + formules consolidés dans le brief Codex. Extraction confirmée exacte (formules `pct`, funnel 6 étapes, 8 compteurs `api-gateway-pro`, cartes sites `outMode`).

## Ce qui reste à faire

- **P1 Acquisition (EN COURS)** : Codex exécute le brief (`BRIEF-CODEX-P1-acquisition.md`) → édite `monitoring-v2.html` uniquement, bump `v2.1.0-p1`. Puis Claude vérifie runtime + parité chiffres v2 vs prod. **DoD** : chiffres identiques au prod.
- **P2 Home** : hero KPI agrégés + grille produits + funnel global + alertes, sur vraies données. **DoD** : agrégats corrects vs somme des apps.
- **P3 Produits payants** : SubWhisper Pro + StoryVoice d'abord (simples), DictoKey en dernier (le plus riche) en panneaux accordéon. Tokens obligatoires. **DoD** : parité KPI + non-régression.
- **P4 Ops** : Factory + Studio. **DoD** : parité.
- **P5 Bascule** : parité globale prod vs v2 → repointer le proxy `se7enai-dash` sur v2 → surveiller 48 h → archiver l'ancien. Réversible (repointer = 1 commit).
- **P6 Hygiène** : supprimer code mort, changelog.

## Pièges à ne pas répéter

- **Ne JAMAIS toucher `index.html` ni le proxy avant P5** : le dashboard prod génère du revenu.
- **JAMAIS `git add -A` dans le dépôt `App`** : des modifs et fichiers non suivis concurrents existent dans des projets frères (`api-gateway-pro`, `noteflow`, `promoclip`, `subwhisper-pro`…). **Indexer fichier par fichier**, uniquement ceux du lot.
- **`node --check` ≠ preuve runtime** : le socle P0 ne s'affichait pas à cause d'un bug runtime (shadowing) invisible aux contrôles statiques. **Toujours** valider via `python -m http.server` + Playwright (`is_mobile=True`), **jamais `file:`** (bloqué par la politique navigateur). Vérifier `view-root` non vide sur CHAQUE vue à froid + `errors console == 0`.
- **Parité AVANT bascule** : comparer chaque chiffre v2 au prod côte à côte. Reproduire les formules EXACTEMENT (piège connu : funnel hub étape 5 « Waitlist » a pour base de conversion `cta`, PAS `vTot`).
- **Codex ne fait ni git, ni mémoire, ni déploiement, ni vérif visuelle** (son sandbox ne rend pas le navigateur). Il code ; Claude relit le `git diff`, teste le rendu, commit, met la mémoire à jour. « Commité + tests verts » ≠ « ça marche » → valider le FONCTIONNEL.
- **Fresh-bar obligatoire sur CHAQUE vue** (exigence forte Quang) + **refresh manuel uniquement**, pas d'auto-fetch (sinon spam réseau + coût).
- **Mobile réel** : Playwright `is_mobile=True` (pas `--window-size`), vérifier `scrollWidth === clientWidth`.

## Prochaine étape unique

Codex : lire `BRIEF-CODEX-P1-acquisition.md` et brancher la vue Acquisition dans `monitoring-v2.html` (8 compteurs publics `api-gateway-pro`, sans token, fallback par compteur ; funnel hub 6 étapes + 3 cartes sites ; formules à l'identique ; version `v2.1.0-p1`). Ne pas committer.

## Actions hors-code à faire par Claude (au retour de Codex)

- **Vérif runtime** : Playwright (`python -m http.server`, PC 1280 + mobile 384), `view-root` non vide sur la vue `acq`, 0 erreur console, `scrollWidth==clientWidth`, fresh-bar présente.
- **Parité chiffres** : ouvrir prod (`index.html`, onglet Acquisition) et v2 côte à côte, comparer chaque chiffre (funnel hub + 3 cartes sites). Corriger tout écart de formule.
- **Git** : commit SCOPÉ (`git add App/monitoring/monitoring-v2.html App/monitoring/HANDOFF.md`, jamais `-A`), message descriptif. Pas de push si non demandé — vérifier la convention.
- **Mémoire** : consigner P1 livré dans le suivi monitoring/dashboard (topic projet, pas MEMORY.md).
- **Déploiement** : AUCUN avant P5. Ne redémarrer aucun serveur.
- **Notifications** : capture Telegram (Honor) après validation visuelle réussie uniquement.

---

**Pour le prochain moteur (résumé 3 lignes)** : refonte dashboard « à côté » — le socle P0 de `monitoring-v2.html` est fait et validé runtime ; on attaque **P1 Acquisition** (la vue la plus simple, token-less). Le brief complet et auto-suffisant est dans `dashboard-refonte/BRIEF-CODEX-P1-acquisition.md` (endpoints + formules exactes déjà extraites du prod). Règles d'or : ne jamais toucher `index.html`/le proxy avant P5, `git add` fichier par fichier (jamais `-A`), parité de chiffres vérifiée en runtime navigateur avant toute bascule.
