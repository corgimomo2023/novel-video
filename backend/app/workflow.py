import base64
import copy
import json
import secrets
from pathlib import Path


class WanS2VWorkflowFactory:
    """Build a RunPod worker-comfyui input from one application shot."""

    ASSET_PREFIX = "/api/media/uploads/"
    MAX_RAW_ASSET_BYTES = 7 * 1024 * 1024

    def __init__(self, workflow_path: Path, media_dir: Path):
        self.workflow_path = workflow_path
        self.media_dir = media_dir
        self.template = json.loads(workflow_path.read_text())
        if not isinstance(self.template, dict) or not self.template:
            raise ValueError("Wan S2V API workflow is invalid")

    def __call__(self, shot: dict) -> dict:
        workflow = copy.deepcopy(self.template)
        reference = self._asset(shot.get("reference_url"), "reference image")
        audio = self._asset(shot.get("audio_url"), "audio")
        if reference.stat().st_size + audio.stat().st_size > self.MAX_RAW_ASSET_BYTES:
            raise ValueError("reference image and audio must total no more than 7 MiB")

        reference_name = f"novel-video-reference{reference.suffix.lower()}"
        audio_name = f"novel-video-audio{audio.suffix.lower()}"
        self._node(workflow, class_type="CLIPTextEncode", title="CLIP Text Encode (Positive Prompt)")["inputs"]["text"] = shot.get("prompt") or "cinematic portrait, natural movement"
        self._node(workflow, class_type="LoadImage")["inputs"]["image"] = reference_name
        self._node(workflow, class_type="LoadAudio")["inputs"]["audio"] = audio_name
        self._node(workflow, class_type="PrimitiveInt", title="Chunk Length")["inputs"]["value"] = self._chunk_length(float(shot.get("duration_seconds") or 3))
        self._node(workflow, class_type="SaveVideo")["inputs"]["filename_prefix"] = "video/novel-video"
        for node in workflow.values():
            if node.get("class_type") == "KSampler" and "seed" in node.get("inputs", {}):
                node["inputs"]["seed"] = secrets.randbits(63)

        return {
            "workflow": workflow,
            "images": [
                {"name": reference_name, "image": base64.b64encode(reference.read_bytes()).decode("ascii")},
                {"name": audio_name, "image": base64.b64encode(audio.read_bytes()).decode("ascii")},
            ],
        }

    def _asset(self, url: str | None, label: str) -> Path:
        if not url:
            raise ValueError(f"{label} is required for Wan S2V")
        if not url.startswith(self.ASSET_PREFIX):
            raise ValueError(f"invalid {label} URL")
        filename = url.removeprefix(self.ASSET_PREFIX)
        if not filename or Path(filename).name != filename:
            raise ValueError(f"invalid {label} URL")
        path = self.media_dir / "uploads" / filename
        if not path.is_file():
            raise ValueError(f"{label} file not found")
        return path

    @staticmethod
    def _chunk_length(duration_seconds: float) -> int:
        # The official workflow concatenates four chunks at 16 fps. Wan lengths
        # use the 4n+1 shape, so this gives roughly the requested 1-20 seconds.
        units = max(1, min(20, round(duration_seconds - 0.25)))
        return 1 + 4 * units

    @staticmethod
    def _node(workflow: dict, *, class_type: str, title: str | None = None) -> dict:
        matches = [
            node for node in workflow.values()
            if node.get("class_type") == class_type
            and (title is None or node.get("_meta", {}).get("title") == title)
        ]
        if len(matches) != 1:
            target = f"{class_type}/{title}" if title else class_type
            raise ValueError(f"workflow must contain exactly one {target} node")
        return matches[0]
