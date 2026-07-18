# Changelog — Dashboard monitoring Se7en AI

Le dashboard servi sur `dash.se7enai.com` est `monitoring-v2.html`.
Le worker `se7enai-dash` lit **github.io en direct** : un `git push` suffit à mettre en ligne
(~30-60 s de propagation Pages), aucun redeploy du worker n'est nécessaire.

---

## v2.16.0-honest — 18/07/2026 · Les 2 décisions tranchées : deux chiffres qui n'en étaient pas

### 1. « MRR total » → « Abonnements SWP + StoryVoice »

La tuile s'appelait « MRR total » alors qu'elle **excluait structurellement DictoKey**, le produit
principal. Un total qui omet le plus gros poste n'est pas un total. Le titre porte maintenant son
périmètre réel.

**Pourquoi on ne la complétera jamais avec DictoKey** (enquête du 18/07, sources vérifiées) :

- DictoKey Premium **est** un abonnement — `BillingManager` : `ProductType.SUBS` ×3, **zéro**
  `INAPP`, zéro `consumeAsync` — à **4,99 €/mois ou 34,99 €/an** (`strings.xml:565-566`). Un MRR y
  serait donc conceptuellement légitime.
- **Mais le nombre d'abonnés payants n'existe dans aucune API.** La seule quantité disponible est
  le compte d'appareils « premium » (**18**), et **il ne mesure pas des payants** : l'app marque
  premium dès que Play signale un abonnement actif (`BillingManager.kt:124` — *« Google Play says
  this user has an active subscription → mark as premium »*), or **un essai gratuit de 7 jours est
  un abonnement actif**.
- **L'arithmétique tranche** : `18 × 4,99 = 89,82 €/mois` contre **24,38 € nets cumulés depuis
  l'origine** (un unique abonnement annuel italien). Le « prix en dur × premium actifs » se
  tromperait d'un **facteur ~45**. Ce n'est pas une approximation, c'est un faux.
- 🔓 **Nouveauté utile** : la vraie source (rapports financiers Play sur GCS) **est de nouveau
  accessible** — testé le 18/07, le zip se télécharge, **plus de 403** (l'ACL a propagé depuis
  avril). Il reste un bug de dézippage dans `unzipSingleEntry` du gateway DictoKey. **C'est le
  chemin d'un vrai KPI de revenu** — un lot en soi, pas une constante à inventer.

### 2. Factory : suppression du taux « Visite→vente »

Deux défauts distincts, deux traitements distincts :

- **`Visite→vente` n'était pas un ratio imprécis, c'était un calcul sans objet** : ventes
  **cumulées depuis l'origine** ÷ visites **depuis le 25/06**. Le marquer « ⚠ fenêtres mixtes »
  (v2.11) laissait le nombre à l'écran — or **un chiffre faux annoté se lit comme un chiffre**.
  Remplacé par les deux faits bruts, chacun avec sa fenêtre.
- **`Visite→clic` et `Visite→dl` sont bien définis** (même source, même fenêtre) mais étaient
  affichés sur 6 à 25 visites. Sous **30 visites** (`FACTORY_MIN_DENOM`), on montre désormais les
  **comptes bruts** (`2/6`) et non un pourcentage — même règle que la rétention en v2.12.2 : ne pas
  donner l'autorité d'un taux à du bruit.

*L'autre option envisagée — borner `/overview` côté worker `factory-stats` — a été écartée : elle
produirait un taux propre sur 6 visites, donc un non-résultat d'allure fiable, en touchant un
worker de production pour un chiffre qui resterait du bruit.*

## v2.15.0-p6 — 18/07/2026 · P6 Hygiène (dernier lot de la refonte)

**Le chantier de refonte est terminé.**

- 🐛 **Supprimé un panneau qui mentait à l'utilisateur** : la vue DictoKey affichait
  « ⏳ Section restante — Panneau détail par appareil (expand) — lot P3b2b » alors que ce
  panneau est **livré depuis la v2.14.0**. Le dashboard annonçait comme « à faire » une
  fonctionnalité présente — et précisément celle dont la perte avait été signalée.
- 🧹 Supprimé le fragment de sélecteur CSS mort `.icon-button` (aucune occurrence dans le
  HTML ni le JS ; `.menu-button` conservé, il est bien utilisé).
- 📄 Ce changelog.

**Audit de code mort (fichier entier, chaque identifiant vérifié)** : 122 fonctions top-level,
**0 morte** ; **0 constante** jamais lue ; **0** `if (false)` / bloc commenté / `console.log`.
La v2 était déjà propre — P6 n'avait quasiment pas de matière.

**Non fait, volontairement** — 5 groupes de helpers font double emploi
(`acqPct`/`swpPct` sont *strictement identiques* ; `facPct` quasi ; 3 formateurs de temps
relatif ; 3 formateurs de nombre ; 2 formateurs date+heure). Les fusionner est un
**refactor**, pas de l'hygiène : les sorties diffèrent (`il y a 5 min` vs `hier` vs
`Il y a 5min`) et le fichier est en production. À traiter comme un lot séparé si souhaité.

## v2.14.0-p3b2b — 16/07/2026 · Détail par appareil au clic

Retour de la fonctionnalité **perdue à la bascule P5** : panneau au clic sur une ligne
d'appareil (3 fenêtres Aujourd'hui / 7 j / 30 j, langues, modes, paires, audio, mots, latence,
pays), « Tout déplier » par batch de 6, état conservé à travers pagination et filtres.

