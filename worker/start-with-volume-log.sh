#!/usr/bin/env bash
set -e

# Keep startup free of Network Volume logging and directory scans. ComfyUI loads
# the verified model volume through /comfyui/extra_model_paths.yaml.
exec /start.sh
