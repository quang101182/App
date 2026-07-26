#!/bin/bash
# Entrainement LoRA de personnage SDXL (kohya sd-scripts) sur le dataset bootstrap ReActor.
set -u
K="D:/Download/02-Apps-Web/kohya-trainer"
S="C:/Users/quang/AppData/Local/Temp/claude/D--Download-02-Apps-Web-Repo-github/697c79c3-713f-4bee-8edf-53d28a1f03b4/scratchpad"
CKPT="C:/Users/quang/Documents/ComfyUI/models/checkpoints/waiIllustriousSDXL_v170.safetensors"
OPT="${1:-AdamW8bit}"   # fallback : AdamW si bitsandbytes casse sous Windows

cd "$K" || exit 1
# Windows : la console est en cp1252, les logs de kohya contiennent de l'UTF-8
# (barres de progression, noms de buckets) -> UnicodeEncodeError qui tue le run.
export PYTHONIOENCODING=utf-8
export PYTHONUTF8=1
./.venv/Scripts/python.exe sdxl_train_network.py \
  --pretrained_model_name_or_path="$CKPT" \
  --train_data_dir="$S/lora_train/img" \
  --output_dir="$S/lora_train/out" \
  --logging_dir="$S/lora_train/log" \
  --output_name="zqmg1rl_v1" \
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
