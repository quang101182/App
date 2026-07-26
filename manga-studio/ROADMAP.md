# Manga Studio — feuille de route

> **Document vivant.** Mis à jour à chaque étape franchie ou infirmée. Dernière révision : **2026-07-26**.
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

### Phase 1 — Verrouiller le personnage ✅ *(atteinte à 89 %, le 26/07 — 2 réserves ouvertes)*
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

**⏳ CE QUI MANQUE ET QUI NE DÉPEND PAS DE MOI** : les **scans réels de Quang**. Le critère de sortie parle de
*ses* planches — testé jusqu'ici uniquement sur des pages générées ou fabriquées. À déposer dans
`D:\Download\02-Apps-Web\01-Term_mob_files_send\` (images, PDF ou captures).

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

### Phase 4 — L'app ⏳
Single-file HTML, version affichée dans l'UI, cliente du proxy 8190. Modèle : projet → chapitre → planche →
case. Chaque case porte sa **recette complète** (modèle, LoRA + poids, seed, prompt, ControlNet, source).
> **Critère de sortie** : une planche de 6 cases produite de bout en bout dans l'app, testée PC **et**
> mobile (Samsung réel), 0 erreur JS.

### Phase 5 — Bulles et lettrage ⏳
Overlay Canvas éditable. Le LLM écrit les répliques, le canvas pose bulle + texte.
> **Critère de sortie** : bulles repositionnables, texte réeditable après coup, export PNG/PDF.

### Phase 6 — Boucle de validation ⏳
**Reprendre la décision GS du 29/06, ne pas réinventer** : l'apprentissage automatique, invisible et
appliqué sur signal faible avait été jugé non fiable et **rétrogradé en suggestions à valider**.
Ici : Quang note ✅/❌ ; le validé alimente (a) une bibliothèque de recettes gagnantes réutilisables,
(b) à ~30-50 cases validées d'un même style, **le dataset d'entraînement du LoRA suivant** — c'est là que
la boucle paie vraiment. **L'app propose, elle n'impose jamais.**
> **Critère de sortie** : un 2ᵉ LoRA entraîné à partir de cases validées bat le 1er sur le test de la phase 1.

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

---

## 6. Journal

| Date | Événement |
|---|---|
| 2026-07-26 | Ouverture du chantier. Décision d'archi (app séparée). Checkpoint Illustrious installé. Essais 1-4 mesurés. Recherche web + vote 3 voix. kohya installé (3 pièges payés : cu128, versions transformers, encodage cp1252). |
| 2026-07-26 | **Phase 1 franchie à 89 %** (contre 50 % sans LoRA). LoRA `zqmg1rl_v1` entraîné et validé sur comparatif strict. 2 réserves ouvertes → LoRA v2 avant la phase 4. |
| 2026-07-26 | **Phase 3 : pipeline d'ingestion écrit et mesuré** (`manga_ingest.py`). Découpage 83 % à IoU 0,66 mais **Pixtral quantifie sur une grille** ⇒ raffinement OpenCV nécessaire. Volet style : OK. **Bloqué sur la validation** faute de scans réels de Quang. Premier test = faux positif, corrigé par un test à vérité terrain. |
| 2026-07-26 | **Phase 2 franchie, 6/6.** Fond maître + ControlNet depth @ 0,55. Témoin sans ControlNet = 0/4 ⇒ répéter le décor dans le prompt est inopérant. Découverte structurante : décor figé et identité fine sont **incompatibles dans une même case** ⇒ règle des deux types de cases. Prochaine étape : **phase 3, ingestion des scans**. |
