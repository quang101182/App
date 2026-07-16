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

- **✅ LOT 4 / P3a — SubWhisper Pro + StoryVoice LIVRÉS + VÉRIFIÉS (Claude, 16/07, v2.3.0-p3a)**.
  - **Token résolu** : les valeurs sont dans `_quickref.md` (pas besoin du KV) — swp/sv = `admin-pro-2026`, dk = `dk-admin-2026-secure`. **v2 lit désormais LES MÊMES clés localStorage que la prod** (`tokenKey` par app : `monitoring_swp_token` / `monitoring_storyvoice_token` / `monitoring_admin_token`) → v2 étant servi depuis la MÊME origine, les tokens déjà collés par Quang sont **hérités**, rien à recoller à la bascule P5.
  - Helpers portés à l'identique (`swpHealth`, `swpPct`, `swpFmtDate/Relative`, `swpPlanBadge`, `SWP_PRICE_EUR=9`, `svRevenue` greedy packs, `svHours`, `svFmt`, `svIsInternal`). `fetchApp` générique gère `cfg.gateway + cfg.endpoints` + `Bearer`. Nouveaux composants : `TokenGate`, `EmptyState`, `.data-table`, `.badge`, `.health`, `.sv-row`.
  - **Parité vérifiée : 21/21 identiques** vs prod (Playwright, tokens injectés, mêmes données live) — SWP : MRR 18 €, payants 2, à risque 2, churn 72.7%, clients réels 11, revoked 8, visites 194, **15 lignes de détail** · SV : conversion 0%, revenu 0 €, 8 KPI + 1 ligne. **0 erreur console v2**, pas d'overflow PC 1280 + mobile 384, **token gate testé** (sans token → formulaire, 401 → « session expirée »).
  - Signaux métier sortis : **churn SWP 72,7 %** (8 révoqués / 11 réels) et **2 payants à risque** (1 payé jamais utilisé = risque remboursement, 1 inactif 43j). SV : le seul client est **interne** (`@local`) → revenu réel **0 €** (le champ API `revenue_eur_est: 24.9` n'est PAS utilisé par le prod — normal, parité respectée).

## Ce qui reste à faire
- **P3b DictoKey** : le gros morceau (~1800 lignes prod : adoption Play/Firebase, rétention, devices paginés, churn, attribution, infra) → à re-packager en **panneaux accordéon** (`Panel` existe déjà dans le socle), pas un fleuve de 7000px. Token `monitoring_admin_token` = `dk-admin-2026-secure`, gateway `api-gateway-dictokey`, endpoints `/admin/monitoring|stats|devices|firebase-stats|playstore-stats`. **DoD** : parité KPI + non-régression + token OK.
- **P4 Ops** : Factory + Studio. **DoD** : parité.
- **P5 Bascule** : parité globale prod vs v2 → repointer le proxy `se7enai-dash` sur v2 → surveiller 48 h → archiver l'ancien. Réversible (repointer = 1 commit).
- **P6 Hygiène** : supprimer code mort, changelog.

## Pièges à ne pas répéter

- **Ne JAMAIS toucher `index.html` ni le proxy avant P5** : le dashboard prod génère du revenu.
- **JAMAIS `git add -A` dans le dépôt `App`** : des modifs et fichiers non suivis concurrents existent dans des projets frères (`api-gateway-pro`, `noteflow`, `promoclip`, `subwhisper-pro`…). **Indexer fichier par fichier**, uniquement ceux du lot.
- **`node --check` ≠ preuve runtime** : le socle P0 ne s'affichait pas à cause d'un bug runtime (shadowing) invisible aux contrôles statiques. **Toujours** valider via `python -m http.server` + Playwright (`is_mobile=True`), **jamais `file:`** (bloqué par la politique navigateur). Vérifier `view-root` non vide sur CHAQUE vue à froid + `errors console == 0`.
- **Parité AVANT bascule** : comparer chaque chiffre v2 au prod côte à côte. Reproduire les formules EXACTEMENT (pièges connus : funnel hub étape 5 « Waitlist » a pour base `cta`, PAS `vTot` · `payants` SWP exige `lsStatus === 'active'` STRICT — un `pro` sans `lsStatus` est labellisé « Actif » mais **exclu** du MRR · churn SWP = ratio **cumulé** révoqués/réels, pas mensuel · les **tableaux de détail affichent TOUT** (test/internes inclus) alors que les **KPI les excluent** = 2 populations sur le même écran).
- **Pièges de HARNESS Playwright rencontrés** (coûtent 20 min chacun) : `add_init_script` attend des **instructions**, PAS une arrow function (`()=>{...}` = expression jamais appelée → token jamais posé) · un `goto` qui ne change que le **hash** = navigation **same-document**, le document n'est pas ré-exécuté → le prod (qui lit le hash seulement à l'init, sans listener `hashchange`) reste sur l'onglet précédent → **forcer `page.reload()`** · ce reload annule les fetch en vol du prod → une erreur console `Failed to fetch` venant d'`index.html` est un **artefact de test**, pas un bug v2 (vérifier la stack avant de conclure).
- **Codex ne fait ni git, ni mémoire, ni déploiement, ni vérif visuelle** (son sandbox ne rend pas le navigateur). Il code ; Claude relit le `git diff`, teste le rendu, commit, met la mémoire à jour. « Commité + tests verts » ≠ « ça marche » → valider le FONCTIONNEL.
- **Fresh-bar obligatoire sur CHAQUE vue** (exigence forte Quang) + **refresh manuel uniquement**, pas d'auto-fetch (sinon spam réseau + coût).
- **Mobile réel** : Playwright `is_mobile=True` (pas `--window-size`), vérifier `scrollWidth === clientWidth`.

