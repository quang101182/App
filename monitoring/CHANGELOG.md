# Changelog — Dashboard monitoring Se7en AI

Le dashboard servi sur `dash.se7enai.com` est `monitoring-v2.html`.
Le worker `se7enai-dash` lit **github.io en direct** : un `git push` suffit à mettre en ligne
(~30-60 s de propagation Pages), aucun redeploy du worker n'est nécessaire.

---

## v2.60.0-liens — 07/11/2026 · Page « Mes apps & liens » (source unique avec le bot Telegram)

- Nouvelle page sous la Vue d'ensemble : Télécharger · Apps web · Sites des produits · Pilotage · Projets hors Se7en AI
  (worker privé `LIENS_PRIVE`) · Chaînes YouTube. Raccourci « Mes apps & liens → » depuis l'accueil.
- **Source unique `data/liens.json`**, lue aussi par `/apps` du bot (n8n) : mettre la liste à jour ici met le bot à
  jour. Fichier public : jamais de lien anonyme ni de secret (le Dossier Vietnam reste dans `/liens` côté n8n).
- Inventaire du 07/11 : `/apps` listait 16 « web apps » dont 8 en 404 (dossiers techniques du dépôt) et 0 APK
  (plus aucun APK publié) ; `/liens` proposait NoteFlowing, NoCodeFlow, The Unseen Child (arrêtés). 18 liens
  publics + 4 privés vérifiés en 200.
- Repli d'une adresse inconnue : explicitement vers l'accueil (la page des liens est désormais en tête de la liste).

---

## v2.59.0-cout — 07/11/2026 · Un seul coût du mois DictoKey (le juste)

- Décision « au plus pragmatique » (Quang) : dictées au **coût réel par moteur** (`/admin/stt-cout`, app `dk`, mois
  heure de Paris — même source que Moteurs & coûts) + LLM + traduction de `/admin/stats`. L'ancienne estimation
  imputait les dictées au tarif Groq alors que MAI tourne à 100 % (0,82 $ affichés contre 0,96 $ réels) : elle ne
  sert plus que de repli, signalé. Tuile DictoKey, en-tête et barres du panneau Infra, accueil : même calcul
  (`dkCoutMois`), format « 1,17 $ » comme Moteurs. Recoupé par un calcul Python indépendant : 1,17 $ identique.

---

## v2.58.2-menu — 07/11/2026 · Menu : rubriques nettement séparées

- Demande de Quang (capture) : chaque rubrique (Produits, Audience, Ops, Archives) devient une bande grise pleine
  largeur avec un espace avant ; entrées en gris doux (graisse allégée) ; seule la page active ressort.
- Le 429 « passerelle DictoKey PC » du bloc Coût venait de la passerelle (quota admin 60/h par IP qui comptait
  aussi les appels authentifiés, épuisé par les bancs du 07/11) : corrigé côté passerelle PC v0.17.2.

---

## v2.58.1-auto — 07/11/2026 · Interrupteur mieux présenté, Moteurs & coûts actualisé

- PC : l'interrupteur quitte la ligne du logo (il y passait à la ligne, capture de Quang) pour une vraie ligne de
  réglage « Actualisation auto · 5 min ● » sous la marque ; téléphone : inchangé (barre du haut), masqué du tiroir.
- **Moteurs & coûts** : le bandeau affichait l'heure d'un premier chargement vide (« il y a 1 h ») alors que ses
  blocs relisent en direct à chaque affichage. Il prend l'heure de la dernière lecture (« lues en direct ») et
  rejoint l'actualisation auto : relu toutes les 5 min s'il reste ouvert (banc : 6 lectures en direct après 1 h).
- Dates ISO restantes (Ondine, journal des refus) en JJ/MM/AAAA.

---

## v2.58.0-auto — 07/11/2026 · Actualisation automatique + corrections du passage QA