Bugs de la v1 corrigés au passage : fetch **sans `signal`** (jusqu'à 50 requêtes en vol, rien
n'était annulé) · ordre de `daily` présumé au lieu d'être trié · « 30 derniers jours » affiché
avec 4 jours d'historique · `latMax` calculé jamais affiché · 401 muet dans 50 panneaux.

> ⚠️ **La leçon du lot** : cette fonctionnalité avait été identifiée, documentée, puis qualifiée
> de « non bloquante » — par moi — et la bascule livrée sans elle. Sa valeur n'était pas la
> mienne à décider. **Une bascule exige la parité FONCTIONNELLE, pas seulement celle des chiffres.**

## v2.13.x — 16/07/2026 · Rôle « vitrine / au repos » + bouton Actualiser unique

Un produit au repos (SubWhisper Pro, StoryVoice) n'est plus présenté comme une anomalie.

## v2.12.x — 16/07/2026 · Persistance + honnêteté des chiffres

- **Panneaux pliés/dépliés persistés** (`monitoring_v2_panels`).
- **Cache persisté** (`monitoring_v2_cache_*`) : règle 3 problèmes d'un coup — la fresh-bar
  était condamnée à rester verte (cache en mémoire seule → refetch à chaque ouverture →
  « à l'instant » perpétuel), DictoKey passe de **20 s à 0,2 s** à l'ouverture, et la Home
  n'affiche plus `—` à froid.
- **`0 %` remplacé par « non mesuré »** là où le numérateur est absent (conversion du bandeau
  bulle). Un zéro affirmé déclenche des décisions ; un trou déclaré les empêche.
- **Rétention** : plus de « 0 % » en rouge sur des cohortes d'**une seule personne** → gris +
  « sur n=X · non significatif ». Une couleur est un jugement.

## v2.11.1 — 16/07/2026 · Indicateur de chargement

La v2 n'en avait aucun alors que la v1 en avait un → DictoKey (5 sources, jusqu'à **22 s** à
froid) était un écran blanc muet. *Une parité chiffrée ne prouve pas l'UX.*

## v2.11.0-p4 — 16/07/2026 · P5 BASCULE + P4 Ops (Factory + Studio)

`dash.se7enai.com` sert la v2. Toutes les vues (7/7) portées et vérifiées.

Bug le plus grave trouvé dans la v1 : « Performances TikTok » affichait **82 226 vues** sous le
libellé « boostées **exclues** » alors que le filtre ne les excluait pas → **81,5 % des vues
affichées étaient achetées**. On pilotait sur un chiffre 5× trop optimiste. La v2 sépare
organique (15 226) et boosté (67 000), **jamais additionnés**.

## v2.1.0 → v2.10.0 — 16/07/2026 · Portage vue par vue (P1 → P3b5)

Acquisition (parité 28/28) · Home (MRR 18 € = 18 SWP + 0 SV, Actifs 159 = 148+11+0) ·
SubWhisper Pro + StoryVoice (21/21) · DictoKey complet : overview/Play Store/infra (33/33),
appareils, charts & donuts, Firebase/adoption/attribution (15/15), rétention (7/7).

Bugs de la v1 corrigés : filtre premium DictoKey (`getDeviceCategory()` oubliait
`tier === 'premium'` en KV → 16 pills au lieu de 18, et ils disparaissaient si on décochait
« free ») · fuite Chart.js (`window._cLatency` jamais détruit) · `dkIsPhantom` défini **3 fois**
avec des variantes.

## v2.0.0-p0 — 16/07/2026 · Socle

Shell nav, routeur par hash, `fetchApp`, composants (`KpiTile`/`Panel`/`FunnelBar`/
`ProductCard`/`Alert`/`FreshBar`), palette dataviz validée pour la daltonie contre la surface
réelle `#141a26` (5/5 PASS).

---

## Divergences VOULUES vs l'ancienne v1 — ce ne sont pas des régressions

| Sujet | v1 | v2 | Pourquoi |
|---|---|---|---|
| Perf TikTok | 82 226 vues « boostées exclues » | 15 226 organique **+** 67 000 boosté, séparés | Le libellé v1 était faux (décision Quang) |
| Appareils / page | 50 | 30 | Demande Quang — n'affecte aucun chiffre |
| Donuts | `couleur[i % n]` → hues répétées | top 7 + « Autres » | Règle dataviz ; **totaux conservés** |
| Filtre premium DictoKey | 16 | 18 | Bug v1 corrigé |
| `Visite→vente` Factory | affiché nu | marqué « ⚠ fenêtres mixtes » | Ratio à fenêtres mixtes (ventes cumulées ÷ visites depuis le 25/06) |

## Décisions en attente

1. **MRR DictoKey** — n'existe dans **aucune** API (revenus Premium gérés par Google Play
   Console). Prix en dur × premium actifs / API Play Developer / laisser tel quel ?
   *Aucun prix ne sera inventé.*
2. **`Visite→vente` Factory** — borner `/overview` côté worker, ou garder le marquage ?

## Archive

`archive/index-v1.23.0.html` = l'ancien dashboard v1, archivé le 18/07/2026 après 48 h de
surveillance. **Toujours le filet de rollback**, joignable sur
`dash.se7enai.com/archive/index-v1.23.0.html`. Voir `archive/README.md`.
