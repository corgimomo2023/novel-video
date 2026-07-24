# RunPod Wan2.2 S2V Worker

Pinned thin image built on `runpod/worker-comfyui:5.8.6-base`.

## Files

- `workflows/wan2.2-s2v-ui.json`: official editable ComfyUI workflow.
- `workflows/wan2.2-s2v-api.json`: generated API workflow used by the backend.
- `models.json`: exact model URLs, byte sizes, and SHA-256 checksums.
- `populate_volume.py`: resumable model downloader for `/runpod-volume/models`.

## Validate without downloading models

```bash
python populate_volume.py --root /tmp/novel-video-volume --dry-run
```

## Build

```bash
docker build --platform linux/amd64 -t novel-video-wan-s2v:local .
```

Models remain on a RunPod Network Volume; they are not baked into the image.
