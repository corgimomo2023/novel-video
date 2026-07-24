#!/usr/bin/env python3
import os
import re
from pathlib import Path

import runpod

ROOT = Path('/runpod-volume')
MODEL_CATEGORIES = ('diffusion_models', 'text_encoders', 'audio_encoders', 'vae', 'loras')


def redact(text: str) -> str:
    return re.sub(r'(?i)(bearer|token|secret|api[_-]?key)([=: ]+)[^\s]+', r'\1\2[REDACTED]', text)


def read_tail(path: Path, limit: int = 16000) -> str:
    with path.open('rb') as handle:
        size = os.fstat(handle.fileno()).st_size
        handle.seek(max(0, size - limit))
        return handle.read(limit).decode('utf-8', errors='replace')


def handler(_job):
    marker = ROOT / '.novel-video-models-ready.json'
    log = ROOT / 'logs' / 'worker-startup.log'
    categories = {}
    for category in MODEL_CATEGORIES:
        path = ROOT / 'models' / category
        categories[category] = {'exists': path.is_dir()}
    return {
        'volume_exists': ROOT.is_dir(),
        'ready_marker': marker.is_file(),
        'categories': categories,
        'startup_log_tail': redact(read_tail(log)) if log.is_file() else '',
    }


runpod.serverless.start({'handler': handler})
