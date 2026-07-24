import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.init()

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def init(self):
        with self.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, source_text TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'draft', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS characters (
                id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', voice TEXT NOT NULL,
                reference_url TEXT, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS shots (
                id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                sequence INTEGER NOT NULL, title TEXT NOT NULL, prompt TEXT NOT NULL DEFAULT '',
                dialogue TEXT NOT NULL DEFAULT '', duration_seconds REAL NOT NULL DEFAULT 3,
                engine TEXT NOT NULL DEFAULT 'wan_s2v', status TEXT NOT NULL DEFAULT 'draft',
                output_url TEXT, reference_url TEXT, audio_url TEXT,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                shot_id TEXT NOT NULL REFERENCES shots(id) ON DELETE CASCADE,
                status TEXT NOT NULL DEFAULT 'queued', provider TEXT NOT NULL, progress INTEGER NOT NULL DEFAULT 0,
                error TEXT, cost_usd REAL NOT NULL DEFAULT 0, created_at TEXT NOT NULL,
                started_at TEXT, finished_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status, created_at);
            CREATE TABLE IF NOT EXISTS gpu_sessions (
                id TEXT PRIMARY KEY, provider TEXT NOT NULL, gpu_type TEXT NOT NULL, status TEXT NOT NULL,
                started_at TEXT, stopped_at TEXT, estimated_cost_usd REAL NOT NULL DEFAULT 0
            );
            ''')
            job_columns = {row["name"] for row in db.execute("PRAGMA table_info(jobs)").fetchall()}
            migrations = {
                "remote_job_id": "ALTER TABLE jobs ADD COLUMN remote_job_id TEXT",
                "remote_status": "ALTER TABLE jobs ADD COLUMN remote_status TEXT",
                "remote_updated_at": "ALTER TABLE jobs ADD COLUMN remote_updated_at TEXT",
            }
            for column, statement in migrations.items():
                if column not in job_columns:
                    db.execute(statement)
            shot_columns = {row["name"] for row in db.execute("PRAGMA table_info(shots)").fetchall()}
            shot_migrations = {
                "reference_url": "ALTER TABLE shots ADD COLUMN reference_url TEXT",
                "audio_url": "ALTER TABLE shots ADD COLUMN audio_url TEXT",
            }
            for column, statement in shot_migrations.items():
                if column not in shot_columns:
                    db.execute(statement)

    def rows(self, query: str, params=()):
        with self.connect() as db:
            return [dict(row) for row in db.execute(query, params).fetchall()]

    def row(self, query: str, params=()):
        with self.connect() as db:
            found = db.execute(query, params).fetchone()
            return dict(found) if found else None

    def execute(self, query: str, params=()):
        with self._lock, self.connect() as db:
            return db.execute(query, params).rowcount

    def create_project(self, title: str, source_text: str):
        item_id, stamp = str(uuid.uuid4()), now()
        self.execute("INSERT INTO projects VALUES (?, ?, ?, 'draft', ?, ?)", (item_id, title, source_text, stamp, stamp))
        return self.get_project(item_id)

    def list_projects(self):
        return self.rows('''SELECT p.*, COUNT(DISTINCT s.id) AS shot_count,
            COALESCE(SUM(CASE WHEN s.status='completed' THEN 1 ELSE 0 END),0) AS completed_shots
            FROM projects p LEFT JOIN shots s ON s.project_id=p.id
            GROUP BY p.id ORDER BY p.updated_at DESC''')

    def get_project(self, project_id: str):
        project = self.row("SELECT * FROM projects WHERE id=?", (project_id,))
        if not project:
            return None
        project["characters"] = self.rows("SELECT * FROM characters WHERE project_id=? ORDER BY created_at", (project_id,))
        project["shots"] = self.rows("SELECT * FROM shots WHERE project_id=? ORDER BY sequence", (project_id,))
        return project

    def update_project(self, project_id: str, changes: dict):
        allowed = {k: v for k, v in changes.items() if v is not None and k in {"title", "source_text"}}
        if allowed:
            allowed["updated_at"] = now()
            clause = ", ".join(f"{key}=?" for key in allowed)
            self.execute(f"UPDATE projects SET {clause} WHERE id=?", (*allowed.values(), project_id))
        return self.get_project(project_id)

    def create_character(self, project_id: str, data: dict):
        item_id, stamp = str(uuid.uuid4()), now()
        self.execute("INSERT INTO characters (id,project_id,name,description,voice,created_at) VALUES (?,?,?,?,?,?)",
                     (item_id, project_id, data["name"], data["description"], data["voice"], stamp))
        return self.row("SELECT * FROM characters WHERE id=?", (item_id,))

    def create_shot(self, project_id: str, data: dict):
        item_id, stamp = str(uuid.uuid4()), now()
        seq = self.row("SELECT COALESCE(MAX(sequence),0)+1 AS n FROM shots WHERE project_id=?", (project_id,))["n"]
        self.execute('''INSERT INTO shots
            (id,project_id,sequence,title,prompt,dialogue,duration_seconds,engine,status,reference_url,audio_url,created_at,updated_at)
            VALUES (?,?,?,?,?,?,?,?, 'draft',?,?,?,?)''',
            (item_id, project_id, seq, data["title"], data["prompt"], data["dialogue"], data["duration_seconds"], data["engine"],
             data.get("reference_url"), data.get("audio_url"), stamp, stamp))
        return self.row("SELECT * FROM shots WHERE id=?", (item_id,))

    def update_shot(self, shot_id: str, changes: dict):
        allowed = {k: v for k, v in changes.items() if v is not None and k in {"title","prompt","dialogue","duration_seconds","engine","reference_url","audio_url"}}
        if allowed:
            allowed["updated_at"] = now()
            clause = ", ".join(f"{key}=?" for key in allowed)
            self.execute(f"UPDATE shots SET {clause} WHERE id=?", (*allowed.values(), shot_id))
        return self.row("SELECT * FROM shots WHERE id=?", (shot_id,))

    def queue_shot(self, shot_id: str, provider: str):
        shot = self.row("SELECT * FROM shots WHERE id=?", (shot_id,))
        if not shot:
            return None
        existing = self.row("SELECT * FROM jobs WHERE shot_id=? AND status IN ('queued','running')", (shot_id,))
        if existing:
            return existing
        job_id = str(uuid.uuid4())
        self.execute("INSERT INTO jobs (id,project_id,shot_id,status,provider,created_at) VALUES (?,?,?,'queued',?,?)",
                     (job_id, shot["project_id"], shot_id, provider, now()))
        self.execute("UPDATE shots SET status='queued', updated_at=? WHERE id=?", (now(), shot_id))
        return self.row("SELECT * FROM jobs WHERE id=?", (job_id,))

    def list_jobs(self):
        return self.rows('''SELECT j.*, s.title AS shot_title, s.engine, p.title AS project_title
            FROM jobs j JOIN shots s ON s.id=j.shot_id JOIN projects p ON p.id=j.project_id
            ORDER BY j.created_at DESC LIMIT 200''')

    def claim_job(self, provider: str | None = None):
        with self._lock, self.connect() as db:
            if provider:
                job = db.execute(
                    "SELECT * FROM jobs WHERE status='queued' AND provider=? ORDER BY created_at LIMIT 1",
                    (provider,),
                ).fetchone()
            else:
                job = db.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY created_at LIMIT 1").fetchone()
            if not job:
                return None
            updated = db.execute("UPDATE jobs SET status='running', progress=5, started_at=? WHERE id=? AND status='queued'", (now(), job["id"]))
            if updated.rowcount != 1:
                return None
            db.execute("UPDATE shots SET status='running', updated_at=? WHERE id=?", (now(), job["shot_id"]))
            return dict(job)

    def finish_job(self, job_id: str, shot_id: str, output_url: str, cost: float = 0):
        stamp = now()
        self.execute("UPDATE jobs SET status='completed',progress=100,finished_at=?,cost_usd=? WHERE id=?", (stamp, cost, job_id))
        self.execute("UPDATE shots SET status='completed',output_url=?,updated_at=? WHERE id=?", (output_url, stamp, shot_id))

    def fail_job(self, job_id: str, shot_id: str, error: str):
        stamp = now()
        self.execute("UPDATE jobs SET status='failed',error=?,finished_at=? WHERE id=?", (error[:2000], stamp, job_id))
        self.execute("UPDATE shots SET status='failed',updated_at=? WHERE id=?", (stamp, shot_id))

    def retry_running_jobs(self):
        self.execute("UPDATE jobs SET status='queued',progress=0,started_at=NULL WHERE status='running'")
        self.execute("UPDATE shots SET status='queued' WHERE status='running'")
