import base64
from pathlib import Path

import pytest

from app.db import Database
from app.worker import RunPodWorker


class FakeRunPodClient:
    def __init__(self, statuses):
        self.statuses = iter(statuses)
        self.submitted = []

    def submit(self, payload):
        self.submitted.append(payload)
        return {"id": "remote-123", "status": "IN_QUEUE"}

    def status(self, remote_job_id):
        assert remote_job_id == "remote-123"
        return next(self.statuses)


def create_job(db: Database):
    project = db.create_project("Test", "")
    shot = db.create_shot(project["id"], {
        "title": "Shot",
        "prompt": "A cinematic close-up",
        "dialogue": "Hello",
        "duration_seconds": 2,
        "engine": "wan_s2v",
    })
    db.queue_shot(shot["id"], "runpod")
    return db.claim_job()


def test_runpod_worker_completes_base64_video(tmp_path: Path):
    db = Database(tmp_path / "video.db")
    job = create_job(db)
    video = b"fake-mp4-content"
    client = FakeRunPodClient([
        {"id": "remote-123", "status": "IN_PROGRESS"},
        {"id": "remote-123", "status": "COMPLETED", "output": {"images": [
            {"filename": "video/ComfyUI_00001_.mp4", "type": "base64", "data": base64.b64encode(video).decode()}
        ]}},
    ])
    worker = RunPodWorker(db, tmp_path / "media", client, lambda shot: {"workflow": {"1": {"class_type": "Test"}}}, poll_interval=0)

    worker.process(job)

    saved_job = db.row("SELECT * FROM jobs WHERE id=?", (job["id"],))
    saved_shot = db.row("SELECT * FROM shots WHERE id=?", (job["shot_id"],))
    assert saved_job["status"] == "completed"
    assert saved_job["remote_job_id"] == "remote-123"
    assert saved_job["remote_status"] == "COMPLETED"
    assert saved_shot["output_url"].endswith(f"/{job['id']}.mp4")
    assert (tmp_path / "media" / "outputs" / f"{job['id']}.mp4").read_bytes() == video
    assert client.submitted == [{"workflow": {"1": {"class_type": "Test"}}}]


def test_runpod_worker_rejects_non_video_output(tmp_path: Path):
    db = Database(tmp_path / "video.db")
    job = create_job(db)
    client = FakeRunPodClient([
        {"id": "remote-123", "status": "COMPLETED", "output": {"images": [
            {"filename": "result.png", "type": "base64", "data": base64.b64encode(b"png").decode()}
        ]}},
    ])
    worker = RunPodWorker(db, tmp_path / "media", client, lambda shot: {"workflow": {}}, poll_interval=0)

    with pytest.raises(RuntimeError, match="video"):
        worker.process(job)
