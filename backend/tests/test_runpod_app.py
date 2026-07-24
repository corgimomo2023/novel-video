import os
os.environ.setdefault("VIDEO_ADMIN_USER", "alan")
os.environ.setdefault("VIDEO_ADMIN_PASSWORD", "test-password")
os.environ.setdefault("VIDEO_SESSION_SECRET", "test-secret-that-is-long-enough")
os.environ.setdefault("VIDEO_DATA_DIR", "/tmp/novel-video-test-data")
os.environ.setdefault("GPU_PROVIDER", "mock")
os.environ.setdefault("VIDEO_COOKIE_SECURE", "false")

from fastapi.testclient import TestClient
from app.main import create_app


def test_runpod_without_endpoint_is_fail_closed(monkeypatch):
    monkeypatch.setenv("GPU_PROVIDER", "runpod")
    monkeypatch.setenv("RUNPOD_API_KEY", "rpa_test")
    monkeypatch.delenv("RUNPOD_ENDPOINT_ID", raising=False)
    with TestClient(create_app(testing=True)) as client:
        health = client.get("/api/health").json()
        assert health["provider"] == "runpod"
        assert health["configured"] is False
        response = client.post("/api/auth/login", json={"username": "alan", "password": "test-password"})
        assert response.status_code == 200
        project = client.post("/api/projects", json={"title": "No endpoint"}).json()
        shot = client.post(f"/api/projects/{project['id']}/shots", json={"title": "Blocked"}).json()
        queued = client.post(f"/api/shots/{shot['id']}/queue")
        assert queued.status_code == 503
