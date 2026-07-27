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

### Phase 7 — Un chapitre depuis un texte ⏳ *(la cible ; déclencheur : après le LoRA v2)*

Entrée : un **texte** (synopsis, script, découpage). Sortie : la suite des cases d'un chapitre, prêtes à
relire et à corriger. C'est le but de l'outil, rappelé par Quang le 27/07.

Ce que les phases précédentes ont déjà posé, et qui n'est donc pas à refaire :
- **l'identité** du personnage tient (LoRA, 89 % — phase 1) ;
- **le décor** tient sur une séquence (fond maître + ControlNet 0,55, 6/6 — phase 2) ;
- **la règle des deux types de cases** dit déjà quand utiliser l'un ou l'autre ;
- **la recette complète** de chaque case est enregistrée, donc une planche est rejouable ;
- **le lettrage** sait poser les répliques, et la **boucle de validation** sait recycler ce qui marche.

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
| **Ids générés à la milliseconde** | `prefix + hex(now_ms)` donne le **même id** à deux insertions dans la même ms — et créer 6 cases d'un coup est une rafale. `_studio_db._uid()` ajoute un compteur monotone. Attrapé par le self-test, pas en production. |

---

## 6. Journal

| Date | Événement |
|---|---|
| 2026-07-26 | Ouverture du chantier. Décision d'archi (app séparée). Checkpoint Illustrious installé. Essais 1-4 mesurés. Recherche web + vote 3 voix. kohya installé (3 pièges payés : cu128, versions transformers, encodage cp1252). |
| 2026-07-26 | **Phase 1 franchie à 89 %** (contre 50 % sans LoRA). LoRA `zqmg1rl_v1` entraîné et validé sur comparatif strict. 2 réserves ouvertes → LoRA v2 avant la phase 4. |
| 2026-07-26 | **Phase 3 : pipeline d'ingestion écrit et mesuré** (`manga_ingest.py`). Découpage 83 % à IoU 0,66 mais **Pixtral quantifie sur une grille** ⇒ raffinement OpenCV nécessaire. Volet style : OK. **Bloqué sur la validation** faute de scans réels de Quang. Premier test = faux positif, corrigé par un test à vérité terrain. |
| 2026-07-27 | **Mesure de cadrage refaite sur une base valide** (`mesure_cadrage.py`) : plus de proxy, la DEFINITION — quelles articulations sont dans le champ (keypoints OpenPose), + un detecteur de visage la ou OpenPose est aveugle. Calibration passee AVANT usage : 7/9, avec **2 sous-estimations et 0 surestimation** ⇒ l'outil declare lui-meme qu'il ne peut donner qu'un **plancher**. Resultat : dataset v1 = **0** plan large sur 24, dataset v2 = **au moins 8** sur 28. **Le reequilibrage du v2 est reel, et c'est desormais etabli.** |
| 2026-07-27 | **⛔ CORRECTION : ma mesure de cadrage etait invalide.** Calibree apres coup sur des images dont j'avais verifie le cadrage a l'oeil, la « taille du visage » donne **0,448 pour un buste et 0,207 pour un plan en pied** — elle ne separe pas les classes, et le detecteur echoue sur 2 plans larges. Retires : la repartition des cadrages des datasets, « aucun vrai plan en pied n'est atteint », « le v2 cadre 11 % plus large ». **Lecon : j'ai pose un seuil que je n'avais jamais etabli, et un second juge non calibre disait la meme chose — leur accord m'a rendu confiant alors qu'ils se trompaient ensemble.** Ajoute `make_pose.py` (squelettes OpenPose synthetiques : la position du squelette EST le cadrage). |
| 2026-07-27 | **LoRA v2 entraine et mesure — critere NON atteint, et c'est le resultat utile.** Cadrage : 11 % plus large seulement, les deux restent des bustes malgre 7 prompts « full body » ⇒ **le modele de base resiste, ce n'est pas (que) le dataset** ; il faudra ControlNet openpose. Grain de beaute : toujours 0/3, et la mesure dit pourquoi — il n'est visible que sur **3/12** images du dataset v2 malgre `(mole:1.4)`. **On n'a jamais montre ce detail assez souvent pour savoir s'il est apprenable.** Le v1 reste le defaut. Trouve au passage : `train_lora.sh` pointait vers une session morte. |
| 2026-07-27 | **Boucle de validation livree** (v1.7.0) : onglet Valide, bibliotheque de recettes rejouables, ecriture du dataset du LoRA suivant, `prep_train.py` rendu generique. La propriete « l'app propose, elle n'impose rien » est **falsifiable** et verifiee rouge sous sabotage. Bug latent trouve : `prep_train.py` ne trouvait plus le dataset depuis le rangement des scripts — le LoRA v1 n'etait plus reentrainable, en silence. RESTE l'entrainement du v2 (GPU, ComfyUI a couper ~40 min). |
| 2026-07-27 | **Effacement du texte source** (v1.6.2). Les bulles d'origine sont VIDEES (diffusion bornee depuis un pixel clair, sans IA) et leur contour survit ⇒ on les REUTILISE au lieu d'en empiler de nouvelles. Mesure : noir dans la zone du japonais 0,070 -> **0,000**, 0 texte qui deborde. Deux erreurs de methode notees : un garde-fou qui se declenchait **a l'envers sur le cas normal**, et une mesure faite **au mauvais endroit** (dans l'export lettre au lieu de la case nettoyee) qui concluait a l'inverse de la verite. |
| 2026-07-27 | **Ingestion et relettrage dans l'app** (v1.5.0). Onglet Ingestion : page reelle -> YOLO -> Pixtral -> planche relettrable, exportee **a la geometrie de la page d'origine**. 5/5 cases, 6/6 bulles francaises, 6/6 **visibles dans le fichier exporte**, ~14 s. Quatre defauts corriges, dont trois invisibles autrement : bulles en portrait (le japonais est vertical), cases ecrasees a l'export, et **3 bulles sur 6 recouvertes** par des cadres qui se chevauchent. **Le modele YOLO avait DISPARU** (il vivait dans un scratchpad) : `fetch_models.py` le rapporte desormais — un chiffre mesure dont l'outil a disparu n'est plus un resultat, c'est un souvenir. |
| 2026-07-26 | **Phase 5 franchie — bulles et lettrage** (v1.2.0). Calque SVG unique (écran = export par construction), 5 formes, queue orientable, police Comic Neue embarquée, export PNG **et** PDF écrit à la main. Trois défauts trouvés par la mesure, dont **le voile de génération qui recouvrait chaque case depuis la v1.0.1** — invisible dans les chiffres, évident à l'écran ⇒ le banc prend désormais une **capture**. Reste : le relettrage d'une page traduite, qui attend un écran d'**ingestion** dans l'app. |
| 2026-07-26 | **Phase 4 franchie — l'app existe.** `manga_studio.html` v1.0.1 (single-file, servie par le proxy sur `/manga`), tables SQLite dédiées `manga_projects/pages/panels` (schéma v3), routes `/manga/*`. Planche de 6 cases de bout en bout : 6/6, 0 erreur JS sur PC **et** Samsung réel, 12/12 responsive. **Exigence Quang du jour : les sorties ne se mélangent plus à celles de Generate Studio** (851→851 fichiers à la racine, 0 résidu) ; 62 fichiers d'exploration rapatriés. Un défaut invisible à l'œil trouvé par le banc : créer un projet ne le sélectionnait pas → cases rangées chez un voisin. Arbitrage Quang : l'app **avant** le LoRA v2, stockage en **table dédiée**. |
| 2026-07-26 | **Phase 2 franchie, 6/6.** Fond maître + ControlNet depth @ 0,55. Témoin sans ControlNet = 0/4 ⇒ répéter le décor dans le prompt est inopérant. Découverte structurante : décor figé et identité fine sont **incompatibles dans une même case** ⇒ règle des deux types de cases. Prochaine étape : **phase 3, ingestion des scans**. |