## Prochaine étape unique

**LOT 5 / P3b — DictoKey** : porter la dernière vue produit, la plus riche (~1800 lignes prod), en **panneaux accordéon** (`Panel(id, title, content, open)` est déjà dans le socle). Token `monitoring_admin_token` = `dk-admin-2026-secure` (déjà câblé dans `APPS[]`), gateway `api-gateway-dictokey`, endpoints `/admin/monitoring|stats|devices|firebase-stats|playstore-stats`.

Méthode qui a marché 3 fois — la rejouer : (1) sous-agent Explore pour extraire endpoints + formules + DOM du prod, (2) **passe critique** = relire soi-même le code cité avant de coder, (3) porter à l'identique avec les composants v2, (4) prouver la parité en Playwright (prod vs v2, mêmes données live, extraction par label), (5) capture + commit scopé.

➡ **Puis revenir compléter la Home (P2)** : brancher MRR total + Utilisateurs actifs (aujourd'hui à `—`) sur les caches produit désormais disponibles, et boucler la part restante de la DoD P2 (agrégats vs somme des apps sur les chiffres payants). MRR total attendu = MRR SWP (18 €) + revenu SV (0 €) + premium DictoKey.

## Actions hors-code déjà faites (P1, P2) / à faire (Claude)

- ✅ P1 : runtime Playwright OK, parité 28/28, commit scopé, captures Telegram livrées.
- ✅ P2 : runtime OK, agrégats vérifiés vs somme des apps, CTA au clic réel, commit scopé, captures Telegram livrées.
- ✅ P3a : parité 21/21, token gate testé, commit scopé, captures Telegram livrées.
- **Git** : toujours commit SCOPÉ (`git add` fichier par fichier, jamais `-A` — dépôt `App` a des frères non commités). Pas de push tant que non demandé.
- **Mémoire** : P1 + observation test Codex autonome à consigner (topic monitoring + `codex.md`).
- **Déploiement** : AUCUN avant P5. Ne redémarrer aucun serveur.

---

**Pour le prochain moteur (résumé 3 lignes)** : refonte dashboard « à côté » — **P0 socle + P1 Acquisition + P2 Home + P3a SWP/StoryVoice sont faits et vérifiés** (`monitoring-v2.html` v2.3.0-p3a ; parité acq 28/28 et produits 21/21 vs prod, agrégats Home == somme des apps, 0 erreur console PC+mobile, token gate testé). **Il ne reste qu'une vue produit : P3b DictoKey** (la plus riche → panneaux accordéon), puis revenir brancher MRR/Actifs sur la Home, puis P4 Ops et P5 bascule. Les tokens sont **résolus** (`_quickref.md` : swp/sv `admin-pro-2026`, dk `dk-admin-2026-secure`) et v2 lit **les mêmes clés localStorage que la prod** → rien à recoller à la bascule. Règles d'or : ne jamais toucher `index.html`/le proxy avant P5, `git add` fichier par fichier (jamais `-A`), vérif en runtime navigateur (`http.server`+Playwright, jamais `file:`) avec extraction par label. Codex n'a pas pu coder en autonomie (clé API → sandbox read-only) : pour le relayer, son onglet doit être en `--dangerously-bypass-approvals-and-sandbox` (cf `codex.md` §1quater).