- **Interrupteur « Auto »** (menu sur PC, barre du haut sur téléphone), mémorisé par appareil, activé par défaut.
  En entrant dans une page : derniers chiffres affichés tout de suite ; s'ils ont plus de 5 min, mise à jour en
  arrière-plan (« ↻ actualisation… », jamais d'écran de chargement) ; page visible → vérification chaque minute ;
  retour sur l'onglet → mise à jour si besoin. Coupé : seul « Actualiser » recharge. Moteurs & coûts non concerné.
- Une mise à jour en arrière-plan qui échoue garde les chiffres (« ⚠ mise à jour échouée ») au lieu de vider l'écran.
- Corrige : un chargement lent pouvait s'afficher par-dessus la page où l'on venait d'aller. L'accueil est mémorisé.
- QA (agent indépendant, v2.57.0) : menu ☰ refermable (Échap, « ✕ Fermer », page figée derrière) ; dates « Créé »
  sur une ligne ; Ondine lisible sur téléphone ; fantômes signalés dans les statuts ; taux de clic et coût du mois
  expliqués à l'écran ; libellés Factory et chevrons alignés ; message GA4 réduit à une ligne.
- Bancs : 9 scénarios de comportement (0 appel si récent / 1 si vieux / 0 si coupé / course / panne / visibilité)
  + 18 vues : tout vert.

---

## v2.57.0-menu — 07/11/2026 · Menu réorganisé, archives, finitions téléphone

- Menu (maquette v0.3) : DictoKey PC rangé **sous** DictoKey ; StoryVoice étiqueté « repos » ; « Audience » ;
  « Moteurs & coûts » ; rubrique **Archives** pour Factory (arrêtée) et Studio (figé) — rien supprimé.
- Pied du menu : la version (au lieu de « Monitoring v2 · P4 Ops (toutes vues portées) »).
- Bandeau de fraîcheur : une seule ligne sur téléphone (110 → 40 px).
- **Moteurs sur téléphone** : le bouton « Choisir » d'un moteur sortait de l'écran (tableau à défilement horizontal,
  11 éléments hors cadre, défaut antérieur à cette session) → un moteur = une carte empilée.
- Factory : 6 tuiles débordaient de leur carte sur PC → 0.
- Banc : 18 vues (9 onglets × PC/360 px) avec données réelles : 0 erreur, 0 élément coupé.

---

## v2.56.0-dictokey — 07/11/2026 · Onglet DictoKey réorganisé + statut des gratuits

- **17 panneaux → 9** (maquette v0.3) : Activation, Usage (ouverts) ; Abonnements & offres, Rétention, Play Store,
  Site & acquisition, Infra, Appareils, Archives des expériences (repliés, **résumé lisible dans l'en-tête**).
  Rien n'est supprimé : tout est regroupé ; refonte v2.61 et attribution v2.61.7 vont dans les Archives.
- « L'essentiel » en 4 tuiles d'un seul style ; barre de tendance retirée (doublons) ; « hier N » au lieu d'un %.
- **Statut des appareils** (demande de Quang) : en semaine de bienvenue (100/j) · gratuits (30/j) · premium · pro,
  avec les actifs 7 j ; badge **🎁 J3/7** dans la liste. Règle copiée de la passerelle (`dkBienvenueJour`),
  recoupée par un calcul indépendant : 26 / 581 / 32 identiques.
- Migration unique des états de panneaux mémorisés (`monitoring_v2_panels_rev` = 2) : sinon l'ancien « Appareils »
  déplié primait sur le nouveau défaut.
- Côté passerelle (dépôt dictokey, v1.17.3 du même jour) : chargement de l'onglet 31,8 s → 1,8 s.

---

## v2.55.0-accueil — 07/11/2026 · Vue d'ensemble refaite (maquette v0.3 validée)

- L'accueil **charge lui-même** les produits (DictoKey, SubWhisper Pro, StoryVoice, DictoKey PC) avec les mêmes
  fonctions que leurs onglets, **seulement si leurs jetons sont présents** (garde-fou §4 de la roadmap : sans jeton,
  rien n'est appelé — vérifié : 0 appel admin sur la page publique).
- 4 chiffres transverses, chacun de même nature et même période : **abonnés payants** (Google / Polar / PC),
  **actifs aujourd'hui** (DictoKey mobile, « hier N » au lieu d'un % contre une veille complète), **nouveaux appareils
  7 j** (dont en semaine de bienvenue — règle exacte de la passerelle, `dkBienvenueJour`), **coût du mois**.
- Corrige « Utilisateurs actifs 16 » (comptait les clients SWP terminés) et le faux « Alertes 0 · rien à signaler »
  affiché tant que les onglets n'étaient pas ouverts.
- « À surveiller » remonté sous les chiffres clés ; tableau compact des produits (Ondine incluse) au lieu des cartes
  à cumuls depuis l'origine ; chaînes YouTube en grille (un seul titre, aligné à gauche).

---

## v2.54.0-youtube-accueil — 07/11/2026 · Chaînes YouTube sur la Vue d'ensemble

- Le panneau « ▶ Chaînes YouTube » passe de l'onglet Studio à la **Vue d'ensemble** (Quang ne le trouvait pas).
- Il ajoute les chaînes de projets anonymes injectées par le worker privé `se7enai-dash` (`window.__YT_PRIVE`) :
  leur nom n'est jamais écrit dans ce fichier public. Sans worker (github.io), seule @DictoKey apparaît.

---

## v2.53.0-youtube — 07/11/2026 · Studio : panneau « ▶ Chaînes YouTube »

- Une ligne par chaîne (une chaîne par application, décision de Quang du 07/11) : lien vers la chaîne,
  lien vers ses statistiques dans YouTube Studio, date d'ouverture, point de décision de sa feuille de route.
- Liens seulement, aucun appel d'API. Liste `YT_CHANNELS` : @DictoKey pour l'instant.
- ⛔ Fichier public : aucune chaîne de projet anonyme n'y est listée (cf. commentaire de `YT_CHANNELS`).

---

## v2.52.0-studio-fige — 07/11/2026 · Studio : les chiffres TikTok disent leur âge

- Le bloc « 📊 Performances TikTok » affichait le relevé du 17/09 sans alerte (date seulement en pied).
  Au-delà de **14 jours** sans collecte, un bandeau orange en tête annonce « chiffres figés au … (il y a N j) ».
- Note de périmètre : le bloc ne couvre ni @namaeatelier ni les chaînes YouTube (une par application,
  décision de Quang du 07/11).
- Aucune donnée ni collecte modifiée : `data/analytics.json` inchangé.

---

## v2.51.0-bienvenue — 07/11/2026 · DictoKey : activation réelle et semaine de bienvenue

Deux cartes ajoutées à l'onglet DictoKey (passerelle 1.17.x, app 2.77.0 en examen production) :
- **🎯 Activation : 1ʳᵉ dictée** — entonnoir `premiere_dictee` de `/admin/funnel` (installation → 1ʳᵉ vraie
  dictée, sans étape intermédiaire), total et par canal. Au 07/11 sur 28 jours : 54 / 144 = 38 %.
- **🎁 Semaine de bienvenue (gratuits)** — `GET /admin/bienvenue?days=14` : état de l'interrupteur
  (éteinte / ombre / test / active), refus « limite du jour » (429) par jour, refus évités en mode ombre.
  ⛔ Un refus d'appareil en bienvenue sous 100 s'affiche en rouge (BUG). Journal tenu depuis le 07/11.

Banc : `test_dk_tab.py` (Edge headless, vraie passerelle, 360 px) → 12/12.

---

## v2.50.0-revue-statuts — 03/11/2026 · Les statuts affichés ne suivaient plus les décisions

Revue complète des 9 onglets (données réelles, origine `dash.se7enai.com` rejouée) : 0 erreur
console, 0 requête en échec, mais six affichages contredisaient des faits vérifiés.

- **Factory** : arrêtée le 16/09/2026, elle affichait encore « Posting 1/j », « Warm-up » et une
  niche #3 « à créer ». → bandeau d'arrêt, badge « Arrêté le 16/09 », niche fantôme retirée. Les
  compteurs restent (domaines conservés). « Polar · non branché » → « plus en vente depuis le
  20/08 » : le worker `factory-stats` répond `lemonsqueezy_key_missing`, aucun produit n'a été
  remis en vente.
- **Acquisition** : les dons étaient attribués à Lemon Squeezy (fermé le 20/08, le site pointe
  sur Polar) → libellé daté des deux. La tuile « Clic CTA » annonçait « accès anticipé /
  sur-mesure / soutien » alors que le site compte toute fenêtre sauf les mentions légales
  (téléchargement et DictoKey PC compris) → renommée « Fenêtre ouverte », avec ce qu'elle compte.
- **Vue d'ensemble** : la carte DictoKey PC affichait « Lot P3 », texte d'attente du chantier de
  juillet → clics du hub vers DictoKey PC (seule mesure de site qui existe pour lui).
- **Studio** : planning sans aucune date à venir → « Aucune publication depuis le 12/10/2026 »
  au lieu de « périmé », sans présumer d'une pause. Collecte TikTok du 17/09 publiée.
- **DictoKey** : message de chargement « 5 sources, ~20 s » → 7 sources, mesuré 6,6 à 44 s.

---

## v2.25.0-offrable — 17/08/2026 · Le funnel reprochait aux visiteurs de ne pas cliquer un bouton qui n'existait pas

**Le denominateur comptait des gens a qui on n'offre rien.** Ondine est Windows uniquement.
Le site ne rend un lien d'installeur que pour `win` et `other` : `mobile`, `mac` et `linux`
recoivent un texte et une porte email. Or l'etape « clic sur l'installeur » se rapportait a
**toutes** les ouvertures de modale. Mesure du jour : 65 ouvertures dont **28 mobile et 3 mac**,
34 clics → le tableau affichait **52 %** de conversion. Le vrai chiffre est **100 %** : sur 34
visiteurs a qui un bouton a ete propose, 34 ont clique. On lisait un echec produit la ou il n'y
avait qu'un defaut de comptage — et le vrai sujet, lui, restait invisible.

- Nouvelle etape **« Installeur propose »** entre l'ouverture de la modale et le clic. Elle nomme
  ce qui manquait : *« 31 sans bouton (Ondine est Windows) → porte email »*.
- Nouvelle ligne **« Rattrapage sans bouton »** : combien de ces visiteurs laissent leur email pour
  recevoir le lien sur leur PC. C'est le seul chemin de conversion du trafic TikTok, massivement
  mobile, et personne ne savait s'il fonctionnait. Alimentee par `f:waitlist:<provenance>`,
  emise par le site depuis sa **v0.19.0** — donc **0 jusqu'a nouvelle mesure**, ce qui n'est pas la
  meme chose que « ca ne convertit pas ». La note l'ecrit, pour qu'on ne lise pas un zero neuf
  comme un verdict.
- **Dons enfin affiches.** `f:donate` etait emis par le site depuis le 19/07 et lu par **personne**.
  Meme famille que le bug `dl_view:` du 21/07 : une mesure qui n'arrive jamais a l'ecran ne se
  signale pas toute seule.
- **Ecart de clics explique** : `f:download` (34) contre la somme par OS (26). Les deux series ne
  peuvent pas coincider — avant le correctif du 21/07, seul le compteur global partait. Affiches
  cote a cote sans un mot, ils se lisaient comme une contradiction.

Preuve : banc Playwright sur les donnees de prod, valeurs lues au DOM et **taux recalcules a la
main** ; mutation verifiee rouge (en restaurant l'ancien denominateur, le banc echoue).

> ⚠️ **Trou de journal assume** : les versions **v2.20.0 a v2.24.0** (tuile Leads, telechargements
> reels GitHub, origine des visites) ne sont documentees que dans les commentaires du code et les
> messages de commit. Elles ne sont pas reecrites ici apres coup — ce serait de la reconstitution.

---

## v2.19.0-ondine — 21/07/2026 · Ondine entre au Studio, et un funnel qui ne mesurait rien

**Studio** — Ondine devient un projet de plein droit (couleur `--ondine` `#2dd4bf`, choisie **par mesure** :
contraste 9,36:1 sur la surface, ecart DeltaE minimal 15,4 contre --dk/--swp/--sv en simulation
protanopie/deuteranopie/tritanopie ; #14b8a6 tombait a 6 = confondu avec DictoKey). Sa serie de 6 videos
est au planning du 22 au 27/07 : 3 FR sur TikTok, 3 EN sur Instagram+Facebook, conformement au lane-split.

Deux ajouts nes du contenu lui-meme :
- champ `title` optionnel sur les entrees de planning — six cartes « Ondine · FR · TikTok » etaient
  autrement indistinguables, on ne savait pas quelle video partait quel jour ;
- mention de **pause volontaire** sur DictoKey / StoryVoice / SubWhisper Pro (arbitrage Quang du 21/07).
  Sans elle, un agenda vide du 30/06 au 22/07 se lit comme un abandon ou une panne de production.

**Acquisition — un bug qui affichait un zero pour une cle qui n'existait pas.** L'etape « Modale DL
ouverte » cherchait les compteurs sous le prefixe `dl_view:` alors que le site les emet TOUS prefixes
`f:` (`beaconFunnel`, site/index.html:977 → `f:dl_view:win`). Elle affichait donc **0 avec 4 ouvertures
reelles en base**, et comme elle sert de denominateur aux deux etapes suivantes, « Code debloque » et
« Telechargement » n'avaient plus de taux du tout.

**Acquisition — le KPI vitrine passe en tete.** Si Ondine sert de vitrine aux autres apps, « Clics
sortants » est le chiffre qui dit si la vitrine fait entrer quelqu'un : il etait en derniere position,
sa ventilation par app noyee en bas du funnel. Il ouvre desormais le recap, avec son taux (affiche
seulement au-dessus de `ACQ_MIN_DENOM = 30` visites) et sa destination.
Etat au 21/07 : **1 clic sortant pour 94 visites**.

La tuile « Telechargements » porte enfin sa vraie nature : elle compte des **clics**, pas des personnes
— le gel etant actif, ce bouton n'existe qu'apres un code debloque (8 clics pour 2 deblocages).

---

## v2.18.0-acq-dl — 19/07/2026 · Le téléchargement Ondine devient mesurable

Le CTA du site est passé de « accès anticipé » à « Télécharger » (release publique), mais
l'onglet acquisition mesurait encore l'ancien parcours — le funnel s'arrêtait à la waitlist
(reproche Quang : « je ne vois pas l'analytique des clics/téléchargements »).

**Côté site (v0.13.1, déployé)** — le parcours DL émet désormais :
- `dl_view:<os>` — ouverture de la modale DL, ventilée par OS (win / mobile / mac / linux / other) ;
- `f:unlock` — code d'accès validé (ère du gel : les testeurs débloquent avant de télécharger) ;
- `f:download` + `f:download:<os>` — clic RÉEL sur l'installeur (avant : le bouton débloqué
  n'émettait rien, et le déblocage était compté comme un téléchargement — deux trous).

**Côté dashboard** — le funnel du hub gagne 3 étapes (📥 Modale DL ouverte, 🔓 Code débloqué,
⬇ Téléchargement, avec ventilation par OS en note) + tuile « Téléchargements » dans le récap.
Aucune étape existante modifiée (parité conservée).

Preuve : 16/16 Playwright (PC 1280 + mobile 360, données réelles gateway-pro, 0 erreur console,
0 overflow).

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
