# Manga Studio — feuille de route

> **Document vivant.** Mis à jour à chaque étape franchie ou infirmée. Dernière révision : **2026-07-27**.
> Autosuffisant : tout ce qu'il faut pour reprendre le chantier est ici, sans mémoire externe.
>
> **Nature des énoncés** (arbitrage `.claude/rules/document-vs-depot.md`) : les sections *Objectif*,
> *Architecture* et *Définition de fini* sont des **intentions** — elles font loi. Les sections *État mesuré*
> et *Journal* sont des **constats datés** — ils se re-vérifient contre le code et le disque avant d'être crus.

---

## 1. Objectif

Créer des **planches de manga complètes** (cases + bulles + lettrage), **tout genre y compris adulte**,
en usage personnel, en s'appuyant sur le moteur de Generate Studio (ComfyUI local, non censuré).

Trois besoins exprimés par Quang le 26/07/2026, dans l'ordre où ils sont arrivés :

1. **Générer** du manga de tout thème.
2. **Ingérer** ses propres scans / captures / PDF de mangas qu'il possède → les analyser → **reproduire
   le style ou en faire des variantes**.
3. **Apprendre de ce qu'il valide** : il note ✅/❌, l'app s'appuie sur les données validées au fil du temps,
   avec du texte généré et incrusté.
4. **Produire un CHAPITRE entier depuis un texte** *(rappelé par Quang le 27/07)* : « le but de l'outil,
   c'est de pouvoir créer une image ou même plusieurs images d'un chapitre, depuis un prompt de texte ou
   autre ». Autrement dit : on donne un synopsis, un script ou un découpage, et l'app en sort la suite de
   cases — pas une image à la fois, à la main.
   **Quang précise lui-même : « ce qui sera possible plus tard ».** C'est donc la cible, pas le prochain
   pas. ⏱ **Déclencheur de reprise : après le LoRA v2**, parce que générer un chapitre n'a de sens que
   si le personnage et le décor tiennent sur la durée — c'est exactement ce que les phases 1, 2 et 6
   servent à garantir. Générer 40 cases avec un personnage instable produirait 40 images à jeter.

### 🎯 Ce qui compte, et ce qui ne compte pas *(directive Quang, 27/07)*

> « Les petits détails, comme le grain de beauté, on s'en fiche totalement. Ce qui compte, c'est la
> **qualité de l'ensemble** et les **détails les plus importants**. »

C'est une règle de priorité, pas une remarque : elle décide où passe l'effort.

- **Compte** : la lisibilité d'une planche, la continuité d'une scène, le rendu N&B, un personnage
  reconnaissable, un lettrage propre, un enchaînement de cases qui se lit.
- **Ne compte pas** : un grain de beauté, une mèche, un pli. Un micro-détail qui coûte des heures de GPU
  et qu'on ne voit pas à la lecture n'est pas un objectif — c'est une distraction.

⇒ **Le grain de beauté est RETIRÉ du design du personnage.** La réserve n°1 de la phase 1 est close par
décision, pas par correctif. Recalcul du comparatif de la phase 1 sans cette ligne : **15/15 = 100 %**
(c'était 16/18 = 89 %, et l'unique échec était le grain). **Le critère de sortie de la phase 1 est donc
atteint franchement, avec le LoRA v1.**

### Hors périmètre (assumé)

- Publication / diffusion : le projet est personnel. Le **style** graphique n'est pas protégé, les
  **personnages et planches** d'autrui le sont — la question ne se pose qu'à la publication.
- Contenus interdits sans exception : mineurs (y compris « loli/shota », réprimé en France même en dessin),
  visages de personnes réelles en contexte sexuel.

---

## 2. Architecture retenue

**Application séparée (single-file HTML), cliente du proxy Generate Studio.** Pas un onglet de plus dans
`generate_studio.html`.

Le « moteur GS » n'est pas le HTML : c'est **`C:\Users\quang\Documents\ComfyUI\_studio_llm_proxy.py`**
(port 8190, ~60 routes) + **ComfyUI** (port 8188). Le proxy renvoie `Access-Control-Allow-Origin: *`
(ligne 1570) ⇒ une app tierce consomme tout le moteur **sans modifier une ligne de proxy**.

| Raison | Détail |
|---|---|
| Modèle de données différent | GS est *one-shot* (prompt → image → galerie). Le manga est hiérarchique et long : projet → chapitre → planche → case. |
| UI différente | Canvas de planche, gouttières, bulles, ordre de lecture, fiches personnages. Ce n'est pas un 4ᵉ onglet. |
| Risque de régression | `generate_studio.html` = 5 728 lignes / 536 Ko. L'historique v5.53 / v5.56 / v5.59 montre que le nœud auto-modèle ⇄ auto-pilote LoRA casse à chaque intervention. Une app à part qui plante ne casse pas le GS quotidien. |

**Hérité gratuitement du proxy** : `/enhance` (amélioration de prompt), `/critique` (vision Pixtral),
`/db/*` (galerie, prompts, préférences), `/lora_*` (11 routes), `/pod_*` + `/ltx_*` (pods RunPod),
`/spend_log` (coûts), tunnel Cloudflare, accès mobile.

**Pont prévu, pas une fusion** : un bouton « → envoyer au Manga » depuis la galerie GS (~10 lignes).

### À trancher avec Quang (non bloquant pour les phases 1-2)

- Galerie commune (`/db/gallery`) ou table dédiée ? *Avis : table dédiée — une planche n'est pas une image de galerie.*
- Lettrage dans l'app, ou en externe comme il monte ses vidéos (CapCut) ? Ça change beaucoup le périmètre de la phase 5.

---

## 3. État mesuré au 26/07/2026 (constats datés — à re-vérifier)

### Environnement installé ce jour

