import base64
import binascii
import subprocess
import threading
import time
import urllib.request
from pathlib import Path
from typing import Callable

from .db import Database, now


class MockWorker:
    def __init__(self, db: Database, media_dir: Path):
        self.db, self.media_dir = db, media_dir
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None

    def start(self):
        self.db.retry_running_jobs()
        self.thread = threading.Thread(target=self.run, name="mock-video-worker", daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=3)

    def run(self):
        while not self.stop_event.is_set():
            job = self.db.claim_job()
            if not job:
                self.stop_event.wait(1)
                continue
            try:
                self.render(job)
            except Exception as exc:
                self.db.fail_job(job["id"], job["shot_id"], str(exc))

    def render(self, job: dict):
        shot = self.db.row("SELECT * FROM shots WHERE id=?", (job["shot_id"],))
        output_dir = self.media_dir / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)
        output = output_dir / f"{job['id']}.mp4"
        duration = max(1.0, min(float(shot["duration_seconds"]), 10.0))
        title = shot["title"].replace("'", "").replace(":", "-")[:30]
        command = ["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=0x111827:s=960x540:d={duration}",
                   "-vf", f"drawtext=text='MOCK GPU - {title}':fontcolor=white:fontsize=32:x=(w-text_w)/2:y=(h-text_h)/2",
                   "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            raise RuntimeError(result.stderr[-1000:])
        self.db.finish_job(job["id"], job["shot_id"], f"/api/media/outputs/{output.name}")


class RunPodWorker:
    TERMINAL_FAILURES = {"FAILED", "CANCELLED", "TIMED_OUT"}
    VIDEO_SUFFIXES = {".mp4", ".webm", ".mov"}

    def __init__(
        self,
        db: Database,
        media_dir: Path,
        client,
        workflow_factory: Callable[[dict], dict],
        *,
        poll_interval: float = 3,
        max_wait_seconds: float = 3600,
        max_output_bytes: int = 500 * 1024 * 1024,
    ):
        self.db = db
        self.media_dir = media_dir
        self.client = client
        self.workflow_factory = workflow_factory
        self.poll_interval = poll_interval
        self.max_wait_seconds = max_wait_seconds
        self.max_output_bytes = max_output_bytes
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None

    def start(self):
        self.db.execute(
            "UPDATE jobs SET status='queued',progress=0,started_at=NULL "
            "WHERE provider='runpod' AND status='running' AND remote_job_id IS NULL"
        )
        self.thread = threading.Thread(target=self.run, name="runpod-video-worker", daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=5)

    def run(self):
        while not self.stop_event.is_set():
            job = self.db.row(
                "SELECT * FROM jobs WHERE provider='runpod' AND status='running' "
                "AND remote_job_id IS NOT NULL ORDER BY started_at LIMIT 1"
            )
            if not job:
                job = self.db.claim_job(provider="runpod")
            if not job:
                self.stop_event.wait(1)
                continue
            try:
                self.process(job)
            except Exception as exc:
                self.db.fail_job(job["id"], job["shot_id"], str(exc))

    def process(self, job: dict):
        shot = self.db.row("SELECT * FROM shots WHERE id=?", (job["shot_id"],))
        if not shot:
            raise RuntimeError("shot not found")

        remote_job_id = job.get("remote_job_id")
        if not remote_job_id:
            submitted = self.client.submit(self.workflow_factory(shot))
            remote_job_id = submitted.get("id")
            if not remote_job_id:
                raise RuntimeError("RunPod submission returned no job ID")
            self.db.execute(
                "UPDATE jobs SET remote_job_id=?,remote_status=?,remote_updated_at=? WHERE id=?",
                (remote_job_id, submitted.get("status", "IN_QUEUE"), now(), job["id"]),
            )

        started = time.monotonic()
        while not self.stop_event.is_set():
            if time.monotonic() - started > self.max_wait_seconds:
                raise RuntimeError("RunPod job polling timed out")
            remote = self.client.status(remote_job_id)
            status = str(remote.get("status", "UNKNOWN")).upper()
            progress = 50 if status == "IN_PROGRESS" else 10
            self.db.execute(
                "UPDATE jobs SET remote_status=?,remote_updated_at=?,progress=? WHERE id=?",
                (status, now(), progress, job["id"]),
            )
            if status == "COMPLETED":
                output_path = self._save_video(job["id"], remote.get("output") or {})
                self.db.finish_job(
                    job["id"], job["shot_id"], f"/api/media/outputs/{output_path.name}"
                )
                self.db.execute(
                    "UPDATE jobs SET remote_status='COMPLETED',remote_updated_at=? WHERE id=?",
                    (now(), job["id"]),
                )
                return
            if status in self.TERMINAL_FAILURES:
                detail = remote.get("error") or remote.get("output") or status
                raise RuntimeError(f"RunPod job {status}: {str(detail)[:1000]}")
            if self.poll_interval:
                self.stop_event.wait(self.poll_interval)

        raise RuntimeError("worker stopped while RunPod job was active")

    def _save_video(self, job_id: str, output: dict) -> Path:
        files = output.get("images") if isinstance(output, dict) else None
        if not isinstance(files, list):
            raise RuntimeError("RunPod output contains no video files")
        video = next(
            (
                item for item in files
                if isinstance(item, dict)
                and Path(str(item.get("filename", ""))).suffix.lower() in self.VIDEO_SUFFIXES
            ),
            None,
        )
        if not video:
            raise RuntimeError("RunPod output contains no video files")

        suffix = Path(str(video["filename"])).suffix.lower()
        output_dir = self.media_dir / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)
        target = output_dir / f"{job_id}{suffix}"
        output_type = video.get("type")
        data = video.get("data")
        if not isinstance(data, str):
            raise RuntimeError("RunPod video output is missing data")

        if output_type == "base64":
            if len(data) > (self.max_output_bytes * 4 // 3) + 16:
                raise RuntimeError("RunPod video output exceeds size limit")
            if "," in data:
                data = data.split(",", 1)[1]
            try:
                content = base64.b64decode(data, validate=True)
            except (binascii.Error, ValueError):
                raise RuntimeError("RunPod video output is invalid base64") from None
            if len(content) > self.max_output_bytes:
                raise RuntimeError("RunPod video output exceeds size limit")
            target.write_bytes(content)
        elif output_type == "s3_url":
            request = urllib.request.Request(data, headers={"User-Agent": "novel-video/0.1"})
            with urllib.request.urlopen(request, timeout=120) as response, target.open("wb") as handle:
                total = 0
                while chunk := response.read(8 * 1024 * 1024):
                    total += len(chunk)
                    if total > self.max_output_bytes:
                        target.unlink(missing_ok=True)
                        raise RuntimeError("RunPod video output exceeds size limit")
                    handle.write(chunk)
        else:
            raise RuntimeError(f"Unsupported RunPod output type: {output_type}")
        return target
