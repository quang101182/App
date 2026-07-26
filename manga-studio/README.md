# Manga Studio — scripts de la phase d'exploration (26/07/2026)

> État : **exploration terminée, app pas encore écrite.** Tous les verrous techniques sont levés et mesurés.
> **La feuille de route est le document de référence : [`ROADMAP.md`](ROADMAP.md)** — objectifs, décision
> d'architecture, verdicts chiffrés, pièges d'environnement, causes des échecs et leurs correctifs.

Ces scripts ne forment pas une application : ce sont les **bancs d'essai** qui ont servi à répondre, un par
un, aux « est-ce que c'est seulement possible ? ». Ils sont conservés parce que chaque chiffre de la roadmap
vient de l'un d'eux, et qu'ils sont réutilisables tels quels.

## Prérequis

| Quoi | Où |
|---|---|
| ComfyUI | `http://127.0.0.1:8188`, base-directory `C:\Users\quang\Documents\ComfyUI` |
| Checkpoint | `waiIllustriousSDXL_v170.safetensors` |
| ControlNet | `depth-sdxl`, `openpose-sdxl-xinsir`, `canny-sdxl-xinsir` |
| Entraînement LoRA | `D:\Download\02-Apps-Web\kohya-trainer\` (venv isolé, torch cu128) |
| YOLO + ultralytics | tourne dans le venv `kohya-trainer` |
| Segmenteur de mosaïque | `App/demosaic-pipeline/models/mosaic_position.pth` (son venv) |

⚠️ **Couper ComfyUI avant d'entraîner** — 16 Go de VRAM ne suffisent pas aux deux.

## Les scripts

### Génération et personnage
| Script | Rôle |
|---|---|
| `manga_test.py` | Essais 1-2 : rendu N&B par les tags · identité sans LoRA (**50 %**) |
| `manga_sheet.py` | Essai 3 : character sheet — **impasse**, visages non résolus |
| `manga_dataset.py` | Essai 4 : dataset par bootstrap ReActor (24 images cohérentes) |
| `prep_train.py` + `train_lora.sh` | Arborescence kohya, captions, entraînement (1 152 steps, ~34 min) |
| `manga_test_lora.py` | Essai 5 : rejoue l'essai 2 avec le LoRA (**89 %**) |
| `manga_scene.py` | Essai 6 : fond maître + ControlNet depth **@ 0,55** (décor tenu **6/6**) |

### Ingestion d'une page existante
| Script | Rôle |
|---|---|
| `panel_yolo.py` | **Découpage des cases et des bulles** (YOLO Manga109, IoU **0,90**) — le bon outil |
| `manga_ingest.py` | Pixtral : type de page, ordre de lecture, **fiche de style + prompt réutilisable**. ⚠️ son découpage de cases est **dépassé** par `panel_yolo.py`, ne pas l'utiliser pour ça |
| `manga_translate.py` | OCR japonais + traduction FR, **2 passes** (bulle isolée puis page en contexte) |
| `mosaic_seg.py` | Localise la censure (BiSeNet de DeepMosaics, segmenteur seul) |
| `inpaint_zone.py` | Reconstruit la zone masquée. **Le prompt doit décrire le sujet**, sinon le modèle improvise |

### Mesure
| Script | Rôle |
|---|---|
| `make_hard_page.py` | Fabrique une planche irrégulière **à vérité terrain** (pour mesurer, pas pour illustrer) |
| `panel_refine.py` | Contient `score()` / `iou()` — la mesure objective. Son raffinement OpenCV est **abandonné** (cf. roadmap) |

## Ce qui n'est PAS versionné

- **Les checkpoints du LoRA** (4 × 218 Mo). Un LoRA se réentraîne depuis son dataset : `prep_train.py` puis
  `train_lora.sh`. Le `zqmg1rl_v1.safetensors` utilisé pour les mesures est dans
  `ComfyUI/models/loras/_manga_test/`.
- **Les pages de Quang** et les images générées — matériel de test, pas du code.
- `dataset/` **est** versionné (31 Mo) : sans lui, aucun chiffre de la roadmap n'est reproductible.