| Élément | État |
|---|---|
| Checkpoint `waiIllustriousSDXL_v170.safetensors` | ✅ installé (6,46 Go) dans `ComfyUI/models/checkpoints/` — WAI-illustrious v17.0, standard anime/manga |
| LoRA locaux | 168 : `Pony/` 65, `SDXL/` 57, `Illustrious/` 34, `NoobAI/` 1 — **aucun de style manga N&B** |
| ControlNet | `depth-sdxl`, `openpose-sdxl-xinsir` + `comfyui_controlnet_aux` |
| ReActor | ✅ installé (`inswapper_128.onnx`, `codeformer-v0.1.0.pth`) |
| IPAdapter | ⛔ **absent** — à installer (transfert de style/visage sans entraînement) |
| Entraîneur LoRA | ✅ `kohya-ss/sd-scripts` → `D:\Download\02-Apps-Web\kohya-trainer\` (venv isolé, torch 2.11+cu128) |
| GPU | RTX 5070 Ti 16 Go, **sm_120 (Blackwell) ⇒ exige cu128**, un torch standard échoue |

### Essais (scripts dans le scratchpad de session, à rapatrier ici si on continue)

| # | Question | Verdict |
|---|---|---|
| 1 | Le rendu manga N&B est-il atteignable ? | ✅ **Oui, base seule, sans LoRA.** Les tags `monochrome, greyscale, manga, screentone, halftone, lineart, ink` + négatif `color` produisent de vraies trames. Le **même seed sans ces tags** donne une illustration couleur ⇒ les tags font tout. ⚠️ Le **rouge persiste** malgré le négatif (effet « spot color ») — à durcir pour du N&B d'impression pur. |
| 2 | Seed fixe + prompt verrouillé suffisent-ils à tenir un personnage ? | ⛔ **Non, ~50 %.** Stables 3/3 : cheveux, uniforme, écharpe. Instables : couleur des yeux (rouge→ambre→ambre), morphologie du visage (0/3), grain de beauté (1/3). Le seed ne fixe que le bruit initial. |
| 3 | Une *character sheet* peut-elle servir de dataset ? | ⛔ **Non.** Costume et silhouette cohérents sur 6 vues, mais **visages non résolus** (trop peu de pixels en pied) ⇒ ininstruisable. Le style dérive aussi (perte des trames). |
| 4 | Bootstrap ReActor : générer N images variées puis y imposer un visage de référence | ✅ **24/24 générées**, identité visuellement cohérente sur cadrages/expressions/fonds variés. ⚠️ Deux limites : la variété de **cadrage reste faible** (tout finit en buste, les « cowboy shot » n'ont pas pris) et ReActor donne parfois une **teinte de peau décalée**. |

### Ce que disent la recherche et les avis extérieurs (web + vote 3 voix, 26/07)

- **Cohérence de personnage**, par fiabilité réelle décroissante : **LoRA de personnage** (20-30 images) ≫
  character-sheet réinjectée > **IPAdapter FaceID / InstantID** (verrou *facial* seulement) > **ReActor**
  (casse au-delà de 30° de profil, lisse les expressions manga exagérées) > seed fixe (inefficace, mesuré).
- **Découpage de planche** : OpenCV seul insuffisant sur manga japonais (cases sans bordure, fonds noirs
  continus, splash pages). Outils réels : **Magi** (`ragavsachdeva/magi` — cases + persos + bulles + OCR +
  ordre de lecture + locuteur ; ⚠️ **licence recherche académique uniquement**),
  **manga-panel-detector-yolo26n** (HuggingFace, fine-tune Manga109-s), **Kumiko**, **manga-image-translator**.
  Alternative maison : **Pixtral, déjà câblé** (`/critique`), à qui on demande les bounding-box en JSON
  (~85-90 % sur layouts standards) — suffisant pour un pré-découpage validé à la main.
- **Bulles / lettrage** : convergence des 3 voix — **ne jamais laisser le modèle générer le texte**.
  Overlay Canvas / Pillow, polices Wild Words / AnimeAce. AnyText / GlyphControl pas mûrs pour du dialogue.
- **Conversion couleur → N&B = mauvaise piste** (la couleur persiste même à faible denoise). **Générer
  directement en N&B**, ce que l'essai 1 confirme.

### 🚩 Le piège principal, pointé par les 3 voix indépendamment

**Ce n'est pas le visage, c'est la continuité scénographique.** Décor, lumière, position des objets et
accessoires dérivent d'une case à l'autre : aucun modèle n'a de mémoire de scène. On obtient 40 belles
images qui, assemblées, racontent une histoire visuellement absurde.

Parades : **fond « maître » figé** réinjecté (ControlNet Tile + inpaint), storyboard avant génération,
voire pré-production 3D pour les depth/openpose.
**Ratio à assumer dès l'architecture : l'IA fait ~30 % du travail** ; 70 % = remontage, inpainting, trames,
lettrage, relecture séquentielle.

---

## 4. Phases

Chaque phase a un **critère de sortie mesurable**. Rien n'est « fait » sans son chiffre.

### Phase 0 — Socle technique ✅ *(fait le 26/07)*
Checkpoint Illustrious installé, kohya opérationnel, pipeline ComfyUI piloté par script, essais 1-4 mesurés.

### Phase 1 — Verrouiller le personnage ✅ *(89 % le 26/07 ; **100 % le 27/07**, les 2 réserves closes)*
1. Dataset bootstrap ReActor — ✅ 24 images.
2. Entraînement LoRA — ✅ `zqmg1rl_v1.safetensors` (218 Mo, dim 32 / alpha 16, 1 152 steps, 8 epochs, ~34 min).
3. Essai 5 = essai 2 rejoué **avec** le LoRA @ 0.8 — mêmes 3 prompts, même seed 222222, même checkpoint.

> **Critère de sortie** : identité ≥ 90 % sur 3 cadrages distincts, sur les attributs **fins**
> (yeux, grain de beauté, morphologie), pas seulement le costume.

**Résultat mesuré — 18 observations (6 attributs × 3 cases) :**

| Attribut | Sans LoRA | Avec LoRA |
|---|---|---|
| Couleur des yeux (ambre demandé) | rouge / ambre / ambre → **1/3** | **3/3** |
| Écharpe rouge | rouge / rouge / **grise** → 2/3 | **3/3** |
| Frange droite (`blunt bangs`) | 2/3 | **3/3** |
| Morphologie du visage | 3 visages différents → **0/3** | **3/3** |
| Grain de beauté sous l'œil | 1/3 | **1/3** ⚠️ *(inchangé)* |
| Uniforme sailor | 3/3 | 3/3 |
| **Total** | **9/18 = 50 %** | **16/18 = 89 %** |

**⚠️ Deux réserves confirmées, toutes deux prévues et réparables — à traiter en LoRA v2 AVANT la phase 4 :**
1. **Le micro-détail ne s'apprend pas** (grain de beauté, 1/3 inchangé). Conforme à ce qu'annonçait le vote :
   « les détails microscopiques dérivent obligatoirement ». Parade : l'inpainting ciblé, ou retirer ce détail
   du design du personnage.
2. **Biais de cadrage** : le dataset étant presque tout en buste (les `cowboy shot` n'ont pas pris), le LoRA
   **tire vers le plan rapproché** — visible sur la case 2, où le `full body` demandé sort plus serré qu'avant.
   Parade : refaire un dataset avec de vrais plans larges (probablement via ControlNet openpose pour forcer le cadrage).

**Effet secondaire à connaître** : le LoRA **n'est pas neutre en style** — il a absorbé le rendu très contrasté
de son dataset (aplats plus durs, moins de nuances de gris). Attendu, mais à surveiller si on veut varier le style.

### Phase 2 — Continuité de scène ✅ *(atteinte le 26/07)*
Fond « maître » généré une fois (décor seul) → carte de profondeur (`DepthAnythingV2`) → imposée à chaque
case via `ControlNetApplyAdvanced` + `depth-sdxl` **à strength 0,55**, avec le LoRA du personnage.

> **Critère de sortie** : sur 6 cases d'une même pièce, décor reconnaissable et lumière de même direction.

**Résultat mesuré (salle de classe, 6 cases + un témoin) :**

| Réglage | Décor cohérent | Personnage présent et lisible |
|---|---|---|
| **Témoin — sans ControlNet**, décor répété verbatim dans le prompt | **0/4** — quatre salles différentes, fenêtres qui changent de côté | 4/4 |
| **ControlNet 0,55** ⭐ | **6/6** — mêmes rangées, même perspective, fenêtres à gauche, lumière de gauche | **6/6** |
| ControlNet 0,85 | 4/4 (quasi-copie du fond) | **1/4** — case 2 : personnage **absent**, case 3 : minuscule, case 4 : raté |

**Ce que ça établit :**
1. **Répéter la description du décor dans le prompt ne sert à rien** (0/4). C'était la parade « minimale »
   recommandée par le vote — mesurée ici, elle est inopérante. Le témoin était indispensable pour le savoir.
2. **0,55 est le réglage utile.** À 0,85 la géométrie du décor *vide* ne laisse plus de place au personnage :
   le modèle rend la salle telle quelle et **oublie la personne**.

**⚠️ Limite structurelle à connaître — elle dicte la méthode de travail :**
le fond maître **impose aussi le cadrage** (la profondeur décrit une pièce vue en plan large). On ne peut donc
**pas faire un gros plan** avec cette méthode, et le personnage y reste petit — donc **son visage n'est pas résolu**,
exactement comme à l'essai 3. Les deux contraintes (décor figé + identité fine) ne tiennent pas dans la même case.

⇒ **Règle de production à appliquer dans l'app** : deux types de cases, traités différemment.
- **Cases d'ambiance / plans larges** → fond maître + ControlNet depth 0,55 (le décor porte l'information).
- **Cases de dialogue / gros plans** → LoRA seul, sans ControlNet (le décor est hors-champ ou flou, il n'a
  pas besoin d'être exact — c'est d'ailleurs la grammaire réelle du manga).

### Phase 3 — Ingestion et analyse des scans 🔄 *(pipeline écrit et mesuré le 26/07 ; validation sur scans réels EN ATTENTE)*
`manga_ingest.py` : fichier (image **ou PDF** via PyMuPDF) → Pixtral → (a) `panels` = boîtes en fractions de page
+ ordre de lecture + découpe automatique, (b) `style` = fiche structurée + `reusable_prompt` prêt à l'emploi.
Passe par le même chemin que le proxy (`GATEWAY/api/mistral`, `pixtral-12b-latest`) : la brique existait, on lui
a donné un autre travail.

> **Critère de sortie** : sur 3 planches **réelles de Quang**, ≥ 80 % des cases correctement détectées,
> et une variante générée qu'il juge « dans l'esprit ».

**⚠️ Leçon de méthode — le premier test était un faux positif.**
Testé d'abord sur une planche générée par SDXL : **8/8 cases**, verdict « ça marche ». Vérification par
superposition des boîtes : la planche était **elle-même une grille 2×4 parfaite** — Pixtral pouvait la deviner
sans rien regarder. *Un test qu'on ne peut pas rater ne mesure rien.*

**Test discriminant construit ensuite** (`make_hard_page.py`) : planche irrégulière à **vérité terrain connue** —
bandeau large, deux cases inégales, une **penchée**, une **sans bordure**, une qui **saigne** au bord.
Mesure objective par IoU, pas à l'œil :

| Case | Style | IoU |
|---|---|---|
| 1 | bandeau large | 0,43 ❌ |
| 2 | bordure | 0,63 ✅ |
| 3 | penchée | 0,66 ✅ |
| 4 | **sans bordure** | 0,69 ✅ |
| 5 | bordure | 0,79 ✅ |
| 6 | **saigne au bord** | 0,76 ✅ |

**5/6 = 83 % à IoU ≥ 0,5 · IoU moyen 0,66.** Le seuil de 80 % est atteint **sur la lettre**, mais il y a une
réserve qui compte plus que le chiffre :

> **Pixtral ne détecte pas les bords, il quantifie sur une grille.** Il n'a proposé que **2 largeurs (0,5 et 1,0)
> et 1 hauteur (0,25)** là où la planche en contient **5 largeurs et 4 hauteurs distinctes**. Il trouve
> le bon **nombre** de cases, la bonne **zone**, le bon **ordre** — pas les bonnes **limites**.

**🔴 PUIS LES 5 PAGES RÉELLES DE QUANG ONT INVALIDÉ CE RÉSULTAT (26/07, soir).**
Sur sa page 1 (planche hentai N&B, cases jointives, fond noir, grande illustration + inserts), le découpage
Pixtral est **franchement mauvais** : boîtes qui coupent en plein milieu des dessins, et le raffinement
OpenCV ne rattrape presque rien (la plupart des bords ressortent « inchangé »).
**Cause** : mes deux planches de test avaient un défaut commun invisible — des **gouttières blanches nettes
et des bordures noires franches**. Une vraie planche n'en a pas. L'algorithme de raffinement cherchait des
signaux qui n'existent pas. ⇒ *Deux fois de suite, un test maison a surestimé la performance. Seul le
matériel réel de l'utilisateur tranche.*

**✅ CORRECTION : bascule sur un modèle DÉDIÉ — `manga-panel-detector-yolo26n`**
(HuggingFace `leoxs22`, YOLO26-nano fine-tuné sur **Manga109-s**, 15 Mo, **licence Apache 2.0** — donc
utilisable, contrairement à Magi). Détecte 2 classes : `frame` (cases) **et `text` (bulles)** — la classe
`text` servira directement au mode traduction. Tourne dans le venv `kohya-trainer` (ultralytics 8.4).

**Comparatif chiffré, même planche à vérité terrain :**

| Méthode | IoU moyen | ≥ 0,5 | Détail |
|---|---|---|---|
| Pixtral seul | 0,660 | 5/6 | 0.43 0.63 0.66 0.69 0.79 0.76 |
| Pixtral + raffinement OpenCV | 0,702 | 6/6 | 0.50 0.68 0.71 0.68 0.85 0.80 |
| **YOLO Manga109** ⭐ | **0,895** | 5/6 | **0.99 0.99 0.99 0.95 0.98** · 0.47 |

Cinq cases sur six à **IoU 0,95-0,99** — c'est-à-dire au pixel près, pas « à peu près ». La 6ᵉ (celle qui
saigne au bord de page) reste à 0,47 : c'est le cas limite à surveiller.
Sur les pages réelles : q1 8 cases + 9 bulles · q2 5+6 · q3 **1 case** (splash correctement vu) · q4 3 · q5 3.

⇒ **Répartition finale des rôles** : **YOLO** détecte les cases et les bulles ; **Pixtral** garde ce qu'il
fait bien — classification de la mise en page (`irregular`/`splash`/`grid`, correcte sur les 5 pages),
ordre de lecture, analyse de style, et bientôt l'OCR-traduction. Le raffinement OpenCV devient inutile.

**✅ RISQUE ARCHITECTURAL LEVÉ** : **Pixtral n'a pas refusé la page explicite** de Quang. La chaîne de vision
tient sur l'usage réel — pas besoin de basculer sur une vision locale.

**✅ Le volet style fonctionne bien** : la fiche sort structurée (trait, trames, contraste, ombrage, cadrage,
ambiance, époque) + une liste de tags Danbooru + un `reusable_prompt` directement injectable. Sur une planche
de test il a correctement identifié « seinen/josei, encrage fin à moyen, trames denses en pointillé et
hachures croisées, fort contraste ».

~~**⏳ CE QUI MANQUE ET QUI NE DÉPEND PAS DE MOI** : les **scans réels de Quang**. Le critère de sortie parle de
*ses* planches — testé jusqu'ici uniquement sur des pages générées ou fabriquées. À déposer dans
`D:\Download\02-Apps-Web\01-Term_mob_files_send\`.~~
→ **✅ PÉRIMÉ dès le 26/07 au soir** : ses 5 pages sont arrivées le jour même et ont servi — ce sont elles qui ont
invalidé Pixtral et provoqué la bascule sur YOLO (voir ci-dessus). Ce constat n'aurait jamais dû rester en « ⏳ » :
il était déjà contredit **par la suite du même paragraphe**. C'est exactement le défaut que
`.claude/rules/document-vs-depot.md` décrit — une livraison qui rend faux un constat écrit, sans que l'auteur
revisite *celui-là*. (Relevé et corrigé à l'ouverture de la phase 4.)

### Phase 3-bis — Les MODES sur une page ingérée ⏳ *(demandes Quang du 26/07, après le premier jet)*

Une fois une page ingérée, elle doit pouvoir ressortir de plusieurs façons. Ces modes sont **combinables** —
c'est un axe par question, pas une liste de boutons.

| Mode | État / méthode | Coût |
|---|---|---|
| **Reproduire le style** | ✅ acquis — le `reusable_prompt` de la fiche de style existe | fait |
| **Traduire le texte en français** | ✅ **OCR + traduction VALIDÉS le 26/07** sur la page japonaise de Quang (`manga_translate.py`) : **6/6 bulles** lues (japonais vertical) et traduites. **Architecture à 2 passes, et la 2ᵉ apporte beaucoup** : (1) chaque bulle est traduite **isolée** — l'attribution vient alors de la détection YOLO, pas du modèle de langue, donc il ne *peut pas* se tromper de bulle ; (2) une passe sur la **page entière** ajuste le registre → **6/6 traductions améliorées** (« Bien sûr ! » → « C'est sûr… », « Qui que tu sois ! » → « Qui que tu sois… » : le ton exclamatif était faux sur une planche mélancolique). ⚠️ Défaut mineur : le champ `tone` sort parfois deux valeurs (`chuchote\|pense`) au lieu d'une. ⏳ **RESTE : le relettrage** — effacer le texte source et reposer le français dans la bulle. C'est le vrai travail, la traduction était la partie facile | moyen |
| **Décensure** | 🔄 **testé le 26/07 sur page réelle — détection OK, reconstruction RATÉE.** (1) `App/demosaic-pipeline/` **est cassé** : `total_mem`→`total_memory` (corrigé, `.bak` fait), `basicsr`/`torchvision.transforms.functional_tensor` supprimé (non corrigé, lib non maintenue), et chemin image inopérant (« Aucune frame trouvée » — il est bâti pour la vidéo). (2) **Détection : ✅ réussie** en réutilisant SEUL son segmenteur `mosaic_position.pth` (BiSeNet) — masque 5,24 % de la page, et vérification objective : **période de bloc 7 px dans la zone contre 3 px ailleurs**. ⚠️ Il ne rend qu'**une** zone (`find_mostlikely_ROI`), la page en avait 3. (3) **Inpainting Illustrious : ✅ la mosaïque disparaît** (période 6 px → 3 px) **mais le contenu est faux** — à denoise 1,0 le modèle efface sans reconstruire ; à 0,85 il invente une **anatomie féminine sur un sujet masculin**. **2 causes identifiées, toutes deux réparables** : le masque BiSeNet est **trop large** (il englobe tout le torse, donc le modèle redessine bien au-delà de la censure) et **le prompt ne décrit pas le sujet**, donc Illustrious improvise et retombe sur son attracteur par défaut. **(4) ✅ CORRIGÉ, la chaîne fonctionne** : masque **manuel** (3,50 % de la page, contre 5,24 % BiSeNet) + prompt **décrivant le sujet** → anatomie correcte et cohérente sur 2 seeds, dans le style de la page. Les deux causes diagnostiquées étaient les bonnes.
**⛔ Détection automatique du masque : ABANDONNÉE après 2 échecs de la même nature** (règle « 2 fois la même erreur → stop »). Mon critère « zone plate » ne discrimine pas : sur une illustration numérique **la peau en aplat est plate aussi** → 26 % de la page au 1er essai, masque *plus grand* que le BiSeNet au 2ᵉ. Le BiSeNet localise mais son enveloppe est trop large. ⇒ **Dans l'app, la zone se trace à la main** (c'est ce que font les outils de décensure sérieux), éventuellement pré-remplie par le BiSeNet et ajustable.
**Défauts résiduels à corriger** : teinte de peau légèrement décalée sur les bords ; `grow_mask_by: 12` **mord sur les onomatopées** voisines et les bave. ⚠️ Rappel : la zone n'existe pas dans le fichier, on **invente** une reconstruction | moyen |
| ~~Décensure (état initial)~~ | ~~2 pistes à départager sur matériel réel~~ — (a) **`App/demosaic-pipeline/`, déjà installé chez Quang** (DeepMosaics + Real-ESRGAN, 1,9 Go de modèles, calibré 5070 Ti) mais ses poids `clean_youknow_*` sont entraînés sur de la **vidéo photoréaliste** → risque de bouillie grise sur du trait encré ; (b) **inpainting WAI-Illustrious** sur la zone masquée, qui redessine dans le style de la planche. ⚠️ Aucune des deux ne « retrouve » l'original : la zone n'existe pas dans le fichier, les deux **inventent** | moyen |
| **Version alternative / continuité** | ⏳ le plus ambitieux — demande de *comprendre* la scène, pas de la voir. Quang : « on creusera plus tard » | élevé |

**Axe colorimétrie — indépendant de la source** (demande du 26/07) :

| Source → Sortie | État |
|---|---|
| N&B → N&B · Couleur → couleur | ✅ rien à faire |
| **N&B → couleur** | 🎯 **ControlNet lineart/canny** : on fige le trait exact, le modèle ne pose que la couleur. Le dessin reste celui de la source. Préprocesseurs déjà là (`AnimeLineArtPreprocessor`) ; **modèle `canny-sdxl-xinsir` téléchargé le 26/07** |
| **Couleur → N&B** | ⚠️ **ne pas désaturer** — ça donne du gris, pas des trames. Un vrai N&B manga = points de demi-teinte + hachures. Chemin retenu : extraire le trait puis **re-générer** en N&B tramé (cohérent avec l'essai 1 et le test tiers lilting.ch) |

### Phase 4 — L'app ✅ *(atteinte le 26/07 — `manga_studio.html` v1.0.1)*
Single-file HTML, version affichée dans l'UI, cliente du proxy 8190. Modèle : projet → chapitre → planche →
case. Chaque case porte sa **recette complète** (modèle, LoRA + poids, seed, prompt, ControlNet, source).
> **Critère de sortie** : une planche de 6 cases produite de bout en bout dans l'app, testée PC **et**
> mobile (Samsung réel), 0 erreur JS.

**Résultat mesuré — banc `scripts/test_app_live.py` (Playwright, pilote l'app comme un utilisateur) :**

| Mesure | Valeur |
|---|---|
| Cases produites de bout en bout | **6/6** (3 ambiance + 3 dialogue), 99 s au total |
| Fond maître + carte de profondeur | 2/2, 22 s |
| Export de la planche assemblée | ✅ PNG 1760×3768 |
| Erreurs JS (`pageerror` + console + journal de l'app) | **0** |
| Mobile — Samsung réel (CDP par `adb reverse`) | **0 erreur JS**, 9/9 vignettes chargées, aucun débordement |
| Responsive 320 / 360 / 384 px × 4 onglets | **12/12 sans scroll horizontal** |

**🔒 Isolation vis-à-vis de Generate Studio — exigence posée par Quang le 26/07, mesurée par différence :**
racine `ComfyUI/output` **851 avant, 851 après** alors qu'on venait de générer 7 images, et **0 résidu** dans
`ComfyUI/output/manga/`. Deux verrous en série, pas un seul :
1. ComfyUI écrit sous `output/manga/<slug>/<planche>/` — sous-dossier profond, hors du scan 1-niveau de
   `list_outputs()`, donc **invisible de la galerie GS** ;
2. `POST /manga/harvest` **déplace** ensuite le fichier dans `manga-studio/output/<slug>/` — il quitte ComfyUI.

**⚠️ Le défaut que le banc a attrapé et que l'œil n'aurait pas vu** : au 1er passage, tout paraissait vert
(6/6 générées, export correct, 0 erreur) — et pourtant les 6 cases avaient atterri dans le dossier d'**un autre
projet**. Cause : *créer* un projet ne le *sélectionnait* pas, `loadProjects()` restaurant celui de la session
précédente. Aucune erreur n'était levée : le rangement se faisait, simplement au mauvais endroit.
Deux corrections, pas une : le projet créé devient courant (v1.0.1), **et** la destination se déduit désormais du
projet **propriétaire de la planche**, plus du projet « sélectionné ». *Un test qui compte les fichiers au bon
endroit valait tous les verdicts « ça marche ».*

**Ce que l'app encode en dur, parce que c'est mesuré et pas négociable :**
- les **deux types de case** (phase 2) — `ambiance` = fond maître + ControlNet depth 0,55 ; `dialogue` = LoRA seul ;
- une case `ambiance` **refuse de se générer** sans fond maître, au lieu de sortir un décor à la dérive ;
- les tags N&B de l'essai 1 dans la recette par défaut ;
- les générations sont **sérielles** (une seule carte, 16 Go de VRAM) ;
- un **journal client** (`window.MangaLog.dump()` / `.errors()`) dès la conception, lisible par CDP.

**Limites visibles sur la planche de validation, toutes deux déjà documentées** : le **rouge « spot color »
persiste** malgré le négatif (réserve de l'essai 1 — ce n'est pas du N&B d'impression), et sur les cases
d'ambiance **le visage n'est pas résolu** (limite structurelle de la phase 2 — c'est précisément ce qui justifie
la règle des deux types de cases).

### Phase 5 — Bulles et lettrage ✅ *(atteinte le 26/07 — v1.2.0)*
Calque éditable par case. Le modèle de diffusion n'écrit **jamais** le texte (convergence des 3 voix) :
le texte est posé par-dessus.
> **Critère de sortie** : bulles repositionnables, texte réeditable après coup, export PNG/PDF.

**Décision d'architecture — un seul chemin de rendu.** Le calque est un **SVG**, affiché tel quel à
l'écran *et* rasterisé pour l'export. Écran et export sont identiques **par construction**, au lieu
d'être deux codes de dessin (DOM + canvas) qu'il faudrait garder d'accord — ils divergent toujours.
Toutes les coordonnées sont des **fractions de la case** : la même bulle tombe au même endroit sur une
vignette de 400 px et sur un export pleine résolution.

**Résultat mesuré — banc `scripts/test_lettering_live.py` :**

| Mesure | Valeur |
|---|---|
| Bulle posée, texte renvoyé à la ligne | ✅ 6 lignes automatiques |
| Texte **contenu** dans la forme (mesure `getBBox`) | ✅ marge ≥ 100 unités sur les 4 côtés |
| Repositionnable, et **enregistré** | ✅ 0,500;0,180 → 0,589;0,332 relu depuis la base |
| Texte rééditable après rechargement complet | ✅ |
| **La bulle est-elle dans le fichier exporté ?** (mesure pixels) | ✅ zone 122 → **229** / 255, 88 % d'aplat, 9 % de texte |
| Export PDF | ✅ valide, 758 Ko, écrit à la main (image JPEG en XObject, aucune bibliothèque) |
| Erreurs JS | **0** |
| Mobile Samsung réel | ✅ 0 erreur, aucun débordement, **police embarquée réellement utilisée** (200 px vs 312 px en repli) |

Formes : ovale · rectangle · **pensée** (couronne de bosses + bulles qui s'éloignent) · **cri** (étoile
déterministe — pas de `Math.random`, sinon la forme changerait entre l'écran et l'export) · **récitatif**
(sans bulle). Queue orientable à la poignée. Police **Comic Neue (OFL) embarquée en base64** : l'export
étant rendu côté client, une police absente du téléphone donnerait un fichier différent de celui du PC —
c'est un défaut de correction, pas de goût.

**⚠️ Trois défauts trouvés par la mesure, dont un présent depuis la phase 4 :**
1. **Le voile « génération en cours » recouvrait chaque case en permanence** — un `display:flex` d'auteur
   écrase l'attribut `hidden` (qui n'est qu'un `display:none` de la feuille du navigateur). Il masquait
   l'image *et interceptait tous les clics*. **Présent dans la v1.0.1 livrée en phase 4** : les critères
   chiffrés de la phase 4 restent vrais, mais l'affichage de la planche était dégradé et personne ne l'avait
   vu — aucun chiffre ne regardait l'écran. C'est ce qui a motivé l'ajout d'une **capture d'écran** au banc.
2. **Le texte débordait de la bulle** : la largeur utile était calculée sans tenir compte de la courbure de
   l'ellipse, et la hauteur n'était jamais vérifiée. Corrigé par la condition d'inscription
   `(a/rx)² + (b/ry)² ≤ 1` — la bulle **grandit** pour contenir son texte, elle ne le tronque jamais.
   Le contrôle `getBBox` qui l'aurait détecté n'existait pas : il a été ajouté *après* le constat visuel.
3. **La queue barrait le texte** : déplacer la bulle ne déplaçait pas la pointe, qui se retrouvait à
   l'intérieur. La queue suit désormais la bulle, et une pointe rentrée est repoussée hors du contour.

*Les trois étaient invisibles dans les chiffres et évidents à l'écran. Un banc qui ne regarde jamais le
rendu mesure l'exécution, pas le résultat.*

~~**⏳ Ce que la phase 5 ne fait PAS** : le relettrage d'une page traduite.~~
→ **✅ FAIT le 27/07 (v1.5.0)** — voir « Ingestion dans l'app » ci-dessous.

### Phase 3 dans l'app — Ingestion et relettrage ✅ *(atteinte le 27/07 — v1.5.0)*

Onglet **Ingestion** : une page à toi (image ou PDF) → **YOLO Manga109** (cases + bulles) → **Pixtral**
(OCR + traduction, bulle isolée puis page entière en contexte) → une planche dans l'app, une case par
cadre, une **bulle française posée là où elle a été trouvée**. Route `POST /manga/ingest` ; le
sous-processus tourne dans le venv **kohya** (c'est lui qui a `ultralytics` + torch cu128).

> **Critère de sortie** : sur une page réelle, cases découpées et servies, bulles rattachées à la bonne
> case, texte français, page exportée à la **géométrie d'origine**, 0 erreur JS.

**Résultat mesuré — banc `scripts/test_ingest_live.py`, sur une page japonaise réelle :**

| Mesure | Valeur |
|---|---|
| Cases créées / avec fichier / images servies | **5 / 5 / 5** |
| Bulles posées / avec texte français | **6 / 6** |
| Bulles hors cadre | **0** |
| Bulles **visibles dans le fichier exporté** (mesure pixels, une par une) | **6 / 6** |
| Mots par ligne (moyenne) | **1,87** (seuil 1,6 — en dessous, le texte est haché) |
| Export à la géométrie de la page source | ✅ 1809×2595 pour une source 603×865 (même format à 3 % près) |
| Erreurs JS | **0** |
| Durée détection + traduction | **~14 s** |

**Quatre défauts trouvés — tous par la mesure ou par le regard, aucun par le hasard :**
1. **Bulles en portrait.** Le japonais s'écrit **verticalement** : ses bulles sont hautes et étroites.
   Reprises telles quelles, elles donnaient du français **à un mot par ligne**. La bulle est désormais
   dimensionnée **par son texte** (bloc visé ~1,6 fois plus large que haut), pas par la boîte détectée.
2. **Cases écrasées à l'export.** Une planche ingérée a des cadres de tailles quelconques ; l'export les
   forçait au format de la première. Le format vient maintenant de **chaque case** (`recipe.box` + `page`).
3. **3 bulles sur 6 disparaissaient du fichier exporté.** Les cadres détectés se **chevauchent** (YOLO
   trouve parfois une grande zone contenant des petites) : une case dessinée ensuite recouvrait les bulles
   des précédentes. Désormais **deux passes** — toutes les images (les plus grandes d'abord), **puis** tous
   les calques de texte. *Aucun autre contrôle ne l'aurait vu : les 6 bulles étaient bien en base.*
4. **Lettrage minuscule dans les bandeaux plats.** La taille du texte était une fraction de la hauteur de
   **la case** ; dans un bandeau large et bas, ça donne un texte illisible. Elle est maintenant calée sur la
   hauteur de **la page** (~1,9 %) — ce que fait un lettreur — et la bulle **couvre au minimum celle
   d'origine**, sinon le japonais reste visible autour du français.

### Effacement du texte source et réutilisation des bulles ✅ *(27/07, v1.6.2)*

~~On superpose une bulle, on n'efface pas la source.~~ → **corrigé le jour même.**

Case à cocher **« effacer le texte d'origine »**. Aucune IA, et c'est délibéré : une bulle de manga est un
**aplat clair borné par un trait noir**. On amorce une diffusion sur le pixel le plus clair de la boîte de
texte — forcément du fond de bulle, puisque le texte est sombre —, elle s'arrête d'elle-même sur le trait,
on rebouche ses trous (les trous, ce sont les lettres) et on peint en blanc. Déterministe, instantané,
et ça **ne peut pas halluciner un dessin**.

⇒ Le **contour d'origine survit**. Donc on ne dessine plus de bulle par-dessus : **on réutilise celle de
la page**, et on n'y pose que le texte. C'est ce que font les groupes de traduction — la bulle fait partie
du dessin, elle épouse la composition.

| Mesure | Valeur |
|---|---|
| Bulles correctement vidées | **6 / 6** |
| Noir dans la zone du texte japonais — page source → case nettoyée | **0,070 → 0,000** |
| Pixels modifiés hors des bulles | **0** (1ʳᵉ version), diffusion bornée à 18 % de la page ensuite |
| Textes débordant de leur bulle | **0** |

**Deux erreurs de méthode, notées parce qu'elles se reproduiront :**
1. **Mon garde-fou se déclenchait à l'envers.** Je décidais « est-ce une bulle ? » selon que l'aplat touche
   les bords d'une fenêtre que j'avais moi-même choisie — or dans le cas **normal** (texte bien au centre
   d'une grande bulle), la fenêtre est entièrement à l'intérieur, donc l'aplat touche tous les bords. Les
   6 bulles tombaient dans le cas de repli. Le bon critère n'est pas géométrique mais **la surface atteinte**.
2. **Je mesurais l'effacement au mauvais endroit** : dans la page *exportée*, à l'emplacement du japonais —
   là où l'on vient justement de poser le français. Le noir *augmentait*, et la mesure concluait à l'envers.
   Il faut mesurer sur la **case nettoyée**, avant lettrage. *Une mesure au mauvais endroit est pire qu'une
   absence de mesure : elle donne l'assurance sans le contrôle.*

**Limite restante** : le texte français doit tenir dans une bulle dessinée pour du **japonais vertical**
(donc en portrait). Il y est plus haché qu'il ne le serait dans une bulle conçue pour lui — c'est le prix
de la fidélité au dessin, et c'est le bon arbitrage.

### Phase 7 — Un chapitre depuis un texte ⏳ *(la cible)*

> **Rappel de Quang, 27/07** : « un mode qui m'aide a generer automatiquement, selon ce que je definis,
> plusieurs images et plusieurs chapitres, qui cree automatiquement l'histoire que je dois valider, et
> qui remplit automatiquement chaque champ que je remplis a la main. […] C'est a cadrer, mais on en
> reparle. »
>
> **Ce que ca suppose, et qui existe deja** : le storyboard (`scripts/storyboard.py`, texte → cases +
> dialogues, jamais branche a l'app), la **base de personnages** (v1.14.0 — sans casting, une histoire
> generee ne saurait pas qui la joue), l'**amelioration de prompt** (v1.13.0 — c'est elle qui remplira
> les champs), et la boucle de validation (phase 6 — c'est elle qui recueille son accord).
> ⇒ **Le mode auto n'est plus de la recherche : c'est l'assemblage de quatre briques deja mesurees.**
> Reste a cadrer AVEC lui : quels champs il definit en entree (genre, personnages, longueur, ton), et
> a quel grain il valide (chaque case ? chaque page ? le decoupage avant toute image ?).
> ⚠ Le point dur reste celui du premier jour : la **continuite sur la longueur**, pas la generation.
>
> **Idée de Quang (27/07), retenue** : un bouton proposant **3 suites possibles** pour la case
> suivante, appuyé non sur la dernière case mais sur **les 4-5 précédentes** — « pour avoir une
> chronologie et une suite plutôt logique ». Manuel ou automatique, comme l'amélioration de prompt.
> *Avis : c'est la brique la MOINS risquée du mode auto* — texte vers texte, zéro GPU — et elle
> attaque le point dur là où il se joue vraiment : dans le **récit**, pas dans l'image. Elle est aussi
> la plus facile à valider (il lit trois phrases, il en choisit une). À faire **avant** la génération
> de chapitre entier.



Entrée : un **texte** (synopsis, script, découpage). Sortie : la suite des cases d'un chapitre, prêtes à
relire et à corriger. C'est le but de l'outil, rappelé par Quang le 27/07.

Ce que les phases précédentes ont déjà posé, et qui n'est donc pas à refaire :
- **l'identité** du personnage tient (LoRA, 89 % — phase 1) ;
- **le décor** tient sur une séquence (fond maître + ControlNet 0,55, 6/6 — phase 2) ;
- **la règle des deux types de cases** dit déjà quand utiliser l'un ou l'autre ;
- **la recette complète** de chaque case est enregistrée, donc une planche est rejouable ;
- **le lettrage** sait poser les répliques, et la **boucle de validation** sait recycler ce qui marche.

### Le périmètre réel *(précisé par Quang le 27/07)*

> « Ce qui sera important, ce sera surtout **la création**. […] la définition des images, la **cohérence des
> actions**, les **textes de dialogue générés automatiquement**, même si je pourrai les corriger. Il faut
> imaginer **plusieurs tests** : plusieurs types de scènes ou de séquences, de deux mangas, de chapitres ou
> de pages — cela peut aller d'une **romance** au **combat**, voire à la **pornographie**, sous plusieurs
> thèmes. Au final n'importe quel sujet : des **personnages humains**, des choses plus **extravagantes ou
> cinématographiques**, **imaginaires**, **futuristes**, des **robots**, etc. »

**Matrice de test — un chantier n'est pas validé sur un seul thème.** Ce qui marche sur une lycéenne dans
un couloir ne prouve rien sur un duel de mechas.

| Axe | À couvrir |
|---|---|
| **Genre** | romance · combat/action · **adulte / pornographie (voir le détail ci-dessous)** · quotidien/slice of life · horreur ou tension |
| **Sujet** | humain réaliste · humain stylisé · **robot / mecha** · créature imaginaire · décor futuriste |
| **Échelle** | une page · une séquence de 2-3 pages · un chapitre |
| **Registre visuel** | intimiste (peu de cases, gros plans) · cinématographique (plans larges, mouvement) |

#### Le volet adulte — explicité *(rappel de Quang, 27/07)*

> « Un des thèmes aussi importants pour moi à tester est le thème pornographique sur plusieurs genres,
> tout en restant légal bien sûr […] mais aussi les thèmes sexuels, de fétichisme et de domination femdom. »

C'était écrit en un mot (« pornographie ») dans la matrice — **trop peu pour être testable**. Un axe qui ne
nomme pas ses sous-genres ne se vérifie pas : « ça marche en porno » ne veut rien dire si l'un des registres
casse. Sous-genres à couvrir, **entre adultes**, tous légaux en France :

| Sous-genre | À vérifier en propre |
|---|---|
| Scène sexuelle explicite « classique » | anatomie tenue à deux personnages, cadrages serrés, N&B tramé sans bouillie |
| **Fétichisme** | accessoires et matières (cuir, latex, bas, bondage de corde…) — c'est du **détail constant**, donc de la fiche personnage/scène, pas du prompt jetable |
| **Femdom / domination** | ce qui casse ici n'est pas l'anatomie mais le **rapport de force** : posture, hauteur relative, regard, qui domine le cadre. C'est de la **mise en scène**, l'axe le plus dur pour un modèle de diffusion |
| Registre suggestif / ecchi | l'autre bout de l'échelle — vérifie que l'app sait aussi ne PAS être explicite quand on ne le demande pas |

**Ce que ça implique techniquement, et qui n'est pas neutre :**
1. **Deux personnages dans une case** — tout ce qui a été mesuré jusqu'ici l'a été sur **un** personnage seul.
   L'identité, le LoRA, IPAdapter : rien ne dit qu'ils tiennent à deux. C'est un **trou de mesure**, pas un acquis.
2. **L'anatomie en interaction** est le point de rupture connu de SDXL (membres fusionnés, mains). Le négatif
   par défaut de l'app devra probablement s'enrichir sur ce registre.
3. **La chaîne de vision (Pixtral) n'a pas refusé** la page explicite de Quang (mesuré, phase 3) — mais Pixtral
   sert à *analyser*, pas à générer. La génération est locale et non censurée : aucun verrou externe.
4. **Le femdom se juge sur la composition**, donc il se contrôle par **ControlNet openpose** (`make_pose.py` sait
   déjà fabriquer des squelettes synthétiques) plus que par le prompt.

**Limites, inchangées et non négociables** : mineurs ou apparence de mineur (« loli/shota » compris — réprimé en
France même en dessin), visages de personnes réelles. Projet personnel, aucune diffusion.

#### 🔁 Ne PAS repartir de zéro : **Muse a déjà résolu la moitié du problème** *(constaté le 27/07)*

Quang : « pour comprendre, tu peux t'inspirer du projet Muse par rapport à mes préférences ».
Muse (`D:\Download\02-Apps-Web\Muse\`, **dépôt local sans remote, délibérément hors synchro**) est son app de
roleplay adulte. Elle tourne sur **le même ComfyUI, la même carte**. Quatre briques y sont déjà éprouvées et
se transposent — *les recopier ici serait une duplication, on les réutilise* :

| Brique de Muse | Où | Ce qu'elle apporte au manga |
|---|---|---|
| **Taxonomie de contenu** (actes · contextes · effets · styles · lieux) | `app/src/lib/taxonomie.ts` | la catégorisation par thème que la bibliothèque de références réclame — **déjà écrite, en français, et validée par l'usage** |
| **Dictionnaire FR → tags booru** + **routage LoRA par pratique** | `app/src/lib/studio.ts` | les **LoRA correspondants sont déjà installés** dans `ComfyUI/models/loras/` : rien à télécharger |
| **Négatif « casting »** (interdit les personnages en trop) | `studio.ts` | répond directement au **trou de mesure « deux personnages »** : Muse a payé ce problème avant nous |
| **Filet déterministe d'interdits** (`INTERDIT_MAP`) | `studio.ts` | garde-fou **par code**, pas par prompt : mineurs · zoophilie · létal sont strippés du positif **et** poussés au négatif |

**Ce qui est à porter en priorité, et c'est un choix de sécurité, pas de confort** : le filet déterministe.
Un garde-fou écrit dans un prompt se négocie ; un garde-fou en code, non.

⚠️ **Discipline : le catalogue explicite reste chez Muse.** Ici on écrit le **mécanisme** (comment on
catégorise, comment on route, comment on garde-fou), jamais la liste détaillée de ses préférences — elle a
déjà un seul domicile, et c'est un dépôt que Quang garde volontairement local. *Une info = un seul endroit.*

⚠️ **Différence de moteur à vérifier avant de croire l'acquis de Muse** : Muse génère en **Pony**, le manga en
**Illustrious**. Les LoRA et le comportement des tags **ne sont pas garantis transférables** — c'est à
mesurer, pas à supposer. (Les 168 LoRA locaux comptent 65 Pony et 34 Illustrious.)

### 🚩 Conséquence d'architecture à trancher AVANT de construire

Tout l'acquis des phases 1 et 2 repose sur **un LoRA entraîné pour UN personnage** (35 min de GPU).
**Ça ne passe pas à l'échelle d'un outil « n'importe quel sujet »** : on ne va pas entraîner un LoRA par
robot, par créature et par figurant. Il faut une stratégie de cohérence qui ne demande **aucun
entraînement**. Pistes, par ordre de crédibilité :

1. **IPAdapter** (référence par image, sans entraînement) — ~~⛔ pas installé~~ → **✅ INSTALLÉ le 27/07**
   (voir la section dédiée plus bas). C'est le candidat le plus sérieux ; il reste à **mesurer**.
2. **Fiche de personnage textuelle détaillée + seed fixe** — mesuré à ~50 % en phase 1. Insuffisant seul,
   utile en complément.
3. **LoRA à la demande**, réservé aux personnages **récurrents** d'un projet long (ce que la phase 6 sait
   déjà préparer depuis les cases validées). Bon pour un héros, pas pour une figuration.

⇒ **Décision à prendre avec Quang** : installer IPAdapter et bâtir la cohérence dessus, ou assumer que
seuls les personnages récurrents ont un LoRA. Tant que ce n'est pas tranché, la phase 7 ne peut livrer que
ce qui est **indépendant du sujet** — c'est-à-dire le découpage narratif et les dialogues.

### 🧩 Conception : base de personnages + boucle de validation *(questions Quang, 27/07)*

> « Comment ça se passe au niveau de la création des personnages, ne serait-ce que de leur visage, et la
> cohérence maintenue entre les chapitres ? […] on pourrait avoir une base de données de tout type de
> personnages différents, c'est moi qui décide si je les valide. »

**A. La cohérence d'un personnage : trois niveaux, pas un seul.** Le choix dépend du rôle du personnage,
pas d'une préférence technique. Fiabilité mesurée sur ce projet et confirmée par l'avis extérieur :

| Rôle | Moyen | Coût | Fiabilité |
|---|---|---|---|
| **Héros récurrent** (1-3 par projet) | **LoRA** entraîné | 35 min GPU, une fois | **100 %** (mesuré, phase 1) |
| **Secondaires réguliers** | **IPAdapter** (image de référence) | ⛔ **à installer** | verrou *facial*, sans entraînement |
| **Figurants, décors, one-shot** | **fiche texte + seed fixe** | gratuit | ~50 % (mesuré) — suffisant pour qui passe une fois |

⇒ **L'installation d'IPAdapter est le chantier technique n°1** : c'est la seule brique qui manque pour
couvrir « n'importe quel sujet » sans entraîner. Identifiée comme manquante dès le 26/07, jamais faite.

**B. La base de personnages** — une **fiche** devient un objet de premier plan (aujourd'hui l'identité
n'est qu'une chaîne de caractères dans la recette du projet, ce qui ne survit pas à un chapitre 2) :

| Champ | À quoi il sert |
|---|---|
| `id`, `nom`, `role` (héros / secondaire / figurant) | choisit le niveau de cohérence ci-dessus |
| `traits` — tags visuels **constants** uniquement | injecté dans **chaque** prompt |
| `refs[]` — images de référence (face, 3/4, profil) | IPAdapter, et dataset de départ si on entraîne |
| `lora` + `trigger` (si entraîné) | verrou fort |
| `recette` (checkpoint, style, poids) | ce qui rend le rendu **reproductible d'un chapitre à l'autre** |
| `valide` (booléen, décidé par Quang) | rien n'entre en base sans son accord |

**La discipline qui compte** : `traits` ne contient QUE le constant. Tout ce qui varie (pose, expression,
cadrage) reste dans la case. C'est la même règle que les captions de LoRA, et c'est elle qui fait tenir la
cohérence — pas la quantité de description.

**C. Apprendre des images REJETÉES — mon avis : à ne PAS faire tel quel.**
Un ❌ ne dit pas *pourquoi*. La même image peut être refusée pour la pose, le visage, le cadrage ou le
style. Réinjecter « évite ça » sans connaître la cause n'apprend rien d'utilisable, et alimenter un négatif
à partir des rejets **empoisonnerait** la génération. L'avis extérieur consulté dit la même chose de son
côté, et c'est aussi ce que disait la décision Generate Studio du 29/06 : l'apprentissage sur **signal
faible** avait été jugé non fiable. **Un ❌ seul EST un signal faible.**

**Ce qui marche, et qui coûte un clic** : ❌ **+ une cause** parmi 4-5 (*visage · cadrage · anatomie ·
style · hors sujet*). La cause, elle, est actionnable — « cadrage » corrige les règles de cadrage,
« visage » remonte l'ancre d'identité d'un cran, « style » ajuste les tags. On transforme un signal
inutilisable en signal utile pour le prix d'un bouton. **C'est ma recommandation.**

Ce qui manque, et qui est le vrai travail :
1. **Le découpage narratif** — un LLM transforme le texte en *storyboard* : combien de cases, quel
   cadrage, quelle action, quelle réplique. C'est du texte vers du texte, donc peu risqué.
2. **La continuité de scène sur la LONGUEUR** — le piège n°1 de tout le chantier, pointé par les 3 voix
   dès le premier jour : ce n'est pas le visage qui casse une planche, c'est le décor et les accessoires
   qui dérivent. Sur 40 cases, le problème change d'échelle.
3. **Le ratio à assumer** : l'IA fait ~30 % du travail. Un chapitre généré est un **premier jet à
   remonter**, pas un livrable. L'app doit être conçue pour ça — relecture séquentielle, régénération
   d'une case sans casser les autres — pas pour livrer un chapitre d'un clic.

### Phase 6 — Boucle de validation 🔄 *(machinerie livrée le 27/07 — v1.7.0 ; reste l'entraînement)*
**Reprendre la décision GS du 29/06, ne pas réinventer** : l'apprentissage automatique, invisible et
appliqué sur signal faible avait été jugé non fiable et **rétrogradé en suggestions à valider**.
Ici : Quang note ✅/❌ ; le validé alimente (a) une bibliothèque de recettes gagnantes réutilisables,
(b) à ~30-50 cases validées d'un même style, **le dataset d'entraînement du LoRA suivant** — c'est là que
la boucle paie vraiment. **L'app propose, elle n'impose jamais.**
> **Critère de sortie** : un 2ᵉ LoRA entraîné à partir de cases validées bat le 1er sur le test de la phase 1.

**Livré (v1.7.0) — onglet « Validé » :** les cases notées ✅ alimentent une bibliothèque de recettes
rejouables, et un bouton écrit le **dataset du LoRA suivant** (`POST /manga/dataset` →
`dataset_<projet>/`, paires image + caption). `prep_train.py` accepte désormais **n'importe quel**
dataset (`--src`, `--trigger`) au lieu d'être figé sur celui de la v1.

Les captions sont construites selon la règle payée sur le LoRA v1 : **trigger + tags de style + ce qui
VARIE**, jamais un attribut constant du personnage — le décrire apprendrait au modèle qu'il est
*détachable*.

**Résultat mesuré — banc `scripts/test_validation_live.py` :**

| Mesure | Valeur |
|---|---|
| Cases validées vues par l'app | 2 ✅ / 1 ❌ sur 4 |
| Recette **copiée** dans la case vide | ✅ (avec un **seed renouvelé** — sinon on rejoue la même image) |
| **Autres cases modifiées d'office** | **0** — *l'app propose, elle n'impose pas* |
| Dataset écrit : images / captions / appariées | **2 / 2 / 2** |
| Trigger en tête, aucun attribut constant | ✅ |
| **L'entraîneur accepte le dossier** | ✅ (`prep_train.py --src` exécuté pour de vrai) |
| Erreurs JS | 0 |

La propriété « l'app n'impose rien » est **falsifiable** : sabotée (la recette appliquée à toutes les
cases), le banc passe de 0 à 3 et vire au rouge. C'est la seule qui compte vraiment — une boucle qui
s'applique toute seule serait une régression sur la décision Generate Studio du 29/06.

### LoRA v2 — entraîné et mesuré le 27/07 : **le critère de sortie n'est PAS atteint**

Dataset v2 (`manga_dataset_v2.py`, 28 images) généré **sans ReActor** — le LoRA v1 sert d'ancre
d'identité — avec un **FaceDetailer** qui re-rend le visage à 512 px, ce qui rendait enfin possible ce
que ReActor interdisait : des plans larges au visage résolu. Entraînement 1 344 steps, 8 epochs, ~35 min.

> ## ⛔ CORRECTION DU 27/07 — une partie des chiffres ci-dessous est INVALIDE
>
> La « taille du visage détecté / hauteur d'image » a été **calibrée après coup**, sur des images dont
> j'avais vérifié le cadrage à l'œil. Elle **ne sépare pas les classes** :
>
> | Cadrage constaté visuellement | Mesure |
> |---|---|
> | gros plan | 0,470 · 0,479 |
> | **buste** | **0,448** — indiscernable d'un gros plan |
> | américain | 0,201 |
> | **plan en pied** | **0,207 · 0,192 · 0,150 · 0,000 · 0,000** — chevauche l'américain, et le détecteur échoue deux fois |
>
> **Ce qui est retiré** : la répartition des cadrages des datasets (« 75 % gros plan », « 18 % américain »…),
> l'affirmation « aucun vrai plan en pied n'est atteint », et « le v2 cadre 11 % plus large » — un écart de
> 0,227 → 0,202 est **dans le bruit** d'un instrument qui donne 0,448 pour un buste et 0,207 pour un pied.
>
> **Ce qui reste vrai**, parce que vérifié à l'œil : le dataset v1 est visiblement presque tout en buste ;
> le dataset v2 contient des cadrages **visiblement distincts** (gros plan, buste, américain, pied) ;
> et un prompt « full body » **produit bien un plan en pied** — donc le modèle ne « résiste » pas comme je
> l'ai écrit.
>
> **La leçon, et elle est plus utile que le LoRA** : j'ai posé un seuil (« < 0,09 = plan en pied ») que je
> n'avais **jamais établi**, et j'en ai tiré des conclusions confiantes. Un second juge (Pixtral) disait
> « buste » sur les mêmes images en pied — j'ai classé son verdict en bruit alors qu'il tombait juste sur
> le fond. **Deux instruments non calibrés qui s'accordent ne se corroborent pas : ils se trompent
> ensemble, et cet accord m'a rendu confiant.** Un seuil doit être calibré sur des cas dont on connaît la
> réponse *avant* de servir à conclure.
>
> ### ✅ Mesure refaite sur une base valide — `mesure_cadrage.py` (27/07)
>
> Plus de proxy : on prend la **définition**. Un cadrage, c'est ce qui entre dans le champ, et les
> keypoints OpenPose le disent — chevilles visibles ⇒ plan en pied, genoux ⇒ américain, etc. Un détecteur
> de visage prend le relais sur les cadrages serrés, où OpenPose ne voit aucun corps (et pour cause).
>
> **`--calibrer` est passé avant tout usage** : 7/9 sur l'étalon, et surtout **2 sous-estimations,
> 0 surestimation**. L'outil rate des plans larges, il n'en invente jamais. Il le dit lui-même et en tire
> ses propres limites : « c'est un plan large » est fiable, « ce n'est pas » ne l'est pas ⇒ **il ne peut
> pas établir une répartition, seulement un plancher.**
>
> | Dataset | Plans larges (genoux ou chevilles visibles) |
> |---|---|
> | v1 — 24 images | **0** — pas un seul |
> | v2 — 28 images | **≥ 8** (6 en pied + 2 américains) = **≥ 29 %** |
>
> ⇒ **Le rééquilibrage du dataset v2 est réel, et cette fois c'est établi.** Ce qui reste retiré, faute
> d'instrument capable de le soutenir : la répartition détaillée, et le « 11 % plus large » du LoRA v2.

**Comparatif v1 vs v2, même seed (222222), même checkpoint, poids 0,8 :**

| Mesure | v1 | v2 | Lecture |
|---|---|---|---|
| Taille du visage sur la case « full body » | 0,227 | **0,202** | cadre **11 % plus large** — réel, mais les deux restent classés « buste » |
| Grain de beauté vu (juge Pixtral, question fermée) | 0/3 | **0/3** | **non corrigé** |
| Visage lisible | 3/3 | 3/3 | égal |
| Couleur des yeux | ambre 3/3 | ambre à l'œil | le juge a dit « red/other » : **c'est du bruit**, vérifié sur les images |

**⛔ Le critère de sortie de la phase 6 n'est pas atteint** : le v2 ne « bat » pas le v1. Il l'améliore
marginalement sur un seul point. Et il n'a même pas été entraîné à partir de *cases validées* — il ne
teste donc pas la boucle elle-même, seulement la correction des deux réserves.

**Ce que la mesure a appris, et qui vaut plus que le LoRA :**

1. ~~**Réserve n°2 (cadrage)** — « aucun vrai plan en pied n'est atteint », « le modèle de base résiste ».~~
   ⛔ **RETIRÉ** : ces deux affirmations reposaient sur l'instrument invalide (voir l'encadré ci-dessus).
   Vérification à l'œil : le dataset v2 contient bien des cadrages distincts jusqu'au plan en pied, et un
   prompt « full body » en produit un. **La réserve n°2 est donc probablement moins grave qu'annoncé —
   mais elle n'est pas mesurée, faute d'instrument valide.** C'est l'état honnête : *on ne sait pas*.
   Il faut d'abord une mesure de cadrage qui tienne (piste : le rapport hauteur du visage / hauteur du
   personnage, invariant d'échelle, plutôt que la hauteur du visage seule).
2. **Réserve n°1 (grain de beauté) — non corrigée, mais on sait enfin pourquoi.** Mesure directe sur les
   datasets : le grain n'est visible que sur **2/12** images du v1 et **3/12** du v2, malgré une
   accentuation à `(mole:1.4)`. Le dataset reste **muet** sur ce détail. ⇒ L'explication « un
   micro-détail ne s'apprend pas » n'est ni prouvée ni réfutée — on n'a **jamais montré** ce détail
   assez souvent pour le savoir. Les deux vraies options : **l'incruster** dans les images du dataset
   (inpainting ciblé), ou **le retirer du design du personnage**. Mettre plus de poids dans le prompt
   ne marche pas : c'est mesuré.

### ⛔ Chantier LoRA v2 : CLOS le 27/07, sans suite

Mesure refaite avec l'instrument **valide** (`mesure_cadrage.py`), à seed identique :

| Case | v1 | v2 |
|---|---|---|
| gros plan | serré | serré |
| **full body** | **plan en pied** | **plan en pied** |
| émotion | serré | serré |

**Identique sur les trois.** Le v2 n'apporte donc rien de mesurable — ni sur le cadrage (seule réserve
encore ouverte), ni ailleurs. Et la réserve du grain de beauté est close par décision.
⇒ **Le LoRA v1 est le bon, et le restera.** Le v2 reste sur le disque mais n'a pas d'usage.

*Ce chantier a coûté ~1 h de GPU pour un résultat nul. Ce qu'il a produit de vraiment utile est ailleurs :
la réparation de `prep_train.py` et `train_lora.sh` (le v1 n'était réentraînable par personne), et la
découverte que ma mesure de cadrage était invalide.*

**Décision : le v1 reste le LoRA par défaut de l'app.** Le v2 est installé à côté
(`ComfyUI/models/loras/_manga_test/zqmg1rl_v2.safetensors`) et sélectionnable. Changer le défaut pour
un gain de 11 % sur un seul axe, avec un style légèrement plus bruité sur la case 3, ne se justifie pas.

### ControlNet openpose — squelettes synthétiques (27/07)

`make_pose.py` fabrique des squelettes **OpenPose synthétiques** (COCO-18, palette canonique) plutôt que
d'en extraire d'une image : une pose extraite hérite du cadrage de son image d'origine, alors qu'ici la
position et l'échelle du squelette dans la toile **sont** le cadrage. Déterministe, gratuit, sans modèle.

Constat **visuel** (la mesure de cadrage n'étant pas fiable, on ne prétend pas chiffrer) : à strength
**0,8-1,0**, on obtient des plans en pied propres et bien composés, avec la pose imposée. À 0,6 l'effet est
plus lâche. Le prompt seul donne aussi un plan en pied sur ce sujet — l'apport d'openpose est donc surtout
le **contrôle** de la pose et de la place du personnage dans le cadre, pas le fait d'obtenir un plan large.

**⏳ Ce qui reste** : une mesure de cadrage valide, trancher le sort du grain de beauté
(incruster ou retirer du design), puis entraîner un LoRA **depuis des cases réellement validées** —
c'est seulement là que le critère de la phase 6 sera testé pour ce qu'il dit.

Rejouer la chaîne (**couper ComfyUI** — 16 Go de VRAM ne suffisent pas aux deux, ~40 min) :
```
python scripts/prep_train.py --src <dataset> --trigger <trigger>
bash scripts/train_lora.sh
python scripts/compare_lora.py         # comparatif v1 vs v2, mesures reproductibles
```

**⚠️ Bug latent trouvé au passage** : `prep_train.py` cherchait le dataset dans `scripts/dataset/` alors
qu'il est à la racine du projet. Il ne trouvait donc **plus rien, en silence, depuis que les scripts ont
été rangés dans `scripts/`** (commit `d2ccc5c`) — le LoRA v1 n'aurait pas pu être réentraîné. Corrigé, et
vérifié : 24 images × 6 repeats = 1 152 steps, exactement les chiffres de la phase 1.

### IPAdapter — installé le 27/07 ✅ *(le blocage annoncé depuis le 26/07 est levé)*

C'était le **chantier technique n°1** : la seule brique manquante pour tenir un sujet quelconque **sans
entraîner**. Installée par le chemin reproductible, pas à la main.

| Élément | Détail |
|---|---|
| Nœuds | `cubiq/ComfyUI_IPAdapter_plus` → `ComfyUI/custom_nodes/` — **774 → 811 nœuds**, 36 nœuds IPAdapter |
| Encodeur d'image | `CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors` (2,53 Go) → `models/clip_vision/` |
| PLUS SDXL | `ip-adapter-plus_sdxl_vit-h.safetensors` (848 Mo) — style / sujet |
| PLUS FACE SDXL | `ip-adapter-plus-face_sdxl_vit-h.safetensors` (848 Mo) — verrou facial sans insightface |
| FACEID PLUS V2 | `ip-adapter-faceid-plusv2_sdxl.bin` (1,49 Go) **+ son LoRA compagnon** (372 Mo, `models/loras/`) |
| Presets exposés | `STANDARD` · `VIT-G` · `PLUS (high strength)` · `PLUS FACE (portraits)` |

**Tout passe par `scripts/fetch_models.py`** (étendu ce jour avec un champ `dest`) — c'est la leçon du modèle
YOLO disparu : un poids binaire ne se versionne pas, **la commande qui le rapporte, si**.

**Deux pièges payés pendant l'installation :**
1. **Le nom du fichier de l'encodeur n'est pas cosmétique.** Sur HuggingFace il s'appelle `model.safetensors` ;
   déposé sous ce nom, `IPAdapterUnifiedLoader` ne le trouve **jamais** — il cherche par motif dans
   `models/clip_vision/`. Il faut le renommer `CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors`.
2. **FaceID v2 sans son LoRA compagnon ne marche pas** — ce sont deux fichiers, dans deux dossiers différents,
   et l'un sans l'autre donne un rendu qui part en vrille sans message d'erreur.

**Redémarrage de ComfyUI — par son propre chemin, pas en tuant un process.** ComfyUI est ici lancé **par le
proxy Generate Studio** (chaîne de parenté vérifiée) ; le proxy expose `POST /shutdown` et `POST /start`, avec
le garde-fou du mandat Quang du 22/06 : *on coupe depuis n'importe quelle appli, mais jamais une génération en
cours*. Le dry-run a confirmé `busy: false` avant de couper. Secret : `ComfyUI/.studio_secret`, en Bearer.

#### ✅ MESURÉ le 27/07 — `scripts/test_ipadapter.py`

**IPAdapter fonctionne sur ce checkpoint, mais seulement à un réglage que rien n'annonçait.**
Aux valeurs par défaut il est inutilisable ; aux bonnes, il tient le personnage en gardant le N&B.

| Réglage | Ce qui se passe |
|---|---|
| Preset **`PLUS FACE (portraits)`** — le nom invite pourtant à le choisir | ⛔ **détruit le rendu** : noir 0,112-0,290 contre 0,599 au témoin |
| Preset **`PLUS (high strength)`** | ✅ préserve le noir (0,443-0,593) |
| Poids **0,8** | ⛔ la planche **vire au bleu**, et la case « full body » part hors sujet |
| **Poids 0,4 · `end_at` 0,5 · référence convertie en N&B** ⭐ | ✅ les 3 cases propres, N&B tenu |

**Comparatif final, mêmes 3 cadrages, même seed 222222 :**

| Mesure | prompt seul | LoRA v1 | **IPAdapter 0,4** |
|---|---|---|---|
| Proximité à la référence (cosinus) | 0,851 (2/3) | **0,894** (3/3) | 0,839 (3/3) |
| **Saturation** (un vrai N&B tend vers 0) | 0,198 | 0,333 | **0,149** ⭐ |
| Fraction de noir | 0,498 | 0,500 | 0,456 |

⇒ **IPAdapter sort la planche la plus proprement monochrome des trois** — plus que le LoRA, dont le dataset
très contrasté tirait vers la « spot color » rouge (effet secondaire déjà noté en phase 1).

**⚠️ Ce que ces chiffres NE disent PAS, et le banc le dit lui-même.**
L'instrument (YOLO recadre le visage → CLIP-ViT-H l'embedde) a passé l'épreuve **facile** : il sépare ce
personnage d'une blonde de 30 ans en blouse (0,908 contre 0,650). Il a **échoué à l'épreuve difficile** — le
même personnage avec **les yeux et la forme du visage changés** sort à 0,868, en plein dans le nuage
« même personnage » (0,868-0,941). ⇒ Il mesure « est-ce le même **genre** de personnage », **pas l'identité
fine** que la phase 1 mesurait. Les trois colonnes se comparent entre elles ; **aucune ne prouve « c'est bien
lui »**. *C'est pourquoi le banc refuse d'afficher une frontière : un chiffre sans instrument valide est pire
qu'un chiffre absent.* Le juge qui tranche reste **l'œil de Quang** — et la boucle de validation de la phase 6
existe précisément pour recueillir ce verdict-là.

**Quatre pièges payés pendant cette mesure, tous instructifs :**
1. **insightface — l'outil « standard » — est inutilisable ici.** C'est la mesure d'identité de toute la
   littérature IPAdapter/InstantID… sur du **photoréaliste**. Sur du manga N&B : 2/12 visages détectés au
   seuil normal, 7/12 en descendant à 0,1 (au prix de l'alignement), et **5/12 même sur un visage déjà
   recadré par YOLO**, qui en trouve 11/12. Deux échecs de même nature ⇒ changer d'outil, pas s'acharner.
2. **La référence donnée à IPAdapter était choisie au hasard.** Le code prenait la première image où un visage
   était détecté, pendant que le commentaire affirmait prendre « celle où le visage est le plus grand ».
   Corrigé : `ds_20`, **visage à 52 % de l'image** — et le résultat en dépend fortement. *Un commentaire qui
   décrit une intention plutôt que le code est un mensonge à retardement.*
3. **Ma première mesure du défaut était aveugle au défaut.** J'avais vu un rendu « délavé » et mesuré la
   **noirceur**. La planche contact a montré autre chose : IPAdapter **injectait de la couleur** (bleu, cyan)
   — et du bleu sombre est *sombre*, donc la noirceur n'y voyait rien. La bonne mesure était la
   **saturation**. Même faute que « mesurer au mauvais endroit » sur l'effacement des bulles.
4. **La couleur venait de la référence elle-même.** IPAdapter transfère la **palette** de l'image montrée, et
   le négatif textuel `color` ne pèse rien face à un conditionnement par image. ⇒ **Toujours convertir la
   référence en N&B** avant de la lui donner (`--ref-nb`).

**Conséquence pour la phase 7 — la question « faut-il un LoRA par sujet ? » a sa réponse :**

| Rôle | Moyen | État |
|---|---|---|
| Héros récurrent | **LoRA** | ✅ 100 % (phase 1), le plus fidèle sur les attributs fins (yeux ambre 3/3) |
| **Secondaires, sujets ponctuels, « n'importe quel sujet »** | **IPAdapter PLUS 0,4 / end 0,5 / réf N&B** | ✅ **utilisable — c'était le verrou de la phase 7** |
| Figurants | fiche texte + seed | ~50 % (phase 1) |

> **⏳ Restent ouvertes, dans cet ordre :**
> 1. Un sujet **sans LoRA du tout** (robot, mecha, créature) — mesuré ici sur un personnage qui *a* un LoRA,
>    donc la question « n'importe quel sujet » n'est pas close.
> 2. **Deux personnages dans une même case** — trou de mesure signalé par le volet adulte.
> 3. Le transfert de **style** d'une page de Quang (brique de la phase 8).

### Phase 10 — Créer un manga entier : les questions de faisabilité *(Quang, 27/07)*

> « Si tu devais créer un petit manga de 10 ou 20 pages, sur trois ou quatre thèmes, avec un, deux,
> trois, quatre, voire cinq personnages — est-ce que tu y arrives ? Comment génères-tu ces
> personnages ? […] faut-il afficher seulement leur visage ou leur corps entier, leurs vêtements,
> leur style vestimentaire ? […] et même leur corpulence. Reste critique sur la faisabilité. »

**Réponse par nombre de personnages — c'est LA variable qui décide.**

| Personnages par case | Faisable aujourd'hui ? |
|---|---|
| **1** | ✅ **Oui, solide.** Identité tenue (LoRA 100 %, IPAdapter validé), décor tenu, lettrage. |
| **2** | ✅ **Oui, mesuré** (`test_duo.py` : co-présence et contact simple passent). ⚠ Mais tenir **DEUX identités précises** dans la même case n'est PAS mesuré : le modèle mélange volontiers les attributs. |
| **3** | 🟠 **Dégradé.** SDXL perd le compte et fusionne les corps. Parade réelle : **openpose à N squelettes** (`make_pose.py` sait déjà en composer) pour imposer les places. |
| **4-5** | ⛔ **Pas de façon fiable, et je ne le promets pas.** La voie réaliste n'est pas de tout générer d'un coup : c'est de **composer** — générer les personnages séparément et les assembler. Ce n'est plus de la génération, c'est du montage, et ça change l'outil. |

**Fabriquer un personnage — trois voies, par coût croissant :**

| Voie | Comment | Fiabilité |
|---|---|---|
| **Texte seul** | ses traits constants, injectés partout | ~50 % (phase 1) — suffit pour un figurant |
| **Image de référence** (générée par l'app **ou** apportée par Quang) | IPAdapter, réglage validé le 27/07 | bon sur le visage, sans entraînement |
| **LoRA** | 20-30 images, 35 min de GPU | **100 %** (phase 1), pour un héros récurrent |

⇒ **Une image récupérée vaut une image générée** — même mécanisme. Seule contrainte mesurée : la
**convertir en N&B** avant de la donner à IPAdapter, sinon il transfère sa palette.

**Visage, corps, vêtements ou corpulence ? La question la plus technique, et elle a une réponse mesurée :**
- **Le visage décide de l'identité**, et IPAdapter le veut **GRAND** : la référence retenue au banc
  occupe **52 % de l'image**. Une référence en pied ne porte presque aucune information de visage —
  c'est exactement l'échec de l'essai 3 (character sheet « visages non résolus »).
- **Vêtements et corpulence ne se transmettent PAS fiablement par l'image.** Ils s'écrivent en
  **tags** (`black hoodie`, `tall`, `muscular`, `petite`) — le modèle les respecte bien, et un tag se
  corrige sans rien régénérer.
- ⇒ **La bonne fiche est MIXTE : un portrait serré en référence + les tags de tenue et de corpulence.**
  C'est déjà ce que la table `manga_chars` stocke (`refs[]` + `tags`).
- ⚠ **Ce que je ne promets pas** : une corpulence identique d'une case à l'autre. Les micro-détails
  dérivent (mesuré : réserve n°1 de la phase 1), et la directive du 27/07 s'applique — *la qualité de
  l'ensemble prime*.

**Verdict sur « 10-20 pages » : oui, à une condition.** 1 à 2 personnages par case, un casting de 3-4
sur l'ensemble, les gros plans à un seul personnage. Le coût principal ne sera pas la génération mais
la **continuité** — le piège n°1 depuis le premier jour.

### Phase 11 — Un semblant de MOUVEMENT par une suite d'images 🔄 *(idée Quang, 27/07 — testée le jour même)*

> « Est-ce possible de créer plusieurs images qui créent un semblant de mouvement, comme les
> dessinateurs qui enchaînent plusieurs pages ? Un effet de mouvement, ou un GIF. »

**Ce qu'on n'utilise PAS, et pourquoi.** Aucun modèle vidéo n'est installé (`animatediff_models/` et
`CogVideo/` sont **vides** — vérifié). Et ces modèles produisent du photoréaliste ou de l'anime
**couleur** : plusieurs Go à télécharger pour un rendu hors sujet. Le manga N&B tramé n'est pas leur
domaine.

**Ce qu'on fait à la place — la méthode des dessinateurs : des POSES CLÉS.** Même seed, même prompt,
même checkpoint ; **seule la pose change**, imposée par des squelettes openpose interpolés entre deux
postures (`test_mouvement.py`, qui réutilise `make_pose.py`). Déterministe, gratuit, et le mouvement
est **choisi** plutôt que subi.

**Mesuré sur 6 images (un coup de poing) :**

| Mesure | Valeur |
|---|---|
| Cohérence entre images **voisines** (CLIP) | min 0,841 · **moy 0,895** |
| Écart entre la **première** et la **dernière** | 0,845 |
| Durée | ~14 s par image |

Les deux critères comptent **ensemble** : une suite très cohérente mais immobile est un échec aussi net
qu'une suite qui bouge en changeant de personnage à chaque vignette.

**⚠️ Un défaut trouvé à l'œil, qu'aucun chiffre ne signalait** : au premier essai, les images 1-2
sortaient **de dos** et les suivantes **de face**. Cause : *un squelette openpose est en 2D et ne dit
pas l'orientation* — les mêmes points se lisent dans les deux sens. Corrigé en fixant `front view,
facing viewer` au prompt et `from behind, back view` au négatif. **Le cosinus global ne voyait pas ce
demi-tour** : encore une mesure aveugle au défaut qu'elle était censée attraper.

**Ce que ça fait, et ce que ça ne fait pas — à ne pas confondre :**
- ✅ **Une séquence de cases** qui donne l'impression du mouvement dans une planche : c'est utile, et
  c'est exactement le langage du manga (les cases successives d'un même geste).
- ⛔ **Pas un GIF fluide.** 6 poses ne font pas une animation ; les plis du vêtement et les détails
  sont redessinés à chaque image, donc ça « fourmille ». Pour du fluide il faudrait un modèle vidéo —
  hors sujet ici (voir plus haut).
- ⚠️ **Le visage n'est pas résolu** en plan large : limite structurelle déjà connue (phase 2). Pour un
  mouvement en gros plan, il faudrait le FaceDetailer du dataset v2.

> **Critère de sortie** : une séquence de 3-4 cases d'un même geste, intégrée dans une planche, que
> Quang juge lisible comme un mouvement. ⏳ Reste à brancher dans l'app (aujourd'hui : script seul).

### Phase 8 — La bibliothèque de références ⏳ *(demande Quang du 27/07)*

> « L'application pourrait se nourrir de scans ou d'images […] de mangas que j'apprécie. Il faudra les
> catégoriser correctement par thème […] cela peut aider à la compréhension de ce que je souhaite créer, et
> surtout au style d'image qui doit être créé. Si je ne charge rien de spécial, ce sera créé par
> l'application de A à Z. »

**Le principe qui commande tout le reste : la bibliothèque est un ACCÉLÉRATEUR, jamais un PRÉREQUIS.**
Une app qui exige d'être nourrie avant de servir est inutilisable au premier lancement. Rien de chargé ⇒ elle
génère de A à Z avec la recette par défaut (Illustrious + tags N&B de l'essai 1 + LoRA du projet s'il y en a
un). Une référence ne fait que **remplacer un défaut**, elle n'ouvre aucune fonction.

**Une image donnée ne sert pas à une chose mais à trois, et il faut les séparer** — les mélanger est
exactement ce qui produit un « ça ressemble vaguement » inexploitable :

| Ce qu'on prend dans la référence | Par quel moyen | État |
|---|---|---|
| **Le style** (trait, trames, contraste, ambiance) | fiche de style Pixtral → `reusable_prompt` injecté dans le prompt | ✅ **acquis** (phase 3) |
| **L'apparence** d'un personnage / d'un objet | **IPAdapter** (image de référence, sans entraînement) | ✅ installé, ⏳ à mesurer |
| **La composition** (mise en page, rythme des cases) | détection YOLO de la page → la grille devient un **gabarit de planche** | ✅ **acquis** (phase 3), jamais réutilisé dans ce sens |

⇒ **Le gabarit de planche est le gain le moins cher et le plus sous-estimé** : le découpage YOLO existe déjà et
tourne en ~14 s. Réutiliser la *grille* d'une page qu'il aime — sans rien copier de son dessin — donne
immédiatement un rythme de lecture crédible, ce qu'aucun prompt ne sait produire.

**La catégorisation par thème** : Pixtral **propose** les tags (il classe déjà correctement les mises en page
et sort une fiche de style structurée), **Quang valide**. Même règle que la boucle de validation de la
phase 6 : *l'app propose, elle n'impose jamais*. La taxonomie n'est pas à inventer — celle de Muse existe.

**Ce qu'une référence N'EST PAS** : un modèle à copier. Le style graphique n'est pas protégé, les
**personnages et les planches** le sont. La bibliothèque sert à orienter une création, pas à reproduire une page.

> **Critère de sortie** : sur 3 références chargées et catégorisées, une planche générée que Quang juge « dans
> l'esprit » de la catégorie demandée — **et** une planche générée **sans aucune référence chargée**, qui reste
> correcte. Le second test compte autant que le premier : il prouve que la dépendance n'existe pas.

### ✅ MESURÉ le 27/07 — deux personnages dans une case (`scripts/test_duo.py`)

Le trou de mesure du volet adulte. Échelle de quatre niveaux, 3 seeds chacun, sujets **adultes**
(28-30 ans, tenue de ville) — pas le personnage du LoRA, décrit « 18 ans » en uniforme scolaire, qui
n'a rien à faire dans un test de registre adulte.

| Niveau | Résultat |
|---|---|
| **n1 — côte à côte**, sans contact | ✅ 3/3 — deux personnes nettes, décor propre |
| **n2 — contact simple** (main sur l'épaule) | ✅ 2/3 |
| **n3 — rapport de force** (elle debout, lui à genoux, femdom) | ⛔ **échec** — l'homme à genoux **n'apparaît pas**. Il reste la femme seule et une forme confuse au sol |
| **n4 — étreinte serrée** | ✅ visuellement bon (2 personnes enlacées), mais le compteur n'en voit qu'une |

> ## ⛔ CORRECTION DU 27/07 (même jour) — mon diagnostic sur n3 était FAUX
>
> J'avais conclu : « le rapport de force ne s'écrit pas, il faut ControlNet openpose ». J'ai construit
> les squelettes à deux corps (`make_pose.py`, posture agenouillée + scènes duo) pour l'imposer.
> **Les deux affirmations sont infirmées, mesure à l'appui :**
>
> | Bras | Deux personnages |
> |---|---|
> | **Texte seul**, sans le terme de cadrage | **3/3**, et visuellement **exactement la scène voulue** — femme debout dominante, homme à genoux, tête levée vers elle |
> | Texte + **ControlNet openpose 0,8** | 2/3, et **le rendu est mauvais** |
> | Texte + **ControlNet openpose 1,0** | 2/3, mauvais également |
>
> **Le ControlNet DÉGRADE ici**, il n'aide pas : le modèle lit mon squelette agenouillé comme un
> **homme debout de petite taille** — cuisse verticale et tibia au sol ne disent pas « à genoux »,
> ils disent « jambes courtes ». Un squelette openpose transmet des positions d'articulations, pas
> une intention de posture.
>
> **La vraie cause de l'échec, isolée par un banc à une seule variable** (`test_lowangle.py`, 8 seeds
> par bras) : **`low angle shot from below`**.
>
> | Prompt | Deux personnages |
> |---|---|
> | sans le terme de cadrage | **6/8** |
> | avec `low angle shot from below` | **3/8** |
>
> ⇒ **Ce n'est pas la mise en scène qui ne passe pas, c'est le terme de CADRAGE qui efface le second
> personnage** — il fait dériver la composition vers un sujet unique vu d'en bas. La règle utile est
> donc l'inverse de ce que j'avais écrit : **le rapport de force s'écrit très bien en toutes lettres ;
> c'est le cadrage qu'il ne faut pas mélanger au même prompt.**
>
> **La leçon, et elle se répète** : j'ai tiré une règle générale (« la mise en scène ne passe pas par
> le texte ») d'un échec dont je n'avais pas isolé la variable, puis j'ai construit un outil pour la
> contourner. Le banc qui départageait les deux explications coûtait dix minutes. *Avant de bâtir une
> parade, il faut avoir mesuré ce qu'on contourne.*
>
> **Ce qui reste acquis de ce détour** : `make_pose.py` sait désormais composer des scènes à
> plusieurs corps (`placer()`, `dessine_pts()`, posture agenouillée) — utile pour le **cadrage**, qui
> reste son domaine. Simplement, ce n'est pas l'outil du rapport de force.

**Ce que ça établit :**
- **Deux corps dans une case, ça marche** dès qu'ils sont simplement co-présents ou en contact simple.
  Ce n'était pas acquis — ça l'est maintenant.
- ~~**Ce qui casse, c'est la MISE EN SCÈNE, pas l'anatomie**, ⇒ parade : ControlNet openpose.~~
  ⛔ **RETIRÉ le jour même** — voir l'encadré ci-dessus. Le rapport de force **s'écrit très bien** (3/3
  en texte seul, et la scène est juste) ; c'est le terme de **cadrage** `low angle shot from below` qui
  effaçait le second personnage (6/8 sans, 3/8 avec). Le ControlNet openpose, lui, **dégrade**.
- **Limite d'instrument déclarée** : le compteur (visages YOLO, calibré 9/9 sur des images à une
  personne) **sous-compte en cadrage serré**, quand les visages se chevauchent. Il vaut pour les plans
  larges ; sur un gros plan enlacé, seul le regard tranche.

### Phase 9 — Partir d'une VRAIE image : photo → manga ⏳ *(demande Quang du 27/07)*

> « Est-il possible de transformer en manga une image ou une photo, n'importe quoi, même une scène […]
> soit l'intégrer sur une page, soit en faire une base de référence pour une nouvelle page ou un
> nouveau chapitre. » Et le rappel : « un contrôle total sur la génération en noir et blanc,
> partiellement colorée ou totalement colorée ».

**Oui, c'est faisable — et l'essentiel est déjà installé.** Mais il faut distinguer **trois usages** que
la même phrase recouvre, parce qu'ils n'ont ni la même difficulté ni le même outil :

| Ce que tu veux faire de la photo | Outil | État |
|---|---|---|
| **1. La convertir en case de manga** (garder la composition exacte, changer le rendu) | **ControlNet lineart/canny** + `img2img` à denoise moyen : le trait de la photo est figé, le modèle ne fait que redessiner en N&B tramé | ✅ `canny-sdxl-xinsir` **déjà téléchargé** (26/07), préprocesseurs déjà là |
| **2. En faire une référence de style/sujet** pour générer AUTRE chose | **IPAdapter** (validé le 27/07) + fiche de style Pixtral | ✅ les deux acquis |
| **3. En faire une base de scène** (décor réutilisé sur plusieurs cases) | **carte de profondeur** de la photo → ControlNet depth 0,55, exactement le mécanisme du « fond maître » | ✅ acquis en phase 2 — il suffit de remplacer le fond généré par une photo |

⇒ **Rien de neuf à inventer : c'est du branchement.** Les trois briques existent, aucune n'est reliée à
l'app pour une image d'entrée.

**Là où je suis critique — deux points qui décideront de la qualité :**
1. **Une photo réelle ne devient pas un beau manga par simple conversion.** Le contour d'une photo est
   *bruité* (cheveux, textures, plis) : passé en lineart, ça donne un fouillis de traits, pas un
   encrage. Un vrai manga a un trait **sélectif** — il jette 90 % du détail. La bonne recette est donc
   un ControlNet à **poids modéré** (la photo guide la composition) plus un **denoise élevé** (le
   modèle redessine vraiment), pas un « filtre » à faible denoise qui ne fera qu'un décalque sale.
   C'est mesurable, et ça se mesurera comme le reste.
2. **Le visage d'une personne réelle est hors périmètre** (règle déjà posée). Pour une scène, un décor,
   une pose, un objet : aucun problème. Pour un visage reconnaissable : non.

**Le contrôle colorimétrique demandé — la vraie réponse est qu'il y a trois modes, pas un curseur :**

| Mode | Chemin technique | État |
|---|---|---|
| **N&B** | tags de l'essai 1 (mesuré : ils font tout) + référence convertie en N&B si IPAdapter | ✅ acquis |
| **Couleur** | mêmes tags retirés | ✅ acquis |
| **Partiellement colorée** (« spot color ») | 🎯 **c'est le mode intéressant, et il est presque gratuit** : la planche est générée en N&B, la couleur est **rajoutée par-dessus** sur une zone choisie. Le rouge qui « persiste » malgré le négatif (réserve de l'essai 1) montre que le modèle sait déjà le faire — mais **subir** un rouge n'est pas le **choisir** | ⏳ à construire |

⇒ **Ma recommandation sur la couleur : ne pas la demander au modèle.** Un rendu N&B propre + un calque
de couleur appliqué au lettrage près (le calque SVG existe déjà) donne un contrôle **total et
réversible**, là où un prompt donne un résultat qu'on subit. C'est le même arbitrage que pour le
texte : ce qui doit être maîtrisé ne se génère pas, il se **superpose**.

> **Critère de sortie** : une photo de Quang → une case en N&B qui tient dans une planche ; la même
> photo → un décor réutilisé sur 3 cases cohérentes ; et une zone colorée choisie **par lui**, pas par
> le modèle.

---

## 5. Pièges connus (payés ou repérés — ne pas les repayer)

| Piège | Détail |
|---|---|
| **torch standard sur RTX 5070 Ti** | sm_120 (Blackwell) ⇒ **cu128 obligatoire** (`--index-url https://download.pytorch.org/whl/cu128`). |
| **Versions de `transformers` pour kohya** | Payé le 26/07 : `pip install transformers` (→ 5.14) casse le chargement du CLIP SDXL (`Unexpected key(s) text_model.*`). **Respecter `requirements.txt` : transformers 4.54.1, diffusers 0.32.1, accelerate 1.6.0.** |
| **VRAM partagée** | ComfyUI garde le checkpoint chargé (~13 Go / 16). **Couper ComfyUI avant d'entraîner** — génération et entraînement ne cohabitent pas sur cette machine. |
| **Visages en plan large** | SDXL ne résout pas un visage trop petit (essai 3), et ReActor échoue pour la même raison. Cadrer serré dans les datasets. |
| **Captions de LoRA de personnage** | Décrire ce qui **varie** (cadrage, expression, fond), jamais ce qui est **constant** (coiffure, uniforme) — sinon le modèle apprend que c'est détachable du personnage. |
| **Magi** | Licence **recherche académique uniquement**. Préférer YOLO26n ou Pixtral pour un usage perso durable. |
| **`llm.py vote`** | ~310 s (Kimi est le facteur limitant). À lancer en arrière-plan, pas en bloquant. |
| **Sorties qui polluent Generate Studio** | Payé le 26/07 : les scripts d'exploration écrivaient à la **racine** de `ComfyUI/output`, où GS range les siennes — 62 fichiers à nous mêlés à 850 à Quang (rapatriés par `scripts/rapatrie_outputs.py`). Tout nouveau script manga doit écrire sous `manga/<slug>/…` **et** passer par `/manga/harvest`. |
| **Créer ≠ sélectionner** | Le projet fraîchement créé n'était pas le projet courant → 6 cases rangées chez un voisin, **sans aucune erreur**. Toujours vérifier *où* un fichier atterrit, pas seulement *qu'il* atterrit. |
| **`hidden` écrasé par un `display` d'auteur** | `.busy{display:flex}` annule l'attribut `hidden` : le voile est resté affiché sur chaque case pendant toute la v1.0.1, masquant l'image et **avalant les clics**. Toujours écrire `.x[hidden]{display:none}` quand on donne un `display` à un élément qu'on masque par attribut. |
| **Un banc qui ne regarde jamais l'écran** | Les 3 défauts de la phase 5 étaient verts sur tous les chiffres. Un banc d'UI doit produire une **capture** — et un contrôle géométrique (`getBBox`) quand la question est « est-ce que ça tient dedans ». |
| **Un secours qui echoue en silence** | Le detecteur de visage de repli etait dans un `try/except` muet. Lance avec le mauvais interpreteur (sans `ultralytics`), il repondait « pas de visage » — et la calibration accusait l'OUTIL au lieu de l'ENVIRONNEMENT. Un secours doit crier quand il ne peut pas fonctionner. |
| **Un seuil de mesure jamais calibre** | J'ai classe des cadrages avec « taille du visage < 0,09 = plan en pied », un seuil **invente**. Calibration a posteriori : un buste mesure 0,448, un plan en pied 0,207 — l'instrument ne separe rien. Toute conclusion tiree d'un seuil doit d'abord montrer que le seuil separe des cas connus. |
| **Deux instruments non calibres qui s'accordent** | Pixtral disait « buste » sur des images en pied ; ma mesure disait pareil. J'ai lu leur accord comme une corroboration et classe le desaccord restant en « bruit ». Ils se trompaient **ensemble**. Un accord ne vaut que si au moins un des deux a ete verifie contre la realite. |
| **Un chemin relatif apres un rangement de fichiers** | `prep_train.py` pointait vers `HERE/dataset` ; les scripts ont ete deplaces dans `scripts/`, le dataset est reste a la racine. Il ne trouvait plus rien **sans rien dire** — un `continue` silencieux dans une boucle. Tout script qui peut finir avec 0 element doit le DIRE bruyamment. |
| **Un caractere non-ASCII dans un message** | Un `⚠` dans un `print()` fait planter le script sur une console Windows cp1252. Le banc qui lisait sa sortie a conclu a un echec d'entrainement **qui n'avait jamais eu lieu**. Forcer `sys.stdout` en UTF-8, ou rester en ASCII. |
| **Un poids de modele non versionne ET non scriptable** | Le detecteur YOLO avait ete telecharge dans un scratchpad, jamais range. A la session suivante il avait disparu, emportant la reproductibilite de la phase 3 alors que ses chiffres etaient soigneusement consignes. Un binaire n'a pas sa place dans le depot, mais **la commande qui le rapporte, si** : `scripts/fetch_models.py`. |
| **Bulles japonaises reprises telles quelles** | Le japonais s'ecrit **verticalement** : ses boites sont en portrait. Les reutiliser pour du francais donne un mot par ligne. Dimensionner la bulle **par son texte**, jamais par la boite detectee. |
| **Un garde-fou cale sur une fenetre arbitraire** | Decider « est-ce une bulle ? » selon que l'aplat touche les bords d'une fenetre qu'on a soi-meme choisie se declenche **a l'envers sur le cas normal** (texte au centre d'une grande bulle : la fenetre est entierement dedans). Le bon critere etait la **surface atteinte** par la diffusion. |
| **Mesurer au mauvais endroit** | Verifier l'effacement du japonais dans la page **exportee**, la ou l'on vient de poser le francais : le noir augmente, et la mesure conclut a l'inverse de la verite. Mesurer sur la **case nettoyee**, avant lettrage. Une mesure mal placee donne l'assurance sans le controle. |
| **Cadres qui se chevauchent** | YOLO detecte parfois une grande zone contenant des petites. En une seule passe de dessin, les cases suivantes **recouvrent les bulles** des precedentes (3/6 perdues, invisibles dans tous les autres controles). Dessiner **toutes les images d'abord**, tous les calques de texte ensuite. |
| **Nom de fichier d'un encodeur CLIP** | `IPAdapterUnifiedLoader` cherche l'encodeur d'image **par motif** dans `models/clip_vision/`. Depose sous son nom d'origine HuggingFace (`model.safetensors`), un fichier parfaitement valide de 2,5 Go n'est **jamais trouve**. Renommer `CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors`. |
| **FaceID sans son LoRA compagnon** | `ip-adapter-faceid-plusv2_sdxl.bin` **exige** `ip-adapter-faceid-plusv2_sdxl_lora.safetensors` — deux fichiers, deux dossiers differents. L'un sans l'autre : rendu qui part en vrille, **sans message d'erreur**. |
| **Tuer ComfyUI au lieu de le redemarrer** | Ici ComfyUI est lance **par le proxy Generate Studio** (parente verifiee). Le tuer dans le dos de son parent, c'est se priver du garde-fou « ne pas couper une generation en cours » que le proxy applique deja. Passer par `POST /shutdown` puis `POST /start` (Bearer `.studio_secret`), avec `dryRun` d'abord. |
| **Un element pose APRES le `<script>`** | Le bloc du plein ecran avait ete ajoute juste avant `</body>`, donc **apres** le script qui lui accroche ses handlers : `$("lbClose")` valait `null`, l'exception tuait **tout le reste du script**, et la galerie restait vide **sans aucun message**. Un seul element mal place eteint une page entiere. |
| **Une version declaree a TROIS endroits** | `<title>`, le badge HTML, **et `const VERSION` en JS** -- et c'est la troisieme qui **ecrase les deux autres** au chargement. Bumper le HTML sans elle ne change RIEN a l'ecran : le depot disait v1.10.0 pendant que Quang lisait **v1.7.0**, trois versions durant. Relire le fichier ne pouvait pas le voir, il fallait regarder la PAGE. ⇒ `python scripts/check_version.py` avant toute livraison (exit 1 si divergence, et il verifie aussi le badge REELLEMENT affiche). |
| **Un `id` en double** | `id="gal"` servait a la fois a la galerie et a l'onglet Valide : `$("gal")` ne voyait que le premier, et l'autre ne se mettait jamais a jour. Ce qui se repete est une **classe**, jamais un id. |
| **Un `overflow-x:auto` qui cache un debordement** | La barre d'onglets faisait 418 px pour 360 disponibles. La page ne debordait pas (le controle automatique disait OK) mais les derniers onglets etaient **inatteignables** sur telephone. Un conteneur qui scrolle en douce est un defaut, pas une parade. |
| **Un banc qui depend d'un effet de bord** | Le banc du clavier comptait sur « creer un projet le rend courant ». Ca a marche une fois, puis des projets **homonymes** se sont accumules et `select_option(label=…)` tombait sur un projet vide : le banc concluait « aucune case » en accusant l'app. Un banc dresse son decor **explicitement**, et nomme ses objets de facon unique. |
| **Un banc qui remplit un DOM invisible** | Appeler `refreshGal()` sans activer l'onglet remplissait un `<section>` masque : rien n'etait cliquable, et le banc testait des donnees en croyant tester une interface. **Cliquer l'onglet**, comme l'utilisateur. |
| **Ids générés à la milliseconde** | `prefix + hex(now_ms)` donne le **même id** à deux insertions dans la même ms — et créer 6 cases d'un coup est une rafale. `_studio_db._uid()` ajoute un compteur monotone. Attrapé par le self-test, pas en production. |

---

## 6. Journal

| Date | Événement |
|---|---|
| 2026-07-27 | **v1.19.0 — un bug d'ORDRE trouve dans la generation reelle de Quang.** Sa case affichait un prompt bien traduit, mais l'image avait ete produite avec la phrase FRANCAISE : `positive` etait calcule **avant** que la traduction automatique ne s'execute, donc celle-ci ne prenait effet qu'a la generation SUIVANTE. Le pire des cas -- ca marche « une fois sur deux » sans que rien ne l'explique, et seul le prompt ENREGISTRE dans la recette le revelait. Corrige : le prompt final se calcule apres la traduction. Dans la foulee, le comptage des personnages apprend a compter des **sujets distincts** : « le maitre frappe la fille » ne contient aucun chiffre et vaut pourtant deux personnages -- il sortait encore `solo, 1girl`. Banc : 6/6 sur les cas reels, et sa phrase produit desormais `2people` sans `solo`. |
| 2026-07-27 | **Phase 11 — le MOUVEMENT par poses cles, teste le jour meme de l'idee.** Aucun modele video installe (dossiers VIDES) et ceux-ci rendent du couleur photorealiste ⇒ on fait comme les dessinateurs : meme seed, meme prompt, **seule la pose change** via des squelettes openpose interpoles. Mesure sur 6 images : coherence entre voisines **0,895** en moyenne, ecart premiere/derniere **0,845** — le personnage tient ET ca bouge. **Defaut trouve a l'oeil que le chiffre ne voyait pas** : les 2 premieres images sortaient DE DOS, les suivantes de face — un squelette openpose est en 2D et ne dit pas l'orientation. Corrige au prompt. Verdict honnete : c'est une **sequence de cases**, pas un GIF fluide — 6 poses ne font pas une animation, et les details redessines a chaque image fourmillent. |
| 2026-07-27 | **v1.18.0 — bouton « 3 suites », la premiere brique du mode automatique.** Idee de Quang, retenue parce qu'elle est la MOINS risquee : texte vers texte, zero GPU, et elle attaque le point dur du chantier -- la continuite -- la ou il se joue vraiment, dans le **recit** et non dans l'image. Le contexte, ce sont les **4-5 cases precedentes** (leurs actions ET leurs dialogues), pas la derniere : une suite ne se deduit pas d'une image isolee. Trois directions volontairement differentes (logique / intense / inattendue) ; un clic remplit la case. Mesure sur une sequence reelle (couloir, visage inquiet, porte qui s'ouvre) : 3 propositions coherentes et distinctes, reprise en un clic. Elle est aussi la plus facile a valider -- Quang lit trois phrases et en choisit une. |
| 2026-07-27 | **v1.17.0 — traduction auto, style de projet, comptage des personnages.** Option « ameliorer automatiquement avant de generer » : elle ne traduit que si besoin (retraduire une traduction la degrade) et ne BLOQUE jamais la generation. **Style du projet en texte LIBRE** plutot qu'une liste de genres — une liste plafonnerait le « n'importe quel sujet » et figerait ce qui doit varier. Et le correctif qui comptait : « il n'y a qu'un seul personnage » venait de `solo` (herite de l'identite du projet, il l'emporte sur tout le reste) et du fait que **le modele compte avec des TAGS, pas avec des mots**. Mesure : meme avec la consigne explicite, le LLM rend « solo, martial arts master » ⇒ le nombre est desormais **derive du texte** (4/4 sur les cas reels), `solo` retire, tag de comptage impose. Piege d'enchainement attrape en testant : le compte se lit sur le texte **d'origine**, la traduction perdant regulierement le nombre (« deux maitres » ressort au singulier). |
| 2026-07-27 | **Faisabilite d'un manga entier : repondu par ecrit (phase 10).** Par nombre de personnages — 1 solide, 2 mesure, 3 degrade, **4-5 pas fiablement et je ne le promets pas** (la voie realiste y est le montage, pas la generation). Sur la fabrication d'un personnage : le **visage** decide de l'identite et IPAdapter le veut GRAND (52 % de l'image au banc ; une reference en pied echoue — essai 3), tandis que **vetements et corpulence** ne passent pas par l'image mais par les **tags**. ⇒ fiche MIXTE, ce que `manga_chars` stocke deja. Non promis : une corpulence identique d'une case a l'autre. |
| 2026-07-27 | **v1.14.0 — la BASE DE PERSONNAGES, et le casting par planche** (demande Quang : « je ne comprends pas a quel moment je peux selectionner les personnages […] c'est plus un controle qu'un aleatoire »). Table `manga_chars` (schema v4), **globale** et non rattachee a un projet : une fiche se cree une fois et sert partout, avec son role (heros LoRA / secondaire IPAdapter / figurant texte) qui decide du **niveau de coherence**. Le CASTING appartient a la **planche** ; une case en herite et peut le surcharger ; **rien de coche = generation libre** — la base est un moyen de controle, jamais un prealable. Le LoRA d'un heros du casting prime sur celui de la recette. Mesure bout en bout : 2 fiches creees, 2 cochees, tags des DEUX injectes dans la case. |
| 2026-07-27 | **v1.13.0 — pourquoi les essais de Quang ne donnaient pas ce qu'il demandait.** « 2 maitres en arts martiaux » et « une femme assise sur la table » ont rendu **la meme lyceenne en uniforme**. Le prompt reel disait `zqmg1rl, 1girl, solo, sailor uniform, red scarf, <sa phrase>` : (1) la recette PAR DEFAUT portait le personnage de test du LoRA, injecte dans **chaque case de chaque projet** ; (2) le negatif contenait `multiple girls`, donc **deux personnages etaient impossibles par construction** ; (3) le moteur ne lit que des tags booru **anglais** — une phrase francaise est ignoree, pas traduite ; (4) rien ne permettait de dire « cette case, c'est autre chose ». Corriges : defaut neutre, negatif nettoye, bouton **✨ Ameliorer** (route `/enhance`), personnage decochable par case. Verifie a l'oeil sur SA demande : un karateka en garde au lieu de la lyceenne. Et sur son 2e essai (explicite) : traduit fidelement, image produite, saturation 0,081 (N&B tenu). Deux pieges attrapes en corrigeant : sans LoRA le noeud restait avec un nom **vide** (ComfyUI refusait tout le graphe, HTTP 400), et ce refus s'affichait **« [object Object] »** — ComfyUI renvoie ses erreurs en objet imbrique, que la concatenation ecrasait. |
| 2026-07-27 | **v1.10.1 — la version affichee etait FAUSSE depuis trois versions.** Signale par Quang (« tu oublies de versionner le bandeau du haut »), et il avait raison. Cause invisible dans le fichier : la version existe a **trois** endroits et `const VERSION` **ecrase** le titre et le badge au chargement. Je bumpais les deux premiers, jamais le troisieme : le depot disait v1.10.0, l'ecran disait **v1.7.0**. ⇒ `scripts/check_version.py` verifie les trois declarations **et le badge reellement affiche par le navigateur** -- la seule valeur que Quang voit. Falsifiable : l'oubli exact que j'avais commis fait sortir exit 1. |
| 2026-07-27 | **⛔ CORRECTION, le jour meme : mon diagnostic sur la scene femdom etait FAUX.** J'avais conclu « le rapport de force ne s'ecrit pas, il faut openpose » et j'avais deja construit les squelettes a deux corps. Mesure : **le texte seul donne 3/3 et la scene est exactement la bonne** (femme debout, homme a genoux tete levee) ; le **ControlNet openpose DEGRADE** (2/3 et rendu mauvais -- le modele lit un squelette agenouille comme un **homme debout de petite taille**). La vraie cause, isolee par un banc a une seule variable sur 8 seeds : **`low angle shot from below`**, qui fait passer la presence du second personnage de **6/8 a 3/8**. ⇒ La regle est l'INVERSE de ce que j'avais ecrit : la mise en scene s'ecrit, c'est le **cadrage** qu'il ne faut pas melanger au meme prompt. **Lecon : j'ai tire une regle generale d'un echec dont je n'avais pas isole la variable, puis bati un outil pour la contourner. Le banc qui tranchait coutait dix minutes.** |
| 2026-07-27 | **v1.8.0 — la galerie SERT enfin a quelque chose** (« je ne peux rien faire dessus ») : plein ecran (taille MESUREE, pas supposee), selection multiple, suppression qui NOMME les fichiers, et une route proxy a trois verrous (anti-traversee verifiee en direct). Trois defauts trouves en chemin, tous invisibles autrement : `id="gal"` **en double**, le bloc du plein ecran pose **apres** le `<script>` (une erreur qui eteignait TOUT le script, galerie vide sans message), et une barre d'onglets qui **debordait en douce** (418 px pour 360) donc des onglets inatteignables sur telephone. responsive-audit OK a 320/360/384. |
| 2026-07-27 | **v1.7.1 — le clavier du telephone ne se referme plus.** Bug remonte par Quang : impossible d'ecrire dans une case. Cause lue dans le code : un clavier virtuel qui s'ouvre **redimensionne la fenetre**, le `resize` rappelait `renderPlate()` qui reconstruit tout en `innerHTML` -- le champ focalise etait **detruit**. Un redimensionnement ne touche plus qu'aux colonnes. Banc falsifiable (`--muter` -> ROUGE, verifie). |
| 2026-07-27 | **DEUX personnages dans une case — mesure, et le trou est partiellement comble.** Co-presence et contact simple : ca marche. **Le rapport de force (femdom) ECHOUE** : decrit en texte, le modele produit la femme debout et **oublie l'homme a genoux**. ⇒ ce qui casse n'est pas l'anatomie mais la **mise en scene**, et la parade est deja outillee (`make_pose.py`, deux squelettes openpose). Limite d'instrument declaree : le compteur de visages **sous-compte en cadrage serre**. |
| 2026-07-27 | **Phase 9 ouverte — photo/capture -> manga** (demande Quang). Trois usages distincts derriere une meme phrase (convertir la case · servir de reference de style · servir de decor reutilisable), **et les trois briques sont deja installees** : canny/lineart telecharge le 26/07, IPAdapter valide le 27/07, carte de profondeur acquise en phase 2. Ce n'est pas de la recherche, c'est du branchement. Deux reserves posees : un contour de photo est **bruite** (un manga jette 90 % du detail -> ControlNet modere + denoise eleve, pas un filtre), et les **visages reels restent hors perimetre**. Sur la couleur : trois modes, et la **couleur partielle se SUPERPOSE** au lieu de se demander au modele -- meme arbitrage que pour le texte. |
| 2026-07-27 | **IPAdapter MESURE — il marche, mais a un reglage que rien n'annoncait.** Par defaut il est inutilisable : le preset `PLUS FACE`, dont le nom invite pourtant a le choisir, **detruit le rendu** (noir 0,112 contre 0,599 au temoin), et a poids 0,8 la planche **vire au bleu**. Le reglage utile est **PLUS / poids 0,4 / end_at 0,5 / reference convertie en N&B** : identite 0,839 sur 3/3, et **saturation 0,149 — la planche la plus proprement monochrome des trois bras**, devant le LoRA (0,333). ⇒ **le verrou de la phase 7 est leve** : un sujet ponctuel n'a plus besoin d'un LoRA. ⚠️ Mais **l'instrument a echoue a l'epreuve difficile** (il ne distingue pas un changement d'yeux et de morphologie) : les chiffres se comparent entre bras, **aucun ne prouve « c'est bien lui »** — le juge reste l'oeil de Quang. Quatre pieges payes : insightface **inutilisable sur du dessin** (5/12 meme sur visage recadre), une reference **choisie au hasard** pendant que le commentaire pretendait le contraire, une **mesure aveugle au defaut** (noirceur au lieu de saturation : du bleu sombre est sombre), et la couleur qui venait **de la reference elle-meme** — IPAdapter transfere la palette, le negatif textuel ne pese rien contre une image. |
| 2026-07-27 | **IPAdapter INSTALLE** — le blocage annonce depuis le 26/07 est leve. 774 -> **811 noeuds**, 5,7 Go de poids (encodeur ViT-H, PLUS, PLUS FACE, FaceID v2 + son LoRA), tous rapportables par `fetch_models.py --dest`. ComfyUI redemarre **par le chemin du proxy** (`/shutdown` + `/start`, dry-run `busy:false` d'abord), pas en tuant un process. Deux pieges payes : le **nom** de l'encodeur CLIP (cherche par motif, invisible sous son nom d'origine) et **FaceID inutilisable sans son LoRA compagnon**. ⏳ **Rien n'est encore mesure** : une installation n'est pas un resultat. |
| 2026-07-27 | **Trois demandes de Quang inscrites dans la feuille de route.** (1) **Volet adulte explicite** : la matrice ne disait que « pornographie » — desormais 4 sous-genres nommes (explicite · **fetichisme** · **femdom/domination** · suggestif), avec ce que chacun met a l'epreuve. Consequence relevee : **tout ce qui a ete mesure l'a ete sur UN personnage seul** — « deux personnages dans une case » est un **trou de mesure**, pas un acquis. (2) **Phase 8, bibliotheque de references** : une image sert a trois choses distinctes (style / apparence / **composition**), a ne surtout pas melanger ; **la bibliotheque est un accelerateur, jamais un prerequis** — rien de charge = generation de A a Z. (3) **Muse a deja resolu la moitie du probleme** (taxonomie, routage LoRA, negatif casting, filet d'interdits **en code**) : on reutilise, on ne recopie pas — et le catalogue explicite **reste chez Muse**, hors synchro. |
| 2026-07-26 | Ouverture du chantier. Décision d'archi (app séparée). Checkpoint Illustrious installé. Essais 1-4 mesurés. Recherche web + vote 3 voix. kohya installé (3 pièges payés : cu128, versions transformers, encodage cp1252). |
| 2026-07-26 | **Phase 1 franchie à 89 %** (contre 50 % sans LoRA). LoRA `zqmg1rl_v1` entraîné et validé sur comparatif strict. 2 réserves ouvertes → LoRA v2 avant la phase 4. |
| 2026-07-26 | **Phase 3 : pipeline d'ingestion écrit et mesuré** (`manga_ingest.py`). Découpage 83 % à IoU 0,66 mais **Pixtral quantifie sur une grille** ⇒ raffinement OpenCV nécessaire. Volet style : OK. **Bloqué sur la validation** faute de scans réels de Quang. Premier test = faux positif, corrigé par un test à vérité terrain. |
| 2026-07-27 | **Directive Quang : la qualite de l'ENSEMBLE prime, les micro-details ne comptent pas.** Le grain de beaute est **retire du design** ⇒ reserve n°1 de la phase 1 close par DECISION, et le comparatif recalcule sans cette ligne donne **15/15 = 100 %** (au lieu de 16/18) : **le critere de la phase 1 est atteint franchement avec le LoRA v1**. Mesure valide a seed identique : v1 et v2 donnent le **meme cadrage sur les 3 cases** ⇒ **chantier LoRA v2 CLOS, sans suite**. |
| 2026-07-27 | **Mesure de cadrage refaite sur une base valide** (`mesure_cadrage.py`) : plus de proxy, la DEFINITION — quelles articulations sont dans le champ (keypoints OpenPose), + un detecteur de visage la ou OpenPose est aveugle. Calibration passee AVANT usage : 7/9, avec **2 sous-estimations et 0 surestimation** ⇒ l'outil declare lui-meme qu'il ne peut donner qu'un **plancher**. Resultat : dataset v1 = **0** plan large sur 24, dataset v2 = **au moins 8** sur 28. **Le reequilibrage du v2 est reel, et c'est desormais etabli.** |
| 2026-07-27 | **⛔ CORRECTION : ma mesure de cadrage etait invalide.** Calibree apres coup sur des images dont j'avais verifie le cadrage a l'oeil, la « taille du visage » donne **0,448 pour un buste et 0,207 pour un plan en pied** — elle ne separe pas les classes, et le detecteur echoue sur 2 plans larges. Retires : la repartition des cadrages des datasets, « aucun vrai plan en pied n'est atteint », « le v2 cadre 11 % plus large ». **Lecon : j'ai pose un seuil que je n'avais jamais etabli, et un second juge non calibre disait la meme chose — leur accord m'a rendu confiant alors qu'ils se trompaient ensemble.** Ajoute `make_pose.py` (squelettes OpenPose synthetiques : la position du squelette EST le cadrage). |
| 2026-07-27 | **LoRA v2 entraine et mesure — critere NON atteint, et c'est le resultat utile.** Cadrage : 11 % plus large seulement, les deux restent des bustes malgre 7 prompts « full body » ⇒ **le modele de base resiste, ce n'est pas (que) le dataset** ; il faudra ControlNet openpose. Grain de beaute : toujours 0/3, et la mesure dit pourquoi — il n'est visible que sur **3/12** images du dataset v2 malgre `(mole:1.4)`. **On n'a jamais montre ce detail assez souvent pour savoir s'il est apprenable.** Le v1 reste le defaut. Trouve au passage : `train_lora.sh` pointait vers une session morte. |
| 2026-07-27 | **Boucle de validation livree** (v1.7.0) : onglet Valide, bibliotheque de recettes rejouables, ecriture du dataset du LoRA suivant, `prep_train.py` rendu generique. La propriete « l'app propose, elle n'impose rien » est **falsifiable** et verifiee rouge sous sabotage. Bug latent trouve : `prep_train.py` ne trouvait plus le dataset depuis le rangement des scripts — le LoRA v1 n'etait plus reentrainable, en silence. RESTE l'entrainement du v2 (GPU, ComfyUI a couper ~40 min). |
| 2026-07-27 | **Effacement du texte source** (v1.6.2). Les bulles d'origine sont VIDEES (diffusion bornee depuis un pixel clair, sans IA) et leur contour survit ⇒ on les REUTILISE au lieu d'en empiler de nouvelles. Mesure : noir dans la zone du japonais 0,070 -> **0,000**, 0 texte qui deborde. Deux erreurs de methode notees : un garde-fou qui se declenchait **a l'envers sur le cas normal**, et une mesure faite **au mauvais endroit** (dans l'export lettre au lieu de la case nettoyee) qui concluait a l'inverse de la verite. |
| 2026-07-27 | **Ingestion et relettrage dans l'app** (v1.5.0). Onglet Ingestion : page reelle -> YOLO -> Pixtral -> planche relettrable, exportee **a la geometrie de la page d'origine**. 5/5 cases, 6/6 bulles francaises, 6/6 **visibles dans le fichier exporte**, ~14 s. Quatre defauts corriges, dont trois invisibles autrement : bulles en portrait (le japonais est vertical), cases ecrasees a l'export, et **3 bulles sur 6 recouvertes** par des cadres qui se chevauchent. **Le modele YOLO avait DISPARU** (il vivait dans un scratchpad) : `fetch_models.py` le rapporte desormais — un chiffre mesure dont l'outil a disparu n'est plus un resultat, c'est un souvenir. |
| 2026-07-26 | **Phase 5 franchie — bulles et lettrage** (v1.2.0). Calque SVG unique (écran = export par construction), 5 formes, queue orientable, police Comic Neue embarquée, export PNG **et** PDF écrit à la main. Trois défauts trouvés par la mesure, dont **le voile de génération qui recouvrait chaque case depuis la v1.0.1** — invisible dans les chiffres, évident à l'écran ⇒ le banc prend désormais une **capture**. Reste : le relettrage d'une page traduite, qui attend un écran d'**ingestion** dans l'app. |
| 2026-07-26 | **Phase 4 franchie — l'app existe.** `manga_studio.html` v1.0.1 (single-file, servie par le proxy sur `/manga`), tables SQLite dédiées `manga_projects/pages/panels` (schéma v3), routes `/manga/*`. Planche de 6 cases de bout en bout : 6/6, 0 erreur JS sur PC **et** Samsung réel, 12/12 responsive. **Exigence Quang du jour : les sorties ne se mélangent plus à celles de Generate Studio** (851→851 fichiers à la racine, 0 résidu) ; 62 fichiers d'exploration rapatriés. Un défaut invisible à l'œil trouvé par le banc : créer un projet ne le sélectionnait pas → cases rangées chez un voisin. Arbitrage Quang : l'app **avant** le LoRA v2, stockage en **table dédiée**. |
| 2026-07-26 | **Phase 2 franchie, 6/6.** Fond maître + ControlNet depth @ 0,55. Témoin sans ControlNet = 0/4 ⇒ répéter le décor dans le prompt est inopérant. Découverte structurante : décor figé et identité fine sont **incompatibles dans une même case** ⇒ règle des deux types de cases. Prochaine étape : **phase 3, ingestion des scans**. |
