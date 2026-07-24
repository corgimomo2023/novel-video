#!/usr/bin/env bash
set -o pipefail

log_dir=/runpod-volume/logs
log_file="$log_dir/worker-startup.log"

if mkdir -p "$log_dir" 2>/dev/null; then
    printf '\n=== worker startup %s ===\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$log_file"
    for category in diffusion_models text_encoders audio_encoders vae loras; do
        source_dir="/runpod-volume/models/$category"
        target_dir="/comfyui/models/$category"
        mkdir -p "$target_dir"
        if [ -d "$source_dir" ]; then
            for model in "$source_dir"/*; do
                [ -f "$model" ] || continue
                ln -sfn "$model" "$target_dir/$(basename "$model")"
            done
        fi
    done
    exec bash -o pipefail -c '/start.sh 2>&1 | tee -a /runpod-volume/logs/worker-startup.log'
fi

exec /start.sh
