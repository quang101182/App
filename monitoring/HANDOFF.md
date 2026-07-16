# HANDOFF — App/monitoring
Lot: R9 · 16 juillet 2026 · Claude (Opus 4.8) → prochain moteur (P3 Produits payants)

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
- **✅ LOT 2 / P1 Acquisition — LIVRÉ + VÉRIFIÉ (Claude, 16/07, `monitoring-v2.html` v2.1.0-p1)**.
  - Codé par **Claude** : le test « Codex mode autonome » (relais Quang) a échoué — Codex n'a rien produit (mode clé API + `--full-auto` = sandbox read-only sur Windows, incapable d'éditer le fichier ; cf `codex.md` §1quater : édition autonome exige `--dangerously-bypass-approvals-and-sandbox`). Quang a rendu la main à Claude.
  - Implémentation : `fetchAcq(signal)` (8 compteurs publics `api-gateway-pro`, sans token, fallback neutre par compteur), branché dans `fetchApp` (`cfg.key==='acq'`) ; `renderAcq/renderAcqHub/renderAcqSites` fidèles aux formules prod ; CSS tokenisé (composants `.acq-*`, réutilise `KpiTile`/`.funnel`) ; version bumpée.
  - **Preuve runtime** (Playwright + `http.server`, jamais `file:`) : PC 1280 + mobile 384, **0 erreur console**, `view-root` non vide, `scrollWidth==clientWidth` (pas d'overflow), fresh-bar présente.
  - **Parité chiffres v2 vs prod** (`index.html#acq` piloté sur les mêmes données live) : **28/28 tokens numériques identiques** (hub visites/waitlist/clics, funnel 6 étapes + %, 3 cartes sites visites/clics/taux). Captures PC+mobile livrées Telegram.

- **✅ LOT 3 / P2 Home — LIVRÉ + VÉRIFIÉ (Claude, 16/07, v2.2.0-p2)**.
  - `fetchHome(signal)` = fetch léger des agrégats publics (réutilise `fetchAcq`), branché dans `fetchApp` (`cfg.key==='home'`). Helpers `acqTotals` / `acqSiteOut` / `homeAlerts`. `ProductCard(app, acq)` remplit les cartes avec les KPI **publics**.
  - Branché sur vraies données : hero « Visites sites » (Σ 4 slugs) + « Alertes » (compte réel), funnel global (Visites → Engagement hub → Clics sortants + % de sortie), 3 cartes produit (visites/clics + barre de taux de sortie), alertes agrégées.
  - **DoD vérifiée** (Playwright) : agrégats == somme des apps → Visites **9578 = 6+9270+194+108** ✅ · Clics sortants **294 = 0+294+0+0** ✅. 0 erreur console PC 1280 + mobile 384, pas d'overflow, fresh-bar présente. **CTA testés au clic réel** : carte produit → `#dk` ✅, lien « Détail → » → `#acq` ✅.
  - ⚠ **2 écarts au mock-up ASSUMÉS et signalés à Quang** (règle d'or #2 = adapter les détails au réel, ne pas prendre le mock-up pour parole d'évangile) :
    1. **« Visites 7j » → « Visites sites »** : le compteur public n'expose que `total` + `today`, **pas de fenêtre 7 j**. Le KPI du mock-up n'est pas réalisable sur cette source. Si le 7 j est voulu, il faut un endpoint qui historise (à décider).
    2. **MRR total / Utilisateurs actifs** restent à `—` (« Données produit — lot P3 ») : ils exigent les endpoints **token-gated**. La part de la DoD P2 « agrégats corrects vs somme des apps » qui les concerne est donc **reportée à P3** — à compléter quand les vues produit existeront.
  - **Alertes réelles remontées** : SubWhisper Pro (194 visites, 0 clic sortant) et StoryVoice (108 visites, 0 clic sortant) → parcours de sortie qui ne convertit pas. **Signal métier à regarder.**

## Ce qui reste à faire
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

**LOT 4 / P3 Produits payants** : porter les vues revenue — **SubWhisper Pro et StoryVoice d'abord** (les plus simples : `gateway-pro` `/admin/swp/overview` et `/admin/sv/overview`), **DictoKey en dernier** (le plus riche, ~1800 lignes prod : adoption Play/Firebase, rétention, devices paginés, churn, attribution, infra → à re-packager en **panneaux accordéon**, pas un fleuve de 7000px). **Tokens obligatoires** (`auth:'token'` déjà dans `APPS[]`, `getToken(key)` lit `localStorage['se7en-monitoring-token-<key>']`). **DoD par app** : parité KPI vs prod + non-régression + token OK.

⚠ **Bloquant à résoudre en premier** : la vérif de parité P3 exige un **token admin réel**. Ne pas demander la clé à Quang → elle est dans le **KV gateway** (`api-gateway.quang101182.workers.dev`, proxy `/api/<provider>/*`, Bearer WORKER_SECRET + UA navigateur sinon 403) — cf `feedback_api_keys_in_kv_gateway` + `_quickref.md`. Vérifier aussi comment le prod stocke son token (`LS_TOKEN_KEY` dans `index.html`) pour rejouer la même auth.

➡ **Une fois P3 fait, revenir compléter la Home** : brancher MRR total + Utilisateurs actifs (aujourd'hui à `—`) sur les caches produit, et vérifier la part restante de la DoD P2 (agrégats vs somme des apps sur les chiffres payants).

## Actions hors-code déjà faites (P1, P2) / à faire (Claude)

- ✅ P1 : runtime Playwright OK, parité 28/28, commit scopé, captures Telegram livrées.
- ✅ P2 : runtime OK, agrégats vérifiés vs somme des apps, CTA au clic réel, commit scopé, captures Telegram livrées.
- **Git** : toujours commit SCOPÉ (`git add` fichier par fichier, jamais `-A` — dépôt `App` a des frères non commités). Pas de push tant que non demandé.
- **Mémoire** : P1 + observation test Codex autonome à consigner (topic monitoring + `codex.md`).
- **Déploiement** : AUCUN avant P5. Ne redémarrer aucun serveur.

---

**Pour le prochain moteur (résumé 3 lignes)** : refonte dashboard « à côté » — **P0 socle + P1 Acquisition + P2 Home sont faits et vérifiés** (`monitoring-v2.html` v2.2.0-p2 ; parité acq 28/28 vs prod, agrégats Home == somme des apps, 0 erreur console PC+mobile, CTA testés au clic). Prochaine étape = **P3 Produits payants** (swp/sv d'abord, DictoKey en dernier en accordéon) — **son bloquant = obtenir un token admin réel pour prouver la parité** (il est dans le KV gateway, ne jamais le demander à Quang) ; puis revenir brancher MRR/Actifs sur la Home. Règles d'or : ne jamais toucher `index.html`/le proxy avant P5, `git add` fichier par fichier (jamais `-A`), vérif en runtime navigateur (`http.server`+Playwright, jamais `file:`). Codex n'a pas pu coder en autonomie (clé API → sandbox read-only) : pour le relayer, son onglet doit être en `--dangerously-bypass-approvals-and-sandbox` (cf `codex.md` §1quater).
