#!/usr/bin/env bash
set -o pipefail

log_dir=/runpod-volume/logs
log_file="$log_dir/worker-startup.log"

if mkdir -p "$log_dir" 2>/dev/null; then
    printf '\n=== worker startup %s ===\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$log_file"
    exec bash -o pipefail -c '/start.sh 2>&1 | tee -a /runpod-volume/logs/worker-startup.log'
fi

exec /start.sh
