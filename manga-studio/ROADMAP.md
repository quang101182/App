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
(ligne 1570) ⇒ une app tierce consomme tout le moteur ~~**sans modifier une ligne de proxy**~~.

> ⚠️ **CE CONSTAT EST PÉRIMÉ DEPUIS LA PHASE 4 ELLE-MÊME** (relevé le 28/07). Le manga a bien des
> routes **à lui** dans le proxy — `/manga/projects|pages|panels|chars|files|ingest|dataset|harvest`,
> et `/manga/crop_ref` depuis le 28/07. La promesse initiale était « pas de modification » ; la
> réalité est « des routes ajoutées, aucune route existante touchée » — ce qui est une autre
> propriété, tout aussi bonne, mais qu'il faut dire.
> 🔴 **Conséquence à connaître** : `C:\Users\quang\Documents\ComfyUI\_studio_llm_proxy.py` **n'est
> pas dans ce dépôt**. Une réinstallation de ComfyUI perdrait ces routes, et l'app tomberait sans
> que rien ne l'annonce. *(Chantier ouvert : versionner un patch ou une liste des routes ajoutées.)*

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
> 2. ~~**Deux personnages dans une même case** — trou de mesure signalé par le volet adulte.~~
>    → ✅ **mesuré et livré le 28/07 (v1.52.0)**, voir ci-dessous.
> 3. Le transfert de **style** d'une page de Quang (brique de la phase 8).

#### ✅ DEUX identités dans une même case — mesuré le 28/07 (`scripts/test_deux_refs.py`)

C'était le trou de mesure n°2, et il expliquait une gêne concrète de Quang : *« Jo n'apparaît pas
vraiment »*. La cause n'était pas que Jo manquait d'ancre — c'est que **l'ancre de l'autre le recouvrait**.

Quatre bras, même seed, même prompt à deux personnages, 6 seeds chacun. L'instrument est celui du
27/07 (YOLO face + CLIP-ViT-H), rejoué sur ses étalons : il sépare A de B avec une marge de 0,145,
donc il a le droit de juger **cet** écart-là — et rien de plus fin.

| Bras | Deux identités distinctes | Chacune à sa place | Saturation |
|---|---|---|---|
| prompt seul (témoin) | 2/6 | 1/6 | 0,185 |
| **une seule référence** *(= l'app jusqu'à la v1.51.0)* | **1/6** | 1/6 | 0,181 |
| deux références **sans masque** | **0/3** | 0/3 | 0,215 |
| deux références **masquées, poids 0,4** | 5/6 | 5/6 | 0,134 |
| **deux références masquées, poids 0,6** ⭐ | **6/6** | **6/6** | **0,105** |
| deux références masquées, poids 0,8 | 4/6 | 4/6 | 0,208 *(la couleur revient)* |

**Trois choses que ces chiffres établissent, et qu'on ne pouvait pas deviner :**
1. **Une seule référence est PIRE que rien pour le second personnage** (1/6 contre 2/6 au témoin) :
   elle ne se contente pas de ne pas le tenir, elle lui **impose le visage de l'autre**. Le
   commentaire du code redoutait le mélange en empilant deux références — le mélange était déjà là,
   avec une seule.
2. **Empiler deux références sans masque est le pire bras de tous** (0/3). La crainte écrite dans le
   code était donc juste — mais elle visait la mauvaise parade : ce n'est pas « deux » qui est
   mauvais, c'est « deux, partout ».
3. **Le poids n'est pas le même qu'à une référence.** 0,4 est le réglage plein cadre mesuré le 27/07 ;
   borné à une moitié, il faut 0,6. À 0,8 on repasse le seuil où IPAdapter réinjecte la palette.

**Et le prompt n'a rien à dire du placement** : rejoué avec une scène qui ne précise **pas** qui est
à gauche, le bras masqué tient toujours **6/6**. C'est le masque qui place, pas le texte — donc
l'app n'ajoute rien à ce que Quang écrit.

**⚠ Ce que ça ne dit pas** : l'instrument distingue une brune à frange d'une blonde en blouse, il a
échoué (27/07) à voir un changement d'yeux. Ces 6/6 signifient « deux personnages **nettement**
différents restent chacun à leur place », pas « l'identité fine de chacun est tenue ». Pour deux
personnages proches, aucune mesure ne le couvre.

**🟠 Vérifié sur les VRAIES fiches de Quang (Jo + Kimiko, 28/07) — et ça découvre le verrou suivant.**
Le duo fonctionne, mais deux choses le sabotaient en amont, dans cet ordre :
1. **Les tags des fiches.** Telles quelles (`character design`, `simple background`, `monochrome`,
   `lineart`), la case sort en **planche de personnage** — vues multiples sur fond vide — et Jo
   n'apparaît pas du tout. Avec des copies aux tags nettoyés, **Jo apparaît vraiment**, à côté de
   Kimiko, dans un décor. ⇒ Le bouton **🧹 Nettoyer** (v1.51.0) n'est pas un confort : sans lui, le
   verrou d'identité travaille contre une mise en page imposée par le texte.
2. **La nature de l'image de référence elle-même.** Celles de Jo et Kimiko sont des **planches de
   design** (plusieurs vues sur fond vide). IPAdapter PLUS transfère la **composition** autant que
   l'identité : la case hérite donc d'un grand visage flottant et d'échelles incohérentes, même après
   nettoyage des tags. ⏳ **Chantier suivant, et il est net** : une référence doit être **recadrée sur
   le visage/buste** avant d'être utilisée — YOLO face sait déjà le faire (`test_ipadapter` s'en sert
   pour choisir sa référence), l'app ne le fait pas encore. *Mesuré à l'œil sur deux générations
   réelles, images conservées dans `scripts/duo_refs_out/`.*

**Un défaut de banc payé au passage, et il avait de quoi tromper** : les deux références étaient
uploadées sous **le même nom** dans `ComfyUI/input` (le fichier N&B intermédiaire s'appelait toujours
`_ref_nb.png`, avec `overwrite`). Deux bras rendaient donc des chiffres **identiques au millième**
sur des images identiques — un tableau parfaitement rempli, qui ne mesurait qu'une seule identité.
Corrigé à la racine (`test_ipadapter.upload` dérive le nom de sa source) et le banc **refuse
désormais de démarrer** si ses deux entrées portent le même nom.

### Phase 10 — Créer un manga entier : les questions de faisabilité *(Quang, 27/07)*

> « Si tu devais créer un petit manga de 10 ou 20 pages, sur trois ou quatre thèmes, avec un, deux,
> trois, quatre, voire cinq personnages — est-ce que tu y arrives ? Comment génères-tu ces
> personnages ? […] faut-il afficher seulement leur visage ou leur corps entier, leurs vêtements,
> leur style vestimentaire ? […] et même leur corpulence. Reste critique sur la faisabilité. »

**Réponse par nombre de personnages — c'est LA variable qui décide.**

| Personnages par case | Faisable aujourd'hui ? |
|---|---|
| **1** | ✅ **Oui, solide.** Identité tenue (LoRA 100 %, IPAdapter validé), décor tenu, lettrage. |
| **2** | ✅ **Oui, mesuré** (`test_duo.py` : co-présence et contact simple passent). ~~⚠ Mais tenir **DEUX identités précises** dans la même case n'est PAS mesuré~~ → ✅ **mesuré le 28/07** : deux références **masquées gauche/droite** à poids 0,6 tiennent **6/6** ; une seule référence n'y arrive que **1/6** et contamine le second. Livré en v1.52.0. Réserve : mesuré sur deux personnages **nettement** distincts. |
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
> Quang juge lisible comme un mouvement.
> ~~⏳ Reste à brancher dans l'app (aujourd'hui : script seul).~~
> → **✅ PÉRIMÉ, vérifié dans le code le 28/07** : c'est le bouton **🎬 Séquence** (v1.21.0), qui
> impose les mêmes squelettes openpose à 0,9, plus **▶ Jouer** (v1.22.0), la **case-groupe**
> (v1.41.0) et le **réordonnancement** (v1.42.0). Le branchement a été fait le jour même, sous un
> autre nom, et ce constat n'a jamais été revisité.
> **Il ne reste donc que le verdict de Quang** : est-ce que ça se lit comme un mouvement ?

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

#### ✅ Recadrer la référence sur le visage — mesuré et livré le 28/07 (v1.53.0)

Le verrou nommé plus haut. Une référence qui est une **planche de personnage** ne transmet pas
seulement un visage : elle transmet sa **mise en page**. Parade : recadrer sur le visage avant de
la donner à IPAdapter (`scripts/crop_ref.py`, YOLO face + carré centré sur le visage, ~3,2 largeurs
de visage pour garder cheveux et épaules).

**Mesuré sur les deux vraies références de Quang** (`test_crop_ref.py`, 6 seeds, mêmes images,
même graphe duo masqué). La mesure principale n'est **pas** l'identité mais le **nombre de
personnages** : on en demande deux, une planche de design en produit trois ou quatre.

| Bras | Exactement 2 personnages | Chacun à sa place | Saturation |
|---|---|---|---|
| références **brutes** | **4/6** — une case à 1 personnage, une à 3 | 4/6 | 0,069 |
| références **recadrées** ⭐ | **6/6** | 3/6 | 0,104 |

Recadrage : Kimiko passe d'un visage à **1,9 %** de l'image à **10 %** ; Jo de 26,9 % à 39,3 %.
À l'œil l'écart est franc : sur un des essais bruts, la case avait littéralement hérité d'une
**mise en page à cases**. Les six essais recadrés montrent deux personnages côte à côte.

**⚠ Ce que ça n'améliore PAS, et il faut le dire** : le **placement** par identité (chacun de son
côté) ne progresse pas — 4/6 contre 3/6, dans le bruit à n=6. Le recadrage règle la **composition**,
pas l'attribution. Et l'instrument est ici plus faible qu'au banc précédent (un seul étalon par
personnage, deux designs manga N&B moins écartés) : ces colonnes-là se lisent avec prudence.

**Dans l'app (v1.53.0)** : le recadrage est appliqué aux **deux** chemins d'entrée d'une référence
— import « ＋ image de référence » et « 🎨 Dessiner → garder ». Aucun visage détecté ⇒ l'image est
**gardée entière** et l'app le dit : une référence peut légitimement être un décor ou un objet, et
couper au hasard serait pire. Route `POST /manga/crop_ref` (sous-processus venv kohya), banc
`test_crop_ref_app.py` — 10 vérifications, mutation rouge.

**Un défaut attrapé par le banc** : mon « carré » sortait en **369×370** — chaque coin était tronqué
séparément. Un cadre carré doit l'être par construction, pas par chance.

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

### Phase 12 — Monter une séquence, et affiner une case ⏳ *(demandes Quang du 27/07 au soir)*

Six demandes arrivées coup sur coup pendant l'essai du bouton 🎬, plus un avertissement qui les
domine toutes : *« on empile beaucoup de choses au fur et à mesure, et on peut vite perdre
l'ergonomie de l'application »*. Il a raison, et c'est mesurable — voir le budget en fin de section.
Chaque demande est traitée ici avec un **avis tranché**, pas seulement enregistrée.

#### 12.0 — ✅ Le budget de boutons *(livré v1.31.0)* — **11 → 6**

**Compté dans le code, pas à l'œil** (`panelHTML`, v1.28.0) : une case **générée** affiche
**11 boutons** — ✨ Améliorer · 💡 3 suites · 🎬 Séquence · ▶ Jouer · Générer · ✎ Lettrage · ⬚ Zone ·
↻ la zone · ✅ · ❌ · suppr. — plus deux zones de texte, un choix de type, un champ seed et une case
à cocher. En mode lettrage, **5 de plus**. Et les demandes ci-dessous en ajoutent au moins **4**
(◀ ▶ de navigation, réordonner ×2, analyser).

⇒ **Rien de neuf ne doit s'ajouter à cette rangée.** La suite se construit avec une règle : la case
montre **ce qu'on fait maintenant** (écrire, générer, juger) ; tout ce qui **affine** (zone, analyse,
séquence, réordonner) passe dans **un seul bouton « ⚙ Affiner »** qui déplie un panneau *dans* la
case — le même geste que 💡 3 suites, déjà connu de l'utilisateur. C'est ce qui rend les 4 demandes
suivantes tenables sans usine à gaz : **elles ne coûtent aucun bouton de plus.**

✅ **Livré v1.31.0. Mesuré : 6 boutons visibles** (Générer · ✎ Lettrage · ▶ Jouer · ✅ · ❌ · ⚙).
La suppression est descendue dans le panneau — irréversible, elle n'a rien à faire à côté des
boutons qu'on touche à chaque case. **Piège désamorcé au passage** : `genPanel` lisait le champ
seed sans garde ; ce champ vivant désormais dans un panneau **repliable**, générer au panneau fermé
aurait jeté une `TypeError`. Une rangée simplifiée qui casse la génération serait un très mauvais
marché — le banc le vérifie explicitement (`test_affiner_et_badge.py`, 14 ✓, mutation rouge).

#### 12.1 — ✅ Regrouper les vignettes d'une séquence *(livré v1.41.0)*

Demande : *« je les imagine plutôt regroupées ensemble sur la même fenêtre, avec un bouton pouvant
les faire défiler […] suivant/précédent avec l'affichage du numéro d'image »*.

✅ **D'accord, et c'est le bon diagnostic** : une séquence de 6 vignettes est **un moment**, pas six
moments. Aujourd'hui elle occupe 6 cases dans le fil de la planche et noie tout le reste.

⚠️ **Le piège à ne pas commettre — et il est sérieux** : ne **jamais** fusionner les données. Une
vignette **est** une case de manga : elle doit rester dans la planche exportée en PNG/PDF, sinon le
regroupement détruit le livrable.

✅ **Livré v1.41.0, et le piège a été vérifié AVANT d'écrire une ligne** : `buildPlateCanvas` lit
`S.panels`, **jamais le DOM** — regrouper l'affichage ne touche donc ni au PNG ni au PDF. C'est
exactement ce que la mutation du banc casse : elle fusionne pour de bon, l'écran reste identique,
et **5 cases disparaissent en silence de l'export**.

Le groupe montre une vignette, **◀ n/N ▶** (ça boucle — un bouton qui ne répond pas au bout passe
pour cassé), et **« déplier les 6 »** pour les revoir côte à côte. L'index se recale seul si une
suppression a raccourci la série. Le tout s'appuie sur `sequence.gid`, posé en v1.31.0 : il servait
au badge et au lecteur, il porte maintenant la case-groupe.

Banc : `test_case_groupe.py` — 12 ✓, mutation rouge à 7 échecs.

> **Effet de bord assumé** : `test_affiner_et_badge` parlait de 6 vignettes affichées séparément ;
> il **déplie** désormais le groupe, parce que c'est l'état dans lequel ses questions (badge,
> panneau ⚙, seed case par case) ont un sens. Ce n'est pas un contournement pour rester vert — sa
> mutation rougit toujours.

#### 12.2 — ✅ Réordonner les vignettes *(livré v1.42.0)*

Demande : *« changer l'ordre des images […] mais au niveau ergonomie, de quelle manière ? »*

✅ **Livré, et la réponse à « de quelle manière » a tenu : surtout pas du glisser-déposer.** Au
doigt, un drag entre en conflit avec le défilement de la page — la source de bug d'ergonomie la plus
classique, et ce projet a déjà payé le clavier qui se refermait. Deux boutons **⇤ ⇥** dans la barre
du groupe échangent la vignette avec sa voisine : un tap, un résultat visible, annulable en tapant
l'autre. Ils se **désactivent aux extrémités** plutôt que de ne rien faire.

⚠️ **Correction de ce qui était écrit ici** : « le `sequence.index` est réécrit, rien d'autre ne
bouge » était **faux**. Il faut échanger **deux** ordres — `sequence.index` (le badge, le lecteur)
**et `idx`**, la position dans la planche, que la base trie et que `buildPlateCanvas` suit.
N'échanger que le premier aurait fait dire à l'écran **l'inverse du PNG**. Le banc vérifie
explicitement que l'ordre de la *planche* suit, pas seulement celui de la séquence.

Banc : `test_case_groupe.py` étendu à 16 ✓, mutation rouge à 11 échecs.

> **Trois défauts du banc, corrigés en route, tous de la même famille** — *un banc qui touche à une
> UI mouvante doit savoir échouer, pas mourir* : une boucle de repositionnement **non bornée** (sous
> mutation, « 1/6 » n'arrive jamais et il tournait jusqu'au timeout) ; l'interrogation de boutons
> **sans vérifier qu'ils existent** ; une comparaison sur `avant_ordre[1]` **sans vérifier qu'il y a
> deux éléments**.

#### 12.3 — Page par page plutôt qu'ascenseur 🟡 *(après 12.1)*

Demande : *« passer en affichage rapide, soit en ascenseur, soit page suivante/précédente,
gauche-droite […] on voit plus facilement chronologiquement ce qui se passe »*.

🤔 **D'accord sur le fond, mais je le mets APRÈS 12.1, et voici pourquoi** : le vrai problème
aujourd'hui, c'est la **longueur** de la planche, et c'est la séquence qui la fabrique. Le
regroupement (12.1) fait passer une planche de 12 cases à 4 blocs — il se peut que le besoin de
défilement horizontal **disparaisse de lui-même**. Construire les deux en même temps, c'est risquer
de payer un mode d'affichage entier pour un problème déjà résolu par l'autre. À réévaluer **après**
12.1, sur une vraie planche.

Si le besoin persiste : un basculeur **global et persistant** (même mécanique que la vitesse de
défilement, v1.28.0) « défilement vertical / page par page », jamais un réglage par projet.

#### 12.4 — Supprimer une vignette d'une séquence : ce que fait le code aujourd'hui

Question de Quang : *« qu'est-ce qui se passe si je décide de supprimer une des images de la
séquence ? Est-ce que ça fonctionne toujours ? »* — **Réponse lue dans le code** (`jouerSequence`,
`act === "del"`), pas supposée :

- La lecture **continue** : elle rassemble les cases qui ont la **même seed** et un fichier, triées
  par leur index. Une case supprimée est simplement absente ; les autres gardent leur ordre.
- En dessous de **2 vignettes**, elle refuse proprement : *« séquence incomplète »*. Pas de plantage.
- ✅ **Le badge menteur : corrigé v1.31.0.** Il était **figé à la création** — supprimer une vignette
  laissait 5 images afficher « /6 » avec des numéros qui sautent. Un numéro d'ordre se **déduit** de
  l'ordre, il ne se stocke pas.

  **Et le banc a trouvé deux défauts de plus en le corrigeant** — c'est le meilleur exemple de
  session sur « un banc sert à découvrir, pas à confirmer » :
  1. **Régénérer une vignette lui donnait une seed aléatoire** (au panneau ⚙ fermé), ce qui cassait
     la continuité du personnage *et* la détachait de sa série. **Dans une séquence, la seed n'est
     pas un réglage : elle est constitutive.** Hors séquence, « Regénérer » veut dire « un autre
     essai » — on tire. Les deux cas sont maintenant distingués.
  2. **L'appartenance à une séquence se déduisait de la seed.** Forcer une autre seed sur une
     vignette pour la retenter la faisait sortir du groupe (badge « 1/1 »). **Une appartenance ne se
     déduit pas d'un réglage : elle se nomme.** D'où `sequence.gid`, posé à la création, avec repli
     sur la seed pour les séries existantes. Le lecteur ▶ utilise le **même** critère — deux
     définitions du mot « séquence » finiraient par diverger. *(Cet identifiant est aussi la
     fondation dont 12.1 avait besoin : une case-groupe doit savoir qui elle groupe.)*

#### 12.5 — ✅ Corriger une zone en DISANT ce qu'on veut *(livré v1.35.0)*

Demande : *« corriger une image sans expliquer en quoi consiste la correction, ou avec le bouton de
zone on cible une zone et on explique ce qu'on veut corriger »*.

État réel (v1.26.1) : ⬚ Zone + ↻ la zone existent et sont mesurés (taille préservée, 0 pixel modifié
hors zone), mais l'inpaint **rejoue le prompt de la case entière**. On ne peut donc pas dire
« ici, une cicatrice » — on ne peut que **retenter la même chose**.

✅ **Livré — et avec UN bouton, pas deux.** En l'écrivant, le second est apparu inutile : « ↻ la
zone » tire déjà une seed neuve à chaque essai. Un champ **facultatif** suffit donc à couvrir les
deux demandes — vide, il retente la même chose autrement ; rempli, il dit quoi dessiner là. *Un
geste, deux usages*, plutôt qu'un bouton de plus à comprendre (règle 12.0).

**Le point qui compte** : la consigne **remplace l'action, mais le style et l'identité restent**.
C'est ce qui sépare « répare ça » de « dessine n'importe quoi là » — envoyer la seule consigne ferait
perdre à la zone le rendu N&B et le personnage, et la réparation se verrait comme une pièce
rapportée. On rejoue donc `promptFinal` sur une copie de la case dont **seule l'action** change : le
reste (comptage des personnages compris) est déjà traité là et ne se dédouble pas.

La consigne est **traduite** comme partout ailleurs (le moteur ne lit que l'anglais : une consigne
française n'y est pas mal comprise, elle est **ignorée**), traduite **une seule fois**, et **gardée
sur la case** — une retouche se refait souvent.

🐛 **Défaut plus ancien, trouvé en lisant la base — pas en le supposant** : la table `manga_panels`
a des colonnes **fixes** (`id, page_id, idx, kind, prompt, recipe, file, verdict, bubbles`). Tout
champ posé **hors de `recipe`** est accepté par l'API puis **jeté à l'écriture**, sans la moindre
erreur. **`p.zone` était dans ce cas depuis la v1.26.1** : le rectangle tracé disparaissait au
rechargement de la page. Zone et consigne vivent désormais dans `recipe`, et sont restaurées au
chargement. *(Règle à retenir pour tout nouveau champ de case : dans `recipe`, ou il n'existera
pas demain.)*

Banc : `test_zone_consigne.py` — 14 ✓, zéro GPU (le graphe envoyé au moteur est intercepté),
mutation rouge. Il a aussi corrigé **deux de ses propres mesures** : il mettait la réponse
`{ok, id}` dans `S.proj` (le piège du §3, donc l'app tournait *sans recette*), et il cherchait
« screentone » pour prouver que le style survit — alors que ce mot est déjà dans le style **par
défaut**. Un vert sans valeur.

#### 12.6 — ✅ « Qu'est-ce qui cloche ? » *(livré v1.43.0)*

Demande : *« un bouton qui analyse et améliore, avec potentiellement un score et la possibilité de
relancer une génération »*.

🤔 **Oui, mais avec une réserve nette, et elle vient d'une mesure de ce projet** : Generate Studio
note le **prompt** (`ImageScorer`), pas l'image — c'est écrit noir sur blanc dans le bilan du Mode
Série. Un score de prompt sur une case déjà dessinée ne dit **rien** de ce qu'on voit : il notera
« bien écrit » une case aux mains ratées. Le porter tel quel serait un **chiffre décoratif**, et un
chiffre décoratif fait plus de mal que pas de chiffre — on lui fait confiance.

⇒ Ce qui a du sens ici, c'est la **critique vision** : `/critique` envoie l'image à **Pixtral**, qui
la **regarde** (lu dans `_studio_llm_proxy.py`, pas supposé) et renvoie `{score, issues (français),
prompt corrigé}`.

✅ **Livré — et la réserve sur le score se précise au lieu de disparaître.** Ce score-là porte bien
sur l'image, donc il n'est pas décoratif ; mais il mesure la **conformité à la demande** (sujet,
compte, attributs, action), **pas la qualité du dessin**. Une case peut être conforme à 95 % et
avoir six doigts. C'est écrit **à l'écran, mot pour mot, à côté du chiffre** — *un chiffre dont on
ignore ce qu'il mesure est pire qu'un chiffre absent*. Pour un défaut de dessin, l'écran renvoie
vers ⬚ Zone.

Le prompt soumis au juge est celui **réellement utilisé** (`recipe.positive`), pas celui qu'on
recalculerait aujourd'hui : la recette a pu changer, et on jugerait l'image contre une demande qui
n'est pas la sienne.

⚠️ **La correction ne passe pas par le champ de la case.** Le juge renvoie le positif **complet**
corrigé, pas une action — l'écrire dans le champ (comme le fait 💡 3 suites) ferait **doublonner le
style et l'identité** à la génération suivante, puisque `promptFinal` les rajoute par-dessus.
`genPanel` accepte donc un positif **imposé**. C'est ce que la mutation casse, et le doublon se
mesure.

Banc : `test_critique.py` — 11 ✓, réponse du juge figée, mutation rouge à 3 échecs.

#### 12.7 — ✅ « On ne génère pas de bulle de texte ? » *(livré v1.40.0)*

**Deux choses différentes se cachent dans cette question, et une seule manque.**

1. **Poser une bulle et écrire dedans : ça existe** (phase 5, v1.2.0). Bouton **✎ Lettrage** sur une
   case → ＋ Bulle / ＋ Pensée / ＋ Récitatif, on la déplace au doigt, on tape la réplique, la queue
   se règle. Le rendu est un **calque SVG par-dessus l'image**, jamais du texte dessiné par le
   modèle — décision d'architecture, et elle est bonne : un modèle d'image écrit du charabia, et un
   texte qu'on ne peut pas corriger n'est pas du lettrage. *(Si ce n'était pas trouvable, c'est le
   même problème d'ergonomie que 12.0 : le bouton est noyé dans une rangée de 11.)*
2. **Ce qui manque vraiment : l'app n'ÉCRIT jamais la réplique.** Le texte vient toujours de Quang.
   Or l'app sait déjà lire les dialogues des cases précédentes — 💡 3 suites s'en sert pour proposer
   la suite du récit.

✅ **Proposition : « 💬 Répliques »**, le pendant exact de 💡 3 suites, appliqué au dialogue. Sur une
case dessinée, il propose **2-3 répliques** tenant compte des cases précédentes et de qui est dans
la case (le casting est connu) ; un tap en pose une dans une bulle, qui reste **entièrement
modifiable**. Texte vers texte, **zéro GPU**, et la brique est déjà écrite à 80 % (contexte de
`3 suites` + `addBubble`). C'est, avec 12.5, le meilleur rapport gain/effort de la liste.

⚠️ **Réserve tenue** : une réplique proposée n'écrit **jamais** dans une bulle existante — elle
**ajoute**. Un texte écrit à la main qui disparaît, c'est la perte qu'on ne pardonne pas à un outil
de création. Le banc pose une bulle « ECRIT A LA MAIN » **avant** de demander des répliques et exige
qu'elle soit encore là après ; c'est précisément ce que la mutation casse.

**Livré v1.40.0.** Le contexte envoyé au modèle : les cases précédentes **avec leurs dialogues**,
l'action de la case à écrire, et **qui est présent** — le casting sait ce que le prompt ne dit pas
toujours (« un vieux maître balaie la cour » ne nomme personne). Consigne : **moins de 12 mots**,
parce qu'une bulle de manga ne tient pas un paragraphe. Deux répliques posées ne se superposent pas,
et on bascule en lettrage dans la foulée — après avoir posé un texte, on veut le **placer**.
Le bouton vit dans ⚙ Affiner : la rangée reste à 6.

Banc : `test_repliques.py` — 13 ✓, réponse du modèle **figée** (on teste la chaîne de l'app, pas
l'inspiration d'un modèle un jour donné), mutation rouge à 3 échecs.

#### 12.8 — ✅ Ouvrir un projet existant *(livré v1.29.0, le jour même)*

Quang : *« je ne vois aucun moyen de charger un projet déjà en cours ou déjà créé »*. **Vérifié dans
le code : ce n'était pas un malentendu.** L'onglet **Projets** — le seul endroit où l'on va pour
reprendre un travail — ne proposait que *supprimer* ; ouvrir n'était possible que par une liste
déroulante en haut d'un **autre** onglet, qui changeait l'état **sans changer l'écran**.

Livré : bouton **Ouvrir** sur chaque projet (le projet courant se signale), qui charge ses planches
**et amène sur la planche**. Et la galerie dit enfin quel projet elle montre, avec un sélecteur pour
en regarder un autre **sans déplacer l'atelier** — *consulter n'est pas ouvrir*, vérifié dans les
deux sens (`test_ouvrir_projet.py`, 11 vérifications, mutation rouge).

> 📌 **La leçon, qui vaut pour tout le reste de cette phase** : la fonction existait, elle était
> même correcte. Ce qui manquait, c'est qu'elle soit **là où on la cherche**. Deux des questions de
> Quang ce soir (celle-ci et 12.7) ne sont pas des demandes de fonctions — ce sont des **rapports de
> panne d'ergonomie**. C'est exactement ce que 12.0 doit empêcher de se reproduire.

#### 12.9 — ✅ Bandeau moteur + VRAM *(livré v1.31.0, demande Quang du 27/07 au soir)*

Demande : *« le bandeau VRAM comme je l'ai demandé, même sur navigateur web PC. Il doit respecter la
largeur globale de l'application […] les mêmes comportements que Generate Studio […] rester affiché
en permanence tout en restant compact en hauteur, surtout sur smartphone »*.

Porté de Generate Studio (header v4.49, toggles ■/▶ v4.53, pulse de transition v4.54), **réduit à
ce que ce projet a réellement : un seul moteur**. État proxy + ComfyUI, bouton **▶/■** qui sait ce
qu'il doit faire, **pulse orange** du clic jusqu'à l'état cible (sécurité 90 s — un pulse qui ne
s'arrête jamais apprend à ne plus le regarder), **jauge VRAM live** aux seuils de Muse/GS
(vert ≥ 8 Go libres · orange 4-8 · rouge en dessous), grisée moteur éteint.

- **Source = `nvidia-smi` via `/vram`, PAS ComfyUI.** La VRAM doit rester lisible **moteur éteint** —
  c'est justement le moment où l'on veut savoir ce qu'il reste.
- **Largeur respectée** : bandeau, **onglets** et contenu sur la même colonne de 760 px. Trois
  alignements différents sur une même page se lisent comme trois applications.
- **Compact, mesuré** : **42 px** sur PC, **72 px** sur un téléphone de 360 px. Le texte est
  volontairement court (« 5,1 / 16 Go ») : en toutes lettres il repassait à la ligne et faisait
  grandir le bandeau d'un tiers — l'inverse exact de la consigne.
- Il se tient à jour seul (3 s pendant une transition, 15 s au repos) : *un état qu'il faut
  rafraîchir à la main n'est pas un état, c'est une photo*.

**Complété v1.33.0** — *« j'aimerais que ce soit le même nom […] un bouton Local qui permet
d'activer et de désactiver le moteur »* :

- La pastille s'appelle **« 🖥 Local »** et c'est **elle, en entier**, qui allume et coupe — plus un
  petit glyphe à viser. Deux apps du même atelier ne doivent ni s'appeler autrement ni se piloter
  autrement. **Vérifié en vrai** (moteur coupé puis rallumé par le bouton, pulse observé, VRAM
  grisée moteur éteint, moteur rendu dans l'état trouvé) — 9 vérifications.
- **Le témoin proxy disparaît** (décision qui m'était laissée) : affiché **seulement s'il tombe**.
  Un témoin vert 100 % du temps n'informe plus personne. 🐛 *Défaut attrapé à la capture, pas au
  raisonnement : `.eng` est en `display:flex`, qui l'emporte sur le `display:none` implicite de
  `hidden` — le témoin « proxy injoignable » restait donc affiché en permanence, **point vert à
  l'appui**.*

#### 12.10 — ✅ Onglets compacts et figés *(livré v1.33.0)*

Demandes : *« tu aurais dû figer les onglets […] surtout si je me retrouve tout en bas »* et
*« sur mobile, compacte les onglets, sinon ça s'affiche sur plusieurs lignes […] on consomme
beaucoup de lignes en hauteur pour rien »*.

- **Compacts** : sous 480 px, les libellés cèdent la place aux **icônes** (solution déjà validée sur
  Generate Studio v4.49) ; **l'onglet actif garde son mot** — sinon on sait où aller, mais plus où
  l'on est. Mesuré : **une seule ligne**, sans débordement, là où sept onglets en toutes lettres en
  prenaient deux (~44 px volés à la planche en permanence).
- ⚠️ **Ce qui n'a PAS été refait : `overflow-x:auto`.** Il rendrait la barre « propre » au contrôle
  automatique tout en cachant les derniers onglets derrière un défilement que personne ne devine —
  piège déjà payé sur ce projet.
- **Figés** : bandeau et onglets dans **un seul** conteneur collant. Deux éléments collés à `top:0`
  se chevauchent dès que la hauteur du premier change — et elle change (42 px sur PC, 66 px sur
  téléphone). Mesure en bas de page : onglets visibles des deux côtés.
- **Barre du haut complète : 108 px sur téléphone, 91 px sur PC.**

#### 12.12 — ✅ Dessiner un personnage depuis sa fiche *(livré v1.37.0)*

Quang, 27/07 : *« je ne vois toujours pas dans le personnage la création des images des personnages.
Ça fait un moment qu'on en parle et ça n'a toujours pas été fait. »* **Vérifié dans le code : il
avait raison.** L'app savait **importer** une référence (v1.25.0), pas en **fabriquer** une — or une
fiche neuve n'a aucune photo de départ, le personnage n'existe que dans les traits qu'on vient
d'écrire.

**🎨 Dessiner** produit **trois vues** (visage · buste · en pied) à la même seed ; on garde celle qui
ressemble, elle devient la référence IPAdapter de la fiche.

> **Trois vues, et c'est un choix, pas une hésitation.** `test_cadrage_reference.py` a comparé
> quatre cadrages le 27/07 et **n'a rien tranché** : les rendus se ressemblent trop pour départager
> à l'œil, et l'instrument automatique de ce projet a déjà échoué à juger une identité. Imposer un
> cadrage serait **inventer un verdict qui n'existe pas**. On propose ; la question se résout par
> l'usage, personnage par personnage. *(La planche `scripts/cadrage_out/planche_cadrages.png`
> reste disponible — elle montre bien que les quatre se valent.)*

**Ce qui n'entre PAS dans le prompt** : ni le LoRA, ni le déclencheur, ni l'identité du **projet**.
Ils dessineraient le héros du manga en cours à la place de la fiche — le défaut exact corrigé le
27/07, où chaque case héritait de la lycéenne de test. Et **rien n'est ajouté à la fiche tant qu'on
n'a pas choisi** : un brouillon qui s'installe tout seul est un choix fait à la place de l'utilisateur.

##### 🐛 Le défaut que ce chantier a révélé, et qui dépasse largement le bouton

Depuis la **v1.23.0**, la traduction est obligatoire *« sur tous les chemins »*. **La fiche de
personnage était le dernier à l'avoir oublié** : son champ disait *« tags anglais, ou écris en
français puis ✨ »*, donc la traduction dépendait d'un bouton qu'on pouvait ne pas voir. Le coût
n'est pas local — les tags d'une fiche partent dans **chaque case qui la caste** : une fiche restée
en français ne rate pas une image, **elle est invisible dans toutes**. Traduction désormais faite à
l'enregistrement, et les fiches déjà en base sont corrigées au premier dessin.

⚠️ **Et traduire n'est pas enrichir — confondre les deux s'est payé immédiatement.** Ma première
version réutilisait la consigne du bouton ✨ ; le modèle a **ajouté** des tags anglais en **gardant**
le français à côté (*« vieux maitre barbu, cicatrice sur la joue, kimono sombre, black and white,
manga style… »*). Le français partait donc quand même, **et** la fiche s'était alourdie de traits que
Quang n'avait pas écrits. *Une traduction automatique ne doit rien inventer* : on reprend la consigne
stricte déjà éprouvée pour les cases (`TRAD_CONSIGNE`). Mesuré après correction : *« old master with
beard, scar on cheek, dark kimono »*. L'enrichissement reste le rôle du bouton ✨ — un geste **voulu**.

Banc : `test_perso_dessiner.py` — 15 ✓, **génération réelle** (3 images, ~2 min : la question est
« est-ce que ça dessine vraiment *ce* personnage », et aucun stub n'y répond). Mutation rouge,
8 échecs.

#### 12.13 — ✅ Voir en grand, zoomer, et une liste qui tient *(livré v1.38.0)*

Quatre remarques de Quang, capture à l'appui, sur la v1.37.0 :

| Remarque | Réponse |
|---|---|
| *« c'est tout petit, je ne peux pas agrandir »* | toucher une vue l'ouvre **en grand**, avec « garder le buste » dans la barre — on choisit **en voyant**, pas d'après 110 px |
| *« zoomer, dézoomer »* | molette + double-clic (PC), **pincée** + double-tap (doigt), boutons − / 1:1 / + |
| *« suivant/précédent au lieu de fermer à chaque image »* | ◀ ▶ naviguent **sans fermer** ; chaque image repart à sa taille |
| *« à aucun moment il n'est indiqué que trois images seront générées »* | bouton **« 🎨 Dessiner 3 vues »**, annonce au lancement (« ~2 min ») et compteur pendant |
| *« la carte des personnages risque de devenir une liste abominable »* | **une fiche = une ligne**, dépliée au toucher, une seule à la fois, + filtre au-delà de 4 fiches |

**Le zoom est ancré sur le point visé** — avec l'origine au centre (le défaut CSS), zoomer *éloigne
du doigt* ce qu'on voulait regarder de plus près. Et **le pan est borné** : impossible de pousser
l'image hors du cadre et de se retrouver devant du noir. Ce sont **les deux défauts déjà identifiés
sur la visionneuse de planche** (§ RESTE) ; ils ne sont pas repayés ici.

🐛 **Trouvé par le banc, pas à l'œil** : ma formule mesurait le point visé depuis le coin du
**cadre**, en oubliant que l'image y est centrée (elle commence à `offsetLeft`). Le zoom dérapait
donc de cette marge — le détail visé s'échappait pendant qu'on zoomait dessus. Après correction :
coin attendu 51 px, obtenu **51 px**.

Banc : `test_visionneuse_et_liste.py` — 20 ✓, zéro GPU, il **mesure des rectangles** au lieu de
constater la présence d'un bouton. Mutation rouge (2 échecs).

> **Deux leçons du banc lui-même**, à ne pas réapprendre :
> 1. il servait une image SVG en base64 **écrite à la main** — invalide, donc mesurée à 0 px : il
>    accusait le zoom d'un défaut qui n'était pas le sien. *(Et `window.vueURL = …` ne remplace
>    **pas** une `const` de module — la résolution lexicale gagne, même piège que `$`.)*
> 2. sa tolérance d'ancrage était de 25 px, et **un zoom centré passait encore** (il dérape de
>    24 px). Un seuil confortable ne mesure plus rien — serré à 8 px.

#### 12.14 — ✅ La troupe d'un manga *(livré v1.39.0)*

Quang, 27/07 : *« c'est quoi la suite quand je crée des personnages, que je crée un nouveau projet,
comment j'ai inclus ces personnages dans le projet ? »* — la question a mis le doigt sur deux
manques réels : le casting appartenait à la **planche seule** (chaque planche neuve repartait vide),
et la ligne affichait **toute la base** en cases à cocher.

**Trois niveaux, une phrase chacun** :

| Niveau | Où | Ce que ça veut dire |
|---|---|---|
| **La base** | onglet Personnages | toutes mes fiches, réutilisables d'un manga à l'autre |
| **La troupe** | `proj.recipe.casting` | ceux qui jouent dans **ce** manga |
| **La planche** | `layout.casting` | ceux qui apparaissent sur **cette** page |

Une planche neuve **hérite** de la troupe. Nuance qui compte : casting **absent** = « je suis la
troupe » ; casting **vide** = « personne sur cette page ». Ce n'est pas la même chose, et le banc le
vérifie après rechargement. Ajouter quelqu'un à la troupe le fait jouer **aussi** sur la planche
ouverte (sinon le geste est à faire deux fois) ; l'en retirer le retire des deux.

Et la ligne remonte **sous le choix de la planche** — c'est une décision de début, elle n'avait rien
à faire sous « Exporter ».

🐛 **Une boîte native oubliée** : « Démarrer une planche » demandait encore le nom **et** le nombre de
cases par des `prompt()`. Mon commit v1.34.0 annonçait « plus aucune boîte native » — j'avais
vérifié les `confirm(`, **pas** les `prompt(`. L'annonce était donc fausse ; c'est corrigé.

> ⚠️ **La leçon la plus utile de ce chantier vient du banc, qui a échoué deux fois à rougir :**
> 1. `window.troupeProjet = …` ne remplace **pas** une `const` de module (la résolution lexicale
>    l'emporte) : le code muté n'était jamais appelé, et le banc restait vert **en ne prouvant
>    rien**. Les fonctions d'héritage sont désormais des **déclarations**, donc remplaçables.
> 2. Retirer `casting` à l'**écriture** ne cassait rien non plus : l'app hérite **aussi à la
>    lecture**. Bonne nouvelle sur le code — deux mécanismes indépendants — mais preuve qu'**une
>    mutation doit viser le comportement, pas une ligne**.

#### Ordre d'exécution *(chronologie tenue par Claude, mandat Quang du 27/07)*

| # | Chantier | État | Pourquoi ce rang |
|---|---|---|---|
| — | **12.8 ouvrir un projet** | ✅ v1.29.0 | blocage d'usage : il ne pouvait pas reprendre son travail |
| — | **12.0 ⚙ Affiner** | ✅ v1.31.0 | tout le reste s'y range ; le faire après = tout refaire |
| — | **12.4 badge menteur** | ✅ v1.31.0 | un bug, pas une fonction |
| — | **12.9 bandeau VRAM** | ✅ v1.31.0 → v1.33.0 | demande explicite, et il rend le moteur pilotable d'un doigt |
| — | **12.10 onglets compacts + figés** | ✅ v1.33.0 | 44 px rendus à la planche, et un onglet atteignable depuis le bas |
| — | **12.11 question d'arrêt** | ✅ v1.34.0 | + les 5 dernières boîtes natives de l'app |
| — | **12.5 zone + consigne** | ✅ v1.35.0 | un seul bouton ; a révélé que `p.zone` n'était pas persistée depuis la v1.26.1 |
| — | **12.12 dessiner un personnage** | ✅ v1.37.0 | demande ancienne et jamais faite ; a révélé que la fiche échappait à la traduction obligatoire |
| — | **12.14 la troupe du manga** | ✅ v1.39.0 | répond à « comment j'inclus mes personnages » ; a révélé un `prompt()` natif oublié |
| — | **12.13 visionneuse + liste** | ✅ v1.38.0 | zoom ancré, navigation, liste repliée — et le zoom de la planche a désormais une implémentation de référence |
| — | **12.7 💬 Répliques** | ✅ v1.40.0 | brique déjà écrite aux ¾ ; la réserve « ajoute, n'écrase pas » est tenue et mesurée |
| — | **12.1 case-groupe** | ✅ v1.41.0 | l'export lit `S.panels`, pas le DOM : le regroupement ne pouvait pas le casser |
| — | **12.2 réordonner** | ✅ v1.42.0 | ⇤ ⇥ plutôt qu'un drag ; échange `sequence.index` **et** `idx` |
| — | **12.6 critique vision** | ✅ v1.43.0 | le score dit ce qu'il mesure ; la correction ne passe pas par le champ |
| 6 | **12.3 page par page** | 🤔 | à réévaluer **après** 12.1 — peut-être sans objet |

#### 12.11 — ✅ La question de sécurité avant de couper le moteur *(livré v1.34.0)*

Demande : *« il manque la pop-up de sécurité quand je veux arrêter le moteur, comme sur Generate
Studio. Après, attends de voir si tu fais aussi la pop-up de démarrage, mais a minima celle
d'arrêt »*.

Generate Studio la pose avec un `confirm()` **natif** (lu dans son `shutdownEngines`). **Ici, non** :
une boîte native peut être refusée par le navigateur et renvoie alors « non » **sans rien
afficher** — l'action disparaît en silence et le bouton passe pour mort. C'est exactement ce qui a
coûté les v1.20.1 et v1.27.0. *Une question de sécurité qui peut ne pas s'afficher n'est pas une
sécurité.* La question est donc posée **à l'écran**, et le défaut de réponse est toujours **« on ne
fait rien »** (Échap et clic hors de la boîte valent non).

**Deux questions, qui ne disent pas la même chose** : la sécurité normale (« la carte est libérée,
plus une seule case dessinée avant 30-60 s de rechargement ») et celle que le **proxy** impose quand
un dessin est en cours — la seule où quelque chose se **perd**. La seconde s'ajoute à la première,
elle ne la remplace pas.

**Et rien au démarrage — c'est un choix, pas un oubli** (la question m'était laissée) : allumer ne
détruit rien. Une question posée sans enjeu apprend à répondre « oui » sans lire, et **affaiblit
celle qui compte**. Le délai de chargement est dit par le pulse et le journal, pas par une boîte à
fermer.

#### ✅ Constat de ménage fermé — plus une seule boîte native dans l'app *(v1.34.0)*

~~Deux `confirm()` natifs subsistent hors de la séquence : la suppression d'images en galerie et la
suppression d'un projet.~~ → **Il y en avait cinq**, comptés en les cherchant : galerie, projet,
planche, fiche de personnage, et retrait du personnage d'un projet — c'est-à-dire **toutes les
actions destructrices de l'app**, toutes suspendues à une boîte que le navigateur peut refuser.
**Les cinq passent par la question à l'écran** (`demander()`), et chacune dit désormais ce qu'elle
détruit *et* ce qu'elle préserve (« les images déjà dessinées restent sur le disque »).
**Vérifié : `grep confirm(` ne renvoie plus que des commentaires.**

---

## 4-ter. Lecture narrée — un chapitre raconté à voix haute *(21/09/2026, v1.66.0 → v1.67.0)*

**Nouvel usage, demandé par Quang le 21/09** : regarder et écouter un chapitre de manga raconté comme une vidéo
« manga recap » (pages qui défilent + voix off qui raconte), à usage personnel. Les pages viennent de
`manga-fetch/` (capture chapitre par chapitre dans la fenêtre Edge dédiée, MangaDex, import) → `sources/`.

⛔ **Assumé, ne pas rouvrir** : pas de recherche automatique multi-sites, pas de contournement de protections.
⛔ `sources/` (pages ET narrations dérivées) est **gitignoré** : le dépôt App est public.

### Chaîne (`scripts/narrate_chapter.py`, lancé par le proxy `POST /manga/narrate`)

| Étape | Outil | Pourquoi celui-là (mesuré) |
|---|---|---|
| Vision, par lots de 4 pages + résumé glissant | **Kimi K3** (défaut) ou Pixtral | Sonde page 4 de Claymore : Pixtral lit un cadavre entouré de villageois comme « une explosion, des enfants qui fuient » ; K3 lit juste. |
| Récit continu, page par page | DeepSeek V4 Flash | 0,003 $ par chapitre ; consigne « RACONTER, pas décrire l'écran ; paraphraser, jamais recopier une réplique » (reproche n°1 des forums aux recaps IA). |
| Voix | Google Chirp 3 HD fr-FR (`/api/gcptts`) | 8 voix testées OK, ~1 s par page. Kokoro écarté : < 11 h de français à l'entraînement. |
| Lecteur | `manga_studio.html` onglet 📚 Chapitres | Page plein écran + zoom lent + sous-titre + enchaînement auto, vitesse, clavier. |

### Banc du 21/09 — Claymore ch.1, pages 1-20

| | Kimi K3 | Pixtral |
|---|---|---|
| Coût | **0,363 $** (vision 0,24 · récit 0,003 · voix 0,12) | **0,077 $** (voix seule) |
| Génération | 5 min 53 | 1 min 43 |
| Audio produit | 3 min 53 | 2 min 27 |

⇒ un chapitre complet de 62 pages ≈ **1,1 $ et ~18 min** avec K3 ; ≈ 0,25 $ et ~5 min avec Pixtral.
Quatre narrations prêtes pour l'**écoute à l'aveugle** de Quang (même texte K3 en Charon / Kore / Fenrir,
+ Pixtral en Charon) : bouton 🎧 dans l'app, notes écrites dans `sources/<chap>/narration/notes.jsonl`.
~~**🟠 Verdict qualité EN ATTENTE de son écoute (constaté v1.67.0)**~~ → ✅ **couvert (re-vérifié v1.72.0)** : moteur tranché par Quang (**K3 v2.2 = défaut depuis v1.70.0**) ; écoute à l'aveugle faite le 21/09 (`notes.jsonl` : Fenrir 4, 4 · Charon sur texte Pixtral 4, 4 · Kore 2 · K3-Charon jamais noté). Voix par défaut restée **Charon** (ex æquo avec Fenrir, Kore écartée) — un changement serait à trancher par Quang.

### Constats du 21/09 (datés — à re-vérifier)

- 🟠 **« La page 2 est une page de crédits » est FAUX pour une capture officielle** (constaté v1.67.0) :
  sur MANGA Plus, les pages 2-3 de Claymore sont une double page couleur. La narration **reconnaît** les
  crédits (`type`), elle n'écarte jamais une page par sa position.
- 🟠 **Le gateway limite à 20 req/min par IP** (constaté v1.67.0) : la voix d'un chapitre (1 appel par page)
  prenait des 429. `narrate_chapter.py` plafonne à 18/min et respecte `retry_after`. *(re-vérifié v1.72.0 : `MAX_PAR_MIN = 18`)* Le frein est **par
  processus** : deux narrations en parallèle peuvent encore le dépasser (le 429 est alors absorbé, en plus lent).
- 🟠 **Le proxy ne connaît que les narrations qu'il a lancées** : après un redémarrage, un run vivant est
  reconnu par la fraîcheur de son `progress.json` (< 3 min), sinon il serait affiché « échec ». *(re-vérifié v1.72.0 : seuil 180 s dans le proxy)*

### Deux défauts de lecteur trouvés par le banc (corrigés v1.67.0)
1. Deux « suivant » rapides **arrêtaient la narration** : `play()` interrompu → `AbortError` pris pour un refus.
2. Après un changement de vitesse, le menu gardait le focus et **avalait espace / flèches**.

### Banc de FIDÉLITÉ du 21/09 (v1.68.0) — exigence Quang : « une erreur, même petite, c'est grave pour l'histoire »

**Outil** : `sources/claymore/ch_1/reference_faits.json` (faits des 20 pages, écrits À LA MAIN en lisant les pages ;
gitignoré car dérivé d'un contenu sous licence) + `scripts/juge_narration.py` (DeepSeek, texte seul, T=0 : compare
chaque page narrée à la référence → ok / mineur / grave + compteur mécanique de « style plat »). Validé : il retrouve
le verdict fait à la main (K3 v1 : 6 graves ; Pixtral : 13). Coût d'un jugement : 0,005 $.

| Version | Moteur | Graves / 20 | Coût 20 p. (sans voix) | Temps |
|---|---|---|---|---|
| v1 (lot de 4 + « reprends les noms connus ») | K3 | 6 | 0,24 $ | 6 min |
| v1 | Pixtral | 13 → **abandonné** | 0 $ | 2 min |
| v2 (faits + fiche prouvée + récit sans ajout, lots de 2) | K3 | 1 | 0,57 $ | **20 min** |
| v2 | Gemini 3.6 Flash | 2 puis 7 (**instable**) | 0,09 $ | 2 min |
| **v2.2 = défaut** (noms résolus à part par VOTE puis figés) | Gemini | **3 / 3 / 3** (3 runs) | 0,19 $ | ~5 min |
| v2.3 (+ vérification des attributions contre l'image) | Gemini | 2 / 4 / 3 | 0,30 $ | ~8 min → option `--verif`, off |
| v2.4 (+ PORTRAITS de référence découpés, étape 1 de la feuille de route) | Gemini | 3 / **5** / 2 | 0,23 $ | ~5 min → option `--portraits`, off |

| **v2.2 K3 = DÉFAUT depuis v1.70.0** (décision Quang : « généré une fois, autant que ce soit bien fait ») | K3 | **1 / 2 / 1** | 0,61-0,73 $ | 15-23 min |
| Magi v2 local (seul, banque Raki+Zaki) | — | **7/13** répliques pièges justes | 0 $ | 1,7 s/page, **VRAM 4,35 Go**, RAM 2,2 Go |

Rejugés à règles ÉGALES (juge v2, 21/09 18h40 : attribuer à « une voix » plutôt qu'au nommé = mineur ; un détail absent
de la référence n'est grave que s'il la CONTREDIT ; référence p19-20 complétée) : **Gemini 3/3/1 = 7, K3 1/2/1 = 4**.
Gemini commet l'erreur la plus trompeuse (réplique de figurant → Raki/Zaki, p4/p16/p18) ; **K3 jamais**. Reste chez K3 :
p8 « Zaki ! » (qui appelle — cas dur, 3/3 runs), une invention p2 (1 run), p19 (1 run).
Magi v2 : environnement jetable `%LOCALAPPDATA%\magi\venv` (C:, 4,8 Go) — **transformers 4.45.2 obligatoire** (la 5.x casse
le tokenizer) + `shapely matplotlib opencv-python-headless pycocotools sentencepiece` absents de toute doc. Tourne bien sur
la RTX 5070 Ti, mais confond aussi Raki et Zaki → non retenu comme juge des locuteurs ; utile plus tard pour le mode
Lecture (OCR + ordre de lecture des bulles intégrés).

⛔ **Étape 1 « personnages par exemples visuels » : ÉCHEC mesuré (21/09 18h), ne pas la rejouer telle quelle.**
Les portraits étaient JUSTES (vérifiés à l'œil : Raki p12, Zaki p6), mais dans Claymore **Raki et Zaki se ressemblent**
(mêmes cheveux clairs en épi, même trait) : deux exemples presque identiques ont RÉINTRODUIT la confusion Raki↔Zaki
(p17-18). Un exemple visuel aide quand les personnages diffèrent à l'œil ; ici ils ne diffèrent que par l'âge/la taille.
Pistes restantes, à arbitrer par Quang (coût/temps) : **K3 en v2.2** (K3 v2 = 0 confusion d'identité mais 20 min et
0,57 $ / 20 pages) ; **Magi v2 en local** (spécialisé dans l'attribution des répliques, GPU, licence « recherche ») ;
ou accepter ~3 pages / 20 où une réplique de figurant est prêtée à un nommé.

**Ce qu'on a appris (à ne pas repayer)** :
- 🔴 La consigne v1 « reprends les noms déjà connus, ne les change pas » **verrouillait une erreur précoce** : Raki
  (l'enfant) et Zaki (l'adolescent) fusionnés en « Zaki » sur 7 pages. Page isolée : « RAKI » lu 6/6.
- 🔴 Un nom écrit dans une bulle (« Zaki ! ») : le modèle hésite entre **celui qui parle et celui qu'on appelle**.
  Question ciblée, une page, 3 votes (Gemini) : 11/12 justes → la passe `etape_noms` fige ensuite
  « Raki = enfant, Zaki = adolescent » (stable sur 3 runs).
- 🟠 **Reste (constaté v1.68.0)** : 3 pages graves par run, toutes du même type — une réplique d'un anonyme brun
  (p4, p16, p18) attribuée à Raki/Zaki (blonds). Cause VISUELLE : le modèle rattache tout garçon qui parle à un
  nommé. La vérification texte+image ne tranche pas mieux (elle a même remplacé « Raki » par « Zaki » une fois).
- Le style « plat » (« un gros plan montre… ») venait d'une consigne de fidélité trop sèche → consigne récit v2.1 :
  dramatiser par le rythme et les mots, jamais par des ajouts. Mesuré : 0 tournure plate sur 3 runs.
- Recherche web (21/09) : MangaVQA place Gemini 2.5 Flash en tête des VLM généralistes sur le manga ; Magi v2
  (Oxford) résout précisément l'attribution des répliques par une banque de personnages à EXEMPLES visuels ;
  Chirp 3 HD a un bug connu sur les élisions françaises (« j'ai », « qu'il ») + prononciations personnalisables.

## 4-ter-bis. FEUILLE DE ROUTE — lecture narrée *(21/09, à reprendre dans cet ordre)*

> Principe tenu depuis le début : **fiabilité d'abord**, puis confort. Chaque étape a un critère mesurable.
> ⛔ Assumé, ne pas rouvrir : pas de recherche multi-sites ni de contournement de protections ; pas de redessin
> par IA des pages d'une série existante (personnages protégés + dérive d'identité mesurée en phases 1-2).

| # | Étape | Pourquoi | Critère de sortie |
|---|---|---|---|
> 📌 **Ordre fixé par Quang le 21/09 à 19h** : (a) finir l'étape 1-bis (consensus, en cours) ; (b) **étape 3 — capture
> DANS l'app** : « il faut absolument que tout ça soit intégré dans une application, et fonctionnel » ; (c) le reste
> dans l'ordre du tableau. « Ne te disperse pas. »
> 💾 **Règle de stockage (Quang, 21/09)** : **tout ce qui prend de la place va sur C:, jamais sur D:.** À faire au
> moment opportun (pas de chantier parallèle) : `sources/` (~40 Mo/chapitre, grossit) et `output/` déplacés sur C:
> avec une **jonction** à l'ancien chemin (zéro changement de code, manga-fetch/narration/proxy inchangés) ;
> `scripts/*_out` (~650 Mo de bancs de juillet, régénérables) : déplacer ou supprimer → **décision Quang**.
> ✅ **FAIT le 21/09 à 19h30** (Quang : « le plus tôt possible », « conserver son espace de stockage actuel ») :
> `sources/`, `output/` et les 13 `scripts/*_out` (**déplacés, pas supprimés**) vivent dans
> `C:\Users\quang\Documents\MangaStudio-donnees\` ; l'ancien chemin sous D: est une **jonction** (même nb de
> fichiers et d'octets vérifié avant chaque bascule ; routes `/manga/sources` et `/manga/costs` relues OK).
> ⚠️ Tout NOUVEAU dossier lourd (ex. un futur `scripts/xxx_out`) se crée d'abord sur C: puis se joint.
> ⚖️ Coût : les TESTS ne sont pas limités ; c'est la **solution finale** (coût + temps par chapitre) qui doit être sobre.
> 📌 **Ordre révisé par Quang le 21/09 à 22h54** : « faire d'abord le tour correctement des fonctions actuelles
> et des options actuelles » — **pas** de lecture case par case (étape 4), ni de mode Lecture / Lecture avancée
> (6), ni de nouvel effort « qui est qui », tant que le socle n'est pas complet. Ordre de travail :
> **(1)** bibliothèque par manga (12) + suppression pages/chapitres/séries (12-bis) ; **(2)** voix (8) ;
> **(3)** **vidéo MP4 au niveau PAGE** (5) — page entière + voix + sous-titres, SANS caméra case par case
> (qui viendra se greffer avec l'étape 4) — **à discuter avec Quang avant tout code** ; **(4)** « Précédemment… » (7),
> suivi de séries (9), hors-ligne (10). **Plus tard** : 4, 6, et la piste « oui/non/incertain » du verrou qui-est-qui.
> 📌 **Ordre précisé par Quang le 22/09 à 00h06-00h07** (le socle bibliothèque/voix/lecteur étant livré, v1.76 → v1.83) :
> **(1) Traduction des DIALOGUES d'un chapitre entier** dans la langue choisie (étape 11 b — oubliée de l'ordre du
> 21/09 22h54, rappelée par Quang) ; **(2) musique de fond DANS L'APP** (étape 13) : on/off, volume réglable à la
> main avec une valeur par défaut ; **(3) la vidéo** (étape 5, toujours À DISCUTER avant de coder) : musique on/off
> et sous-titres on/off choisis À LA GÉNÉRATION.
> **(2-bis) Sous-titres KARAOKÉ** (Quang 22/09 00h08 : « on l'a déjà fait avec d'autres applications ») : le mot
> prononcé s'allume. Déjà fait deux fois : **Lumen v2.3** (style « ✨ Karaoké TikTok », Whisper `word_timestamps`) et
> **PromoClip** (`generateSubtitleASSFromWords` → ASS `{\k<cs>}` par mot, incrusté ffmpeg) → RÉCUPÉRER, ne pas
> réinventer. Temps des mots : Whisper mot par mot sur le MP3 de chaque page (gateway, une fois par narration,
> gardé dans `narration.json`) ; secours = répartition proportionnelle à la longueur des mots. Deux usages :
> le **lecteur de l'app** (avant la vidéo) et la **vidéo** (option à la génération, comme les sous-titres simples).
> ✅ **(2-bis) LECTEUR FAIT v1.86.0 (22/09 01h10)** : `scripts/karaoke_mots.py` = Whisper Groq mot par mot (même appel que promoclip-local `whisperTimestamps()`) + **recalage sur le texte exact** (difflib) ; deux pièges mesurés sur Claymore et corrigés : Whisper **saute** parfois un passage et étire le mot suivant (p.2 : 15 mots absents, « ombre » = 2,7 s) → les accroches qui bordent un trou impossible à dire (> 25 caractères/s) sont retirées ; et il **déborde** de ~3 % après la fin du MP3 → échelle ramenée à la durée vraie. **94 % des mots reconnus, 0,003 $ et 61 s pour 19 pages**, 0 page incohérente. Bouton « 🎤 Karaoké » par narration (route `/manga/karaoke`, `proxy-patch/patch_karaoke.py` + `.diff`) ; lecteur : case « karaoké » (mémorisée), mot en cours en jaune, mots dits allumés, suite atténuée ; **repli au prorata** tant qu'une narration n'est pas calée. Banc `test_karaoke_ui.py` **30/30** (PC + 360 px, dont un calage réel lancé par le bouton), mutation rouge. Calées : Claymore `banc-k3-charon` et `banc-k3-fenrir`. **Reste** : la vidéo (ASS `{\k}`, étape 5, à discuter) ; caler automatiquement en fin de narration (non fait : ça touche `narrate_chapter.py`).

| ~~1~~ | ~~Personnages par EXEMPLES visuels~~ → **ÉCHEC mesuré** (v1.69, `--portraits`) | Raki et Zaki se ressemblent | — |
| ~~1-bis~~ | ~~CONSENSUS « désaccord = prudence »~~ → **mesuré le 21/09 18h55, NON retenu** (`scripts/consensus_narration.py`, hors app) : K3 seul 1/2/1 (4) · K3+Gemini 1/0/2 (3) · Gemini×2 2/1/4 (7) · K3×2 0/1/1 (2). Aucun à 0/0/0 ; gains dans le bruit d'un si petit échantillon, et la FUSION crée ses propres erreurs (p4 « Raki près du cadavre » n'apparaît qu'après fusion). Doubler le coût (K3×2 ≈ 4,20 $/chapitre) pour ~2 erreurs de moins sur 60 pages : non. **Défaut maintenu = K3 seul** (~1 grave / 15 pages, toujours sur un cas ambigu « qui interpelle qui »). | — | — |
| **2-bis ⭐ (Quang 21/09 19h18)** | **COÛTS toujours visibles**, comme StoryVoice (`#hdrCost` + overlay « Suivi & coûts ») : pastille en haut « 💰 auj. X · mois Y », clic = détail par ÉTAPE (noms, lecture, récit, voix), par MOTEUR et par chapitre. Source = les `stats` de chaque `narration.json` (coûts mesurés, pas estimés) ; un run `--reuse-vision` ne recompte PAS la lecture | juger le rapport qualité-prix en usage réel (« laisser passer quelques erreurs, juger qualité/prix, et la vitesse quand c'est nécessaire ») | totaux = somme vérifiée des `narration.json` ; 0 double compte |
| 2 | **Fiche personnages par SÉRIE** : les noms prouvés au ch.1 servent au ch.2 | moins d'erreurs, moins de votes | ~~ch.2 de Claymore~~ → **One-Punch Man ch.300 → ch.301** (ch.301 capturé par Quang via l'app le 21/09 19h29, 19 p., code 3 = 3 avertissements) : 0 grave |
|  | 📏 **Mesuré le 21/09 à 20h15 — AUCUN GAIN sur cette paire** (`narrate_chapter.py --serie`, v1.74.0, désactivé par défaut) : ch.301 (scan **vietnamien**, 1ᵉʳ test hors anglais) jugé contre `reference_faits.json` écrite en lisant les 19 p. → **sans fiche 7 graves / 19 · avec fiche 7 / 19** (1 run chacun, K3 v2.2, 0,76 $ l'un). La fiche du ch.300 ne contenait QUE Tatsumaki (absente du 301) : elle n'a rien nommé de travers, mais n'avait rien à apporter — **Blue, le vrai personnage récurrent, n'est pas nommé au ch.300**. ⇒ La fiche ne vaut que si le personnage récurrent a été NOMMÉ avant ; ce test ne la valide ni ne l'invalide. **Les 7 graves sont ailleurs, et c'est le vrai verrou** : (a) **un anonyme confondu avec un nommé** — le héros au teint sombre (p13-17) pris pour Blue, 4-5 pages à lui seul, les deux étant de jeunes hommes aux cheveux courts ; (b) **un nom CITÉ pour un ABSENT collé à un présent** — « M. McCoy ? » (parti aux toilettes) devient l'homme du fauteuil. Le vote des noms prouve qu'un nom est ÉCRIT, pas QUI le porte (Raiden, Webigaza : « cheveux non visible » = absents, figés quand même). | — | — |
|  | 📏 **Correctif v3 mesuré le 21/09 à 22h05 — AUCUN GAIN, non retenu** (`--noms v3`, v1.75.0, désactivé par défaut) : le vote demande si le porteur est DESSINÉ + son teint + sa tenue. **8 graves / 19** (1 run valide) contre 7 en v2, pour **0,96 $** au lieu de 0,76 $. Il écarte bien les CITÉS (Raiden, Webigaza) mais aussi Sitch (présent p11, nommé p12 hors champ), et **garde McCoy** 2 runs sur 2 : Gemini juge mal la présence. La tenue n'aide pas : K3 écrit lui-même « Blue a changé de tenue p7, même âge, cheveux, teint : c'est bien Blue » — puis appelle Blue le héros au teint sombre. ⇒ Le verrou « qui est qui » ne se lève PAS par la fiche ; piste suivante à mesurer : faire trancher par page « ce personnage est-il CELUI de la fiche, oui/non/incertain », incertain = anonyme. **Acquis de robustesse (gardé, v1.75.0)** : K3 rendait un contenu VIDE, 4 fois sur 4, sur p11-12 en v3 (7 997 / 8 000 tokens passés à raisonner, `finish_reason=length`) → le chapitre entier était perdu ; budget désormais **doublé à chaque essai (8 000 → 16 000 → 32 000)** et délai d'appel proportionnel (5 timeouts à 240 s ont tué le run suivant). Ré-essai du lot : passé du 1ᵉʳ coup (3 150 tokens) — la montée de budget n'a donc pas encore été exercée en réel. | — | — |
| ✅ **3 — FAIT v1.71.0 (21/09 19h)** | **Capture intégrée à l'app** — banc live 4/4 (3 captures/remplacements réels de 23 p. + 1 remplacement en ÉCHEC → ancien chapitre RESTAURÉ à l'identique), refus de remplacer = rien lancé 3/3, 0 orpheline, 360 px OK. Deux défauts trouvés et corrigés : manga-fetch sort en **code 3 = réussite avec avertissements** (pris pour un échec) ; `--force` laissait les **anciennes pages orphelines** → le proxy met l'ancien de côté et le restaure si la capture rate. **Avant** : (manga-fetch v0.2.1, consommé tel quel, JAMAIS modifié par Manga Studio — domaine de la session GLM) : l'app **liste les onglets** de la fenêtre dédiée (CDP 9223, `/json/list`) → Quang **choisit** l'onglet (remplace la confirmation console, cf. incident 18:47 du mauvais onglet) → titre (existants proposés) + n° → proxy lance `capture --tab <url exacte> [--force si remplacement confirmé] [--page-1]` → progression lue dans `%LOCALAPPDATA%\manga-fetch\events.log` → le chapitre apparaît dans 📚 Chapitres. + afficher les **notes** du manifeste (page étroite, départ au milieu, intercalaire) et un bouton **Vérifier** (`verify` : intégrité + complétude) | tout dans l'app, plus de console | 10 captures via l'app = 10 manifests valides ; 0 mauvais onglet |
| 4 | **Lecture case par case** + **bulles effacées** : la caméra suit les cases (YOLO Manga109, déjà là) au rythme de la voix ; texte des bulles effacé (v1.6.2) | le dynamisme des recaps ; la narration remplace le texte | ordre des cases juste sur 20 pages ; 0 bulle lisible |
| 4-bis | **DÉCISION QUANG 22/09 23h58 — mode vidéo « case par case » AJOUTÉ, l'actuel CONSERVÉ.** Démo hors app vue sur Telegram (OPM ch.300 p.3-7, même audio que la vidéo actuelle ; caméra de case en case, reste assombri, sous-titres en fenêtre de 4 lignes) : « clairement beaucoup plus immersif, je préfère nettement ». EXIGENCES : choix du mode **mémorisé** ; **mode par défaut** réglable (profil général ⭐) ; appliqué aux **nouveaux chapitres / nouvelles séries**, à **tous les chapitres**, au **lot** (« Tout traiter », suivi de nuit). Détection : `scripts/panel_yolo.py` (YOLO26n Manga109, gratuit, local) — la démo utilisait une détection par blocs d'encre (2 cases fusionnées p.6). Coût IA : **0** (narration inchangée, page par page). Limite connue : le temps par case suit sa TAILLE, pas la phrase dite. ⛔ Pas de code avant le GO de Quang. | immersion | ordre des cases juste ; 0 réglage perdu au redémarrage ; lot et suivi de nuit respectent le défaut |
| 4-ter | **Démo WEBTOON 23/09 00h03** (Solo Leveling Ragnarok ch.1 p.26-30, Telegram) : case par case = la case remplit la largeur + défilement vertical (une page découpée = déjà UNE case). Quang : « moins immersif, moins d'effet… pas mauvais » → garder le choix ; manga classique = case par case, webtoon = plutôt le mode actuel. ~~PROPOSITION Claude : défaut « Automatique »~~ → **Quang se ravise le 23/09 00h08 : « même pour les webtoons, c'est quand même plus immersif, le deuxième mode » ⇒ DÉFAUT = CASE PAR CASE partout**, page entière au choix. (Ancienne proposition : défaut « Automatique » (case par case si manga, actuel si webtoon ; webtoon = hauteur/largeur des pages ≥ ~2,5 ou chapitre découpé par manga-fetch), forçable par série (profil) et changeable dans le défaut général ⭐. Réserve : en mode actuel, un webtoon s'affiche en bande étroite (lisibilité). | le bon mode sans y penser | détection manga/webtoon juste sur les 6 séries de la bibliothèque |
| ✅ **4-quater — FAIT v2.5.0 (23/09 01h)** | **Mode « case par case » livré — vidéo ET lecteur** (Quang 23/09 00h1x : « oui, lecteur aussi »). Règle unique `scripts/cases_video.py` (détection YOLO Manga109 pour le manga, étendue du dessin pour le webtoon, cache `sources/<chap>/cases.json` invalidé si une page change ; caméra : aperçu de la page 10 %, puis chaque case le temps ∝ √aire, glissé 0,5 s, zoom 1→1,035, voile 170/255 ; double page = moitié droite puis gauche ; webtoon = pleine largeur + défilement, fondu 0,3 s). Le lecteur en porte le miroir JS (`camPlan`/`camPose`), **identique à 0,01 px près sur 20 880 poses** (banc `test_camera_ui.py`, mutation vérifiée rouge). Réglage `camera` à 3 niveaux (intégré « cases » < ⭐ défaut général < profil de série) ; case 🎥 du lecteur = choix de la SÉRIE (lecteur + vidéos) ; « Précédemment… » garde le zoom lent. Vidéos d'avant : **empreinte inchangée (20/20)** → pas « à refaire » dans la liste, mais « Tout traiter » les voit « réglage changé (caméra) ». Rendu : ~temps réel/2 (webtoon 13 min 18 en 7 min, 3 pages en parallèle). Proxy : `proxy-patch/patch_camera.py` (+ `.diff`), `/manga/cases`, `/manga/camera`. **v2.5.1 (23/09 08h51, Quang : « dans un chapitre, je n'ai pas le choix […] seulement le batch »)** : sélecteur [🎥 Case par case · Page entière] dans le bloc 🎬 Vidéo du chapitre et le panneau 🎬 Vidéos, même choix de série (banc 18/18 PC + 360 px). | immersion | ✅ banc caméra 29/29 (PC + 360 px) ×2 relances du proxy · lot « Tout traiter » → vidéo cases à jour · bouton 🎬 → webtoon entier OK · ⭐ défaut « page » puis forçage série OK · profil 17/17, lecteur 13/13 |
| ✅ **11 b-bis — BULLES OUBLIÉES RATTRAPÉES, traduire_chapitre v1.92.0 (23/09 12h45)** (Quang 10h26 : « quasi toutes les pages sont en anglais » sur Noritaka ch.1 ; puis « le risque, c'est de patcher en baissant ce seuil et que cela engendre des bugs ailleurs ») | **État des lieux sur TOUT le traduit** (9 chapitres, 1 052 bulles) : le seuil YOLO 0,25 = valeur par défaut d'ultralytics, jamais mesurée ; 206 zones vues dessous, classées à l'œil → 53 vraies répliques dès 0,10, mais **baisser le seuil tout court remplaçait 10-14 bonnes bulles** par un fragment (`sans_chevauchement` garde la plus petite). **Retenu : COMPLÉMENT** (`zones_texte`) — le traitement à 0,25 reste identique, on n'AJOUTE que les zones ≥ 0,10 qui ne touchent (à 15 % près) aucune bulle forte, et on ne les pose que si c'est franc : ≥ 2 lettres, traduction qui TIENT (essai à blanc avant effacement). **Mesuré en réel sur copies (2 passages, ~5 $)** : bulles d'avant 1 052/1 052 aux mêmes zones ; 1ᵉʳ passage 7 ratés + 5 logos « Đ » effacés → garde-fous → 0 dessin/logo touché (vérifié à l'œil), 27 répliques gagnées ; surcoût +2 à +9 % (1 appel par page, inchangé). Banc sans coût : `scripts/test_complement_bulles.py` (identité sur toutes les pages + mutation rouge). Tes traductions existantes ne sont PAS refaites d'office. | moins de bulles en VO | ✅ identité 222 pages · 0 dessin effacé · 27 répliques |
| 5 | **Vidéo MP4 par chapitre** (ffmpeg : pan/zoom + voix + sous-titres incrustés) | simple, et c'est le **mode hors-ligne** : un fichier sur le téléphone, PC éteint | MP4 lisible sur le Fold, synchro voix/page ±0,3 s |
| 6 | **Deux MODES** : *Récit* (l'actuel, un narrateur raconte) et *Lecture* (les répliques lues case par case, attribuées au bon personnage, voire une voix par personnage) | demandé par Quang le 21/09 ; le mode Lecture exige l'étape 1 | mode Lecture : 0 réplique mal attribuée sur 20 pages |
| ✅ **7 — FAIT v1.94.0 (22/09 08h55)** | **« Précédemment… » + rattrapage** (décision Quang 08h40 : les deux, voix, réglable) : `scripts/precedemment.py` résume le RÉCIT déjà écrit des chapitres d'avant (narration la plus récente avec voix), jamais les images → 0 nouvelle erreur de « qui est qui » ; DeepSeek V4 Flash « n'ajoute rien » + Chirp 3 HD ; sous `ch_N/precedemment/`, sources gardées → 🟠 si une narration source change. Mesuré OPM ch.301 : ouverture **21 s, 0,013 $, 6 s de fabrication** — 6 affirmations sur 6 retrouvées dans le récit du ch.300, 0 ajout (vérifié à la main) ; rattrapage **63 s pour 1 chapitre, 0,033 $** (1er jet = le chapitre recopié, 600 mots → consigne « AU PLUS » + redemande si > 2× la cible : 3/3 à ~140 mots). Lecteur : case 📜 (mémorisée, cochée) = l'ouverture avant la page 1 ; « ▶ Rattrapage puis ce chapitre » ; jamais en écoute à l'aveugle. Coûts (poste « précédemment », corbeille comprise) + cellule d'activité. Proxy : `patch_precedemment.py` + `.diff`. Banc `test_precedemment_ui.py` **37/37** (PC + 360 px, son qui joue réellement), mutation rouge 12 KO. **Non fait, à trancher par Quang (question posée 22/09 08h55)** : la VIDÉO n'inclut pas le « Précédemment… ». **Au passage (demande Quang 08h43)** : la vidéo prend bien le volume de musique du lecteur (mesuré 0/10/25/60/100 % → gain exact) ; défaut corrigé : 0 % devenait 25 % (`video_chapitre.py` v1.94.0). ⚠ Le volume est UN réglage par appareil (lecteur), pas par chapitre. | reprendre une série après une pause | ✅ fidèle (contrôle manuel) |
| 8 — ✅ en grande partie (v1.76 + v1.82) | **Voix** : ~~changer de voix sans refaire la lecture~~ ✅ v1.82.0 (bouton « 🎙 Autre voix » : texte repris via `reuse`, voix seule refaite — mesuré **15 pages en 57 s, 0,165 $ = 0,011 $/page**, OPM 301 → `kimi-fenrir`) · ~~aperçu~~ ✅ v1.76.0 · ~~voix mémorisée par série~~ ✅ v1.82.0 (défaut Charon si rien de mémorisé) · **reste** : prononciation des noms, contrôle des élisions | « selon l'humeur et le manga » (Quang) | changer de voix ≤ 1 min, 0 relecture vision |
| ✅ **9 — SUIVI DE SÉRIES v1.98.0 (22/09 09h40)** (sans plafond, décision Quang 09h00) | `scripts/suivi_nuit.py` : pour chaque série au suivi actif (`sources/<série>/suivi.json` — PAS `serie.json`, que « Tomes et dates » réécrit en entier), narre un par un les chapitres SANS narration avec voix (K3, voix de la série), cale le karaoké, fait / refait le « Précédemment… » là où il manque, demande la vidéo (option). Jamais deux passages (verrou PID), jamais un chapitre déjà en narration, 2 essais max. Tâche planifiée **MangaStudioSuiviNuit** 01:30 (rattrapée au réveil si le PC dormait) + « ▶ Lancer maintenant ». App : « 🌙 Suivi » dans la barre de la série (file + estimation, voix, options, dernier passage, journal). Proxy `patch_suivi.py` + `.diff`. Banc `test_suivi_ui.py lancer` **9/9** (lancé EN VRAI depuis l'app sur Demo Frieren ch.143) ; `verifier` à passer à la fin de ce passage. ⚠ 1er passage réel : essai 1 en ÉCHEC (code 1 au bout de 27 min, lecture des pages K3) et sa CAUSE PERDUE — l'essai 2 réécrivait le même run.log et narrate_chapter ne journalisait pas ses échecs → corrigé (log AJOUTÉ avec en-tête, cause dans `narration.log` et dans le journal du suivi). **Cause de l'échec, trouvée à l'essai 2** : « lot [1, 2] : JSON illisible (Expecting ',' delimiter) » — K3 rendait un JSON MAL FORMÉ (pas tronqué) et le code relisait les images avec un budget doublé 3 fois (8 k → 16 k → 32 k tokens, ~27 min facturées) puis abandonnait le chapitre. Sonde : K3 lit bien 2 pages en 29 s → pas une panne du moteur. **Corrigé (narrate_chapter v1.98.1)** : un JSON mal formé se RÉPARE d'abord (appel texte DeepSeek, contenu inchangé mot pour mot, ~0,0001 $, journal `json_repare`), la relecture des images ne reste qu'en dernier recours. **Méthode de test (Quang 10h36)** : déboguer avec **Gemini** (rapide, bon marché), passer sur K3 une fois la chaîne sûre → le suivi a maintenant un choix de MOTEUR (Kimi K3 défaut | Gemini), l'estimation suit. K3 sur Frieren ch.143 le 22/09 : 380 s pour le lot 1-2, lot 3-4 > 17 min → arrêté ; les délais dépassés ne laissaient AUCUNE trace → journal `reseau` (narrate_chapter v1.98.3). Pixtral : éliminé depuis le 21/09 (contresens, « explosion d'enfants »), confirmé par Quang. ⚠ Une narration lancée hors du proxy n'apparaît « en cours » que si son progress.json a < 3 min (K3 réfléchit parfois plus longtemps entre deux mises à jour). | tout est prêt le matin | ✅ **1er passage réel RÉUSSI (22/09 10h57)** : Demo Frieren ch.143 en **Gemini**, lancé depuis l'app → narration (19/19 avec voix) + karaoké, 0 erreur, **0,58 $ en 10 min 19** (lots de 2 pages en 10-25 s ; K3 le matin : 380 s pour le seul lot 1-2). Banc `test_suivi_ui.py verifier` **6/6**. À noter : le repérage des noms (votes) prend ~6 min sur 19 p. quel que soit le moteur — c'est maintenant l'étape la plus longue. |
| ✅ **10 — HORS-LIGNE DANS LE TÉLÉPHONE v1.99.0 (22/09 09h50)** (décision Quang 09h00) | « 📥 » sur une narration = texte, pages VO, voix et « Précédemment… » copiés dans le cache de l'app ; `pwa/sw.js` v1.99.0 : réseau d'abord, stockage SEULEMENT si le PC ne répond pas (erreur ou 5xx du tunnel) ; n'intercepte que la page et ce que lit le lecteur (vidéos, zip, actions : direct) ; audio par morceaux (Range) découpé dans le stockage ; coquille gardée dès l'installation. Bibliothèque : « 📥 Gardés sur ce téléphone » (taille, ▶, 🗑) visible PC éteint ; stockage persistant demandé. **Piège trouvé sur le Samsung** : l'index en localStorage était PERDU si l'app était tuée juste après (Android l'écrit en retard) — 36 fichiers gardés, liste vide → l'index vit maintenant DANS le cache. Banc `test_horsligne_ui.py` **26/26** (réseau coupé, localStorage effacé), mutation rouge ; **Samsung en mode avion après arrêt forcé** : liste présente, lecture « Précédemment… » puis pages, son qui avance. Limites : pages en VO, pas de musique. | écouter PC éteint | ✅ lecture en mode avion |
| 11 | **Toutes langues → français** (demande Quang 21/09 : « j'irai chercher les sources que je trouve, n'importe quelle langue ») : (a) narration FR depuis une page JP/ES/KR… (déjà le principe, **jamais testé hors anglais**) ; (b) **pages relettrées en français** (bulles effacées + texte traduit replacé, briques de l'onglet Ingestion v1.5-1.6.2) sur un chapitre entier | Quang lit ce qu'il trouve, quelle que soit la langue | banc de fidélité PAR LANGUE (JP vertical droite→gauche, webtoon KR) : 0 grave |
| ✅ **12 — FAIT v1.76.0 (21/09 23h20)** | **Bibliothèque rangée PAR MANGA** (Quang 21/09 19h29 : « ranger correctement par manga et ne pas tout afficher par chapitre ; dans les mangas, on verra bien sûr les chapitres ») : l'onglet 📚 montre d'abord les séries (couverture, nb de chapitres), un clic ouvre ses chapitres | la liste plate ne tiendra pas au-delà de quelques chapitres | 0 chapitre affiché hors de sa série ; ouvrir une série ≤ 1 clic. *Esthétique non prioritaire à ce stade (Quang), la structure l'est* **+ POCHETTE propre par série et par tome** (Quang 21/09 22h58 : « la pochette de la saison du manga ») — sources vérifiées le 21/09, sans clé : **AniList** `coverImage.extraLarge` = pochette officielle de la SÉRIE (Claymore, Boruto TBV OK) ; **MangaDex** `/cover?manga[]=<id>` = une couverture **par TOME** (37 pour OPM, locale `ja`), le chapitre → tome se lit sur l'API chapitre. Repli : choisir une page d'un chapitre, ou déposer une image. Fichier `sources/<série>/pochette.jpg` (donc sur C:) ; plus jamais la page 1 brute (souvent une mascotte de scanlateur, cf. OPM 301) |
| 3-bis ⭐ | **Capture MANGA Plus en défilement VERTICAL et sens JAPONAIS** (Quang 21/09 21h11, BORUTO -TWO BLUE VORTEX- #001, `mangaplus.shueisha.co.jp/viewer/7000901`, FR, 54 p.) : **1 seule page capturée, déclarée « terminée » sans erreur**. Journal `%LOCALAPPDATA%\manga-fetch\events.log` : `[mode] page par page doc=1273 ecran=1273` → `[navigation] bascule en clic (flèches sans effet)` → fin. Onglet relu en CDP : les 54 pages sont **empilées verticalement** (10 `<img>` 800×1223 à y = -3613…6408, compteur « 4 / 54 ») dans un conteneur qui défile — le document, lui, fait la hauteur de l'écran, d'où le faux « page par page ». Et (Quang) **les clics sont inversés** : clic à GAUCHE = avancer (sens de lecture japonais), l'inverse de MangaDex. Claymore (même site, 62 p. OK) était en page par page. ⚠️ `manga-fetch` = **domaine d'une autre session** (règle du HANDOFF) : correctif à y porter ou à confier. Côté app : **une capture de 1-2 pages doit être signalée comme suspecte**, jamais affichée comme réussie | capturer n'importe quel chapitre MANGA Plus | chapitre vertical 54 p. = 54 pages ; mode page par page toujours OK ; 0 capture tronquée affichée « réussie » |
| ✅ **12-bis — FAIT v1.76.0** | **Supprimer dans l'app** (Quang 21/09 21h11) : une ou plusieurs **pages** d'un chapitre (crédits, pubs du groupe de scan…), un **chapitre** entier, une **série** entière — avec confirmation (irréversible) | ménage des captures ratées (ex. `boruto-tow-blue-vortex/ch_1`, 1 page) et des pages parasites | supprimer 1 page / 1 chapitre / 1 série depuis l'app, relu sur disque ; annuler = rien supprimé |
| ✅ **13 — lecteur FAIT v1.85.0 (22/09 00h55)** — vidéo : à l'étape 5 | 📏 **Livré** : bloc « 🎵 Musique de la série » dans le chapitre (choisir, ▶ écouter seul, **importer un morceau** — fichier du PC ou du téléphone —, 🗑 corbeille) ; un morceau PAR SÉRIE (`sources/<série>/musique/` + `choix.json`), le 1ᵉʳ importé joue d'office. Dans le lecteur : case 🎵 et **curseur de volume** (défaut 25 % = −20 dB sous le niveau d'origine, mémorisés par appareil), **ducking** (−7 dB quand la voix parle, remonte en ~2,5 s entre les pages, redescend en 0,3 s), **boucle en fondu enchaîné** de 3 s (deux lecteurs qui se croisent), silence à la pause et à la fermeture. Proxy : `/manga/musiques`, `/manga/musique_import|choix|suppr` (`proxy-patch/patch_musique.py` + `.diff`). Les **4 échantillons de Quang importés par l'app** (Claymore et Boruto, moteurs 1 et 2). Bancs : routes `test_musique.py` **13/13**, interface `test_musique_ui.py` **40/40** (volumes RÉELS des lecteurs mesurés, PC + 360 px) ; mutations vérifiées rouges. ⚠ **Choix conservateur fait seul** (Quang dormait ; il avait dit « on verra comment on gère leur intégration et leur ajout ») : IMPORT d'un fichier + un morceau par série. **Reste à trancher avec lui** : générer depuis l'app (route de Generate Studio à LIRE avant), un morceau par ambiance, le niveau par défaut à l'oreille, et vérifier que les morceaux sont bien instrumentaux. | | |
|  | 📏 **Livré v1.87.0 (22/09 05h10) — « 🎛 Prendre dans Generate Studio »** (Quang 05h04 : les plus récentes par défaut, « tout voir » si besoin). Tu génères LÀ-BAS (mode intelligent + Instrumental) ; ici la playlist = `output/gs/audio/` lue par SES routes (`/outputs_list`, `/audio_meta`), 8 plus récentes / tout + recherche, écoute, badge MESURÉ « 🎤 voix détectée / 🎹 instrumental » (`analyse.json` de Generate Studio), avertissement avant de prendre un morceau chanté. « Prendre » = MP3 par `mp3_depuis()` (le cache `_mp3cache/` de la notif Telegram, jamais purgé) → série. Rien de Generate Studio dupliqué ni modifié. Route `/manga/musique_depuis_gs` (`proxy-patch/patch_musique_gs.py` + `.diff`). Banc `test_musique_gs_ui.py` **29/29** (8191, remet la série comme avant). |  |  |
|  | 📏 **Livré v1.88.0 (22/09 05h25) — cellule d'ACTIVITÉ dans l'en-tête** (Quang 05h12 : « un bandeau dynamique d'événements actuels […] ne crée pas d'effet où le bandeau apparaît et disparaît ») : cellule TOUJOURS présente, prise sur la largeur de la VRAM (le mot « VRAM » disparaît sous 480 px) ; grise « Rien en cours », colorée + pulsation quand ça travaille (« Narration Claymore ch.1 16/62 +1 »), verte « ✓ … finie » 10 min ; clic = panneau SUPERPOSÉ sous l'en-tête (tâches + barres, « Terminé pendant cette session », clic = ouvre le chapitre). Route `/manga/activite` (tous chapitres : plusieurs narrations/traductions en parallèle) qui RÉUTILISE `manga_narrations` / `manga_traductions` / `manga_fetch_status` ; le karaoké écrit `karaoke_progress.json` (son état survit enfin à un redémarrage du proxy). `proxy-patch/patch_activite.py` + `.diff`. Banc `test_activite_ui.py` **60/60** : hauteur d'en-tête IDENTIQUE à v1.87 aux 4 largeurs (43 / 75,5 / 94,5 / 94,5 px — la 1ʳᵉ version la cassait sur PC et à 320 px, trouvé par le banc) et immobile quand l'état change ; mutation rouge. |  |  |
| ✅ **FAIT v1.92.0 (22/09 06h20)** — ~~À faire ensuite (Quang 22/09 05h15)~~ | **Ergonomie de la bibliothèque et des chapitres** : le bloc « Rafraîchir » (gros texte avant/après = rectangle haut pour rien) → fin et discret ; lignes de narration en ZONES FIXES (🗑 et boutons toujours au même endroit, quel que soit le texte) ; moins de pavés de texte ; rendu propre et professionnel. + **Visionneuse plein écran** (05h15) : boutons du bas trop bas sur SON smartphone (chevauchent le bas de l'écran), PC OK → ~~les remonter~~ ✅ **v1.89.0** : sur écran tactile, marge fixe + zone de sécurité (`env(safe-area-inset-bottom)`, la page est en `viewport-fit=cover`) ; mesuré sur le VRAI Samsung : barre à 37 px du bas, rien ne se chevauche ; même marge sous les commandes du lecteur ; PC inchangé. |  |  |
|  | 📏 **v1.90 → v1.92 (22/09 05h30 → 06h20)** : **v1.90** musique par SÉRIE ou par CHAPITRE (« celle de la série / propre au chapitre »), jusqu'à 5 morceaux au hasard enchaînés en fondu, liste en colonnes fixes ; « décocher » = retirer d'ici ≠ 🗑 = supprimer de la base (série + tous les chapitres, corbeille) ; nom du manga numéroté, **un numéro supprimé n'est jamais réutilisé** (compteur) ; morceaux existants renommés (Claymore 1-3, Boruto 1-2). **v1.91** pastille des coûts COMPLÈTE (narration en cours, traductions, karaoké — elle ne lisait que les narrations finies) ; **temps restant** mesuré ; bug : une narration K3 immobile > 3 min (un lot a pris 12 min le 22/09) aurait été affichée « échec » après une relance du proxy → PID + `_pid_vivant` (celui de Generate Studio, réutilisé : le redéfinir l'aurait remplacé pour tout le proxy). **v1.92** ergonomie : barre de bibliothèque fine (230 → 65 px), capture repliée, avertissements repliés, actions du chapitre sur une ligne, narrations en ZONES FIXES (▶ 🎤 🎙 🗑 toujours au même endroit, nom en pleine ligne sur téléphone), traduction compacte. Banc `test_ergonomie_ui.py` 22/22 MESURÉ au pixel (1ʳᵉ version aveugle à un nom RECOUVERT par les boutons, vu sur capture → contrôle ajouté, mutation fidèle rouge). **Narration Claymore relancée (K3 v2.2, `kimi-charon`)** : Raki ×40 (0 dans les anciennes v1.66), 61 p., 11,3 min, 2,07 $, karaoké calé. |  |  |
| ✅ **5-bis — VIDÉO, compléments FAITS v1.95.1 (22/09 09h15)** (demandes Quang 09h00 → 09h10) | (a) **« Précédemment… » en tête de la vidéo si la case 📜 est cochée** (le réglage suit la case comme les sous-titres ; empreinte « le Précédemment… a été refait » ; clé ajoutée SEULEMENT si demandé → les vidéos d'avant ne passent pas 🟠) ; sous-titres longs réduits (46 → ≥ 30 px selon la longueur : le résumé débordait du bandeau). (b) **Voix de la vidéo** : menu quand le chapitre a ≥ 2 narrations avec voix (défaut = voix de la vidéo existante, sinon la plus récente ; mémorisé par chapitre). (c) **Nom du fichier téléchargé** lisible : « Série - ch001 - Voix - VO/FR - karaoké - musique 25 % - précédemment - 1,15x - date heure.mp4 » (+ nom ASCII de secours) — vérifié en VRAI téléchargement sur le Samsung. (c-ter) **file vidéo : programme MORT sur « Accès refusé »** (défaut v1.93, trouvé 22/09 09h54) : deux demandes à quelques ms d'écart lançaient DEUX programmes de file (le proxy ne voyait pas encore le 1er), qui traitaient la même demande → `os.replace` refusé par Windows → programme arrêté, demande bloquée « en cours » à vie. `video_lot.py` : verrou exclusif (`_runner.lock`, création atomique), écriture réessayée, demandes orphelines nettoyées au démarrage (vidéo faite → effacée, sinon échec avec raison). Rejoué : 2 demandes en parallèle → 2 vidéos à jour, file vide. (c-bis) empreinte « Précédemment… » sur le CONTENU, pas la date du fichier (le banc restaurait ouverture.json à l'identique et la vidéo passait 🟠 ; le banc restaure aussi la date, `shutil.copy2`). (d) pastille des coûts à DROITE sur téléphone (caméra au centre, Fold 8) et raccourcie. Bancs : `test_video_voix_ui.py` 25/25 (dont une vraie vidéo OPM ch.301 par la file), `test_precedemment_ui.py` 37/37, `test_karaoke_ui.py` 28/28. | | ✅ |
| ✅ **15 — GROUPE DE VIDÉOS FAIT v1.97.0 (22/09 09h35)** (Quang 09h17) | Panneau Vidéos de la série : sélection devenue un ÉTAT par série (elle se PERDAIT à chaque rafraîchissement, toutes les 4 s pendant une fabrication) ; **tout coché par défaut** ; « ☑ Tout » / « ☐ Rien » / plage « ch. X à Y » ; compte + poids (« 2 coché(s) · 2 vidéo(s) prête(s) · 114 Mo ») ; « ⬇ Une par une » ou **« ⬇ En une archive .zip »** : proxy `GET /manga/videos_zip` EN FLUX, MP4 stockés (pas de recompression), zip64, rien en mémoire ; nom « Série - vidéos ch300 à ch301 (2) - date.zip », vidéos dedans aux noms lisibles ; avertit au-delà de 2 Go. `patch_videos_zip.py` + `.diff`. Banc `test_videos_groupe_ui.py` **22/22** (PC + 360 px : archive valide, tailles exactes) ; **vrai téléchargement sur le Samsung** : un seul fichier de 113,8 Mo. ⚠ Le 1er passage a été coupé par une relance du proxy par la session Generate Studio (09:29:55, `logs/proxy_vie.log`) : rejoué vert. | 20 chapitres en un geste | ✅ |
| ✅ **16 — CHAPITRE PRÉCÉDENT / SUIVANT FAIT v1.96.0 (22/09 09h30)** (Quang 09h19) | Fiche du chapitre : « ⏮ ch. N » / « ch. N ⏭ » autour du titre (même série, ordre des numéros ; cachés s'il n'y a pas de voisin). Lecteur : « ⏮ ch. » / « ch. ⏭ » en haut → enchaîne la narration la plus récente AVEC voix du voisin sans sortir (musique et « Précédemment… » du voisin repris) ; en fin de chapitre « ▶ Chapitre suivant (ch. N (voix)) » ; voisin sans voix = grisé, raison au survol ; jamais en écoute à l'aveugle. Banc `test_chapitres_voisins_ui.py` **30/30** (PC + 360 px, son qui joue après chaque saut), mutation rouge ; vérifié sur le Samsung (app installée). | enchaîner la lecture | ✅ |
| ✅ **17 — CAPTURE DEPUIS LE TÉLÉPHONE FAIT v2.0.0 (22/09 10h45)** (Quang 10h29 → 10h42) | Trois modes EN PLUS du mode d'origine (onglet choisi sur le PC, inchangé — Quang 10h42 : « on conserve le mode d'origine ») : (a) **🕹 Piloter la fenêtre** : l'écran de l'onglet (CDP 9223, 0,1-0,2 s), toucher = cliquer, glisser = défiler, onglets (basculer, ＋, ✕), ◀ ▶ ⟳, adresse ou recherche, ⬆ ⬇ ← → Page ⏎, texte, « ✔ Capturer cet onglet » ; (b) **🔗 Lien du chapitre** collé → ouvert dans un nouvel onglet de la fenêtre de capture (ouverte au besoin), choisi, titre et n° proposés d'après la page (titre de la bibliothèque reconnu) ; (c) **Partager → Manga Studio** depuis n'importe quel navigateur du téléphone (`share_target` du manifeste) = même chose. La capture ne part JAMAIS seule : Quang vérifie et touche « Capturer ». Client websocket CDP écrit en bibliothèque standard (`scripts/cdp_mini.py`) : le venv du proxy n'en a pas, on n'y installe rien. Proxy `patch_pilote.py` + `.diff`. Bancs : `test_pilote_ui.py` **25/25** (dans un onglet à lui, ceux de Quang intacts), `test_lien_ui.py` **12/12** ; **vrai partage Android** sur le Samsung (intent SEND vers l'app installée) → onglet ouvert sur le PC, « Claymore » reconnu. ⚠ **L'app déjà installée ne se met pas à jour tout de suite** : Chrome relit le manifeste à son rythme → pour avoir « Manga Studio » dans le menu Partager TOUT DE SUITE, désinstaller et réinstaller l'app (vérifié sur le Samsung). ⚠ Piège du banc : un clic juste après un défilement peut viser un lien encore en mouvement. | se placer et lancer une capture depuis le téléphone | ✅ |
| ✅ **18 — PLUSIEURS CHAPITRES D'AFFILÉE FAIT v2.3.0 + manga-fetch v0.4.0 (22/09 14h20)** (Quang 10h43) | Étape 3 de la capture : « puis [N] chapitre(s) suivant(s), ou jusqu'au ch. [Y] ». **Vérifié site par site AVANT de coder** : **MangaDex** passe seul au suivant (Noritaka 1, OPM 300/301 le montraient déjà) mais on passe par l'API (`aggregate`, même langue que le chapitre lu) ; **MANGA Plus** ne passe jamais seul au suivant et son bouton « To Chapter #002 » ignore un clic scripté → page de la série, clic sur le chapitre, réouverture de son adresse (le lecteur se recharge juste après le clic : 1er essai en « Execution context was destroyed »). Suivant = plus petit numéro > courant ; **un trou arrête la série en le disant** (sauf « jusqu'au » qui le couvre). **Découverte** : MANGA Plus liste Claymore #004 comme gratuit mais son lecteur web reste à « 1 / 0 » (API 200, 0 page) → détecté en 30 s, arrêt expliqué. Mesures réelles : OPM 302→304 en 1 min 49 ; Claymore #002→#003 (39+39 p., 0 image commune). Pages : MangaDex annonce 21 images pour 19 pages réelles (crédits du traducteur répétés en fin) — rien de perdu. Proxy : `patch_capture_serie.py` (statut = chapitre EN COURS + `dossiers` + bilan `serie`). Bancs : `test_capture_serie.py` **27/27** (mutation « saute un chapitre » → 14/20 rouge), `test_capture_serie_ui.py` **13/13** sur le 8190 réel (360 px sans débordement ; « jusqu'au » avant le départ → rien d'envoyé ; 2 chapitres en 1 min 11), non-régression manga-fetch **9/9**. La règle 5 du README manga-fetch (« chapitre par chapitre, pas de crawl ») est **levée par Quang** (14h, « usage privé ») — barrée. | une série entière en un geste | ✅ |
| ✅ **25 — REPÈRES VISUELS v2.3.1 + langue_chapitre v2.2.1 (22/09 14h50)** (Quang 14h27, capture de la fiche Boruto) | (a) Fiche du chapitre : chaque bloc a son **titre + icône en haut à gauche** et un **liseré de couleur** à gauche — 🎬 Vidéo (orange, masqué si le chapitre n'a pas de vidéo), 🎙 Narration (rouge), 🌐 Traduction (bleu), 🎵 Musique (violet). Vérifié en réel 1280 et 360 px : 4 titres, 4 couleurs calculées, 0 débordement, 0 erreur JS (1er essai : liserés GRIS — la bordure de `.narr-box` déclarée plus bas l'emportait → sélecteur `.narr-box.bloc-x`). (b) **Boruto ch.2 affichait « VO (original) »** : la détection de langue avait échoué — Gemini dépensait **396 des 400 tokens** à réfléchir, réponse coupée à 28 caractères (« langue illisible »). Budget 2000 + « un seul objet » → 5/5 justes (Boruto fr ×3, Claymore en, OPM vi, ~0,0025 $ chacune), route proxy réelle : fr. (c) **Fenêtre de capture réduite — mesuré, NON retenu** : la capture réussit (23/23) mais manga-fetch la fait RÉAPPARAÎTRE (mise au premier plan de l'onglet, indispensable : un onglet de fond est freiné) et l'écran du pilotage met 1 à 2 min à venir. Quang : « soit une solution fiable, soit tant pis » → **la fenêtre reste affichée** (même derrière d'autres), pas de bricolage (hors écran, etc.). | se repérer d'un coup d'œil | ✅ |
| ✅ **26 — SÉLECTEUR + CHAPITRES INTERMÉDIAIRES v2.3.2 + manga-fetch v0.4.1 (22/09 15h00)** (Quang 14h45-14h47) | « puis N / ou jusqu'au » n'était pas clair → **sélecteur « Chapitres : jusqu'au ch. (défaut, vide = ce chapitre seul) / + chapitres suivants / ce chapitre seul »**, seul le champ utile affiché. Case **« ignorer les chapitres intermédiaires (298.5…) »**, cochée par défaut (`--sans-intermediaires`, proxy `patch_capture_entiers.py`) : fiable, le numéro vient du site (API MangaDex / liste MANGA Plus). OPM vi 295→299 aurait pris 296.5 ET 298.5. Banc `test_capture_serie_ui.py` **16/16** sur le 8190 réel : 296→298 = 296, 297, 298 (296.5 sauté), 1 min 54. | une série sans les hors-séries | ✅ |
| ✅ **2-ter — COÛTS EN DIRECT v2.0.1 (22/09 10h52)** (Quang 10h49 : « je dois relancer l'application pour que ça se rafraîchisse ») | La pastille n'était rafraîchie qu'à l'ouverture de l'app ou à la fin d'une tâche DU chapitre ouvert (suivi, vidéos, autre chapitre : jamais). Elle suit maintenant la cellule d'activité : toutes les 12 s tant que quelque chose travaille, aussitôt qu'une tâche finit, et au retour dans l'app. Mesuré sur la narration Gemini de Frieren, app ouverte sans le chapitre : 3,34 $ → 3,38 $ sans rien toucher, en phase avec le proxy. | | ✅ |
| ✅ **24 — CONFORT v2.2.1 (22/09 13h30)** | (a) **🔊 volume général** du lecteur (voix + musique au prorata), mémorisé par appareil (Quang 13h23) — mesuré : 40 % → voix 0,4, musique 0,045 → 0,018 ; (b) le **moteur de lecture** choisi la dernière fois redevient le défaut (Quang 13h25 : « Gemini par défaut ») ; (c) **en-tête sur deux lignes partout** (PC compris : à ~880 px « VRAM » passait sous ℹ — Screenshot Quang 13h26) — 0 chevauchement à 360/880/1280/1700 px. | | ✅ |
| ✅ **23 — REPÉRAGE DES PERSONNAGES 3,8× PLUS RAPIDE, narrate_chapter v1.99.2 + gateway v1.60 (22/09 13h20)** (Quang 12h58 : Boruto « à peine page 4 » après plusieurs minutes) | Journal : le repérage des noms (votes Gemini) prenait **17 min** pour Boruto 49 p. (tout le reste : ~6 min). 1re hypothèse (le plafond 20/min du gateway) **mesurée FAUSSE** : sans elle, Frieren 19 p. prenait encore 364 s et **aucun refus** — c'était l'ATTENTE : ~6 s par question, posées une par une. Remède : pages interrogées **4 à la fois** (+ leurs votes en parallèle), regroupement inchangé dans l'ordre des pages → **95 s au lieu de 364 s**, mêmes 10 noms, 0 refus. Le plafond a quand même été ouvert, pour que ce parallélisme ne se fasse pas refuser : gateway v1.60 = compteur À PART pour Manga Studio (User-Agent `manga-studio/`), 60/min ; les autres apps gardent le compteur commun à 20/min, inchangé (vérifié : 30 appels Manga Studio en 22 s = 30 × 200, un appel « autre app » = 200) ; frein client 18 → 54/min. **Au passage** : les noms qui ne diffèrent que par un accent sont fusionnés (« Fräse »/« Fràse » → un seul personnage ; Raki/Zaki restent distincts). Narration de bout en bout (Frieren p.1-6, Gemini) : OK en 91 s. | une narration Gemini de 49 p. en ~8 min au lieu de ~23 | ✅ |
| ✅ **22 — LANGUE D'ORIGINE DU CHAPITRE v2.2.0 (22/09 12h55)** (Quang 12h43 : « c'est marqué VO original ; j'étais sur un chapitre déjà en français, j'aurais pu lancer une traduction français → français ») | `scripts/langue_chapitre.py` : chapitre MangaDex → **API MangaDex** (translatedLanguage, exact, gratuit) ; sinon **Gemini lit 2 pages du milieu** (votes, ~0,003 $ ; Gemini rendait un objet PAR page → lecture de tous, majorité). Gardé dans `langue.json`, détecté une fois ; un chapitre nouvellement capturé reçoit sa langue tout seul à l'affichage de la bibliothèque. Mesuré : OPM 300/301 **vietnamien** (MangaDex), Noritaka anglais (MangaDex), Claymore anglais, Demo Frieren **français**, Boruto **français** (pages — vérifié à l'œil). App : « Pages affichées : **VO — vietnamien** », « ⚠ déjà en français » à côté du choix de langue, confirmation avant une traduction vers la même langue ; « VO vietnamien » sur la carte du chapitre. Proxy : `GET /manga/langue`, `/manga/resume` porte la langue, **`/manga/traduire` refuse la même langue sans « force »** — `patch_langue.py` + `.diff`. Banc `test_langue_ui.py` **20/20** (refus → rien n'est lancé). Au passage : le nom « Frāse » (macron) explique le doublon « Fräse / Fràse » du repérage des noms K3 de Frieren. | ne plus traduire vers la langue d'origine | ✅ |
| ✅ **21 — PLUSIEURS TÂCHES EN MÊME TEMPS sans se gêner, narrate_chapter v1.99.0 (22/09 12h45)** (question Quang 12h37 : narration + traduction en même temps ?) | Ça marchait déjà (aucun blocage), mais chaque programme se freinait SEUL à 18/min alors que le gateway limite à 20/min PAR IP (tout le PC) : à deux, refus « 429 ». Et chaque refus CONSOMMAIT un des 5 essais d'un appel → 5 refus d'affilée = narration en échec sans aucune panne. Corrigé : **frein commun** (compteur partagé sur disque, verrou msvcrt, `%LOCALAPPDATA%/manga-studio/frein_gateway.json`) pour narration, traduction, karaoké, Précédemment, suivi ; un 429 ne consomme plus d'essai (borne : 15 refus). Banc `test_frein_commun.py` **6/6** (3 programmes × 12 = 36 passages étalés sur 61 s, jamais > 18/60 s ; mutation « chacun son frein » → 36 d'un coup = rouge ; 7 refus puis OK → réussit). Limite : Generate Studio et les autres apps passent par le même gateway sans ce frein. | lancer narration + traduction + suivi ensemble | ✅ |
| ✅ **17-bis — CAPTURE EN 4 ÉTAPES v2.1.1 (22/09 11h10)** (Quang 11h01 : « pas clair, la chronologie, le lien smartphone, à quel moment je mets le nom du manga et le numéro » — « car les champs sont après ») | 1. Ouvre la page : UN choix (📱 lien du téléphone | 🕹 piloter la fenêtre | 🖥 sur le PC), seule la façon choisie s'affiche, mémorisée (défaut : lien sur téléphone, PC sinon) · 2. l'onglet (choisi tout seul) · 3. nom et n° (proposés d'après la page : à vérifier) · 4. Capturer. Aucun identifiant ni code de capture changé. Bancs `test_pilote_ui` 25/25, `test_lien_ui` 12/12. ⚠ Trouvé à la capture d'écran : un onglet Wikipédia de mon diagnostic était resté dans la fenêtre de capture de Quang → fermé (ses 4 onglets intacts). | | ✅ |
| ✅ **20 — CE QUE CHAQUE SÉRIE / CHAPITRE POSSÈDE, en page principale v2.1.0 (22/09 11h10)** (Quang 10h58) | Carte de série : « 🎙 n/N narrés · 🎬 vidéos · 🎵 morceaux · 🌙 moteur du suivi » ; carte de chapitre : « 🎙 n · voix · 🎤 karaoké · 📜 Précédemment · 🌐 langues » (le badge 🎬 ✅/🟠 existant reste), « pas encore narré » sinon. Proxy `GET /manga/resume` (une lecture du disque, narration.json en cache par date : 15 ms) — `patch_resume.py` + `.diff` ; rechargé à l'ouverture de la bibliothèque et à la fin de chaque tâche. Banc `test_resume_ui.py` **16/16** (chiffres comparés à un comptage INDÉPENDANT du disque, PC + 360 px). | voir d'un coup d'œil ce qui est prêt | ✅ |
| ✅ **19 — SITES VALIDÉS FAIT v2.3.3 (22/09 15h05)** (Quang 10h47) | Étape 1 de la capture : « 🌐 Sites validés (2) » repliable — une ligne par site (nom = lien qui s'ouvre dans le navigateur, capture ✅/🟠/❌, plusieurs chapitres, note + date du contrôle), puis « Partager → Manga Studio ». Liste VERSIONNÉE `manga-fetch/sites.json` (règle dans son champ `_lire` : un site n'y entre qu'après capture réelle + test d'enchaînement ; un site cassé est marqué, pas retiré), servie par `GET /manga/sites` (`patch_sites.py`). MangaDex ✅/✅ ; MANGA Plus ✅/🟠 (gratuits seulement, #004 Claymore vide sur le web). Au passage (Quang 14h58) : bouton du pilotage renommé « ✔ Choisir cet onglet » (il ne capture pas) ; **PAS de nom/n° préremplis en mode Piloter** (Quang : le titre ne le dit pas toujours). Banc `test_sites_ui.py` **21/21** sur 8191 puis 8190 (1280 + 360 px, le lien ouvre bien le site). | savoir où capturer, y aller en un geste | ✅ |
| ✅ **14 — APP INSTALLABLE FAIT v1.95.0 (22/09 09h00)** (demande Quang 08h36) | `pwa/` : manifeste (display **fullscreen** : ni barre d'adresse ni bandeau de notifications ; portée et départ `/manga/`), icônes 192/512 + masquable (le ◤ de l'en-tête), `sw.js` minimal SANS cache (gestionnaire fetch qui ne répond à rien : Range des MP3/vidéos intacts ; hors-ligne = étape 10). Proxy (`patch_pwa.py` + `.diff`) : ces 5 fichiers PUBLICS, liste fermée, avant le contrôle du jeton (le navigateur les charge sans jeton ni cookie) ; `/manga` → **302 `/manga/`** (sinon la page était HORS de la portée : pas d'installation proposée). Pas de Cloudflare Access sur le tunnel (vérifié : 200 direct). **Vérifié** : tunnel sans jeton → manifeste/icônes/sw 200, `/manga/costs` 401 ; **Samsung réel** : manifeste lu, sw actif, Chrome propose « Installer » (≠ « raccourci ») → **WebAPK installé** (`org.chromium.webapk.*`, 08:59:41), lancé depuis l'icône = plein écran, données chargées (clé reprise de Chrome). **Chez Quang** : ouvrir le lien dans Chrome → ⋮ → « Installer et créer un raccourci » → **Installer** (supprimer l'ancien raccourci). | icône sur l'écran d'accueil, plein écran | ✅ installation réelle |
| ✅ **5 — VIDÉO FAITE v1.93.0 (22/09 06h50)** | **Vidéo d'un chapitre = le lecteur, réglages compris** (décisions Quang 06h24-06h26 : 9:16 seul, « refléter exactement ce qui est affiché », mode série, traçabilité, tag « à refaire », supprimer / régénérer, télécharger PC et téléphone, téléchargement multiple). `scripts/video_chapitre.py` REJOUE le lecteur (montrerPage / musTick / karTick) : durée d'une page = voix/vitesse + 0,45 s (muette 2,5 s), zoom kb/kb2 sur la scène entière, sous-titres ou karaoké (ASS, un événement par mot), musique aléatoire à graine gardée + ducking rejoué au pas de 100 ms ; ffmpeg + NVENC, 0 $. Compression MESURÉE : CQ 25 = 5,3 Mbit/s, CQ 30 / 2 Mbit/s = 2,1, identiques à l'œil en gros plan → **Claymore ch.1 : 10 min 17, 160 Mo, fabriquée en 4 min 06**. File : un fichier PAR demande (`sources/_videos_file/`), `scripts/video_lot.py` les fabrique une par une (survit à une relance du proxy). **Empreinte** gardée avec la vidéo (narration, karaoké, voix, pages, traduction, musique) → 🟠 « à refaire » + raisons ; les réglages du LECTEUR (propres à chaque appareil) ne sont qu'une note ℹ️ (trouvé par le banc : sinon tout serait 🟠 sur un autre téléphone). Proxy : `/manga/videos`, `/manga/video`, `video_suppr`, `video_annule`, `/manga/video_file` EN FLUX (Range ; `serve_manga_file` lisait tout en mémoire) — `proxy-patch/patch_video.py` + `.diff`. Banc `test_video_ui.py` **31/31** (lecture réelle 1080×1920, téléchargement complet, Range, raisons proxy ET client), mutation rouge. **Plus tard** : caméra case par case (4), « Précédemment… » (7). |  |  |
| 13 (historique) | **Musique de fond sous la narration** (idée Quang 21/09 22h56), générée EN LOCAL par la fonction Musique de Generate Studio (droits : à nous). 2 échantillons « Claymore » reçus (moteur 1 : 3 min 23 ; moteur 2 : 2 min 00). Mesures : **−11,4 LUFS** et LRA 10,8 / 12,7 LU = mixés pour être écoutés SEULS → sous une voix il faut : (a) **instrumental** (des paroles se battent avec le narrateur — à vérifier sur chaque morceau), (b) niveau **~20 dB sous la voix**, (c) **ducking** (la musique baisse quand la voix parle, remonte entre les pages), (d) **boucle en fondu** (un chapitre dure 5-20 min). Un thème PAR SÉRIE, peut-être par ambiance (combat / calme) plus tard. Deux endroits : le lecteur de l'app (mélange en direct, curseur de volume, interrupteur — rien à régénérer) et la vidéo MP4 (étape 5, `sidechaincompress` ffmpeg). **Échantillons reçus** : Claymore (moteurs 1 et 2, 21/09 22h56) et **Boruto** (moteurs 1 et 2, 23h41), générés par Quang dans Generate Studio. **Reste à définir AVEC Quang** (23h43 : « on verra comment on gère ça dans l'application, leur intégration et leur ajout ») : importer un morceau, l'associer à une série, en générer depuis l'app. **Précision Quang 21/09 22h59** : OPTIONNELLE partout (activer / désactiver) ; pour la VIDÉO, c'est un choix fait À LA GÉNÉRATION — avec ou sans musique, avec ou sans sous-titres (gravé dans le fichier). ⚠️ Route de génération de Generate Studio : LIRE son code avant de l'appeler (règle : jamais deviner un endpoint) | l'ambiance des recaps | voix intelligible à 100 % au banc d'écoute ; musique qui baisse sous chaque phrase |
| — | **Codex de série importé** (piste Quang 21/09 22h55, pour le verrou « qui est qui », APRÈS le socle) : wiki Fandom (API MediaWiki, sans clé : fiche + **apparence détaillée** de Blue, Sitch, McCoy vérifiées le 21/09) + AniList (GraphQL sans clé : distribution, portraits officiels, rôle). Limites vérifiées : le wiki OPM numérote les chapitres **web**, pas le manga → pas de liste par chapitre, seulement **par arc** (longue) ; tous les mangas n'ont pas un tel wiki. Combiné à une vérification par page « oui / non / incertain → anonyme » ; filet : correction d'un clic par Quang, propagée à la série. Garde-fou : la liste d'arc sert à IDENTIFIER, jamais à raconter (anti-divulgâchage). Banc : OPM 301 (7 graves à battre) | 0 anonyme pris pour un nommé | ≤ 2 graves / 19 sur OPM 301 |
|  | 📏 **Livré v1.76.0 (21/09 23h20)** : séries d'abord (pochette, nb de chapitres et de pages), un clic = ses chapitres, série ouverte mémorisée ; pochette officielle AniList (bouton, titre modifiable), « charger une image », « cette page comme pochette » ; suppression série / chapitre / pages sélectionnées → **corbeille** `sources/_corbeille/` (réversible à la main), refusée pendant une capture ou une narration ; narrations **sans voix repliées** sous « Essais techniques » (Quang : « liste moche ») ; **aperçu ▶/■ de chaque voix** avant de narrer (8 échantillons `sources/_apercus/`, `scripts/voix_apercus.py`, 0,03 $ — avance de l'étape 8). Proxy : routes `/manga/pochette` + `/manga/source_delete` (`proxy-patch/patch_bibliotheque.py` rejouable + `.diff`), testées sur une instance 8191 puis le 8190 réel. Bancs : `test_bibliotheque.py` **19/19** (mutation vérifiée rouge) + `test_bibliotheque_ui.py` **32/32** PC et 360 px. Défaut trouvé par le banc : la classe `.pick` était déjà celle des cases de la galerie → les pages cochées se réduisaient à 26 px et disparaissaient. | | |
| ✅ **12-ter — FAIT v1.77.0 (21/09 23h25)** | **Saisons / tomes avec leurs dates** (Quang 21/09 23h07 : « la gestion des saisons, peut-être même leurs dates, leur année… il y en a plusieurs ») : ranger les chapitres d'une série par **tome / partie** (ex. Boruto : partie 1 puis *Two Blue Vortex*), avec l'**année** ; pochette PAR tome. Sources à vérifier au moment de coder : MangaDex (tome de chaque chapitre, couvertures par tome, dates de publication), AniList (dates de début/fin, statut). | s'y retrouver dans les longues séries | chaque chapitre rangé dans son tome, année affichée |
|  | 📏 **Livré v1.77.0** : route `/manga/serie_infos` (`proxy-patch/patch_tomes.py` + `.diff`) — série retrouvée sur MangaDex par l'URL EXACTE d'un chapitre capturé sur MangaDex, sinon par le titre ; tome de chacun de nos chapitres (`/aggregate`, un vrai tome l'emporte sur « none ») ; couvertures des tomes possédés (512 px, `sources/<série>/tomes/`) ; année + statut (MangaDex), année de FIN (AniList, retenue seulement si l'année de début concorde) → `sources/<série>/serie.json`. Récupéré tout seul à la 1ʳᵉ ouverture d'une série ; bouton « 📅 Tomes et dates » (titre modifiable). Carte : « 2001–2014 · terminé · 27 tomes » ; série : chapitres groupés « Tome N » (couverture) / « Hors tome — pas encore relié ». Résultat réel : Claymore ch.1 = tome 1 (2001–2014) ; Boruto TBV et Noritaka ch.1 = tome 1 ; OPM 300-301 et Frieren 143 hors tome (trop récents). ⚠️ **Pas de date PAR CHAPITRE** : MangaDex n'a que la date de la TRADUCTION, pas la parution japonaise — non affichée pour ne pas mentir. + **supprimer une NARRATION** (Quang 23h19 : « ai-je la possibilité de supprimer un audio ? ») → corbeille, refusée si elle tourne ; + le lecteur **saute les pages supprimées après coup** (chaque page narrée porte son FICHIER : aucun décalage possible). Bancs : routes **28/28**, interface **40/40** (PC + 360 px). | | |
| ✅ **12-quinquies — FAIT v1.78.0 (21/09 23h25)** | **Agrandir une page DANS l'app** (Quang 23h22 : « zoomer, dézoomer, me déplacer… PC mais aussi smartphone », au lieu d'ouvrir un onglet) : réutilise la visionneuse de la galerie (molette centrée sur le curseur, double-clic, pincée, glisse, double-tap, flèches, Échap) + **balayage** gauche/droite au doigt pour changer de page quand l'image n'est PAS zoomée (zoomée, le même geste la déplace). Banc 50/50 dont gestes tactiles RÉELS (CDP `Input.dispatchTouchEvent`, 360 px). | | |
| ✅ **12-sexies — FAIT v1.80.0** | **Bloc « Capturer un chapitre » repliable, état mémorisé** (Quang 23h23) : plié / déplié gardé d'une ouverture à l'autre (par appareil) | la capture est ponctuelle, la bibliothèque est le quotidien | replié reste replié après rechargement |
|  | 📏 **Livré v1.80.0 (21/09 23h45)** : **onglet « Bibliothèque » en PREMIER** (ex-« Chapitres », au milieu des outils de création — accord Quang 23h31), séparé des onglets de création, ouvert par défaut à la 1ʳᵉ visite. **Renommer** (✏ dans la série) = titre ET dossier (`slugify` copié de manga-fetch, sinon la prochaine capture sous le nouveau titre fonde un 2ᵉ dossier) + `manifest.json` de chaque chapitre + champ `chapitre` des narrations + chemins des couvertures de tomes dans `serie.json` ; refusé si le nom est pris ou si une capture / narration tourne (`proxy-patch/patch_renommer.py` + `.diff`). **Bloc de capture repliable**, état gardé. + v1.79.0 : détail des coûts visible depuis tous les onglets (la fenêtre vivait DANS Planche : cassée par la mémoire d'onglet v1.73.0), narrations supprimées toujours comptées, VRAM = mémoire UTILISÉE / 16 Go. Bancs : routes **36/36**, interface **64/64**. Piège payé : à 360 px, la règle `@media(max-width:700px)` placée plus bas annulait la règle mobile (même spécificité) ; un navigateur mobile ÉLARGIT la page au lieu de déborder (`innerWidth` = 366) — mesurer `right > 360`, pas `> innerWidth`. | | |
| ✅ **12-septies — FAIT v1.81.0 (21/09 23h55, sauf la recherche dans le TEXTE des narrations, à faire)** | **Recherche INTELLIGENTE dans la bibliothèque** (Quang 23h23 : « risque de se retrouver avec beaucoup de mangas ») : tolérante aux accents, à la casse et aux fautes de frappe ; cherche aussi dans les **titres alternatifs** (MangaDex `altTitles` : « Frieren » ↔ « Sousou no Frieren », « Lord of Destruction » ↔ « Hakaiou Noritaka »), numéros de chapitre et de tome ; plus tard, dans le **texte des narrations** (« le chapitre où Blue sort de son armure »). Filtre instantané pendant la frappe | retrouver vite dans une grosse bibliothèque | 1 faute de frappe tolérée ; titre alternatif trouvé |
|  | 📏 **Livré v1.81.0** : champ de recherche au-dessus des séries, filtre pendant la frappe ; sans accents / casse / ponctuation ; **1 faute tolérée (2 dès 8 lettres), inversion de 2 lettres = 1 faute** (Damerau — « freiren » ratait avec Levenshtein, trouvé par le banc) ; titres alternatifs MangaDex gardés dans `serie.json` (`proxy-patch/patch_titres_alt.py`, toutes langues : « Wanpanman », 「クレイモア」) ; nombres = chapitre ou tome ; chaque mot doit trouver sa place (« one punch 300 ») ; la raison s'affiche (« trouvé : autre titre : Sousou no Frieren »). Banc interface **90/90** (11 recherches réelles au clavier, dont 2 qui ne doivent RIEN trouver). | | |
| ✅ **12-octies — FAIT v1.83.0 (22/09 00h05)** | **Barre de temps du lecteur, cliquable et glissable** (Quang 21/09 23h57 : « cliquer sur la barre en bas pour avancer, reculer, se déplacer temporellement » — l'écoute dans l'app, PAS encore la vidéo) + **recherche dans le TEXTE des narrations** (fin de 12-septies). Barre = temps du CHAPITRE entier (durée mesurée de chaque page, 2,5 s pour une muette), « 3:12 / 9:45 », clic ou glisse au doigt (zone 18 px). ⚠️ **Piège payé** : le proxy ne gérait pas `Range` (200 + fichier entier) → Chrome ne peut PAS se positionner dans un MP3 : la barre sautait à la bonne PAGE mais l'audio repartait du DÉBUT de la page — invisible avec une vérification molle (« > 0,3 s »), trouvé en relisant les chiffres ; `proxy-patch/patch_range.py` → 206 + `Content-Range` + `Accept-Ranges`. Recherche texte : route `/manga/recherche_texte` (`patch_recherche_texte.py`), tous les mots sur la même page, un résultat par page, narrations avec voix d'abord, extrait affiché, clic = ouvre le chapitre. Bancs : lecteur **13/13** (point visé exact, PC + doigt 360 px), bibliothèque **90/90**. | | |
| ✅ **12-quater — FAIT v1.80.0 (21/09 23h45)** | **Renommer un titre de manga** (Quang 21/09 23h07) : ex. « Boruto-Tow blue vortex » → « Boruto: Two Blue Vortex ». Attention : le titre vit dans le `manifest.json` de CHAQUE chapitre ET dans le nom du dossier (slug) — renommer = mettre à jour les deux, sans casser les narrations (chemins relatifs) | titres propres | renommer depuis l'app, chapitres et narrations intacts |
| ✅ **11 b — FAIT v1.84.0 (22/09 00h55)** | **Traduire les dialogues d'un chapitre** : `scripts/traduire_chapitre.py <chap> --langue fr [--pages] [--engine gemini|kimi]` → `sources/<chap>/traduction/<langue>/page_NNN.png` + `traduction.json`. Détection YOLO + effacement OpenCV **réutilisés d'`ingest_page.py`** (non modifié) ; **un appel Gemini par page** (page entière + bulles découpées numérotées → texte, type, traduction) ; onomatopées **laissées telles quelles** (choix du 22/09, « je te laisse gérer ») ; pose Pillow Comic Neue (`scripts/fonts/`, OFL), largeur d'**ellipse** ligne par ligne, **taille commune** à la page (médiane), ponctuation insécable. **Mesuré sur Claymore p.1-20** : 102 bulles, **100 traduites**, 2 onomatopées gardées, 98 effacées en bulle + 2 en boîte, **2 « ne tient pas »**, **0,18 $ (0,009 $/page), 2 min 35**. Pixtral (ancien moteur de l'Ingestion) : 2 bulles / 7 ratées + markdown + faute sur p.5 → remplacé. **Pièges payés** : (1) `""` dans une chaîne Python NORMALE = `chr(1)` → les ? ! devenaient des carrés ; (2) une « bulle » effacée 6× plus grande que son texte = le FOND D'UNE CASE → la 1ʳᵉ version effaçait TOUTE la case (dessin perdu, p.9) ; (3) deux zones qui se chevauchent : garder la plus PETITE (la vraie bulle) ; (4) Gemini renvoie des retours à la ligne → Pillow refuse de mesurer. **Limites** : texte flottant hors bulle (p.19 « YOU, THERE! » : VO visible + traduction minuscule), quelques lignes frôlent le bord. ~~RESTE : appliquer les patchs…~~ → ✅ **v1.84.0** : routes `/manga/traduire` + `/manga/traductions` (`proxy-patch/patch_traduction.py` + `.diff`, testées 9/9 sur une instance 8191 puis sur le 8190) ; bouton « Traduire les dialogues » + langue, sélecteur « Afficher les pages : VO / français » appliqué à la grille, la visionneuse ET le lecteur, mémorisé par appareil ; suivi « ⏳ page N/62 » pendant la traduction. Banc `scripts/test_traduction_ui.py` **32/32** (PC + 360 px, mutation vérifiée rouge). **Claymore ch.1 ENTIER traduit par le bouton de l'app** : 305 bulles, **294 traduites**, 11 onomatopées gardées, 3 « ne tient pas », **0,54 $ (0,009 $/page), 7 min 39**. Contrôle visuel p.30, 47, 54 : français naturel, dessin intact. 🟠 **Limite mesurée (constaté v1.84.0)** : des répliques que YOLO NE DÉTECTE PAS restent en VO (p.47 « SPARE ME! », p.54 « YEAH, I HEARD. », p.19 « YOU, THERE! ») — elles n'entrent même pas dans la liste envoyée à Gemini. **Piste** (non codée) : Gemini voit déjà la page entière → lui demander aussi « les textes hors des zones numérotées » avec une boîte approximative, puis effacer/poser comme une boîte. Autre défaut : quelques textes très petits (p.54 « INCROYABLE… », zone détectée plus étroite que la bulle). |  |  |
| 11 (rappel) | **Traduction des textes selon la langue choisie** (Quang 21/09 23h00) : déjà l'étape 11 (b) — pages relettrées dans la langue définie (ex. Claymore, en anglais → français). | | |
| — | **Mode Lecture avancé** (précisé par Quang 21/09) : case par case, texte masqué, chaque réplique lue par la **voix de son personnage** | réutiliser le multi-voix de StoryVoice / smart-reader (pré-casting éditable, v0.21) ; Magi fournit OCR + ordre des bulles | après l'étape 1-bis (exige des attributions sûres) |

## 4-quinquies. FEUILLE DE ROUTE — BIBLIOTHÈQUE : masquer, trier, filtrer *(23/09/2026, cible v2.6.0)*

> Demande Quang (23/09, 12h42-12h44) : *« un système de filtres dans la bibliothèque en page principale, filtré par genre
> ou autre chose, tout affiché bien sûr ? […] un système de rangement aussi personnalisé ? Si j'ai envie d'exclure certains
> mangas […] l'autre session travaille sur d'autres choses, cela permet de ne pas créer et supprimer à chaque fois. Ainsi,
> je garde ma bibliothèque propre à moi. »* — puis *« je vais en ajouter des mangas, c'est sûr »* (donc les filtres par
> genre MAINTENANT, pas « à 20 séries ») — puis *« prends le temps de bien regarder tous les détails […] l'ergonomie
> également, et tu traces une feuille de route bien détaillée […] et tu suis »*.
> ⏸ **Contrainte du moment (12h44)** : *« on ne déplace rien parce que l'autre session est en train de finir »* (Vidéo
> Studio, série `black-jack-ni-yoroshiku`). ⇒ **Aucune écriture sur `sources/`, aucune relance du proxy, aucune
> modification de `manga_studio.html` servi, tant que Quang n'a pas dit que c'est libre.** Déclencheur de reprise : son feu vert.
> ✅ **Feu vert donné le 23/09 à 13h10** (« l'autre session a fini »).
> ✅ **LIVRÉ le 23/09 ~13h45 — v2.6.0** (toutes les étapes N1-N2, B1-B7). Mesures : narration EN créée à côté de la FR
> (FR identique octet pour octet) · garde-fou CJK 6/6, 0/661 pages existantes touchées · fiche MangaDex : 5 séries gardent
> leur id, Black Jack → la BONNE série (l'ancien code aurait pris « Shin-Black Jack », la suite EXCLUE de la licence) ·
> genres remplis sans autre changement (OPM : fiche complétée 2 → 17 chapitres) · bancs : `test_bibliotheque_perso_ui.py`
> 40/40 (PC + 360 px, chaque tri et chacune des 25 pastilles comparés au calcul du banc), `test_bibliotheque_api.py` 16/16
> (contre-épreuve rouge sur l'ancien proxy), caméra 29/29, vidéos fraîches 7/7, profil 17/17, lecteur 13/13.
> **En plus, à la demande de Quang (13h26)** : chapitres des cartes en plages (« ch. 295 → 311 ») et genres sur une
> ligne → cartes homogènes. Les bancs d'avant ne dépendent plus de copies laissées ni d'un n° de version en dur
> (`scripts/banc_outils.py`). ⚠️ `test_bibliotheque_ui.py` (v1.81) : 76/92 AVANT comme APRÈS ce chantier — données
> périmées (série de démo « Frieren » disparue, OPM passé de 2 à 17 chapitres) ; déclencheur : le réécrire au prochain
> chantier bibliothèque.
> ✅ **Retouches de Quang, même après-midi** : **v2.6.1** (13h43) la ligne « pas encore de pochette » quitte les cartes
> (au survol de l'image) + « Pochette officielle » essaie tous les titres connus (AniList répondait 404 sur la faute
> « Solo Levelng » ; `patch_pochette_titres.py`) · **v2.6.2** (13h52) les séries masquées derrière un bouton
> **« 👁 Masquées (N) »** à droite de « Filtres » (plus de section en bas de liste). Banc perso 40/40.
> **Reste ouvert (rien d'engagé)** : réécrire `test_bibliotheque_ui.py` (v1.81, données périmées) au prochain chantier
> bibliothèque ; filtres par genre pour les séries hors MangaDex (Pepper&Carrot) = pas de source, rien à faire tant que
> Quang ne le demande pas ; webtoon libre de droits (§ « Hors de ce chantier », déclencheur écrit).

### Constats (lus dans le code et mesurés le 23/09 — à re-vérifier si le code a bougé)

| Constat | Conséquence pour le design |
|---|---|
| `sources/<serie>/serie.json` porte `mangadex_id`, titres, années, statut, tomes (5 séries sur 6 ; pas Black Jack). | Les genres viennent de **MangaDex** (gratuit, sans compte) : `GET /manga/<id>` → `attributes.tags[]` (groupes `genre` 25, `theme` 38, `format`, `content`) + `publicationDemographic` (shounen, seinen…). Vérifié sur Claymore : Action, Aventure, Fantasy, Horreur, Tragédie + thèmes Démons, Monstres, Surnaturel ; shounen. |
| `manga_serie_infos` (proxy) **réécrit `serie.json` en entier** à chaque rafraîchissement. | ⛔ Un choix « masquée » NE va PAS dans `serie.json` (il serait effacé) → fichier dédié `sources/_bibliotheque.json`. |
| `manga_serie_infos` retrouve la série **par le 1ᵉʳ résultat** de la recherche MangaDex par titre, et ne réutilise pas un `mangadex_id` déjà connu. | ~~🔴 Mesuré~~ → ✅ **couvert par v2.6.0 (B1)** : id connu réutilisé, sinon titre exact, sinon rien n'est écrit. Constat d'origine : « Black Jack ni Yoroshiku » → 1ᵉʳ résultat = une AUTRE série (« Kurokami Seiso… ») ; la bonne (« Give My Regards to Black Jack », `9fca3c19…`) est 3ᵉ, et la suite exclue de la licence (« Shin-Black Jack ») 2ᵉ. ⇒ (a) réutiliser l'id déjà connu ; (b) choisir le résultat dont un titre ou titre alternatif correspond **exactement** (normalisé), sinon ne rien écrire et le dire. |
| `/manga/sources` renvoie déjà `serie_info` (tout `serie.json` sauf `chapitres`) avec chaque chapitre. | Les genres arrivent dans l'app **sans nouvelle route** dès qu'ils sont dans `serie.json`. |
| La liste des séries (`renderLib`) suit l'ordre des chapitres renvoyés par le proxy ; recherche intelligente existante (`chercherSerie`, titres alternatifs, 1 faute tolérée). | Le tri et les filtres se posent **à côté** de la recherche, et se combinent avec elle. |
| Préférences d'affichage déjà mémorisées par appareil (`localStorage` : série ouverte, vue traduction…). | Tri + filtres = **par appareil** (c'est une vue). Masquage = **commun à tous les appareils** (c'est « ma bibliothèque »). |

### Décisions d'ergonomie (proposées par Claude, cadre posé par Quang)

1. **Masquer ≠ supprimer.** Une série masquée disparaît de la page principale, de la recherche et des filtres ; elle reste
   intacte et utilisable par tout le reste (vidéos, lot, nuit, autre session). Bouton **« 🙈 Masquer »** dans la barre de
   la série ouverte ; ~~en bas de la liste, une ligne discrète **« 👁 Séries masquées (N) »** qui les déplie~~ → **décision
   Quang 23/09 (v2.6.2)** : bouton **« 👁 Masquées (N) »** à droite de « Filtres », qui bascule la liste sur les séries
   masquées (retour par « ← Ma bibliothèque »), chacune avec **« Ré-afficher »**. Pas de confirmation pour masquer (réversible en un geste) ; un toast le dit.
   Une recherche qui ne trouve rien parmi les visibles mais trouve une masquée l'indique (« 1 résultat dans les séries masquées »).
2. **Trier** : un menu compact **« Trier : Récemment ajoutée · Récemment ouverte · A → Z »**. Défaut = récemment ajoutée
   (date de capture du chapitre le plus récent). « Récemment ouverte » = mémorisée côté PC (commune aux appareils).
   Pas de rangement à la main (glisser-déposer) : lourd à faire et à entretenir — **déclencheur pour y revenir** : Quang le redemande.
3. **Filtrer** : un bouton **« Filtres (n) »** à côté du tri ouvre un panneau de pastilles :
   **Genres** (MangaDex, traduits en français) · **Public** (shōnen, seinen, shōjo, josei) · **Statut** (en cours, terminé) ·
   **Thèmes** (repliés sous « + thèmes », ils sont nombreux). Plusieurs pastilles = la série doit les avoir **toutes**
   (on resserre, comme la recherche où chaque mot doit trouver sa place). Seules les pastilles **présentes dans la
   bibliothèque** sont proposées, avec leur nombre (« Action 4 ») : jamais un filtre qui ne mène à rien.
   Les filtres actifs restent visibles sous la barre (pastilles avec ✕ + « Tout effacer ») ; la ligne d'état dit
   « 3 / 7 séries ». Une série sans genres connus reste visible tant qu'aucun filtre de genre n'est actif.
4. **Téléphone d'abord** (360-480 px) : barre sur une ligne (recherche) + une ligne (Trier · Filtres) ; le panneau de
   pastilles s'ouvre sous la barre, pastilles qui passent à la ligne, cibles ≥ 36 px ; aucun débordement horizontal.

### Étapes (dans cet ordre ; une étape = un commit qui la nomme)

| # | Étape | Définition de « fini » |
|---|---|---|
| ✅ N1 | **Narration en anglais depuis l'app** (remontée Vidéo Studio 23/09, **confirmée dans le code**) : `manga_narrate` (proxy) impose l'étiquette `moteur-voix` et ne transmet jamais `--langue` → impossible de narrer en anglais depuis l'app, et ajouter la langue sans changer l'étiquette ÉCRASERAIT la narration française. Le proxy accepte `langue` (liste blanche = celle du script) et nomme `moteur-voix-<langue>` hors français (comme `narrate_chapter.py`) ; l'app propose la langue de la narration. | Banc : narration EN lancée depuis l'app → dossier `…-en` créé, la FR intacte (octets identiques) ; FR inchangée sans le paramètre. |
| ✅ N2 | **Garde-fou avant la voix** (remontée Vidéo Studio : « un nom en kanji fait dérailler la voix française », vu avec Kimi) : **non reproduit** le 23/09 (0 caractère japonais dans les textes LUS de toute la bibliothèque ; les kanji ne sont que dans les notes internes de lecture) — mais rien ne l'empêche. Juste avant la synthèse vocale : tout caractère CJK du texte à lire est retiré (entre parenthèses compris), la page le note dans le journal. 0 $. | Banc : un texte avec « Saitô (研修医) » → lu sans le kanji ; un texte sans CJK → strictement identique ; mutation rouge. |
| ✅ B1 | **Proxy — fiche de série fiable** (`patch_bibliotheque_genres.py`) : `manga_serie_infos` réutilise le `mangadex_id` connu ; sinon choisit le résultat au titre exact (normalisé, titres alternatifs compris), sinon ne touche à rien et renvoie l'erreur ; ajoute `genres`, `themes`, `public`. | Banc : les 5 séries existantes gardent leur id ; Black Jack → « Give My Regards to Black Jack » (`9fca3c19…`), jamais « Shin- » ; une série introuvable → erreur, `serie.json` intact. `.bak` de chaque `serie.json` avant. |
| ✅ B2 | **Proxy — `_bibliotheque.json`** : `GET /manga/bibliotheque` → `{masquees:[slug], ouvertes:{slug:ts}}` ; `POST {action: masquer|afficher|ouverte, slug}` (slug validé, écriture atomique `.tmp` + `os.replace`). | Banc API : masquer / afficher / ouverte, relecture après relance du proxy ; slug invalide refusé ; fichier absent = tout visible. |
| ✅ B3 | **Remplissage des genres des séries existantes** : à l'ouverture de la bibliothèque, une série avec `serie_info` mais sans `genres` est rafraîchie UNE fois (même mécanisme que les tomes). | Les séries ont leurs genres ; tomes, couvertures, dates inchangés (diff des `serie.json` : seules les clés ajoutées). |
| ✅ B4 | **App — masquer** (barre de la série + section « Séries masquées » + recherche qui le signale). | Banc UI : masquer → disparaît, compteur juste, ré-afficher → revient ; commun PC/téléphone (2 contextes de navigateur) ; la série masquée reste ouvrable (lien d'activité, lecteur). |
| ✅ B5 | **App — trier** (3 ordres, mémorisé par appareil ; « récemment ouverte » alimentée par `ouverte`). | Banc : les 3 ordres donnent l'ordre attendu, calculé indépendamment dans le banc ; survit au rechargement. |
| ✅ B6 | **App — filtres** (pastilles FR avec comptes, ET, pastilles actives, « Tout effacer », combinaison recherche + filtres + masquées). | Banc : pour chaque pastille, la liste affichée == le calcul du banc sur les données ; 2 pastilles = intersection ; 360 px sans débordement ; capture relue à l'œil. |
| ✅ B7 | **Clôture** : version **v2.6.0** aux 3 endroits, `node --check`, bancs existants (bibliothèque, recherche, profil, vidéos fraîches, caméra) verts, feuille de route + journal mis à jour, commit + push. | Tout vert, captures PC + téléphone contrôlées, rien d'écrit dans la bibliothèque de Quang hors `serie.json` (genres) et `_bibliotheque.json`. |

### Hors de ce chantier, mais à ne pas perdre

- ~~🟠 **Webtoon vertical libre de droits : introuvable** (Vidéo Studio, 23/09)~~ → **ÉTUDIÉ le 23/09 14h10 (Manga Studio,
  à la demande de Quang)**. Contrainte : libre de droits UNIQUEMENT, jamais de démarchage d'auteurs (Quang 23/09).
  Licences relues À LA SOURCE, pas sur la foi des 2 sous-agents web :
  - ✅ **Mini Fantasy Theater** (David Revoy) = le seul candidat « vertical natif » : **CC-BY-SA 4.0** (ligne de licence
    de chaque épisode, 001 et 073 relus), **73 épisodes** (dernier = 073, mesuré par dichotomie), **4 cases carrées
    séparées 1280×1280** (planche hi-res 3840×3840) → empilées = bande **1280×5120** sans recadrer ; **FR et EN**
    officiels. ⚠️ Gags courts, peu de texte (ép. 1 : un seul « BLOOP ») → narration plus inventive que lue.
    ⚠️ **ShareAlike** : la vidéo dérivée doit être publiée elle-même sous CC-BY-SA 4.0 (le dire dans la description).
    Crédit : « Art: David Revoy. Scenario: David Revoy » + peppercarrot.com.
  - ✅ **Pepper&Carrot** (CC-BY 4.0, déjà au stock) : pages, pas vertical → empilement (déjà fait : `pepper-carrot-vertical`).
  - ✅ **« Pepper&Carrot interdit l'IA » (mars 2026) ne nous concerne PAS juridiquement** : le Code de conduite dit
    *« This project does not allow contributions generated by LLMs »* — il vise les **contributions** au projet, la
    licence CC-BY reste inchangée (page licence relue : aucune mention d'IA). 🟠 Sensibilité de l'auteur à connaître :
    ne jamais faire passer ses planches dans un GÉNÉRATEUR d'images.
  - ✅ **KOGL type 1 couvre aussi les dessins** (kogl.or.kr : *« 영리 목적으로 이용할 수 있습니다 »*, *« 2차적 저작물로
    변경하여 이용 가능 »*, aucune exclusion par média) ; l'exclusion des images est propre au site korea.kr. Mais aucun
    webtoon narratif en type 1 trouvé (Séoul « 육아 레벨업 » = type 4 : NC + pas de modification). 🟠 Piste non épuisée :
    recherche filtrée sur 공유마당 (gongu.copyright.or.kr) — déclencheur : Quang veut plus de volume que Revoy.
  - 🟠 **CDC « Preparedness 101: Zombie Pandemic »** (2011) : domaine public (œuvre fédérale US, « Public Domain Mark
    1.0 » sur archive.org), vraie histoire en anglais, one-shot, pages classiques → empilement.
  - ❌ Webcomics « CC » grand public : tous NC ou ND (xkcd, Sandra and Woo, Diesel Sweeties… vérifiés par le sous-agent).
  **Rien d'importé ici** — tranché le 23/09 14h16 : la production (import, narration, vidéo, **masquage** dans la
  bibliothèque) revient à **Vidéo Studio** (Quang : « je préfère que ce soit VideoStudio qui gère tout ça ») ; la
  trouvaille est écrite dans son `manga-demo/STOCK.md` (commit `16bc58f`). Manga Studio n'intervient que si l'app bloque.

⚠️ **Pièges à ne pas repayer** : `serie.json` réécrit en entier (ne rien y stocker d'autre que MangaDex) · recherche
MangaDex par pertinence ≠ bon titre · `hidden` écrasé par un `display` CSS (piège payé 3 fois, cf. § 6 du 28/07) ·
une apostrophe dans une chaîne JS = tous les boutons morts (`node --check` après chaque édition) · le proxy est partagé
avec Generate Studio (relance UNIQUEMENT par `relance-proxy.ps1`, `.bak` avant patch).

## 4-sexies. FEUILLE DE ROUTE — TRADUCTIONS OPM + SITE manga-scantrad *(23/09/2026 21h55, demandée par Quang : « trace une feuille de route détaillée […] suis les étapes une à une »)*

> **Pourquoi** : remontée Vidéo Studio 21h50 — le stock One Punch-Man est BLOQUÉ (rien ne part), 1re publication
> prévue le **27/09**. Les 10 chapitres OPM sont en source **zh-hk** et traduits en français par `traduire_chapitre.py`
> v1.92.0. **Règle Quang** ([[feedback_systeme_fonctionne_sans_moi]]) : corriger le SYSTÈME (tous les chapitres, les
> suivants aussi), jamais « la page N » à la main.
> **Ordre** : T (traductions, urgent, date) → S (site manga-scantrad) → clôture. Une étape = un commit qui la nomme.
>
> ✅ **CLOS le 24/09 ~00h20** : T4 (OPM ch.1-10 retraduits en v1.96.0, **0 page blanche**, 1,90 $) + T5 (10 vidéos refaites avec leurs réglages ; contrôle 1 image / 10 s sur les 10 vidéos : **229 images, 0 écran blanc** ; ch.1 relu à l'œil : texte français, dessin intact) · A1 fini en **v2.8.4** (batch = ses chapitres + vidéos à venir, total FIXE ; « estimation en cours… » ; vague mémorisée sur l'appareil, vérifié dans l'app réelle : 10 vidéos en file → 0/10). **Limites acceptées** (Quang 22h28-22h29 : niveau convenable) : quelques textes posés petits ou mordant un peu sur le dessin ; ~8 textes encore en chinois sur les pages difficiles de OPM (encadrés verticaux) ; onomatopées dessinées gardées. **Déclencheur de reprise** : Vidéo Studio remonte un défaut FLAGRANT (page blanche, bulle entière non traduite).
>
> 📍 **ÉTAT au 23/09 23h50 (pour une reprise)** : ✅ T0, T1→T1-bis, T2+T2-bis (traduire_chapitre **v1.96.0**, `875e7b7`) ·
> ✅ NR (Black Jack fr/en, Noritaka : 0 blanche, minuscules inchangés) · ✅ S1 manga-scantrad (manga-fetch **v0.6.0**,
> `e4fb681`) · ✅ A1 compteur d'activité (app **v2.8.1**, `da7e355`) · ⏳ **T4 en cours** : `scripts/refaire_traductions.py
> one-punch-man 1-10` (journal `%TEMP%/t4.txt`) — retraduit ch.1-10 puis, si le contrôle est vert, met les 10 vidéos
> « pages fr » à la corbeille et les redemande avec leurs réglages (T5, file du proxy, ~1 h). **Reste** : vérifier T4/T5
> (controle_traduction.py one-punch-man 1-10 = 0 page blanche ; file vidéo vide), puis le texte de retour pour Vidéo Studio
> (étape C) et la mémoire. Anciennes traductions : `sources/_corbeille/*traduction__fr-avant-v196`.

### Constats (mesurés le 23/09 21h55, v1.92.0 — à re-vérifier si le code bouge)

| Constat | Preuve |
|---|---|
| 🔴 **Défaut 1 — pages devenues blanches** : **20 pages** (ch.1 p.12/18/22 · ch.2 p.9 · ch.3 p.1/7 · ch.4 p.11/16/23 · ch.6 p.1/11 · ch.7 p.1/6 · ch.8 p.1/11 · ch.9 p.7/10/11/18 · ch.10 p.22 ; ch.5 : 0). | Mesure maison (luminosité page traduite > 235 ET ≥ original + 15). La remontée oubliait le ch.3. |
| **Cause du défaut 1** (lue dans le code) : `ingest_page.clean_bubbles` remplit par diffusion depuis le pixel le plus clair du texte ; tant que la surface atteinte reste ≤ **18 % de la page**, c'est « une bulle » et TOUT est peint en blanc. Un petit texte posé sur un fond clair (titre collé au bord, ciel, décor blanc) blanchit donc un morceau de page — plusieurs par page = page blanche. Le garde-fou de `traduire_chapitre` (« bulle 6× plus grande que son texte = fond de case ») ne change que l'endroit où l'on ÉCRIT : l'effacement a DÉJÀ eu lieu. | ch.1 p.12, bulle 2 : « 一拳超人 » (titre), boîte 5,9 % × 1,9 %, `effacement: fond de case -> zone detectee`. |
| 🟠 **Défaut 2 — textes restés en chinois** : encadrés rectangulaires à texte vertical (pensées, narration) et cris ; bulles rondes mieux traitées. | Remontée (ch.2 p.10, ch.3 p.13, ch.4 p.11/16/22, ch.5 p.2/3/14) ; déjà noté v1.84 (« des répliques que YOLO NE DÉTECTE PAS restent en VO »). |
| 🟠 **Annexe** : effacement incomplet (restes chinois sous le français, ch.5 p.2 « l'épo ue ») ; textes réduits jusqu'à l'illisible (ch.1 p.12). | Remontée ; à mesurer en T3. |
| Ingestion (Studio) utilise AUSSI `clean_bubbles` : son comportement ne doit PAS changer. | `ingest_page.py` partagé. |

### Étapes

| # | Étape | Définition de « fini » (mesurée) |
|---|---|---|
| ✅ T0 | **Fait 22h05** : `controle_traduction.py` retrouve exactement les 20 pages ; (b) Gemini, 0,029 $ / 9 pages. | ✅ |
| ✅ T1 → T1-bis | **v1.93.0 PUIS corrigé en v1.96.0**. v1.93 (règle « 6× » à l'effacement) : 0 page blanche sur 73 (essai copies, 0,61 $) MAIS la mesure `mesure_fonds.py` a montré **28 vraies bulles de Black Jack** (texte vertical étroit) au-dessus du rapport 6 → texte posé en taille 8 (p.1 « 8千人 ») : régression que « bulles traduites » ne voyait pas. **v1.96.0** : effacement d'avant, et si la page est **blanchie à plus de 18 %** (pixels non blancs devenus blancs, hors boîtes de texte) elle est refaite en mode prudent. Mesure `mesure_blanchiment.py` : pages devenues blanches ≥ 22,5 % ; pages saines OPM / Black Jack / Noritaka ≤ 13,6 % → séparation nette. | essai v1.96 en cours |
| ✅ T2 + T2-bis | **v1.94-1.95** : textes hors bulles (Gemini) + contrôle de couverture (effacement < 50 % de la boîte = raté → boîte entière). OPM pages citées : chinois restant **16 → 8**, ch.2 p.10 et ch.5 p.2 traduites (vu à l'œil) ; NR : bulles traduites en hausse partout (BJ fr 91→99, en 93→97, Noritaka 129→144), 0 page blanche. T3 (texte qui déborde un peu, texte minuscule isolé) **non fait**, accepté (Quang 22h28 : niveau convenable, pas de polissage). | ✅ |
| T0 | **Banc de contrôle** `scripts/controle_traduction.py <serie> [chapitres]` : (a) pages blanches (règle ci-dessus) ; (b) lettres CJK restantes dans la page traduite — relecture Gemini d'UNE question par page (« reste-t-il du texte chinois/japonais/coréen hors onomatopées dessinées ? où ? »), coût noté ; (c) sortie chiffrée par chapitre. | Sur l'état actuel : (a) = les 20 pages ci-dessus, exactement. (b) trouve les exemples de la remontée. |
| T1 | **Défaut 1** : `clean_bubbles(..., ratio_max=None)` — si fourni et que la surface « bulle » dépasse `ratio_max` × la boîte du texte, on n'efface QUE la boîte (« fond ouvert → boîte seule »). `traduire_chapitre` passe `ratio_max=6` (le seuil qu'il utilisait déjà, trop tard). Ingestion : défaut `None` = inchangée. | Banc hors ligne (image synthétique : petit texte sur grand fond clair → seule la boîte blanchit ; vraie bulle fermée → bulle effacée comme avant) + mutation rouge ; les 20 pages retraduites → **0 page blanche** (T0-a). |
| T2 | **Défaut 2** : l'appel Gemini de chaque page (qui voit déjà la page entière) renvoie AUSSI les textes HORS des zones numérotées (`hors_zones` : texte, boîte approximative, type) ; ils sont effacés en « boîte » et traduits comme les autres, onomatopées dessinées gardées. | Sur les pages citées : les textes listés sont traduits ; T0-b en nette baisse, chiffrée avant / après. |
| T3 | **Annexe** : effacement « boîte » élargi (marge) pour le texte vertical dense ; taille minimale lisible (sinon « ne tient pas » + texte posé plus petit mais ≥ seuil, signalé). | ch.5 p.2 et ch.1 p.12 contrôlés à l'œil (captures relues). |
| NR | **Non-régression AUTRES langues** (Quang 21h55 : « ne crée pas de régression sur d'autres types de manga avec d'autres langues » ; vérifier sur la base existante, ne rien supposer). Sur des COPIES (`zz-`), retraduire un échantillon avec la nouvelle version et comparer à la traduction actuelle : **Black Jack ch.1-2** (japonais → fr et → en), **Noritaka ch.1** (anglais → fr), OPM (chinois, déjà couvert par T1/T2). | Par série : 0 page blanche ; bulles traduites ≥ avant (hors onomatopées) ; chaque texte « hors zones » ajouté relu à l'œil (vrai texte, bien placé) ; 3 pages par série comparées avant / après à l'œil ; sinon on corrige AVANT T4. |
| T4 | **Retraduire OPM ch.1-10** (≈ 224 pages × 0,009 $ ≈ 2 $) par le vrai chemin (script), anciennes traductions à la corbeille. | T0 : 0 page blanche, CJK restant chiffré et justifié (onomatopées), captures de 3 pages relues. |
| T5 | **Vidéos** : les vidéos qui montrent les pages traduites deviennent « à refaire » (empreinte traduction) → les refaire par la file. Prévenir Vidéo Studio (texte à transmettre par Quang). | File vide, vidéos à jour (badge ✅), 0 écran blanc (1 image / 10 s relue sur 2 vidéos). |
| S1 | **manga-scantrad.io** : capture VÉRIFIÉE le 23/09 (ch.200 : 13 bandes → 97 pages, dossier temporaire). Reste l'ENCHAÎNEMENT : adresses `vol-N` (volume entier : vol-1 = 193 bandes) et `vol-N-chapitre-M(-5)`. ❓ **Question à Quang** : numérotation d'un volume entier dans l'app (proposé : « ch. N » = volume N, noté « volume entier »). | Capture + suivant réels (dans un dossier temporaire, sur des chapitres que Quang n'a pas) ; `sites.json` mis à jour (règle du fichier). |
| ✅ A1 | **FAIT v2.8.0 (23h40)** — **Compteur d'activité** (Quang 22h14, capture du panneau Activité) : dans la pastille du haut et à droite de « Activité », **« 3 / 15 »** (terminées / total = terminées de la session + en cours + EN ATTENTE : file vidéo, chapitres restants d'un lot) et **« ~30 min / ~1 h »** (restant / total estimé = estimation de la tâche en cours, déjà calculée, + attente estimée : moyenne mesurée par type de tâche ou estimation du lot). Recalcul continu, arrondi, « ~ » assumé ; remis à zéro quand tout est fini. APRÈS les étapes T (date du 27/09). | Banc UI : compteur = calcul du banc sur l'état réel du proxy ; estimation qui décroît pendant une vraie tâche ; PC + 360 px. |
| C | **Clôture** : bancs verts, feuille de route + journal, mémoire, commit + push ; texte de retour pour Vidéo Studio. | — |

## 4-septies. CASES ENTIÈRES EFFACÉES (remontée Vidéo Studio 24/09 0h40) — traduire_chapitre v1.97.0

**Signalé** : 5 pages OPM (ch.3 p.7, ch.4 p.6/p.20, ch.5 p.8, ch.10 p.24) où le texte français est posé sur un grand blanc qui a remplacé le dessin. **Trouvé en mesurant** : 14 pages OPM touchées (dont **ch.1 p.24**, Saitama effacé, que Vidéo Studio croyait sain), + Noritaka p.23 et Black Jack ch.2 p.24.

| Cause (lue dans le code, prouvée page par page) | Correction v1.97.0 |
|---|---|
| **1.** `clean_bubbles` rebouchait TOUS les « trous » de la zone claire (les lettres) — or un personnage entouré de fond clair est aussi un trou : case entière blanchie. Le garde-fou « page blanchie > 18 % » ne le voyait pas : une case détruite pèse 5 à 15 % de la page. | `trous_dans_texte` : on ne rebouche que la partie des trous située dans la boîte du texte élargie de 25 %. |
| **2.** Les trous se cherchaient en remplissant l'extérieur depuis le pixel (0,0) : une zone claire qui coupe la page fait passer l'autre moitié pour un trou. | Remplissage depuis un cadre ajouté autour de la page. |
| **3.** Effacement « boîte entière » sur une boîte géante (ch.3 p.7 : zone de complément de 32 % de la page ; Black Jack ch.2 p.14 : 87 %). | `boite_max` 25 % (jamais d'effacement en boîte entière au-delà) ; zone de **complément** en boîte entière > 5 % = écartée. |

**Mesure** (critère Vidéo Studio : blocs 24 px blancs unis là où l'original avait du dessin, `scripts/mesure_cases_effacees.py`, rejouée sur les zones enregistrées) : pages > 16 % — OPM 12 → 3, Black Jack 1 → 0, Noritaka 2 → 0 ; 4 pages « empirent » de +0,5 à +1,2 pt, vérifiées à l'œil : équivalentes (aucun dessin perdu). Rendu final : **0 page > 20 %** sur OPM ch.1-10 (5 avant). Banc `test_effacement_fond.py` **16/16**, mutations rouges (M1 découpe, M2 plafond, M4 cadre). Ingestion inchangée (options à `False`/`None` par défaut).

**Livraison sans aucun appel** : `traduire_chapitre --rerendu` refait effacement + pose depuis `traduction.json` (mêmes zones, **mêmes textes** : 0 différence sur 902 bulles). `refaire_traductions.py --rerendu`. `controle_traduction.py` signale désormais les cases effacées > 20 % (non bloquant : OPM ch.5 p.3, grands encadrés légitimement blanchis, montait à 20,3 %).

**Limites ACCEPTÉES (décision Claude, 24/09)** : 10 répliques ne sont plus posées — ch.3 p.7 la légende « 我只是想成為世界最強的男人… » (zone mal détectée, 32 % de la page) et 9 **grands cris calligraphiés** (ch.4 p.1/p.17, ch.6 p.8/p.23, ch.7 p.5, ch.8 p.17, ch.10 p.12/p.29) : ils restent en chinois, comme les onomatopées dessinées, au lieu d'un rectangle blanc qui mangeait la case. La narration porte le sens. 🟠 (constaté v1.97.0) Les traductions Noritaka ch.1 (v1.91) et Black Jack ch.1-2 (v1.91/1.92) sont **antérieures** aux corrections v1.96-v1.97 (Noritaka p.54 et Black Jack ch.2 p.2 sont des pages blanches) : à refaire le jour où ces séries servent (`refaire_traductions.py <serie> <ch> --rerendu --version-min 1.97.0`).

## 4-undecies. DOUBLE ESTIMATION « ☁ EN LIGNE / 🖥 SUR MON PC » PARTOUT *(24/09/2026 14h13, demande Quang — ✅ LIVRÉ v2.12.0, 24/09 14h50)*

> Quang : *« dans les estimations de coût, au-delà du switch PC ou cloud, partout tu m'affiches les deux estimations de
> coût avant de générer quoi que ce soit […] ainsi que le temps de traitement […] dynamique selon le switch […] deux
> visus avec les mêmes couleurs, partout où je suis, même dans les chapitres ou dans les batchs […] j'ai juste à appuyer
> sur le bouton en haut à droite pour switcher. »*

### Spécification
- Avant CHAQUE lancement (narrer un chapitre, traduire, lot/batch du profil, vidéos) : **deux cartouches côte à côte**,
  aux couleurs de la pastille : **bleu ☁ En ligne** (coût $ + durée) et **orange 🖥 Sur mon PC** (coût $ + durée +
  « carte graphique occupée ~X min »). Le cartouche du **mode actif** est plein/encadré, l'autre estompé ; un clic sur la
  pastille en haut bascule, les cartouches suivent **immédiatement**.
- Chiffres = mesures réelles, pas des devinettes : coût par page mesuré (§ 4-nonies : analyse 0,0041 $, récit 0,0001 $,
  voix 0,0058 $ ; traduction ~0,006-0,012 $/page) ; voix locale ~1× temps réel (≈ 14 s d'audio par page OPM) ;
  effacement local 1-3 s/page. Idéalement recalculés depuis le REGISTRE des dépenses (sources/_depenses.jsonl) et les
  durées du journal, pour suivre la réalité.
- Point de départ dans le code : `lotEstimer()` (estimation du lot, profil) — l'étendre plutôt que dupliquer.

### Protection : basculer pendant qu'un traitement tourne (Quang 24/09 14h14)
> *« si quelque chose tourne, que je ne switch pas en plein milieu […] pas une sécurité qui empêche, mais une pop-up
> d'alerte, et c'est moi qui décide si je veux interrompre ou non […] gérer les effets collatéraux si je décide
> d'interrompre. Il faut que je sache exactement où j'en suis. »*
- Constat (code, 24/09) : le mode est lu **au lancement** de chaque traitement (narrate reçoit `--tts`, traduire
  `--effacement`, ~~la nuit relit `reglages.py` à CHAQUE chapitre~~) → ce qui tourne finit dans son mode ; seuls les
  chapitres SUIVANTS d'un lot / de la nuit changeraient.
  → 🔴 **FAUX pour la voix, relu dans le code le 24/09 14h35 (v2.11.0)** : le lot et la nuit lisaient le profil UNE fois
  au démarrage (`voix_moteur` figé), seule la traduction relisait l'interrupteur à chaque chapitre. Basculer en plein lot
  aurait donné des chapitres « voix en ligne + effacement local ». ✅ **couvert par suivi_nuit v2.5.0** : le mode est
  relu au début de CHAQUE chapitre, pour la voix comme pour l'effacement (banc `test_interruption.py`, point D).
- À faire : clic sur la pastille pendant une activité (`/manga/activite` non vide) → fenêtre : ce qui tourne (chapitre,
  étape), « le traitement en cours finit en ☁/🖥 », « N chapitre(s) restants du lot passeraient en 🖥/☁ » ; choix :
  **Basculer pour la suite** / **Annuler** / **Interrompre**. Interrompre = arrêt propre (tuer le process du chapitre en
  cours, retirer le reste de la file) puis **bilan exact** : chapitres finis, chapitre coupé + étape atteinte (l'analyse
  payée est gardée : `--reuse-vision` la reprend sans repayer), chapitres non commencés ; tout ce qui a été payé est
  déjà au registre des dépenses. Bouton « Reprendre » qui repart de là.
- Mémoriser dans chaque passage le mode avec lequel il a tourné (narration.json `tts`, traduction.json `effacement` :
  déjà écrits) → le bilan peut le dire.

### Livré — v2.12.0 (24/09 14h50) *(suivi_nuit 2.5.0 · estimation 1.0.0 · interruption 1.0.0 · reglages 1.1.0)*
**Double estimation.** `scripts/estimation.py` recalcule les chiffres sur les **passages réels** (médianes par page :
21 narrations Gemini, 3 Kimi, 12 traductions, 1 voix locale ; cache 1 h `sources/_etalonnage.json`, repli sur les mesures
du 24/09 sous 3 échantillons). Mesuré : Gemini ≈ 0,0100 $ d'analyse + 0,0066 $ de voix par page, 9,2 + 2,1 s ; Kimi
≈ 0,040 $ + 0,0069 $, 76 s ; traduction 0,0089 $ et 9,7 s par page ; voix sur le PC 0,078 s par caractère (≈ 17 s par
page). Les anciennes constantes surestimaient la durée Gemini (15 s/page annoncées). L'étalonnage part avec
`GET /manga/reglages` ; l'app calcule avec `estimChap()`, **miroir** de `estimation.chapitre()`.
Affiché : ☁ et 🖥 sur **une ligne compacte** (proposition de la session précédente, pour tenir à 360 px), mode actif
plein, l'autre estompé, 🖥 dit « carte ~X min » ; **Narrer**, **Traduire**, **Tout traiter** (lot du profil) et les
**confirmations** Traduire / Lancer (mode actif en premier). Un clic sur la pastille du haut : tout suit, sans recharger.
Le plan du lot côté serveur porte `estim: {cloud, pc}` ; `cout` / `minutes` = le mode actif.
**Protection.** Clic sur la pastille pendant une narration, une traduction ou un lot : question à l'écran (pas de boîte
native) avec ce qui tourne (le lot compté une seule fois), « ce qui tourne FINIT en ☁/🖥 », « N chapitre(s) restant(s)
passeraient en … », karaoké / vidéos / « Précédemment » non concernés. Trois choix : **Basculer pour la suite** ·
**Annuler** (Échap) · **Interrompre et basculer** → `POST /manga/interrompre` (proxy, diff
`proxy-patch/_studio_llm_proxy_interrompre_v2120.diff`, relancé par `relance-proxy.ps1`) → `scripts/interruption.py` :
l'étape puis le lot tués (arbre de processus), `progress.json` marqués « interrompu », état « interrompu » + journal,
**bilan** : ✅ finis · ❌ en échec · ✂ coupé à l'étape X (+ « analyse des pages gardée ») · ⏸ pas commencés. Bouton
**▶ Reprendre** : relance le lot sur (coupé + pas commencés) ; le chapitre coupé **relit son analyse dans son dossier
d'origine** même si le mode a changé (dossier `-local`) et même en « refaire » ; une narration lancée seule est relancée
avec `reuse` si son analyse était finie. Une tâche coupée n'apparaît plus comme « ✓ finie » dans l'activité (défaut vu
sur la capture du banc, corrigé).
**Bancs** : `test_estimation.py` VERT (320 cas app = serveur ; 2 mutations rouges) · `test_estimation_ui.py` 19/19
(1280 + 360 px, 0 appel payant) · `test_interruption.py` 17/17 (isolé, vrais processus factices ; 2 mutations rouges) ·
`test_interruption_ui.py` 18/18 (faux lot dans l'app réelle, état + journal + interrupteur restaurés à l'identique,
« Reprendre » intercepté ; mutation « coupé ≠ fini » rouge) · non-régression `test_alertes_ui` 18/18, `test_moderation`
21/21 · plan à blanc Claymore ch.2-3 (358 p.) : ☁ ≈ 6 $ / ~2 h ; 🖥 ≈ 3,58 $ / ~3 h 15.
| Avantages | Limites (connues) |
|---|---|
| Les deux prix et les deux durées avant chaque lancement, sur tes chiffres réels | Voix locale étalonnée sur **1 seul** passage (OPM ch.1) : le chiffre 🖥 s'affinera à chaque narration locale |
| Basculer en plein lot ne mélange plus voix et effacement | Karaoké / « Précédemment » / vidéo : valeurs fixes (pas encore mesurées sur les passages) |
| Interrompre ne jette rien de payé ; bilan exact + reprise en un clic | Narration seule reprise sur **tout** le chapitre (une plage de pages demandée n'est pas mémorisée) ; traduction coupée : à relancer à la main |
| | « Précédemment », karaoké, vidéo : pas encore de double estimation à l'écran (identiques dans les deux modes, sauf la vidéo qui est toujours sur le PC) |

### Propositions critiques ouvertes (Claude, 24/09) — décision de Quang attendue
1. ✅ **FAIT le 24/09 (§ 4-terdecies)** : réflexion minimale sur le repérage, −48 % sur analyse+noms, fidélité inchangée. Ancien texte : ~~**Repérage des personnages = 4,43 $ du mois** (presque autant que l'analyse, 5,04 $) : chaque page passe plusieurs fois
   pour un vote. Mesurer 1 passage au lieu de N, ou seulement sur les pages avec un visage (fidélité des noms avant/après,
   même banc que le 21/09). Gain estimé 2-3 $/mois. **Déclencheur** : Quang dit « go » ; sinon au prochain lot > 5 $.~~
2. **Reprendre l'analyse d'une narration EN LIGNE quand on refait le même chapitre EN LOCAL** (aujourd'hui seulement
   pour un chapitre coupé) : l'analyse est identique dans les deux modes → refaire OPM en 🖥 coûterait ~0 $ au lieu de
   ~0,01 $/page. **Déclencheur** : première demande « refais ce chapitre sur le PC ».
3. **Essai de modération RÉEL** (bancs = refus simulés, § 4-decies) sur les pages les plus dures de Claymore — toujours
   ouvert. **Déclencheur** : prochain chantier modération ou premier refus réel constaté au journal.

### État du chantier moteurs locaux / modération à la coupure (24/09 14h15) — « fait » = `git log`
- ✅ v2.10.0 voix locale · v2.11.0 alertes de modération (bouton d'activité, onglet « À traiter ») + interrupteur global
  (`scripts/reglages.py`, `sources/_reglages.json`) · traduire 1.99.0 (effacement local, refus → VO + alerte) · narrate 2.7.0
  (refus → page mise de côté, `--reprendre-moderation`) · video_chapitre 1.98.0 (alerte ouverte → code 4, « attente
  modération ») · registre des dépenses `sources/_depenses.jsonl` (compteur réparé : mois ≈ 46,5 $).
- Bancs : test_moderation 21/21 · test_alertes_ui 18/18 · non-régression verte (série vide, musiques, capture, profil musique).
- 🟠 Non testé en réel : un VRAI refus de Gemini (bancs = refus simulés) → essai prévu sur les pages les plus dures de
  Claymore ; le traitement « Autre moteur / Pages voisines / Local » depuis l'app (route testée seulement pour « Ignorer »).
- ~~⬜ Reste : 4-undecies (cette section)~~ → ✅ v2.12.0 ; bouton « Effacement local » n'est plus nécessaire (l'interrupteur le pilote) ;
  refaire les pages OPM avec l'effacement local si Quang le veut (`--rerendu --effacement local`, 0 $).

## 4-quaterdecies. COMPARTIMENT SECRET *(24/09/2026 16h01-16h04, demande Quang — ✅ S0 → S8 LIVRÉS le 24/09 17h20-21h20, v2.15.0 → v2.25.0)*

> Quang : *« un compartiment secret qui aura exactement la même fonction que l'application actuelle, mais caché sous un
> déclencheur, par exemple rester appuyé sur le bouton de la bibliothèque […] avec des mangas plus sensibles […] sa
> propre fenêtre Edge […] je pourrais te donner un ou deux chapitres d'essai […] après que tu aies fini tout ce que tu
> es en train de faire et créé un compartiment secret fonctionnel. »* Puis (16h04) : *« une gestion intelligente pour
> éviter que je lance des processus des deux côtés […] que j'aie la vue quand même, même si je ne suis pas dedans. »*

**Décisions de Quang (24/09 16h03)** : accessible **PC ET téléphone** ; entrée par **appui long seul** (pas de code).
**Conception proposée (Claude)** :
1. **Séparation PHYSIQUE, même code** : un dossier de données à part (hors `sources/`), une **2ᵉ instance du serveur**
   qui ne voit que lui (port dédié), la même `manga_studio.html`. Rien de l'espace secret ne peut fuir dans l'app
   normale (activité, coûts, alertes, vidéos, « récemment ouvertes », nuit, cache hors ligne) puisqu'elle ne le voit pas.
   ⚠ Précédent connu : une 2ᵉ instance COMPLÈTE du proxy relancerait pod watchdog + notifs Telegram → n'importer que le
   gestionnaire HTTP. Tous les scripts doivent lire la racine des données par variable d'environnement (aujourd'hui
   `../sources` en dur).
2. **Accès** : PC = fenêtre Edge dédiée (profil séparé : historique et cache isolés) ; téléphone = **sous-domaine dédié
   derrière Cloudflare Access** (règle apps perso), même politique que l'app. L'appui long sur 📚 ouvre l'autre adresse.
3. **Vue croisée, discrète** (16h04) : chaque espace voit que l'autre travaille — côté normal **sans aucun titre**
   (« 🔒 1 traitement en cours · étape · reste ~X min ») ; au lancement, si l'autre espace travaille, la même question à
   l'écran que pour le changement de mode (lancer quand même / annuler) ; la jauge VRAM montre les moteurs quel que soit
   l'espace ; pastille des coûts = total des deux, détail des titres seulement dans l'espace qui les possède.
3-bis. **Tout ce qui tourne est visible** (Quang 16h53 : « je ne vois pas de témoin d'activité ») : aujourd'hui le témoin
   ne voit que `traduction/<langue>/` et `narration/<tag>/` ; les essais (`--sortie`, `_banc_reflexion/`) et les scripts
   lancés hors de l'app tournent sans témoin (la jauge VRAM, elle, les voit). À faire avec la vue croisée : un registre
   commun des traitements vivants (même principe que `sources/_gpu/`), étiquette « 🧪 essai », quel que soit l'espace.
4. **Chaîne sans modération** (§ 4-decies « contenu adulte ») à bâtir sur les chapitres d'essai de Quang : voix locale,
   traduction locale (Qwen3-30B, 90 % vs 94 %), analyse = le point dur (locale 16/30 vs Gemini 21/30) — mesurer d'abord
   si Gemini refuse vraiment.
5. **Dépôt `App` PUBLIC** : le code oui, **jamais un titre ni un chemin de série secrète** dans la feuille de route, le
   journal ou un commit. Limite posée par Claude : personnages adultes uniquement.
6. ~~**Paravent à l'ouverture** (Quang 16h06)~~ → **remplacé** (Quang 16h13) : chaque fenêtre (capture, normale, secrète) s'ouvre
   d'office à SA place discrète (sur le côté, en partie hors de l'écran) + boutons « Ranger » / « Taille sûre » / « Retenir » ;
   plus de fenêtre qui en cache une autre. Principe livré pour la fenêtre de capture en v2.14.0. Ancien texte : : quand la fenêtre Edge SECRÈTE s'ouvre sur le PC par le déclencheur de
   l'app (Quang devant le PC ou à distance), la fenêtre de l'app NORMALE est ramenée au premier plan, DÉPLIÉE (pas
   réduite), par-dessus — lancée d'abord si elle n'existe pas. **Au moment de l'ouverture seulement** ; ensuite, les
   gestes manuels sont ceux de Quang. ⚠ Verrou de premier plan de Windows (SetForegroundWindow refusé à un processus
   non actif) : la méthode se choisit en le TESTANT à l'écran (compter les fenêtres visibles, ordre Z), pas en supposant.
7. **Bouton « remettre en place »** (Quang 16h07) : depuis l'app, PC ou téléphone, à tout moment : la fenêtre normale
   repasse devant la secrète. **Taille** (question Quang) : passer devant ne dépend pas de la taille, mais CACHER exige
   de RECOUVRIR → le paravent (ouverture + bouton) **cale la fenêtre normale sur le rectangle exact de la secrète**
   (position + taille), recouvrement garanti quelle que soit la taille choisie ; aucune des deux réduite.
**Propositions Claude (Quang 16h06 : « ouvert à toutes les recommandations ») — à trancher au moment de construire** :
titre + icône de la fenêtre secrète IDENTIQUES à l'app normale (barre des tâches / Alt+Tab ne distinguent rien) ·
contenu FLOUTÉ dès que la fenêtre perd le focus (aperçus Alt+Tab / barre des tâches illisibles) · bouton PANIQUE
(ex. Échap ×2 → app normale) · retour automatique à l'app normale après N min d'inactivité · aucun titre secret dans
Telegram, notifications ou journaux · un déclenchement depuis le TÉLÉPHONE n'ouvre RIEN sur le PC.
**Déclencheur** : ~~fin des chantiers en cours~~ → chantier coûts CLOS le 24/09 17h15 ; **Quang : « on fait le découpage et la
feuille de route » (17h16) → la PROCHAINE SESSION construit, étape par étape, dans cet ordre.**

### Découpage (24/09 17h20) — une étape = un commit qui la nomme ; « fait » = `git log`
Mesuré avant de découper : **22 scripts** + `manga-fetch` écrivent dans `../sources` en dur ; le proxy y fait **29 références**
(`MANGA_SOURCES = MANGA_ROOT/sources`, ligne ~7475) ; il sert tout par une classe `H` (`ThreadingHTTPServer((host, port), H)`).
- **S0 — Une seule racine de données, réglable** : `scripts/racine.py` (`SOURCES = os.environ.get("MANGA_SOURCES_DIR") or
  ../sources`) importé par les 22 scripts + manga-fetch ; proxy : `MANGA_SOURCES` lu depuis la même variable (1 ligne,
  diff versionné). **Fini quand** : sans la variable, TOUT est identique (non-régression : `test_estimation`,
  `test_interruption`, `test_alertes_ui`, `test_moderation`, `test_vram_ui`, un lot à blanc `suivi_nuit --dry`) ; avec
  la variable pointée sur un dossier jetable, un chapitre importé y atterrit et nulle part ailleurs (banc dédié).
  ✅ **FAIT 24/09 17h35** : 18 scripts + manga-fetch + proxy (1 ligne, `proxy-patch/_studio_llm_proxy_racine_s0.diff`)
  lisent `MANGA_SOURCES_DIR`, repli sur `../sources`. Pas de `racine.py` importé : le proxy charge `video_chapitre.py`
  par `spec_from_file_location` sans `scripts/` dans le chemin → un `import racine` y casserait ; la même expression est
  donc écrite dans chaque ligne. Le proxy transmet son environnement à tous les scripts qu'il lance (`dict(os.environ…)`
  partout, vérifié). Banc `test_racine.py` **47/47** (20 lignes × sans/avec + import réel, alerte et dépense dans un
  dossier jetable, vrai `sources/` inchangé) ; mutation → rouge, partie B **sautée** si A échoue (sinon elle écrirait
  dans les vraies données). Non-régression : `test_estimation` 320 cas 0 écart, `test_interruption` 17/17,
  `test_moderation` 21/21, `test_alertes_ui` 18/18, `test_vram_ui` 10/10, `test_bibliotheque_api` 16/16, plan de lot
  `suivi_nuit --dry` identique avant/après ; proxy relancé par `relance-proxy.ps1`.
  🟠 **Hors racine, à traiter plus loin (constaté 24/09)** : les journaux de manga-fetch (`%LOCALAPPDATA%/manga-fetch/
  fetch.log`, `events.log`) et `%LOCALAPPDATA%/manga-studio/capture_run.log` sont COMMUNS aux deux espaces et portent
  des titres → S6 ; le profil Edge de capture aussi → S3 ; `dataset_*` et `output/` restent sous `MANGA_ROOT` (hors
  périmètre : l'espace secret n'ingère pas de dataset).
- **S1 — La 2ᵉ instance** : `espace_prive.py` = n'importe QUE la classe `H` du proxy (⚠ jamais une 2ᵉ instance COMPLÈTE :
  elle relancerait pod watchdog + notifs Telegram), `MANGA_SOURCES_DIR` = dossier secret **hors du dépôt et hors de
  `sources/`** (ex. `C:/Users/quang/Documents/MangaStudio-donnees/prive`), port dédié (~~8191~~ → **8192** : 8191 est
  déjà pris par le banc `scripts/proxy_8191.py`, constaté 24/09). Tâche planifiée au démarrage
  de session comme le proxy. **Fini quand** : `http://127.0.0.1:8191/manga/` sert l'app, bibliothèque VIDE, et une capture
  de test faite par 8191 n'apparaît PAS sur 8190 (et inversement).
  ✅ **FAIT 24/09 17h45** : `scripts/espace_prive.py` v1.0.0 (port **8192**, 127.0.0.1, données
  `C:/Users/quang/Documents/MangaStudio-donnees/prive` — sur C:, refus s'il pointe dans le dépôt, refus si le proxy
  ne lit pas la variable ; journal de capture à part `capture_run_prive.log`). Vérifié : importer le proxy ne lance
  AUCUN fil (tout est sous `__main__`). L'app ouverte sur 8192 parle à 8192 (`location.origin`, stockage local propre
  à l'origine). Tâche planifiée **`MangaStudioInstance2`** (nom neutre ; ouverture de session + toutes les 10 min,
  `lancer_espace_prive.vbs` → `.ps1`, relance seulement si 8192 muet ; journal `%LOCALAPPDATA%/manga-studio/
  espace_prive.log(.vie)`) : coupée → relancée, 2ᵉ déclenchement → pas de doublon. Banc `test_espace_prive.py`
  **15/15** (même app servie ; import réel de chaque côté, invisible de l'autre dans les deux sens ; une écriture du
  serveur privé — bibliothèque — reste dans le dossier privé, la normale inchangée à l'octet). Mutation (instance
  qui ignore la variable) → rouge et **arrêt avant toute écriture** ; bibliothèque normale intacte (empreinte).
  🟠 **Constaté 24/09, pour S3** : la fenêtre Edge de capture (CDP 9223, profil `manga-fetch-edge`) et
  `%LOCALAPPDATA%/manga-fetch/events.log` restent COMMUNS → deux captures simultanées se marcheraient dessus.
  ⚠ Pièges : l'instance = **2 PID** (lanceur du venv + enfant) ; l'ancien `ComfyUI/stop-secret-studio.ps1`
  (Generate Studio, juin) tue tout Python du venv ComfyUI, donc le proxy 8190 ET l'instance 8192.
- **S2 — L'app sait dans quel espace elle est** : `/manga/espace` → `{"espace": "normal"|"prive"}` ; titre et icône
  IDENTIQUES dans les deux (barre des tâches / Alt+Tab muets) ; une discrète marque visible seulement DANS l'espace
  secret (Quang doit savoir où il est). **Appui long sur 📚 Bibliothèque** (≥ 1,2 s, pas de clic simple) → ouvre l'autre
  espace ; rien d'autre ne le trahit (pas de menu, pas d'aide qui en parle dans l'espace normal).
  ✅ **FAIT 24/09 17h58 — v2.15.0** : proxy `/manga/espace` → `{espace, autre}` (`MANGA_ESPACE`, `MANGA_AUTRE_URL` ;
  diff `proxy-patch/_studio_llm_proxy_espace_s2.diff`) ; `espace_prive.py` v1.1.0 : `MANGA_ESPACE=prive`, **sa propre
  base** (`STUDIO_DB_PATH` → `prive/_studio_content.db` : Planche/Projet/Personnages étaient COMMUNS via SQLite,
  constaté 24/09), **sa propre galerie** (`MANGA_OUT` → `prive/_output`), et **la clé exigée comme sur 8190**
  (`STUDIO_SECRET` : sans elle le loopback serait ouvert à tout le futur tunnel de S4 — constaté : 8192 répondait sans
  clé). App : marque = badge de version en pointillé + « · », seulement dans l'espace privé ; appui long 1,2 s sur 📚
  → l'autre espace (PC : l'autre port, la clé suit en `#k=` puis quitte l'URL ; téléphone : `autre` fourni par le
  serveur, **vide jusqu'à S4 → le geste ne fait rien**) ; clic simple inchangé ; le chemin direct Wi-Fi (Caddy →
  8190) est **coupé dans l'espace privé** (il enverrait des requêtes de l'espace privé au serveur normal). Banc
  `test_espace_ui.py` **29/29** (1280 et 360 px). 🟠 Reste commun (hors usage de l'espace privé) : `dataset_*` sous
  `MANGA_ROOT` (entraînement LoRA). 🟠 Quang 17h57 : « sur mon PC ça ne fait rien » — à confirmer : page non
  rechargée (v2.14.1) ou ouverte par l'adresse du tunnel (geste inactif jusqu'à S4).
- **S3 — Fenêtre Edge dédiée à l'espace secret (PC)** : profil Edge séparé (historique/cache isolés), ouverte à SA place
  discrète (même mécanique que la fenêtre de capture v2.14 : `fenetre.json` propre, boutons Ranger / Taille sûre /
  Retenir / **Fermer à distance**), jamais d'ouverture sur le PC quand le déclenchement vient du téléphone.
  ⛔ **Exigence Quang (24/09 17h28)** : à sa 1ʳᵉ ouverture, **STOP** — Quang place lui-même la fenêtre, de façon
  discrète, et la retient ; Claude ne s'en sert (capture, banc) **qu'après**.
  ✅ **FAIT 24/09 18h55 — v2.16.0 → v2.17.0** (vocabulaire Quang 18h41 : **application principale** / **application
  secondaire**). (1) Fenêtre de CAPTURE de la secondaire : CDP **9224**, profil `manga-fetch-edge-2`, journaux et place
  `%LOCALAPPDATA%/manga-fetch-2/` (manga-fetch 0.6.5 + `cdp_mini` lisent `MANGA_CAPTURE_PORT/_DONNEES/_PROFIL`) ; placée
  par Quang puis retenue (les DEUX fenêtres de capture, chacune dans son fichier). Banc `test_fenetre_espace.py` 10/10.
  (2) Fenêtre de l'APP secondaire sur le PC : `fenetre_espace.py` + route `/manga/espace_fenetre` (CDP 9225, profil
  `EdgeApps/MangaStudio-2`) ; l'appui long l'ouvre depuis la principale et la ferme depuis la secondaire ; carte « Cette
  fenêtre » (Ranger / Retenir / Fermer) seulement dans la secondaire ; **jamais d'ouverture pour une demande relayée**
  (tunnel / Caddy), fermer à distance oui. (3) 🔴 **Constaté** : Edge connectait d'office chaque nouveau profil au compte
  Microsoft avec synchro COMPLÈTE (historique vers tous les appareils) → profils de la secondaire recréés sans connexion
  ni synchro (préférences forcées + `--disable-sync`, manga-fetch 0.6.6) ; vérifié dans Edge : « Pas en cours de
  synchronisation ». 🟠 **Le profil de capture de la PRINCIPALE synchronise toujours** (état antérieur, non touché —
  question posée à Quang). (4) Liste de sites validés PROPRE à la secondaire, hors dépôt (`MANGA_SITES_FILE` →
  `prive/_sites.json`) : 2 sites testés (capture + enchaînement). (5) Captures réelles dans la secondaire : un webtoon
  en longues bandes (20 → 141 pages, 2/2) et un site `chapter-N` (ch.1 → ch.2 enchaînés) ; la principale n'a pas bougé.
  Deux défauts de manga-fetch trouvés et corrigés (0.6.7, profitent aux deux applications) : un bloc intérieur plus
  COURT que la page était pris pour le lecteur ; la marque `data-mf-defile` d'une capture précédente restait dans
  l'onglet et faisait défiler le mauvais élément. (6) **Indicateur d'enchaînement** (Quang 18h48, les deux
  applications) : l'onglet choisi dit « 🔗 enchaînement possible : <type> » ou « ⛔ un chapitre à la fois », et dans ce
  cas le sélecteur « Chapitres » est fermé sur « ce chapitre seul ». Même règle côté app (`capEnchainement`) et outil
  (`enchainement_possible`, manga-fetch 0.6.8) : `test_enchainement.py` 14/14 (mutation rouge),
  `test_enchainement_ui.py` 12/12 sur 8190 ET 8192 (vrais onglets, 1280 + 360 px).
  ℹ Limites de capture (question Quang 18h49, lu dans le code) : pas / tours / chrono sont remis à zéro À CHAQUE
  chapitre ; limite PAR LANCEMENT = 50 chapitres (`suite` ≤ 50, `jusqua` ≤ 50 passages).
  ⬜ Proposé, non fait : enchaîner sur les sites à adresse à identifiant interne (suivre le lien « chapitre suivant »).
- **Après S4 (Quang, 24/09 17h28)** : l'espace secret devra aussi capturer du **manga classique** (pages), pas
  seulement du webtoon. Le site d'essai (webtoon) fourni par Quang est noté **hors dépôt** (dépôt public) :
  `C:/Users/quang/Documents/MangaStudio-donnees/prive/_NOTES-essai.txt`.
- **S4 — Téléphone** : sous-domaine dédié → tunnel → 8191, **derrière Cloudflare Access** (règle
  `.claude/rules/apps-perso-zero-secret.md` : même origine app+API, policy = email de Quang). ⚠ `CF_API_TOKEN` n'a pas la
  permission Zero Trust (liste VIDE au lieu d'une erreur) → API interne du dashboard depuis une page loguée ; PWA :
  bypass Access sur `/manifest.json` + `/icon-*` ET `estPublic()` (règle PWA derrière Access). Vérifier SANS cookie :
  manifeste 200, page 302.
  ✅ **FAIT 24/09 19h20** (adresse NON écrite ici : dépôt public — elle est dans `prive/_acces.json`). Ordre suivi pour
  qu'elle ne soit jamais exposée : (1) 3 Access Applications créées AVANT le DNS (API du dashboard, session `EdgeAuto-cf`
  reconnectée par Quang via passkey) — nom neutre, **invisible du lanceur d'apps**, policy « Allow Quang » (e-mail
  seul, relu après création), session 730 h, OTP ; + 2 bypass PWA (`/manga/manifest.webmanifest`, `/manga/icon-*`) ;
  (2) CNAME proxifié vers le tunnel existant `generate-agent` ; (3) une entrée d'ingress → 127.0.0.1:8192 (validée par
  `cloudflared ingress validate/rule`), seul le cloudflared de ce tunnel relancé. Pas de worker ni de `estPublic()` :
  le proxy sert déjà manifeste et icônes sans clé. **Clé jamais saisie sur le téléphone** : `espace_prive.py` 1.5.0
  accepte le jeton `Cf-Access-Jwt-Assertion` VÉRIFIÉ (signature JWKS, audience, émetteur, e-mail) ; faux jeton → 401.
  `launch-generate-agent.ps1` donne à la principale l'adresse de la secondaire (`MANGA_AUTRE_URL`, lue hors dépôt).
  Vérifié SANS cookie : page, API, `sw.js`, racine → **302** ; manifeste + 2 icônes → **200** ; principale inchangée.
  Bout en bout (navigateur neuf, format téléphone, code OTP lu dans Gmail) **7/7** : connexion → app secondaire, se sait
  secondaire, AUCUNE clé stockée, bibliothèque chargée, chemin Wi-Fi coupé, 0 erreur. Appui long depuis la principale
  ouverte par le tunnel → la secondaire, et **rien ne s'ouvre sur le PC**. Sauvegardes (avant/création, diffs tunnel et
  lanceur) : `prive/_acces-sauvegardes/`. ⚠ Session Access = 1 mois max (WARP pour aller au-delà, règle apps perso).
- **Entre S4 et S5 — fait le 24/09 19h30** (demandes Quang 19h10) : (a) ✅ fenêtre de capture PRINCIPALE sans compte
  Microsoft ni synchro (manga-fetch 0.6.9, défaut pour toute fenêtre de capture ; rouverte à sa place, onglets rétablis ;
  ⚠ ce qui a été synchronisé AVANT reste dans le compte Microsoft de Quang). (b) ✅ enchaînement « par la page » pour
  les sites à identifiant interne (manga-fetch 0.7.0) : liste des chapitres de la page (identifiant de l'option →
  adresse du suivant, validée à l'arrivée ; changer la valeur d'une liste CACHÉE pilotée par un widget ne déclenche
  rien — constaté), sinon lien « chapitre suivant ». Vérifié sur un site qui échouait : ch.1 → ch.2. (c) ✅ sites
  TAGUÉS : l'indicateur de l'app (v2.18.0) lit d'abord la liste des sites validés de SON application (« non » =
  fermé, « ok » = ouvert), puis les formats d'adresse. 🟠 Le banc `test_enchainement_ui.py` exige un onglet de chaque
  sorte : il reste rouge quand la fenêtre n'a que des sites qui enchaînent (constaté v2.18.0 sur la principale).
  🟠 Le contrôle « principale inchangée » des essais de capture compare les dates des entrées de `sources/` : Quang
  qui ouvre une série dans la principale le fait passer au rouge (fausse alerte du 24/09 19h24, vérifiée).
- **24/09 20h55** : manga CLASSIQUE (pages) capturé dans la secondaire (MangaDex, 35 pages, mode page par page) ✅.
  **v2.24.0** (Quang) : la secondaire affiche AUSSI les sites de la principale, étiquetés « principale » ; la principale ne
  voit jamais ceux de la secondaire (proxy `manga_sites`, sens unique). 8190 : 4 sites ; 8192 : 2 + 4 « principale ».
- **24/09 21h30 — v2.26.0 → v2.27.0 (demandes Quang)** : (1) **Reprendre un manga** (étape 1 de la capture) : le lien de
  chaque chapitre était DÉJÀ enregistré (`manifest.source_url`) → une ligne PAR SITE avec son chapitre le plus avancé ;
  🔗 l'ouvre dans la fenêtre de capture (PC) ou le navigateur (téléphone), SANS avance automatique (l'ordre dépend trop
  du site — Quang) ; ✕ rouge = retirer un site obsolète, ↺ = le remettre (route `/manga/liens`, `<racine>/_liens_retires.json`,
  ⚠ active après la prochaine relance du proxy) ; « 🔗 Site » aussi dans l'en-tête de la série. (2) « ↻ Actualiser » les
  onglets passe à l'étape 2. (3) Narration : DEUX champs « de la page / à la page » ; narrate_chapter 2.9.0 applique
  enfin la plage à une analyse reprise (elle était ignorée). ⏸ **Maquette de la capture repensée** à valider par Quang :
  `maquette_capture_v1.html` (4 étapes colorées, une question chacune ; étape 1 = 3 cartes ; un seul bouton final).
- **24/09 22h10 — manga-fetch 0.7.1 + site AnimoFlix (scans VF)** ajouté aux sites validés de la PRINCIPALE (la secondaire
  le voit, étiqueté) : Claymore vol. 4 (166 p.), 5 → 6 enchaînés (175 / 174 p.). Deux défauts trouvés et corrigés : la
  mode était jugé AVANT que la page soit construite (attente d'une hauteur stable, 12 s max) ; la page d'un volume est un
  ACCUEIL avec « Lire Volume N » → clic auto, seulement s'il n'y a aucune image de page. Constat Quang : ces volumes sont
  de longues bandes → découpe dans les blancs (jamais dans une case), mais une « page » de l'app peut mêler la fin d'une
  page du livre et le début de la suivante — sans effet sur la narration ; amélioration possible (couper aux vrais
  blancs de page) NON demandée. Captures simultanées principale + secondaire : constatées OK en réel (21h41-21h43).
  ⚠ `/manga/liens` (✕ des sites) actif sur la principale ; la SECONDAIRE sera relancée quand elle sera au repos (lot de
  Quang en cours à 22h07) — déclencheur : prochaine relance, vérifier `/manga/activite` vide avant.
- **24/09 22h15 — v2.28.0 : CAPTURE REPENSÉE** (maquette `maquette_capture_v1.html` validée par Quang 22h09) : 4 étapes de
  couleurs différentes (une question chacune) ; étape 1 = 3 cartes (🔁 Reprendre / 📱 Lien du téléphone / 🖥 Déjà ouvert sur
  le PC) + lien discret « 🕹 piloter à distance » ; étape 4 = 3 boutons (le sélecteur caché reste la source de vérité,
  grisés quand le site n'enchaîne pas) ; résumé en direct ; UN bouton vert final ; outils de fenêtre derrière le voyant
  « ● fenêtre ouverte ▾ » ; sites validés repliés en bas. Blocs DÉPLACÉS tels quels : les 49 identifiants d'avant présents
  une seule fois (contrôle automatique). Piège payé : `<section>` = onglet pour l'app (`main section{display:none}`) →
  étapes en `<div>`. Vérifié 360 + 1280 px : zones, boutons, résumé, 0 débordement, 0 erreur ; enchaînement UI 7/8
  (le KO = pas d'onglet « non » ouvert, connu).
- **24/09 22h25 — suivi_nuit 2.5.1 : la vidéo d'un lot de la SECONDAIRE échouait** (Quang : « une erreur, mais aucune
  alerte »). Log `prive/_suivi/journal.jsonl` : narration ✅ (875 s), karaoké ✅, puis `video : chapitre introuvable`. Cause :
  `PROXY = "http://127.0.0.1:8190"` EN DUR → la secondaire demandait la vidéo d'un chapitre privé à la PRINCIPALE. Le serveur
  8192 n'a PAS été coupé (les `WinError 10053` de `espace_prive.log.err` = onglets fermés côté client, du bruit). Fix : l'adresse
  suit l'espace (`MANGA_PROXY`, sinon 8192 si `MANGA_ESPACE=prive`, sinon 8190) — le proxy transmet déjà son environnement,
  donc AUCUNE relance nécessaire. Vérifié : relance réelle du lot par `/manga/suivi_lancer` sur 8192 → narration gardée (0 $),
  vidéo acceptée par 8192. 🟠 (constaté 2.5.1) d'autres scripts MANUELS ont 8190 en dur (`refaire_*`, `check_version`,
  `samsung`, bancs) : sans effet sur la secondaire tant qu'on ne les lance pas contre elle.
- **24/09 22h21 → 23h15 — MAQUETTE D'ENSEMBLE appliquée à toute l'app** (`maquette_entete_serie_v1.html` variante A puis
  `maquette_ensemble_v1.html`, validées par Quang 22h21 et 22h31 « je te laisse gérer de manière autonome jusqu'au bout »).
  Charte : retour BLEU en haut à gauche qui dit où il ramène ; ≤ 4 actions en vue, le reste dans « ⋯ » ; Supprimer en
  ROUGE, en dernier ; un seul gros bouton vert par écran ; téléphone = grille icône + mot court ; un réglage = une ligne.
  Menu « ⋯ » générique (`.menu-plus` / `menusFermer`, se ferme au clic ailleurs / après un choix / Échap, reste ouvert
  quand on tape dans un champ du menu). Lots, chacun avec son banc sur l'app RÉELLE à 1280 + 360 px :
  v2.29.0 en-tête de série (44/44) · v2.30.0 page principale (55/55) · v2.31.0 Profil et traitement (57/57) ·
  v2.32.0 Vidéos (36/36) · v2.33.0 un chapitre (40/40) · v2.34.0 lecteur (28/28 + ancien 13/13) · v2.35.0-v2.36.0 le
  reste (40/40). **Demandes Quang en cours de route, appliquées** : VRAM (22h32) ET mode ☁/🖥 (22h33) VISIBLES EN
  PERMANENCE (seuls coûts et ℹ️ dans ⋯) ; sur téléphone la pastille du mode calée À DROITE contre ⋯ (22h52 : poinçon de
  la caméra au centre) ; le mode est GLOBAL côté serveur (`sources/_reglages.json`, un par application) et une page
  ouverte se recale seule (retour dans l'app + tour d'activité) (22h53) ; 🔗 de « Reprendre » / « Site » : TOUJOURS la
  fenêtre Edge dédiée de CETTE application, téléphone compris, ouverte si fermée (23h05). Alerte de fin de traitement :
  bandeau en tête de Bibliothèque + pastille ❌ sur l'activité (jusqu'à « Voir » / ✕), bilan du Profil en bandeau
  rouge + « Refaire ». **Écart assumé** : les CASES de la planche et leur « ⚙ Affiner » ne bougent pas (déjà repensées le
  27/07 selon le même principe ; `.panel{overflow:hidden}` couperait un menu) — seule « 🗑 Bulle » passe en rouge à droite.
  Anciens bancs : 13 adaptés (ouvrir le ⋯ / la ligne avant de cliquer, `scripts/…bak-20260924-menus`) ;
  ~~`test_bibliotheque_ui` 76/92 = IDENTIQUE à v2.28 (16 échecs de DONNÉES périmées : « demo-frieren », OPM = 27 ch.).~~
  → ✅ repointé le 25/09 (v2.48.0) : **95/95** — autre titre réel (Solo Leveling « level up alone »), série MASQUÉE absente
  de la recherche (Black Jack), « claymore 5 » trouve Claymore (le ch.5 existe), nombre de chapitres d'OPM lu sur le DISQUE,
  ch.301 ouvert par son nom ; + contrôle : le banc ne touche plus le tri « récemment ouverte ».
- ~~⬜ **PROCHAINE SESSION — demandes Quang 22h11-22h14, dans cet ordre**~~ → 1 ✅ v2.29.0 · 2 ✅ v2.37.0 (voir plus bas)
  · 3 ✅ v2.30.0 · 4 voir plus bas :
- **24/09 23h30 — v2.37.0 : TOMES AUTOMATIQUES** : un chapitre capturé depuis une page de VOLUME (l'adresse le dit :
  `volume-4`, `vol_3`, `tome-07`, `tomo 5`) EST le tome N, dès sa capture, sans relance de serveur (`tomeDuLien`, côté app,
  principale et secondaire). Prime sur la table MangaDex (qui ne connaît que les vrais chapitres). Claymore : ch. 4/5/6
  AnimoFlix → Tome 4/5/6, plus de « Hors tome ». Banc `test_tomes_volume.py` 6/6 (12 adresses dont 6 pièges), mutation
  rouge. 🟠 (constaté v2.37.0) **Raijin-scans ch. 1-3 de Claymore** : 180 pages chacun = sans doute les VOLUMES 1-3, mais
  l'adresse (`/claymore/1/`) ne le dit pas → ils restent « Tome 1 » (table MangaDex). Le nombre de pages n'est PAS un signal
  sûr (un chapitre webtoon en fait 141). ~~⏸ Question posée à Quang : marquer ces 3-là à la main comme volumes~~ → ✅
  tranché v2.38.0 : Quang ne veut PAS de rangement manuel (« automatiquement pour les prochains ») et plus d'intertitres
  de tome du tout (23h35 : « le chapitre me suffit, c'est plus compact et plus propre ») → la vue d'une série = les
  chapitres dans l'ordre, grille 2 colonnes PC / 1 téléphone ; le tome reste connu pour la recherche « tome N »
  (banc `test_tomes_volume.py` 7/7, `test_bibliotheque_ui` 76/92 = référence).
- **24/09 23h50 — v2.39.0 : passe QA (sous-agent, les 2 applications, 360 + 1280 px, POST bloqués)** → corrigés :
  (1) ouvrir un chapitre le faisait défiler SOUS la barre collée (retour bleu et actions cachés) → `scroll-margin-top`
  = hauteur réelle de la barre (`--haut-colle`, suivie en direct) ; (2) le ⋯ de la Planche sortait à gauche à 360 px →
  tout menu ouvert est recalé dans l'écran (`menuRecaler`) ; (3) ⚙ du lecteur : « ← Lecture » bleu à gauche. Bancs
  enrichis (chapitre 42/42 avec mutation rouge, reste 42/42). 🟠 (constaté v2.39.0, antérieurs à ce soir, non traités) :
  ~~listes « Moteur de lecture » / « Voix » du chapitre coupées à 360 px~~ → ✅ couvert par v2.45.0 (25/09 10h30 :
  mesuré 142 px « Kimi K3 — le pl » + 104 px « Charon — » sur une ligne ; sous 640 px chacune a sa ligne → 291 / 254 px ;
  PC inchangé ; banc `test_chapitre_detail.py` 43/43, mutation rouge) ; ~~console bruitée de 502 `/comfy/*` quand le
  moteur local est éteint~~ → ✅ couvert par v2.46.0 (25/09 10h55) : c'était PLUS qu'un bruit — les références des
  personnages (fichiers de `ComfyUI/input`) étaient demandées au MOTEUR (`/comfy/view`) → moteur éteint = références
  INVISIBLES. Proxy : `GET /manga/comfy_file` (lecture disque, confinée, clé exigée) + `GET /manga/comfy_up` (toujours
  200) — `proxy-patch/patch_comfy_hors_moteur.py` + `.diff`, principale relancée par `relance-proxy.ps1`, secondaire au
  repos par sa tâche. App : images par la route disque, sonde sans 502, listes LoRA/checkpoints chargées à l'allumage.
  Mesuré 1 min chapitre ouvert : 10 erreurs → 0. Banc `test_moteur_eteint.py` 23/23 (1280 + 360 px, 10 références
  affichées, 7 évasions de dossier refusées), mutation rouge ; moteur allumé vérifié à la main (8 ckpt, 173 LoRA, 0 erreur). Déclencheur : prochaine passe sur le bloc Narration d'un chapitre.
- **25/09 00h30 — un site ajouté à la SECONDAIRE (nom hors dépôt)** (Quang 00h10) — manga-fetch **0.7.2** + app **v2.40.0** :
  adresses « chapter/N » (barre oblique) reconnues ; la page ne liste PAS les autres chapitres, seul un `<button>`
  « NEXT Ch. N » (sans href) mène au suivant → nouveau recours `_suivant_par_bouton` : on ne touche qu'un bouton qui
  ANNONCE un numéro, on clique, puis on VÉRIFIE que l'arrivée porte ce numéro (adresse ou titre) ; intermédiaires sautés
  si « entiers ». Piège payé : le lien d'accessibilité `…/chapter/2#main-content` passait pour une « liste de
  chapitres » ne contenant que le courant → quand cette liste ne propose rien après, le bouton est essayé avant de
  conclure. Contrôle réel (fenêtre de la secondaire) : ch.1 83 p., ch.2 76 p., ch.3 → ch.4 enchaînés d'un lancement ;
  pages vérifiées à l'œil (manhwa EN). `test_enchainement.py` 16/16. Entrée ajoutée à `prive/_sites.json` (hors dépôt).
- **25/09 09h30 — v2.41.0 + suivi_nuit 2.6.0 : vitesses SÉPARÉES en ligne / sur le PC pour les VIDÉOS** (Quang 09h20 :
  « la narration locale a tendance à aller plus vite »). Le lecteur les séparait déjà (v2.21.0). Une vidéo prend la
  vitesse de SA voix (tag « …-local » = sur le PC) : bouton Vidéos / ↻ = mémoires du lecteur (`manga_vit_cloud` /
  `manga_vit_local`), une demande par type de voix ; profil (lots, la nuit) = « vitesse ☁ » + « 🖥 »
  (`reglages_video.vitesse_local`, défaut 1×, retiré avant l'envoi à la vidéo). Banc `test_vitesses_video.py` 12/12
  (mutation rouge), `test_voix_vitesses_ui` 13/13. ⚠ Conséquence ASSUMÉE : une vidéo LOCALE déjà faite à une autre
  vitesse que la nouvelle vitesse 🖥 est vue « périmée (vitesse) » → refaite au prochain lot / à la nuit (sans coût : GPU).
- **25/09 09h35 — v2.42.0 : les deux vitesses VISIBLES dans le bloc Narration de chaque chapitre** (Quang 09h27 : « dans
  la création de narration, les vitesses n'apparaissent pas »). Champ « Vitesse d'écoute » ☁ / 🖥 = les MÊMES mémoires
  que le lecteur et les vidéos (un changement ici vaut partout, le lecteur ouvert suit) ; celle du mode actuel
  (pastille ☁/🖥 de l'en-tête) est encadrée. Banc `test_vitesses_video.py` 22/22 (1280 + 360 px).
- **25/09 10h00 — v2.43.0 : RELAIS AUTOMATIQUE de modération, sur interrupteur persistant** (Quang 09h50) —
  reglages 1.2.0 (`relais_moderation`, par application, défaut NON), narrate_chapter 2.10.0, patch serveur
  `proxy-patch/patch_relais.py` (la route ne transmettait QUE `mode` → « mode inconnu » vu par Quang ; principale relancée
  par `relance-proxy.ps1`, secondaire à relancer après sa narration en cours). Une page refusée à l'ANALYSE est reprise
  DANS LA MÊME BOUCLE par l'autre moteur en ligne (gemini ↔ kimi, pixtral → gemini) avec le MÊME contexte ; refusée par
  les deux → alerte comme avant ; jamais en « reprise de modération », jamais le local. COÛT : l'appel de relais est
  facturé au tarif du moteur qui RÉPOND (`cout(model_eng)`), vérifié au chiffre près + mutation rouge
  (`test_relais_moderation.py` 18/18 hors ligne) ; interrupteur `test_relais_ui.py` 14/14 (écrasé à 0 px sur téléphone
  au 1er jet, vu par Quang, corrigé). ⚠ Non couvert : un refus au RÉCIT (DeepSeek) n'est pas relayé.
- **25/09 10h15 — v2.44.0 + narrate_chapter 2.11.0 : PIXTRAL en dernier recours + TRAÇABILITÉ + coût des refus**
  (Quang 09h59-10h00). Chaîne de relais gemini → kimi → pixtral (kimi → gemini → pixtral) ; Pixtral RETIRÉ des choix de
  moteur (« il ne servira qu'à ça »). Chaque page touchée porte dans `narration.json` un champ `trace`
  {refuse_par: [{moteur, motif, t}], lu_par, comment : relais automatique | mise de côté (alerte) | reprise choisie
  dans « À traiter »} ; le lecteur l'affiche sur la page (« 🔁 lue par Kimi (refusée par Gemini) »). **Coût** : un REFUS
  était perdu avec l'exception (jetons jamais comptés, défaut antérieur au relais) → désormais facturé au tarif du
  moteur qui refuse, d'après les jetons qu'il déclare ; Pixtral = 0 $ (offre gratuite Mistral). Banc
  `test_relais_moderation.py` 25/25 hors ligne (mutation du coût des refus → rouge), `test_relais_ui.py` + affichage.
  ~~🟠 (constaté v2.44.0) refus aux étapes RÉCIT / NOMS / TRADUCTION : ni relayés ni comptés — même traitement à porter
  si Quang en rencontre (déclencheur : 1re alerte « récit » ou « traduction »).~~ → ✅ couvert par **v2.47.0 +
  narrate_chapter 2.12.0 + traduire_chapitre 2.0.0** (25/09 10h50, carte blanche Quang 10h19) : même interrupteur,
  mêmes règles qu'à l'analyse. NOMS : gemini → kimi (budget 16 000, K3 raisonne) → pixtral. RÉCIT (texte seul, même
  consigne, même contexte) : la page est d'abord ISOLÉE par DeepSeek (coupes du lot), puis kimi → gemini ; un refus EN
  TOUTES LETTRES (réponse 200 « I'm sorry… ») est désormais reconnu comme refus (avant : « JSON illisible »).
  TRADUCTION : gemini ↔ kimi → pixtral, même page, mêmes bulles ; la trace survit à `--rerendu`. Chaque refus est
  FACTURÉ au tarif du moteur qui refuse (refus HTTP DeepSeek = 0, rien n'est rendu). Lecteur : « ✍ récit par Kimi
  (refusé par DeepSeek) », « ⛔ récit refusé par … », « 🌐 traduite par Kimi (refusée par Gemini) », « ⛔ traduction
  refusée (…) — en VO » (depuis `stats.relais` / `stats.moderation` de traduction.json, déjà rendus par le proxy).
  **Défaut antérieur trouvé par le banc** : une page refusée au récit ressortait « vide » → redemandée → refusée une 2ᵉ
  fois (alerte en DOUBLE + appels facturés en trop) ; exclue de la relance. Bancs : `test_relais_moderation.py`
  **51/51** hors ligne (5 mutations, toutes rouges), `test_trace_etapes_ui.py` **24/24** (vraie narration dans le
  lecteur, 1280 + 360 px, mutation rouge) ; non-régression moderation 21/21, recit_lots 16/16, latin 11/11, hors_zones
  5/5, frein 6/6, sans_cjk, complement_bulles verts. Passage RÉEL court (Claymore ch.1, analyse reprise, p. 5-6, sans
  voix) : 2 pages, 0,0006 $ — rangé dans `sources/_corbeille/essai-v2120-20260925/`.
- **25/09 11h03 — v2.48.0 : les BANCS ne dérangent plus les données de Quang** (carte blanche, passe « bancs périmés »).
  (1) Un navigateur piloté (`navigator.webdriver`, Playwright) n'écrit plus « ouverte » dans `_bibliotheque.json` : les
  bancs réordonnaient le tri « récemment ouverte » (constaté : Claymore et OPM datés 10h54 par un banc — leurs dates
  d'avant sont PERDUES, irrécupérables). Mesuré : `ouvertes` identique avant/après 2 bancs ; mutation (garde retirée) →
  fichier modifié. (2) `test_moderation.py` créait `sources/zz-serie/ch_1/video` (vide) dans les VRAIES données (son
  sous-processus `video_chapitre.py` n'héritait pas de la racine du banc) → `MANGA_SOURCES_DIR` = dossier du banc ; dossier
  fuité supprimé (vide), 21/21. 🟠 (constaté v2.48.0) `ouvertes` garde 5 slugs de bancs anciens qui n'existent plus
  (`zz-serie`, `banc-profil-ui`, `banc-prof-mus`, `zz-essai-mus`, `zz-essai-vide`) : sans effet visible, laissés.
- **25/09 11h20 — v2.49.0 : passe QA (sous-agent, 2 applications × 1280/360 px, POST bloqués)** → corrigés : (1) lecteur
  à 360 px : le compteur « page N (i/n) » était COUPÉ (« Claymore ch. 1 · page … » ; rien de la page avec un titre long) →
  3 parts, l'étiquette et le titre rétrécissent, le compteur jamais ; (2) Narration sur PC : « Kimi K3 — le plus fiabl… »
  (193 px) → largeur de base 300 px (335 / 297 px) ; (3) un menu ⋯ en bas d'écran s'ouvrait HORS de la fenêtre (906-1058
  px pour 900) → `menuRecaler` l'ouvre vers le haut s'il y a la place. Bancs : `test_chapitre_detail` 45/45,
  `test_trace_etapes_ui` 28/28 (titre très long compris), mutation v2.48 rouge ; lecteur 13/13, reste 42/42, vitesses
  22/22 + 13/13, moteur éteint 23/23. Non retenus : tolérance aux fautes < 4 lettres (voulu), liste de page de la Planche
  tronquée à 360 px (liste déroulante). ⏸ **Question à Quang** : dans la secondaire, fermer 2 menus par Échap en < 0,6 s
  déclenche la PANIQUE (mesuré par le QA) — geste peu probable à la main ; faut-il qu'un Échap qui ferme un menu ne compte
  pas ? (plus sûr contre les faux départs, mais une panique menu ouvert demanderait 3 appuis). → ✅ **Tranché par Quang (25/09 11h54) : on le laisse TEL QUEL** (« ça ne m'a jamais dérangé ») — ne pas reproposer.
- **25/09 11h34 — v2.50.0 : une capture ARRÊTÉE AVANT SON BUT se signale, et se REPREND en un clic** (Quang 11h19-11h24 :
  « 40 chapitres programmés, arrêté à 22 […] à aucun moment je n'ai eu de notification » ; puis « un bouton pour reprendre
  exactement là où ça s'est arrêté » ; puis « une erreur peut arriver même au milieu d'un chapitre »). Journal lu d'abord :
  à 02h57 (secondaire) l'adresse du ch. 23 portait le jeton du contrôle Cloudflare (`__cf_chl_rt_tk`) → 1 page capturée
  (la page de contrôle) → « capture tronquée », dossier partiel RETIRÉ par manga-fetch, série arrêtée « le chapitre 23 a
  échoué ». Le signal manquait parce que le bilan ne vivait qu'en MÉMOIRE du serveur (`_FETCH`, effacé par une relance) et
  dans le panneau de capture s'il était ouvert. **Serveur** (`proxy-patch/patch_capture_bilan.py` + `.diff`) : un veilleur
  attend la fin de chaque capture et écrit `<sources>/_capture_derniere.json` (tenu ou non, faits, arrêt, reprise : chapitre
  en échec, objectif ou nombre restant, options, adresse SANS jeton) ; `GET /manga/capture_derniere`. **App** : bandeau 🟠 +
  pastille ❌ (relu au chargement, à la fin d'une capture suivie, et toutes les ~60 s), « 🔗 Ouvrir le ch. N » (onglet dans la
  fenêtre de capture), « ▶ Reprendre au ch. N » : REFUSE tant que l'onglet affiche la vérification (titre « Just a moment… »),
  repart TOUJOURS de la 1re page du chapitre (`page1` forcé), objectif d'origine gardé, chapitre partiel mis de côté (`force`).
  Rien ne part tout seul : un contrôle Cloudflare se valide à la main (réessayer seul risquerait un blocage de l'IP).
  Bilan de la nuit RECONSTITUÉ par le code du veilleur dans la secondaire (reprise ch. 23 → 40) ; la principale n'en voit
  rien. Bancs : `test_capture_bilan.py` **16/16** hors ligne (8 fins de capture), `test_capture_alerte_ui.py` **36/36**
  (1280 + 360, routes interceptées, mutation « vérification ignorée » rouge) ; vrai bandeau vérifié dans la secondaire.
  🟠 (constaté v2.50.0) une relance du SERVEUR pendant une capture tue le veilleur → pas de bilan pour celle-là.
- **25/09 11h40 — v2.51.0 + reglages 1.3.0 : le FLOU de la secondaire devient OPTIONNEL** (Quang 11h19 : « le rendre plutôt
  optionnel, en persistance, dans les trois petits points »). Interrupteur « 🌫 Flouter hors de la fenêtre » dans ⋯ (secondaire
  seulement ; la principale n'a pas de flou), réglage `flou_discretion` côté SERVEUR par application (vaut sur tous les
  appareils), ACTIF par défaut (comportement d'avant). Proxy : `proxy-patch/patch_flou.py` + `.diff` (la route ne transmettait
  que mode + relais). ⚠ **Incident payé pendant ce chantier** : le gestionnaire `$("hdrFlou").onchange` placé AVANT
  `const $` (ligne 2427) → zone morte → TOUT le script mort, les DEUX applications inertes quelques minutes (≈ 11h36-11h39) ;
  `node --check` ne le voit pas (erreur d'exécution, pas de syntaxe) — c'est le banc réel qui l'a attrapé. Banc
  `test_flou_option_ui.py` **28/28** (1280 + 360, clic réel, persistance au rechargement, valeur du serveur restaurée),
  mutation rouge ; relais 51/51, alerte capture 36/36, relais UI verts.
- **25/09 11h42 — v2.52.0 : à la REPRISE, la fenêtre de capture se range et se dimensionne SEULE** (Quang 11h38 : « par
  sécurité, redimensionnée à la taille sûre et surtout rangée sur le côté. Automatiquement, c'est le seul moment où ça doit
  être automatique »). « ▶ Reprendre » enchaîne `fenetre_ranger` (place retenue) puis `fenetre_taille` (juste assez, sans
  déplacer) — plus de question « taille sûre ? » ; fenêtre restée trop petite → reprise bloquée avec message. Le bouton
  « Capturer » habituel garde sa question (inchangé). Banc `test_capture_alerte_ui.py` **42/42**, mutation (v2.51) rouge.
- **25/09 12h40 — v2.53.0 : NAVIGATION TOUJOURS À PORTÉE** (Quang 12h19 : « quand je scrolle très bas […] il manque le retour,
  le rafraîchissement et précédent / suivant »). Maquette `maquette_navigation_v2.html` (proposition A + glissement), validée
  12h22 — ⚠ gardée EN LOCAL, non versionnée : elle contient de vraies pages de manga (dépôt public). Barre flottante en bas,
  invisible en haut de page, visible dès qu'on a descendu : chapitre = ← série · ‹ ch. · ↻ · ch. › · ↑ ; série = ← séries · ↻
  · ↑ ; ailleurs = ↻ · ↑. Jamais sur le lecteur, une fenêtre, la visionneuse ni la sélection de pages. ↻ garde la position.
  Consignes de Quang pendant le chantier : (1) « pas de ZONE CONDAMNÉE » → une réserve en bas de page de la hauteur de la
  barre : la fin d'une page s'arrête AU-DESSUS (mesuré sur tous les onglets) ; (2) téléphone : barre FINE, la hauteur d'une
  barre de notification (36 px, réserve 52 px) ; PC : taille standard (54 px) ; (3) jamais dans la zone des GESTES d'Android
  (≥ 14 px du bas, ou zone sûre + 10 px) ; (4) le glissement gauche-droite est LIMITÉ À LA BARRE (à gauche = suivant, à droite =
  précédent ; en série, à droite = retour), un geste court ne fait rien. Piège payé : une règle téléphone `main{padding:10px}`
  écrasait la réserve (28 px cachés, vus par le banc) → `body > main`. Banc `test_nav_flot_ui.py` **35/35** (1280 + 360,
  gestes tactiles simulés sur la barre), mutation rouge. ⚠ 2ᵉ zone morte de `$` le même jour (bloc inséré avant `const $`) :
  restauré en ~1 min grâce à la sonde de chargement réel, puis replacé.
- **25/09 12h25 — constat Quang (capture) : « calcul du temps restant… » affiché EN PERMANENCE pour une capture** — le serveur
  n'envoie qu'un nombre de pages, total VIDE → aucun temps restant possible. App v2.53.0 : plus de « calcul… » sans fin pour
  une capture d'UN chapitre. 🟠 (constaté v2.53.0) Serveur : avancement EN CHAPITRES + temps restant mesuré pour une capture
  en série → patch préparé, **appliqué quand la capture en cours dans la secondaire sera finie** (la relancer la couperait).
- **25/09 12h45 — v2.54.0 : la barre de navigation TOUJOURS AFFICHÉE + bulle « où je suis »** (Quang 12h36-12h39). (1) « Je
  préfère qu'il soit affiché en permanence ; ce qui se masque et s'affiche selon les interactions est déroutant ; un bouton
  pas accessible devient simplement grisé » → toujours les 5 boutons aux mêmes places, grisés quand ils sont sans effet ici
  (‹ › hors d'un chapitre, ↑ déjà en haut, ← dans la bibliothèque) ; seuls le lecteur plein écran, une fenêtre ou la barre de
  sélection de pages la retirent. (2) « ← Séries » était COUPÉ sur téléphone (limité à 44 px) → largeur du texte. (3) SENS DU
  GLISSEMENT inversé (« précédent à gauche, suivant à droite ») : le geste va dans le sens du bouton — à droite = suivant, à
  gauche = précédent, à gauche en série = « ← Séries ». (4) Bulle VERTE à gauche des boutons : « ch. 301 » (téléphone) /
  « One Punch-Man · ch. 301 » (PC, le retour devient « ← Série »), le nom du manga dans une série, « Bibliothèque » ou
  l'onglet ailleurs ; trop longue → elle DÉFILE (aller-retour ; figée avec « … » si le téléphone réduit les animations).
  Banc `test_nav_flot_ui.py` **46/46** (1280 + 360), mutations rouges (bulle, sens).
- **25/09 12h55 — v2.55.0 : « la notification est fausse » (Quang 12h43)** — journaux lus d'abord : la reprise (lancée à 11h54
  par « ▶ Reprendre », ch. 23 → 40 depuis la page 1) TOURNAIT normalement (ch. 35 fini 12h44:05, ch. 36 démarré 12h44:42 ;
  ~30 s de découpage webtoon entre deux chapitres). Le faux signal : le bandeau « capture arrêtée — Reprendre au ch. 23 »
  n'était fermé QUE sur l'appareil où l'on avait cliqué (mémoire locale) → ailleurs il affirmait un arrêt pendant la reprise.
  Correctif : une capture EN COURS rend le bilan d'avant caduc → pas de bandeau ni de ❌ tant qu'elle tourne ; le bilan de la
  NOUVELLE capture (écrit à sa fin) prend le relais. Vérifié dans la vraie secondaire pendant la capture. Banc
  `test_capture_alerte_ui.py` **46/46**. Piège de diagnostic évité : une « 2ᵉ capture » vue à 12h47 était ma propre commande
  de recherche de processus (sa ligne de commande contenait « manga_fetch.py capture ») — vérifier le PARENT avant de conclure.
- **25/09 13h05 — v2.56.0 : fin de la reprise (ch. 23 → 40)** : 17 chapitres (23-39), arrêt « aucun chapitre après le 39 sur ce
  site », code 3 (réussite) — le ch. 40 n'est PAS PARU. Le bandeau l'aurait annoncé en « capture arrêtée » orange : c'est une
  INFORMATION → bleue, sans ❌ ni reprise (« le site s'arrête au ch. 39 — tout ce qui existe a été capturé »). Secondaire relancée
  à 13h01 par le veilleur (fin de capture détectée) → avancement en chapitres actif. Banc `test_capture_alerte_ui.py` **47/47**.
- **25/09 13h15 — v2.57.0 : APPUI LONG sur la bulle verte = « ▶ Tout traiter » prêt** (idée Quang 13h01). Dans un chapitre :
  CE chapitre coché ; dans une série : « pas terminés » (jamais « toute la série », qui referait / repaierait le fait) ; ailleurs :
  un message. Le panneau s'ouvre et se centre sur « ▶ Lancer » — RIEN ne part sans ce clic (estimation visible). **Pas de
  toucher simple** (Quang 13h09 : « pour éviter les appuis par erreur, le bouton retour est juste à côté »). 0,6 s immobile
  (> 10 px = glissement, annulé), la bulle se remplit pendant l'appui, vibration au déclenchement, pas de menu de sélection
  Android. Banc `test_appui_long_ui.py` **18/18** (1280 souris + 360 tactile, TOUT POST bloqué et compté : 0), mutation rouge ;
  barre 46/46.
- **25/09 13h25 — v2.58.0 : REPLIER vite ce qui s'est déplié** (Quang 13h16, capture : « Profil et traitement » resté OUVERT
  sur la bibliothèque, et plus de retour : la flèche ← y était grisée). (1) Quitter / changer de série referme SES panneaux
  (Profil, Vidéos) — c'était le défaut de la capture. (2) Comme le retour d'un téléphone : ← de la barre devient « ← Fermer »
  tant qu'un panneau est déplié (Profil, Vidéos, Capturer un chapitre) et le replie d'abord, puis reprend son rôle. (3) Échap
  (PC) fait pareil — mais avec un menu ⋯ ouvert, il ferme le MENU (comme avant). Pas d'usine à gaz : ni historique, ni
  nouveau bouton. Banc `test_replier_ui.py` **26/26** (1280 + 360, POST bloqués), mutation rouge ; barre 46/46, appui long 18/18.
- **25/09 13h35 — v2.59.0 : Fold 8 DÉPLIÉ → la barre du bas passait sur DEUX lignes** (Quang 13h25, portrait ET paysage).
  Reproduit à 704 / 933 px (pas à 360 / 476). Cause : la barre est un `<nav>` → elle héritait du `nav{flex-wrap:wrap}` des onglets
  du haut (rattrapé par une règle téléphone seulement), et centrée par left:50 %, sa largeur était plafonnée à la moitié de
  l'écran. → `flex-wrap:nowrap;width:max-content`. Contrôle des 8 onglets à 704 et 933 px : aucun débordement. Banc
  `test_nav_flot_ui.py` **49/49** (+ 476 / 704 / 933 px), mutation rouge. ⚠ Leçon : tester AUSSI les largeurs du Fold déplié.
- **25/09 14h05 — v2.60.0 : UN CHAPITRE EN COMPACT** (Quang 13h37 : « ce bloc est trop énorme en hauteur […] afficher l'essentiel,
  le reste comme pour le reste de l'application », PC et téléphone). Maquette `maquette_chapitre_compact_v1.html` validée 13h41.
  Chaque bloc (Narration → Vidéo → Traduction → Musique, l'ordre du travail) = UNE LIGNE repliée : icône, titre, état en une
  phrase, ACTION principale (🎙 Narrer + ☁/🖥, ▶ Écouter, ▶ Voir / 🎬 Faire la vidéo, 🌐 Traduire) qui clique le bouton
  d'ORIGINE (mêmes confirmations). Toucher la ligne = tous les réglages d'avant (rien retiré) ; une seule ouverte ; mémorisé
  sur l'appareil ; « ← Fermer » la replie ; les raccourcis Narration / Vidéo du haut déplient leur bloc. 246 px au lieu de
  ~850 (PC et téléphone ; état ≤ 2 lignes sur téléphone). ⚠ Défaut GRAVE trouvé par le banc en route : la barre du bas qui
  suivait le doigt (40 px) débordait un instant → en mode téléphone le navigateur AGRANDISSAIT la zone d'affichage sans
  retour → la barre partait SOUS l'écran (et une page captait le toucher de « ← ») → `html,body{overflow-x:clip}` + 20 px.
  Bancs : `test_chapitre_compact_ui.py` **31/31** (mutation rouge), barre 50/50, et 7 anciens bancs adaptés (ils ouvrent le
  bloc avant d'en toucher les réglages) : chapitre 45/45, vitesses 22/22, reste 42/42, lecteur 13/13, relais UI 18, trace 28/28,
  appui long 18/18, replier 26/26.
- **25/09 14h35 — v2.61.0 : trois remarques de Quang (13h48-13h49)**. (1) Appui long → « Tout traiter » → fermer ne RAMENAIT PAS
  au chapitre (le panneau est plus haut dans la page) → un repère (le chapitre ouvert, ou la ligne en haut de l'écran) et sa
  place sont retenus à l'ouverture et rétablis à la fermeture — par ← Fermer, le bouton du panneau ou Échap (tous passent par
  `suiviFermer`). Mesuré : ±0 px. (2) VISIONNEUSE (images agrandies) : même barre que la navigation (bulle verte « N/M · p. N »
  à gauche, ← Fermer, ‹ › ronds) + glissement SUR LA BARRE (pas sur l'image : elle a son zoom), dans le sens des boutons ; le clic
  parasite après un glissement est ignoré. (3) LECTEUR de narration : le même glissement sur sa barre (⏮ ⏸ ⏭), curseur de
  volume exclu. La VIDÉO (lecteur natif, barre de temps) n'est pas touchée : un glissement y entrerait en conflit.
  Banc `test_retour_visionneuse_ui.py` **24/24**, mutation rouge ; lecteur 13/13, barre 50/50, appui long 18/18, compact 31/31.
- **25/09 22h25 — manga-fetch 0.7.4 : MODE RAPIDE, automatique et prudent** (Quang 20h50 : « gagner du temps, mais sûr à
  100 %, pas de sur-ingénierie ») : un chapitre prenait ~4 min à cause d'une attente FIXE de 1,2 s par pas de défilement.
  Si TOUTES les images de la page sont déjà chargées au départ, l'attente devient 0,4 s et remonte jusqu'à 1,2 s dès qu'une
  image à l'écran n'est pas prête ou que la page change de hauteur (connexion lente : jamais plus lent qu'avant) ; fenêtre
  redimensionnée pendant le chapitre → retour à l'attente d'avant + un pas en arrière. Filet : toute image de la largeur des
  pages non prise = ECHEC écrit (alerte « capture incomplète »), prouvé par sabotage. Coupe-circuit `MANGA_FETCH_RAPIDE=0`.
  Preuve A/B (même chapitre, ancienne puis nouvelle méthode, `scripts/ab_mode_rapide.py`) : **9 sites, tous IDENTIQUES
  octet pour octet** — principale : manga-scantrad ×2,6, WEBTOON ×2,0, MANGA Plus ×1,6, AnimoFlix ×1,0 (non enclenché) ;
  secondaire (noms hors dépôt) : 4 sites ×2,3 à ×2,6 (dont le plus lent : 269 s → 114 s), 1 non enclenché. `test_manga_fetch`
  9/9. Déplacer la fenêtre pendant une capture (`scripts/test_deplacer_fenetre.py`, 38 déplacements) : identique, aucun
  effet. La REDIMENSIONNER (165 fois) : aucune image perdue, mais ⬜ fausse alerte « arrêtée avant la fin » (plafond de 400
  pas atteint à 99 %, les pas raccourcissent) — DÉJÀ le cas avec l'ancienne méthode ; déclencheur : si ça arrive en vrai.
  ⚠ Non expliqué : 1 capture de RÉFÉRENCE (sans mode rapide ni déplacement) a échoué une fois sans message, la relance a
  réussi — à surveiller.
- **25/09 22h50 — manga-fetch 0.7.5 + v2.64.1 : fin de série bien dite** (Quang 22h01). CAUSE réelle (bilan lu) : objectif
  « jusqu'au 54 », 54 capturé, mais manga-fetch cherchait QUAND MÊME le 55 → « aucun chapitre après le 54 » → le serveur
  concluait « objectif non tenu » (il n'accepte que « : fait » / « dépasse la borne ») → notification « le ch. 54 n'est pas
  encore paru ». Correctif à la source : objectif atteint = arrêt « jusqu'au ch. 54 : fait » (serveur inchangé, tenu = vrai).
  En plus : site sans suite ET dernier chapitre marqué « Final / End / Fin » (APRÈS le n° dans le titre ou l'adresse ; une fin
  de SAISON / partie / tome ne compte pas, un NOM de série « The End of … » non plus — 12/12 cas) → bilan « (série
  terminée) » → l'app : « ✅ série terminée : le ch. N est le dernier ». Vrai test (fenêtre secondaire, dossier temporaire) :
  53 → objectif 54 = « jusqu'au ch. 54 : fait » ; 54 → objectif 60 = « aucun chapitre après le 54 » (pas marqué final).
  Au passage (22h30) : `test_vue_croisee` 25/25 au repos ; `test_activite_ui` 53/64 = MÊME score sur v2.61.0 → ✅ réparé 23h50
  (déclencheur atteint : boutons d'arrêt v2.65) : son interception `**/manga/activite*` captait AUSSI `/activite_autre` (v2.19)
  → tâches simulées en double ; « +1 » remplacé par la vague « 0/2 » (v2.8) ; hauteurs recalées sur la charte validée (v2.29-2.42).
  **64/64**. ⚠ Correction (23h55) : le 1er commit (`9dcb0cd`) annonçait « mutation rouge » à TORT — le compteur caché passait
  encore (le texte d'un élément caché reste lisible). Contrôle durci (`is_visible`) → mutation 60/64 rouge, sain 64/64.
- ~~À FAIRE — série TERMINÉE reconnue en fin de capture~~ → ✅ ci-dessus (manga-fetch 0.7.5)
- **25/09 23h10 — v2.65.0 + manga-fetch 0.7.6 + proxy : ARRÊTER UNE CAPTURE** (maquette `maquette_arret_v1.html` validée par
  Quang 22h48). Dans le détail de l'activité, sous la capture : en série « ⏹ Après ce chapitre » (drapeau `arret_demande.json`
  à côté du journal de manga-fetch, lu ENTRE deux chapitres ; manga-fetch repère le suivant + son adresse) → puce annulable ;
  « ✖ Maintenant » (confirmation) = fin du processus (arbre), chapitre à moitié → CORBEILLE (un remplacement est restauré comme
  après un échec). Bilan « arrêtée à ta demande » (champ `demande`) → bandeau BLEU + la reprise v2.50 telle quelle ; panneau de
  capture « ⏹ … à ta demande », jamais « ❌ échec ». Proxy : `patch_arret.py` + `.diff` (route `/manga/fetch_arret`), deux
  applications relancées au repos. Banc RÉEL `test_arret_capture.py` **14/14** (vraie capture WEBTOON ep. 1-3 sur la
  principale : après / maintenant / annuler + écran ; nettoyage complet), mutation (drapeau ignoré) 9 KO. Voisins : vue croisée
  25/25, barre 50/50, reprendre 112/112, activité 53/64 (= score antérieur).
- **25/09 23h35 — v2.66.0 : « ✖ Arrêter » une NARRATION / TRADUCTION / un LOT** depuis le détail de l'activité = l'interruption
  PROPRE qui existait pour la bascule ☁/🖥 (v2.12.0, `/manga/interrompre`), mais SANS changer de mode : confirmation qui liste
  ce qui s'arrête (tout ensemble), bilan exact (fini / coupé + analyse gardée / pas commencé), « ▶ Reprendre » du bon lot.
  Banc réel `test_arret_traitement_ui.py` **11/11** (faux lot à vrais processus, tout restauré), mutation (mode changé) rouge ;
  bascule d'origine `test_interruption_ui` 18/18. ⬜ VIDÉO : pas de bouton (hors de l'interruption, et une vidéo en cours
  n'a pas de reprise) — déclencheur : si Quang en a besoin.
- ~~À FAIRE — bouton PAUSE / ARRÊT d'un traitement~~ → ✅ v2.65.0 (captures) + v2.66.0 (narration / traduction / lot) (question Quang 25/09 21h05 : « utile ? fonctionnel sans risque de bug ni
  de régression ? » — à traiter SEUL, pas en même temps qu'autre chose). Constat du code (21h10) : seules l'annulation d'une
  vidéo en attente (`/manga/video_annule`) et l'arrêt du moteur local existent ; rien pour une capture, une narration, un lot.
  Analyse : utile surtout pour une capture en SÉRIE (jusqu'à ~2 h) et un lot. Le risque n'est pas le bouton, c'est l'ÉTAT
  laissé derrière : un chapitre à moitié capturé (dossier sans manifeste), un bilan qui crierait « capture arrêtée » à tort.
  Proposition la plus sûre : (1) « ⏹ Arrêter après ce chapitre » = drapeau lu par manga-fetch entre deux chapitres → zéro
  chapitre partiel, bilan « arrêtée à ta demande » ; (2) « ✖ Arrêter maintenant » (confirmation) = fin du processus + le
  chapitre en cours mis à la corbeille ; (3) « ▶ Reprendre » = relancer la série au chapitre suivant (l'enchaînement sait
  déjà sauter les chapitres présents). Une VRAIE pause (processus gelé) est déconseillée : l'onglet et la session du site
  expirent pendant la pause. Lots / narrations : réutiliser le mécanisme « coupé → ▶ repris » qui existe déjà. Maquette
  d'abord. Déclencheur : la prochaine session Manga Studio (après le mode rapide).
  ✅ Déjà en place (vérifié dans le code 21h35, question Quang 21h34) : la REPRISE d'une capture arrêtée (v2.50.0) — bilan sur
  disque (chapitre, ADRESSE, objectif), « 🔗 Ouvrir le ch. N » rouvre SEULE la fenêtre de capture si elle est fermée
  (`capOngletsPrets` → `/manga/fetch_edge`) puis l'adresse ; « ▶ Reprendre » relance jusqu'au même objectif. Deux clics
  voulus (vérification Cloudflare possible entre les deux). ⇒ l'ARRÊT doit écrire CE bilan : aucun nouveau circuit de reprise.
- **25/09 20h50 — v2.64.0 : NUMÉRO DE CHAPITRE suggéré d'après l'ADRESSE de la page** (idée Quang 20h34) : `chapDeLaPage` lit
  l'adresse (« …/chapter-37 », « …/chapter/4 », « ?episode_no= »), sinon le titre (« Chap 3 », « Chapter 143 », « #004 ») ;
  affiché en DORÉ tant qu'il est suggéré ; un n° tapé n'est jamais écrasé (`CAP_CHAP_AUTO`) ; accueil / recherche = vide.
  Pièges couverts : « chapter-1-ch265736 » (identifiant du site) → 1 ; MangaDex `/chapter/<uuid>/1` → le titre (143, pas le
  3 du début de l'uuid) ; « chapter-12-5 » → 12.5 ; « 012 » → 12. Vrais onglets (principale + secondaire) : 3/3 chapitres
  justes, 6 accueils/recherches vides. Banc `test_choix_manga_ui` **127/127**, 3 mutations rouges ; titres 46/46, lien 12/12,
  série vide 11/11.
- **25/09 18h55 — v2.63.1 : témoin d'activité VIVANT pendant une capture en série** (Quang 18h24-18h46) : il restait figé ~5 min
  par chapitre (« ch.4 1/28 ») alors que le serveur envoyait déjà les pages → « ch.8 p. 105 · 5/28 · ~1 h 56 ». Mesuré en direct
  sur une vraie capture (secondaire) : p. 105 → 112 en 18 s. Capture d'un seul chapitre / narration inchangées (« 42 p. », « 3/10 »).
  `test_activite_ui` 49/64 et `test_vue_croisee` 21/25 = MÊMES scores sur v2.63.0 dans les mêmes conditions (ils exigent une app
  au repos, une vraie capture tournait) → ⬜ les rejouer au repos (déclencheur : prochaine session Manga Studio).
- **25/09 18h00 — v2.63.0 : CHOISIR LE MANGA À LA CAPTURE, fiable sur téléphone + DÉTECTION d'après la page** (retours Quang
  17h10-17h40 ; maquette `maquette_choix_manga_v1.html` validée 17h13). Constaté dans l'app réelle : (1) la liste sous le champ
  était cachée par le clavier et se fermait au moindre toucher à côté ; (2) CAUSE du champ qui plongeait derrière le clavier : le
  calcul des barres « collées en haut » comptait la barre de navigation du BAS (fixe depuis v2.53) → à CHAQUE lettre la page
  remontait de ~880 px ; (3) le champ déjà rempli : on tapait à la suite du nom proposé ; (4) « cl » trouvait « exclusive ».
  Livré : sur tactile le champ est un BOUTON → écran de choix plein écran (`choixOuvrir`, réutilisable), sans clavier tant qu'on
  ne touche pas la recherche, recherche fixée en haut, hauteur = partie visible (`visualViewport`), récentes puis A→Z avec barre
  de lettres (≥ 40 séries), dessin par paquets de 60 (3 000 séries : recherche < 150 ms), « ➕ Nouvelle série », retour Android
  = fermer. Classement `rangTitres` (début du titre > début de mot > contenu > faute tolérée ; 1-2 lettres = débuts de mots),
  aussi dans la liste souris (PC), qui ne recale plus la page pendant la frappe. DÉTECTION (idée Quang 17h40) : titre ET adresse
  de l'onglet comparés à mes séries (titres alternatifs compris) : correspondance entière → le champ prend le nom EXACT ;
  partielle → « Détecté sur la page » en tête de liste, mots reconnus en DORÉ ; jamais par-dessus un nom choisi / tapé ; page
  d'accueil d'un site → champ vide. Contrôle réel (secondaire, vrais onglets) : 4/4 séries reconnues, 2 accueils vides.
  Banc `test_choix_manga_ui.py` **115/115** (360, 476, 704, 933×700 tactile + 1280 souris), 7 mutations rouges ; adaptés :
  `test_cap_titres_ui` 46/46 (souris 1280 + 700), `test_lien_ui` 12/12 ; `test_serie_vide_ui` 11/11, barre 50/50, reprendre
  112/112, appui long 18/18, replier 26/26. ⬜ `test_capture_serie_ui` était DÉJÀ périmé (il cherche `#capSerieMode`, remplacé
  par les boutons « Combien de chapitres ? ») — déclencheur : la prochaine modification de l'étape 4.
- **25/09 16h20 — manga-fetch 0.7.3 : deux sites testés pour la SECONDAIRE** (demande Quang 15h19 ; noms et résultats dans sa
  liste de sites, hors dépôt). Le premier passe tel quel. Le second n'avait capturé que 26 pages par chapitre avant l'arrêt :
  (1) son serveur d'images renvoie 403 à tout client hors navigateur, sans CORS → repli sur la capture d'écran de l'élément,
  qui fait DÉFILER la page vers l'image → la position n'avançait que de ~14 px par pas → plafond atteint à 3 % du chapitre.
  Correctif : l'image est redemandée au NAVIGATEUR (CDP `Page.getResourceContent`) → fichier original, instantané, sans
  bouger (mesuré 144/145 ; le reste passe encore par la capture d'écran). (2) Le filtre de forme (hauteur > 500, pas carré)
  jetait les bandes COURTES de dialogue (10 sur 145) → en bande défilante, une image de la MÊME largeur que les pages déjà
  prises est gardée. Résultat : 175/175 et 138/138, contrôle croisé avec les images de l'onglet. Non-régression
  `test_manga_fetch.py` 9/9. ⬜ Constaté (non corrigé, déclencheur : si Quang remplace une série) : `force` ne s'applique
  pas aux chapitres ENCHAÎNÉS (le suivant, déjà présent, est conservé).
- **25/09 15h20 — v2.62.0 : « ▶ REPRENDRE » + HISTORIQUE DE LECTURE** (idée Quang 14h37, maquette `maquette_reprendre_v1.html`
  validée 14h43). Bouton AMBRÉ tout à gauche de la barre du bas : dans un manga = le dernier chapitre ouvert de CE manga, À SA
  PAGE (« ▶24 » ≤ 480 px, « ▶ ch. 24 » au-delà) ; dans un chapitre déjà ouvert = celui d'AVANT (va-et-vient d'un geste) ; ailleurs
  = grisé (jamais masqué). Appui long (0,6 s, mécanique de la bulle) = fenêtre « 🕘 Reprendre » : une ligne par manga (pochette,
  « il y a 2 h · sur le Fold », « ch. 24 · p. 12 »), la plus récente en haut ; toucher = y aller ; fermer par ← Fermer, son bouton,
  Échap ou un toucher à côté. Page retenue EN SILENCE : 1re page de la rangée du haut de la grille (1 à 4 colonnes selon la
  largeur) + chaque page vue dans la visionneuse ; envoyée après 3 s de calme ou au passage en arrière-plan.
  Serveur : `_bibliotheque.json` gagne `lectures: {slug: {d, page, t, appareil, prec}}` (action `lecture`, chapitre DE la série
  exigé) → commun PC + Fold, séparé principale / secondaire (chacune son dossier sources). Proxy : `patch_lectures.py` + `.diff`,
  principale relancée par `relance-proxy.ps1`, secondaire au repos. Correctif trouvé par le banc : `bibCharger()` remplaçait la
  copie locale et perdait une page pas encore envoyée → `bibFusion()` (la plus récente gagne).
  Banc `test_reprendre_ui.py` **112/112** aux 5 largeurs (360, 476, 704, 933×700, 1280), mutations rouges (chapitre d'avant,
  fusion) ; serveur vérifié en réel puis fichier de Quang restauré à l'octet ; barre 50/50 (banc adapté : `#nfRep` exclu),
  appui long 18/18, replier 26/26, compact 31/31, visionneuse 24/24. Les bancs n'écrivent rien (`navigator.webdriver`).
  **v2.62.1** : « sur le Fold » — Chrome Android RÉDUIT l'user-agent (« Android 10; K »), le modèle exact (SM-F971B) est lu par
  `navigator.userAgentData.getHighEntropyValues` (contexte sécurisé seulement ; sinon « téléphone »). Banc 112/112.
  ✅ 10h04 : SECONDAIRE relancée au repos (tâche `MangaStudioInstance2`) → interrupteur du relais opérationnel des deux côtés
  (principale : ACTIF, allumé par Quang ; secondaire : coupé).
- **24/09 23h32 — SECONDAIRE relancée** (au repos : `/manga/activite` vide, dernière capture « fini ») par sa tâche
  `MangaStudioInstance2` : `/manga/liens` répond (✕ des sites ACTIF), banc `test_page_principale.py 8192` 55/55.
  1. **En-tête d'une série** (capture Quang : « ça fait un peu fouiller ») : « ← Toutes les séries » d'une couleur
     légèrement différente et mieux placé (surtout sur PC) ; le bouton ↻ de la bibliothèque, isolé tout seul, à
     regrouper ; la rangée de boutons (Masquer, Renommer, Site, Tomes, Pochette, Charger, Vidéos, Profil, Supprimer) à
     organiser. **Maquette d'abord (PC + téléphone), validation Quang, puis code.**
  2. **Tomes automatiques** : un chapitre ajouté arrive « hors tome » ; Quang demande que le rangement par tome se
     fasse seul à la fin de la capture. À examiner : la fiche MangaDex/AniList (`serie_infos`, « 📅 Tomes et dates »)
     est-elle relancée après une capture ? Un volume capturé comme « ch. N » (AnimoFlix) = tome N.
  3. **Alerte de fin de traitement** (Quang 22h17 : « aucune alerte ») : un lot fini en échec n'est signalé QUE dans le
     panneau ⚙ Profil (ligne « Dernier passage … ❌ »), qu'il faut rouvrir. À proposer : un avertissement visible sans rien
     ouvrir (pastille du témoin / bandeau) quand un passage finit avec des erreurs. Maquette d'abord.
  4. Relancer la SECONDAIRE (8192) quand elle est au repos, pour activer `/manga/liens` (✕ des sites) — vérifier
     `/manga/activite` vide avant.
- **Voix de l'application secondaire (Quang 19h18)** : 1-2 voix FÉMININES, expression adaptée au thème → à faire à S7
  avec ce qu'on a (Chatterbox local : clonage + intensité d'expression, pas de modération ; Chirp 3 HD). Pistes
  notées, non obligatoires : StoryVoice utilise OpenAI `gpt-4o-mini-tts` avec consigne de ton par personnage.
  Gemini 3.8 TTS : évalué par une AUTRE session de Quang — attendre son verdict, ne pas le refaire ici.
- **S5 — Vue croisée discrète** : chaque instance publie ses traitements vivants dans un registre COMMUN (même principe
  que `sources/_gpu/`, mais hors des deux racines) ; témoin d'activité : côté normal « 🔒 1 traitement en cours · étape ·
  reste ~X min » SANS titre ; côté secret, tout. Au lancement, si l'autre espace travaille : question à l'écran (lancer
  quand même / annuler). **Profite-en pour § 3-bis** : les essais (`--sortie`) et scripts hors app visibles aussi (🧪).
  Coûts : pastille = total des deux, détail des titres seulement chez leur propriétaire.
  ✅ **FAIT 24/09 19h45 — v2.19.0** (principe retenu : pas de registre commun à tenir à jour par chaque script, chaque
  serveur INTERROGE l'autre) : route `/manga/activite_autre` (proxy, diff `proxy-patch/_studio_llm_proxy_vue_croisee_s5.diff`)
  lit `/manga/activite` de l'autre instance (`MANGA_AUTRE_PORT`, clé commune, 3 s max, injoignable = rien) ; la
  principale n'en reçoit que `type/etape/fait/total` (ni titre, ni chapitre, ni dossier). Témoin : « 🔒 N traitement(s)
  en cours · Narration · voix 3/12 » (principale au repos) ou « … · 🔒 N » après le sien ; la secondaire voit « ↔
  principale : … — titre ». Question avant tout lancement lourd (narration, traduction, lot, vidéo, karaoké, résumé,
  ingestion) posée dans `api()` — un seul point de passage ; refuser = rien n'est envoyé. Jauge VRAM : `vram_parts` 1.2.0
  lit aussi les déclarations GPU de l'autre application (`MANGA_GPU_AUTRE` ; elles ne portent que moteur/taille/PID).
  Variables posées par `espace_prive.py` 1.6.0 et par `launch-generate-agent.ps1` (principale). Banc `test_vue_croisee.py`
  **21/21** (traitements FACTICES : PID d'un processus qui dort, rien généré ni payé ; 1280 + 360 px ; titre secret
  absent de toute la page ET de la question). Non-régression : vram 10/10, alertes 18/18, interruption 18/18,
  estimation verte, espace 15/15, espace UI 37/37.
  ⬜ **Reste de S5, à faire avant S8 (recette)** : ~~(1) pastille des coûts = total des deux applications~~ → v2.22.0 (route
  `/manga/costs_autre` : les 3 totaux de l'autre, jamais ses passages ; pastille = somme, détail = celui d'ici + « dont l'autre ») ;
  + (Quang 20h33) le DÉTAIL du témoin montre aussi l'autre application — jauge, étape, avancement, temps restant (`reste_s`
  ajouté aux champs anonymes) ; dans la principale « 🔒 autre application » à la place du titre. Banc S5 **25/25** ;
  ~~(2) § 3-bis —
  essais (`--sortie`, `_banc_reflexion/`) et scripts lancés hors app visibles (🧪) dans le témoin.~~
  → ✅ **v2.23.0** : un ESSAI = un script Python de manga-studio qui ne descend d'AUCUN serveur (psutil, ~0,04 s) ; rattaché
  à l'application dont il lit les données (`MANGA_SOURCES_DIR` de son environnement) ; « 🧪 Essai · <nom du script> », jamais
  ses arguments ; lanceur du venv + enfant = une ligne. Banc `test_essais_visibles.py` **7/7**. 🟠 Constaté (préexistant) :
  ~~`test_suivi_ui.py` vise la série `demo-frieren`, qui n'existe plus → banc PÉRIMÉ (à repointer lors du prochain chantier suivi).~~
  → ✅ 25/09 : la cible se DONNE en argument (`lancer|verifier [port] serie/ch_N`, un chapitre sans narration) ; absente →
  refus clair (code 2) au lieu d'échecs silencieux. Banc PAYANT (~0,76 $) : non relancé sans chantier suivi.
- **S6 — Discrétion** : contenu FLOUTÉ quand la fenêtre secrète perd le focus ; bouton PANIQUE (Échap ×2 → espace
  normal) ; retour auto à l'espace normal après N min d'inactivité (N à fixer avec Quang) ; aucun titre secret dans
  Telegram / notifications / journaux / commits (dépôt `App` PUBLIC).
  ✅ **FAIT 24/09 20h00 — v2.20.0** (actif SEULEMENT dans la secondaire, `espDiscretion()`) : flou (`filter: blur`) dès
  que la fenêtre perd le focus ou passe en arrière-plan ; PANIQUE = Échap ×2 en < 0,6 s → même geste que l'appui long
  (PC : la fenêtre dédiée se ferme ; sinon l'adresse principale) ; ~~retour automatique après 15 min sans geste~~ →
  **RETIRÉ en v2.21.0** (Quang 20h08 : « je ne veux pas de retour automatique, c'est moi qui gère »). Vérifié : aucun script n'envoie de Telegram
  ni de notification (la boucle Telegram du proxy = musique GS, non lancée dans la secondaire) ; journaux de la
  secondaire à part (`espace_prive.log`, `manga-fetch-2/`, `capture_run_prive.log`) ; dépôt : 0 titre/site/adresse
  (grep à chaque commit). Banc `test_discretion_ui.py` **12/12** (principale jamais floutée ni touchée par Échap ;
  flou/net ; Échap ×1 et ×2 lents = rien ; panique avec et sans fenêtre dédiée ; inactivité 3 s avec et sans son).
- **S7 — Chaîne sans modération (profil de l'espace secret)** : voix 🖥 locale, traduction locale (Qwen3-30B, § 4-nonies
  étape 4), analyse = à mesurer sur les 1-2 chapitres d'essai de Quang (Gemini refuse-t-il vraiment ? sinon qwen3-vl
  local, moins fidèle) ; sonde : `scripts/sonde_moderation.py`. Limite posée : personnages adultes uniquement.
  🟡 **EN COURS 24/09 20h05** — MESURÉ : (1) sonde Gemini (question des noms, réflexion minimale) sur 2 chapitres d'essai
  × 20 pages : **0 refus / 40**, 0,04 $ (rapports hors dépôt, `prive/_essais/`, nouvelle option `--sortie`) ; (2) une VRAIE
  narration dans la secondaire (40 pages, analyse Gemini, voix en ligne) : **40/40 pages narrées, 0 page vide, 0 alerte
  de modération**, 8 min 32 d'audio, **0,52 $**, 6 min 30 ⇒ sur ces chapitres, la chaîne EN LIGNE suffit ; la chaîne
  locale reste la solution de repli si un chapitre est refusé. Corrigé : la voix locale n'avait pas ses extraits de
  référence dans la secondaire (`_apercus/` copié, fichiers génériques) ; `tts_local.py` 1.3.0 : `--expression`
  (Chatterbox `exaggeration`, défaut du modèle inchangé). Gemini 3.8 TTS : évalué par une autre session, **écarté pour
  l'instant** (trop récent, plus cher, incomplet — Quang 19h44).
  ⏸ **ATTENTE QUANG — choix des voix** (sa demande 19h54 : « me faire écouter sur des courtes phrases, puis je valide
  les voix et le ton ») : `prive/_echantillons_voix/` = mêmes 3 phrases × 8 voix féminines EN LIGNE (Chirp 3 HD) +
  3 timbres LOCAUX × 2 tons (expression 0,5 / 1,0). 🟠 `local_Kore_ton-appuye` = 23,5 s au lieu de 12,6 s (répétition
  probable). Ensuite : appliquer la ou les voix retenues comme défaut du profil de la secondaire.
  ✅ **Voix validées par Quang (20h08)** — en ligne : Aoede, Despina, Leda, Sulafat ; locales : Aoede ton appuyé, Leda
  ton appuyé, Kore ton normal, Leda ton normal. **v2.21.0** : la secondaire propose CES voix, selon le mode (☁ / 🖥) ;
  la principale garde les 8 d'avant. Ton local = « Voix@1.0 » (tts_local 1.4.0 en tire l'intensité d'expression,
  la voix en ligne l'ignore) ; tag « gemini-leda-ton10-local » (sans point : `_RE_TAG` refusait « ton1.0 » et le
  serveur répondait À TORT « chapitre introuvable » — constaté puis corrigé, proxy + narrate_chapter + suivi_nuit).
  Aperçus Despina/Sulafat générés dans la secondaire (`voix_apercus.py` : `MANGA_VOIX`). **Vitesses séparées** (Quang
  20h08, les DEUX applications) : une mémoire « en ligne » (défaut 1,15) et une « sur le PC » (défaut 1), reprise à
  l'ouverture de chaque narration selon SA voix ; option 1,1× ajoutée. **Retour automatique RETIRÉ** (Quang 20h08 :
  « c'est moi qui gère ») — flou et panique Échap ×2 restent. Banc `test_voix_vitesses_ui.py` **13/13**.
  ~~🟠 Constaté (préexistant, non corrigé) : avec `reuse` (analyse réutilisée), `pages` est ignoré — une narration
  « pages 1-2 » a traité les 40 pages.~~ → ✅ couvert par narrate_chapter 2.9.0 (commit `78074e1`, 24/09 21h36, avec
  l'app v2.27.0 : `if a.pages:` filtre l'analyse reprise sur les pages voulues) — constat resté non barré, relevé 25/09.
- **S8 — Recette réelle** : les deux espaces ouverts en même temps (PC + téléphone), un lot de chaque côté, vue croisée,
  paravent/fermeture à distance, 360 px, cycle couper→relancer ; bancs chiffrés + mutation.
  ✅ **RECETTE RÉELLE 24/09 21h20** : secondaire installée sur le Fold comme application à part (sinon Chrome l'affiche dans
  son bandeau — autre adresse que la principale ; décision Quang : 2ᵉ icône, « pas gênant ») ; v2.25.0 bandeau VIOLET
  foncé dans la secondaire (+ barre d'état). Deux narrations EN MÊME TEMPS : Quang depuis le Fold (secondaire, 35 p.,
  voix en ligne) + Claude sur le PC (principale, 24 p., voix locale) → les deux complètes, 0 page d'histoire sans voix,
  0 alerte ; principale voit « narration · noms 26/35 · reste » SANS titre, secondaire voit la principale avec son titre ;
  jauge VRAM = la voix locale (~3,9 Go) pendant que les deux tournaient. Coût secondaire 0,59 $, principale 0 $.
  Narrations d'essai de Claude rangées dans `sources/_corbeille/essai-s8-20260924/`. Bancs chiffrés de chaque étape :
  S0 47/47 · S1 15/15 · S2 37/37 · S3 10/10 · S5 25/25 · essais 7/7 · S6 11/11 · voix 13/13 (mutations rouges sur S0, S1, enchaînement).
**Pièges connus pour ce chantier** : écrire un fichier en Python texte sous Windows convertit LF→CRLF (proxy entier en
diff → `newline=""`) ; toute relance du proxy par `relance-proxy.ps1 -Qui manga-studio` (jamais Stop-Process) ; un script
qui lit un secret au démarrage doit être relancé après rotation.

## 4-sexdecies. FEUILLE DE ROUTE — LECTEUR VIDÉO + SÉLECTEUR RAPIDE « ALLER AU CHAPITRE » *(26/09/2026 10h58-11h05, demandes Quang)*

**Demandes** : (a) 10h58 — lecteur vidéo : « il manque les commandes essentielles play pause précédent suivant, swipe avant
arrière comme le reste de l'application » + « des suggestions en plus ? ». Maquette `maquette_lecteur_video_v1.html`, envoyée
sur Telegram 11h00 ; **validée en entier 11h05 (« c'est bon pour moi » : A à H)**. (b) 11h05 — « dans toute l'application avec
les barres du bas, il nous manque la fonction rapide de sélection de chapitre via fenêtre rapide + recherche par numéro ?
Swipe vers le bas sur la barre ? ».

### Constat (lu dans le code, 26/09 11h05)
- Lecteur vidéo (`#vidLecteur`) : `<video controls>` natif + deux boutons « ⏮ ch. / ch. ⏭ » en HAUT (masqués sans voisin) ;
  `vidVoisin()` / `vidNavMaj()` gèrent déjà les voisins et les sauts. Aucun geste, aucune reprise, aucune fin enchaînée.
- Barres du bas existantes, toutes « précédent / suivant » seulement (bouton + glissement horizontal > 60 px) : navigation
  bibliothèque/chapitre (`#nf…`, v2.54-v2.61), lecteur narré (`#lecteur .lec-ctl`, pages), visionneuse (`#lightbox .lbbar`).
  **Aucun sélecteur rapide de chapitre** ; pour aller du ch. 3 au ch. 40 il faut revenir à la liste.
- Geste : glisser VERS LE BAS une barre collée en bas = peu de course + conflit avec la barre de gestes Android →
  proposé : glisser **VERS LE HAUT** (panneau qui monte de la barre) + toucher la bulle « ch. N ».

### Étapes
- [x] **V0 — Maquette lecteur vidéo validée** (A-H).
- [x] **V1 — Lecteur vidéo v2.68.0** (26/09 11h30) : `app_patch_268_lecteur_video.py` + proxy `patch_video_pos.py` (+ `.diff`). Banc
      `test_lecteur_video_ui.py` **24/24** (vraies vidéos OPM, 360→1280, gestes tactiles simulés), mutation v2.67.2 rouge ;
      `test_video_nav_ui` 12/12. ⚠ Nom `fmtT` DÉJÀ PRIS dans l'app → `vidFmt` (piège « vérifier les noms »). Proxy patché sur disque,
      **relance à faire au repos** (les deux applications travaillaient à 11h20) : sans elle, la position n'est gardée que sur l'appareil.
      + **2 bugs Quang 11h15 (Fold fermé)** corrigés (`app_patch_268b_clignotement.py`) : onglet Vidéo qui clignotait 54→16 px toutes
      les 4 s pendant une génération (vidRendre effaçait l'en-tête compact) → 0 changement en 12 s ; chevron de la ligne Narration
      hors du cadre < 480 px → OK à 360/476/704/1280. Sonde : `scripts/sonde_clignotement_video.py` (génération simulée).
      Initialement : barre du bas (⏮ ch. · −10 · ⏯ · +10 · ch. ⏭, glissement = chapitre) ; toucher l'image = ⏯,
      double toucher gauche/droite = −10/+10 s ; progression large + temps ; reprise de position par vidéo (serveur, commune
      PC/téléphone) ; fin → ch. suivant dans 5 s (Annuler / Maintenant) ; barre masquée après 3 s ; ⋯ vitesse + plein écran ;
      écran allumé (Wake Lock) ; clavier PC. L'avertissement de saut reste.
- [x] **S0 — Maquette du sélecteur rapide** : v1 (grande feuille : champ n° + grille de tous les chapitres) et v2 (compacte, puces
      du lot, à la demande de Quang 11h06) envoyées ; **Quang 11h08 : « je préfère ta 1ère proposition » → v1 retenue**.
- [x] **S1 — Sélecteur v2.69.0** (26/09 11h25 ; `app_patch_269_selecteur.py`, banc `test_selecteur_ui.py` **26/26** à 360 et 1280 px :
      bulle, glisser vers le haut, n° exact / préfixe / absent → plus proche, filtres, vidéo grisée + raison, version, Échap, glisser
      vers le bas). ⚠ Non couvert par le banc : contexte NARRATION (lecteur narré) et PAGES (visionneuse) — codés, à tester.
      (Quang 11h10 : « sélecteur de chapitre, sélecteur de narration et sélecteur de vidéo, pense à tous les cas »).
      **Cas à couvrir, chacun testé** : chapitre courant (vert, centré à l'ouverture) · lu / non lu · numéro ABSENT de la bibliothèque
      (pointillé, non cliquable ; la recherche propose le plus proche) · chapitre SANS narration / SANS vidéo dans le sélecteur
      correspondant (grisé + raison) · PLUSIEURS narrations (voix) ou vidéos (versions) pour un chapitre → choix de la version
      (défaut : celle en cours / la plus récente) · narration ou vidéo EN COURS de génération (⏳, non lançable) · vidéo « à refaire »
      (signalée, lançable) · numéros décimaux (12.5) et « ignorer les intermédiaires » · série à 1 chapitre · série longue (300+ :
      rendu rapide, recherche) · recherche par numéro exact / préfixe / « 12,5 » · reprise vidéo à sa position · fermeture (✕, voile,
      glisser vers le bas, Échap) · clavier PC (G) · 360 → 1280 px · les deux applications.
      Branchement : un seul composant, branché sur chaque barre du bas (navigation chapitre, lecteur narré, lecteur vidéo ;
      visionneuse = « aller à la page »), ouvert par glissement vers le haut ou toucher de la bulle.
- [x] **PWA secondaire — bandeau Chrome : RÉSOLU sur le Fold, sans code** (26/09 12h05, ADB sans fil accordé par Quang).
      **Cause** (`pm get-app-links`) : sur le Fold (Android 17, Chrome 153) les 2 WebAPK sont NON vérifiées pour leur domaine
      (état `1024`) et « Ouvrir les liens compatibles » était DÉSACTIVÉ → Android ne sait pas que l'adresse appartient à l'autre
      application : Chrome la garde dans la fenêtre courante (= bandeau, dans les deux sens). Sur le Samsung (Android 13) elles sont
      `verified` → ça marchait. `intent://…` testé sur le Fold : **n'aide pas** (même fenêtre) → écarté, rien codé.
      **Remède appliqué** : « liens compatibles » activés pour chacune sur SON hôte
      (`pm set-app-links-user-selection --user 0 --package <webapk> true <hôte>` ; = Infos sur l'appli → Ouvrir par défaut).
      Vérifié : principale → secondaire = tâche de la secondaire ; retour = tâche de la principale ; une seule page par application.
      ⚠ Réglage PAR APPAREIL : à refaire si une des deux est réinstallée (nouvelle WebAPK = nouveau paquet).
      Historique de l'enquête :
      ~~NON RÉSOLU.~~ ⛔ La conclusion de 11h40 ci-dessous est FAUSSE pour le Fold —
      Quang 11h46 : *« je t'ai dit que c'est déjà fait […] c'est marqué que cette appli est déjà installée »*.
      11h47 : piste « appui long = minuteur sans geste utilisateur » (`manga_studio.html` appui long sur 📚, `setTimeout` au
      `pointerdown`) **réfutée sur le Samsung** : un VRAI appui long (`input swipe` 1,8 s) ouvre bien la WebAPK de la secondaire.
      11h48 : Samsung (Android 13, Chrome 154) — les 2 WebAPK sont « verified » pour leur domaine (`pm get-app-links`) alors que
      `/.well-known/assetlinks.json` est bloqué (401 / 302) sur les deux → ce fichier ne décide pas : piste écartée.
      11h50 : secondaire réinstallée sur le Samsung et LAISSÉE installée (sert à comparer avec le Fold).
      11h58 — **essai de Quang sur le Fold (décisif)** : les DEUX installées ; l'application lancée EN PREMIER n'a jamais de
      bandeau, l'autre (atteinte par l'appui long) s'ouvre DANS la fenêtre de la première avec le bandeau — et ça s'inverse selon
      celle qu'on lance. ⇒ sur le Fold, Chrome garde la navigation dans l'application courante au lieu de la confier à l'autre
      WebAPK (le Samsung, lui, la confie). Pas un problème d'installation.
      Piste à tester (Samsung puis Fold, **connexion ADB promise par Quang**) : bascule par une adresse `intent://…#Intent;scheme=https;end`
      (Android choisit l'application installée) au lieu de `location.href` ; repli = l'adresse actuelle.
      **Prochaine étape (déclencheur : accord de Quang)** : lire le même état sur le Fold (`pm get-app-links` des 2 WebAPK,
      lecture seule, ADB sans fil) et comparer ; ou Quang regarde « Infos sur l'appli → Ouvrir par défaut » de la secondaire.
      ~~CAUSE TROUVÉE, pas un défaut du code~~ (26/09 11h40, Samsung de test, CDP + `dumpsys activity`) :
      secondaire INSTALLÉE (WebAPK, « Installer » et non « Créer un raccourci ») → `espaceBasculer()` (inchangé, `location.href`) l'ouvre
      dans SA propre application : tâche Android distincte, en-tête violet, AUCUNE barre ; le retour rouvre la tâche existante de la
      principale (les 2 sens vérifiés). Secondaire DÉSINSTALLÉE → même geste = barre Chrome (✕ + adresse) DANS la tâche de la principale :
      **le symptôme de Quang, reproduit à l'identique**. ⇒ sur le Fold, la secondaire n'est pas (ou plus) une vraie application installée
      pour l'adresse actuelle (raccourci, ou installée depuis une ancienne adresse). Remède côté téléphone : supprimer l'icône, ouvrir la
      secondaire dans Chrome → ⋮ → « Installer et créer un raccourci » → **Installer**. `window.open(…, "_blank")` écarté : inutile ici.
      Manifestes publics (200 sans cookie) sur les deux ; noms identiques (« Manga Studio ») = seul inconvénient restant, cosmétique.
      ⏭ Proposé, NON codé (accord de Quang requis) : dans la secondaire hors application installée, un rappel discret « installe-la ».
      ⚠ La barre affiche l'ADRESSE de la secondaire en clair : raison de plus de l'installer. Samsung remis dans son état initial.
      Énoncé d'origine :
      (Quang 11h22-11h26, captures) : la secondaire, atteinte par l'APPUI LONG depuis la
      principale installée, s'ouvre DANS la fenêtre de la principale (`espaceBasculer` : `location.href = ESPACE.autre`) → onglet
      Chrome + bandeau qui apparaît / disparaît au défilement. Les deux sont installées ; leurs manifestes ont le MÊME nom
      (« Manga Studio / Manga », id /manga/) — indiscernables. Piste : en mode installé, `window.open(ESPACE.autre, "_blank")` pour
      qu'Android confie l'adresse à l'appli installée de la secondaire ; + un nom distinct neutre pour la secondaire. ⛔ À VÉRIFIER
      SUR UN VRAI TÉLÉPHONE (Samsung de test, les deux installées) — le choix d'appli par Android ne se simule pas.
- [x] **Lecteur vidéo v2.70.0 — commandes TOUJOURS affichées** (26/09 11h55, `app_patch_270_commandes.py`). Quang 11h49 : *« je
      préfère que ce soit affiché en permanence. Ensuite, si j'ai envie, je n'ai qu'à passer en plein écran »* → PAS de bouton ;
      hors plein écran plus aucun effacement ; l'effacement (3 s, un toucher ramène) ne vit plus QU'EN plein écran (⋯ → Plein écran) ;
      sortie du plein écran = barre rendue. Banc `test_lecteur_video_ui` **27/27** (F réécrit : 4 s sans effacement, plein écran,
      sortie) ; sabotage (garde plein écran retirée, app servie modifiée) → **rouge** ; voisins `test_video_nav_ui` 12/12 (lancer
      avec `PYTHONIOENCODING=utf-8` : sinon plantage cp1252 sur « ⏮ », pas un défaut), `test_selecteur_ui` 26/26.
      ~~Énoncé intermédiaire (11h48), remplacé~~ : *« une tempo qui
      fait que les boutons disparaissent automatiquement, je n'aime pas trop ; je préfère que ça reste affiché en permanence, ou que
      ça apparaisse / disparaisse selon si j'appuie sur un bouton […] à la rigueur je préfère tout le temps affichées »*) →
      défaut : affichées en permanence, plus aucun masquage automatique ; un bouton de la barre les masque, un petit bouton
      flottant les réaffiche ; choix retenu sur l'appareil. Toucher l'image = ⏯ inchangé. Banc + sabotage + version v2.70.0.
- [x] **Sélecteur — geste INVERSÉ : glisser la barre VERS LE BAS pour ouvrir** (v2.71.0, 26/09 12h25, `app_patch_271_geste_bas.py`).
      ⚠ Trouvé au VRAI doigt (Samsung) et invisible au banc : sous une barre collée en bas il ne reste que **49 px** de course
      (barre 804 → écran 853) ; le seuil de 50 px rendait le geste IMPOSSIBLE (le banc simulait 120 px). → seuil **24 px** vers le
      bas, geste net (|dy| > 1,5 |dx|). Vrais gestes 3 séries : haut 0/3 ouvert, bas 3/3. Bancs `test_selecteur_ui` 28/28,
      `test_selecteur_narr_pages_ui` 105/105 (glissés ramenés à 32 px = course réelle ; « vers le haut n'ouvre plus rien »
      ajouté) ; sabotage (ancien sens) → 2 KO. Samsung remis en veille.
      Énoncé : Quang 12h18 : *« je le
      déclenche plus facilement en scrollant vers le bas sans faire exprès […] c'est le même geste pour sortir d'une application
      sur un smartphone. Par contre, le contraire ne déclenche rien sur mon smartphone »* — il l'avait demandé ainsi à 11h05 ;
      le choix « vers le haut » (constat 11h05 : peu de course) est annulé par l'usage réel. Vers le haut n'ouvre PLUS rien ;
      bulle / titre / G inchangés ; fermer la feuille = glisser vers le bas SUR la feuille (inchangé). Bancs + vrai geste
      (`input swipe`) sur le Samsung, puis écran en veille.
- [x] **Barre de notifications Android visible** (v2.73.0, 26/09 12h40). Cause : `pwa/manifest.webmanifest` en `"display":
      "fullscreen"` (+ `display_override` fullscreen) — le SEUL de ses apps ainsi (Friday : pas de plein écran) ; le « clignotement »
      = Android qui réaffiche la barre un instant puis la recache. → `"display": "standalone"` (un seul fichier : la secondaire passe
      par le même proxy). Le plein écran du LECTEUR VIDÉO (⋯) reste. Vérifié sur le Samsung, application réinstallée :
      `display-mode: standalone` = vrai, heure + batterie visibles sur le fond sombre de l'app.
      ⚠ Piège payé : le manifeste est servi `Cache-Control: max-age=3600` → la 1re réinstallation a repris l'ANCIEN manifeste
      (cache Chrome) ; vider le cache puis réinstaller. `chrome://webapks` inaccessible par ADB/CDP (2 échecs, abandonné).
      ✅ **Fold de Quang, 26/09 12h55-13h00 (sur son accord)** : Quang 12h52 a signalé la barre toujours cachée — ses 2 WebAPK
      dataient du 23 et du 24/09 (jamais mises à jour). Débogage Chrome du Fold muet (2 échecs) → **v2.73.1** : lien du manifeste
      `?v=2.73.1` (adresse neuve = l'ancien manifeste en cache ne peut pas revenir). Désinstallées puis réinstallées depuis Chrome
      (pilotage par les TEXTES de l'écran, uiautomator), « liens compatibles » réactivés pour chacune. Mesuré par Android : barre
      d'état `visible=true` dans la principale ; vrai appui long → secondaire (sa propre tâche) `visible=true` ; retour → principale
      `visible=true`.
      ~~⏭ Chez Quang (Fold) : les applications installées se mettent à jour SEULES (Chrome relit le manifeste, en général
      sous 24 h ; au-delà d'1 h de cache). NE PAS réinstaller pour aller plus vite : une réinstallation = nouveau paquet =
      « liens compatibles » à réactiver (bandeau). **À vérifier** (déclencheur : Quang voit la barre, ou le 28/09) : après la mise
      à jour, la bascule principale ↔ secondaire reste sans bandeau.~~ → fait à la main le 26/09 13h00 (ci-dessus).
      Énoncé (Quang 12h22) : dans Manga Studio installée, la barre du haut (heure,
      batterie) est cachée et « clignote » parfois (apparaît brièvement puis disparaît) ; Friday et Generate Studio la gardent
      TOUJOURS visible → faire comme eux. Constat (lu 26/09) : manifestes `display: "fullscreen"` (principale ET secondaire).
      À comparer avec les manifestes de Friday / Generate Studio avant de toucher.
- [x] **Visionneuse — balayer L'IMAGE : vers la droite = suivante** (v2.72.0, 26/09 12h35, `app_patch_272_balayage_image.py`).
      C'était le balayage SUR L'IMAGE (`dx < 0 ? 1 : -1`, sens « livre ») ; la BARRE de la visionneuse allait déjà dans le bon sens
      (v2.61.0). Maintenant les deux vont pareil. Nouveau banc `test_balayage_image_ui.py` **14/14** (vrais événements tactiles
      CDP, 360 + 1280 : droite, droite, gauche, vertical = rien, zoomée = déplace sans tourner) ; `--mutation` (ancien sens) → 5 KO.
      Vrai doigt Samsung : 1 → 2 → 3 → 2. ⚠ `test_bibliotheque_ui.py` est PÉRIMÉ (bloque sur un `select` devenu invisible, avant
      le balayage — sans lien avec ce changement) ; ses 2 attentes de balayage sont déjà inversées. **Déclencheur** : prochaine
      modification de la bibliothèque. Énoncé :
      (Quang 12h26) : glisser VERS LA DROITE = image
      SUIVANTE, vers la gauche = précédente (« on l'avait inversé ailleurs, celui-là on l'a oublié »). Vérifier le sens des autres
      barres pour rester cohérent.
- [x] **Capture : « depuis la page 1 » cochée d'office + mémorisée** (v2.74.0, 26/09 13h12, `app_patch_274_page1.py` ; banc
      `test_capture_page1_ui.py` **10/10** à 360 + 1280 (appareil neuf = cochée, décochée/recochée survivent au rechargement),
      `--mutation` → 2 KO ; Quang 13h06 : *« en persistance mémoire, ou le
      laisser toujours coché d'office »*). Défaut = cochée ; si Quang la décoche, le choix est gardé sur l'appareil
      (`localStorage manga_cap_page1`). Sans risque : partir de la page 1 ne change rien quand l'onglet y est déjà.
- [x] **Pochette + fiche d'une série fraîchement capturée, SANS l'ouvrir** (v2.75.0, 26/09 14h15, `app_patch_275_serie_auto.py`).
      Quang 14h06 : la pochette ne se met à jour qu'à la 1re ouverture. **Régression de MA v2.67.1** : la fin de capture ouvrait
      le manga, ce qui déclenchait pochette (AniList) + fiche (tomes, dates) ; ouverture retirée (demande Quang) → plus rien.
      → `serieAuto(serie)` (mêmes conditions : capture finie, pas de pochette / fiche plus vieille que le dernier chapitre), appelée à
      l'ouverture ET en fin de capture pour **la série capturée, elle seule** — l'ouverture auto reste RETIRÉE (Quang 14h08 : « tu ne
      réactives pas »). ⚠ 1er jet rejeté par le banc : un balayage « séries capturées depuis 7 jours » visait **7 séries réelles**
      sans pochette (dont une masquée) → recherches AniList à chaque ouverture de l'app, voire mauvaise pochette. Banc
      `test_serie_auto_ui.py` **14/14** (sources + fin de capture SIMULÉES, appels interceptés : rien d'écrit) ; v2.74.0 servie → 4 KO.
- [x] **v2.76.0 (Quang 14h12 : « go »), `app_patch_276_pochette_tot.py`** : POCHETTE dès le 1er chapitre capturé, pendant la
      capture (`pochetteTot`, manga tout neuf compris ; une fois ; seulement sans pochette). Banc `test_serie_auto_ui.py` **19/19**
      (en cours : 0 chapitre = rien, 1er fini = pochette sans fiche, manga neuf = pochette) ; v2.75.0 servie → 2 KO. Énoncé : (titre connu, dossier
      créé). La FICHE doit attendre la fin : elle range les chapitres par tome d'après leur NUMÉRO (v2.8.5 : lancée pendant la
      capture → Solo Leveling ch.1 sans tome). **Déclencheur** : accord de Quang.
- [x] **N° suggéré d'après l'adresse : volume entier « …/vol-N/ » = ch. N** (v2.77.0, 26/09 15h05, `app_patch_277_num_volume.py`).
      Quang 14h57 (capture Solo Leveling en volumes, 740 p. chacun, « jusqu'au 15 ») : l'app ne devinait pas « 2 ». Vérifié dans
      manga-fetch 0.6.0 (`RE_VOL`, `vol_suivant`) : vol-N = ch. N, enchaînement dans l'ordre du site, arrêt net après vol-15
      (vol-16-chapitre-179-5 = 179,5 > 15) → sa capture MARCHE telle quelle. Seule la SUGGESTION de l'app ignorait vol-N (le
      format mixte était déjà lu). Banc `test_num_adresse_ui.py` **13/13** (anciens formats compris, « volcano-hero » = rien) ;
      v2.76.0 servie → 4 KO ; onglet réel de Quang → « 2 ».
- [x] **Site Mangas Origines (VF) validé et ajouté** (26/09 15h10, Quang 15h02). Règle 22/09 respectée : capture RÉELLE + enchaînement
      testés — The Beginning After the End ch.1→2 (choix de Quang, gardés DANS sa bibliothèque à sa demande) : 44 + 51 pages,
      0 image vide, 145 s, contenu vérifié à l'œil (crédits « Chapitre 1 / 2 »). Nouveau banc `scripts/test_site_nouveau.py`
      (lit l'adresse réelle du chapitre sur la page de la série ; dossier temporaire, ou bibliothèque si un titre est donné).
      Fiche MangaDex posée. ⚠ **Pochette introuvable sur AniList** : 8 titres essayés (anglais, coréen, japonais…), AniList
      répond 404 même au titre exact (One Punch-Man / Solo Leveling répondent) → la série n'y est pas. **Piste (non codée,
      déclencheur : accord de Quang ou 2e série sans pochette AniList)** : recours aux couvertures MangaDex quand AniList échoue.
- [x] **Gestes de FENÊTRE autorisés pendant une capture** (26/09 15h20, Quang 15h15 : « redimensionner […] et déplacer, testé
      hier, aucun problème ; la sécurité datait d'avant les tests »). Confirmé par les mesures du 25/09 22h25 (déplacer ×38 = aucun
      effet ; redimensionner ×165 = aucune image perdue, fausse alerte possible). ⚠ « Ranger » change AUSSI la taille (place
      retenue) → refusé si la place est trop petite. Proxy `patch_pilote_fenetre_capture.py` (+ `.diff`) : liste
      `PILOTE_OK_EN_CAPTURE` = taille / memoriser / etat / ranger ; fermer, onglets, clics : toujours bloqués ; `scripts/cdp_mini.py`
      `en_capture` (ranger vérifie la taille, fermer refuse). Principale relancée 15h18 ; secondaire relancée au repos 15h21
      (veilleur, PID vérifié).
      Banc `scripts/test_fenetre_pendant_capture.py` **8/8 PENDANT la vraie reprise de Quang** (Solo Leveling vol.2) : taille OK,
      ranger OK, fermer refusé, clic refusé, place trop petite refusée sans bouger, `fenetre.json` restauré à l'octet, capture
      continue. + **« Arrêter maintenant » testé en vrai par Quang** (1re fois) : coupé à 63 p., AUCUN vol.2 partiel dans la
      bibliothèque, « Reprendre » proposé et utilisé. **Bilan vol.2 (fenêtre agrandie + rangée PENDANT sa capture)** :
      219/219 images, découpées en 912 pages (218 bandes, 1 coupe hors gouttière), 0 vide, hauteur médiane 1 218 px (vol.1 : 1 197).
      ⚠ Piège : le découpage tourne APRÈS la ligne « OK : N/N » — ne pas juger les pages avant l'événement `[webtoon] bandes découpées`
      de `%LOCALAPPDATA%\manga-fetch\events.log` (fausse alerte de ma part à 15h29).
- [x] **Lien visuel Traduction / Musique → Vidéo + surbrillance de l'étape suivante — variante B, v2.79.0** (26/09 16h55,
      Quang 16h30 « B » ; `app_patch_279_liens_video.py`). « → 🎬 » sur Traduction / Musique (+ Narration sur PC) ; ligne Vidéo =
      pastilles 🎙 / 🌐 FR|VO / 🎵 N (vert prêt, pointillé facultatif absent ; sous l'état sur téléphone) ; UNE lueur = étape
      suivante (Narrer → Traduire si VO → Faire la vidéo), jamais la musique, coupée si « réduire les animations ». Banc
      `test_liens_video_ui.py` **44/44** (3 vrais chapitres, 1280 / 360 / 360 réduit) ; v2.78.0 servie → rouge ; voisins fiche 31/31,
      sonde clignotement 0. Trouvés sur CAPTURE (pas par les chiffres) : pastilles qui écrasaient l'état Vidéo à 360 → 2e ligne ;
      flèche qui mangeait l'état Narration à 360 → masquée sur téléphone. ✅ **v2.79.1** (Quang 16h50 « tout ce que tu
      trouves à corriger, tu le fais ») : état d'un chapitre NON narré à 360 px 0 → 159 px (coûts en 2e ligne) ; plus de
      « Traduire » dans l'en-tête si déjà dans la langue cible. Banc 50/50, v2.79.0 servie → 5 KO ; fiche 31/31 (le test du relais
      « Traduire » choisit une langue cible différente). Énoncé : Constat (code lu) :
      la narration ne dépend de rien ; `video_chapitre.py` prend les pages traduites si elles existent (sinon VO) et la musique si
      choisie → traduire / choisir la musique AVANT la vidéo, pas avant la narration. Tout reste FACULTATIF, le lien doit se VOIR.
      Maquette `maquette_liens_video_v1.html` (A groupe « pour la vidéo », B pastilles d'ingrédients sur la ligne Vidéo, C rail) ;
      avis Claude : B. **Déclencheur** : choix de Quang.
- [x] **Fiche du chapitre : ordre logique Narration → Traduction → Musique → Vidéo** (v2.78.0, 26/09 16h28, Quang 16h20-16h22).
      Avant (v2.60.0) : Narration, Vidéo, Traduction, Musique — seule vue à ne pas suivre les Réglages / le lot. `CL` réordonné et
      `clMaj()` impose l'ordre des 4 blocs (`after`). Banc `test_chapitre_compact_ui` **31/31** (ordre mis à jour, hauteur mesurée
      jusqu'au bloc Vidéo) ; v2.77.0 servie → 2 KO ; `sonde_clignotement_video` : 0 changement de hauteur du bloc Vidéo déplacé.
- [x] **Un seul suivi de capture à la fois** (v2.79.2, 26/09 19h00, `app_patch_2792_suivi_unique.py`). Trouvé dans le journal client
      du Fold (`ComfyUI/logs/log-manga-live-mobile-*.json`) : à 12h54:31, ~40 lignes « capture en série terminée » en 50 ms — en
      arrière-plan les suivis (1 / 1,5 s) s'empilaient puis finissaient ensemble (40 rechargements, et 40 pochettes / fiches en
      v2.75+). Banc `test_suivi_unique_ui.py` **5/5** ; v2.79.1 servie → **40 / 40** reproduits (4 KO). `test_serie_auto_ui` vert.
- [ ] **Bandeau « arrêtée à ta demande… Reprendre » toujours affiché sur le Fold** (Quang 18h48-18h51, hors de chez lui) alors
      que le bilan serveur est « jusqu'au ch. 15 : fait » (18h24). Mécanisme vérifié sain en test (s'efface à la vérif des 60 s) ;
      la page du Fold date de 13h19 (v2.77.0). Capture de Quang 19h02 : c'est bien le BANDEAU (Ouvrir / Reprendre), pas `capEtat`.
      Vérifié PAR Cloudflare (en-têtes réels) : `capture_derniere` et `fetch_status` frais (`no-store`, DYNAMIC) et justes →
      ni serveur ni cache. Cause NON prouvée : `capAlerteVerifier` avalait ses erreurs (`catch { return; }`) et le journal du
      Fold est muet depuis 13h19. **v2.79.3** (`app_patch_2793_bandeau_trace.py`) : échec ÉCRIT au journal (une fois par type),
      effacement écrit, re-vérification au RETOUR dans l'app (visibilitychange / pageshow / focus). Banc
      `test_bandeau_capture_ui.py` **7/7** ; v2.79.2 servie → 3 KO. **Déclencheur de reprise** : la prochaine fois que le
      bandeau résiste sur le Fold (après rechargement en v2.79.3) → lire `ComfyUI/logs/log-manga-live-mobile-*.json`.
- [x] **Relance de la secondaire** (au repos) — ✅ 26/09 11h50 par le veilleur (2 relevés vides, PID = `espace_prive.py`),
      `GET /manga/bibliotheque` rend maintenant `videos_pos` : reprise de position commune PC / téléphone sur les DEUX applications. : active `video_pos` côté serveur pour elle (patché sur disque, pas relancée à 11h20).
      26/09 11h35 : principale ✅ (`GET /manga/bibliotheque` rend `videos_pos`), secondaire ❌ (clé absente) et OCCUPÉE (lot de
      narration + vidéo) → veilleur lancé : relance dès 2 relevés vides à 1 min (procédure HANDOFF § 3.7), délai max 3 h.
- [x] **B — Bancs du sélecteur, contextes NARRATION et PAGES** (26/09 11h35) : `scripts/test_selecteur_narr_pages_ui.py` **100/100**
      à 360/476/704/933/1280 (titre / glisser / G, courant en vert, sans narration = grisé + raison, filtre, n° absent → plus proche,
      aller à un autre chapitre narré, « à l'aveugle » = pas de sommaire, Échap ne ferme QUE le sélecteur ; visionneuse : « Aller à la
      page (N) », n° exact, page absente → la plus proche, G). Sabotage `--mutation` (visionneuse débranchée + garde « à l'aveugle »
      retirée) → **6 KO, les bons**. Aucun code d'app modifié → bancs voisins non rejoués.
- ~~**B — Bancs** (énoncé d'origine)~~ → ✅ couvert ci-dessus : app réelle, 360/476/704/933/1280, gestes simulés (touch), sabotage rouge, bancs voisins
      (`test_activite_ui`, navigation, visionneuse).
- [ ] **C — Clôture** : ROADMAP, HANDOFF-reprise, commit + push.


## 4-quindecies. FEUILLE DE ROUTE — « JUSQU'AU DERNIER PARU » + CHAPITRES DÉJÀ PRÉSENTS *(25/09/2026 23h38-23h44, demandes Quang : « trace une feuille de route bien détaillée et suis-la […] ne te disperse pas »)*

**Demandes (Quang, 25/09)** : (a) 23h38 — un bouton « jusqu'au bout » au lieu de taper le dernier n° ; « final » induit en
erreur (série pas finie). (b) 23h42 — « une vraie sécurité pour que le script ne reste pas bloqué, que l'on ne spamme pas la
fenêtre et le site » ; plafond de 50 levé SEULEMENT avec cette sécurité ; décisions déléguées (plafond, sites partiels).
(c) 23h43 — demander 1 → 10 en ayant déjà 2-5 : sauter ce qui est là, compléter le reste, « sans recommencer le travail ».
Maquette : `maquette_dernier_paru_v1.html` (v1, **à valider par Quang avant tout code**).

### Constat (lu dans le code, 25/09 23h40 — re-vérifier avant de coder)
- Le site décide déjà si l'on enchaîne (`capEnchSite`, v2.17/v2.18) : la nouvelle puce suit la même règle, rien à inventer.
- Fin de site (« aucun chapitre après ») et « série terminée » (marque Final, 0.7.5) : déjà reconnues par manga-fetch.
- Plafond : `limite = 50 if jusqua is not None else suite` (`manga_fetch.py` boucle série) ; aucune décision écrite derrière
  (borne de prudence v0.4, relevée le 24/09 18h49). Taper 9999 aujourd'hui = faux message « le ch. 9999 n'est pas encore paru ».
- Déjà présent : en série, `un_chapitre` saute un chapitre au manifeste présent (`return 0`, aucune image), un chapitre à
  moitié (sans manifeste) est refait. **Trou 1** : si le 1ᵉʳ chapitre existe, l'app ne propose que « le remplacer ? » — non =
  toute la série annulée. **Trou 2** : le bilan compte les sautés dans « faits ». Le saut attend quand même le lecteur (≤ 90 s).
- Le proxy dérive total, « objectif tenu » et reprise de `jusqua` (`_studio_llm_proxy.py` ~8857, ~9873, ~9909, ~9970) :
  le nouveau mode le traverse → patch proxy obligatoire.

### Décisions (déléguées par Quang 23h42, prises par Claude)
- Nom : **« Jusqu'au dernier paru »** (vrai que la série soit finie ou non).
- Plafond 50 → **supprimé**, remplacé par les sécurités ci-dessous + un **filet de 300** chapitres d'écart par lancement.
  ~~Les modes « jusqu'au ch. » et « + N » gardent 50~~ → **Quang 23h51 : 300 PARTOUT** (« jusqu'au ch. » : écart > 300 refusé
  à la saisie, app ET proxy ; « + N » ≤ 300 ; filet commun dans la boucle, car les x.5 peuvent dépasser l'écart).
- Sites **partiels 🟠** : puce ouverte (au pire un arrêt orange avec « ▶ Reprendre », jamais de boucle ni de perte).

### Étapes (dans l'ordre, une à la fois ; chacune = banc réel + sabotage rouge + commit)
- [x] **E0 — Validation de la maquette** par Quang. ✅ 25/09 23h49 (« c'est tout bon pour moi »).
- [x] **E1 — manga-fetch 0.8.0, mode `--jusqua-fin`** : pas de borne ; fin de site → arrêt « à jour : le ch. N est le dernier
      paru » (texte DISTINCT de « dépasse la borne » et de « série terminée ») ; code retour 0 (demande tenue).
      Vérifier le cas « chapitre suivant manquant » (trou de numérotation) : sans borne, `_choisir_suivant` exige c+1 → à
      aligner sur le mode `jusqua` (sauts tolérés), la sécurité E2 prenant le relais au-delà de 10.
- [x] **E2 — Sécurités (tous modes de série, sauf mention)** :
      (1) progression strictement croissante — existe, ajouter un test ; (2) **empreinte** : pages du chapitre identiques
      à celles du précédent → arrêt ; (3) **saut > 10 numéros** → arrêt avec reprise (mode dernier-paru) ; (4) **pause 3 s**
      entre deux chapitres, sautés compris ; (5) **filet 300** (mode dernier-paru) ; (6) chaque arrêt de sécurité journalisé
      (`events.log`, catégorie `sécurité`) avec la raison lisible.
- [x] **E3 — Déjà présents** : bilan manga-fetch sépare `captures` et `deja_la` (ligne SÉRIE + `log_evt`) ; proxy les
      transmet ; app : bilan « N capturés (…), M déjà là (…) » ; 1ᵉʳ chapitre présent en série → dialogue « ⏭ Le garder et
      continuer » (défaut) / « ♻ Le refaire » / Annuler (dialogue actuel inchangé pour un chapitre seul).
- [x] **E4 — Proxy (`proxy-patch/patch_dernier_paru.py` + `.diff`)** : accepter `fin: true`, passer `--jusqua-fin`, total
      inconnu (« N faits », pas « N sur ? »), « tenu » = arrêt « à jour » ou « série terminée », reprise qui garde le mode.
      Testé sur une COPIE, relance AU REPOS (principale puis secondaire, procédure du HANDOFF-reprise § 3.7).
- [x] **E5 — App v2.67.0** : 4ᵉ puce `data-serie="fin"` (option du `<select>` caché aussi), résumé « puis tous les suivants,
      jusqu'au dernier paru », grisée comme les autres, ligne d'activité « N chapitre(s) fait(s) · jusqu'au dernier paru »,
      bilans vert « à jour » / orange « arrêtée par sécurité » + reprise. Version aux 3 endroits.
- [x] **E6 — Bancs** : vraie capture « dernier paru » sur un site de test court de la principale (fin atteinte, bilan vert) ;
      1 → N avec des chapitres déjà présents (aucun recapturé : dates des manifestes inchangées) ; chaque sécurité sabotée →
      rouge ; bancs voisins (`test_arret_capture`, `test_reprendre_ui`, `test_enchainement_ui`) ; largeurs 360/476/704/933/1280 ;
      les DEUX applications. `test_capture_serie_ui.py` périmé : le réparer ici (il touche l'étape 4).
- [x] **E7 — Clôture** : ROADMAP (entrée datée, constats barrés), HANDOFF-reprise à jour, commit + push. Aucun nom de la
      secondaire nulle part (dépôt PUBLIC).

### Livré (26/09/2026 00h40) — manga-fetch 0.8.0 · proxy `patch_dernier_paru` · app v2.67.0
- Champ du proxy nommé **`dernier_paru`**, PAS `fin` : le bilan a DÉJÀ un champ `fin` (heure de fin = clé « déjà vu » de
  l'app) — un `fin: true` l'aurait écrasé et cassé tous les bandeaux (repéré avant livraison).
- **Défaut trouvé par le banc réel** : sur MangaDex la raison est « **MangaDex :** aucun chapitre après le 143… » → les 3
  tests en `startswith` rataient la fin (bandeau bleu au lieu de vert, « tenu » faux). Corrigé en « contient », aux 3
  endroits ; la reconnaissance « série terminée » (0.7.5) avait le même défaut sur MangaDex → corrigée aussi.
- Bancs : `test_dernier_paru.py` **19/19** (141 → 143 réels, 142 déjà là non touché, départ sur un déjà-là, bandeau vert,
  puce grisée, 5 largeurs ; mutation app → rouge) · `test_serie_securites.py` **16/16** (mutation 15/16) ·
  `test_capture_serie.py 8190` **27/27** (cas « suite 51 refusée » → 301 ; assertion « dépasse la borne » périmée depuis
  0.7.5 → « jusqu'au ch. 308 : fait ») · `test_capture_serie_ui.py` **17/17** (réparé : puces au lieu du sélecteur caché,
  + puce « dernier paru ») · `test_arret_capture` **14/14** · `test_reprendre_ui` **112/112** · `test_activite_ui` **64/64** ·
  `test_enchainement_ui` 8192 **12/12**, 8190 **7/8** (🟠 constaté 26/09 : la fenêtre principale n'avait aucun onglet
  d'un site qui n'enchaîne pas — condition du banc, pas un défaut ; le cas est couvert sur 8192 et par `test_dernier_paru`).
- ⚠ Non testé en réel (impossible à provoquer sur un vrai site) : saut > 10, contenu identique, filet 300 → couverts par
  les fonctions et la lecture du source (`test_serie_securites`).
- Relances : principale via `relance-proxy.ps1` (×2) ; secondaire relancée AU REPOS (bilan de Quang conservé).
- 🔒 Contrôle dépôt public à la clôture : 4 fichiers suivis contenaient encore des noms de la secondaire (commentaires,
  maquette, données d'un banc — antérieurs à cette session) → neutralisés, `test_choix_manga_ui` **127/127** inchangé.

### Hors périmètre (noté, non fait)
- Le bouton d'arrêt pour une vidéo, la fausse alerte au redimensionnement : inchangés (déclencheurs dans HANDOFF-reprise § 2).
- ~~🔴 **(constaté 26/09, manga-fetch 0.7.6/0.8.0) Webtoon découpé en bandes PRESQUE CARRÉES → capture d'1 page, ÉCHEC.**~~
  → ✅ **couvert par manga-fetch 0.8.1 (26/09 00h55)** : B1 rouge reproduit sur le VRAI onglet (0 bande / 213) ; B3 **186 prises
  + 27 quasi vides écartées (< 10 Ko, règle existante) = 213/213**, sans ÉCHEC ; mutation (code 0.8.0) → rouge ; B4
  `test_manga_fetch` 9/9, `test_arret_capture` 14/14, `test_dernier_paru` 19/19, `test_serie_securites` 16/16. Banc :
  `scripts/banc_bandes_carrees.py <port> <filtre d'onglet> [manga_fetch à tester]` (sortie + journal TEMPORAIRES).
- 🔴→✅ **(constaté 26/09 00h58 par Quang : « des bulles découpées en plein milieu ») la 0.8.1 capturait les tuiles mais ne les
  DÉCOUPAIT pas** (critère « bande » = ratio > 3 ; tuiles 720×700 = 0,97). État des lieux (`scripts/etat_decoupe.py`, lecture
  seule) : secondaire, 2 séries touchées — la série en cours dès le ch. 16 (0.8.1, cette nuit) et une série de 54 ch. capturée
  le 25/09 16h-21h (tuiles ratio 2,08, jamais découpées : défaut ANTÉRIEUR). **manga-fetch 0.8.2** :
  1. ruban = ≥ 5 images consécutives de même largeur dont ≥ 50 % des raccords CONTINUENT le dessin (mesuré : vrais rubans
     62-83 %, pages bonus d'un manga 33 % → exclues) ;
  2. à la capture, les tuiles-espaces (< 10 Ko, largeur de colonne) sont GARDÉES, déduplication comprise (27/213 perdues avant) ;
  3. contrôle final : un ruban en tuiles passe sans image ≥ 800 px (ch. 21 vécu : 222 tuiles capturées puis rejetées) ;
  4. coupes : 2ᵉ recours « verticalement stable » (fond rayé « papier », ≥ 40 lignes), pages jusqu'à 7H avant de forcer,
     gouttière stricte COURTE (< 12 lignes) seulement si son voisinage est stable (une bulle à pointes était coupée entre ses
     deux lignes de texte — faille préexistante), coupe forcée sur le voisinage le plus stable.
  Vérifié À L'ŒIL (planches de coupes) + `test_decoupe_rubans.py` **15/15** (copies ; mangas non touchés) + vraie recapture
  ch. 21 : 166 raccords dans le dessin → **0** ; mutation (0.8.1) rouge ; non-régression 9/9, 14/14, 19/19, 16/16.
  **Redécoupés** (`scripts/redecouper.py`, sauvegarde intégrale dans `<racine>/_avant_redecoupe/`) : série en cours ch. 1, 4, 9,
  16-20 (584 → 2), série de 54 ch. (4 061 → 46), 1 ch. d'une autre série (3 → 0), Solo Leveling ch. 1 (3 → 0).
  ⬜ **Refusé exprès** : Ragnarok ch. 2 (narration + vidéo + cases liées aux numéros de page). ⬜ 7 ch. de la série de 54
  gardent 3-5 coupes (site sans aucun espace, tuiles-espaces perdues à la capture) : seule une recapture ferait mieux —
  déclencheur : si Quang le demande. Mangas (Boruto, Claymore, Noritaka) signalés par la mesure = doubles pages, rien à faire.
- ✅ **26/09 02h25-02h40 — fin du webtoon en cours (demande Quang)** : ch. 21 → 24 capturés en « dernier paru » avec la 0.8.2,
  0 coupe forcée / 0 raccord dans le dessin, planche vérifiée à l'œil (Quang : « le format est correct »). Le ch. 21 de 01h07
  n'était PAS un effet de son « Arrêter après ce chapitre » (posé 01h05) : le chapitre avait échoué au contrôle 800 px AVANT
  le point d'arrêt ; son drapeau restant est effacé par le serveur à tout nouveau lancement.
- ✅ **manga-fetch 0.8.3** : le site ANNONCE un ch. 25 dont la page n'a aucune image (pas encore publié) → en « dernier paru »,
  « aucun chapitre après le 24 sur ce site (le ch. 25 est annoncé mais sans aucune image) », code 0, bandeau vert « à jour »
  (au lieu de « le chapitre 25 a échoué »). Seul le cas AUCUNE image ; tout autre échec reste un échec. Vrai test (onglet
  jetable, sortie temporaire) : 0.8.3 code 0 / 0.8.2 « a échoué » (mutation rouge).
- ✅ **26/09 02h46-03h02 — « fais le nécessaire, occupe-toi des images » (Quang)** :
  - Ragnarok ch. 2 : `redecouper.py … --ecarter-lies` (option nouvelle, accord explicite) → images redécoupées 8 → 0 raccords
    dans le dessin (107 → 95 p.) ; **narration + cases.json retirées du chapitre** (elles décrivaient les anciennes pages),
    gardées dans `sources/_avant_redecoupe/solo-levelng-ragnarok__ch_2__…` (SEULE copie de la narration : ne pas effacer
    sans demander) ; vidéo mp4 intacte.
  - 7 ch. de la série de 54 **recapturés** (0.8.3, tuiles-espaces gardées) : 4→3, 3→3, 4→2, 4→4, 3→2, 5→4 ; ch. 37 moins bon
    (6→9) → ancien REMIS automatiquement. ⇒ ce site enchaîne des fonds dégradés SANS espace : 2-4 coupes/chapitre = la limite
    (sauf pages démesurées). Rien de plus à faire.
- 🔴→✅ **(signalé par Quang 03h03, capture d'écran) « banc raijin » apparu dans la bibliothèque** = Ragnarok ch. 2 : repartir des
  originaux remettait le manifeste de CAPTURE (titre de banc d'origine) → l'app le rangeait dans une autre série. Corrigé à la
  main (titre + slug d'avant) ; `redecouper.py` garde désormais tout le manifeste ACTUEL sauf pages/decoupe/notes (test sur
  copie : OK ; ancien script → « banc raijin », rouge). Contrôle des 210 chapitres : slug = dossier partout, aucun autre écart.
  Vécu par Quang sur la secondaire le 25/09 23h56 (ch. 16 d'une série, arrêt « capture tronquée à 1 page »). Mesuré en
  lecture seule dans l'onglet : 210 bandes DISTINCTES, 208 en 720×700 (ratio 1,03). `collecter()` écarte les ratios
  0,93-1,15 (avatars/logos) et ne réadmet une bande de la largeur des pages qu'après **3** pages déjà prises à cette
  largeur (v0.7.3) — ici une seule passait (720×1161) → blocage au démarrage. Le contrôle final a bien crié (212
  manquantes) : aucune fausse réussite. **Remède proposé** : amorcer la largeur de colonne sur le DOCUMENT (largeur
  commune à ≥ 5 grandes images) et non seulement sur les pages déjà prises. **Déclencheur : accord de Quang (question
  posée le 26/09 à la livraison) ; tant qu'il n'est pas fait, « Reprendre au ch. 16 » échouera pareil.**
  → **Accord Quang 26/09 00h31 (« carte blanche »)** — étapes : B1 reproduire l'échec avec 0.8.0 sur le VRAI onglet du ch. 16
  (fenêtre 9224, sortie + journal TEMPORAIRES, aucune donnée de Quang touchée) ; B2 manga-fetch 0.8.1 : largeur de colonne
  amorcée sur le document ; B3 même capture → toutes les bandes ; B4 non-régression (test_manga_fetch, test_arret_capture,
  test_dernier_paru) ; B5 ROADMAP + commit.


## 4-terdecies. COÛTS — LA « RÉFLEXION » DE GEMINI *(24/09/2026 14h40, question Quang sur les 4,43 $ du repérage)*

> Quang : *« si c'est pour économiser la moitié, par exemple 15 $ sur 30 $ d'utilisation actuelle, ça vaut le coup […]
> si tu penses que ça peut marcher, que tu peux optimiser, fais-le. »*

**Où va l'argent (registre, septembre, 46,36 $)** : narration 30,42 $ · traduction 15,76 $ · karaoké 0,13 $ ·
« Précédemment » 0,05 $. Dans la narration (postes connus) : voix 5,92 $ · analyse des pages 4,89 $ · **repérage des
noms 4,00 $** · récit 0,15 $.
**Trouvé dans le code** : aucun appel Gemini ne bornait sa « réflexion » (facturée au prix de la sortie, 3,75 $/M).
`narrate_chapter` **2.8.0** : `MANGA_GEMINI_REFLEXION` (analyse + traduction, vide = défaut Google, inchangé) et
`MANGA_GEMINI_REFLEXION_NOMS` (repérage des noms, **défaut « minimal »**).
**Mesures** (0 $ de régression possible sans elles) :
| Banc | Réflexion par défaut | « low » | « minimal » |
|---|---|---|---|
| Coût analyse + noms, OPM ch.301 (17 p.) | 0,19-0,20 $ | 0,10-0,11 $ | 0,063 $ |
| Fidélité vs référence écrite à la main (recalée +2, cf. piège) | 9 et 9 graves | 9 et 8 | 9 et 9 |
| OPM ch.2, 2 juges À L'AVEUGLE qui VOIENT les pages (Gemini / Kimi K3) | — | défaut préféré 7-2 (Gemini) · **égalité 4-4** (Kimi) · 0 grave | défaut préféré **10-2 et 7-3**, 1 grave chacun |
| Noms trouvés (4 passages) | 5 noms, **2 oubliés 1 fois sur 2** | les 5 à chaque fois | les 5 à chaque fois |
**Traduction** (banc `banc_reflexion_trad.py`, OPM ch.3, 56 bulles, 2 juges à l'aveugle) : défaut 0,168 $ ·
« low » 0,101 $ (−40 %) · « minimal » 0,099 $. DeepSeek : défaut 100 % / low 98 % / minimal 98 % ; Kimi : défaut 86 % vs
low **90 %**, défaut 92 % vs minimal 85 %. Défauts visibles : low « LE **LE** ROI DES BICEPS » (guillemets perdus),
minimal ajoute des gloses « Fugao (visage renfrogné) ». ⇒ **traduction INCHANGÉE** (défaut Google) ; « low » en réserve
(`MANGA_GEMINI_REFLEXION=low`). ~~**Déclencheur** : un 2ᵉ banc sur un autre chapitre sans défaut visible, ou Quang qui
choisit l'économie (~6 $/mois au rythme de septembre).~~ → **2ᵉ banc FAIT (24/09 17h10), décision CLOSE : traduction =
réflexion complète.** Black Jack ch.1 (ja→fr, 83 bulles) : défaut 0,224 $ / low 0,131 $ (−41 %) ; DeepSeek 92 % vs 88 %,
Kimi 87 % vs 89 %, mais les fautes de « low » sont de vraies fautes : mot inventé (« rontonnes »), contresens (« EIDAI,
BOUGE ! »), anglais dans une bulle (« Sigh... »), vouvoiement perdu, sens changé (« touché à la poitrine »). Règle Quang :
une erreur même petite est grave. « **medium** » mesuré aussi : −7 % (Black Jack) / 0 % (OPM) en traduction, et PLUS cher
que le défaut en analyse (0,079 vs 0,070 $) → sans intérêt. **Déclencheur de réouverture** : un nouveau modèle Gemini.
⇒ **Décision (Claude, feu vert Quang « fais-le »)** : réflexion **minimale pour le seul repérage des noms** (il ne
fixe que des noms ; le texte du récit vient de l'analyse, qui garde sa réflexion complète). Confirmé sur la référence :
**9 et 6 graves** (vs 9 et 9), coût analyse+noms **0,10-0,11 $ au lieu de 0,19-0,20 $ (−48 %)**. Supprimer la réflexion
de l'ANALYSE est **refusé** (dégrade, 2 juges d'accord) ; « low » sur l'analyse = **en réserve** (0 grave, mais 1 juge
sur 2 préfère le défaut) — décision de Quang s'il veut −40 % de plus sur l'analyse.
**Piège payé** : `sources/one-punch-man/ch_301/reference_faits.json` décrit la capture d'ORIGINE (19 p., dont 2 de
crédits) ; la capture actuelle en a 17 → page n = référence n+2. Sans recalage, tout était « grave » (faux banc).
La référence de Claymore ch.1 a disparu à la recapture du 23/09.
**Modération réelle (§ 4-decies, essai demandé)** : 669 pages analysées + 521 traduites depuis le 21/09 → **0 refus
réel** (les 14 du journal = mes bancs simulés). Sonde `scripts/sonde_moderation.py` sur **Claymore ch.2** (le plus
violent) : **Gemini 178/178 acceptées** (0,20 $), **Kimi K3 20/20** (échantillon, 0,29 $). ⇒ La violence ne déclenche
rien ; un refus réel viendra du contenu sexuel (cf. « contenu adulte à venir »), qu'on ne teste pas sans série réelle.

## 4-duodecies. JAUGE VRAM VENTILÉE PAR MOTEUR *(24/09/2026 15h11, demande Quang — ✅ LIVRÉ v2.13.0, 15h30)*

> Quang : *« je crois qu'on l'a fait sur Generate Studio d'une certaine manière, mais fais-le à ta façon […] des
> couleurs afin de distinguer quel moteur occupe quelle quantité de RAM. Le gris représente le système, et les couleurs
> l'application. »*

**Mesuré avant de construire** (sinon on aurait bâti sur du faux) : sous Windows (pilote en mode WDDM), **aucune source
externe ne ventile la VRAM par processus** — `nvidia-smi --query-compute-apps` rend `[N/A]` pour tous, et un processus
CUDA de 1,5 Go est **invisible** dans les compteurs « GPU Process Memory » (alors que nvidia-smi voit bien +1,7 Go) ;
`dwm.exe` y annonce 14,5 Go pour 2,9 Go réellement utilisés. ⇒ Comme Generate Studio, **chaque moteur déclare sa part** :
- ComfyUI (:8188 `/system_stats`), musique Generate Studio (:8388 `/vram`), **Ollama** (:11434 `/api/ps`, `size_vram`) ;
- **nos scripts** (voix locale `tts_local` 1.2.0, traduction/effacement `traduire_chapitre` 1.99.1, cases `cases_video`
  1.0.1) : `scripts/declaration_gpu.py` écrit toutes les 3 s `sources/_gpu/<pid>.json` = `torch.cuda.memory_reserved()`
  (n'initialise jamais CUDA lui-même) ; un battement > 15 s ou un PID mort ne compte plus, un orphelin > 60 s est rangé.
- `scripts/vram_parts.py` (à chaud, `GET /manga/vram`, diff `proxy-patch/_studio_llm_proxy_vram_v2130.diff`) : total =
  nvidia-smi ; **gris = total − parts déclarées** (calculé, jamais deviné) ; les 3 moteurs interrogés en parallèle
  (un port fermé coûte ~1 s sous Windows) ; cache 4 s.
**App** : barre en segments (ComfyUI violet · voix orange · traduction turquoise · cases jaune · Ollama rose · musique
vert · gris = système et autres applis) ; le niveau de mémoire LIBRE (seuils SDXL 8 / 4 Go) passe sur la couleur du
chiffre ; un toucher sur la jauge = légende en Go (+ « Libre »), toucher ailleurs / Échap = fermée. Repli sur l'ancienne
barre si le proxy n'a pas la route.
**Banc** `test_vram_ui.py` 10/10 (vrai processus CUDA 1,5 Go déclaré « voix » + déclaration « cases » ; couleurs, largeurs =
parts/total, légende, 360 px, retour au seul gris quand tout s'arrête) ; non-régression 19/19, 18/18, 18/18, 320 cas.
~~**Limite connue** : chaque moteur a ~0,3 Go de contexte CUDA qu'il ne déclare pas → compté dans le gris~~ → **v2.13.1
(Quang 15h39 : « ton processus devrait afficher une couleur »)** : vu en réel, la détection de la traduction ne
déclarait que 30 Mo (filet invisible) pendant que le gris prenait +190 Mo. Chaque moteur PyTorch compte désormais
**+230 Mo de contexte estimé** (mesuré 190-275 Mo ; Ollama exclu, son chiffre l'inclut) — dit « estimation » dans la
légende. Vérifié en direct : traduction 324 Mo, gris revenu à 2,9 Go (son niveau avant le lancement). Les moteurs de Generate Studio autres que la musique (ComfyUI est partagé) apparaissent sous « ComfyUI ».

## 4-decies. MODÉRATION — CONTINUER, PRÉVENIR, LAISSER QUANG TRAITER *(24/09/2026 13h52, spécification de Quang)*

> Quang : *« un système qui permet de continuer même si des pages ou autre chose sont refusées par modération […] une
> fenêtre […] qui ne prend pas trop de place, qui est repliée, en couleur et qui clignote un peu […] si je l'ouvre, tous
> les chapitres ou toutes les pages concernées […] expliquent clairement que c'est lié à la modération, avec une
> proposition de solution. Il suffit de cliquer, et je peux sélectionner ce que je veux traiter […] une notification
> historique persistante que je peux traiter moi-même à tout moment […] si j'ai lancé la génération d'une vidéo ou d'un
> batch et qu'il y a des erreurs sur un chapitre, il faut peut-être ne pas générer la vidéo. »*
> Et avant : *« si je lance une génération dans le cloud, à tout moment le local pourrait prendre la main […] si j'étais
> sur le PC en train de faire des choses, cela pourrait créer des effets »* ⇒ **le local ne prend JAMAIS la main tout seul.**

### Constat (lu dans le code, 24/09)
Aucun refus n'est reconnu : Gemini « SAFETY » = réponse vide → lue comme « JSON illisible » → **3 essais PAYÉS** →
**le chapitre entier abandonné**. Une seule page sensible fait tomber tout un lot. (Récit = DeepSeek, déjà permissif.)

### Ce qu'on construit
1. **Reconnaître un refus** (Gemini `finishReason`/`blockReason` de sécurité, refus Kimi/DeepSeek « risque »/content
   filter, réponse de refus en toutes lettres) → **pas de nouvel essai payant**, une ligne au journal.
2. **Continuer** : en analyse, le lot refusé est découpé page par page ; seule la page refusée est mise de côté (pas de
   narration, marquée `moderation`), le chapitre continue. En traduction : la page refusée garde sa VO, le chapitre continue.
3. **Registre persistant** `sources/_alertes.json` : une entrée par page ou chapitre touché (série, chapitre, page(s),
   étape, moteur, motif, date, solution proposée, état : ouverte / traitée / ignorée). Survit aux redémarrages.
4. **Fenêtre d'alertes = DANS le bouton d'activité existant** (Quang 24/09 13h54 : *« le bouton du haut qui donne les
   événements d'activité […] je clique dedans, ça ouvre comme aujourd'hui, puis j'ai encore un autre menu qui me permet
   de voir tout ce qui n'a pas marché »*) : le bouton garde son rôle ; s'il y a des alertes ouvertes, il porte en plus un
   **badge orange « ⚠ N » qui pulse doucement** (seul ce badge clignote : l'activité normale ne clignote pas). Dans le
   panneau, un 2e onglet **« ⚠ À traiter (N) »** : liste par chapitre, motif en clair (« refusé par la modération de
   Gemini »), solution proposée, cases à cocher, **« Traiter la sélection »** ; historique (traitées / ignorées).
5. **Solutions proposées** (Quang choisit, rien d'automatique) : réessayer avec l'autre moteur en ligne (Kimi ↔ Gemini) ;
   narrer la page par DeepSeek à partir des pages voisines (sans image) ; relire en LOCAL (carte graphique, **seulement
   sur clic**, avec la garde « carte libre ») ; ignorer.
6. **Vidéo** : un chapitre avec une alerte OUVERTE n'est **pas mis en vidéo** (batch, nuit, demande) ; l'alerte le dit
   (« vidéo en attente ») ; une fois l'alerte traitée ou ignorée, la vidéo peut repartir. Option « générer quand même ».

### 🔞 Contenu adulte à venir *(Quang 24/09 14h40)*
> *« c'est possible que plus tard je tombe sur des mangas pour adultes de plus de 18 ans ; à ce moment-là on fera une
> catégorie un peu secrète […] mais à ce moment-là l'absence de modération sera importante. »*
- Conséquence : pour ces séries, un refus ne sera plus une exception à traiter page par page mais la **règle** — il
  faudra une chaîne **qui marche sans modération** de bout en bout, pas seulement des alertes.
- Ce qu'on sait déjà (mesuré) : récit = DeepSeek (permissif) ; analyse des pages = Gemini / Kimi (modérés) ; analyse
  **locale** (qwen3-vl 8B, § 4-nonies étape 3) = aucune modération mais **récit nettement moins fidèle** (16/30 vs 21/30) ;
  voix : Google TTS (modérée ?) ou **voix locale** (aucune) ; traduction : Gemini (modéré) ou Qwen3-30B local (90 % vs 94 %).
- À concevoir le moment venu : catégorie **cachée** dans la bibliothèque (hors vue par défaut, accès volontaire) +
  **profil « sans modération »** par série (analyse / traduction / voix routées vers ce qui ne refuse pas).
- **Déclencheur** : la 1ʳᵉ série adulte capturée par Quang. **Préalable utile dès maintenant** : l'essai de refus RÉEL
  (Claymore) dira quels moteurs refusent quoi — c'est la carte dont ce chantier aura besoin.

### Tester
Banc sans réseau (réponses de refus simulées Gemini / Kimi / DeepSeek → reconnues, chapitre continue, alerte écrite,
vidéo bloquée) + mutation ; puis pages réellement dures déjà présentes (Claymore) ; non-régression narration/vidéo.

## 4-nonies. FEUILLE DE ROUTE — MOTEURS LOCAUX EN OPTION *(24/09/2026 12h50, demandée par Quang : « trace une feuille de route bien détaillée, puis on travaille étape par étape »)*

### Les règles du chantier (décision Quang, non négociables)
1. **Rien n'est débranché.** Gemini / Kimi restent le fonctionnement par défaut. Le local est une **OPTION** que Quang
   choisit « selon ce que je fais sur mon PC » (carte graphique libre ou non).
2. **Chaque étape se termine par un tableau AVANTAGES / INCONVÉNIENTS MESURÉS** (coût, temps, qualité, confort,
   risques) **et une décision écrite** : intégrer / garder en réserve / **ne rien faire**. « Ne rien faire » est un
   résultat valable, pas un échec.
3. **Mesurer avant de croire** : bancs chiffrés, juges à l'aveugle (≥ 2) pour la qualité de langue, **écoute de Quang**
   pour les voix, non-régression sur TOUTES les séries (OPM + Black Jack + Noritaka + Solo Leveling).
4. **Tout le lourd sur C:** (`Documents/MangaStudio-donnees/modeles`, `~/.ollama`, cache HF, venv `AppData/Local/manga-tts`).
5. Une étape = un commit qui la nomme ; chaque report a un **déclencheur de reprise**.

### Point de départ (mesuré le 24/09, § 4-octies)
Coût réel par page (OPM ch.1-10, 228 p.) : analyse des pages 0,0041 $ · récit 0,0001 $ · **voix 0,0058 $ (57 %)** ·
traduction ~0,006-0,012 $ si VO. Solo Leveling vol.1 (755 p., déjà en français) ≈ **7,60 $** aujourd'hui ;
≈ 3,20 $ avec la voix locale ; ≈ 0,10 $ si l'analyse devenait locale aussi (**non testé**).

### Étape 0 — Le socle commun (avant toute intégration)
- **0a. Sélecteur de moteur** dans le profil de série (réglages du batch) ET à la demande sur un chapitre :
  « ☁ En ligne (défaut) » / « 🖥 Local ». Par étape : voix, effacement, analyse. Mémorisé par série.
- **0b. État de la carte graphique** affiché avant de lancer en local : mémoire libre, et ComfyUI / Generate Studio
  occupé ou non. En local, un traitement qui trouverait la carte prise **attend**, il ne se bat pas avec elle.
- **0c. Journal** : chaque passage local écrit ce qu'il a fait (moteur, durée, mémoire GPU, erreurs) dans le journal
  existant + inscription au registre des logs.
- **Fini quand** : le sélecteur existe, choisir « Local » sans moteur installé dit clairement pourquoi c'est impossible,
  et le choix « En ligne » produit EXACTEMENT le même résultat qu'avant (banc de non-régression).

### Étape 1 — Voix locale (Chatterbox, 4 voix retenues par Quang : Algenib, Aoede, Charon, Leda)
- **1a. Banc chapitre entier** (OPM ch.1, 24 p.), méthode stable (phrase par phrase, graine fixe, timbre cloné) :
  temps de calcul, débit par page (homogène ?), silences, mots avalés, **timbre identique d'une page à l'autre**.
- **1b. Karaoké** : `karaoke_mots.py` aligne-t-il les mots sur ces voix comme sur Gemini ? (mesure : mots alignés / total)
- **1c. Écoute de Quang** sur le chapitre complet, les 4 voix.
- **1d. Intégration** comme moteur de voix « local » dans `narrate_chapter` (mêmes fichiers de sortie, même karaoké,
  même vidéo), 0 $ facturé, durée affichée honnêtement.
- **Avantages attendus (à confirmer)** : −57 % de la facture, voix illimitées, hors ligne, pas de quota.
- **Inconvénients attendus (à mesurer)** : ~1× temps réel (≈ 3 h pour Solo Leveling vol.1), carte graphique occupée,
  qualité validée sur 3 pages seulement, un environnement Python de plus à maintenir.
- **Décision** : intégrer / réserve / rien.

### Étape 2 — Effacement local du texte posé sur le dessin (masque des lettres + LaMa manga)
- **2a. Banc complet** : toutes les pages OPM ch.1-10 + Black Jack + Noritaka. Mesures : cases blanchies (critère
  Vidéo Studio), texte d'origine restant (contrôle CJK), « ! » isolés, bavures (échantillon regardé à l'œil).
- **2b. Corrections** des défauts connus : fragments éloignés de la boîte (« ! »), lisibilité du français sur dessin chargé.
- **2c. Intégration** en option dans `traduire_chapitre` (vraies bulles : effacement actuel inchangé ; texte sur le
  dessin : local) + re-rendu SANS appel (`--rerendu`) pour refaire les pages existantes.
- **Avantages attendus** : cris/légendes enfin traduits sans abîmer la case, 0 $, 1-3 s/page.
- **Inconvénients attendus** : bavures quand LaMa invente beaucoup, 2 modèles de plus (≈ 300 Mo), code GPL-3.0
  (manga-image-translator / comic-text-detector) — sans conséquence pour un usage perso, à savoir si l'app était un jour
  distribuée.
- **Décision** : intégrer / réserve / rien.

### Bilan mesuré — étape 1 (voix locale), 24/09/2026
Banc OPM ch.1 (17 pages) puis **chaîne réelle via l'API** : narration `--tts local` (analyse reprise, 0 appel payant) →
karaoké → vidéo avec les réglages de Quang (1,15x, sous-titres, karaoké, musique 20 %, caméra case par case).
| Avantages (mesurés) | Inconvénients (mesurés) |
|---|---|
| Voix **0 $** (57 % de la facture ; Solo Leveling vol.1 ≈ 7,60 → 3,20 $) | **~0,9-1× temps réel** : 3 min de voix = ~3,5 min de carte graphique (+14 s de chargement) |
| Débit recalé sur l'en-ligne (atempo) : **16,9 car/s** vs 17,4 — le 1,15x de Quang garde son rythme | Carte graphique occupée pendant ce temps (attend ComfyUI s'il travaille) |
| Karaoké **17/17 pages, 95 % des mots reconnus** par Whisper | Timbre = une IMITATION de la voix Google (extraits `_apercus`) : validé à l'oreille sur 3 pages + palette ; le chapitre complet n'a pas encore été ÉCOUTÉ par Quang |
| Voix illimitées (clonage), hors ligne, pas de quota | Un environnement Python de plus (sur C:, torch cu128 forcé par-dessus la dépendance CPU de Chatterbox) |
| L'en-ligne n'est jamais écrasé (étiquette `-local`) | « Précédemment… » reste en voix en ligne (courte) |
À écouter : `sources/one-punch-man/ch_1/video/gemini-charon-local.mp4` (à côté de `gemini-charon.mp4`).

### Bilan mesuré — étape 2 (effacement local), 24/09/2026
3 essais sur OPM ch.3 : appliqué à TOUT le texte hors bulle, le détecteur de lettres attrape aussi les **onomatopées
DESSINÉES** (p.9 « ズゴゴゴ » abîmée, textes superposés p.4, zone gonflée) → **variante PRUDENTE retenue** : le local ne
traite QUE les zones que le mode standard laisse en VO (cris, légendes géantes, titres). Banc OPM ch.3 + 4 + 10
(77 pages) : **5 pages changent, toutes des gains** (ch.3 p.7 légende, ch.4 p.1 titre « 4E COUP : LES SOUTERRAINS
TÉNÉBREUX », ch.4 p.17 + ch.10 p.12 cris, ch.10 p.29 « …UN SIGNAL DE DANGER ABSOLU ! ») ; **les 72 autres identiques
à l'octet** ; mode standard = identique à l'octet (non-régression).
| Avantages | Inconvénients |
|---|---|
| Les textes laissés en VO sont traduits sans abîmer la case | Gain PETIT en volume : ~1 page sur 15 sur OPM |
| Aucune régression possible ailleurs (pages identiques) | Restes : « ! » isolés, onomatopée voisine parfois touchée (ch.3 p.7) |
| 0 $, 3-6 s par chapitre | 2 modèles (≈ 300 Mo sur C:), code d'origine GPL-3.0 (usage perso : sans effet) |
| Option : `--effacement local` (+ `--rerendu` pour refaire sans appel) | Pas encore de bouton dans l'app (option en ligne de commande) |
Piste non retenue (à rouvrir seulement si besoin) : distinguer texte / onomatopée dessinée (détecteur `comic-text-and-bubble-detector`, classes `text_bubble` / `text_free`).

### Étape 3 — Analyse locale des pages### Étape 3 — Analyse locale des pages (ce qui nourrit le récit) — l'inconnue
- **3a. Banc** : qwen3-vl 8B instruct (et ce qui tient en 16 Go) produit la fiche de chaque page (faits, personnages
  présents, type de page) ; comparaison à Gemini **par 2 juges à l'aveugle** sur la fidélité, puis sur le RÉCIT final.
- **3b. Si prometteur** : essai sur un chapitre entier + écoute/lecture de Quang.
- **Avantages possibles** : −40 % de la facture en plus (≈ 0,10 $ le volume au total).
- **Risques** : c'est ce que Gemini fait de plus difficile (reconnaître les personnages d'une page à l'autre, l'ordre
  de lecture, le ton) ; un 8B risque de raconter à côté. Temps de calcul par page à mesurer.
- **Décision** : intégrer / réserve / rien.

### Bilan mesuré — étape 3 (analyse locale des pages), 24/09/2026
`narrate_chapter --engine local` (qwen3-vl 8B instruct via Ollama, 0 $) sur OPM ch.2 (16 p.), récit comparé à celui de
Gemini **par 2 juges à l'aveugle** : **DeepSeek local 16/30 vs Gemini 21/30 · Kimi local 10/30 vs Gemini 30/30**.
Lecture : contresens (p.3 : qui menace qui ; p.5 : le « mêmes yeux vides » disparaît), pages vidées de sens (p.8 :
« les mêmes mots tournent… comme un écho »). ~5 min pour 16 pages ; 1 lot sur 8 → HTTP 500 d'Ollama (repris sans
JSON imposé). Et ce n'est pas entièrement local : la passe des noms et la latinisation restent en ligne (0,09 $).
| Avantages | Inconvénients |
|---|---|
| −40 % de facture possible (analyse 0,0041 $/page) | Récit **nettement moins fidèle** — c'est le cœur de la vidéo |
| | Plus lent, carte graphique occupée, erreurs Ollama à gérer |
**Proposition : ne rien faire** (garder le code `--engine local` en réserve). **Déclencheur de reprise** : un modèle
vision local ≥ 30 B tenant en 16 Go, ou Gemini/Kimi indisponibles ; banc à rejouer : même chapitre, mêmes 2 juges.

### Étape 4 — Traduction locale : EN RÉSERVE (déjà mesurée)
Qwen3-30B-A3B : 90 % vs Gemini 94 % (DeepSeek), 77 % vs 93 % (Kimi), 87 bulles à l'aveugle → **on ne l'intègre pas**.
**Déclencheur de reprise** : Gemini indisponible durablement, OU prix de la traduction ×3, OU un nouveau modèle local
annoncé meilleur en zh/ja→fr (à rejouer avec `essai_trad_local.py`, même banc, mêmes juges).

### Étape 4-bis — UN interrupteur global « ☁ Cloud / 🖥 Local » (Quang 24/09 13h53)
> *« un menu simple, ergonomique et très clair, pour que je repère rapidement visuellement si je vais lancer quelque
> chose en local ou en cloud […] mets ça en persistance mémoire […] à toi de voir si c'est par chapitre, par manga ou
> global ; je préfère te laisser réfléchir. »*
**Choix (Claude)** : **GLOBAL à l'app**, mémorisé CÔTÉ SERVEUR (`sources/_reglages.json`, le même sur le PC et le
téléphone, lu par la nuit/batch). Raison : ce qui décide « local ou cloud », c'est **ce que Quang fait sur son PC à ce
moment-là**, pas le manga ; un réglage par série/chapitre obligerait à le changer à dix endroits et se ferait oublier.
- Un **gros bouton-bascule coloré dans l'en-tête**, visible depuis tous les onglets : bleu « ☁ CLOUD » / orange
  « 🖥 LOCAL · carte graphique » (+ mémoire libre de la carte en petit).
- **Chaque bouton qui lance quelque chose** (narrer, traduire, lot, vidéo) **porte l'icône** ☁ ou 🖥 du mode actif.
- LOCAL = voix locale + effacement local ; l'analyse des pages et le récit restent en ligne dans les deux modes.
- Les menus « Moteur de voix » par chapitre/série (v2.10.0) sont remplacés par cet interrupteur unique.

### Étape 5 — La stratégie finale (après 1, 2, 3)
Tableau de synthèse : pour chaque bloc, en ligne vs local, coût / temps / qualité / confort. Choix proposés à Quang :
**« Qualité »** (tout en ligne), **« Économie »** (local partout où c'est validé), **« Auto »** (local si la carte est
libre, sinon en ligne) — ou rester comme aujourd'hui. Décision de Quang, écrite ici.

### Suivi
| Étape | État | Décision |
|---|---|---|
| 0 Socle | ✅ v2.10.0 (24/09) : menu « Moteur de voix » (chapitre + profil/batch/nuit), état de la carte (`/manga/gpu`), attente d'une carte libre dans `tts_local.py`, journal | — |
| 1 Voix locale | ✅ codée + testée de bout en bout (24/09) ; **chapitre complet ÉCOUTÉ et validé par Quang (24/09 17h17 : « c'est bien »)** | ✅ **Quang 24/09 13h53 : en OPTION** |
| 2 Effacement local | ✅ codé, variante PRUDENTE (24/09) | ✅ **Quang 24/09 13h53 : en OPTION** |
| 3 Analyse locale | ✅ mesurée (24/09) | ❌ **ne rien faire** — validé Quang 24/09 13h53 |
| 4 Traduction locale | ⏸ en réserve | ne pas intégrer (mesuré 24/09) |
| 5 Stratégie | ⬜ après 1-3 | — |

## 4-octies. EXPLORATION IA LOCALE (24/09/2026, demandée par Quang : « explorer à fond, puis on tranche »)

Matériel : RTX 5070 Ti 16 Go. Tout le lourd sur **C:** (`Documents/MangaStudio-donnees/modeles`, `~/.ollama`, cache HF,
venv voix `AppData/Local/manga-tts`). Scripts `scripts/essai_*.py` (l'app n'est pas modifiée).

| Bloc | Essai | Verdict (mesuré) |
|---|---|---|
| **Effacer le texte posé sur le dessin** | comic-text-detector (ONNX via OpenCV, masque des LETTRES au pixel ; morceaux qui touchent la boîte, gardés entiers) + LaMa par zone (généraliste `big-lama.pt` / manga `lama_large_512px.ckpt`) | ✅ **Vrai plus.** Cris et légende ch.3 p.7 effacés sans abîmer la case, puis traduits ; 1-3 s/page. Reste : « ! » isolés loin de la boîte, bavures quand LaMa invente beaucoup. Boîtes seules (v1 de l'essai) = RATÉ : le goulot était la localisation. |
| Lire les bulles | qwen2.5vl 7B / qwen3-vl 8B **instruct** (Ollama) | Lecture médiane 100 %, ~1 s/bulle. ⚠ `qwen3-vl:8b` = variante « thinking » : réponse VIDE (tout part en réflexion) → prendre `-instruct`. |
| Traduire | Qwen3-30B-A3B instruct q4 (Ollama, 18 Go) à partir du texte lu | ❌ **Gemini reste meilleur** : 87 bulles, 2 juges à l'aveugle — 90 % vs 94 % (DeepSeek), 77 % vs 93 % (Kimi). Un 1er essai à 26 bulles disait l'inverse (88 vs 86) : échantillon trop petit. |
| Voix | Chatterbox multilingue (venv C:, torch cu128 forcé par-dessus sa dépendance CPU) | ✅ **Validé à l'oreille par Quang** en version « stable » : phrase par phrase, graine fixe, timbre cloné sur `p009_local_defaut.wav`. Sans ça, même paramètres = timbre qui change et débit jusqu'à 21,6 car/s (p024 « horrible »). ~1× temps réel. |

**Suite proposée (à valider par Quang)** : (1) intégrer l'effacement local dans `traduire_chapitre` pour les zones hors bulle (banc de non-régression sur OPM + Black Jack + Noritaka) ; (2) moteur de voix « local » en option de narration.

## 4-bis. L'essai utilisateur du 28/07 — 10 puis 12 cases, pilotées comme Quang

> Demande de Quang : *« fais l'essai toi-même, en pilotant comme si tu étais moi, pour voir si au
> niveau ergonomie et efficacité tout est en ordre »*. Harnais : `scripts/essai_combat.py` —
> **aucun appel `api()` pour agir**, uniquement des gestes d'écran. Un script qui triche mesure son
> propre confort, pas celui de l'utilisateur.

**L'ergonomie tient.** 52 gestes, 2 min 48, **zéro erreur JS** pour dix cases de bout en bout
(nettoyer les fiches → créer le projet → écrire → caster → générer → exporter). Une seule friction
d'usage : sur un projet **neuf**, la troupe est vide, donc aucune pastille « Qui est là » n'est
proposée — il faut déplier « + ajouter » d'abord, et le refaire à chaque case.

### 🔴 Le vrai défaut, trouvé en LISANT le prompt envoyé (pas en le supposant)

La case 1 disait *« plan large du dojo **vide** »*. Le prompt réellement envoyé :

```
masterpiece, 2people, …, 1girl, black hair, …, 1man, short hair, …, wide shot, empty dojo…
```

**Le casting est appliqué à toutes les cases sans exception**, y compris celles qui ne parlent que
d'un personnage — ou d'aucun. D'où douze cases avec la même composition à deux corps, quel que soit
le découpage. Une part est une **erreur de pilotage** (j'avais coché les deux personnages partout,
ce que l'app n'impose pas depuis la v1.49.0), mais l'app n'aide pas : rien ne signale qu'un
`close-up on the face of a man` cohabite avec un casting de deux et un `2people` dérivé.

⇒ **Règle de production, à appliquer dans un découpage** : le casting se décide **case par case**,
comme au storyboard. Une case de décor n'a personne.
⏳ **Piste pour l'app** (non faite) : avertir dans l'aperçu quand le texte d'une case ne mentionne
manifestement qu'un personnage alors que le casting en compte deux.

### ✅ Une cause secondaire, mesurée : les fiches qui décrivent la tenue jusqu'aux chaussures

Même seed, même action, seuls les tags changent — mesure = part de l'image occupée par le visage :

| Tags de la fiche | Action « coup de pied sauté » | Gros plan demandé |
|---|---|---|
| complets (`black socks, black shoes, black skirt…`) | **4,8 %** | 10,2 % |
| allégés (traits + `sailor uniform`) | **15,2 %** | 13,0 % |

**Un modèle à qui l'on décrit des chaussures dessine des pieds** : la fiche tire vers le plan en
pied, et le cadrage demandé passe après. Une fiche décrit ce qui **identifie** un personnage, pas sa
garde-robe complète. *(Le 🧹 Nettoyer actuel retire le style et les couleurs, pas ces éléments-là.)*

### ⛔ Trois hypothèses posées et INFIRMÉES le même jour — elles auraient toutes coûté un chantier

| Hypothèse | Mesure | Verdict |
|---|---|---|
| « les masques gauche/droite imposent une composition en deux bandes » | prompts d'action, avec/sans masque | ⛔ **faux** — le masque donne de vraies scènes dynamiques |
| « l'app met l'action en fin de prompt, donc elle est noyée » | même prompt, action en tête vs identités en tête | ⛔ **faux** — 13,0 % contre 13,0 %, aucun écart |
| « le format portrait 832×1216 rend les masques trop étroits » | carré vs portrait, avec/sans masque | ⛔ **faux** — en portrait, **avec** masque 9,1 % contre **4,1 %** sans : le masque *aide* |

*Trois fois, une explication plausible a été démentie par la mesure — et la vraie cause était
lisible en une ligne dans le prompt enregistré. La leçon n'est pas nouvelle sur ce projet, elle est
juste plus nette : **lire la donnée avant de construire la parade**.*

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
| **Attendre un témoin déjà présent** | Un `wait_for` sur un champ qu'un cas précédent a laissé en place rend la main AVANT que quoi que ce soit ne se produise. Le banc lit alors l'état d'avant en croyant lire le résultat. Vider le témoin, puis l'attendre. |
| **Un separateur pleine largeur dans une grille** | Un element en `grid-column:1/-1` pose AVANT CHAQUE case ramene la planche a UNE colonne : chaque case demarre apres une ligne complete. Le `grid-template-columns` reste juste — seul un controle GEOMETRIQUE (`getBoundingClientRect`) voit le defaut. Ne poser une ligne pleine largeur que la ou elle SEPARE vraiment. |
| **Deux largeurs pour une meme page** | Elargir `main` sans elargir le bandeau et les onglets donne un contenu a 1600 px sous un en-tete a 760. Ce n'est pas « plus d'espace », c'est une page cassee. Toute largeur se decide pour la page ENTIERE. |
| **`hidden` ecrase par un `display` d'auteur** *(3e recidive)* | Traite a la racine depuis la v1.61.0 par une regle globale `[hidden]{display:none !important}`. La consigne « ecrire `.x[hidden]{display:none}` a chaque fois » etait une discipline — donc elle ratait. |
| **Une consigne qui se contredit** | Demander un `COUNT:` puis finir par « Nothing else » donne **0 COUNT sur 14**. Le modele tranche par la FIN. Enumerer le format attendu la ou l'on dit « rien d'autre ». |
| **Couper avant d'extraire** | `split("\n")[0]` applique a la reponse du LLM jette la ligne `COUNT:` (2e ligne), puis on constate qu'elle manque. Le decoupage appartient a qui SAIT ce qu'il cherche. |
| **Un compteur jamais incremente** | Un banc annoncait « 0 COUNT absent » alors qu'il l'etait sur les 14 cas : la ligne d'incrementation n'avait pas ete inseree (un `.replace()` de patch rate en silence). **Un chiffre doit venir d'une addition, jamais d'une valeur par defaut** — et tout patch automatise doit `assert` son remplacement. |
| **Le casting confondu avec le comptage** | Le casting dit QUI est identifie, pas COMBIEN de corps sont dans la case : un figurant non fiche disparaissait. Le casting est un PLANCHER, relevable par le compte lu dans la phrase. |
| **`grid lines` (et la famille de la planche)** | Ces tags demandent une PAGE decoupee : `grid lines` a produit HUIT fenetres dans UNE case. Ils arrivent par l'AMELIORATION, pas par l'utilisateur. Retires du positif dans le code, et mis au negatif. |
| **Juger une image avec l'outil d'a cote** | Le detecteur de cases de l'INGESTION (phase 3) est le bon juge pour « combien de fenetres dans cette image ». Un projet accumule des instruments : penser a les reutiliser avant d'en ecrire un. Et les calibrer sur un cas connu, toujours. |
| **Un `file` sans `versions`** | Les cases d'avant la v1.48.0 portent une image mais aucun historique. Toute logique qui fait `versions || []` les prive de leur image d'origine a la premiere regeneration -- sur le disque, mais plus atteignable. Reintegrer avant d'ajouter. |
| **Une cle d'API qui differe de ses voisines** | `/manga/files` rend `files`, les autres rendent `items`. Lire la mauvaise cle donne une liste vide, donc « 0 probleme » -- le pire des faux verts. Un script qui ne trouve pas la cle attendue doit s'ARRETER, pas conclure. |
| **Une seed lue dans un CHAMP repliable** | `genPanel` prend la seed du champ `[data-seed]` s'il existe. Tiroir ferme il n'existe pas (tout va bien), tiroir ouvert il porte l'ancienne valeur et l'emporte sur la recette. Ecrire une seed « neuve » dans la recette seule ne suffit donc pas. |
| **Un comportement ecrit EN LIGNE n'est pas falsifiable** | Le tirage de seed etait inline : impossible a remplacer, donc la mutation du banc restait verte et ne prouvait rien. Ce qu'on veut pouvoir saboter doit avoir un NOM. |
| **Un refus qui ne nomme pas sa raison** | « rien a generer » sur une planche pleine de cases : le filtre exigeait un TEXTE, le message n'en disait rien, et le libelle du bouton parlait de « cases vides ». Trois mensonges pour un seul geste. |
| **Tester un chemin apres avoir lance l'autre** | Le banc mesurait « le contexte n'entre pas dans le prompt » APRES avoir appele l'amelioration -- qui a le DROIT de reprendre le decor. Il reprochait a l'app son travail, une fois sur deux. L'ordre des tests fait partie du test. |
| **Un tag invente** | `2people`, `3people` n'existent pas dans le vocabulaire danbooru. Mesure : 2/5 contre 3/5 SANS aucun tag. Un mot que le modele n'a jamais vu ne fait pas « rien » — il occupe la place et deplace le reste. Verifier qu'un tag existe avant de l'imposer. |
| **`multiple people`** | Produit des FOULES (7 a 24 personnages mesures), jamais un duo. A bannir des prompts a deux personnages. |
| **Compter des visages pour compter des personnages** | En plan large, aucun visage n'est detectable : toutes les variantes sortent « 0 », y compris celles qui montrent deux personnes. Le chiffre est juste, la question posee ne l'est pas. Calibrer l'instrument sur des comptes CONNUS avant de conclure — et regarder les images. |
| **Une capture de banc au nom fixe** | Le run `--muter` écrasait celle du run normal : on regarde alors l'écran d'une app volontairement sabotée en croyant regarder l'app. Le nom du fichier doit porter la variante. |
| **Un `` de regex devenu un BACKSPACE** | Trois regex de production ne pouvaient *jamais* matcher : un édit passé avait écrit `` comme le caractère U+0008. Invisible à la lecture (`grep` l'affiche comme rien), invisible à `node --check` (la syntaxe est valide). Et dans une **chaîne** JS, `""` est un backspace lui aussi — `new RegExp("" + n)` ne teste rien. Chercher `` dans le fichier après toute réécriture automatisée. |
| **Une négation traduite en tag positif** | CLIP n'a pas de négation : `no head`, `face not visible` **demandent** ce qu'on refuse (5 cas sur 14 mesurés). Ce qui est nié va au NÉGATIF — et le négatif veut le **sujet**, pas sa négation : `no_humans` (avec underscore, tel que le modèle le rend) mis au négatif réclame des humains. |
| **Un tag des DEUX côtés** | `empty` au positif *et* au négatif de la même case : les deux s'annulent, et rien ne l'affiche puisque le négatif n'est pas montré. Un tag entier présent au positif ne doit jamais figurer au négatif. |
| **L'identité complète sur un gros plan** | Une fiche décrit une personne ENTIÈRE. Sur « close-up sur ses mains », `sailor uniform` demande au modèle d'élargir le cadre, et l'image de référence IPAdapter ramène le visage à elle seule. Mesuré : même identité retirée, **`1girl` seul** suffit à faire un visage plein cadre 4 fois sur 5. |
| **Un décor de banc posé sur `window`** | `let CHARS` est une liaison **lexicale** : `window.CHARS = […]` crée un homonyme que la page ne lit pas. Le banc testait un casting vide et ses cas « ce tag doit être absent » passaient au vert pour la mauvaise raison. Pire, l'app **réassigne** `CHARS` en asynchrone : un décor posé une fois s'efface en cours de boucle. Poser le décor à chaque cas, et vérifier un **témoin positif**. |
| **Ids générés à la milliseconde** | `prefix + hex(now_ms)` donne le **même id** à deux insertions dans la même ms — et créer 6 cases d'un coup est une rafale. `_studio_db._uid()` ajoute un compteur monotone. Attrapé par le self-test, pas en production. |

---

## 6. Journal

| Date | Événement |
|---|---|
| 2026-09-26 (03h55) | ✅ **v2.67.2** (Quang 03h38, capture d'écran : « Reading No to Obsession… » proposé, « &quot; » affiché) : `devinerTitre()` retire le mot de lecture en tête (Reading / Read online / Lire / Lecture en ligne) SEULEMENT sur un titre de page de chapitre, et décode les entités HTML (proposition + liste des onglets). Banc `test_titre_onglet_ui.py` 9/9 (« Reading the Room », « Ready Player Two » intacts), mutation v2.67.1 → 6 KO ; `test_choix_manga_ui` vert. |
| 2026-09-26 (03h45) | ✅ **v2.67.1** (Quang 03h35 : « quand les captures sont finies, ça ouvre directement le manga […] désagréable quand je navigue ailleurs ») : plus d'ouverture automatique du chapitre en fin de capture (série et chapitre seul) ; bibliothèque rafraîchie + message « capture terminée ». Banc `test_fin_capture_ui.py` 8/8 (fin SIMULÉE, secondes), mutation v2.67.0 → 4 KO ; `test_capture_serie_ui` : assertion inversée. |
| 2026-09-26 (02h45) | ✅ **manga-fetch 0.8.3** : chapitre annoncé sans image = fin du lisible en « dernier paru » (bandeau « à jour » au lieu d'un faux échec). Webtoon en cours complété ch. 21-24. |
| 2026-09-26 (02h30) | ✅ **manga-fetch 0.8.2** : webtoons en TUILES découpés aux gouttières (critère de continuité du dessin, tuiles-espaces gardées, fonds rayés, bulles protégées) ; 63 chapitres redécoupés (sauvegardes gardées), 4 645 raccords en plein dessin → 49. |
| 2026-09-26 (00h55) | ✅ **manga-fetch 0.8.1** : webtoon en bandes presque carrées (720×700) → la largeur de colonne s'amorce sur le document (≥ 5 images ≥ 500 px à la même largeur) ; ch. réel 0 → 213/213 bandes. |
| 2026-09-26 (00h40) | ✅ **v2.67.0 + manga-fetch 0.8.0 + proxy `patch_dernier_paru`** (§ 4-quindecies) : puce « Jusqu'au dernier paru » ; plafond de 50 remplacé par des sécurités (croissance stricte, contenu identique, saut > 10, pause 3 s, filet 300 partout) ; chapitres déjà là sautés et comptés à part (« 2 capturé(s), 1 déjà là »), 1er chapitre déjà là = « ⏭ Le garder et continuer ». Banc réel 19/19 + voisins verts. 🔴 Défaut noté : webtoon en bandes presque carrées (1 page capturée). |
| 2026-09-24 (17h20) | 🎧 **Voix locale validée à l'oreille** sur un chapitre complet (OPM ch.1, `gemini-charon-local.mp4`) — Quang : « c'est bien ». Rappel du partage : ☁ = tout en ligne (seul changement du jour : repérage des noms sans réflexion, dans les deux modes) ; 🖥 = voix + effacement sur la carte, le reste en ligne. |
| 2026-09-24 (17h15) | 💰 **Chantier « réflexion Gemini » CLOS** : repérage des noms sans réflexion (gardé, −48 % analyse+noms) ; analyse et traduction gardent la réflexion complète (« low » : vraies fautes sur Black Jack — mot inventé, contresens, anglais ; « medium » : pas d'économie). Économie réelle attendue ≈ −4 $/mois en ligne, + la voix (≈ −6 $/mois) quand Quang narre en 🖥. § 4-terdecies. |
| 2026-09-24 (19h30) | ✅ **v2.18.0 + manga-fetch 0.6.9 → 0.7.0** : capture principale sans synchro ; enchaînement par la liste des chapitres de la page (site à identifiant interne : ch.1 → ch.2) ; indicateur d'enchaînement qui lit les sites tagués de chaque application. Prochaine étape : S5 (vue croisée). |
| 2026-09-24 (19h20) | ✅ **Compartiment S4 — accès téléphone** : adresse dédiée derrière Cloudflare Access (créé avant le DNS), jeton Access vérifié = aucune clé à saisir, appui long principale ↔ secondaire sur le téléphone, rien ne s'ouvre sur le PC. Sans cookie : 302 partout sauf manifeste/icônes (200). Bout en bout 7/7. Ensuite (demandes Quang 19h10) : fenêtre de capture PRINCIPALE sans synchro ; enchaînement par lien « chapitre suivant » (sites tagués après test réel) ; puis S5. |
| 2026-09-24 (18h55) | ✅ **v2.16.0 → v2.17.0 — compartiment secret S3 + indicateur d'enchaînement** : fenêtres de capture et d'app propres à l'application secondaire (profils sans compte ni synchro, placées par Quang), sa liste de sites hors dépôt, captures réelles OK ; manga-fetch 0.6.5 → 0.6.8 (2 défauts de défilement corrigés, indicateur « ce site enchaîne-t-il ? » dans les deux applications). Bancs 10/10, 14/14, 12/12 ×2. Prochaine étape : S4. |
| 2026-09-24 (17h58) | ✅ **v2.15.0 — compartiment secret S2** : l'app sait dans quel espace elle est (`/manga/espace`), appui long 1,2 s sur 📚 = l'autre espace (PC ; téléphone à S4), titre/icône identiques, marque discrète seulement dedans ; l'espace privé a aussi sa base, sa galerie et la même exigence de clé que 8190. `test_espace_ui.py` 29/29. |
| 2026-09-24 (17h45) | ✅ **Compartiment secret S1 — la 2ᵉ instance** (`espace_prive.py`, port 8192, données sur C: hors dépôt, tâche `MangaStudioInstance2`). Ce qui est créé d'un côté n'apparaît pas de l'autre, dans les deux sens (`test_espace_prive.py` 15/15, mutation rouge sans écriture). Prochaine étape : S2 (l'app sait dans quel espace elle est + appui long sur 📚). |
| 2026-09-24 (17h35) | ✅ **Compartiment secret S0 — racine des données réglable** (`MANGA_SOURCES_DIR`, 18 scripts + manga-fetch + 1 ligne du proxy). Sans la variable, rien ne change (6 bancs verts + plan de lot identique) ; avec, tout atterrit dans le dossier donné et nulle part ailleurs (`test_racine.py` 47/47, mutation rouge). Prochaine étape : S1 (2ᵉ instance sur **8192**). |
| 2026-09-24 (16h45) | ✅ **v2.14.1 — « ✕ Fermer la fenêtre »** (Quang 16h29) : ferme la fenêtre de capture à distance, et elle seule (Browser.close sur son navigateur dédié, jamais l'Edge de Quang), question à l'écran avant. Banc `test_fenetre_fermer.py` 4/4 (Edge jetable ; la vraie fenêtre n'est pas fermée : ses onglets seraient perdus). La fenêtre secrète aura le sien, indépendant (§ 4-quaterdecies). |
| 2026-09-24 (16h45) | ✅ **v2.14.0 + manga-fetch 0.6.4 — la fenêtre de capture à la main de Quang** (demandes 16h07-16h22). Mesuré : sous ~576 × 774 px intérieurs, MangaDex n'affiche plus la page (capture « aucune image ») → minimum **700 × 950** avec marge. La place choisie par Quang (~93 % sous l'écran) capture normalement (MangaDex 18/18, webtoon 7/7). La fenêtre s'ouvre à cette place ; « ↘ Ranger sur le côté », « ⤢ Taille sûre », « 📌 Retenir cette place » dans l'étape 1 ; contrôle avant chaque capture (question à l'écran + correction en un bouton). Rien ne bouge sans clic, sauf à l'ouverture. Banc `test_fenetre_ui.py` 10/10 (fenêtre et réglage restaurés). ⇒ Le PARAVENT du compartiment secret (§ 4-quaterdecies, point 6) est remplacé par ce principe (Quang 16h13 : « pas besoin de cacher la fenêtre avec la fenêtre principale »). ~~🟠 Raijin Scans fermé (renvoie vers Discord) : à retirer des sites validés.~~ → ✅ retiré de `sites.json` le 24/09 16h50. |
| 2026-09-24 (16h10) | ✅ **v2.13.2 — coûts dynamiques** (Quang 16h02 : « j'ai dû rafraîchir l'application pour voir les nouveaux coûts ») : la pastille ne suivait que les tâches vues par l'app → rechargée toutes les 30 s (page visible). Et les outils d'essai (sonde, juges, essai de réflexion) payaient **hors registre** : ils s'y inscrivent (type `essai`, poste « essais et bancs », proxy corrigé), 1,53 $ du jour rattrapés. |
| 2026-09-24 (16h05) | 💰 **narrate_chapter 2.8.0 — repérage des noms sans réflexion Gemini** : analyse+noms −48 % (0,19 → 0,10 $ pour 17 p.), fidélité inchangée (référence recalée : 9/6 graves vs 9/9 ; noms plus stables). Réflexion de l'analyse gardée (la couper dégrade : 2 juges à l'aveugle). Modération réelle : Claymore ch.2 = 178/178 Gemini, 20/20 Kimi, 0 refus. § 4-terdecies. |
| 2026-09-24 (15h30) | ✅ **v2.13.0 — jauge VRAM ventilée par moteur** (demande Quang 15h11). Windows ne ventile pas la VRAM par processus (mesuré) → chaque moteur déclare sa part ; gris = le reste. Banc 10/10. Détail § 4-duodecies. |
| 2026-09-24 (14h50) | ✅ **v2.12.0 — chantier 4-undecies.** Double estimation ☁ / 🖥 recalculée sur les passages réels (Narrer, Traduire, Tout traiter, confirmations), protection du changement de mode pendant un traitement (question à l'écran, Basculer / Annuler / Interrompre, bilan exact + Reprendre sans repayer l'analyse). Trouvé en route : le lot figeait la voix au lancement pendant que l'effacement suivait l'interrupteur (corrigé, suivi_nuit 2.5.0) ; une tâche coupée s'affichait « ✓ finie ». Bancs 320 cas + 19 + 17 + 18 verts, 5 mutations rouges, non-régression verte. 0 $ dépensé. Détail § 4-undecies. |
| 2026-09-24 (10h15) | ✅ **v2.9.1 → v2.9.2 + manga-fetch v0.6.2 → v0.6.3.** (1) Étiquette « aussi dans » passée sous le nom (débordait la poubelle hors écran sur smartphone ; banc 22/22 à 380 px, mutation 19/22). (2) **Capture Solo Leveling vol.1 coupée à 39 % EN SILENCE** : plafond fixe de 400 pas (~356 000 px sur 903 000) → plafond proportionnel à la hauteur, et tout arrêt avant la fin = note « ECHEC » ; même traitement pour le mode page par page (500 p. / 12 min). L'app affiche « ⛔ capture incomplète ». (3) **Règle de Quang : une série = un DOSSIER**, visible à 0 chapitre (bibliothèque + menu de capture) ; supprimer un chapitre ≠ supprimer le manga (banc `test_serie_vide_ui` 11/11, mutation 4 KO). ~~🟠 (constaté v2.9.2) Solo Leveling vol.1 est à RECAPTURER~~ → ✅ recapturé 24/09 10h40 avec manga-fetch 0.6.3 : 193 bandes (982 218 px cumulés pour une page de 903 320 px), 755 pages, dernière = page de crédits D&C Webtoon, arrêt « bas atteint », 0 ECHEC (avant : 79 bandes, 39 %). |
| 2026-09-24 (09h30) | ✅ **v2.8.5 → v2.9.0** (demandes Quang pendant la capture de Solo Leveling). **Titre tapé affiché dès le début de la capture** (manga-fetch v0.6.1 écrit `sources/<slug>/titre.json` ; le manifeste, qui marque « chapitre capturé », n'arrive qu'en fin de capture). **Tomes/dates relancés** quand un chapitre est capturé après la dernière recherche, **pochette AniList** cherchée seule — jamais pendant une capture (banc `test_auto_tomes_pochette_ui` 10/10). **« 🎵 Depuis un autre manga »** dans le chapitre ET le profil (batch) : musiques des autres séries, une par contenu (sha1), copiées sous le nom de la série, étiquette « ↔ aussi dans » (banc `test_musiques_app_ui` 18/18). 🟠 (constaté v2.9.0) `test_musique_ui.py` casse sur des données disparues (narration `banc-k3-charon` de Claymore ch.1), pas sur le code. |
| 2026-09-24 (01h15) | ✅ **Chantier 4-septies** (remontée Vidéo Studio 24/09 0h40, cases entières effacées). traduire_chapitre **v1.97.0** : trous rebouchés seulement dans la boîte du texte, cadre autour de la page, plafond des boîtes entières. OPM ch.1-10 re-rendus **sans appel (0 $, textes identiques)**, 0 page à cases effacées > 20 % (5 avant), 10 vidéos redemandées. 14 pages OPM étaient touchées, pas 5 (dont ch.1 p.24). Leçon : un garde-fou à l'échelle de la PAGE (18 %) laisse passer une CASE détruite — la mesure juste compte le dessin perdu, pas le blanc gagné. |
| 2026-09-24 (00h20) | ✅ **Chantier 4-sexies CLOS** (remontée Vidéo Studio 23/09 21h50). traduire_chapitre **v1.96.0** : 0 page blanche sur OPM ch.1-10 (20 avant), textes hors bulles + contrôle de couverture, effacement prudent si > 18 % de la page blanchie ; NR Black Jack (ja→fr/en) et Noritaka (en→fr) sans régression. 10 vidéos refaites (229 images contrôlées, 0 blanche). En route : manga-fetch **v0.6.0** (manga-scantrad.io : volumes entiers + chapitres), app **v2.7.4 → v2.8.4** (poubelle des morceaux dans le profil ; compteur d'activité « 3/27 », total fixe, batch + vidéos à venir, mémorisé sur l'appareil). Leçon : la 1re règle anti-page-blanche cassait 28 vraies bulles de Black Jack — compter les textes MINUSCULES, pas seulement les bulles traduites. Coût du chantier ≈ 5 $ (essais + retraduction). |
| 2026-09-23 (21h30) | 🔴→✅ **Narrations OPM ch.5-10 amputées des noms de personnages** (remontée Vidéo Studio, vérifiée dans les fichiers). Cause : chapitres capturés en **chinois de Hong Kong** (`langue.json` zh-hk, MangaDex) → l'étape noms figeait « 傑諾斯 » (Genos), « 埼玉 » (Saitama), « 土龍 » ; le récit les recopiait, `sans_cjk()` les effaçait → **47 pages** du type « En bas, lève sa main mécanique », en silence (le rapport en citait 39 : ch.9 et 10 narrés depuis). Black Jack (japonais dans les faits) : 0 page amputée, non touché. **narrate_chapter v2.3.0** (règle Quang : alphabet latin, consigne + contrôle code) : consignes latines (noms, vision) ; `latiniser()` AVANT le récit — tout mot CJK (fiche, faits, présents, résumé) converti en UN appel DeepSeek (nom d'usage / traduction), redemandé une fois, journalisé, idempotent (0 appel si déjà latin), marche aussi en reprise d'analyse ; **filet** : CJK dans une narration → échec code 3 ; sorties forcées en UTF-8 (lancé par le proxy, la sortie va dans un fichier cp1252 : le JSON final plantait APRÈS avoir tout payé → code 1 → ma reprise a refait la voix, **~0,8 $ payés deux fois**). Bancs `test_latin.py` **11/11** (rouge sur v2.2.0), `test_recit_lots.py` 16/16, sortie cp1252 : code 0 avec / 1 sans. **Refait** (`refaire_opm_latin.py`, analyse reprise) : ch.5-10 → 0 page amputée, 0 CJK, voix sur chaque page narrée, karaoké refait (« Genos lève sa main mécanique… », « …du lion et de Tsuchiryu ») ; anciennes narrations + vidéos à la corbeille, vidéos redemandées avec leurs réglages. |
| 2026-09-23 (19h55) | **v2.7.3 — « Tout traiter » : ☑ Tout · ☐ Rien · ch. X à Y** (Quang 19h41 : « il manque des boutons tout sélectionner et tout désélectionner »). Recensement des sélections multiples de l'app : vidéos (☑ Tout / ☐ Rien / plage), galerie (Tout sélectionner / Aucune), redessin des cases (tout cocher / décocher) les avaient DÉJÀ ; il ne manquait que la grille de « Tout traiter » (la troupe d'une scène : quelques cases, sans objet). Mêmes gestes que les vidéos ; ils passent en « ma sélection », ajustable ensuite au doigt ; compteur « n / N sélectionné(s) ». Banc `test_lot_selection_ui.py` **24/24** (sélection comparée au plan lu dans `/manga/suivi`, PC + 360 px, ne lance rien), rouge sur v2.7.2. Non fait (non demandé) : harmoniser les libellés des 3 autres endroits. |
| 2026-09-23 (19h45) | **v2.7.2 — choix du NOM DU MANGA à la capture (étape 3)** (Quang 19h20, capture : « la liste va s'allonger […] deux catégories : ce qui est masqué et ce qui ne l'est pas […] un bouton pour les afficher »). Le `<datalist>` natif (toutes les séries en vrac, sans ordre ni hauteur bornée) est remplacé par une liste maison : **« Mes séries (N) »** (récemment ouvertes, puis ajoutées), puis **« 👁 Afficher les masquées (N) »** replié ; la recherche est celle de la bibliothèque (titres alternatifs, 1 faute) ; une masquée SEULE réponse est montrée d'office ; un nom inconnu reste libre (« créera une nouvelle série »). Hauteur ≤ 340 px / 52 % de l'écran, défilement interne ; téléphone : largeur ≥ 320 px (le champ seul fait ~165 px à 360 px → titres coupés), décalée si elle déborde, page remontée sous la barre d'onglets collée ; clavier ↑↓ Entrée Échap. Banc `test_cap_titres_ui.py` **46/46** (ordre et contenu recalculés par le banc depuis l'API, PC 1280 + 360 px), rouge sur v2.7.1 ; `test_bibliotheque_perso_ui.py` 40/40. |
| 2026-09-23 (17h40) | **v2.7.0 — téléchargement des vidéos : reprise après coupure ✅ + chemin direct Wi-Fi 🟠** (idée de Quang : reprendre ce que Télégramme Vidéo a déjà). ✅ **Reprise** : `serve_manga_video` envoie `ETag` + `Last-Modified` et respecte `If-Range` (`proxy-patch/patch_video_etag.py` + `.diff`, proxy relancé par `relance-proxy.ps1`) ; banc `test_video_reprise.py` **8/8** (Claymore ch.1, 467 Mo : coupure à mi-course puis reprise → SHA-256 identique au disque ; If-Range périmé → fichier ENTIER), en local ET par le chemin direct. ✅ **Chemin direct posé** : Caddy DÉDIÉ (`direct/`, port 8723, lié à 192.168.1.141 seulement — instance séparée de celle de Télégramme Vidéo pour ne jamais couper l'autre), certificat Let's Encrypt obtenu, `manga-wifi.crushrank.xyz` (A non proxié, `direct/dns_direct.py`), tâche `MangaStudioDirect` (ouverture de session + toutes les 10 min), préflight `Allow-Private-Network` vérifié, 310 Mo/s depuis le PC. App : sonde 1,5 s puis téléchargement (vidéo et archive) par le Wi-Fi si joignable, sinon Cloudflare, journal « par le Wi-Fi ⚡ / par Cloudflare ☁ » ; worker réinstallé NEUF (`sw.js?v=2.7.0`) avec règle de routage `addRoutes` pour l'hôte direct (recette Télégramme Vidéo). ~~🟠 **BLOQUÉ sur téléphone (constaté v2.7.0, Samsung, Chrome 152)** : dans l'app INSTALLÉE (WebAPK plein écran — l'usage réel de Quang), Chrome laisse la demande « réseau local » EN ATTENTE sans jamais afficher l'invite (permission restée `prompt`, avec ou sans geste simulé) ; `Browser.setPermission` par CDP ne l'accorde pas non plus. Effet aujourd'hui : **aucune régression** — la sonde abandonne en 1,5 s et tout passe par Cloudflare comme avant. Non vérifié : l'invite dans un onglet Chrome NORMAL (le Samsung restait sur la WebAPK) et l'autorisation manuelle (Chrome → Paramètres des sites → Accès au réseau local). **Déclencheur de reprise** : Quang veut le Wi-Fi rapide sur le Fold → tester d'abord l'autorisation manuelle dans les paramètres de Chrome, sinon chercher comment une WebAPK obtient la permission (ou servir la page elle-même par le chemin direct à la maison). Banc `test_direct_samsung.py` (rouge à ce jour, pour cette raison).~~ → ✅ **FAUX DIAGNOSTIC, couvert v2.7.1 (18h06)** : l'invite « … souhaite accéder à d'autres appareils sur votre réseau local — Bloquer / Autoriser » s'affiche BIEN, aussi dans l'app installée (vue chez Quang sur le PC et sur le Fold, puis sur le Samsung) ; mes bancs la ratent parce que (1) la page était en ARRIÈRE-PLAN (`visibilityState: hidden` : un vieil onglet ou un sfr.fr ouvert de l'extérieur passait devant — une page cachée met ses requêtes en pause et n'affiche pas d'invite) et (2) je regardais l'écran trop tôt. Autre prérequis vu chez Quang : la 1re fois, **pare-feu Windows** « Caddy » → Autoriser (règle entrante Privé + Public ; le Wi-Fi de la maison est classé Public). **v2.7.1** : la 1re sonde abandonne à 1,5 s pendant que la question est encore affichée → l'app resonde dès que la permission passe à `granted`. **Mesuré sur le Samsung, app installée** : banc `test_direct_samsung.py` **6/6** — Claymore ch.1 **467 Mo en 18 s = 25,4 Mo/s** « par le Wi-Fi ⚡ » (tunnel : 5-6), fichier à l'octet près, supprimé après. ⚠️ Chrome passe en **HTTP/3 (UDP)** : `netstat` ne montre aucune connexion TCP, ce n'est pas un signe d'échec. Hors de la maison : « injoignable, Cloudflare ☁ » en ≤ 1,5 s (journal). |
| 2026-09-23 (16h20) | 🔴→✅ **Lot Claymore ch.1 « fini » mais MUET** (Quang, depuis le téléphone). Chapitre recapturé en tome (**180 pages**) : le récit v2 partait en UN appel plafonné à 8 000 tokens → réponse illisible (« Expecting ',' delimiter », char 26 885) → **180 pages sans texte, 0 voix**, et pourtant `ok: true`, narration « ok » dans le lot, karaoké « ok » (0 page) ; seule la vidéo refusait (« pas de narration avec voix »), ce qui masquait la cause. 1,74 $ d'analyse. **Corrigé** : `narrate_chapter.py` **v2.2.0** — récit **par lots de 40 pages** (fin du lot précédent en contexte, chute seulement dans la dernière partie), réponse tronquée → lot coupé en deux, JSON mal formé → réparé ; **garde-fou** : narration vide sur > 10 % des pages d'histoire, ou voix manquante → **code 3, pas de `narration.json`**, progress « echec » + raison ; l'analyse des pages est gardée dans **`vision.json`**. `suivi_nuit.py` **v2.4.1** : un nouvel essai (et un lot relancé) **reprend `vision.json`** s'il est postérieur à la capture — l'analyse n'est plus jamais re-payée. Banc `test_recit_lots.py` **16/16** (sans réseau), rouge sur l'ancienne version. **Rejoué en réel par la route de l'app** : analyse reprise, 5 lots, **170/170 pages narrées et voisées (33 min)**, karaoké 170 pages (90 % des mots), vidéo demandée ; dépense de la relance : récit 0,028 $ + voix 1,01 $ + karaoké 0,023 $. |
| 2026-09-21 | **Lecture narrée** (v1.66.0 → v1.67.0). Onglet 📚 Chapitres (consomme `sources/` de manga-fetch), narration K3/Pixtral → récit DeepSeek → voix Chirp 3 HD, lecteur plein écran, écoute à l'aveugle. Banc live : liste 30/30, lecteur 30/30, Narrer + progression OK, aveugle 3/3, 360 px OK. Coût mesuré 20 pages : K3 0,363 $, Pixtral 0,077 $. Détail § 4-ter. |
| 2026-07-28 (soir) | **✅ Proxy redémarré, la suppression est ACTIVE : banc 8/8.** Et une leçon payée en coupant un service : j'avais vérifié la **logique** de lecture du secret (en `python -c`, où `io` est importé) mais **jamais le démarrage réel du proxy** — qui, lui, n'importe pas `io`. `NameError: name 'io' is not defined`, proxy **down**, découvert seulement après la coupure. ⇒ **Tester l'effet, pas la formulation** : la seule vérification qui vaut pour un service, c'est de le LANCER. Corrigé (`open()` natif, aucune dépendance), démarrage vérifié **avant** de le remettre en agent. ComfyUI n'a pas bougé — il est indépendant du proxy (parents différents, vérifié avant de couper). |
| 2026-07-28 (soir) | **Supprimer un projet supprime enfin ses images — et le disque a rendu 1 Go.** Quang : *« la base conserve les images même si je supprime des projets [...] le répertoire manga est vraiment contaminé de vieilles données, ce n'est pas du tout acceptable »*. Le comportement était **assumé dans le code** (« effacer une fiche ne doit jamais effacer des images ») ; son avis le renverse, et c'est le sien qui compte : *un projet supprimé qu'on retrouve en fouillant le disque n'est pas supprimé*. `delete_manga_project` balaie désormais les **deux** dossiers — les images rangées **et l'atelier de ComfyUI**, invisible depuis l'app et jamais nettoyé — et **rapporte** le nombre de fichiers effacés (une suppression silencieuse ne se vérifie pas). Gardes : un slug vide ou suspect n'efface **rien** (il viserait la racine), et le contrôle anti-traversée est refait à chaque dossier. État mesuré : **1051 Mo** à nettoyer — **700 Mo d'atelier**, 165 Mo de mes bancs, 187 Mo d'orphelins. `scripts/menage_sorties.py` (dry-run par défaut, projets vivants **intouchables dans les deux dossiers**) a tout rendu. Banc `test_suppression_projet.py` : le cas qui compte n'est pas « ça efface » mais **« ça n'efface QUE ça »** — le projet voisin est vérifié intact après coup. |
| 2026-07-28 (soir) | 🔴 **Le `WORKER_SECRET` était ENCORE en dur dans le proxy** — trouvé en lisant le fichier pour tout autre chose : `SECRET = os.environ.get("WORKER_SECRET", "<la valeur>")`. **C'est LA source des trois rechutes** : la valeur vivait dans un fichier qu'on copie, qu'on sauvegarde en `.bak` et dont on versionne les diffs. Elle se lit désormais dans l'environnement ou dans `ComfyUI/.worker_secret`, et le proxy **s'arrête en le disant** si elle manque. ⚠️ **Et le diff qui la retire la contenait** — dans sa ligne *supprimée*. Même piège qu'en juillet, par l'autre bout : masquée, avec un en-tête qui prévient que le diff n'est plus applicable tel quel. |
| 2026-07-28 (soir) | **`ignore_errors=True` a fait mentir mon script de ménage.** Il a annoncé « EFFACÉS » alors qu'un dossier avait résisté (tenu par un autre processus). Les fichiers étaient bien partis, mais l'outil ne l'avait pas vérifié. ⇒ **Un outil qui ne contrôle pas son propre geste rapporte une action, pas un fait.** Il vérifie maintenant, et nomme ce qui a résisté. |
| 2026-07-28 (soir) | **v1.65.0 — une case ANCIENNE ne perd plus son image d'origine.** Quang : *« le lot remplace littéralement les images qui étaient présentes avant »*. Vérifié en base : ses cases régénérées ne portaient plus qu'**un** essai. **La cause n'était pas le lot** — le bouton unitaire aurait fait pareil, c'est le même `genPanel`. Ses cases dataient d'**avant la v1.48.0** : elles ont un `file` mais **aucun `versions`** ; l'historique repartait donc de `[]` et l'image d'origine n'y entrait jamais. ✅ **Rien n'avait été perdu sur le disque** — le fichier était toujours là, simplement plus atteignable depuis l'app. `essaisAvec()` la réintègre en tête (une seule fois, comparaison par nom de fichier : les versions reviennent de la base, ce ne sont plus les mêmes objets). `scripts/reparer_essais.py` répare le passé : **6 images rendues** à ses 6 cases, dry-run par défaut, aucune suppression. Banc 17/17, dont le cas exact — une case sans historique. |
| 2026-07-28 (soir) | **Mon script de réparation a d'abord annoncé « 0 orpheline sur 35 cases ».** Un zéro rassurant et **faux** : la route `/manga/files` rend `{files: [...]}` et non `{items: [...]}` comme ses voisines — je lisais une clé qui n'existe pas, donc une liste vide. ⇒ **Une liste vide n'est pas une preuve d'absence : c'est souvent la preuve qu'on a mal demandé.** Le script s'ARRÊTE désormais s'il ne trouve pas la clé attendue, au lieu de conclure « rien à faire ». Même famille que `feedback_sortie_vide_nest_pas_une_preuve`. |
| 2026-07-28 (soir) | 💡 **Pourquoi le banc n'avait rien vu** : ses cases de test avaient toutes un historique. **Un banc ne trouve que les cas qu'il met en scène** — et le cas qui casse est presque toujours l'ancien état, celui qu'on ne pense pas à recréer parce qu'on ne le produit plus. Le cas « case d'avant la v1.48.0 » y est désormais. |
| 2026-07-28 (soir) | **v1.64.0 — régénérer un LOT de cases, choisies sur MINIATURES.** Demande de Quang : *« un bouton [...] soit je régénère tout, soit je sélectionne [...] une vue miniature des cases, puis je choisis lesquelles — au lieu de le faire case par case »*. Pop-up de vignettes : les cases déjà dessinées sont **pré-cochées** (le cas courant est « je veux revoir ma planche »), celles **sans texte sont désactivées** — on ne dessine pas sans description. Régénération **en série** avec témoin d'avancement (une seule carte, 16 Go), **seed neuve par case**, et les essais précédents restent accessibles. Banc `test_regen_lot.py` **14/14** dont une régénération réelle, mutation rouge. |
| 2026-07-28 (soir) | **Le libellé « Générer toutes les cases vides » MENTAIT, et son refus aussi.** Quang : *« j'ajoute des cases vides, je clique, il dit qu'il n'y a aucune case vide à générer »*. Le filtre exige un **texte** (une case sans description n'a rien à dessiner) mais le message parlait comme si la case n'existait pas. Le refus **nomme désormais les cases fautives** (« case(s) n°3 : écris d'abord ce qu'on y voit »), l'affiche **dans** la case concernée, et le bouton s'appelle **« Générer les cases décrites »**. ⇒ *Un refus doit nommer SA raison, sinon il se lit comme une panne.* |
| 2026-07-28 (soir) | **Le lot redessinait la MÊME image quand le tiroir « Affiner » était ouvert.** `genPanel` lit la seed dans le **champ** `[data-seed]`, pas dans la recette : tiroir fermé le champ n'existe pas et tout va bien, tiroir **ouvert** il porte l'ancienne valeur et **gagne**. Le lot aurait été un long geste sans effet — *le pire des résultats, parce qu'il ressemble à un fonctionnement*. La seed s'écrit maintenant **aux deux endroits**. 🔎 **Trouvé par une mutation qui restait VERTE** : le tirage était écrit en ligne, donc non remplaçable, donc non falsifiable. Extrait en `seedNeuve()` — **un comportement qu'on veut pouvoir saboter doit avoir un nom.** |
| 2026-07-28 (soir) | **v1.64.1 — le contexte de scène SORT du chemin fidèle.** Le banc a attrapé « seiza » — une posture venue de la case **précédente** — dans les tags d'une case qui parlait d'autre chose, **une fois sur deux**. Le contexte y était « pour désambiguïser », avec consigne explicite de ne rien en reprendre ; le modèle ne la respecte pas toujours. La distinction du 27/07 tranche : **TRADUIRE est fidèle** (il ne reçoit plus rien), **AMÉLIORER enrichit** (le contexte y reste, la continuité du lieu y est le but). Ce qu'on perd est minime : le `COUNT` se lit dans la phrase seule, l'identité vient du casting. ⚠️ **Un défaut intermittent est le pire** : il passe les contrôles et vit chez l'utilisateur. Le banc est désormais **déterministe** (15/15 sur trois passes). |
| 2026-07-28 (soir) | **v1.63.0 — une CASE contient une image, pas une planche.** Signalé par Quang : sa case 5 est sortie avec *« plusieurs petites fenêtres dans l'image »*, et il pose le bon diagnostic — *« un manque de contrôle sur le nombre de fenêtres »*. **Ce n'était pas aléatoire** : le prompt **enregistré** portait `manga panel, **grid lines**, shibari…`. `grid lines` ne vient pas de lui — c'est l'**amélioration** qui l'a ajouté (le même tag figurait déjà dans une autre de ses cases). Le tag décrit littéralement des lignes de grille. Juge : le **détecteur de cases de la phase 3** (celui de l'ingestion — c'est son métier), calibré d'abord sur ses deux images réelles, où il compte **8 fenêtres**. Mesure sur **sa** seed : `tel quel` **2/4** (dont une à 8 fenêtres) · sans `grid lines` **3/4** · + négatif anti-planche **4/4**. Livré : les tags qui fabriquent une planche sont **retirés du positif par le code** (`TAGS_PLANCHE`) et le vocabulaire de la planche part au **négatif** sur toutes les cases. Résultat mesuré sur 8 seeds : **7/8** contre 2/4 avant. 📌 `manga panel` est **conservé** : le duel E vs D sur 8 seeds donne 7/8 contre 8/8 — **un écart de 1, non concluant**. On retire ce qui nuit (prouvé), pas ce qui ressemble. À re-mesurer si le défaut revient. |
| 2026-07-28 (soir) | **v1.62.0 — `2people` n'existe pas dans le vocabulaire du modèle, et il faisait PIRE que rien.** Le duo était le point dur annoncé. Mesure (`scripts/test_duo_comptage.py`, 25 générations, mêmes seeds, une scène qui demande deux personnages) : **`2people` 2/5** — ce que l'app envoyait — contre **aucun tag 3/5**, **`1boy 1girl` 3/5**, **`2boys` 4/5**, et **`multiple people` 0/5** (des foules de 7 à 24 personnages). Un tag inventé ne vaut pas zéro : il consomme des tokens et pousse vers 3 corps. Le tag est désormais choisi dans le vocabulaire danbooru réel, à partir du genre lu dans l'identité du casting et les tags de la case ; **genre indéterminé ⇒ on n'ajoute RIEN** (3/5 vaut mieux que 2/5). `multiple people` est banni. Banc 25/25, mutation rouge. |
| 2026-07-28 (soir) | **⛔ MA MESURE DU DUO A D'ABORD CONCLU L'INVERSE — l'instrument était aveugle.** Le premier verdict donnait **0/5 partout, témoin compris**, et j'en avais tiré (dans un message à Quang) que « le duo n'est respecté que 1 à 2 fois sur 4 ». **Faux.** Le juge comptait des **visages** : en plan large, aucun n'est détectable, alors que les images montraient bien deux personnages — la planche-contact l'a montré en un coup d'œil. La mesure ne disait pas « pas de personnage », elle disait « pas de visage ». ⇒ `scripts/juge_personnages.py`, qui **se calibre sur des comptes vérifiés à l'œil avant de servir** (5/6 ; son unique erreur est une **sous-estimation** sur un gros plan sans corps — une erreur qui va toujours dans le même sens reste exploitable, cf. la mesure de cadrage du 27/07). **Deuxième fois en deux jours qu'un instrument non calibré fait conclure à l'envers** : ne jamais publier un chiffre avant d'avoir montré que l'outil retrouve un cas connu. |
| 2026-07-28 (soir) | **⛔ HYPOTHÈSE INFIRMÉE — l'ordre du prompt ne change rien.** J'avais signalé à Quang que sur « Magic woman » sa demande arrivait en ~45ᵉ position, au-delà des 77 tokens d'un chunk CLIP, et qu'elle pesait donc « presque rien ». Mise au banc avant d'y toucher (`scripts/test_ordre_prompt.py`, 24 générations, mêmes seeds, style long de 28 tags, juge = détecteur de visages sur des demandes dont le respect se **compte**) : **A (actuel) 9/12 · B (demande en tête) 9/12**. Écart nul. ⇒ **On ne change pas l'app** : ce serait un chantier gratuit, et le style en tête reste la convention booru. 📌 Ce que la mesure montre au passage, et qui est le vrai sujet : « deux personnages face à face » n'est respecté que **1/4 et 2/4** — quel que soit l'ordre. Le duo reste le point dur, comme la phase 10 le disait. 💡 Troisième hypothèse plausible infirmée par la mesure en deux jours. Le coût d'un banc est de dix minutes ; celui d'un chantier bâti sur une intuition, une session entière. |
| 2026-07-28 (soir) | **v1.61.0 — le COMPTAGE cesse d'être une liste de mots.** Mesure du matin : **5 comptages faux sur 14**. `nbPersonnages()` cherchait des sujets dans une liste fermée de 28 mots — elle ratait « les deux **adversaires** », « **elle** s'élance et **lui** donne », « les autres **élèves** », et la vraie case de Quang de 11h36 (*« elle frotte ses orteils… l'homme attaché au lit »*, sortie en `solo` pour une scène à deux). Une liste fermée ne tiendra jamais : la langue est ouverte. On demande donc le compte **à qui lit la phrase**, sur une ligne `COUNT:` séparée — même mécanique que `NEG:` — et l'app l'impose dans le code. Mesuré : **13/14 exacts, 1 absent** (contre 5 faux). L'ordre de confiance n'est plus un `Math.max` aveugle : casting coché **puis** compte du modèle **puis** heuristique. |
| 2026-07-28 (soir) | **Trois défauts en chaîne sur ce seul chantier, tous silencieux, tous trouvés en LISANT la donnée.** (1) La consigne demandait le COUNT puis finissait par « Nothing else » : **0 COUNT sur 14** — *une consigne qui se contredit est tranchée par sa fin*. (2) Corrigée, le modèle répondait bien `COUNT:2`… et `traduire()` faisait `split("
")[0]` **avant** l'extraction : il le jetait puis constatait qu'il manquait. (3) Mon banc affichait « 0 COUNT absent » alors qu'il l'était **sur les 14** : le compteur n'était jamais incrémenté (remplacement de texte silencieusement raté). ⇒ **Un chiffre doit venir d'une addition, jamais d'une valeur par défaut** — et un `.replace()` de patch sans `assert` ment sans bruit. |
| 2026-07-28 (soir) | **Le casting disait COMBIEN alors qu'il ne sait que QUI.** « elle est debout au-dessus de lui, il est attaché sur le lit » avec **une** fiche cochée : le casting répondait 1, et l'homme non fiché disparaissait du prompt. Le casting devient un **plancher** (ces gens-là sont là, c'est un fait), que le compte du modèle peut relever s'il voit des figurants en plus. Vérifié bout en bout : `2people` part enfin. |
| 2026-07-28 (soir) | **La traduction recopie parfois le français, et le moteur ne s'en plaint pas — il dessine.** Vu au banc live : *« elle est debout au-dessus de lui… »* ressorti mot pour mot. On ne peut pas empêcher un modèle de se tromper, on peut le **rappeler une fois** : seconde tentative explicite, puis signalement visible si elle échoue aussi (jamais de boucle muette). ⚠️ Défaut trouvé dans mon propre correctif par le banc de scène : la relance **perdait le contexte de scène** — « elle » y redevenait indéterminée, et le comptage avec. |
| 2026-07-28 (soir) | **RÉGRESSION que j'ai introduite en v1.59.0, signalée par Quang (capture PC).** Le séparateur de scène était posé **avant chaque case** en `grid-column:1/-1` : chaque case démarrait donc après une ligne pleine largeur ⇒ **une case par ligne**, sa planche à 2 colonnes n'en avait plus qu'une. Le séparateur ne s'affiche désormais qu'aux **vraies frontières** (là, une ligne entière est justement ce qu'on veut) ; le geste « couper la scène » vit dans un **badge `✂` au coin de chaque case** — visible partout, et il ne prend aucune place dans la grille. ⚠️ **Ma parade intermédiaire était fausse aussi** : j'avais élargi la page à 1600 px pendant que le bandeau et les onglets restaient à 760 — *deux largeurs pour une même page*. Quang : *« tu es censé respecter la largeur initiale […] et ne pas la faire dépasser »*. Largeur initiale restaurée : ce qu'il avait perdu, c'étaient les **colonnes**, pas la largeur. Banc `test_grille_largeur.py` **11/11**, qui **mesure la géométrie** (`getBoundingClientRect`) et non le CSS — le `grid-template-columns` était juste pendant tout ce temps. |
| 2026-07-28 (soir) | **Le piège `hidden`, payé une TROISIÈME fois, enfin traité à la racine.** Le bandeau « revenir à la planche » s'affichait alors qu'il était marqué `hidden` : `.row{display:flex}` écrase le `display:none` implicite. Déjà payé sur le voile des cases (v1.0.1) et le témoin « proxy injoignable » (v1.33.0). La ROADMAP demandait d'écrire la parade **élément par élément** — c'est une discipline, donc ça rate. Une règle **globale** `[hidden]{display:none !important}` ne s'oublie pas. Vérifié par un test sur un élément *porteur* d'un `display`, pas sur un cas facile. |
| 2026-07-28 (soir) | **v1.60.0 — le CASTING et le DÉCOR suivent la scène, plus la planche.** La v1.59.0 avait posé la scène comme frontière de contexte, mais les deux choses qui *définissent* une scène — qui est là, où on est — restaient accrochées à la planche : deux scènes d'une même planche partageaient la même troupe et le même décor figé. **Principe retenu, zéro concept et zéro UI en plus : le casting d'une scène = celui de sa PREMIÈRE case.** On coche les personnages sur la case qui ouvre la scène (le geste « Qui est là », déjà connu) et les suivantes en héritent. C'est aussi l'intuition juste : *qui joue dans cette scène* = qui est là quand elle commence. Chaîne complète : **BASE → TROUPE → PLANCHE → SCÈNE → CASE**, chaque palier pouvant se **taire** (= hérite) ou dire **« personne »** (= liste vide) — deux choses différentes. Le décor : une scène peut avoir le sien (`recipe.sceneMaster`), généré depuis le bouton `🎞 décor…` du séparateur ; le panneau **annonce pour qui il travaille** et les fichiers portent l'id de la scène — sans quoi le décor de la scène 2 écraserait celui de la scène 1 (même planche, même nom : le piège des versions de case, v1.48.0). Une scène muette retombe sur la planche ⇒ **aucune migration**, les planches existantes ne bougent pas. Banc `test_scene_casting_decor.py` **16/16** dont 4 en génération réelle, mutation rouge (3 cas). |
| 2026-07-28 (soir) | **Un banc qui attend un témoin qu'il n'a pas vidé annonce trois échecs imaginaires.** La partie live attendait `sceneMaster.depthInput` — un champ que le **décor factice du test précédent possédait déjà**. L'attente rendait la main instantanément et le banc lisait le faux décor en croyant lire le vrai : trois « défauts » signalés alors que la génération était juste (vérifié à part, en isolant le chemin). ⇒ **Un banc remet son décor à zéro entre deux cas, et attend un témoin qu'il vient lui-même de vider.** Troisième fois en deux jours qu'un banc accuse l'app à tort — après le décor posé sur `window` et la capture du run muté. |
| 2026-07-28 (soir) | **v1.59.0 — LA SCÈNE : une planche est une mise en page, pas une unité de récit.** Quang : *« je pensais que, quand j'ajoutais une case, le contexte des cases précédentes était pris en compte »* — et il pose lui-même l'effet de bord : au changement de scène, ce contexte doit **cesser**. État mesuré avant d'écrire une ligne : `3 suites` recevait les 5 cases précédentes, `Dialogues de la planche` toute la planche, mais **`✨ Améliorer` et la traduction ne recevaient RIEN** (`Scene: <la phrase>`, seule). Sa case de 11h36 — *« elle frotte ses orteils… l'homme attaché au lit »* — est sortie en **`solo`** au premier jet : personne ne savait qu'ils sont deux. **Décision d'architecture** : la planche est une unité de **mise en page**, la scène une unité de **récit** (lieu + moment + qui est là). Les faire coïncider laisserait le format du papier décider du découpage narratif — et obligerait à casser une mise en page pour changer de lieu. La scène est donc un **groupe de cases consécutives**, marqué par un séparateur `✂` entre deux cases ; un seul drapeau sur la case qui **ouvre** (pas de fin à tenir à jour, donc rien qui puisse devenir incohérent). Sans séparateur : une planche = une scène = le comportement d'avant, à l'identique. ⚠️ **Le contexte reste dans la couche LLM et n'entre JAMAIS dans le prompt SDXL** — l'y mettre referait le défaut du 28/07 (dix cases, la même composition) et pousserait la demande encore plus loin au-delà des 77 tokens de CLIP. Un banc le vérifie explicitement. Banc `test_scene_contexte.py` **14/14**, mutation rouge (7 cas tombent) : il mesure le contexte **sur le corps HTTP réel** (`fetch` écouté, `api()` **pas** remplacé) et vérifie les deux sens — repris au milieu d'une scène, **absent** sur la case qui en ouvre une. |
| 2026-07-28 (soir) | **Le run muté écrasait la capture du run normal — et j'ai lu la mauvaise.** La capture montrait « scène 1 · case 4 » là où l'app coupe en scène 2 : j'ai failli diagnostiquer un bug inexistant. C'était l'écran de l'**app sabotée**, le mode `--muter` écrivant dans le même fichier. ⇒ **Une capture de banc doit porter dans son NOM la variante qui l'a produite.** Même famille que les pièges déjà payés ici : une mesure juste, prise au mauvais endroit, se lit comme une preuve. |
| 2026-07-28 (soir) | **v1.58.0 — la phrase de Quang cesse d'être détruite, et les négations cessent de demander le contraire.** Signalé par lui : *« mes requêtes sont plus des phrases explicatives que de vrais prompts »*. **Rien n'était auditable** : `traduire()` et `ameliorerPrompt()` faisaient `p.prompt = <sortie du LLM>` — la phrase française n'existait ni en base ni dans le journal. Rejouée sur 14 phrases écrites comme il écrit (`scripts/banc_traduction.py`) : **5/14 négations rendues en tag POSITIF** (« on ne voit pas son visage » → `face not visible`, « pas de tête » → `no head, no face`, « aucun personnage » → `1girl, …, no humans`), **5/14 comptages faux**, 0/14 cadrage perdu. Livré : la phrase reste dans son champ et les **tags partent dans `recipe.tags`, visibles et corrigeables** ; les négations vont au **NÉGATIF** (ligne `NEG:` déjà extraite par le proxy depuis v5.44) ; une case « sans personne » impose `no humans` et coupe casting, comptage et identité ; l'**échelle du plan commande l'identité** (0 = rien + IPAdapter coupé, 1 = traits du visage, 2 = complète) ; le style est dédoublonné. Bancs : `test_prompt_v158.py` **21/21** (mutation rouge, 3 cas tombent), `test_phrase_intacte_live.py` **15/15** avec générations réelles. |
| 2026-07-28 (soir) | **La parade « gros plan sans visage » a été CHOISIE PAR LA MESURE, et ma première idée était fausse.** Après avoir retiré l'identité, le modèle dessinait **toujours** un visage plein cadre. 15 générations, 3 formulations, mêmes seeds (`scripts/test_sans_visage.py`, juge = le détecteur `face_yolov8m` déjà utilisé par `crop_ref.py`) : identité retirée seule **1/5** sans visage (moyenne 0,501) · + comptage retiré + négatif élargi **3/5** (0,227) · + **tags positifs de recadrage** (`head out of frame, cropped`) **4/5** (0,037). ⇒ Deux enseignements : **`1girl` seul suffit à ramener le visage** (je le gardais en me disant que des mains ont un propriétaire), et **un négatif interdit, il ne recadre pas** — il faut dire au positif où est le cadre. |
| 2026-07-28 (soir) | **Quatre défauts trouvés en chemin, tous silencieux.** (1) **Trois regex mortes en production** : un `` avait été écrit comme un vrai caractère **backspace** (U+0008) par un édit passé — `/1boy 1girl/`, `/ink/` et le nettoyage du style ne pouvaient *jamais* matcher. (2) `new RegExp("" + n + …)` : dans une **chaîne** JS, `` est aussi un backspace — le garde anti-double-comptage n'a jamais fonctionné, d'où `2people` **et** `1girl, 1boy` dans le même prompt. (3) Le modèle a rendu `NEG: no_humans` **avec underscore** : mis au négatif tel quel, il réclamait des humains dans une case qui demandait un dojo vide — un négatif qui exige ce qu'on refuse. (4) `empty` présent **au positif ET au négatif** de la même case ⇒ règle `sansContradiction()` : un tag entier demandé n'est jamais interdit. |
| 2026-07-28 (soir) | **Mon banc s'est trompé deux fois avant de servir, et c'est instructif.** (a) Il posait son décor par `window.CHARS = […]` — or `CHARS` est déclaré `let` : une **liaison lexicale n'est pas une propriété de `window`**. Le casting restait vide, et tous les cas « ce tag doit être ABSENT » passaient au vert **pour la mauvaise raison**. (b) Décor réparé, il le posait **une seule fois** — l'app recharge ses fiches en asynchrone et **réassigne** `CHARS`, donc il s'effaçait en cours de boucle : les premiers cas passaient, les derniers échouaient, et le banc accusait l'app. ⇒ **Un témoin positif explicite** (« le décor est-il monté ? ») est désormais vérifié à chaque cas, et le banc s'arrête s'il manque. Et c'est la **capture**, pas le code, qui a montré que l'aperçu se contredisait : « identité retirée » suivi de « Kimiko sera dessiné quand même ». |
| 2026-07-28 | 🔴 **SÉCURITÉ — le `WORKER_SECRET` était versionné EN CLAIR dans un dépôt PUBLIC** (`quang101182/App`, depuis le commit `61cbab9` du 26/07). Trouvé en versionnant la route `/manga/crop_ref` : le diff du proxy le portait dans une ligne de contexte, et **cinq scripts** l'avaient en dur. Retiré partout (lecture par `WORKER_SECRET` ou `ComfyUI/.worker_secret`, hors dépôt, avec arrêt explicite s'il manque). ⚠️ **Ce n'est pas la remédiation complète** : l'historique git reste lisible publiquement ⇒ **le secret doit être CHANGÉ côté gateway** — décision de Quang, il est partagé avec d'autres apps. |
| 2026-07-28 | **v1.56.0 + v1.57.0 — l'alerte de casting, puis les dialogues de la planche.** (1) L'aperçu prévient quand le texte d'une case et son casting divergent — il **avertit**, il ne refuse rien (l'heuristique de texte reste « trop faillible pour retirer un bouton », v1.24.0 ; ce qui change, c'est le coût d'un faux positif). (2) **💬 Dialogues de la planche** : les répliques de toute la planche écrites **d'un seul tenant** au lieu de case par case. Essai réel, 12 cases : dialogues courts qui s'enchaînent, rien sur les cases de décor. **Leçon : une consigne dans un prompt n'est PAS un garde-fou** — le modèle a ignoré « une case sans personne n'a aucune réplique » au premier essai et l'app a posé la bulle. Les deux garde-fous sont désormais vérifiés dans le code. Bancs : 11/11 et 9/9, mutations rouges. |
| 2026-07-28 | **Trois bancs périmés réparés, tous de la même famille.** `test_references` pariait sur 5 s fixes là où le recadrage ajoute un aller-retour serveur ; `test_personnages` était mort depuis la **v1.39.0** (« Qui joue sur cette planche » ne montre que la troupe, et il n'y inscrivait pas ses fiches) ; il cliquait en prime sur le mauvais onglet. **Troisième récidive** (après `test_perso_dessiner` et `test_references` en v1.38.0) : *quand l'UI replie, filtre ou déplace une liste, les bancs qui la parcouraient meurent en silence — et accusent l'app.* |
| 2026-07-28 | **v1.53.0 → v1.55.0 — les références et l'affichage.** Recadrage de la référence sur le visage (**4/6 → 6/6** personnages corrects) ; l'état « aides affichées » n'est plus rouge (il se lisait comme une alerte) ; une image qui n'a pas chargé **se réessaie et le dit** — le fichier était intact, seul le chargement avait échoué. ⚠️ Le banc ne pouvait pas le voir : il comptait les **balises** `<img>`, pas les images affichées. C'est Quang qui l'a vu. |
| 2026-07-28 | **v1.52.0 — deux visages tenus dans une même case.** Deux références IPAdapter, chacune bornée à une moitié par `attn_mask`, poids **0,6** : **6/6** contre **1/6** à une seule référence — qui *contaminait* le second personnage. Trois hypothèses posées et **infirmées** le même jour (les masques imposeraient deux bandes · l'action serait noyée en fin de prompt · le portrait rendrait les masques trop étroits) : la vraie cause tenait en une ligne du prompt enregistré. |
| 2026-07-27 | **v1.22.0 + REVALIDATION.md — fin de session.** La sequence cree desormais des cases SEPAREES (elle ecrasait l'image de la case de depart : deux fichiers ranges au meme endroit, vu dans le journal) et se joue **en defile** (▶, aller-retour) — seul moyen de JUGER une sequence, alignees on voit des dessins, enchainees on voit si le geste tient. Les cases suivantes sont **reindexees** (bug latent : deux `idx` identiques = ordre de lecture aleatoire au rechargement). ⚠ **`REVALIDATION.md` ecrit** a la demande de Quang : 22 versions en une session, chaque piece mesuree isolement, **l'ensemble jamais**. Lacune assumee en tete du document : **rien n'a ete teste sur le Samsung reel** — tous les bancs tournent dans un Edge emule. 11 fonctions sur 20 n'ont pas de banc rejouable. |
| 2026-07-27 | **v1.20.1 — la sequence ne demarrait pas chez Quang, et le journal l'a prouve.** « J'ai clique, visuellement je ne vois pas de difference » : le journal ne montrait **aucune** ligne de sequence, et aucune case ne portait de marquage — elle n'avait jamais demarre. Cause : **deux `prompt()` en cascade**. Sur telephone, une boite annulee ou une saisie hors des trois mots attendus ne laissait qu'un toast de 2,6 s. Remplaces par un **panneau dans la case** : on CHOISIT le geste puis le nombre, et on peut annuler. Ses trois questions avaient la meme racine — ce n'est **pas un mode** (rien a desactiver), c'est une action ponctuelle ; et une case issue d'une sequence porte desormais un **badge 🎬 2/4**, puisque rien ne la signalait. Lecon : un reglage se choisit a l'ecran, il ne se tape pas de memoire. |
| 2026-07-27 | **v1.20.0 — la SEQUENCE est dans l'app** (bouton 🎬 sur chaque case). On ecrit l'action, on choisit un geste (coup · marche · chute) et 2 a 6 vignettes : l'app cree les cases, fabrique les squelettes openpose interpoles **en canvas cote client** (pas de dependance a un script Python) et genere la suite a **seed FIXE** — c'est lui qui garde le meme dessin. `wfPanel` accepte desormais openpose OU depth, **jamais les deux** (les cumuler ferait s'annuler les deux contraintes). `front view` impose, sinon le personnage se retourne au milieu de la suite. Mesure dans l'app : 3/3 vignettes, meme seed partout, 0 erreur JS, et le geste est lisible a l'oeil. |
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

### 27 — PROFIL DE SÉRIE + « TOUT TRAITER » — ✅ FAIT v2.4.0 (22/09 15h40 ; cadrage 15h10, feu vert Quang 15h12 « go non stop »)

**Livré** (P1 `d318722`, P2+P3 ce commit) : `suivi_nuit.py` v2.4.0 = la chaîne ; `patch_profil.py` (proxy) ; panneau
« ⚙ Profil et traitement » (remplace « 🌙 Suivi »). **Bancs** : `test_chaine.py` **18/18** (lot RÉEL 2 chapitres jusqu'aux
2 vidéos, pages traduites ; relance = rien à faire ; mutation « même langue » rouge) · `test_profil.py` **19/19** (8191
puis 8190 : défaut d'une série neuve, ⭐/↺, normalisation, lots invalides refusés, lot réel suivi dans l'activité) ·
`test_profil_ui.py` **17/17** (8191 puis 8190 : 360 px sans débordement, puces, sélection, « Lancer » refusé = rien
d'envoyé, ⭐, VRAI lot depuis le bouton → ✅ + puces en couleur). Défauts trouvés en route : clé « t » en double dans le
journal (crash après le 1er chapitre) ; cases à cocher pleine largeur (styles globaux) ; « dernier passage » d'une AUTRE
série affiché (l'état est commun → filtré par série). **Décision prise seul** : le défaut général ne copie PAS « la nuit »
(une série neuve ne dépense rien toute seule) ; moteur/voix PAR CHAPITRE = plus tard si besoin.

**Demande** : régler une fois (moteur, voix, langue de traduction, musique, karaoké, « Précédemment », vidéo), l'appliquer
à toute la série, puis lancer d'un geste la chaîne complète — sur toute la série ou une sélection — jusqu'à la vidéo de
chaque chapitre. + un bouton « ces réglages = mes réglages par défaut » pour toute NOUVELLE série. « Pratique,
ergonomique et joli. » Quang (15h03) : « je te laisse prendre les meilleures décisions ».

**Constat qui fixe l'architecture (vérifié dans le code 22/09)** : `scripts/suivi_nuit.py` EST déjà cette chaîne
(narration → karaoké → « Précédemment » → vidéo, réglages par série dans `sources/<serie>/suivi.json`, verrou « un seul
passage », journal). ⇒ **on l'étend, on n'en écrit pas une 2ᵉ.** Il lui manque : la traduction, une sélection de
chapitres à la demande, le « refaire », et des réglages par défaut.

**Trois niveaux de réglages**
| Niveau | Fichier | Rôle |
|---|---|---|
| Défaut général | `sources/_profil_defaut.json` (NOUVEAU) | ce que reçoit une série qui n'a pas encore de profil ; ⭐ « En faire mes réglages par défaut » y copie le profil affiché |
| Profil de la série | `sources/<serie>/suivi.json` (EXISTANT, étendu) | moteur, voix, `traduction` (NOUVEAU : "" = aucune, sinon fr/en/…), karaoké, précédemment, vidéo + `reglages_video`, `actif` (nuit) ; ↺ « Reprendre mes défauts » |
| Chapitre | `musique.json` (EXISTANT) | seule exception par chapitre en v1 : la musique « propre au chapitre ». Moteur/voix par chapitre = plus tard si le besoin apparaît (la narration « Autre voix » reste possible à la main) |
La musique de la série reste `musique/choix.json` (existant) : le profil l'AFFICHE et renvoie à son bloc, il ne la duplique pas.

**Décisions (croisements)**
1. Ordre, par chapitre : narration → karaoké → traduction → « Précédemment » → vidéo. **Chapitre par chapitre** (le 1er
   est regardable pendant que les suivants se font).
2. Déjà fait = sauté : narration `<moteur>-<voix>` finie, karaoké présent, traduction `<lg>` finie, ouverture à jour,
   vidéo « à jour ». Case « refaire » (lot uniquement) : force narration + étapes en aval.
3. Traduction vers la langue d'origine du chapitre : sautée (la protection fr→fr existe déjà).
4. Pages de la vidéo : traduites si la traduction existe, sinon VO (le proxy le fait déjà).
5. Un chapitre qui échoue n'arrête pas le lot : essai suivant, bilan « N faits / M échecs (raison) ».
6. Estimation coût + durée AVANT (celle du suivi, étendue à la traduction), confirmation ; pas de plafond auto.
7. La nuit (01:30) = la même chaîne sur les nouveaux chapitres des séries « actif ».
8. Un seul lot à la fois (verrou existant) ; capture et narration manuelle restent possibles en parallèle (frein commun).
9. Progression visible dans la cellule d'activité : « ⚙ lot One Punch-Man — ch. 297 (3/5) · narration ».

**Écran** (remplace le panneau « 🌙 Suivi », même langage visuel que la fiche : titres à icône + liserés)
```
⚙ Profil de la série — One Punch-Man                          [✕]
│🎙 Narration   moteur [Kimi K3 ▾]   voix [Charon ▾] [▶]
│🌐 Traduction  [aucune ▾]     (VO vietnamien)
│🎵 Musique     2 morceaux de la série  → régler
│✨ Extras      [✓] karaoké   [✓] « Précédemment… »
│🎬 Vidéo       [✓] fabriquer   vitesse 1,15 · sous-titres · musique 25 %
│🌙 La nuit     [✓] traiter tout seul les nouveaux chapitres (01:30)
 ⭐ En faire mes réglages par défaut     ↺ Reprendre mes défauts
 ─────────────────────────────────────────────────────────────
 ▶ Tout traiter…
   (•) chapitres pas terminés   ( ) toute la série   ( ) ma sélection
   [295 🎙🎤🌐🎬] [296 🎙· · ·] [297 · · · ·] …   (puce = état par étape)
   [ ] refaire même ce qui est déjà fait
   ≈ 5 chapitres · ~4,20 $ · ~2 h 10          [Lancer]
```

**Phases** (un commit + banc chiffré chacune)
- P1 moteur : `suivi_nuit.py` → `--chapitres`, `--refaire`, étape traduction, défaut général ; bancs à sec (`--dry`) + un vrai lot 2 chapitres Gemini.
- P2 proxy : `GET/POST /manga/profil_defaut`, profil étendu, `POST /manga/suivi_lancer {serie, chapitres, refaire}`, estimation + traduction, item « lot » dans `/manga/activite`.
- P3 app : le panneau ci-dessus (1280 + 360 px, captures), bilan du lot.
- DoD : un lot réel de 2-3 chapitres lancé depuis l'app, de la capture brute à la vidéo, sans intervention ; défaut appliqué à une série neuve ; nuit à sec (`--dry`) cohérente.

### 28 — WEBTOONS (manhwa) — ✅ capture + découpage + narration (22/09 16h10) ; 🟠 traduction des encadrés sombres

Question Quang 15h47 (lien *Solo Leveling: Ragnarok* ch.1, MangaDex, VO coréenne, traduction ITALIENNE). Mesuré : 26 bandes
de 800 × ~9 500 px. **Fait** (manga-fetch v0.4.2 + v0.5.0, détail README manga-fetch § Webtoons) : capture en bande
réparée (body ≠ bloc défilant) ; découpage automatique après capture (26 bandes → 129 pages, aucune coupe dans du texte) ;
narration Gemini 12 pages = récit fidèle (0,26 $). Chapitre de test gardé : `sources/banc-webtoon/ch_1` (à renommer ou
supprimer par Quang).
**Reste — déclencheur : prochaine session Manga Studio, avant tout autre chantier de traduction** :
(a) 🟠 traduction : encadrés TEXTE CLAIR SUR FOND SOMBRE non effacés (6 bulles vues sur 6 pages, texte resté en italien) →
détecter la polarité de l'encadré, remplir de SA couleur de fond, écrire en clair ; mesurer aussi la détection YOLO sur
ces encadrés rectangulaires. (b) 🟠 capture : deux onglets sur la même adresse → la capture prend le 1er (constaté 22/09).
