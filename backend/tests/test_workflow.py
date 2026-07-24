import base64
import json
from pathlib import Path

import pytest

from app.workflow import WanS2VWorkflowFactory


def workflow_fixture(path: Path):
    path.write_text(json.dumps({
        "6": {"class_type": "CLIPTextEncode", "_meta": {"title": "CLIP Text Encode (Positive Prompt)"}, "inputs": {"text": "old"}},
        "52": {"class_type": "LoadImage", "_meta": {"title": "Load Image"}, "inputs": {"image": "old.jpg"}},
        "58": {"class_type": "LoadAudio", "_meta": {"title": "Load Audio"}, "inputs": {"audio": "old.mp3"}},
        "93": {"class_type": "WanSoundImageToVideo", "inputs": {"width": 640, "height": 640}},
        "104": {"class_type": "PrimitiveInt", "_meta": {"title": "Chunk Length"}, "inputs": {"value": 77}},
        "3": {"class_type": "KSampler", "inputs": {"seed": 1}},
        "113": {"class_type": "SaveVideo", "inputs": {"filename_prefix": "video/ComfyUI"}},
    }))


def test_factory_patches_workflow_and_embeds_assets(tmp_path: Path):
    workflow_path = tmp_path / "workflow.json"
    workflow_fixture(workflow_path)
    uploads = tmp_path / "media" / "uploads"
    uploads.mkdir(parents=True)
    (uploads / "ref.jpg").write_bytes(b"jpeg")
    (uploads / "voice.mp3").write_bytes(b"mp3")
    factory = WanS2VWorkflowFactory(workflow_path, tmp_path / "media")

    payload = factory({
        "prompt": "cinematic portrait",
        "duration_seconds": 3,
        "reference_url": "/api/media/uploads/ref.jpg",
        "audio_url": "/api/media/uploads/voice.mp3",
    })

    assert payload["workflow"]["6"]["inputs"]["text"] == "cinematic portrait"
    assert payload["workflow"]["52"]["inputs"]["image"] == "novel-video-reference.jpg"
    assert payload["workflow"]["58"]["inputs"]["audio"] == "novel-video-audio.mp3"
    assert payload["workflow"]["104"]["inputs"]["value"] == 13
    assert payload["workflow"]["113"]["inputs"]["filename_prefix"] == "video/novel-video"
    assert len(payload["images"]) == 2
    assert base64.b64decode(payload["images"][0]["image"]) == b"jpeg"
    assert base64.b64decode(payload["images"][1]["image"]) == b"mp3"


def test_factory_requires_existing_local_assets(tmp_path: Path):
    workflow_path = tmp_path / "workflow.json"
    workflow_fixture(workflow_path)
    factory = WanS2VWorkflowFactory(workflow_path, tmp_path / "media")
    with pytest.raises(ValueError, match="reference image"):
        factory({"prompt": "x", "duration_seconds": 3, "reference_url": None, "audio_url": None})
    with pytest.raises(ValueError, match="not found"):
        factory({
            "prompt": "x", "duration_seconds": 3,
            "reference_url": "/api/media/uploads/missing.jpg",
            "audio_url": "/api/media/uploads/missing.mp3",
        })


def test_factory_rejects_payload_over_runpod_limit(tmp_path: Path):
    workflow_path = tmp_path / "workflow.json"
    workflow_fixture(workflow_path)
    uploads = tmp_path / "media" / "uploads"
    uploads.mkdir(parents=True)
    (uploads / "ref.jpg").write_bytes(b"x" * 6_000_000)
    (uploads / "voice.mp3").write_bytes(b"x" * 4_000_001)
    factory = WanS2VWorkflowFactory(workflow_path, tmp_path / "media")
    with pytest.raises(ValueError, match="7 MiB"):
        factory({
            "prompt": "x", "duration_seconds": 3,
            "reference_url": "/api/media/uploads/ref.jpg",
            "audio_url": "/api/media/uploads/voice.mp3",
        })
