from pathlib import Path

from app.db import Database


def test_database_migrates_remote_job_tracking_columns(tmp_path: Path):
    db = Database(tmp_path / "video.db")
    columns = {row["name"] for row in db.rows("PRAGMA table_info(jobs)")}
    assert {"remote_job_id", "remote_status", "remote_updated_at"} <= columns
