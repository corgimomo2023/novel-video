import asyncio
import json
import os
import shutil
import tempfile
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, Request, Response, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .auth import authenticate, clear_session, require_user, set_session
from .db import Database
from .schemas import CharacterCreate, LoginRequest, ProjectCreate, ProjectUpdate, ShotCreate, ShotUpdate
from .worker import MockWorker


def create_app(testing: bool = False) -> FastAPI:
    data_dir = Path(os.environ.get("VIDEO_DATA_DIR", "/app/data"))
    if testing:
        data_dir = Path(tempfile.mkdtemp(prefix="novel-video-test-"))
    media_dir = data_dir / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    db = Database(data_dir / "video.db")
    worker = MockWorker(db, media_dir)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if os.environ.get("GPU_PROVIDER", "mock") == "mock":
            worker.start()
        if not testing and not db.list_projects():
            seed_demo(db)
        yield
        worker.stop()
        if testing:
            shutil.rmtree(data_dir, ignore_errors=True)

    app = FastAPI(title="小說影片工作室", version="0.1.0", lifespan=lifespan)
    app.state.db = db
    app.state.media_dir = media_dir

    @app.get("/api/health")
    def health():
        return {"status": "ok", "service": "novel-video", "provider": os.environ.get("GPU_PROVIDER", "mock")}

    @app.post("/api/auth/login")
    def login(payload: LoginRequest):
        if not authenticate(payload.username, payload.password):
            raise HTTPException(status_code=401, detail="帳戶或密碼不正確")
        response = JSONResponse({"username": payload.username})
        set_session(response, payload.username)
        return response

    @app.post("/api/auth/logout")
    def logout():
        response = JSONResponse({"ok": True})
        clear_session(response)
        return response

    @app.get("/api/auth/me")
    def me(user: str = Depends(require_user)):
        return {"username": user}

    @app.get("/api/projects")
    def list_projects(_: str = Depends(require_user)):
        return db.list_projects()

    @app.post("/api/projects", status_code=status.HTTP_201_CREATED)
    def create_project(payload: ProjectCreate, _: str = Depends(require_user)):
        return db.create_project(payload.title, payload.source_text)

    @app.get("/api/projects/{project_id}")
    def get_project(project_id: str, _: str = Depends(require_user)):
        project = db.get_project(project_id)
        if not project:
            raise HTTPException(404, "Project not found")
        return project

    @app.patch("/api/projects/{project_id}")
    def update_project(project_id: str, payload: ProjectUpdate, _: str = Depends(require_user)):
        project = db.update_project(project_id, payload.model_dump())
        if not project:
            raise HTTPException(404, "Project not found")
        return project

    @app.post("/api/projects/{project_id}/characters", status_code=201)
    def create_character(project_id: str, payload: CharacterCreate, _: str = Depends(require_user)):
        if not db.get_project(project_id):
            raise HTTPException(404, "Project not found")
        return db.create_character(project_id, payload.model_dump())

    @app.post("/api/projects/{project_id}/shots", status_code=201)
    def create_shot(project_id: str, payload: ShotCreate, _: str = Depends(require_user)):
        if not db.get_project(project_id):
            raise HTTPException(404, "Project not found")
        return db.create_shot(project_id, payload.model_dump())

    @app.patch("/api/shots/{shot_id}")
    def update_shot(shot_id: str, payload: ShotUpdate, _: str = Depends(require_user)):
        shot = db.update_shot(shot_id, payload.model_dump())
        if not shot:
            raise HTTPException(404, "Shot not found")
        return shot

    @app.post("/api/shots/{shot_id}/queue", status_code=202)
    def queue_shot(shot_id: str, _: str = Depends(require_user)):
        job = db.queue_shot(shot_id, os.environ.get("GPU_PROVIDER", "mock"))
        if not job:
            raise HTTPException(404, "Shot not found")
        return job

    @app.post("/api/projects/{project_id}/queue", status_code=202)
    def queue_project(project_id: str, _: str = Depends(require_user)):
        project = db.get_project(project_id)
        if not project:
            raise HTTPException(404, "Project not found")
        jobs = [db.queue_shot(shot["id"], os.environ.get("GPU_PROVIDER", "mock"))
                for shot in project["shots"] if shot["status"] not in {"queued", "running"}]
        return {"queued": len([job for job in jobs if job]), "jobs": jobs}

    @app.get("/api/jobs")
    def list_jobs(_: str = Depends(require_user)):
        return db.list_jobs()

    @app.get("/api/dashboard")
    def dashboard(_: str = Depends(require_user)):
        projects = db.list_projects()
        jobs = db.list_jobs()
        return {
            "projects": len(projects),
            "shots": sum(int(item["shot_count"]) for item in projects),
            "completed": sum(int(item["completed_shots"]) for item in projects),
            "queued": len([job for job in jobs if job["status"] in {"queued", "running"}]),
            "recent_jobs": jobs[:8],
        }

    @app.get("/api/gpu/status")
    def gpu_status(_: str = Depends(require_user)):
        provider = os.environ.get("GPU_PROVIDER", "mock")
        configured = provider == "mock" or bool(os.environ.get("RUNPOD_API_KEY"))
        return {
            "provider": provider,
            "configured": configured,
            "status": "mock-ready" if provider == "mock" else ("idle" if configured else "unconfigured"),
            "gpu_type": "Mock GPU" if provider == "mock" else os.environ.get("RUNPOD_GPU_TYPE", "A100 PCIe 80GB"),
            "mode": "本機模擬" if provider == "mock" else "RunPod Serverless Flex",
            "note": "目前生成測試片，不會產生GPU費用" if provider == "mock" else "Minimum workers必須設為0",
        }

    @app.post("/api/media/upload", status_code=201)
    async def upload_media(file: UploadFile = File(...), _: str = Depends(require_user)):
        suffix = Path(file.filename or "asset.bin").suffix.lower()
        if suffix not in {".png", ".jpg", ".jpeg", ".webp", ".wav", ".mp3", ".m4a", ".mp4"}:
            raise HTTPException(400, "Unsupported file type")
        upload_dir = media_dir / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        target = upload_dir / f"{uuid.uuid4()}{suffix}"
        size = 0
        with target.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > 100 * 1024 * 1024:
                    target.unlink(missing_ok=True)
                    raise HTTPException(413, "File too large")
                output.write(chunk)
        return {"url": f"/api/media/uploads/{target.name}", "name": file.filename, "size": size}

    @app.get("/api/media/{folder}/{filename}")
    def get_media(folder: str, filename: str, _: str = Depends(require_user)):
        if folder not in {"uploads", "outputs"} or Path(filename).name != filename:
            raise HTTPException(404)
        path = media_dir / folder / filename
        if not path.is_file():
            raise HTTPException(404)
        return FileResponse(path)

    @app.get("/api/events")
    async def events(request: Request, _: str = Depends(require_user)):
        async def stream():
            while not await request.is_disconnected():
                jobs = db.list_jobs()
                payload = {"queued": len([j for j in jobs if j["status"] == "queued"]),
                           "running": len([j for j in jobs if j["status"] == "running"]),
                           "completed": len([j for j in jobs if j["status"] == "completed"])}
                yield f"event: snapshot\ndata: {json.dumps(payload)}\n\n"
                await asyncio.sleep(2)
        return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})

    frontend_dist = Path(os.environ.get("FRONTEND_DIST", "/app/frontend"))
    if frontend_dist.is_dir():
        assets = frontend_dist / "assets"
        if assets.is_dir():
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

        @app.get("/{full_path:path}")
        def spa(full_path: str):
            candidate = frontend_dist / full_path
            if full_path and candidate.is_file() and frontend_dist in candidate.resolve().parents:
                return FileResponse(candidate)
            return FileResponse(frontend_dist / "index.html")

    return app


def seed_demo(db: Database) -> None:
    project = db.create_project("短篇測試：雨夜重逢", "雨夜，離開多年的林澈回到舊城，在車站再次遇見蘇晚。")
    db.create_character(project["id"], {"name": "林澈", "description": "沉著寡言，黑色外套", "voice": "zh-HK-WanLungNeural"})
    db.create_character(project["id"], {"name": "蘇晚", "description": "表面冷靜，內心激動", "voice": "zh-HK-HiuGaaiNeural"})
    for shot in [
        {"title": "雨夜車站", "prompt": "cinematic rainy train station at night, wide establishing shot", "dialogue": "", "duration_seconds": 3.0, "engine": "camera_motion"},
        {"title": "抬頭重逢", "prompt": "woman looks up in surprise, medium close-up, subtle breathing", "dialogue": "你終於返嚟。", "duration_seconds": 3.5, "engine": "wan_s2v"},
        {"title": "沉默回應", "prompt": "man pauses under umbrella, restrained emotion, close-up", "dialogue": "對唔住，等咗你好耐。", "duration_seconds": 4.0, "engine": "echo_mimic"},
    ]:
        db.create_shot(project["id"], shot)


app = create_app()
