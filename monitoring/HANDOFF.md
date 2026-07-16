# HANDOFF — App/monitoring
Lot: R11 · 16 juillet 2026 · Claude (Opus 4.8) → **P5 BASCULÉ (go Quang donné le 16/07)** · reste : surveillance 48 h, P6 hygiène

## 🚨 BASCULE FAITE le 16/07/2026 — `dash.se7enai.com` sert `monitoring-v2.html` (v2.11.1-p4)

**Rollback = 1 minute, 1 ligne** (le worker n'est PAS versionné — se7enai-hub n'est pas un dépôt git) :
```bash
cd D:/Download/02-Apps-Web/se7enai-hub/dash-worker
# remettre "/index.html" à la place de "/monitoring-v2.html" (src/inject.js l.22)
# un .bak horodaté existe : src/inject.js.bak-pre-p5-*
export CLOUDFLARE_API_TOKEN="cfut_..."   # token « claude-factory », cf _quickref.md (Workers Scripts:Edit)
npx wrangler deploy --config ./wrangler.toml
```
- **Filet immédiat SANS redeploy** : `dash.se7enai.com/index.html` sert TOUJOURS l'ancien dashboard v1.23.0 (seul le chemin `/` a basculé). Quang peut y aller à tout moment.
- **Ce qui a changé** : `se7enai-hub/dash-worker/src/inject.js` l.22 → `const path = url.pathname === "/" ? "/monitoring-v2.html" : url.pathname;`. Déployé : version `5b361ede-3b2f-4815-945d-1ad4cee5fb51`. **Rien d'autre** (UPSTREAM, injection des tokens, secrets, Access : inchangés).
- ⚠ **`wrangler` n'était plus authentifié** (OAuth local expiré → `Failed to fetch auth token: 400`). Utiliser `CLOUDFLARE_API_TOKEN` = token **« claude-factory »** (`_quickref.md`, a bien `Workers Scripts:Edit`). Toujours `--config ./wrangler.toml` (2 incidents de worker déployé au mauvais endroit, cf `feedback_wrangler_parent_config.md`).
- ⚠ **`index.html` (prod v1) n'a JAMAIS été touchée** de tout le chantier et reste servie sur `/index.html` + le github.io public. Ne pas la supprimer avant la fin de la surveillance 48 h.
- **Vérification post-bascule faite** (Cloudflare Access interdit la lecture anonyme → la chaîne du worker a été **rejouée à l'identique** en local depuis la MÊME source github.io avec la MÊME injection de tokens) : **14/14 vues OK** (7 PC 1280 + 7 mobile 384), **aucun token-gate** (tokens injectés bien hérités), 0 erreur console, 0 overflow. Source github.io confirmée en `v2.11.1-p4`.
- ⏭ **Reste** : surveiller 48 h (jusqu'au 18/07), puis archiver `index.html` · P6 hygiène · P3b2b (non bloquant).

## Objectif courant

Refonte du dashboard monitoring « reconstruire à côté » : porter chaque vue de la prod `index.html` v1.23.0 vers `monitoring-v2.html` (config-driven, tokenisé, responsive), **sans toucher la prod**, en migrant onglet par onglet, bascule seulement à parité de chiffres vérifiée.

**Étape immédiate = surveillance 48 h + P6 hygiène.** ✅ Fait et vérifié : P0 socle, P1 Acquisition, **P2 Home COMPLÈTE (DoD bouclée)**, P3a SWP/StoryVoice, P3b1→P3b5 DictoKey (vue complète), **P4 Ops Factory + Studio**, **P5 BASCULE (16/07)**. **TOUTES LES VUES SONT PORTÉES (7/7) ET EN PRODUCTION.**

## Références figées

- Mock-up de direction VALIDÉ : `D:/Download/02-Apps-Web/dashboard-refonte/MOCKUP-v0.2.html`.
- Feuille de route mère : `D:/Download/02-Apps-Web/dashboard-refonte/DASHBOARD-REFONTE-ROADMAP.md` (§3 = phasage P0→P6).
- ~~`dashboard-refonte/BRIEF-CODEX-P1-acquisition.md`~~ — **PÉRIMÉ, ne pas exécuter** : P1 est livré. Le fichier ne reste utile que comme **exemple de brief** auto-suffisant si on veut relayer un lot à Codex/Gemini.
- **Prod = `App/monitoring/index.html` v1.23.0, dernier commit `1546c70`. Elle n'a PAS été touchée de tout le chantier — et ne doit pas l'être avant P5.**

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

- **✅ LOT 5 / P3b1 — DictoKey : Overview + Play Store + Infra (Claude, 16/07, v2.4.0-p3b1)**.
  - `fetchDk` : `Promise.all` des 5 sources (monitoring `?period=7d&advanced=1`, stats, devices, visit/click publics `page=dk` tolérants) **+ playstore-stats toléré et AWAITÉ** → supprime la race du prod (qui le lance en fire-and-forget depuis `render()` et doit re-render via `window._kpiDevicesCtx` + `updateKpiDevices`). Un seul rendu, chiffres identiques.
  - Helpers portés à l'identique : `dkPctChange`, `dkPlayDate`/`dkDaysSinceUtc` (UTC forcé), `dkDeviceStats` (PC exclus, phantom, premiumRuntime, totalPremium, newDevicesToday), `TRACKING_BASELINE_VISITS = 1874`.
  - Rendu : trend-bar, 4 KPI (hero appareils Play-ou-KV), bandeau Premium silencieux, funnel site, Play Store (adoption + 28 j + warning figé), Infra (erreurs + coûts) — **en panneaux accordéon** (`Panel`), ce qui règle le fleuve de 7000px.
  - **Parité vérifiée : 33/33 identiques** vs prod (extraction prod **par ID d'élément**, v2 par structure DOM). Couvre les cas tordus : delta −68 %, `snapshot Google au 11 juil. (J-5)`, breakdown clics `hero 235 · pricing 8 · …`, taux 4.0 % (avec baseline), conversion 42.0 %, note 4.73. **0 erreur console**, pas d'overflow PC 1280 + mobile 384.

- **✅ LOT 6 / P3b2 — DictoKey Appareils (Claude, 16/07, v2.5.0-p3b2)**.
  - Summary (realCount = devices − fantômes, breakdown pro/💎premium/free, fantômes, ⚡nouveaux), **filtres tier persistés sur la MÊME clé que la prod** (`monitoring_tier_filters` → hérités), recherche (id/cat/plateforme/pays), **tableau paginé 50/page** (4 colonnes : Appareil + 3 sous-lignes fixes drapeau/modèle/Android, Tier + `KV:` si effectif ≠ KV, Créé, Vu), état vide + « Tout réactiver », pagination masquée si ≤ 50.
  - Filtres/recherche/pagination re-rendent **uniquement le panneau** (`dkRefreshDevicesPanel`) → **zéro requête réseau**, focus de la recherche conservé.
  - **Parité vérifiée** : summary, compteurs des pills, `1 / 10 (464 appareils)`, 50 lignes, 3 premières lignes identiques au caractère près. **Interactions testées au clic réel** : pill `free` OFF → `1 / 2 (51 appareils)`, page suivante → `2 / 10`, recherche « fr » → `1 / 9 (435)`. 0 erreur console, pas d'overflow PC + mobile 384.
  - 📐 **ÉCART ASSUMÉ vs prod, demandé explicitement par Quang (16/07) : `DK_PER_PAGE = 30`** (la prod est à 50). Arbitrage Claude entre les 20 ou 30 proposés : 30 → 16 pages pour 464 devices (20 en ferait 24 = trop de clics), tout en divisant presque par 2 le scroll mobile. **N'affecte AUCUN chiffre** (total 464, KPI, filtres identiques) — seulement le nombre de pages (`1 / 16` en v2 vs `1 / 10` en prod). Descendre à 20 = changer la constante, rien d'autre.
  - 🐛 **BUG PROD CORRIGÉ en v2 (feu vert Quang 16/07, v2.6.0-p3b2) — divergence assumée** : `getDeviceCategory()` (prod l.3813-3822) teste `pro` puis `effectiveTier === 'premium'` et **oublie le cas `tier === 'premium'` en KV** → ces appareils retombaient dans « free ». Pills premium **16** alors que le summary comptait **18**, et ils **disparaissaient dès qu'on décochait « free »**. Fix v2 : `if (kvTier === 'premium' || d.effectiveTier === 'premium') → premium`. Vérifié : pills **16 → 18** (= summary), free **413 → 411**, filtrer premium seul → **18 appareils**. Summary/fantômes inchangés. ⚠ La prod garde le bug jusqu'à la bascule P5 (interdit d'y toucher).
  - 📖 **Vocabulaire — ne pas se tromper (correction Quang 16/07)** : **seul `pro` est admin-set** (cadeau à vie, 35 appareils). Les **premium sont des achats Google Play réels**, jamais « manuels ». Les 2 sources sont disjointes par construction : `tier='premium'` en KV = écrit par l'APP (`/device/restore` / `/device/update-tier`, cf `notifyGatewayTierUpdate` BillingManager v2.61.4+) = **12 appareils** ; `effectiveTier='premium'` + KV free = premium runtime non syncé (app < v2.61.4) = **6 appareils**. Total 18.
  - 🔍 **Anomalie à investiguer (constatée 16/07, PAS un bug de portage)** : les 2 appareils KV premium sans `effectiveTier` (`afb0bccbec65…` créé 12/05, `fe82785685e5…` créé 23/05) ont **`createdAt == lastSeen`** (vus une seule fois, jamais revenus), **zéro métadonnée** (`appVersion`/`deviceModel`/`country`/`lastSource` tous null) et **aucun signal premium runtime** (`effectiveTierAt` null). Pattern proche du « payé · jamais utilisé » de SubWhisper Pro = **risque de remboursement**. À croiser avec la Play Console pour voir s'ils correspondent à de vrais achats.
  - ✅ **`free` 346 (summary) vs 411 (pills) = NON aligné volontairement** : ce n'est pas une incohérence, les deux répondent à des questions différentes — le summary annonce les free *réels* (fantômes sortis, comptés à part) ; le filtre compte ce qui est **dans le tableau**, fantômes inclus (et le tableau les affiche bien, grisés + tag FANTOME).
  - 🔁 **`dkIsPhantom(d)` unifié (feu vert Quang)** : la prod définissait le test **3 fois** (render l.2606 + renderDevicesPage l.4008 = ms & tier minusculé ; donut pays l.2811 = strings ISO & `d.tier` **brut sans minuscules** → un tier `"Free"` aurait cassé le donut seul). **Mesuré sur les 464 devices réels : les 2 variantes donnent 65, ZÉRO écart** (tiers déjà en minuscules, aucune date manquante) → unification sans changer un chiffre. **Le donut de P3b3 DOIT utiliser `dkIsPhantom`.**
  - ✏️ Pluriel corrigé (« 1 appareil » et non « 1 appareils » — faute présente dans la prod). Aucun chiffre touché.
  - ⏭ **P3b2b** (reporté) : panneau détail par appareil (expand) — `buildDevicePanelHtml` + `aggregateDaily`, endpoint `/admin/monitoring?device=<id>&period=30d`, batch de 6 avec guard `_fetchCounters` + `_bulkCancelled`, état conservé à travers la pagination.

- **✅ LOT 7 / P3b3 — DictoKey Charts & donuts (Claude, 16/07, v2.7.0-p3b3)**.
  - `Chart.js@4` via CDN (comme la prod). **Registre `dkCharts` + `dkDestroyCharts()`** appelé avant chaque re-render et à chaque changement de vue → **corrige la fuite de la prod** (`window._cLatency` est hors de son objet `charts`, donc jamais détruit). Vérifié : **0 instance résiduelle** après changement de vue.
  - Palette = colonne **dark** de la palette dataviz, **ordre fixe** (l'ordre EST le mécanisme de sécurité daltonisme). **Validée par `validate_palette.js` contre NOTRE surface `#141a26`** (pas celle par défaut de la skill) : 5/5 PASS (bande L, chroma, CVD ΔE 8.4, vision normale 19.3, contraste ≥3:1). Ne pas réordonner.
  - Livré : DAU quotidien (line, **série unique → pas de légende**, le titre nomme la série), Activité quotidienne (bar stacked 4 séries, spacer 2px couleur surface), Latence P50 (line, `spanGaps`), **4 jauges** par endpoint (statut = couleur **+ mot** « Rapide/Moyen/Lent », jamais la couleur seule), donut Langues, donut Top pays (fantômes exclus via `dkIsPhantom`).
  - Panneau replié → **resize des charts à l'ouverture** (sinon canvas 0×0 = chart écrasé).
  - 📐 **ÉCART ASSUMÉ vs prod (règle dataviz « jamais de hues cyclées »)** : la prod fait `DONUT_COLORS[i % length]` → ses **17 langues** sortent avec des couleurs qui **se répètent** (2 langues de même couleur = illisible). v2 replie sur **top 7 + « Autres »** et trie desc (la prod ne triait pas les langues). **Vérifié : le total est CONSERVÉ** — donut langues **945** = somme exacte des 17 langues ; donut pays **399** = 464 devices − 65 fantômes. Aucune donnée perdue, juste les doublons de couleur supprimés.

- **✅ LOT 8 / P3b4 — Firebase + Adoption v2.61 + Attribution v2.61.7 (Claude, 16/07, v2.8.0-p3b4)**.
  - `fetchDk` ajoute `/admin/firebase-stats?period=7d`, **toléré** (`.catch(() => null)`) comme playstore.
  - `renderDkFirebase` (3 KPI + funnel d'activation + sources d'acquisition avec bandeau IA), `renderDkAdoption` (badge + flow ime_only/with_bubble + conversion bandeau par déclencheur + drop-off par slide en **ordre fixe** + refus de permission), `renderDkAttribution` (badge + sources d'installation + top boutons/pages + kills OEM). Tout en panneaux accordéon.
  - **Parité vérifiée : 15/15** vs prod (KPI + séquence numérique de chaque bloc). 0 erreur console, pas d'overflow PC + mobile 384.
  - ⚠ **Piège de harness** : le prod lance `fetchFirebaseLive()` en **fire-and-forget** et l'endpoint interroge **GA4 en live** (plusieurs secondes). Attendre une **vraie valeur numérique**, pas juste « plus de ⏳ » : `—` = jamais rendu, et on croit à tort à un écart de parité (m'a coûté un faux négatif 15/15 → 0/15).
  - ✏ **Libellés repris à l'identique** : le bandeau IA dit « Phase 0/1/2 GEO live 29/05 » (renvoie aux phases GEO) — je l'avais reformulé, corrigé. Ne pas réécrire les libellés du prod en douce.
  - 📊 **Signaux métier sortis (à regarder, indépendants du dashboard)** : **19 désinstalls pour 31 nouveaux users sur 7 j** (17 users distincts) · **bandeau d'activation bulle = 0 % de conversion** (0 activation sur **11 taps** : `main_banner` 0/7, `post_dictation_notif` 0/4) — le bandeau est cliqué mais n'aboutit JAMAIS · funnel : first_open 31 → bulle 11 (35 %) → IME 8 (26 %) → first_dictation 7 (23 %) → premium_purchase 1 (3 %) · attribution : google-play 19 (73 %), **dictokey-site 1 (4 %)** seulement.

- **✅ LOT 9 / P3b5 — DictoKey Rétention + Mouvements de tier (Claude, 16/07, v2.9.0-p3b5) — DictoKey COMPLET**.
  - `renderDkAdvanced` : rétention D1/D7/D30 (seuils 0.4 vert / 0.2 orange / sinon rouge, carte « Pas assez de données » si cohorte absente), nouveaux utilisateurs (sub + chart bar **enregistré dans `dkCharts`**), distribution d'usage (min/max/moyenne/médiane + segments power/regular/casual), adoption des features.
  - `renderDkChurn` : affiche les **2 sources côte à côte avec leur sémantique exacte** (comme la prod) — Firebase 7j (achats fresh / restaurations / désinstalls) ET KV gateway. **Pourquoi** : le KV (`m:churn:{date}`) ne bouge QUE sur un changement de tier **admin** ; les achats Play Billing de l'APK **ne notifient pas le gateway** → KV à 0 alors que Firebase voit les events. Ne pas « corriger » en fusionnant les deux : ce sont deux mesures différentes.
  - **Parité vérifiée : 7/7** vs prod, dont le cas `D7 = « Pas assez de données »` (cohorte nulle) et le tableau vide « Aucun mouvement de tier sur la période ». Chart signup : 5 points, total 10 = `new_users.total_period`. 0 erreur console, pas d'overflow.

- **✅ LOT 10 / Home complétée — DoD P2 BOUCLÉE (Claude, 16/07, v2.10.0-home)**.
  - `homeSwpStats` / `homeSvStats` / `homeDkStats` lisent **UNIQUEMENT `state.cache`** — la Home reste **TOKEN-LESS** (roadmap §4) : elle ne fetche JAMAIS un endpoint payé. Cache absent → `—` + note honnête (« ouvre les vues produit pour agréger »).
  - **DoD vérifiée en flux réel** (Playwright) : à froid MRR/Actifs = `—` (aucun fetch payé) ; après visite des 3 vues → **MRR 18 € = 18 SWP + 0 SV** ✅ · **Actifs 159 = 148 DictoKey + 11 SWP + 0 SV** ✅ · **4 alertes agrégées** (2 sites sans clic sortant + 2 payants SWP à risque + snapshot Play figé J-5). 0 erreur console, pas d'overflow.
  - ⚠ **3e écart au mock-up ASSUMÉ** (après « Visites 7j ») : **« MRR total = Σ dk premium + swp + sv » n'est PAS réalisable pour la part DictoKey.** Ses revenus Premium sont gérés par **Google Play Console** et exposés par **AUCUN endpoint** — le prod le dit lui-même dans son infobulle « MRR estimé » (l.4804) — et il n'existe **aucune constante de prix DK** (contrairement à `SWP_PRICE_EUR = 9`). v2 somme ce qui est réel et l'écrit dans l'UI : « 18 € SWP + 0 € StoryVoice · DictoKey via Play Console (non exposé par l'API) ». **Aucun prix inventé.** Si Quang veut le MRR DK, il faut une source (prix en dur + compte de premium actifs, ou l'API Play Developer).
  - 📖 « Utilisateurs actifs » agrège des **populations hétérogènes** (DictoKey = appareils, SWP/SV = clients) → la composition est affichée en note, pas cachée.

- **✅ LOT 11 / P4 Ops — Factory + Studio LIVRÉS + VÉRIFIÉS (Claude, 16/07, v2.11.0-p4) — TOUTES LES VUES SONT PORTÉES**.
  - **Factory** — `fetchFactory` + `renderFactoryView`. 9 compteurs publics (`tuc|aea|lpp` × `_|-buy|-dl`) tolérants par compteur + `/overview` en Bearer. **Token VRAIMENT optionnel** (`auth:'none'` + gating partiel, PAS de TokenGate) : sans token, aucun appel au worker (zéro bruit console), ventes/abonnés à `—`, `Visite→vente` non rendu.
  - **Parité vérifiée : 24/24 valeurs identiques** vs prod (3 comptes × 6 métriques + placeholder), **dans les 2 modes** : sans token (`6 / 0 / 2 / — / — / —`…) ET avec token (`8.39 EUR`, 1 vente, subs 0). Conversions identiques. 0 erreur console, pas d'overflow PC 1280 + mobile 384. Bouton token testé au clic réel.
  - **Studio** — `fetchStudio` + `renderStudioView`. Planning statique porté (15 posts, backlog, lanes) + rollup `data/analytics.json`. **Parité agenda** : 15 cartes, « À produire 3 », « Publié 15 », 3 KPI identiques. Filtres/chips/état vide/persistance testés au clic réel, **0 requête réseau par clic** (la prod refetch à CHAQUE chip).
  - 📐 **ÉCART ASSUMÉ — décision Quang 16/07 (perf TikTok séparée)** : organique et boosté affichés **côte à côte, JAMAIS additionnés** → « Organique 16 vidéos · **15 226** vues » / « Boostées · vues achetées 4 vidéos · **67 000** vues ». La prod affichait **82 226 vues** sous le libellé « boostées exclues » (cf. bug #6 ci-dessous). v2 rend 12 lignes (8 organiques + 4 boostées) vs 8 en prod : **rupture de parité VOULUE**, c'est le seul chiffre du chantier qui diverge par décision produit.
  - 🐛 **BUGS PROD CORRIGÉS en v2** (la prod les garde jusqu'à P5) : voir #6 → #10 de la roadmap §8 (libellé perf mensonger, `J+N` faux d'un jour, backlog filtré au tiers, canaux décochés affichés, cache/token désynchronisés).
  - ⚠ **`Visite→vente` = ratio à FENÊTRES MIXTES** (ventes cumulées depuis l'origine ÷ visites depuis le **25/06**, date où le worker `factory-visits` est reparti de 0) → mécaniquement surévalué (`tuc` affiche 16.7 %). La prod l'affiche nu ; v2 le **marque** (`⚠ fenêtres mixtes` + tooltip) sans le supprimer ni changer le chiffre. **Le vrai correctif est côté worker** (borner `/overview` sur une période) — à décider avec Quang.
  - 🔍 **Anomalie Factory à investiguer** : `tuc` = **1 vente / 8.39 €** pour **6 visites** et **0 clic achat** enregistré. Une vente sans clic tracé = le compteur `tuc-buy` ne capte pas le vrai chemin d'achat (ou la vente précède le 25/06). À croiser avec LemonSqueezy.

## Ce qui reste à faire
- **P5 Bascule** : parité globale prod vs v2 → repointer le proxy `se7enai-dash` sur v2 → surveiller 48 h → archiver l'ancien. Réversible (repointer = 1 commit). ⚠ **Go explicite de Quang OBLIGATOIRE** (revenue).
- **P6 Hygiène** : supprimer code mort, changelog.
- **Non bloquant** : P3b2b (expand par appareil).
- ⚠ **Ne PAS porter le code mort** identifié : `#funnelUnified` (masqué v1.13.0 mais toujours calculé), donuts Modes/Paires (masqués), Sessions 7j Firebase (masqué), `PLAYSTORE_STATS_BASELINE` (déclarée jamais lue), `isAutoRefresh` (auto-refresh retiré v1.14.0). Côté P4 : `mailerliteGroups` (jamais lu), champ `ver` de `STUDIO_SCHEDULE` (15 occurrences mortes), `series[]` d'`analytics.json` (~60 % du poids du fichier, jamais lu) — **non portés**.

## Pièges à ne pas répéter

- **Ne JAMAIS toucher `index.html` ni le proxy avant P5** : le dashboard prod génère du revenu.
- **JAMAIS `git add -A` dans le dépôt `App`** : des modifs et fichiers non suivis concurrents existent dans des projets frères (`api-gateway-pro`, `noteflow`, `promoclip`, `subwhisper-pro`…). **Indexer fichier par fichier**, uniquement ceux du lot.
- **`node --check` ≠ preuve runtime** : le socle P0 ne s'affichait pas à cause d'un bug runtime (shadowing) invisible aux contrôles statiques. **Toujours** valider via `python -m http.server` + Playwright (`is_mobile=True`), **jamais `file:`** (bloqué par la politique navigateur). Vérifier `view-root` non vide sur CHAQUE vue à froid + `errors console == 0`.
- **Parité AVANT bascule** : comparer chaque chiffre v2 au prod côte à côte. Reproduire les formules EXACTEMENT (pièges connus : funnel hub étape 5 « Waitlist » a pour base `cta`, PAS `vTot` · `payants` SWP exige `lsStatus === 'active'` STRICT — un `pro` sans `lsStatus` est labellisé « Actif » mais **exclu** du MRR · churn SWP = ratio **cumulé** révoqués/réels, pas mensuel · les **tableaux de détail affichent TOUT** (test/internes inclus) alors que les **KPI les excluent** = 2 populations sur le même écran).
- **Pièges de HARNESS Playwright rencontrés** (coûtent 20 min chacun) : `add_init_script` attend des **instructions**, PAS une arrow function (`()=>{...}` = expression jamais appelée → token jamais posé) · un `goto` qui ne change que le **hash** = navigation **same-document**, le document n'est pas ré-exécuté → le prod (qui lit le hash seulement à l'init, sans listener `hashchange`) reste sur l'onglet précédent → **forcer `page.reload()`** · ce reload annule les fetch en vol du prod → une erreur console `Failed to fetch` venant d'`index.html` est un **artefact de test**, pas un bug v2 (vérifier la stack avant de conclure).
- 🚨 **`reload()` SYSTÉMATIQUE = faux négatif de parité (vécu en P4, 20 min)** : un `reload()` après un `goto` vers une AUTRE page relance le boot du prod, dont l'`AbortController` **annule ses 9 fetch Factory en vol** → toutes ses métriques tombent à `—` et la parité semble catastrophique alors que v2 est juste. **La règle exacte** : `reload()` UNIQUEMENT quand on change le seul hash d'un document déjà chargé. Sinon → `goto('about:blank')` puis `goto(url)` = vraie navigation, le document s'exécute proprement. Corollaire : `add_init_script` s'exécute AUSSI sur `about:blank` → il y lève `localStorage: Access is denied` ; ces erreurs console sont un **artefact du harness** (leur nombre suit celui des handlers cumulés), pas un bug — les compter séparément.
- **Codex ne fait ni git, ni mémoire, ni déploiement, ni vérif visuelle** (son sandbox ne rend pas le navigateur). Il code ; Claude relit le `git diff`, teste le rendu, commit, met la mémoire à jour. « Commité + tests verts » ≠ « ça marche » → valider le FONCTIONNEL.
- **Fresh-bar obligatoire sur CHAQUE vue** (exigence forte Quang) + **refresh manuel uniquement**, pas d'auto-fetch (sinon spam réseau + coût).
- **Mobile réel** : Playwright `is_mobile=True` (pas `--window-size`), vérifier `scrollWidth === clientWidth`.

## Prochaine étape unique

**Surveillance 48 h (jusqu'au 18/07), puis archiver `index.html`.** La bascule est faite (voir le bloc en tête). Ne rien archiver avant la fin de la surveillance : `/index.html` est le filet de secours sans redeploy.
- ✅ ~~Parité globale~~ : passe faite le 16/07 avant bascule — 14/14 vues saines (7 PC + 7 mobile), spot-check des chiffres clés OK (DictoKey 464/4.73, SWP 18/11/72.7, acq 9270, Factory 6/12/25/8.39, Studio 15226/67000, Home 18/159).
- ✅ ~~Repointer le proxy~~ : fait, version `5b361ede`.
- ⏭ **Surveiller** : si Quang signale un écran vide/lent, penser au **cold start du worker DictoKey (jusqu'à 22 s)** — c'est attendu, l'état de chargement l'annonce désormais.
- ✅ **Tokens : rien à recoller.** v2 lit les MÊMES clés localStorage que la prod (`monitoring_admin_token`, `monitoring_swp_token`, `monitoring_storyvoice_token`, `monitoring_factory_token`, `dk-monitoring-studio-filters`) et est servi depuis la MÊME origine → tokens et filtres hérités.
- ⚠ **Divergences VOULUES à assumer publiquement à la bascule** (ce ne sont PAS des régressions) : perf Studio séparée organique/boosté (82 226 → 15 226 + 67 000, décision Quang), 30 appareils/page (vs 50), donuts top 7 + « Autres », filtre premium DictoKey corrigé (16 → 18), `Visite→vente` marqué « fenêtres mixtes ». Roadmap §7 + §8.

**Décisions EN ATTENTE de Quang (ne pas trancher seul)** :
1. **MRR DictoKey** — inexistant dans l'API (Play Console). Prix en dur × premium actifs / API Play Developer / laisser « via Play Console » ?
2. **`Visite→vente` Factory** — corriger côté worker (borner `/overview` sur une période) ou garder le marquage v2 ?

**Non bloquant** : P3b2b (expand par appareil) — `buildDevicePanelHtml` + `aggregateDaily` (prod l.4273-4402), endpoint `/admin/monitoring?device=<id>&period=30d`, batch de 6 avec guard `_fetchCounters` + `_bulkCancelled`.

⚠ **Fraîcheur hétérogène** à afficher honnêtement : Play = snapshot J-2..J-7 (peut être figé >3j), Firebase = **J-1** (cache KV 1h), KV gateway = live, visites site = live. C'est la raison documentée du masquage du funnel unifié en prod — ne pas le ressusciter sans en parler à Quang.

✅ **Piège phantom : RÉGLÉ** — `dkIsPhantom(d)` unifie les 3 variantes (mesuré : 65 = 65 sur les 464 devices réels). Le donut Top pays l'utilise déjà. Ne jamais re-coder une 4e variante.
✅ **Fuite Chart.js : RÉGLÉE** — registre `dkCharts` + `dkDestroyCharts()` dans `renderApp`. Tout nouveau chart DOIT s'enregistrer dans `dkCharts`.

Méthode qui a marché 4 fois — la rejouer : (1) sous-agent Explore pour extraire endpoints + formules + DOM du prod, (2) **passe critique** = relire soi-même le code cité avant de coder, (3) porter à l'identique avec les composants v2, (4) prouver la parité en Playwright (prod vs v2, mêmes données live — **extraire le prod par ID d'élément**, c'est le plus robuste), (5) capture + commit scopé.

➡ **Puis revenir compléter la Home (P2)** : brancher MRR total + Utilisateurs actifs (aujourd'hui à `—`) sur les caches produit désormais disponibles, et boucler la part restante de la DoD P2 (agrégats vs somme des apps sur les chiffres payants). MRR total attendu = MRR SWP (18 €) + revenu SV (0 €) + premium DictoKey.

## Actions hors-code déjà faites (P1, P2) / à faire (Claude)

- ✅ P1 : runtime Playwright OK, parité 28/28, commit scopé, captures Telegram livrées.
- ✅ P2 : runtime OK, agrégats vérifiés vs somme des apps, CTA au clic réel, commit scopé, captures Telegram livrées.
- ✅ P3a : parité 21/21, token gate testé, commit scopé, captures Telegram livrées.
- ✅ P3b1 : parité 33/33, commit scopé, capture Telegram livrée.
- ✅ P3b2 : parité summary/pills/pagination/lignes + interactions au clic réel, commit scopé, capture Telegram livrée.
- ✅ P3b3 : charts vérifiés (totaux conservés, 0 fuite Chart.js, palette validée), commit scopé, capture Telegram livrée.
- ✅ P3b4 : parité 15/15 (Firebase + Adoption + Attribution), commit scopé, capture Telegram livrée.
- ✅ P3b5 : parité 7/7 (rétention + usage + mouvements de tier), commit scopé, capture Telegram livrée. **DictoKey complet.**
- ✅ Home complétée : DoD P2 bouclée (MRR 18 € = 18 SWP + 0 SV, Actifs 159 = 148+11+0), commit scopé.
- ✅ P4 Ops : parité Factory 24/24 (2 modes de token), parité agenda Studio, interactions au clic réel, commit scopé, captures Telegram livrées. **Toutes les vues portées.**
- **Git** : toujours commit SCOPÉ (`git add` fichier par fichier, jamais `-A` — dépôt `App` a des frères non commités). Pas de push tant que non demandé.
- **Mémoire** : P1 + observation test Codex autonome à consigner (topic monitoring + `codex.md`).
- **Déploiement** : AUCUN avant P5. Ne redémarrer aucun serveur.

---

**Pour le prochain moteur (résumé 3 lignes)** : refonte dashboard « à côté » — **TOUTES LES VUES (7/7) SONT PORTÉES ET VÉRIFIÉES** (`monitoring-v2.html` **v2.11.0-p4**) : P0 socle, P1 Acquisition (28/28), P2 Home COMPLÈTE (MRR 18 € = 18 SWP + 0 SV, Actifs 159 = 148+11+0), P3a SWP/StoryVoice (21/21), P3b1→P3b5 DictoKey (33/33 + 15/15 + 7/7 + appareils/charts), **P4 Ops Factory (24/24 sur 2 modes de token) + Studio**. 0 erreur console PC 1280 + mobile 384 partout, interactions testées au clic réel. **Il ne reste que P5 = LA BASCULE** (repointer `se7enai-dash` sur v2, rollback = 1 commit) — ⚠ **revenue : go explicite de Quang OBLIGATOIRE**, plus P6 hygiène et P3b2b (non bloquants). Tokens **résolus** et **hérités** (mêmes clés localStorage que la prod, même origine) → rien à recoller. **Divergences VOULUES** à assumer à la bascule (roadmap §7/§8, pas des régressions) : perf Studio séparée organique/boosté, 30/page, donuts top 7, filtre premium corrigé, `Visite→vente` marqué « fenêtres mixtes ». **2 décisions en attente de Quang** : MRR DictoKey (aucune source) et `Visite→vente` (corriger le worker ?). Règles d'or : ne jamais toucher `index.html`/le proxy avant P5, `git add` fichier par fichier (jamais `-A`), vérif en runtime navigateur (`http.server`+Playwright, jamais `file:`), extraire le prod **par ID d'élément**, et **jamais de `reload()` sur une vraie navigation** (annule les fetch du prod → fausse parité). Codex n'a pas pu coder en autonomie (clé API → sandbox read-only) : pour le relayer, son onglet doit être en `--dangerously-bypass-approvals-and-sandbox` (cf `codex.md` §1quater).
