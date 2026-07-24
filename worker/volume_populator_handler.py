#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path

import runpod

ROOT = Path('/runpod-volume')
MARKER = ROOT / '.novel-video-models-ready.json'
MANIFEST = json.loads(Path('/app/models.json').read_text(encoding='utf-8'))


def progress():
    files = []
    for model in MANIFEST['models']:
        target = ROOT / 'models' / model['folder'] / model['filename']
        partial = target.with_name(target.name + '.part')
        current = target.stat().st_size if target.is_file() else partial.stat().st_size if partial.is_file() else 0
        files.append({
            'folder': model['folder'],
            'filename': model['filename'],
            'current_bytes': current,
            'expected_bytes': model['bytes'],
            'complete': target.is_file() and current == model['bytes'],
        })
    return files


def handler(job):
    seconds = max(10, min(int(job.get('input', {}).get('chunk_seconds', 45)), 48))
    if not MARKER.is_file():
        try:
            subprocess.run(
                ['python', '/app/populate_volume.py', '--root', str(ROOT)],
                timeout=seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            pass
    files = progress()
    ready = MARKER.is_file()
    return {
        'ready': ready,
        'model_count': 5 if ready else sum(1 for item in files if item['complete']),
        'downloaded_bytes': sum(item['current_bytes'] for item in files),
        'total_bytes': sum(item['expected_bytes'] for item in files),
        'files': files,
    }


runpod.serverless.start({'handler': handler})
