import subprocess
import threading
from pathlib import Path
from .db import Database


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
