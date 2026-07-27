# Revalidation — repartir d'une base propre

> ## ⏱ Où on en est — session du 27/07 après-midi (app **v1.24.0**)
>
> **Étapes 1, 2 et 3 : faites.** Étape 4 : commencée, elle a livré le défaut le plus grave.
>
> | Étape | État | Ce qui en est sorti |
> |---|---|---|
> | 1 · Samsung réel | ✅ **12 gestes sur 12**, 0 erreur JS | 3 défauts, tous corrigés (v1.22.1 → v1.23.0) |
> | 2 · Rejouer les bancs | ✅ tous verts, mutations rouges | 1 banc **périmé** qui accusait l'app à tort |
> | 3 · Bancs manquants | ✅ **5 sur 5 écrits**, tous falsifiés | les 20 fonctions ont enfin un filet |
> | 4 · Effets de bord | ✅ **5 sur 6 mesurées** | 1 défaut corrigé (v1.24.0) + 2 constats · reste l'ingestion |
> | 5 · Nettoyage | ✅ projets et fiches de test supprimés | restent `test A`, `Test A`, `Salle de classe` |
>
> **La lacune de fond est levée** : le Samsung `SM-A326B` a servi, au doigt, avec
> `scripts/samsung.py` (CDP pour mesurer, `adb` pour toucher). Deux des trois défauts du
> jour ne se voyaient que là.
>
> **Décidé et livré (v1.24.0)** : la pose garantie n'est plus proposée quand le casting a ≥ 2
> personnages. L'étape 4 est mesurée à **5 combinaisons sur 6** (`test_compositions.py`, 18
> vérifications, **zéro GPU** — il lit le graphe envoyé à ComfyUI au lieu de générer).
>
> **Chantiers n°1 et n°2 livrés** : images de référence sur les fiches (v1.25.0, IPAdapter) et
> **zone ciblée** (v1.26.1, inpaint au doigt). Les deux 🔴 du §3 sont fermés.
>
> | **v1.53.0** | **la référence est recadrée sur le visage** à l'entrée (les deux chemins : import et 🎨 Dessiner → garder) · aucun visage ⇒ gardée entière, et l'app le dit · route `POST /manga/crop_ref` | `test_crop_ref_app.py` — 10 ✓, mutation rouge · `test_crop_ref.py` (GPU) : **4/6 → 6/6** personnages |
>
> ~~**🟠 Le verrou suivant, découvert le 28/07** : une référence qui est une planche de design fait
> hériter la case de sa composition.~~ → ✅ **traité le jour même (v1.53.0)**, mesuré 4/6 → 6/6 sur le
> nombre de personnages. ⚠ Le **placement** par identité, lui, ne progresse pas (4/6 → 3/6, bruit) :
> le recadrage règle la composition, pas l'attribution.
> 🟠 **Reste vrai** : **passer les fiches par 🧹 Nettoyer** est un préalable — avec leurs tags actuels
> (`character design`, `simple background`), la case sort en planche de personnage quoi qu'on fasse
> aux images. Les fiches de Quang n'ont pas été modifiées, c'est à lui de lancer le nettoyage.
>
> **Prochain** : la bibliothèque de références (phase 8) ou le mode chapitre automatique
> (phase 7) — cf. §4. Et la dernière combinaison de l'étape 4 (ingestion puis séquence).
>
> ### ⏱ Suite de la session — soir du 27/07 (app **v1.29.0**)
>
> L'essai du bouton 🎬 par Quang a ouvert **huit** demandes de conception, toutes arbitrées et
> ordonnées dans `ROADMAP.md` § **Phase 12**. Deux sont déjà livrées :
>
> | Version | Livré | Banc |
> |---|---|---|
> | **v1.28.0** | vitesse de défilement **globale et persistante**, réglable pendant la lecture · largeur PC ramenée à une colonne (760 px) · carte **Moteur** (VRAM réelle, arrêt avec garde-fou, confirmation à l'écran) | `test_lecture_vitesse.py` — 14 ✓, mutation rouge |
> | **v1.29.0** | **ouvrir un projet existant** depuis l'onglet Projets · la galerie dit quel projet elle montre et peut en regarder un autre sans déplacer l'atelier | `test_ouvrir_projet.py` — 11 ✓, mutation rouge |
> | **v1.31.0** | **⚙ Affiner : 11 boutons → 6** · le badge 🎬 ne ment plus après suppression (+ 2 défauts de seed trouvés par le banc) · **bandeau moteur + VRAM** aligné sur la colonne de l'app | `test_affiner_et_badge.py` — 14 ✓, mutation rouge |
> | **v1.33.0** | pastille **« 🖥 Local »** cliquable en entier (comme Generate Studio) · témoin proxy visible seulement en panne · **onglets compacts (1 ligne) et figés** sous le bandeau | test live du moteur — 9 ✓ (coupe + rallume réels) |
> | **v1.34.0** | **question de sécurité avant de couper le moteur** (+ la seconde, quand une génération tourne) · **les 5 dernières boîtes natives** de l'app remplacées par une question à l'écran | `test_arret_moteur.py` — 14 ✓, moteur réellement coupé puis rallumé |
> | **v1.35.0** | **zone + consigne écrite** (« ce que tu veux à cet endroit », facultatif) · 🐛 **`p.zone` n'était pas persistée depuis la v1.26.1** — la zone tracée disparaissait au rechargement | `test_zone_consigne.py` — 14 ✓, mutation rouge |
>
> | **v1.37.0** | **🎨 Dessiner un personnage** depuis sa fiche (3 vues, on garde la bonne → référence IPAdapter) · 🐛 **la fiche de personnage échappait à la traduction obligatoire** depuis la v1.23.0 — une fiche en français est **invisible dans toutes** les cases qui la castent | `test_perso_dessiner.py` — 15 ✓, génération réelle, mutation rouge |
>
> | **v1.38.0** | **visionneuse plein écran** (zoom ancré + pan borné + ◀ ▶ + action « garder ») · nombre d'images **annoncé** · **liste de personnages repliée** (1 fiche = 1 ligne) + filtre | `test_visionneuse_et_liste.py` — 20 ✓, mutation rouge |
>
> | **v1.39.0** | **la troupe du manga** : base → troupe (projet) → casting (planche), avec héritage des planches neuves · ligne remontée sous le choix de planche · 🐛 deux `prompt()` natifs oubliés dans « Démarrer une planche » | `test_troupe.py` — 12 ✓, mutation rouge |
>
> | **v1.40.0** | **💬 Répliques** : l'app propose 3 dialogues d'après les cases précédentes et le casting ; une réplique choisie **ajoute** une bulle et n'écrase jamais un texte écrit à la main | `test_repliques.py` — 13 ✓, mutation rouge |
>
> | **v1.41.0** | **case-groupe** : une séquence occupe un seul bloc (◀ n/N ▶ + déplier), **sans fusionner les données** — l'export continue de voir toutes les cases | `test_case_groupe.py` — 12 ✓, mutation rouge |
>
> | **v1.42.0** | **réordonner une séquence** au tap (⇤ ⇥, pas de glisser-déposer) — l'ordre de la **planche** suit, donc l'export aussi | `test_case_groupe.py` — 16 ✓, mutation rouge |
>
> | **v1.43.0** | **🔎 Qu'est-ce qui cloche ?** — Pixtral regarde la case, dit le défaut en français et propose une correction régénérable ; le score annonce **ce qu'il mesure** (conformité, pas qualité) | `test_critique.py` — 11 ✓, mutation rouge |
>
> | **v1.46/47.0** | 🐛 trois défauts trouvés **par le journal du Honor** : `castingPage()` renvoyait `null` (6 erreurs JS pendant que Quang ajoutait quelqu'un) · la troupe se **doublonnait** à chaque tap · **+ Case** n'existait qu'en haut de planche | `test_troupe` 12 ✓ · `test_perso_dessiner` 15 ✓ |
>
> | **v1.52.0** | **deux images de référence dans une même case** (une par personnage, chacune bornée à sa moitié) · 🐛 la référence se choisissait sur le casting de la **planche**, pas de la case — la v1.51.0 avait corrigé les tags, pas l'image | `test_deux_refs_app.py` — 20 ✓, mutation rouge, + `--live` (image réelle) et `--samsung` (6 ✓) |
>
> ⚠️ **Règle qui sort de la v1.52.0 — un banc ne vérifie pas un NUMÉRO de nœud.**
> `test_references.py` exigeait que le KSampler consomme le nœud « 22 » : renuméroter pour
> pouvoir en chaîner deux l'a fait rougir sur un graphe pourtant juste. Un numéro est une
> convention interne ; ce qui doit tenir, c'est le **branchement**.
> Et `test_references.py` était **mort depuis la v1.38.0** pour la même raison que
> `test_perso_dessiner` : la liste repliée fait que le champ « ＋ image de référence »
> **n'existe pas** tant que la fiche est fermée — le banc accusait l'app. Réparé.
>
> 🎨 **Les « taches noires » sur les personnages : c'était `ink`** — mesuré, pas supposé
> (`scripts/mesure_taches_encre.py`, même seed, un tag retiré à la fois) : le modèle dessine
> littéralement de l'encre **qui coule** sur les visages ; `high contrast` noircissait le reste
> (sol noir à **88 %** → **3 %** sans les deux). Retirés du style par défaut, **les trames restent**.
> Les projets déjà créés gardent leur style — l'onglet Projet propose le nettoyage, il ne le fait pas
> dans le dos de Quang.
>
> ⚠️ **Règle qui sort de la v1.47.0 — les FICHES ne portent ni couleur ni style** : « red hair » dans
> une app N&B fait basculer l'image **en couleur**, et « sketch » dans une fiche contredit le
> **négatif** du projet. Une fiche décrit la **valeur** (clair/foncé) et des traits ; le style
> appartient au projet.
>
> ⚠️ **Et un banc peut mourir en silence** : `test_perso_dessiner` était cassé depuis la v1.38.0 (la
> liste repliée avait rendu son bouton invisible) — il coûte 2 min de GPU, donc il n'avait pas été
> rejoué. **Un banc coûteux qu'on ne rejoue pas ne protège plus rien.**
>
> ⚠️ **Règle qui sort de la v1.39.0 — sur les BANCS** : une `const` de module n'est **pas**
> remplaçable (`window.x = …` ne l'atteint pas, la résolution lexicale gagne) ; et une mutation doit
> viser **le comportement**, pas une ligne — ici l'héritage se joue à l'écriture *et* à la lecture,
> donc casser un seul des deux ne rougissait pas. Un banc vert dont la mutation ne rougit pas ne
> prouve rien.
>
> ⚠️ **Règle qui sort de la v1.37.0** : **traduire n'est pas enrichir.** Une traduction automatique
> ne doit **rien inventer** — sinon elle alourdit la fiche de traits que Quang n'a pas écrits, *et*
> laisse le français partir quand même. Consigne stricte (`TRAD_CONSIGNE`) pour la traduction,
> consigne d'enrichissement **seulement** derrière un bouton explicite.
>
> ⚠️ **Règle qui sort de la v1.35.0, à ne pas réapprendre** : la table `manga_panels` a des colonnes
> **fixes**. Tout champ d'une case posé **hors de `recipe`** est accepté par l'API puis **jeté à
> l'écriture, sans erreur**. Un nouveau champ va dans `recipe`, ou il n'existera pas demain.
>
> 🔴 **Le point qui commande la suite** (Quang : *« on empile beaucoup de choses […] on peut vite
> perdre l'ergonomie »*) : compté dans le code, une case générée affiche **11 boutons**. Rien de
> neuf ne doit s'ajouter à cette rangée — d'où le chantier **12.0 « ⚙ Affiner »**, qui conditionne
> les autres. Détail et ordre d'exécution : `ROADMAP.md` § Phase 12.

> Écrit le **2026-07-27** en fin de session, à la demande de Quang :
> *« dresse une feuille de route bien détaillée, revalide tout ce qu'il faut valider, avec le
> smartphone Samsung ou sur PC. Nous repartons d'une base propre et complètement solide, entièrement
> déboguée, et nous faisons la suite. »*
>
> **À faire AVANT toute nouvelle fonction.** Ce document est la porte d'entrée de la prochaine
> session ; la conception vit dans `ROADMAP.md`, ici on ne parle que de **remise au propre**.

---

## 0. Pourquoi ce document existe

En une seule session, l'app est passée de **v1.0.1 à v1.22.0** — 22 versions, dont une quinzaine de
correctifs empilés les uns sur les autres, plusieurs sur les **mêmes fonctions** (la génération, le
prompt, la séquence). Chaque changement a été mesuré isolément ; **l'ensemble ne l'a jamais été**.

C'est exactement la situation où les effets de bord se logent : chaque pièce est vérifiée, la
composition ne l'est pas.

### ✅ La lacune est levée — le Samsung a servi (27/07 après-midi)

Les 12 gestes ont été joués **au doigt** sur le `SM-A326B`, via `scripts/samsung.py` :
**CDP pour mesurer, `adb` pour toucher**. Deux des trois défauts du jour ne se voyaient
que là. Trois pièges du harness, payés et désormais tenus par le code :

- un **onglet périmé** a répondu à la place de l'app (Chrome gardait une v1.2.0 en veille) :
  le harness compare maintenant la version de l'écran à celle du fichier source, et refuse
  de travailler sinon ;
- l'offset de la **barre d'URL** faisait atterrir les taps dans la barre de recherche de
  Chrome : il est **mesuré** par calibration, jamais deviné, et chaque tap vérifie après
  coup que le doigt a bien atteint sa cible ;
- ⛔ **ne jamais fermer le clavier par `KEYCODE_BACK`** : sans clavier ouvert, BACK ferme
  l'onglet ou quitte Chrome (on s'est retrouvé dans Macro Deck). `close_keyboard()` fait
  un `blur()`.

<details><summary>Le constat d'origine (avant la session du 27/07 après-midi)</summary>

**Rien n'a été testé sur le Samsung réel.** Tous mes bancs tournent dans un Edge piloté par
Playwright, en viewport 360×780 émulé. C'est utile — ça a attrapé le clavier, la hauteur des cases,
le débordement de la barre d'onglets — mais **un navigateur émulé n'est pas un téléphone** : pas le
même moteur de rendu tactile, pas le même clavier virtuel, pas la même gestion mémoire, pas le même
réseau (Quang passe par le tunnel Cloudflare, mes bancs par `127.0.0.1`).

Or la règle du projet est explicite : *le Samsung `SM-A326B` est mon device de test dédié, branché en
permanence*. Je ne m'en suis pas servi de la session. **C'est la première chose à corriger.**

</details>

---

## 1. Inventaire de ce qui doit être revalidé

Livré aujourd'hui, dans l'ordre chronologique. La colonne « testé » dit **comment**, pas si c'est bon.

| # | Fonction | Version | Testé | Banc |
|---|---|---|---|---|
| 1 | Clavier qui ne se referme plus | 1.7.1 | Playwright 360 px | `test_clavier_mobile.py` (+ `--muter`) |
| 2 | Galerie : plein écran, sélection, suppression | 1.8.0 | Playwright + **disque** | `test_galerie_live.py` |
| 3 | Onglets qui passent à la ligne | 1.8.0 | responsive-audit | `.claude/scripts/responsive-audit.py` |
| 4 | Fil conducteur (« étape suivante ») | 1.9.0 | Playwright | `test_ergonomie_case.py` |
| 5 | Hauteur d'une case sur téléphone | 1.9.0 | Playwright + `--muter` | `test_ergonomie_case.py` |
| 6 | Témoin d'activité + refus persistants | 1.10.0 | **génération réelle** | `test_temoin_activite.py` |
| 7 | Version affichée à l'écran | 1.10.1 | navigateur réel | `check_version.py` |
| 8 | Régénérer une case (cache ComfyUI) | 1.11.0 | génération réelle | `test_regenerer_et_log.py` |
| 9 | Journal envoyé au PC, par appareil | 1.11.1 | fichier sur disque | `lire_log.py` |
| 10 | « Démarrer une planche » | 1.12.0 | **Samsung réel** + base | `test_demarrage.py` (+ `--muter`) |
| 11 | Prompt : plus de personnage par défaut | 1.13.0 | génération réelle | `test_prompt_chaine.py` (+ `--muter`) |
| 12 | ✨ Améliorer (FR → tags) | 1.13.0 | **Samsung réel** | `test_prompt_chaine.py` — 2 bugs corrigés le 27/07 |
| 13 | Base de personnages + casting | 1.14.0 | Playwright + base | `test_personnages.py` (+ `--muter`) |
| 14 | Aperçu du prompt + annonce de traduction | 1.23.0 | **Samsung réel** | `test_prompt_chaine.py` |
| 15 | **Traduction OBLIGATOIRE** (≠ améliorer) | 1.23.0 | **Samsung réel** | `test_prompt_chaine.py` · `test_sequence_live.py` |
| 16 | Style du projet | 1.17.0 | Playwright | *(toujours sans banc dédié)* ⚠ |
| 17 | Comptage des personnages | 1.19.0 | **Samsung réel** | `test_prompt_chaine.py` (4 cas + ordre) |
| 18 | 💡 3 suites | 1.18.0 | **Samsung réel** | `test_suites.py` (+ `--muter`) |
| 19 | 🎬 Séquence (11 gestes + libre) | 1.21.0 | **Samsung réel** | `test_sequence_live.py` — garde-fou casting v1.24.0 |
| 20 | Séquence : cases séparées + ▶ jouer | 1.22.0 | **Samsung réel** | `test_sequence_live.py` (+ `--muter`) |

~~**11 fonctions sur 20 n'ont pas de banc rejouable.**~~ → ✅ **couvert le 27/07 (étape 3 terminée).**
Les 5 bancs manquants sont écrits, verts, et **chacun a été falsifié par mutation** :

| Banc | Vérifications | Couvre |
|---|---|---|
| `test_prompt_chaine.py` | 26 | fonctions 11, 12, 14, 15, 17 — réponse LLM figée |
| `test_personnages.py` | 13 | fonctions 13, 17 — fiche → casting → prompt → suppression |
| `test_sequence_live.py` | 19 | fonctions 19, 20 — 2 vraies vignettes (~30 s GPU) |
| `test_suites.py` | 12 | fonction 18 — lit la **requête**, pas la réponse |
| `test_demarrage.py` | 8 | fonction 10 — relit la **base**, pas l'écran |

Et un banc **existant** était périmé : `test_regenerer_et_log.py` visait `log-manga-live.json`
alors que le journal est écrit **par appareil** depuis la v1.11.1. Il criait « journal ABSENT »
sur une app qui l'envoyait très bien — un rouge qui n'accusait que lui-même. Corrigé.

---

## 2. Le plan, dans l'ordre

### Étape 1 — Sur le Samsung RÉEL ✅ FAIT le 27/07 (12 gestes sur 12, 0 erreur JS)

> Rejouable : le harness est `scripts/samsung.py`. Les 12 gestes ci-dessous restent la
> référence — c'est le parcours réel de Quang, à refaire après tout changement d'UI.

```bash
ADB=C:/Users/quang/AppData/Local/Android/Sdk/platform-tools/adb.exe
$ADB devices                          # SM-A326B, serial RFCT32ATWGJ
$ADB shell dumpsys power | findstr mWakefulness     # doit dire Awake
$ADB reverse tcp:8190 tcp:8190        # l'app servie par le proxy du PC
```

Puis, **à la main sur le téléphone**, dans cet ordre — c'est le parcours réel de Quang :

1. Ouvrir l'app, vérifier que le bandeau affiche **la bonne version**.
2. **Démarrer une planche** (3 cases). Vérifier que les 3 cases apparaissent.
3. Écrire une action **en français** dans la case 1, **au doigt** → le clavier doit rester ouvert.
4. Vérifier l'**aperçu** sous la case (« Sera envoyé… ») et l'alerte français.
5. **Générer** → le témoin doit apparaître, nommer l'action, puis annoncer la fin.
6. **✎ Lettrage** : poser une bulle, la déplacer **au doigt**, écrire du texte.
7. **✅** puis **❌** : le bouton doit s'allumer, le badge apparaître, et **la case rester visible**.
8. **💡 3 suites** sur la case 2, en reprendre une.
9. **🎬 Séquence** sur la case 2 → 3 vignettes → **▶ Jouer**.
10. **Galerie** : plein écran, sélectionner 2 images, supprimer.
11. **Exporter** en PNG puis en PDF.
12. Onglet **Réglages** → **Envoyer le journal au PC**, puis le lire :
    `python scripts/lire_log.py --ou mobile --n 60`

> **Critère** : les 12 gestes passent, **0 erreur JS dans le journal**, et rien n'oblige à faire
> défiler pour voir ce qu'on vient de toucher.

### Étape 2 — Rejouer TOUS les bancs existants ✅ FAIT le 27/07 (tous verts, mutations rouges)

```bash
cd App/manga-studio/scripts
python check_version.py                 # source ET écran
python test_clavier_mobile.py           # puis --muter : DOIT virer au rouge
python test_ergonomie_case.py           # puis --muter
python test_galerie_live.py
python test_temoin_activite.py
python test_regenerer_et_log.py
python ../../../.claude/scripts/responsive-audit.py "http://127.0.0.1:8190/manga#k=<secret>"
```

> **Critère** : tout vert, **et** chaque banc muté vire au rouge. Un banc qui ne sait plus échouer ne
> prouve plus rien — c'est la règle payée sur ce projet.

### Étape 3 — Écrire les bancs manquants ✅ FAIT le 27/07 (5 sur 5, tous falsifiés)

Par ordre d'importance, en s'arrêtant dès qu'un défaut apparaît :

1. **`test_prompt_chaine.py`** — la chaîne complète du prompt, celle qui a produit le plus de bugs :
   français → traduction (manuelle **et** automatique) → casting → comptage → `promptFinal`.
   Vérifier que **le prompt enregistré dans la recette** est bien celui attendu — c'est le seul
   endroit qui a révélé le bug d'ordre du 27/07.
   Cas à couvrir : phrase FR simple · phrase FR à 2 sujets (« le maître frappe la fille ») ·
   tags anglais déjà propres (ne doivent **pas** être retraduits) · case sans personnage ·
   case avec casting de 2 personnages.
2. **`test_personnages.py`** — créer, valider, modifier, supprimer une fiche ; cocher un casting ;
   vérifier que les tags des **deux** personnages arrivent dans le prompt ; décocher et vérifier
   qu'ils disparaissent.
3. **`test_sequence_live.py`** — la case de départ n'est **pas** écrasée, les `idx` restent uniques
   et ordonnés, le badge 🎬 s'affiche, ▶ joue au moins 2 images, et une famille « libre » produit
   le bon cadrage.
4. **`test_suites.py`** — 3 propositions distinctes, appuyées sur les 4-5 cases précédentes,
   reprise en un clic.
5. **`test_demarrage.py`** — « Démarrer une planche » crée bien projet + planche + N cases **liées**
   (le piège `projectId` en camelCase, qui créait des planches orphelines **sans aucune erreur**).

### Étape 4 — Chasse aux effets de bord (composition, pas unités)

Ce qui n'a **jamais** été testé ensemble :

- [x] ✅ Séquence **dans une planche qui a déjà un fond maître** — mesuré 27/07, **rien ne casse**.
      Le squelette openpose (0,9) remplace proprement le depth (0,55), et aucun des deux ne se
      superpose à l'autre. 🟠 **Un constat à connaître (v1.24.0)** : les vignettes sont créées en
      `kind: 'dialogue'` (codé en dur), donc une séquence lancée depuis une case **ambiance**
      **perd le décor du fond maître** dans son prompt. C'est cohérent — openpose et depth
      s'excluent de toute façon — mais **ce n'est dit nulle part à l'écran**.
- [x] ~~Séquence **sur une case d'un casting à 2 personnages**~~ → **mesuré le 27/07, défaut
      confirmé et plus grave que prévu** (cf. §3). Le prompt est juste ; ce sont les images qui
      échouent : aucune pose appliquée, 3 puis 4 personnages pour `2people`. Contre-épreuve :
      sans casting, la même séquence produit une vraie progression de mouvement.
      **Attend un arbitrage de Quang**, ce n'est pas un correctif mécanique.
- [x] ✅ Traduction **+** casting **+** comptage tous actifs — mesuré 27/07, **la chaîne tient** :
      le français est traduit avant d'atteindre le moteur, le comptage relevé *avant* traduction
      survit, les deux personnages du casting arrivent, `solo` ne passe pas, `2people` est injecté.
- [ ] ⏳ **SEULE COMBINAISON NON MESURÉE** : ingestion d'une page réelle **puis** séquence sur une
      case ingérée (formats de cases variables). Demande YOLO + le venv `kohya` — à faire.
- [x] ✅ Export d'une planche aux formats **hétérogènes** — mesuré 27/07 : la planche s'assemble
      (3096×4480 pour 4 cases de tailles mêlées), sans erreur.
- [x] ✅ Deux appareils sur le **même** projet — mesuré 27/07 : **le dernier écrivain gagne**,
      sans erreur ni doublon. 🟠 **Constat (v1.24.0)** : aucune fusion, aucun avertissement — le
      travail du premier est écrasé **en silence**. Acceptable pour un usage solo, à savoir avant
      d'éditer la même planche depuis le PC et le téléphone en parallèle.

### Étape 5 — Nettoyage

- [x] ✅ **Fait le 27/07.** Projets et fiches de test supprimés ; il ne reste que `test A`,
      `Test A`, `Salle de classe` (et la fiche `Kimiko`). Les nouveaux bancs **se nettoient
      eux-mêmes** en fin de run — seuls les runs qui plantent laissent des traces.
      ⚠ Piège payé : une première version de `test_personnages.py` supprimait `S.proj` **après
      un rechargement**, où `S.proj` est le dernier projet *ouvert* — elle a détruit un projet
      qui n'était pas le sien. Un banc vise ses objets **par leur nom**, jamais par l'état de l'app.
- [x] Aucune sortie n'a fui **à la racine** de `ComfyUI/output/` (règle d'isolation Generate
      Studio) : les seuls fichiers du jour y sont des `friday_*`, qui ne viennent pas d'ici.
- [ ] 🟠 **(constaté 27/07)** En revanche `ComfyUI/output/manga/` accumule : **42 dossiers de
      travail et 186 fichiers** pour la seule journée. `harvest` déplace l'image finale vers
      `App/manga-studio/output/`, mais ce qui reste (squelettes openpose uploadés, intermédiaires)
      n'est jamais purgé. Ce n'est pas une fuite — c'est un répertoire qui grossit sans fin.
      **Ne pas supprimer à l'aveugle** : vérifier d'abord ce que sont ces 186 fichiers.
- [ ] 🟡 Un dossier `undefined/` y est apparu : un script de test avait mis la **réponse
      d'écriture** `{ok, id}` dans `S.proj`, donc `S.proj.slug` valait `undefined` (même piège que
      `S.page`, cf. §3). L'app, elle, recharge ses projets après création — elle n'est pas
      concernée. Mais le préfixe de sortie mériterait un garde-fou.
- [ ] `git status` propre, et **ne jamais** relancer `git add -A` depuis un sous-dossier
      (1 438 fichiers commités par erreur le 27/07, dont un profil Edge entier).

---

## 3. Défauts connus, non corrigés

| Défaut | Gravité | Note |
|---|---|---|
| ~~**Fiches de personnages sans image de référence**~~ → ✅ **livré v1.25.0** | 🟢 | La table a `refs[]`, l'UI ne permet pas d'en ajouter. Un personnage tient donc à ~50 % (texte seul) au lieu du verrou IPAdapter mesuré et validé. ~~**Chantier n°1.**~~ → **FAIT le 27/07 (v1.25.0)** : bouton « ＋ image de référence » sur chaque fiche (il ouvre la galerie ou l'appareil photo sur téléphone), vignette + retrait, et branchement IPAdapter dans le graphe aux réglages **mesurés** (PLUS 0,4 / end_at 0,5). La référence est **convertie en N&B côté client avant l'upload** — IPAdapter transfère la palette et le négatif textuel ne pèse rien contre une image. Vérifié en génération réelle : référence rouge vif → case rendue à **1,5 de saturation**, identité tenue. Banc `test_references.py` (13 vérifications), mutation rouge à 180 de saturation. ~~⚠ **Une seule référence est utilisée** (le premier personnage du casting qui en a une) : empiler deux identités n'a pas été mesuré.~~ → ✅ **périmé le 28/07 (v1.52.0)** : l'app en applique **deux**, chacune bornée à une moitié par `attn_mask`, poids 0,6 — mesuré **6/6** contre **1/6** à une seule référence, qui *contaminait* le second personnage. Détail : `ROADMAP.md` § IPAdapter. |
| ~~**Pas de zone ciblée (masque manuel)**~~ → ✅ **livré v1.26.1** | 🟢 | `inpaint_zone.py` est mesuré et fonctionne ; rien dans l'app. Une case bonne à 90 % ne peut aujourd'hui qu'être **entièrement** régénérée. ~~**Chantier n°2.**~~ → **FAIT le 27/07 (v1.26.1)** : bouton **⬚ Zone** sur toute case générée, rectangle tracé **au doigt** (précision mesurée 0,001 sur le Samsung), cadre visible même hors mode tracé, puis **↻ la zone**. ⚠ **Le piège, mesuré** : l'inpaint réencode l'image ENTIÈRE par le VAE — une case de 1500×1200 revenait en **1496×1200**, donc elle rétrécissait à chaque reprise et tout le dessin était retouché alors qu'on promettait l'inverse. Corrigé **dans le graphe** (`ImageScale` + `ImageCompositeMasked`) : mesure finale **taille préservée, 0 pixel modifié hors de la zone**, 234 898 dedans. La promesse est vraie par construction, pas par confiance. |
| **Traduction auto intermittente** | 🟠 (constaté v1.23.0) | Elle échoue parfois (API), et c'est **volontairement non bloquant** : on génère alors le texte tel quel, en le notant dans le journal. Mais l'utilisateur ne le voit pas. À rendre visible dans l'aperçu. Depuis la v1.23.0 la traduction n'est plus optionnelle, donc cet angle mort porte désormais sur **tous** les chemins. |
| **Un objet partiel dans `S.page` détache la planche, en silence** | 🟠 (constaté v1.23.0) | L'upsert serveur réécrit **tous** les champs d'une planche. Un `api('/manga/pages', obj)` avec un objet incomplet (par ex. la réponse `{ok, id}` d'une écriture) remet `project_id` à vide : la planche devient **orpheline**, sans la moindre erreur. Aucun chemin de l'app ne fait ça aujourd'hui (`S.page` vient toujours de `loadPages`), mais rien ne l'empêche. Trouvé en écrivant `test_personnages.py`, qui est tombé dedans. |
| **Une régénération accumule les fichiers** | 🟠 | Chaque génération écrit un fichier de plus ; l'ancien n'est pas supprimé. Choix assumé (on ne détruit pas sans demander) mais **à trancher avec Quang** : supprimer, ou garder comme historique avec retour arrière. |
| ~~**Séquence sur un casting de 2 : la pose est PERDUE**~~ → ✅ **traité v1.24.0** | 🟢 | ~~Non testé, défaut probable.~~ → **Mesuré le 27/07, et c'est pire que soupçonné.** Le prompt est pourtant juste (`2people`, les deux identités, pas de `solo`). Ce sont les **images** qui échouent : sur les 2 vignettes, **aucune pose n'est appliquée** — personnages debout, bras le long du corps, quasi identiques — et le compte est faux (**3 puis 4 personnages** pour `2people`). Contre-épreuve faite le même jour : **sans casting, la pose fonctionne parfaitement** (course dans un couloir, membres qui changent d'une vignette à l'autre). Le squelette openpose est mono-corps et imposé à un poids de **0,9** ; face à deux identités, le modèle abandonne la pose et multiplie les corps. ⚠ **Décision de conception attendue** — trois routes : (a) refuser la famille « pose garantie » quand le casting a ≥ 2 personnages et le dire ; (b) dessiner N squelettes côte à côte ; (c) baisser le poids et accepter que la pose ne soit qu'indicative. **Aucune n'est un simple correctif.** → **Route (a) retenue et livrée le 27/07 (v1.24.0)** : dès que le casting compte ≥ 2 personnages, la famille « pose garantie » 🎬 n'est plus proposée et l'écran dit pourquoi ; les gestes libres 🎭 restent disponibles. Un second garde-fou dans `sequence()` refuse l'appel même si un autre chemin y mène — un bouton retiré de l'écran n'est pas une garantie. Le refus se fonde sur le **casting seul** (explicite), pas sur `nbPersonnages` (heuristique de texte, trop faillible pour retirer un bouton). Les routes (b) N squelettes et (c) poids abaissé restent ouvertes si tu veux vraiment animer deux corps. |
| **Le projet `test-a` porte encore le personnage de test** | 🟡 | Quang doit cliquer *Recette → Retirer le personnage de ce projet*, ou le faire soi-même à la reprise. |
| **`sembleFrancais` : liste de mots** | 🟡 | Robuste mais approximative (« action » est français **et** anglais). Faux positif possible → traduction inutile d'un texte déjà bon. Sans gravité : la traduction d'un texte anglais le laisse anglais. |

---

## 4. Après la revalidation — la suite, dans l'ordre

1. **Images de référence sur les fiches de personnages** (IPAdapter validé le 27/07 : preset PLUS,
   poids 0,4, `end_at` 0,5, **référence convertie en N&B**). C'est ce qui fait passer un personnage
   de « ~50 % » à une identité tenue, sans entraînement.
2. **Zone ciblée** : tracer un masque sur une case et ne régénérer que lui.
2-bis. ~~**Deux références IPAdapter**~~ → ✅ **fait le 28/07 (v1.52.0)**, mesuré 6/6.
3. **Bibliothèque de références** (phase 8) : nourrir l'app de pages que Quang aime — style,
   apparence, **et gabarit de planche** (le découpage YOLO existe déjà et n'a jamais servi à ça).
4. **Mode chapitre automatique** (phase 7) : les 4 briques existent (storyboard, casting,
   amélioration de prompt, 3 suites). Reste à cadrer **le grain de validation** — mon avis : valider
   le découpage AVANT de dépenser du GPU.
5. **Volet adulte** : fétichisme et explicite ne sont toujours pas testés au-delà d'un essai.

---

## 5. Ce qu'il ne faut pas refaire (rappels des pièges payés aujourd'hui)

- Un banc qui **ne regarde jamais l'écran** valide des chiffres, pas un résultat.
- Un banc qui mesure une case **sans image** rend un vert sans valeur.
- Un **seuil inventé** (« 85 % de l'écran ») déclare rouge à 1 px près : mesurer ce que
  l'utilisateur fait, pas un pourcentage.
- Une **valeur dupliquée dont une copie écrase les autres** (la version) est un mensonge silencieux.
- `git add -A` depuis un sous-dossier ratisse **la racine du dépôt**.
- Corriger un **défaut par défaut** ne répare pas les **données déjà écrites**.
- Un LLM ne garantit pas un tag : ce qui doit être maîtrisé se **dérive** du texte, pas se demande.
