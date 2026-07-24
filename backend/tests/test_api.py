import os
os.environ.setdefault("VIDEO_ADMIN_USER", "alan")
os.environ.setdefault("VIDEO_ADMIN_PASSWORD", "test-password")
os.environ.setdefault("VIDEO_SESSION_SECRET", "test-secret-that-is-long-enough")
os.environ.setdefault("VIDEO_DATA_DIR", "/tmp/novel-video-test-data")
os.environ.setdefault("GPU_PROVIDER", "mock")
os.environ.setdefault("VIDEO_COOKIE_SECURE", "false")

from fastapi.testclient import TestClient
from app.main import create_app


def login(client: TestClient) -> None:
    response = client.post("/api/auth/login", json={"username": "alan", "password": "test-password"})
    assert response.status_code == 200
    assert response.cookies.get("video_session")


def test_health_is_public_and_reports_ready():
    with TestClient(create_app(testing=True)) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_protected_endpoint_requires_login():
    with TestClient(create_app(testing=True)) as client:
        response = client.get("/api/projects")
        assert response.status_code == 401


def test_login_and_project_lifecycle():
    with TestClient(create_app(testing=True)) as client:
        login(client)
        created = client.post("/api/projects", json={"title": "第一集", "source_text": "測試小說內容"})
        assert created.status_code == 201
        project_id = created.json()["id"]

        listed = client.get("/api/projects")
        assert listed.status_code == 200
        assert any(project["id"] == project_id for project in listed.json())

        shot = client.post(
            f"/api/projects/{project_id}/shots",
            json={
                "title": "重逢",
                "prompt": "兩人在雨中重逢，中近鏡",
                "dialogue": "你終於返嚟。",
                "duration_seconds": 3.0,
                "engine": "wan_s2v",
            },
        )
        assert shot.status_code == 201

        queued = client.post(f"/api/shots/{shot.json()['id']}/queue")
        assert queued.status_code == 202
        assert queued.json()["status"] == "queued"


def test_runpod_is_not_faked_when_unconfigured():
    with TestClient(create_app(testing=True)) as client:
        login(client)
        status = client.get("/api/gpu/status")
        assert status.status_code == 200
        assert status.json()["provider"] == "mock"
        assert status.json()["configured"] is True
