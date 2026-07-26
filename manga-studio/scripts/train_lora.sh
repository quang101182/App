#!/bin/bash
# Entrainement d'un LoRA de personnage SDXL (kohya sd-scripts).
#
# Les chemins pointaient vers le scratchpad d'une session (`.../697c79c3-.../`) qui
# n'existe plus, et le nom de sortie etait code en dur. Autrement dit : le LoRA v1
# n'etait REENTRAINABLE PAR PERSONNE, alors que ses chiffres etaient soigneusement
# consignes dans la roadmap. Meme defaut que prep_train.py, trouve le meme jour.
# => tout est desormais relatif au projet, et parametrable.
#
# Usage :
#   bash train_lora.sh                      # nom par defaut, AdamW8bit
#   bash train_lora.sh zqmg1rl_v2           # nom de sortie
#   bash train_lora.sh zqmg1rl_v2 AdamW     # + optimiseur (si bitsandbytes casse)
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
K="D:/Download/02-Apps-Web/kohya-trainer"
TRAIN="$HERE/lora_train"                    # produit par prep_train.py
CKPT="C:/Users/quang/Documents/ComfyUI/models/checkpoints/waiIllustriousSDXL_v170.safetensors"
NAME="${1:-zqmg1rl_v2}"
OPT="${2:-AdamW8bit}"

if [ ! -d "$TRAIN/img" ]; then
  echo "ERREUR : $TRAIN/img est absent. Lance d'abord :"
  echo "  python prep_train.py --src <dossier_dataset> --trigger <trigger>"
  exit 2
fi
N=$(find "$TRAIN/img" \( -name '*.png' -o -name '*.jpg' \) | wc -l)
echo "=== entrainement '$NAME' : $N image(s), optimiseur $OPT ==="
echo "    donnees : $TRAIN/img"
echo "    sortie  : $TRAIN/out"

cd "$K" || exit 1
# Windows : la console est en cp1252, les logs de kohya contiennent de l'UTF-8
# (barres de progression, noms de buckets) -> UnicodeEncodeError qui tue le run.
export PYTHONIOENCODING=utf-8
export PYTHONUTF8=1
./.venv/Scripts/python.exe sdxl_train_network.py \
  --pretrained_model_name_or_path="$CKPT" \
  --train_data_dir="$TRAIN/img" \
  --output_dir="$TRAIN/out" \
  --logging_dir="$TRAIN/log" \
  --output_name="$NAME" \
  --caption_extension=".txt" \
  --resolution="1024,1024" \
  --enable_bucket --min_bucket_reso=512 --max_bucket_reso=1536 \
  --network_module=networks.lora --network_dim=32 --network_alpha=16 \
  --learning_rate=1e-4 --unet_lr=1e-4 --text_encoder_lr=5e-5 \
  --lr_scheduler=cosine_with_restarts --lr_warmup_steps=50 \
  --optimizer_type="$OPT" \
  --max_train_epochs=8 --train_batch_size=1 \
  --mixed_precision=bf16 --save_precision=bf16 --no_half_vae \
  --cache_latents --gradient_checkpointing --sdpa \
  --save_every_n_epochs=2 --save_model_as=safetensors \
  --max_data_loader_n_workers=0 --seed=42
